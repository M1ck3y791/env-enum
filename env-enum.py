#!/usr/bin/env python3
"""
env_enum_tool.py
Comprehensive async environment & endpoint enumerator with JS crawling and optional JS execution.
Usage:
    python3 env_enum_tool.py --mode discovery --jsmode regex /path/to/input.txt
Modes: debug, verbose, discovery, quiet
JSmode: regex, exec
"""

import argparse
import asyncio
import aiohttp
import re
import sys
import os
from urllib.parse import urlparse, urljoin
from pathlib import Path
from collections import deque

# ----------------------------
# Configuration (tweakable)
# ----------------------------
CONCURRENCY = 80               # global concurrency
REQUEST_TIMEOUT = 10           # per-request timeout secs
MAX_JS_FETCH_PER_HOST = 25     # cap JS fetches per page
TITLE_RE = re.compile(rb"<title>(.*?)</title>", re.I | re.S)

# Built-in curated lists (reasonable size)
ENV_PREFIXES = [
    "dev", "stage", "staging", "uat", "qa", "test",
    "beta", "preprod", "preview", "internal", "canary", "sandbox"
] + [f"v{i}" for i in range(1, 11)]

COMMON_PATHS = [
    "", "api", "api/v1", "api/v2", "v1", "v2", "v3",
    "swagger", "swagger.json", "swagger-ui", "api/docs",
    "openapi", "openapi.json", "docs", "doc",
    "graphql", "graphiql", "health", "status", "debug",
    "admin", "dashboard", "portal", "api-docs"
]

# Small param hint list to fuzz
PARAM_HINTS = ["id", "page", "limit", "offset", "token", "auth", "user", "q", "query", "search"]

# Regexes used for JS/html/JS body parsing
SCRIPT_SRC_RE = re.compile(r'<script[^>]+src=["\']([^"\']+)["\']', re.I)
ABS_URL_RE = re.compile(rb"https?://[^\s\"'<>]+", re.I)
REL_URL_RE = re.compile(rb"['\"](/[^\"']+?)['\"]")
JSON_RE = re.compile(rb"[A-Za-z0-9_\-\/]+\.json")
PARAM_RE = re.compile(rb"[?&]([a-zA-Z0-9_\-]+)=")
API_HINT_RE = re.compile(rb"(?:/|\\b)(api|v[0-9]+|graphql|openapi|swagger)(?:/|\\b)", re.I)
SENSITIVE_RE = re.compile(rb"(token|secret|apikey|authorization|bearer|jwt)", re.I)

# ----------------------------
# Optional PyMiniRacer for JS execution
# ----------------------------
try:
    from py_mini_racer import py_mini_racer
    _HAS_PYMINIRACER = True
except Exception:
    _HAS_PYMINIRACER = False

# ----------------------------
# Utility helpers
# ----------------------------
def normalize_host_from_input(line: str) -> str:
    line = line.strip()
    if not line:
        return ""
    parsed = urlparse(line if "://" in line else "http://" + line)
    host = parsed.netloc or parsed.path
    if "@" in host:
        host = host.split("@", 1)[1]
    host = host.split(":", 1)[0]
    return host

def generate_env_subdomains(host: str):
    parts = host.split(".")
    if len(parts) < 2:
        return {host}
    root = ".".join(parts[-2:])
    left = parts[:-2]
    base_label = parts[0] if parts else ""
    candidates = set([host])
    for env in ENV_PREFIXES:
        candidates.add(f"{env}.{host}")
        candidates.add(f"{env}-{base_label}.{root}")
        candidates.add(f"{base_label}-{env}.{root}")
        if left:
            left_join = ".".join(left)
            candidates.add(f"{env}.{left_join}.{root}")
            for lbl in ("api", "app", "admin", "panel"):
                candidates.add(f"{env}-{lbl}.{host}")
                candidates.add(f"{lbl}-{env}.{host}")
                candidates.add(f"{lbl}.{env}.{host}")
    if "api" not in host:
        candidates.add(f"api.{host}")
        for env in ENV_PREFIXES:
            candidates.add(f"api-{env}.{host}")
            candidates.add(f"{env}-api.{host}")
    return candidates

def build_paths_with_hash_variants():
    all_paths = []
    for p in COMMON_PATHS:
        if p in ("", "/"):
            all_paths.extend(["", "#", "/#", "/#/"])
        else:
            all_paths.append(p)
            all_paths.append(f"#/{p}")
            all_paths.append(f"/#/{p}")
            all_paths.append(f"{p}#")
            all_paths.append(f"{p}#/")
    seen = set()
    out = []
    for p in all_paths:
        if p not in seen:
            out.append(p)
            seen.add(p)
    return out

ALL_PATHS = build_paths_with_hash_variants()

def construct_url(scheme: str, host: str, path: str) -> str:
    if path == "" or path == "/":
        return f"{scheme}://{host}"
    if path.startswith("#"):
        if path.startswith("/#"):
            return f"{scheme}://{host}{path}"
        return f"{scheme}://{host}/{path}"
    return f"{scheme}://{host}/{path.lstrip('/')}"

# ----------------------------
# Logging / output according to mode
# ----------------------------
class Logger:
    def __init__(self, mode: str, output_file: Path):
        self.mode = mode  # debug, verbose, discovery, quiet
        self.output_file = output_file
        self._printed = set()

    def _should_print(self, level):
        # mapping levels to mode
        if self.mode == "debug":
            return True
        if self.mode == "verbose":
            return level in ("info", "warn", "discover")
        if self.mode == "discovery":
            return level == "discover"
        if self.mode == "quiet":
            return False
        return False

    def info(self, msg: str):
        if self._should_print("info"):
            print(msg, flush=True)

    def warn(self, msg: str):
        if self._should_print("warn"):
            print(msg, flush=True)

    def discover(self, tag: str, value: str):
        # minimal discovery printing (no timestamps), also append to output file
        line = f"[{tag}] {value}"
        if self._should_print("discover") and line not in self._printed:
            print(line, flush=True)
            self._printed.add(line)
        # always append discoveries to file (even in quiet mode)
        try:
            with open(self.output_file, "a") as fh:
                fh.write(line + "\n")
        except Exception:
            pass

# ----------------------------
# JS execution helper (best-effort)
# ----------------------------
def execute_js_and_extract(js_text: str):
    """
    Evaluate JS in a safe minimal context using py_mini_racer (best-effort).
    We do not execute untrusted code fully — only attempt to evaluate simple expressions
    that look like string concatenations or constants. This is best-effort and may
    raise; guard callers accordingly.
    """
    extracted = set()
    if not _HAS_PYMINIRACER:
        return extracted
    try:
        ctx = py_mini_racer.MiniRacer()
        # Heuristic: find var assignments to strings and concatenations
        # Very limited approach: find "var x = '...';" or "const x = '...';"
        for m in re.findall(r"(?:var|let|const)\s+([A-Za-z0-9_$]+)\s*=\s*([\"'].*?[\"'])\s*;", js_text, re.S):
            try:
                val = ctx.eval(m[1])
                if isinstance(val, str) and len(val) > 3 and ("http" in val or "/" in val or "api" in val):
                    extracted.add(val)
            except Exception:
                continue
        # Try to evaluate simple concatenation expressions like '"/api/" + ver + "/x"'
        # Find simple quoted fragments joined by +, ignore if dynamic variables unknown (best-effort)
        for expr in re.findall(r"([\"']\/[^\n\"']+[\"'](?:\s*\+\s*[^\n;]+)+)", js_text):
            try:
                val = ctx.eval(expr)
                if isinstance(val, str) and len(val) > 3:
                    extracted.add(val)
            except Exception:
                continue
    except Exception:
        pass
    return extracted

# ----------------------------
# Main enumerator class
# ----------------------------
class EnvEnumerator:
    def __init__(self, input_file: str, logger: Logger, jsmode: str = "regex"):
        self.input_path = Path(input_file).resolve()
        self.base_dir = self.input_path.parent
        self.output_file = self.base_dir / "env-enum.txt"
        self.queue = asyncio.Queue()
        self.seen = set()
        self.alive = dict()  # url -> (status,title)
        self.logger = logger
        self.jsmode = jsmode
        self.sem = asyncio.Semaphore(CONCURRENCY)
        self.session = None
        # track discoveries to avoid duplicates in prints
        self.found_urls = set()
        self.found_params = set()
        self.found_js_endpoints = set()
        self.found_api_docs = set()

    async def seed(self):
        with open(self.input_path, "r") as fh:
            for line in fh:
                host = normalize_host_from_input(line)
                if not host:
                    continue
                candidates = generate_env_subdomains(host)
                for cand in candidates:
                    for scheme in ("http", "https"):
                        for path in ALL_PATHS:
                            url = construct_url(scheme, cand, path)
                            await self.enqueue(url)

    async def enqueue(self, url: str):
        u = url.strip()
        if not u or u in self.seen:
            return
        self.seen.add(u)
        await self.queue.put(u)

    async def fetch(self, url: str):
        try:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            async with self.sem:
                async with self.session.get(url, allow_redirects=True, timeout=timeout) as resp:
                    status = resp.status
                    body = await resp.read()
                    headers = resp.headers
        except Exception as e:
            if self.logger.mode == "debug":
                self.logger.warn(f"[ERR] fetch {url} -> {e}")
            return

        # extract title
        title = ""
        m = TITLE_RE.search(body)
        if m:
            try:
                title = m.group(1).decode(errors="ignore").strip()
            except:
                title = ""

        # if alive (status < 500), treat as discovery
        if status and status < 500:
            if url not in self.found_urls:
                self.found_urls.add(url)
                self.alive[url] = (status, title)
                self.logger.discover("DISCOVERY", f"{url} [{status}] {title}")

        ctype = headers.get("Content-Type", "")
        discovered_urls = set()
        discovered_params = set()
        js_links = set()

        # HTML-like: extract script src and relative paths
        if body and (b"<script" in body or "text/html" in ctype or "application/xhtml+xml" in ctype):
            try:
                html_text = body.decode("utf-8", "ignore")
                for m in SCRIPT_SRC_RE.findall(html_text):
                    if m.startswith("//"):
                        js_links.add(f"{urlparse(url).scheme}:{m}")
                    elif m.startswith("http"):
                        js_links.add(m)
                    else:
                        js_links.add(urljoin(url, m))
                for rm in re.findall(r'["\'](/[^"\']+)["\']', html_text):
                    discovered_urls.add(urljoin(url, rm))
            except Exception:
                pass

        # find absolute and relative URLs and JSON refs in body
        for m in ABS_URL_RE.findall(body):
            try:
                discovered_urls.add(m.decode())
            except:
                pass
        for m in REL_URL_RE.findall(body):
            try:
                discovered_urls.add(urljoin(url, m.decode()))
            except:
                pass
        for m in JSON_RE.findall(body):
            try:
                candidate = m.decode()
                if candidate.startswith("/"):
                    discovered_urls.add(urljoin(url, candidate))
                else:
                    discovered_urls.add(urljoin(url, "/" + candidate))
            except:
                pass

        # Process JS links: fetch and parse
        if js_links:
            js_list = list(js_links)[:MAX_JS_FETCH_PER_HOST]
            js_tasks = [self.fetch_js(js_url) for js_url in js_list]
            js_results = await asyncio.gather(*js_tasks, return_exceptions=True)
            for res in js_results:
                if not res:
                    continue
                endp_set, param_set = res
                for e in endp_set:
                    if isinstance(e, bytes):
                        try:
                            e = e.decode()
                        except:
                            continue
                    if e.startswith("/"):
                        discovered_urls.add(urljoin(url, e))
                    elif e.startswith("http"):
                        discovered_urls.add(e)
                    else:
                        discovered_urls.add(urljoin(url, e))
                    if e not in self.found_js_endpoints:
                        self.found_js_endpoints.add(e)
                        self.logger.discover("JS-ENDPOINT", e)
                for p in param_set:
                    if p not in self.found_params:
                        self.found_params.add(p)
                        self.logger.discover("PARAM", p)
                        base = url.split("?", 1)[0]
                        fuzz_url = f"{base}?{p}=FUZZ"
                        discovered_urls.add(fuzz_url)

        # detect API docs / swagger / openapi / graphql in discovered urls
        for su in list(discovered_urls):
            low = su.lower()
            if any(k in low for k in ("/swagger", "swagger.json", "openapi", "openapi.json", "graphql", "graphiql", "/docs")):
                if su not in self.found_api_docs:
                    self.found_api_docs.add(su)
                    self.logger.discover("API-DOC", su)

        # enqueue discovered urls
        for du in discovered_urls:
            await self.enqueue(du)

    async def fetch_js(self, js_url: str):
        endpoints = set()
        params = set()
        try:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            async with self.sem:
                async with self.session.get(js_url, allow_redirects=True, timeout=timeout) as r:
                    if r.status != 200:
                        return endpoints, params
                    body = await r.read()
        except Exception:
            return endpoints, params

        # regex-based extraction
        try:
            for m in ABS_URL_RE.findall(body):
                try:
                    endpoints.add(m.decode())
                except:
                    pass
            for m in REL_URL_RE.findall(body):
                try:
                    endpoints.add(m.decode())
                except:
                    pass
            for m in JSON_RE.findall(body):
                try:
                    endpoints.add(m.decode())
                except:
                    pass
            for m in PARAM_RE.findall(body):
                try:
                    params.add(m.decode())
                except:
                    pass
            for m in API_HINT_RE.findall(body):
                try:
                    endpoints.add(m.decode())
                except:
                    pass
            for m in SENSITIVE_RE.findall(body):
                try:
                    endpoints.add("SENSITIVE:" + m.decode())
                except:
                    pass
        except Exception:
            pass

        # optional JS execution mode for dynamic string extraction
        if self.jsmode == "exec" and _HAS_PYMINIRACER:
            try:
                text = body.decode("utf-8", "ignore")
                extracted = execute_js_and_extract(text)
                for ex in extracted:
                    endpoints.add(ex)
            except Exception:
                pass

        return endpoints, params

    async def worker(self):
        while True:
            try:
                url = await self.queue.get()
            except asyncio.CancelledError:
                break
            try:
                if not url.startswith("http"):
                    await self.enqueue("http://" + url)
                    await self.enqueue("https://" + url)
                    self.queue.task_done()
                    continue
                await self.fetch(url)
            except Exception as e:
                if self.logger.mode == "debug":
                    self.logger.warn(f"[ERR] worker processing {url} -> {e}")
            self.queue.task_done()

    async def run(self):
        # prepare output file (clear / rotate)
        try:
            if self.output_file.exists():
                bak = self.output_file.with_suffix(".bak")
                self.output_file.replace(bak)
        except Exception:
            pass
        # create empty file
        try:
            with open(self.output_file, "w") as fh:
                fh.write("")
        except Exception:
            pass

        conn = aiohttp.TCPConnector(limit=CONCURRENCY, ssl=False)
        async with aiohttp.ClientSession(connector=conn) as session:
            self.session = session
            await self.seed()
            worker_count = max(2, CONCURRENCY // 8)
            workers = [asyncio.create_task(self.worker()) for _ in range(worker_count)]
            await self.queue.join()
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

        # final dedupe and write
        lines = []
        for url, (status, title) in sorted(self.alive.items()):
            title_clean = title.replace("\n", " ").strip()
            lines.append(f"{url} [{status}] {title_clean}")
        uniq = []
        seen = set()
        for l in lines:
            if l not in seen:
                uniq.append(l)
                seen.add(l)
        try:
            with open(self.output_file, "w") as fh:
                fh.write("\n".join(uniq))
        except Exception:
            pass

        if self.logger.mode != "quiet":
            print(f"[DONE] Saved {len(uniq)} discoveries to {self.output_file}", flush=True)

# ----------------------------
# CLI / Entrypoint
# ----------------------------
def parse_args():
    p = argparse.ArgumentParser(description="Env & endpoint enumerator (async) with JS crawling")
    p.add_argument("input_file", help="Path to input file containing domains/urls (one per line)")
    p.add_argument("--mode", choices=("debug", "verbose", "discovery", "quiet"), default="discovery", help="Output verbosity mode")
    p.add_argument("--jsmode", choices=("regex", "exec"), default="regex", help="JS extraction mode: regex or exec (py-mini-racer)")
    p.add_argument("--concurrency", type=int, default=CONCURRENCY, help="Global concurrency")
    return p.parse_args()

def main():
    args = parse_args()

    # adjust concurrency if provided
    global CONCURRENCY
    CONCURRENCY = args.concurrency

    input_path = Path(args.input_file).resolve()
    if not input_path.exists():
        print("Input file not found:", input_path)
        sys.exit(1)

    # JS exec fallback
    if args.jsmode == "exec" and not _HAS_PYMINIRACER:
        if args.mode != "quiet":
            print("[WARN] py-mini-racer not found; falling back to regex JS extraction")
        args.jsmode = "regex"

    logger = Logger(args.mode, input_path.parent / "env-enum.txt")
    enumerator = EnvEnumerator(str(input_path), logger, jsmode=args.jsmode)
    try:
        asyncio.run(enumerator.run())
    except KeyboardInterrupt:
        if args.mode != "quiet":
            print("[INTERRUPT] interrupted by user", flush=True)

if __name__ == "__main__":
    main()

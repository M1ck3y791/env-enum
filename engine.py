import asyncio
import aiohttp
from pathlib import Path
from urllib.parse import urlparse, urljoin

from core.config import (
    CONCURRENCY, REQUEST_TIMEOUT, MAX_JS_FETCH_PER_HOST,
    TITLE_RE, API_HINT_RE, ABS_URL_RE, REL_URL_RE, JSON_RE,
)
from core.logger import Logger
from core.utils import (
    ALL_PATHS, generate_env_subdomains, normalize_host_from_input,
    construct_url
)
from scanner import Scanner


class EnvEnumerator:
    """
    The main enumeration engine.
    Cleaned-up structure but NO logic alterations.
    """

    def __init__(self, input_file: str, logger: Logger, jsmode: str = "regex"):
        self.input_path = Path(input_file).resolve()
        self.base_dir = self.input_path.parent
        self.output_file = self.base_dir / "env-enum.txt"

        self.logger = logger
        self.jsmode = jsmode

        # Async elements
        self.queue = asyncio.Queue()
        self.sem = asyncio.Semaphore(CONCURRENCY)
        self.session = None

        # State tracking
        self.seen = set()
        self.alive = {}
        self.found_urls = set()
        self.found_api_docs = set()
        self.found_js_endpoints = set()
        self.found_params = set()

        # Scanner module
        self.scanner = Scanner(jsmode=self.jsmode)

    # ============================
    # 1. Queue + Input Seed
    # ============================
    async def seed_initial_targets(self):
        """
        Seed all initial URLs based on input file
        """
        with open(self.input_path, "r") as fh:
            for line in fh:
                host = normalize_host_from_input(line)
                if not host:
                    continue

                for sub in generate_env_subdomains(host):
                    for scheme in ("http", "https"):
                        for path in ALL_PATHS:
                            url = construct_url(scheme, sub, path)
                            await self.enqueue(url)

    async def enqueue(self, url: str):
        """
        Add new URL to the queue if not processed already.
        """
        url = url.strip()
        if not url or url in self.seen:
            return
        self.seen.add(url)
        await self.queue.put(url)

    # ============================
    # 2. HTTP Fetch
    # ============================
    async def fetch(self, url: str):
        """
        Performs HTTP fetch with timeout + redirect support.
        Then triggers HTML/JS scanning.
        """

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

        self._record_alive(url, status, body)

        # Extract URLs from HTML/JS
        discovered = await self._process_body(url, body, headers)

        # Deep recursion: enqueue everything discovered
        for u in discovered:
            await self.enqueue(u)

    # ============================
    # 2A. Alive Discovery
    # ============================
    def _record_alive(self, url, status, body):
        """
        Log reachable endpoints (<500) and extract <title>.
        """
        if not status or status >= 500:
            return

        title = ""
        m = TITLE_RE.search(body)
        if m:
            try:
                title = m.group(1).decode(errors="ignore").strip()
            except:
                pass

        if url not in self.found_urls:
            self.found_urls.add(url)
            self.alive[url] = (status, title)
            self.logger.discover("DISCOVERY", f"{url} [{status}] {title}")

    # ============================
    # 3. Scanning logic (calls scanner.py)
    # ============================
    async def _process_body(self, base_url: str, body: bytes, headers):
        """
        Calls scanners for HTML, JS, API-doc, param extraction.
        """

        discovered = set()

        # Basic extraction from HTML/JSON
        discovered |= self.scanner.extract_urls_from_body(base_url, body)
        discovered |= self.scanner.extract_absolute_refs(body)
        discovered |= self.scanner.extract_json_refs(base_url, body)

        # JS file discovery
        js_links = self.scanner.extract_js_links(base_url, body, headers)

        if js_links:
            js_results = await self._process_js_files(js_links, base_url)
            for url in js_results:
                discovered.add(url)

        # API documentation detection
        api_docs = self.scanner.detect_api_docs(discovered)
        for doc in api_docs:
            if doc not in self.found_api_docs:
                self.found_api_docs.add(doc)
                self.logger.discover("API-DOC", doc)

        return discovered

    # ============================
    # 3A. JS file processing
    # ============================
    async def _process_js_files(self, js_links, base_url):
        """
        Fetch JS files concurrently + extract endpoints/params.
        """

        links = list(js_links)[:MAX_JS_FETCH_PER_HOST]
        tasks = [self.scanner.fetch_and_scan_js(url, self.session) for url in links]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        discovered = set()

        for res in results:
            if not res:
                continue

            endpoints, params = res

            # Endpoints
            for e in endpoints:
                full = self.scanner.normalize_js_endpoint(base_url, e)
                if full and full not in self.found_js_endpoints:
                    self.found_js_endpoints.add(full)
                    self.logger.discover("JS-ENDPOINT", full)
                    discovered.add(full)

            # Params
            for p in params:
                if p not in self.found_params:
                    self.found_params.add(p)
                    self.logger.discover("PARAM", p)
                    base_clean = base_url.split("?", 1)[0]
                    discovered.add(f"{base_clean}?{p}=FUZZ")

        return discovered

    # ============================
    # 4. Worker Loop
    # ============================
    async def worker(self):
        """
        Worker that continuously processes queued URLs.
        """
        while True:
            try:
                url = await self.queue.get()
                if not url.startswith("http"):
                    await self.enqueue("http://" + url)
                    await self.enqueue("https://" + url)
                    self.queue.task_done()
                    continue

                await self.fetch(url)

            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.logger.mode == "debug":
                    self.logger.warn(f"[ERR] worker {url} -> {e}")

            self.queue.task_done()

    # ============================
    # 5. Run Engine
    # ============================
    async def run(self):
        """
        Main entrypoint: rotates output file, seeds, launches workers,
        waits for crawl to finish.
        """

        # Rotate old output
        if self.output_file.exists():
            self.output_file.replace(self.output_file.with_suffix(".bak"))

        # Create empty output
        with open(self.output_file, "w"):
            pass

        # Start session
        conn = aiohttp.TCPConnector(limit=CONCURRENCY, ssl=False)
        async with aiohttp.ClientSession(connector=conn) as session:
            self.session = session

            await self.seed_initial_targets()

            # Spawn workers
            worker_count = max(2, CONCURRENCY // 8)
            workers = [asyncio.create_task(self.worker()) for _ in range(worker_count)]

            await self.queue.join()
            for w in workers:
                w.cancel()

            await asyncio.gather(*workers, return_exceptions=True)

        self._final_write()

    # ============================
    # 6. Write Final Output
    # ============================
    def _final_write(self):
        """
        Deduplicate, sort, write alive endpoints to env-enum.txt
        """
        lines = []
        for url, (status, title) in sorted(self.alive.items()):
            clean = title.replace("\n", " ").strip()
            lines.append(f"{url} [{status}] {clean}")

        uniq = list(dict.fromkeys(lines))

        with open(self.output_file, "w") as fh:
            fh.write("\n".join(uniq))

        if self.logger.mode != "quiet":
            print(f"[DONE] Saved {len(uniq)} discoveries to {self.output_file}", flush=True)

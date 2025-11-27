import re
from urllib.parse import urljoin

import aiohttp

from core.config import (
    ABS_URL_RE, REL_URL_RE, JSON_RE, PARAM_RE,
    API_HINT_RE, SENSITIVE_RE,
)
from core.config import MAX_JS_FETCH_PER_HOST
from core.utils import construct_url

# Optional JS exec engine
try:
    from py_mini_racer import py_mini_racer
    HAS_JS_EXEC = True
except Exception:
    HAS_JS_EXEC = False


class Scanner:
    """
    Contains ALL scanning/extraction logic:
    - HTML scanning
    - JS scanning
    - API-doc detection
    - Parameter extraction
    - JSON references
    - JS dynamic evaluation (exec mode)
    """

    def __init__(self, jsmode="regex"):
        self.jsmode = jsmode
        self.ctx = py_mini_racer.MiniRacer() if HAS_JS_EXEC and jsmode == "exec" else None

    # ==================================================================
    # HTML & Body parsing
    # ==================================================================

    def extract_urls_from_body(self, base_url: str, body: bytes):
        """
        Extracts script src, relative URLs, inline endpoints, etc.
        """
        discovered = set()

        try:
            html = body.decode("utf-8", "ignore")
        except Exception:
            return discovered

        # script src="..."
        for src in re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.I):
            if src.startswith("//"):
                discovered.add(f"{base_url.split(':')[0]}:{src}")
            elif src.startswith("http"):
                discovered.add(src)
            else:
                discovered.add(urljoin(base_url, src))

        # Inline references like "/api/login"
        for m in re.findall(r'["\'](/[^"\']+)["\']', html):
            discovered.add(urljoin(base_url, m))

        return discovered

    def extract_absolute_refs(self, body: bytes):
        """
        Extract HTTP/HTTPS absolute URLs.
        """
        discovered = set()
        for m in ABS_URL_RE.findall(body):
            try:
                discovered.add(m.decode())
            except:
                continue
        return discovered

    def extract_json_refs(self, base_url: str, body: bytes):
        """
        Extract JSON config references.
        """
        discovered = set()
        for m in JSON_RE.findall(body):
            try:
                path = m.decode()
                if path.startswith("/"):
                    discovered.add(urljoin(base_url, path))
                else:
                    discovered.add(urljoin(base_url, "/" + path))
            except:
                continue
        return discovered

    # ==================================================================
    # JS File Extraction
    # ==================================================================

    def extract_js_links(self, base_url: str, body: bytes, headers):
        """
        Extract external JS file references.
        """

        discovered = set()
        ctype = headers.get("Content-Type", "")

        # HTML content
        if b"<script" in body or "text/html" in ctype:
            try:
                html = body.decode("utf-8", "ignore")
            except:
                return discovered

            for src in re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.I):
                if src.startswith("//"):
                    scheme = base_url.split(":")[0]
                    discovered.add(f"{scheme}:{src}")
                elif src.startswith("http"):
                    discovered.add(src)
                else:
                    discovered.add(urljoin(base_url, src))

        return discovered

    async def fetch_and_scan_js(self, js_url: str, session: aiohttp.ClientSession):
        """
        Fetch JS file and extract endpoints + params.
        Returns: (endpoints_set, params_set)
        """

        endpoints = set()
        params = set()

        try:
            async with session.get(js_url, allow_redirects=True) as resp:
                if resp.status != 200:
                    return endpoints, params
                body = await resp.read()
        except Exception:
            return endpoints, params

        # -------------------------------
        # Regex extraction (default mode)
        # -------------------------------
        endpoints |= self._extract_js_endpoints(body)
        params |= self._extract_js_params(body)

        # -------------------------------
        # JS execution mode (dynamic)
        # -------------------------------
        if self.jsmode == "exec" and self.ctx:
            text = body.decode("utf-8", "ignore")
            dyn = self._execute_js_and_extract(text)
            endpoints |= dyn

        return endpoints, params

    # --------------

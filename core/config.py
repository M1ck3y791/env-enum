# core/config.py

import re

# ----------------------------
# Global configuration
# ----------------------------
CONCURRENCY = 80
REQUEST_TIMEOUT = 10
MAX_JS_FETCH_PER_HOST = 25

# ----------------------------
# Regexes
# ----------------------------
TITLE_RE = re.compile(rb"<title>(.*?)</title>", re.I | re.S)
SCRIPT_SRC_RE = re.compile(r'<script[^>]+src=["\']([^"\']+)["\']', re.I)
ABS_URL_RE = re.compile(rb"https?://[^\s\"'<>]+", re.I)
REL_URL_RE = re.compile(rb"['\"](/[^\"']+?)['\"]")
JSON_RE = re.compile(rb"[A-Za-z0-9_\-\/]+\.json")
PARAM_RE = re.compile(rb"[?&]([a-zA-Z0-9_\-]+)=")
API_HINT_RE = re.compile(rb"(?:/|\\b)(api|v[0-9]+|graphql|openapi|swagger)(?:/|\\b)", re.I)
SENSITIVE_RE = re.compile(rb"(token|secret|apikey|authorization|bearer|jwt)", re.I)

# ----------------------------
# Environment prefixes
# ----------------------------
ENV_PREFIXES = [
    "dev", "stage", "staging", "uat", "qa", "test",
    "beta", "preprod", "preview", "internal", "canary", "sandbox"
] + [f"v{i}" for i in range(1, 11)]

# ----------------------------
# Common paths
# ----------------------------
COMMON_PATHS = [
    "", "api", "api/v1", "api/v2", "v1", "v2", "v3",
    "swagger", "swagger.json", "swagger-ui", "api/docs",
    "openapi", "openapi.json", "docs", "doc",
    "graphql", "graphiql", "health", "status", "debug",
    "admin", "dashboard", "portal", "api-docs"
]

# ----------------------------
# Parameter hints
# ----------------------------
PARAM_HINTS = ["id", "page", "limit", "offset", "token", "auth", "user", "q", "query", "search"]

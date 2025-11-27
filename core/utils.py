# core/utils.py

from urllib.parse import urlparse, urljoin
from pathlib import Path

from core.config import COMMON_PATHS, ENV_PREFIXES

# ----------------------------
# Normalize input host
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

# ----------------------------
# Environment subdomain generator
# ----------------------------
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

# ----------------------------
# Hash-based SPA path variants
# ----------------------------
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

# ----------------------------
# URL constructor
# ----------------------------
def construct_url(scheme: str, host: str, path: str) -> str:
    if path == "" or path == "/":
        return f"{scheme}://{host}"
    if path.startswith("#"):
        if path.startswith("/#"):
            return f"{scheme}://{host}{path}"
        return f"{scheme}://{host}/{path}"
    return f"{scheme}://{host}/{path.lstrip('/')}"

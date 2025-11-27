⭐ env-enum (Legacy – Archived Branch)
⚠ This branch is deprecated and kept only for reference.
👉 The actively maintained and improved version now lives in the modular branch`.
📌 About This Branch

This main branch contains the original monolithic implementation of env-enum, a high‑performance environment enumerator and endpoint discovery toolkit created for:

Penetration testers

Bug bounty hunters

Red teamers

Recon enthusiasts

Since the project grew significantly, the architecture has been fully migrated to a modular, plugin‑based structure that is easier to maintain, extend, and customize.

🔗 For the current version, visit the modular branch:
https://github.com/Learn5ec/env-enum/tree/modular

🏛 Status of This Version

This legacy version remains available for:

Historical reference

Users who want to understand the earlier architecture

Researchers inspecting the initial async recon engine

Backwards compatibility tests

No new features, optimizations, or patches will be applied here.

If you want long-term stability or the latest performance improvements, use the modular branch.

📚 Overview (Legacy Version)

The legacy tool performs asynchronous enumeration of:

Environment‑based subdomains

API and backend endpoints

Swagger/OpenAPI/GraphQL paths

SPA-style /#/hidden routes

JS files for hidden URLs and parameters

Config files & versioned API paths

It uses a monolithic async engine with baked-in logic and no plugin abstraction.

All results are saved to:

env-enum.txt

✨ Key Features (Legacy)
🏗 Environment Subdomain Enumeration

Generates common patterns such as:

dev.example.com
staging.example.com
uat.example.com
beta.api.example.com
v1.example.com

🧪 API Discovery

Detects:

/swagger, /swagger-ui, /api-docs

/openapi.json, /openapi.yaml

/api/v1/, /api/v2/

/graphql

/internal/, /config, /admin

🕸 JavaScript Crawling (Legacy Mode)

Supports:

Mode	Description
regex	Lightweight text-based extraction
exec	JS evaluation using py-mini-racer
⚡ Async Recon Engine

High-speed aiohttp-based enumeration.

📦 Installation (Legacy)
git clone https://github.com/Learn5ec/env-enum
cd env-enum
git checkout main   # legacy
python3 -m venv here
source here/bin/activate
pip3 install aiohttp py-mini-racer


If JS execution is not required:

pip3 install aiohttp

⚙ Usage (Legacy)
python3 env-enum.py input.txt


Modes:

--mode debug
--mode verbose
--mode discovery
--mode quiet


JS modes:

--jsmode regex
--jsmode exec


Set concurrency:

--concurrency 100

🚩 Flags (Legacy)
Logging Modes
Flag	Description
--mode debug	Full logs
--mode verbose	Info + discoveries
--mode discovery	Default minimal logs
--mode quiet	Silence console output
JS Parsing Modes
Flag	Description
--jsmode regex	Regex-based extraction
--jsmode exec	Executes JS payloads (slower)
Performance
Flag	Description
--concurrency N	Number of async workers
📝 Input Format
example.com
api.example.com
https://portal.company.in
sub.domain.org


Protocols are auto-normalized.

📤 Output Format
[DISCOVERY] https://dev.example.com/api/v1/login [200]
[JS-ENDPOINT] /internal/config
[API-DOC] https://app.example.com/swagger.json
[PARAM] token


Backup file is created:

env-enum.txt.bak

📌 Example Commands
python3 env-enum.py targets.txt --mode debug --jsmode exec --concurrency 100
python3 env-enum.py targets.txt --mode discovery --concurrency 150
python3 env-enum.py targets.txt --jsmode regex
python3 env-enum.py targets.txt --mode quiet

🤝 Contributions

Contributions should target the modular branch, not this one.

Please go here for active development:

➡ https://github.com/Learn5ec/env-enum/tree/modular

📜 License

MIT License

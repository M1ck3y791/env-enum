# ⚡ env-enum (Modular Edition)
### **Next-Gen Environment Enumerator & Endpoint Discovery Toolkit**

```
███████╗███╗   ██╗██╗      ██╗      ███████╗███╗   ██╗██╗   ██╗███╗     ███║
██╔════╝████╗  ██║╚██╗    ██╔╝      ██╔════╝████╗  ██║██║   ██║████╗   ████║
█████╗  ██╔██╗ ██║ ╚██   ██╔╝       █████╗  ██╔██╗ ██║██║   ██║██ ██╗ ██ ██║
██╔══╝  ██║╚██╗██║  ╚██ ██╔╝        ██╔══╝  ██║╚██╗██║██╚═══██║██╔═███╔═╗██║
███████╗██║ ╚████║   ╚███╔╝         ███████╗██║ ╚████║████████║██║ ╚══╝ ║██║
╚══════╝╚═╝  ╚═══╝    ╚══╝          ╚══════╝╚═╝  ╚═══╝╚═══════╝╚═╝      ╚══╝

             Modular Environment Enumerator & API/JS Recon Engine
```

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-yellow?style=flat-square" />
  <img src="https://img.shields.io/badge/Architecture-Modular-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/Async-AIOHTTP-green?style=flat-square" />
  <img src="https://img.shields.io/badge/JS_Analysis-Regex%2FExec-purple?style=flat-square" />
  <img src="https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square" />
</p>

---

> ⚙️ **Welcome to the Modular Edition of env-enum!**  
> This version introduces a *plugin-ready architecture*, faster async engine, cleaner scanning layers, and highly extensible structure.  
>
> 🔥 **Awesome plugins coming soon!**

---

## 📚 Table of Contents
- [🚀 Introduction](#-introduction)
- [🏗 Modular Architecture](#-modular-architecture)
- [✨ Key Features](#-key-features)
- [📦 Installation](#-installation)
- [⚙ Usage](#-usage)
- [📁 Sample Input File](#-sample-input-file-example-inputtxt)
- [🧩 Plugins](#-plugins)
- [📌 Example Commands](#-example-commands)
- [🛠 Future Improvements](#-future-improvements-ultra-compact)
- [🤝 Contributions](#-contributions)
- [📜 License](#-license)

---

## 🚀 Introduction

The **modular edition** is a complete rewrite focused on:

- Clean separation between engine, scanner, and config  
- High-performance asynchronous recon  
- Plugin architecture for future expansion  
- Better JS crawling and dynamic string evaluation  
- More realistic environment subdomain logic  

This is the recommended version for **pentesters, bug hunters, red-teamers, and recon automation engineers**.

---

## 🏗 Modular Architecture

```
env-enum/
│── cli.py          → CLI argument parsing
│── main.py         → PyPI entrypoint
│── engine.py       → Async crawling engine
│── scanner.py      → JS/HTML/API-doc analyzers
│── core/
│    ├── config.py  → Regexes, constants, env prefixes
│    ├── utils.py   → Normalizers, SPA paths, builders
│    └── logger.py  → Multi-level logging
│── plugins/        → 🔥 (Coming Soon) Drop-in scanner plugins
│── pyproject.toml
└── requirements.txt
```

---

## ✨ Key Features

### ⚡ High-Speed Async Recon
- `aiohttp` powered  
- Controlled concurrency  
- Recursive crawling with smart deduplication  

### 🏗 Environment Subdomain Expansion  
Automatically generates dozens of permutations such as:

```
dev.example.com
qa-api.example.com
stage-admin.example.com
preview.app.example.com
v1.example.com
sandbox.example.com
```

### 🕸 JavaScript & JSON Deep Scanning  
- Regex-based JS endpoint detection  
- Optional JS evaluation via **py-mini-racer**  
- Sensitive token pattern recognition  
- JSON config path extraction  

### 🔍 API Documentation Discovery  
Detects:

- `swagger.json`
- `openapi.json`
- `/graphql`
- `/api-docs`
- `/docs`

---

## 📦 Installation

```bash
git clone -b modular https://github.com/Learn5ec/env-enum.git
cd env-enum
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

---

## ⚙ Usage

```bash
python3 main.py input.txt
```

Optional flags:

```
--mode debug|verbose|discovery|quiet
--jsmode regex|exec
--concurrency 150
```

---

# 📁 Sample Input File Example (input.txt)

```
example.com
api.example.com
https://portal.company.in
sub.project.internal
http://staging.company.io
www.saasproduct.xyz
demo.clientapp.org
login.partner.io
```

---

## ✔ Supported Formats

### **Bare domains**
```
example.com
target.xyz
company.in
```

### **Subdomains**
```
api.example.com
dev.company.io
portal.app.xyz
```

### **Full URLs (HTTP/HTTPS)**
```
https://app.example.com
http://legacy.company.in/login
```

### **Additional Accepted Styles**
- Mixed URLs + domains  
- Any number of lines  
- Comments (future feature)

---

## ✔ Auto-normalization

Automatically handles:

- Removing protocols  
- Stripping ports  
- Cleaning `user@host` patterns  
- Handling `www.` prefixes  
- Internal deduplication  

---

## ❌ Not recommended (but accepted gracefully)

- IP addresses (JS crawling makes them slow)  
- Localhost entries  
- Invalid TLDs / junk lines  

---

## 🧩 Plugins

> ⚡ **Plugins are first-class citizens in this version.**  
> Add your own scanners in the `plugins/` directory.

**Coming Soon:**
- Passive DNS  
- Cloud metadata probe  
- Param brute-force plugin  
- GraphQL introspection  

---

## 📌 Example Commands

```bash
python3 main.py scope.txt --mode debug --jsmode exec --concurrency 150
```

```bash
python3 main.py scope.txt --mode discovery
```

```bash
python3 main.py scope.txt --jsmode regex
```

```bash
python3 main.py scope.txt --mode quiet
```

---

## 🛠 Future Improvements (Ultra-Compact)

- Reduce false positives (blank 200s, login redirects, disguised errors)  
- Smarter subdomain logic (pattern re-use, skip redundant tests)  
- Basic auth probing (common creds, login form detection)  
- Arjun integration (auto param merging)  
- ffuf enhancement (cookies, tokens, POST bodies, cleaner output)  
- Performance boosts (async pools, caching, pruning)  
- QoL features (screenshots, retries, framework fingerprinting)

🔥 **And a full plugin ecosystem!**

---

## 🤝 Contributions

PRs welcome!  
Please contribute:

- Plugins  
- Performance improvements  
- JS extraction logic  
- Regex signatures  

---

## 📜 License

MIT License — free for personal & commercial use.

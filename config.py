#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configuration for Human-in-the-Loop Pipeline"""
import os
from pathlib import Path

from dotenv import load_dotenv  


load_dotenv()

# === 🔑 LLM Configuration ===
# Mặc định ưu tiên Gemini 2.5 Pro
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google/gemini-2.5-pro-exp")

# Google Gemini API key
LLM_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

# OpenAI fallback
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# === 🌐 Browser Configuration ===
BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "true").lower() == "true"
BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "30000"))
USE_JS_TABS = os.getenv("USE_JS_TABS", "true").lower() == "true"

# === 📁 File Paths ===
DATA_DIR = Path("data")
COOKIES_PATH = DATA_DIR / "cookies.json"
AUDIT_RESULTS_DIR = DATA_DIR / "audit_results"

# === ⚙️ Processing Configuration ===
DEFAULT_BATCH_LIMIT = int(os.getenv("BATCH_LIMIT", "10"))
ENABLE_CACHE = os.getenv("ENABLE_CACHE", "true").lower() == "true"

# === 🧾 Logging ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

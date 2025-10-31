# 🗂️ PROJECT RESTRUCTURE PLAN

## 📁 Cấu trúc mới có logic:

```
thuvienphapluat-crawler/
├── core/                           # Core functionality
│   ├── extractors/                 # Formula extractors
│   │   ├── __init__.py
│   │   ├── production_extractor.py # Main extractor (từ production_ready_extractor.py)
│   │   └── llm_extractor.py        # LLM backup extractor
│   ├── patterns/                   # Regex patterns
│   │   ├── __init__.py
│   │   └── regex_patterns.py       # 29 patterns (từ enhanced_regex_patterns.py)
│   ├── filters/                    # Pre-filtering
│   │   ├── __init__.py
│   │   └── document_filter.py      # Document filtering
│   └── __init__.py
├── scripts/                        # Executable scripts
│   ├── crawl/                      # Crawling scripts
│   │   ├── crawl_formulas.py       # Main crawl script (từ crawl_formulas_fast.py)
│   │   ├── crawl_links.py          # Link crawling
│   │   └── crawl_data.py           # Data crawling
│   ├── test/                       # Test scripts
│   │   ├── test_extractor.py       # Test extractors
│   │   └── test_patterns.py        # Test patterns
│   └── utils/                      # Utility scripts
│       ├── setup_db.py             # Database setup
│       └── backup_data.py          # Data backup
├── data/                           # Data storage
│   ├── results/                    # Extraction results
│   ├── screenshots/                # Screenshots
│   └── downloads/                  # Downloaded files
├── sql/                            # Database scripts
├── api/                            # API service
├── docs/                           # Documentation
│   ├── README.md                   # Main documentation
│   ├── USAGE.md                    # Usage guide
│   └── API.md                      # API documentation
├── .env                            # Environment config
├── requirements.txt                # Dependencies
└── main.py                         # Entry point
```

## 🎯 Files cần di chuyển:

### Core Components:
- `production_ready_extractor.py` → `core/extractors/production_extractor.py`
- `enhanced_regex_patterns.py` → `core/patterns/regex_patterns.py`
- `smart_formula_separator.py` → `core/extractors/formula_separator.py`

### Scripts:
- `crawl_formulas_fast.py` → `scripts/crawl/crawl_formulas.py`
- `setup_database.py` → `scripts/utils/setup_db.py`

### Documentation:
- `README.md` → `docs/README.md`
- `FORMULA_EXTRACTION_REPORT.md` → `docs/EXTRACTION_GUIDE.md`

## 🗑️ Files cần xóa (duplicate/obsolete):
- `formula_extraction/` folder (duplicate functionality)
- `test_*.py` files (consolidate into scripts/test/)
- `debug_*.py` files (move to scripts/utils/)
- Old extractor files (keep only production_ready_extractor.py)

## 📝 Entry point mới:

```python
# main.py
from core.extractors.production_extractor import ProductionReadyExtractor

def main():
    extractor = ProductionReadyExtractor()
    # Main logic here

if __name__ == "__main__":
    main()
```

## 🚀 Benefits:
- ✅ Clear separation of concerns
- ✅ Easy to find and maintain
- ✅ Scalable architecture
- ✅ Professional structure
- ✅ Remove duplicate files
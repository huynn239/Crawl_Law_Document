# 📁 Cấu trúc Project Mới

```
thuvienphapluat-crawler/
├── api/                          # API endpoints
│   ├── main.py
│   └── crawler_api.py
│
├── core/                         # Core logic
│   ├── extractors/
│   ├── filters/
│   └── patterns/
│
├── tvpl_crawler/                 # Main crawler package
│   ├── __main__.py
│   ├── config.py
│   ├── db.py
│   ├── parser.py
│   └── storage.py
│
├── scripts/                      # Utility scripts
│   ├── crawl/                   # Crawling scripts
│   │   ├── crawl_*.py
│   │   └── quick_crawl.py
│   ├── extract/                 # Extraction scripts
│   │   ├── *_extractor.py
│   │   └── formula_*.py
│   ├── test/                    # Test scripts
│   │   ├── test_*.py
│   │   └── debug_*.py
│   ├── migration/               # DB migration
│   │   ├── migrate_*.py
│   │   └── import_*.py
│   ├── utils/                   # Utilities
│   │   ├── setup_*.py
│   │   └── cleanup_*.py
│   └── analysis/                # Analysis tools
│       ├── audit_*.py
│       └── gap_analyzer.py
│
├── sql/                         # SQL files
│   ├── migration_step_by_step.sql
│   ├── current_schema.sql
│   └── *.sql
│
├── docs/                        # Documentation
│   ├── README.md
│   ├── QUICKSTART.md
│   ├── SQL_QUERIES_CHEATSHEET.md
│   ├── SCHEMA_MIGRATION_GUIDE.md
│   └── *.md
│
├── config/                      # Configuration
│   ├── n8n/                    # N8N workflows
│   │   ├── n8n_*.json
│   │   └── n8n_*.md
│   └── .env files
│
├── data/                        # Data files
│   ├── audit_results/
│   ├── backups/
│   ├── downloads/
│   └── screenshots/
│
├── archive/                     # Old/unused files
│   ├── old_tests/
│   └── debug/
│
├── .env                         # Environment config
├── requirements.txt             # Dependencies
└── main.py                      # Entry point
```

## Chạy Restructure

```bash
python restructure_project.py
```

## Files Quan Trọng

### Core Files (Giữ nguyên ở root)
- `main.py` - Entry point
- `config.py` - Config chính
- `requirements.txt` - Dependencies
- `.env` - Environment variables

### Folders Chính
- **`api/`** - API endpoints
- **`core/`** - Business logic
- **`tvpl_crawler/`** - Main crawler
- **`scripts/`** - Utility scripts (chia nhỏ theo chức năng)
- **`sql/`** - Tất cả SQL files
- **`docs/`** - Tất cả documentation
- **`data/`** - Data files (giữ nguyên)
- **`archive/`** - Files cũ/không dùng

## Sau Khi Restructure

1. Update imports trong code
2. Test lại các scripts
3. Xóa folder `archive/` nếu không cần

# 🔧 Các Bước Restructure Project

## Bước 1: Backup
```bash
# Tạo backup trước khi restructure
git add .
git commit -m "Before restructure"
# Hoặc copy toàn bộ folder
```

## Bước 2: Chạy Restructure
```bash
python restructure_project.py
```

Kết quả:
- SQL files → `sql/`
- Docs → `docs/`
- Test scripts → `scripts/test/`
- Crawl scripts → `scripts/crawl/`
- Extractors → `scripts/extract/`
- Migration → `scripts/migration/`
- Utils → `scripts/utils/`

## Bước 3: Fix Imports
```bash
python fix_imports_after_restructure.py
```

Script sẽ tự động sửa:
- `from crawl_xxx import` → `from scripts.crawl.crawl_xxx import`
- `from test_xxx import` → `from scripts.test.test_xxx import`
- `from xxx_extractor import` → `from scripts.extract.xxx_extractor import`

## Bước 4: Test
```bash
# Test import core modules
python -c "from core.extractors.production_extractor import ProductionReadyExtractor; print('OK')"

# Test import tvpl_crawler
python -c "from tvpl_crawler.config import Config; print('OK')"

# Test main entry
python main.py --help
```

## Bước 5: Manual Fixes (nếu cần)

### Files cần check thủ công:
1. **`__init__.py`** files - có thể cần update imports
2. **`main.py`** - entry point
3. **`api/main.py`** - API endpoints
4. **`tvpl_crawler/__main__.py`** - package entry

### Common Issues:

**Issue 1: ModuleNotFoundError**
```python
# Trước
from crawl_data_fast import crawl

# Sau
from scripts.crawl.crawl_data_fast import crawl
```

**Issue 2: Relative imports**
```python
# Trong scripts/crawl/xxx.py
# Trước
from utils.setup_db import setup

# Sau
from scripts.utils.setup_db import setup
```

**Issue 3: Config imports**
```python
# Config ở root nên giữ nguyên
from config import Config  # ✓ OK
```

## Bước 6: Update Documentation
- Update README.md với cấu trúc mới
- Update QUICKSTART.md với paths mới

## Rollback (nếu cần)
```bash
git reset --hard HEAD
# Hoặc restore từ backup
```

## Cấu Trúc Cuối Cùng

```
thuvienphapluat-crawler/
├── api/                    # Giữ nguyên
├── core/                   # Giữ nguyên
├── tvpl_crawler/          # Giữ nguyên
├── scripts/               # MỚI - chứa utility scripts
│   ├── crawl/
│   ├── extract/
│   ├── test/
│   ├── migration/
│   ├── utils/
│   └── analysis/
├── sql/                   # MỚI - chứa SQL files
├── docs/                  # MỚI - chứa documentation
├── config/                # MỚI - chứa config files
├── data/                  # Giữ nguyên
├── archive/               # MỚI - files cũ
├── main.py               # Giữ nguyên
├── config.py             # Giữ nguyên
└── requirements.txt      # Giữ nguyên
```

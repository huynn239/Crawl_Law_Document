# Cải thiện Formula Extraction

## Vấn đề trước đây
- Regex patterns quá rộng, bắt cả HTML fragments
- Kết quả chứa nhiều artifacts như `<div>`, `href`, `aspx`
- Không phân biệt được công thức thực sự vs HTML code

## Cải thiện đã thực hiện

### 1. Regex Patterns mới (chính xác hơn)
```python
patterns = [
    # Công thức có dấu = với số tiền cụ thể
    r'([A-Za-zÀ-ỹ\s]{5,50})\s*=\s*([\d.,]+(?:\s*(?:đồng|VNĐ|%))?)(?:\s*/\s*[A-Za-zÀ-ỹ]+)?',
    
    # Công thức tính % rõ ràng
    r'([\d.,]+)\s*%\s*(?:của|×|\*)\s*([\d.,]+(?:\s*(?:đồng|VNĐ))?)',
    
    # Công thức có phép tính + - × /
    r'([A-Za-zÀ-ỹ\s]{5,40})\s*=\s*([\d.,]+)\s*([+\-×*/])\s*([\d.,]+)(?:\s*(?:đồng|VNĐ|%))?',
    
    # Mức/Tỷ lệ với số cụ thể
    r'((?:mức|tỷ\s*lệ)\s*[^:]{5,40}):\s*([\d.,]+\s*(?:%|đồng|VNĐ))',
    
    # Công thức tính lương/phụ cấp
    r'((?:lương|phụ\s*cấp|trợ\s*cấp|thuế|phí)\s*[^=]{5,40})\s*=\s*([\d.,]+(?:\s*[+\-×*/]\s*[\d.,]+)*(?:\s*(?:đồng|VNĐ|%))?)',
    
    # Công thức có từ "tính" hoặc "bằng"
    r'(tính|bằng)\s*([^.]{10,80}(?:[\d.,]+(?:\s*[+\-×*/]\s*[\d.,]+)*(?:\s*(?:đồng|VNĐ|%))))',
]
```

### 2. HTML Cleaning
- Loại bỏ tất cả HTML tags trước khi áp dụng regex
- Chuẩn hóa whitespace

### 3. Advanced Filtering
```python
# Filter out HTML artifacts and invalid formulas
if (len(formula_text) > 15 and len(formula_text) < 300 and
    not any(x in formula_text.lower() for x in ['<', '>', 'href', 'class', 'style', 'div', 'span', 'aspx', 'listidlaw', 'javascript', 'function', 'var ', 'document']) and
    any(char.isdigit() for char in formula_text) and
    ('=' in formula_text or '%' in formula_text or any(op in formula_text for op in ['+', '-', '×', '*', '/'])) and
    any(word in formula_text.lower() for word in ['lương', 'phụ cấp', 'thuế', 'phí', 'tiền', 'mức', 'tỷ lệ', 'tính', 'bằng', 'đồng', 'vnd', '%'])):
```

### 4. Deduplication
- Loại bỏ công thức trùng lặp
- Giới hạn tối đa 20 công thức/document

## Kết quả cải thiện

### Trước đây:
```json
{
  "name": "Công thức 1",
  "formula": "ản gốc</a>, <a href=\"#\" class=\"info-green-light\">Văn bản tiếng Anh</a>,",
  "description": "Được tìm thấy bằng pattern 1"
}
```

### Sau cải thiện:
```json
{
  "name": "Công thức 1",
  "formula": "Mức lương cơ bản = 1.800.000 đồng/tháng",
  "description": "Công thức tính toán (pattern 1)"
}
```

## Files đã cập nhật
1. `tvpl_crawler/formula_extractor.py` - Core extraction logic
2. `crawl_formulas_simple.py` - Standalone crawler không cần crawl4ai
3. `test_formula_simple.py` - Test script

## Cách sử dụng

### Option 1: Standalone script (khuyến nghị)
```bash
python crawl_formulas_simple.py data/links.json data/formulas.json
```

### Option 2: Qua API
```bash
curl -X POST http://localhost:8000/extract-formulas \
  -H "Content-Type: application/json" \
  -d '{"links": ["https://..."], "method": "playwright"}'
```

## Test Results
- ✅ Loại bỏ hoàn toàn HTML artifacts
- ✅ Chỉ bắt công thức toán học thực sự
- ✅ Hỗ trợ tiếng Việt (lương, phụ cấp, thuế, phí...)
- ✅ Nhận diện các phép tính (+, -, ×, /, %)
- ✅ Xử lý đơn vị tiền tệ (đồng, VNĐ)
- ✅ Deduplication và giới hạn kết quả
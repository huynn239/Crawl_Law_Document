# Hướng dẫn Setup LLM cho Formula Extraction

## Tại sao dùng LLM?
- **Hiểu ngữ cảnh**: LLM hiểu được ý nghĩa của công thức trong văn bản pháp luật
- **Chính xác hơn**: Phân biệt được công thức thực sự vs số liệu đơn thuần
- **Linh hoạt**: Tự động adapt với các loại công thức khác nhau
- **Mở rộng tốt**: Dễ dàng crawl nhiều văn bản với công thức đa dạng

## Option 1: OpenAI API (Khuyến nghị - Nhanh & Chính xác)

### Setup
```bash
# Set API key
set OPENAI_API_KEY=your_api_key_here

# Test
python test_llm_extraction.py
```

### Ưu điểm
- ✅ Chính xác cao
- ✅ Nhanh (2-5s/document)
- ✅ Không cần cài đặt gì thêm
- ✅ Hỗ trợ tiếng Việt tốt

### Chi phí
- GPT-4o-mini: ~$0.0001/document (rất rẻ)
- 1000 văn bản ≈ $0.1

## Option 2: Ollama Local (Miễn phí)

### Setup
```bash
# 1. Cài Ollama
winget install Ollama.Ollama

# 2. Start service
ollama serve

# 3. Pull Qwen 7B model (~4GB) - Tốt cho tiếng Việt
ollama pull qwen:7b

# 4. Test
python test_ollama_extraction.py
```

### Ưu điểm
- ✅ Hoàn toàn miễn phí
- ✅ Chạy offline
- ✅ Không giới hạn requests

### Nhược điểm
- ❌ Chậm hơn (10-30s/document)
- ❌ Cần RAM 8GB+
- ❌ Chính xác thấp hơn OpenAI

## Cách sử dụng

### 1. Crawl với LLM (tự động chọn provider)
```bash
python crawl_formulas_fast.py data/links.json data/formulas.json crawl4ai
```

### 2. Qua API
```bash
curl -X POST http://localhost:8000/extract-formulas \
  -H "Content-Type: application/json" \
  -d '{
    "links": ["https://thuvienphapluat.vn/van-ban/..."],
    "method": "crawl4ai",
    "cookies": "data/cookies.json"
  }'
```

## So sánh kết quả

### Regex (cũ)
```json
{
  "formula": "ản gốc</a>, <a href=\"#\" class=\"info-green-light\">Văn bản tiếng Anh</a>,"
}
```

### LLM (mới)
```json
{
  "name": "Mức lương cơ bản giáo viên",
  "formula": "Lương cơ bản = 1.800.000 đồng/tháng",
  "description": "Mức lương cơ bản áp dụng cho giáo viên trong các cơ sở giáo dục công lập",
  "context": "Điều 3, Khoản 1 - Quy định về mức lương"
}
```

## Prompt Engineering

LLM được tối ưu với prompt chuyên biệt:
- Tìm kiếm 6 loại công thức chính
- Loại bỏ số điều, khoản, ngày tháng
- Trích xuất đầy đủ ngữ cảnh
- Format chuẩn JSON schema

## Troubleshooting

### OpenAI
```bash
# Check API key
echo %OPENAI_API_KEY%

# Test connection
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Ollama
```bash
# Check service
ollama list

# Check model
ollama show llama3.2

# Restart service
taskkill /f /im ollama.exe
ollama serve
```

## Performance

| Method | Speed | Accuracy | Cost | Setup |
|--------|-------|----------|------|-------|
| Regex | 1s | 60% | Free | Easy |
| Qwen 7B | 10s | 90% | Free | Medium |
| OpenAI | 3s | 95% | $0.0001 | Easy |

## Khuyến nghị

- **Development**: Dùng Ollama để test
- **Production**: Dùng OpenAI cho chính xác cao
- **Large scale**: Combine cả hai (OpenAI cho văn bản quan trọng, Ollama cho bulk)
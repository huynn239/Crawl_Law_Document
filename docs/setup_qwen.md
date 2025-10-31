# Setup Qwen 7B cho Formula Extraction

## Cài đặt Ollama và Qwen 7B

### 1. Cài Ollama
```bash
# Download từ https://ollama.com/download/windows
# Hoặc dùng winget
winget install Ollama.Ollama
```

### 2. Start Ollama service
```bash
ollama serve
```

### 3. Pull Qwen 7B model (~4GB)
```bash
ollama pull qwen:7b
```

### 4. Test model
```bash
ollama run qwen:7b "Xin chào, bạn có thể phân tích văn bản tiếng Việt không?"
```

## Tại sao chọn Qwen 7B?

- ✅ **Tiếng Việt xuất sắc**: Được train đặc biệt cho các ngôn ngữ châu Á
- ✅ **Hiểu ngữ cảnh pháp luật**: Tốt với văn bản chính thức, kỹ thuật
- ✅ **Kích thước hợp lý**: 7B parameters, cần ~8GB RAM
- ✅ **Nhanh**: Nhanh hơn các model 13B+
- ✅ **Chính xác**: Đặc biệt tốt cho extraction tasks

## Test Formula Extraction

```bash
# Test với Qwen 7B
python test_ollama_extraction.py

# Crawl với Qwen 7B
python crawl_formulas_fast.py data/links.json data/formulas.json crawl4ai
```

## So sánh Models

| Model | Size | RAM | Speed | Tiếng Việt | Accuracy |
|-------|------|-----|-------|------------|----------|
| llama3.2 | 3B | 4GB | Fast | Good | 75% |
| qwen:7b | 7B | 8GB | Medium | Excellent | 90% |
| qwen:14b | 14B | 16GB | Slow | Excellent | 95% |

## Prompt tối ưu cho Qwen

Qwen hiểu tốt prompt tiếng Việt:

```
Phân tích văn bản pháp luật và trích xuất các công thức tính toán:

1. Công thức lương, phụ cấp (VD: Lương = 1.800.000 đồng)
2. Công thức thuế, phí (VD: Thuế = 10% × thu nhập)  
3. Công thức phạt (VD: Phạt = 500.000 + 2% × giá trị)
4. Tỷ lệ phần trăm (VD: BHXH: 8%)
5. Mức quy định (VD: Tối thiểu: 1.800.000 đồng)

Trả về JSON với: name, formula, description, context
```

## Troubleshooting

### Ollama không start
```bash
# Check process
tasklist | findstr ollama

# Kill và restart
taskkill /f /im ollama.exe
ollama serve
```

### Model không load
```bash
# Check available models
ollama list

# Re-pull if needed
ollama pull qwen:7b

# Check model info
ollama show qwen:7b
```

### RAM không đủ
```bash
# Dùng model nhỏ hơn
ollama pull qwen:1.8b

# Hoặc quantized version
ollama pull qwen:7b-q4_0
```

## Performance Tips

1. **Warm-up model**: Chạy 1 request đầu để load model vào RAM
2. **Batch processing**: Xử lý nhiều văn bản cùng lúc
3. **Keep-alive**: Set timeout cao để model không bị unload
4. **GPU acceleration**: Nếu có NVIDIA GPU, Ollama sẽ tự động dùng

## Expected Results

Với Qwen 7B, bạn sẽ có kết quả như:

```json
{
  "name": "Mức lương cơ bản giáo viên",
  "formula": "Lương cơ bản = 1.800.000 đồng/tháng",
  "description": "Mức lương cơ bản áp dụng cho giáo viên tiểu học trong các cơ sở giáo dục công lập",
  "context": "Điều 5, Khoản 1 - Quy định về chế độ trả lương"
}
```
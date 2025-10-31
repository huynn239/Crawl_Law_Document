# 🔄 HUMAN-IN-THE-LOOP PIPELINE - Quy trình cải tiến Regex

## 🎯 Mục tiêu
Xây dựng bộ Regex ngày càng mạnh mẽ bằng cách sử dụng LLM (Gemini) như "người thầy" để chỉ ra điểm yếu, con người học hỏi và cải tiến patterns.

## 📋 Quy trình chi tiết

### 🌟 **BƯỚC 0: Pre-screening Filter (Chỉ khi >100 văn bản)**
```
Input: Batch 1000+ văn bản
    ↓
┌─────────────────────┐
│   Layer 0: Filter   │
│ (Regex siêu nhanh)  │
│                     │
│ - Check dấu hiệu:   │
│   (=, ×, /, %)      │
│ - Trả lời: Yes/No   │
└─────────────────────┘
    ↓ (Chỉ Yes)
Output: ~50 văn bản có khả năng chứa công thức
```
**⚠️ Lưu ý: Với 10-20 văn bản test → BỎ QUA bước này**

### 🔄 **BƯỚC 1: Audit Mode - Chạy song song**
```
Input: Batch 10-20 văn bản test (hoặc ~50 văn bản đã qua lọc)
    ↓
┌─────────────────────┐    ┌─────────────────────┐
│   Hệ thống A        │    │   Hệ thống B        │
│ (Regex Only)        │    │ (LLM Only)          │
│                     │    │                     │
│ ProductionReady     │    │ Crawl4AI + Gemini  │
│ Extractor           │    │ 2.5 Pro             │
│                     │    │                     │
│ 25+ patterns        │    │ Pure AI extraction  │
└─────────────────────┘    └─────────────────────┘
    ↓                          ↓
result_regex.json         result_llm.json
```

### 🕵️ **BƯỚC 2: Gap Analysis - Phân tích khác biệt**
```
┌─────────────────────┐
│  Comparison Script  │
│                     │
│ Compare results:    │
│ - Regex found: A    │
│ - LLM found: B      │
│ - Missing: B - A    │
│ - False positive: A-B│
└─────────────────────┘
    ↓
gap_analysis.json
```

### 🧑‍💻 **BƯỚC 3: Human Learning - Con người cải tiến**
```
┌─────────────────────┐
│ Manual Review       │
│                     │
│ 1. Xem công thức    │
│    bị bỏ lỡ         │
│ 2. Phân tích cấu    │
│    trúc mới         │
│ 3. Viết pattern     │
│    Regex mới        │
│ 4. Test pattern     │
└─────────────────────┘
    ↓
enhanced_patterns_v2.py
```

### 🔁 **BƯỚC 4: Iteration - Lặp lại**
```
┌─────────────────────┐
│ Re-run with new     │
│ patterns            │
│                     │
│ Measure improvement:│
│ - Gap reduction %   │
│ - New accuracy      │
│ - Pattern coverage  │
└─────────────────────┘
```

## 🛠️ Implementation Plan

### **Phase 1: Setup Dual Systems**

#### 1.1 Hệ thống A (Regex Only)
```python
# File: regex_only_extractor.py
class RegexOnlyExtractor:
    def extract_from_url(self, url: str) -> Dict:
        # Chỉ dùng ProductionReadyExtractor
        # Không gọi LLM
        pass
```

#### 1.2 Hệ thống B (LLM Only) 
```python
# File: llm_only_extractor.py  
class LLMOnlyExtractor:
    def extract_from_url(self, url: str) -> Dict:
        # Chỉ dùng Crawl4AI + Gemini 2.5 Pro
        # Không dùng Regex patterns
        pass
```

#### 1.3 Batch Runner
```python
# File: audit_mode_runner.py
class AuditModeRunner:
    def run_batch(self, urls: List[str]):
        for url in urls:
            regex_result = regex_extractor.extract(url)
            llm_result = llm_extractor.extract(url)
            
            save_results(url, regex_result, llm_result)
```

### **Phase 2: Gap Analysis Tools**

#### 2.1 Comparison Script
```python
# File: gap_analyzer.py
class GapAnalyzer:
    def compare_results(self, regex_results, llm_results):
        # So sánh formulas tìm được
        # Tìm missing patterns
        # Tạo báo cáo chi tiết
        pass
```

#### 2.2 Pattern Suggester
```python
# File: pattern_suggester.py
class PatternSuggester:
    def suggest_patterns(self, missed_formulas):
        # Phân tích cấu trúc công thức bị lỡ
        # Đề xuất regex patterns mới
        pass
```

### **Phase 3: Human Review Interface**

#### 3.1 Review Dashboard
```python
# File: review_dashboard.py
# Web interface để review missed formulas
# Cho phép con người viết patterns mới
```

#### 3.2 Pattern Tester
```python
# File: pattern_tester.py
class PatternTester:
    def test_new_pattern(self, pattern, test_cases):
        # Test pattern mới với các trường hợp cụ thể
        pass
```

## 📊 Metrics & Tracking

### **Key Performance Indicators**
```
1. Gap Reduction Rate
   - Iteration 1: LLM finds 50 formulas, Regex finds 30 → Gap: 20
   - Iteration 2: LLM finds 50 formulas, Regex finds 45 → Gap: 5
   - Improvement: 75% gap reduction

2. Pattern Coverage
   - Total patterns: 25 → 35 → 50
   - Coverage increase per iteration

3. Accuracy Metrics
   - Precision: True positives / (True + False positives)
   - Recall: True positives / (True + False negatives)
   - F1 Score: Harmonic mean of precision & recall
```

### **Progress Tracking**
```json
{
  "iteration": 3,
  "date": "2025-01-15",
  "batch_size": 200,
  "results": {
    "regex_formulas": 180,
    "llm_formulas": 195,
    "gap": 15,
    "gap_reduction": "85%",
    "new_patterns_added": 8,
    "total_patterns": 33
  }
}
```

## 🎯 Expected Outcomes

### **Short Term (1-2 iterations)**
- Gap reduction: 50-70%
- Pattern count: 25 → 40
- Regex accuracy: 70% → 85%

### **Medium Term (3-5 iterations)**  
- Gap reduction: 80-90%
- Pattern count: 40 → 60
- Regex accuracy: 85% → 95%

### **Long Term (6+ iterations)**
- Gap reduction: 95%+
- Regex handles 95% of cases
- LLM only needed for edge cases
- Cost reduction: 80% (less LLM calls)

## 🚀 Implementation Steps

### **Phase 0: Pre-screening (Chỉ khi scale lên)**
```python
# File: pre_screening_filter.py
class PreScreeningFilter:
    def __init__(self):
        self.pattern = re.compile(r"(?i)(=|×|/|%|công thức|tính bằng|tỷ lệ)", re.IGNORECASE)
    
    def has_formula_signs(self, text: str) -> bool:
        return bool(self.pattern.search(text)) if text else False
```

### **Week 1: Setup (10-20 văn bản test)**
1. Create `RegexOnlyExtractor`
2. Create `LLMOnlyExtractor` 
3. Create `AuditModeRunner`
4. Test with 10-20 documents (BỎ QUA Layer 0)

### **Week 2: First Analysis**
1. Run audit mode on 10-20 documents
2. Generate gap analysis
3. Manual review of ALL missed formulas
4. Create 3-5 new patterns

### **Week 3: Iteration 1**
1. Update patterns
2. Re-run batch
3. Measure improvement
4. Document learnings

### **Week 4+: Continuous Improvement**
1. Weekly batch runs
2. Pattern refinement
3. Accuracy tracking
4. Cost optimization

---

## 📋 Action Items

### **Immediate (Next 2 days) - Test Scale**
- [ ] Create `RegexOnlyExtractor` class
- [ ] Create `LLMOnlyExtractor` class  
- [ ] Setup basic comparison logic
- [ ] Test with 10-20 documents (SKIP Layer 0)

### **This Week**
- [ ] Implement `AuditModeRunner`
- [ ] Create gap analysis tools
- [ ] Run first test batch (10-20 docs)
- [ ] Manual review of ALL gaps

### **Next Week**
- [ ] Create 3-5 new patterns
- [ ] Re-test improved regex
- [ ] Measure gap reduction

### **Future Scaling (>100 docs)**
- [ ] Implement `PreScreeningFilter` (Layer 0)
- [ ] Scale to larger batches
- [ ] Automate pattern suggestions

**🎯 Goal: Transform Regex from 70% → 95% accuracy through systematic human-in-the-loop learning**
"""Thu gọn schema JSON output từ crawler"""
import json

def compact_schema(data):
    """Chuyển đổi schema cũ sang schema mới gọn gàng hơn"""
    result = []
    
    for item in data:
        # Nếu có error, giữ nguyên
        if item.get("error"):
            result.append(item)
            continue
            
        # Extract doc_info fields (all fields except known structure fields)
        exclude_keys = {"stt", "url", "ngay_cap_nhat", "Ngay cap nhat", "tab4_relations", "tab4_summary", 
                       "tab4_total_relations", "tab8_links", "_screenshot_before", "_screenshot_tab4", 
                       "_screenshot_tab8", "error"}
        doc_info = {k: v for k, v in item.items() if k not in exclude_keys}
        
        compact_item = {
            "stt": item.get("stt"),
            "url": item.get("url"),
            "ngay_cap_nhat": item.get("Ngay cap nhat") or item.get("ngay_cap_nhat"),
            "doc_info": doc_info,
            "screenshots": {
                "before": item.get("_screenshot_before"),
                "tab4": item.get("_screenshot_tab4"),
                "tab8": item.get("_screenshot_tab8")
            },
            "tab4": {
                "relations": item.get("tab4_relations", {}),
                "summary": item.get("tab4_summary", {}),
                "total": item.get("tab4_total_relations", 0)
            },
            "tab8": {
                "links": item.get("tab8_links", [])
            }
        }
        result.append(compact_item)
    
    return result

if __name__ == "__main__":
    # Đọc file gốc
    with open("data/LinkTest_Result.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Thu gọn schema
    compact_data = compact_schema(data)
    
    # Lưu file mới
    with open("data/LinkTest_Result_Compact.json", "w", encoding="utf-8") as f:
        json.dump(compact_data, f, ensure_ascii=False, indent=2)
    
    print(f"Da thu gon {len(compact_data)} ban ghi")
    print(f"Luu tai: data/LinkTest_Result_Compact.json")

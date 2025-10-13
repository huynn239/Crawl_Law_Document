"""Thu gọn schema JSON output từ crawler"""
import json

def compact_schema(data):
    """Chuyển đổi schema cũ sang schema mới gọn gàng hơn"""
    result = []
    
    for item in data:
        compact_item = {
            "stt": item.get("stt"),
            "url": item.get("url"),
            "ngay_cap_nhat": item.get("Ngay cap nhat") or item.get("ngay_cap_nhat"),
            "doc_info": {
                "so_hieu": item.get("Số hiệu"),
                "loai_van_ban": item.get("Loại văn bản"),
                "linh_vuc": item.get("Lĩnh vực, ngành"),
                "noi_ban_hanh": item.get("Nơi ban hành"),
                "nguoi_ky": item.get("Người ký"),
                "ngay_ban_hanh": item.get("Ngày ban hành"),
                "ngay_hieu_luc": item.get("Ngày hiệu lực"),
                "ngay_dang": item.get("Ngày đăng"),
                "so_cong_bao": item.get("Số công báo"),
                "tinh_trang": item.get("Tình trạng")
            },
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

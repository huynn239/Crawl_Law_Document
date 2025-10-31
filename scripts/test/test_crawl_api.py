import requests
import json

# Test data - 2 links mẫu
test_links = [
    {
        "Stt": 1,
        "Url": "https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Nghi-dinh-01-2021-ND-CP-sua-doi-Nghi-dinh-78-2015-ND-CP-dang-ky-doanh-nghiep-463854.aspx",
        "Ten van ban": "Nghị định 01/2021/NĐ-CP",
        "Ngay cap nhat": "2021-01-04"
    },
    {
        "Stt": 2,
        "Url": "https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Luat-Doanh-nghiep-2020-438239.aspx",
        "Ten van ban": "Luật Doanh nghiệp 2020",
        "Ngay cap nhat": "2020-06-17"
    }
]

# Call API
response = requests.post(
    "http://localhost:8000/crawl-documents",
    json={
        "links": test_links,
        "concurrency": 2,
        "timeout_ms": 30000,
        "reuse_session": True,
        "headed": False
    }
)

print(f"Status: {response.status_code}")
print(f"Response:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")

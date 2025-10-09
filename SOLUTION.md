# Giải pháp: Thu thập đầy đủ hyperlink Tab4

## Vấn đề
Code hiện tại không thu thập được hyperlink trong Tab4 vì:
1. Logic phức tạp tìm kiếm theo pattern và bounding box
2. Không click nút "Xem thêm" đúng cách
3. Cấu trúc HTML thực tế khác với giả định

## Cấu trúc HTML thực tế
```html
<div id="tab4">
  <div id="guidedDocument"><!-- Văn bản được hướng dẫn --></div>
  <div id="DuocHopNhatDocument"><!-- Văn bản hợp nhất --></div>
  <div id="amendedDocument"><!-- Văn bản bị sửa đổi bổ sung --></div>
  <div id="correctedDocument"><!-- Văn bản bị đính chính --></div>
  <div id="replacedDocument"><!-- Văn bản bị thay thế --></div>
  <div id="referentialDocument"><!-- Văn bản được dẫn chiếu --></div>
  <div id="basisDocument"><!-- Văn bản được căn cứ --></div>
  <div id="contentConnection"><!-- Văn bản liên quan cùng nội dung --></div>
</div>
```

## Giải pháp đơn giản
Thu thập trực tiếp theo ID của từng div:

```python
# Mapping ID -> Nhãn tiếng Việt
REL_LABELS = {
    "guidedDocument": "Văn bản được hướng dẫn",
    "DuocHopNhatDocument": "Văn bản hợp nhất",
    "amendedDocument": "Văn bản bị sửa đổi bổ sung",
    "correctedDocument": "Văn bản bị đính chính",
    "replacedDocument": "Văn bản bị thay thế",
    "referentialDocument": "Văn bản được dẫn chiếu",
    "basisDocument": "Văn bản được căn cứ",
    "contentConnection": "Văn bản liên quan cùng nội dung",
}

# 1. Click tất cả nút "Xem thêm"
page.evaluate("""
    () => {
        const buttons = document.querySelectorAll('.dgcvm');
        buttons.forEach(btn => btn.click());
    }
""")
page.wait_for_timeout(1000)

# 2. Thu thập từng nhóm theo ID
tab4_relations = {}
for div_id, label in REL_LABELS.items():
    items = []
    div = page.query_selector(f"#{div_id}")
    if div:
        anchors = div.query_selector_all("a[href]")
        for a in anchors:
            href = a.get_attribute("href")
            if href and ("/van-ban/" in href or "/cong-van/" in href):
                full_url = urljoin(page.url, href)
                text = re.sub(r"\s+", " ", a.inner_text().strip())
                items.append({"text": text, "href": full_url})
    tab4_relations[label] = items
```

## Kết quả
Script test `tvpl_crawler/playwright_extract_fixed.py` đã thu thập thành công 12 văn bản:
- Văn bản được hướng dẫn: 1
- Văn bản bị thay thế: 1
- Văn bản được dẫn chiếu: 2
- Văn bản được căn cứ: 4
- Văn bản liên quan cùng nội dung: 4

## Cách áp dụng
Thay thế toàn bộ phần thu thập Tab4 (từ dòng ~450 đến ~1100) trong `playwright_extract.py` bằng logic đơn giản từ `playwright_extract_fixed.py`.

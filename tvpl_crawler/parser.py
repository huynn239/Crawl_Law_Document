from bs4 import BeautifulSoup
from typing import Optional, Dict, List
from urllib.parse import urljoin, urlparse
import re

def parse_title(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")
    title_tag = soup.find("title")
    return title_tag.get_text(strip=True) if title_tag else None

def extract_document_info(html: str) -> Dict:
    soup = BeautifulSoup(html, "lxml")
    # Placeholder: adapt CSS selectors for thuvienphapluat.vn later
    h1 = soup.find("h1")
    return {
        "title": h1.get_text(strip=True) if h1 else parse_title(html),
    }


def extract_document_links_from_search(html: str, base_url: str) -> List[str]:
    """
    Trích xuất các hyperlink của từng bản ghi (văn bản) từ trang kết quả tìm kiếm.
    Chiến lược an toàn: lấy mọi <a> có href chứa "/van-ban/" trong khu vực nội dung.
    """
    soup = BeautifulSoup(html, "lxml")

    candidates = []
    # Ưu tiên tìm trong vùng kết quả nếu có
    result_containers = soup.select("#content, .content, .main, .search, .result, .results")
    if not result_containers:
        result_containers = [soup]

    for container in result_containers:
        for a in container.find_all("a", href=True):
            href = a["href"].strip()
            if "/van-ban/" in href:
                candidates.append(urljoin(base_url, href))

    # Khử trùng, giữ nguyên thứ tự
    seen = set()
    links: List[str] = []
    for url in candidates:
        if url not in seen:
            seen.add(url)
            links.append(url)
    return links


def extract_document_items_from_search(html: str, base_url: str) -> List[Dict]:
    """
    Trả về danh sách item chứa thông tin định danh cơ bản cho mỗi văn bản trên trang kết quả:
    - url: URL đầy đủ tới văn bản (giữ nguyên, chưa chuẩn hóa)
    - title: tiêu đề hiển thị ngay tại kết quả tìm kiếm (nếu có)
    - category: phân nhóm chính theo path sau /van-ban/
    - slug: phần slug của văn bản (không gồm id)
    - doc_id: số id trong URL (ví dụ 674991)
    """
    soup = BeautifulSoup(html, "lxml")

    def parse_from_href(href: str) -> Dict:
        u = urljoin(base_url, href)
        pu = urlparse(u)
        # Path dạng: /van-ban/<category>/<slug>-<id>.aspx
        parts = [p for p in pu.path.split('/') if p]
        category = parts[1] if len(parts) > 2 and parts[0] == 'van-ban' else None
        last = parts[-1] if parts else ''
        m = re.search(r"-(\d+)\.aspx", last)
        doc_id = m.group(1) if m else None
        # slug trước phần -<id>.aspx
        slug = re.sub(r"-(\d+)\.aspx$", "", last)
        return {
            "url": u,
            "category": category,
            "slug": slug,
            "doc_id": doc_id,
        }

    items: List[Dict] = []
    result_containers = soup.select("#content, .content, .main, .search, .result, .results")
    if not result_containers:
        result_containers = [soup]

    for container in result_containers:
        for a in container.find_all("a", href=True):
            href = a["href"].strip()
            if "/van-ban/" in href:
                item = parse_from_href(href)
                text = a.get_text(strip=True)
                if text:
                    item["title"] = text
                items.append(item)

    # Khử trùng theo (doc_id hoặc url), giữ thứ tự
    seen = set()
    unique_items: List[Dict] = []
    for it in items:
        key = it.get("doc_id") or it.get("url")
        if key not in seen:
            seen.add(key)
            unique_items.append(it)
    return unique_items


def extract_luoc_do(html: str) -> Dict:
    """
    Trích xuất dữ liệu trong tab "Lược đồ" của trang văn bản.
    Chiến lược heuristic, không phụ thuộc chặt vào id/class cụ thể:
    - Tìm tất cả các bảng có nhiều hàng 2 cột (label, value)
    - Gộp thành dict key->value, loại bỏ các hàng rỗng
    - Lấy thêm title từ <h1> nếu có
    """
    soup = BeautifulSoup(html, "lxml")
    result: Dict[str, str] = {}

    # Tiêu đề văn bản
    h1 = soup.find("h1")
    if h1:
        title_text = h1.get_text(strip=True)
        if title_text:
            result["Tiêu đề"] = title_text

    # Heuristic: quét các bảng có nhiều dòng 2 cột
    def normalize_text(s: str) -> str:
        return re.sub(r"\s+", " ", s or "").strip()

    # Ưu tiên khu vực tab "Lược đồ": id "tab4" nếu có
    containers: List = []
    tab4 = soup.select_one("#tab4")
    if tab4:
        containers.append(tab4)
    # fallback: tìm theo tiêu đề tab có chữ Lược đồ
    for el in soup.find_all(text=re.compile(r"\bLược đồ\b", re.I)):
        sec = el.find_parent()
        if sec and sec not in containers:
            containers.append(sec)
    # cuối cùng: toàn bộ trang
    if not containers:
        containers = [soup]

    candidate_tables = []
    for c in containers:
        candidate_tables.extend(c.find_all("table"))

    # Danh sách nhãn mong đợi trong bảng ở giữa (theo ảnh)
    expected_labels = [
        "Số hiệu", "Loại văn bản", "Lĩnh vực, ngành", "Nơi ban hành", "Người ký",
        "Ngày ban hành", "Ngày hiệu lực", "Ngày hết hiệu lực", "Số công báo", "Tình trạng"
    ]

    def is_expected(label: str) -> bool:
        lab = re.sub(r":\s*$", "", label)
        for pat in expected_labels:
            if pat.lower() in lab.lower():
                return True
        return False

    # Chọn bảng có nhiều nhãn kỳ vọng nhất (đây thường là bảng "Văn bản đang xem")
    best_pairs: Dict[str, str] = {}
    best_score = -1
    for tbl in candidate_tables:
        rows = tbl.find_all("tr")
        pairs_local: Dict[str, str] = {}
        score = 0
        for tr in rows:
            tds = tr.find_all(["td", "th"])  # đôi khi là th
            if len(tds) == 2:
                left = normalize_text(tds[0].get_text(" ", strip=True))
                right = normalize_text(tds[1].get_text(" ", strip=True))
                if left:
                    if is_expected(left):
                        score += 1
                    # Chuẩn hoá label: bỏ dấu ':' cuối
                    left_key = re.sub(r":\s*$", "", left)
                    if right:
                        pairs_local[left_key] = right
            elif len(tds) == 1:
                # Một số hàng mô tả có colspan=2 => lưu làm "Mô tả" nếu hợp lý
                cell = tds[0]
                try:
                    colspan = int(cell.get("colspan", "1"))
                except Exception:
                    colspan = 1
                if colspan >= 2:
                    desc = normalize_text(cell.get_text(" ", strip=True))
                    # Bỏ dòng tiêu đề đỏ như "Văn bản đang xem"
                    if desc and not re.search(r"^Văn bản đang xem$", desc, flags=re.I):
                        # Tránh đè nếu đã có
                        pairs_local.setdefault("Mô tả", desc)
        # Ưu tiên theo score cao nhất, tie-breaker là số cặp nhiều hơn
        if score > best_score or (score == best_score and len(pairs_local) > len(best_pairs)):
            best_score = score
            best_pairs = pairs_local

    # Nếu không tìm thấy bảng phù hợp, fallback: tìm các label/value trong divs
    if not best_pairs:
        items = []
        # Tìm các khối có dạng label ở cột trái và value ở cột phải
        scope = tab4 or soup
        for lbl in scope.find_all(text=re.compile(r"Văn bản|Số hiệu|Loại văn bản|Ngày ban hành|Cơ quan ban hành|Nơi ban hành|Người ký|Ngày hiệu lực|Số công báo|Tình trạng", re.I)):
            label = normalize_text(str(lbl))
            if not label:
                continue
            # lấy giá trị từ node kế cận
            val_node = None
            parent = getattr(lbl, 'parent', None)
            if parent:
                # thử sibling kế tiếp
                val_node = parent.find_next_sibling()
            value = normalize_text(val_node.get_text(" ", strip=True)) if val_node else ""
            if value:
                items.append((re.sub(r":\s*$", "", label), value))
        for k, v in items:
            best_pairs[k] = v

    # Gộp kết quả
    for k, v in best_pairs.items():
        result[k] = v

    return result

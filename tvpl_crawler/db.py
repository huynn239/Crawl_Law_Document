"""Module lưu dữ liệu vào PostgreSQL"""
import psycopg2
import json
import hashlib
from datetime import datetime
from typing import Dict, List

class TVPLDatabase:
    def __init__(self, host="localhost", port=5432, dbname="tvpl_crawl", user="tvpl_user", password=""):
        self.conn_params = {
            "host": host,
            "port": port,
            "dbname": dbname,
            "user": user,
            "password": password
        }
        self.conn = None
    
    def connect(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**self.conn_params)
        return self.conn
    
    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()
    
    def start_crawl_session(self) -> int:
        """Bắt đầu session crawl mới"""
        conn = self.connect()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO crawl_sessions (status) VALUES ('RUNNING') RETURNING session_id
            """)
            session_id = cur.fetchone()[0]
            conn.commit()
            return session_id
        finally:
            cur.close()
    
    def complete_crawl_session(self, session_id: int, total: int, new_versions: int, unchanged: int):
        """Kết thúc session crawl"""
        conn = self.connect()
        cur = conn.cursor()
        try:
            cur.execute("""
                UPDATE crawl_sessions 
                SET status = 'COMPLETED', completed_at = NOW(), 
                    total_docs = %s, new_versions = %s, unchanged_docs = %s
                WHERE session_id = %s
            """, (total, new_versions, unchanged, session_id))
            conn.commit()
        finally:
            cur.close()
    
    def _compute_hash(self, data: dict) -> str:
        """Tính hash của dữ liệu để phát hiện thay đổi"""
        content = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _parse_date(self, date_str: str):
        """Chuyển đổi chuỗi ngày dd/mm/yyyy sang date"""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%d/%m/%Y").date()
        except:
            return None
    
    def _compute_diff(self, old_data: dict, new_data: dict) -> dict:
        """Tính toán thay đổi giữa 2 versions"""
        diff = {"changed_fields": []}
        
        # So sánh doc_info
        old_info = old_data.get("doc_info", {})
        new_info = new_data.get("doc_info", {})
        for key in new_info:
            if old_info.get(key) != new_info.get(key):
                diff["changed_fields"].append(key)
        
        # So sánh relations
        old_rels = old_data.get("tab4", {}).get("relations", {})
        new_rels = new_data.get("tab4", {}).get("relations", {})
        old_total = sum(len(v) for v in old_rels.values())
        new_total = sum(len(v) for v in new_rels.values())
        diff["relations_added"] = max(0, new_total - old_total)
        diff["relations_removed"] = max(0, old_total - new_total)
        
        return diff if diff["changed_fields"] or diff["relations_added"] or diff["relations_removed"] else None
    
    def save_document(self, data: dict, session_id: int = None):
        """Lưu văn bản vào database"""
        conn = self.connect()
        cur = conn.cursor()
        
        try:
            doc_id = data.get("url", "").split("-")[-1].replace(".aspx", "") if data.get("url") else None
            if not doc_id:
                return
            
            title = data.get("doc_info", {}).get("so_hieu", "") or "Untitled"
            url = data.get("url", "")
            update_date = self._parse_date(data.get("ngay_cap_nhat", ""))
            effective_date = self._parse_date(data.get("doc_info", {}).get("ngay_hieu_luc", ""))
            
            metadata = data.get("doc_info", {})
            
            # Lấy link download đầu tiên từ tab8
            download_link = ""
            tab8_links = data.get("tab8", {}).get("links", [])
            if tab8_links:
                download_link = tab8_links[0].get("href", "")
            
            content_hash = self._compute_hash(data)
            
            # Kiểm tra hash cũ TRƯỚC khi update
            cur.execute("""
                SELECT hash FROM documents_finals WHERE doc_id = %s
            """, (doc_id,))
            old_hash_row = cur.fetchone()
            old_hash = old_hash_row[0] if old_hash_row else None
            
            # Xác định có thay đổi không (lần đầu = thay đổi)
            has_changed = (old_hash is None or old_hash != content_hash)
            
            # Insert/Update documents_finals
            cur.execute("""
                INSERT INTO documents_finals (doc_id, title, url, hash, update_date, effective_date, metadata, download_link, last_crawled)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (doc_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    url = EXCLUDED.url,
                    hash = EXCLUDED.hash,
                    update_date = EXCLUDED.update_date,
                    effective_date = EXCLUDED.effective_date,
                    metadata = EXCLUDED.metadata,
                    download_link = EXCLUDED.download_link,
                    last_crawled = NOW(),
                    updated_at = NOW()
            """, (doc_id, title, url, content_hash, update_date, effective_date, json.dumps(metadata), download_link))
            
            # Chỉ insert version nếu có thay đổi (bao gồm lần đầu)
            if has_changed:
                # Tính diff_summary và source_snapshot_date
                diff_summary = None
                source_snapshot_date = update_date
                
                if old_hash:  # Không phải lần đầu
                    cur.execute("""
                        SELECT content FROM document_versions 
                        WHERE doc_id = %s ORDER BY crawled_at DESC LIMIT 1
                    """, (doc_id,))
                    old_content_row = cur.fetchone()
                    if old_content_row:
                        old_data = json.loads(old_content_row[0])
                        diff_summary = self._compute_diff(old_data, data)
                
                cur.execute("""
                    INSERT INTO document_versions (doc_id, version_hash, content, session_id, diff_summary, source_snapshot_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (doc_id, content_hash, json.dumps(data), session_id, json.dumps(diff_summary) if diff_summary else None, source_snapshot_date))
            
            # Chỉ update relations nếu có thay đổi
            if has_changed:
                # Xóa relations cũ
                cur.execute("""
                    DELETE FROM document_relations WHERE source_doc_id = %s
                """, (doc_id,))
                
                # Insert relations mới
                tab4 = data.get("tab4", {})
                relations = tab4.get("relations", {})
                
                for relation_type, targets in relations.items():
                    if not targets:
                        continue
                    for target in targets:
                        target_url = target.get("href", "")
                        target_title = target.get("text", "")
                        target_doc_id = target_url.split("-")[-1].replace(".aspx", "") if target_url else None
                        
                        cur.execute("""
                            INSERT INTO document_relations (source_doc_id, relation_type, target_doc_id, target_url, target_title, resolved)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (doc_id, relation_type, target_doc_id, target_url, target_title, bool(target_doc_id)))
            
            conn.commit()
            return has_changed
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cur.close()

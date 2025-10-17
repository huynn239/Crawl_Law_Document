"""TNPL Database operations"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

class TNPLDatabase:
    def __init__(self, host="localhost", port=5432, dbname="tvpl_crawl", user="tvpl_user", password=""):
        self.conn_params = {"host": host, "port": port, "dbname": dbname, "user": user, "password": password}
        self.conn = None
    
    def connect(self):
        if not HAS_PSYCOPG2:
            raise ImportError("psycopg2 not installed")
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**self.conn_params)
        return self.conn
    
    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()
    
    def start_session(self) -> int:
        conn = self.connect()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO tnpl_crawl_sessions (status) VALUES ('RUNNING') RETURNING session_id")
            session_id = cur.fetchone()[0]
            conn.commit()
            return session_id
        finally:
            cur.close()
    
    def complete_session(self, session_id: int, total: int, new: int, updated: int, status: str = 'COMPLETED'):
        conn = self.connect()
        cur = conn.cursor()
        try:
            cur.execute("""
                UPDATE tnpl_crawl_sessions 
                SET status = %s, completed_at = NOW(), 
                    total_terms = %s, new_terms = %s, updated_terms = %s
                WHERE session_id = %s
            """, (status, total, new, updated, session_id))
            conn.commit()
        finally:
            cur.close()
    
    def save_term(self, term: dict, session_id: int = None):
        conn = self.connect()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO tnpl_terms (term_name, definition, url, source_crawl)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (url) DO UPDATE SET
                    term_name = EXCLUDED.term_name,
                    definition = EXCLUDED.definition,
                    source_crawl = EXCLUDED.source_crawl,
                    updated_at = NOW()
                RETURNING term_id, (xmax = 0) AS inserted
            """, (
                term.get("term_name"),
                term.get("definition"),
                term.get("url"),
                term.get("source_crawl")
            ))
            result = cur.fetchone()
            conn.commit()
            return result[1]  # True if inserted, False if updated
        finally:
            cur.close()

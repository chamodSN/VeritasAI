from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
import sqlite3
import time
import json
from common.security import verify_message

class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        body = await request.body()
        response = await call_next(request)
        duration = time.time() - start

        # Simple SQLite append-only log
        conn = sqlite3.connect("data/audit_log.db")
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts INTEGER,
                route TEXT,
                body_hash TEXT,
                duration REAL
            )
        """)
        c.execute("INSERT INTO audit_log(ts, route, body_hash, duration) VALUES (?,?,?,?)",
                  (int(start), str(request.url), str(hash(body)), duration))
        conn.commit()
        conn.close()
        return response

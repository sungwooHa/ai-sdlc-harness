#!/usr/bin/env python3
"""Local synthetic staff app with atomic SQLite batches and response-loss injection."""
import argparse
import hashlib
import json
import re
import socket
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
STATIC = {"index.html": "text/html; charset=utf-8", "fields.mjs": "text/javascript",
          "state.mjs": "text/javascript", "app.mjs": "text/javascript"}


def validate(payload):
    if not isinstance(payload, dict):
        raise ValueError("object_required")
    request_id = payload.get("request_id")
    if not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,80}", request_id):
        raise ValueError("request_id_required")
    entries = payload.get("entries")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 10:
        raise ValueError("one_to_ten_entries_required")
    clean = []
    keys = ("name", "phonePrefix", "phoneMiddle", "phoneLast", "payType", "payAmount",
            "bank", "bankName", "account")
    for entry in entries:
        if not isinstance(entry, dict) or any(not isinstance(entry.get(key), str) for key in keys):
            raise ValueError("entry_fields_required")
        row = {key: entry[key] for key in keys}
        row["name"] = row["name"].strip()
        if not row["name"] or len(row["name"]) > 80:
            raise ValueError("name_required")
        if row["phonePrefix"] not in ("010", "011", "016", "017", "018", "019"):
            raise ValueError("mobile_prefix_required")
        if any(not re.fullmatch(r"[0-9]{4}", row[key]) for key in ("phoneMiddle", "phoneLast")):
            raise ValueError("four_digit_segments_required")
        if row["payType"] not in ("hourly", "monthly") or not re.fullmatch(r"[0-9]{1,12}", row["payAmount"]):
            raise ValueError("pay_value_required")
        if not re.fullmatch(r"[0-9]{0,40}", row["account"]):
            raise ValueError("account_digits_required")
        if len(row["bank"]) > 80 or len(row["bankName"]) > 80:
            raise ValueError("bank_value_too_long")
        clean.append(row)
    return request_id, clean


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def send_json(self, status, value):
        body = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        if path == "/api/entries":
            with sqlite3.connect(self.server.db) as connection:
                rows = connection.execute("SELECT id, payload FROM entries ORDER BY id").fetchall()
            self.send_json(200, {"entries": [{**json.loads(payload), "id": row_id} for row_id, payload in rows]})
        elif path.startswith("/api/results/"):
            request_id = path[len("/api/results/"):]
            with sqlite3.connect(self.server.db) as connection:
                row = connection.execute("SELECT result FROM batches WHERE request_id = ?", (request_id,)).fetchone()
            self.send_json(200, json.loads(row[0])) if row else self.send_json(404, {"error": "not_registered"})
        else:
            name = "index.html" if path == "/" else path.lstrip("/")
            if name not in STATIC:
                self.send_json(404, {"error": "not_found"})
                return
            body = (ROOT / name).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", STATIC[name])
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    def do_POST(self):
        if urlsplit(self.path).path != "/api/batches":
            self.send_json(404, {"error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536:
                raise ValueError("invalid_body_size")
            request_id, entries = validate(json.loads(self.rfile.read(length)))
        except (ValueError, UnicodeDecodeError):
            self.send_json(400, {"error": "invalid_batch"})
            return
        canonical = json.dumps(entries, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        with sqlite3.connect(self.server.db, timeout=10) as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT digest, result FROM batches WHERE request_id = ?", (request_id,)).fetchone()
            if existing:
                if existing[0] != digest:
                    status, result = 409, {"error": "request_id_conflict"}
                else:
                    status, result = 200, json.loads(existing[1])
            else:
                ids = []
                for entry in entries:
                    cursor = connection.execute(
                        "INSERT INTO entries (request_id, payload) VALUES (?, ?)",
                        (request_id, json.dumps(entry, ensure_ascii=False)))
                    ids.append(cursor.lastrowid)
                status, result = 201, {"request_id": request_id, "count": len(ids), "ids": ids}
                connection.execute("INSERT INTO batches (request_id, digest, result) VALUES (?, ?, ?)",
                                   (request_id, digest, json.dumps(result)))
        with self.server.drop_lock:
            drop = status == 201 and self.server.drop_once
            if drop:
                self.server.drop_once = False
        if drop:
            self.close_connection = True
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.connection.close()
            return
        self.send_json(status, result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--drop-response-once", action="store_true")
    args = parser.parse_args()
    if not args.db.is_absolute():
        parser.error("--db must be an absolute path outside the source checkout")
    db = args.db.resolve()
    source = ROOT.parent.parent if ROOT.name == "app" and ROOT.parent.name == "apps" else ROOT
    if db == source or source in db.parents:
        parser.error("--db must be outside the source checkout")
    db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db) as connection:
        connection.executescript(
            "CREATE TABLE IF NOT EXISTS batches (request_id TEXT PRIMARY KEY, digest TEXT NOT NULL, result TEXT NOT NULL);"
            "CREATE TABLE IF NOT EXISTS entries (id INTEGER PRIMARY KEY, request_id TEXT NOT NULL, payload TEXT NOT NULL);")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.db = str(db)
    server.drop_once = args.drop_response_once
    server.drop_lock = threading.Lock()
    print("http://127.0.0.1:" + str(server.server_port), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

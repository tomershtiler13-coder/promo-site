#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVENTS_DIR = ROOT / "events"
INDEX_JSON = EVENTS_DIR / "index.json"

SLUG_RE = re.compile(r"[^a-z0-9\-]+", re.IGNORECASE)

META_TEMPLATE = {
    "title": "",
    "date": "2026-03-02",      # YYYY-MM-DD
    "time": "22:00",           # HH:MM (optional but recommended)
    "location": "",
    "description": "",
    "ticket_url": "",
    "promoter_url": "",
    "coupon_code": "",
    "image": "cover.jpg"
}

def slugify(s: str) -> str:
    s = s.strip().lower()
    s = s.replace(" ", "-")
    s = SLUG_RE.sub("", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "event"

def read_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))

def write_json(p: Path, data: Any) -> None:
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def parse_dt(meta: dict) -> datetime:
    date = str(meta.get("date", "")).strip()
    time = str(meta.get("time", "00:00") or "00:00").strip()

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        raise ValueError(f"Bad date format: {date!r} (expected YYYY-MM-DD)")
    if time and not re.match(r"^\d{2}:\d{2}$", time):
        raise ValueError(f"Bad time format: {time!r} (expected HH:MM)")
    return datetime.fromisoformat(f"{date}T{time}:00")

def cmd_new(args: argparse.Namespace) -> None:
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)

    date = args.date
    title = args.title
    slug = args.slug or slugify(title)
    folder_name = f"{date}-{slug}"
    event_dir = EVENTS_DIR / folder_name

    if event_dir.exists():
        raise SystemExit(f"❌ Folder already exists: {event_dir}")

    event_dir.mkdir(parents=True)

    meta = dict(META_TEMPLATE)
    meta["title"] = title
    meta["date"] = date

    if args.time:
        meta["time"] = args.time
    if args.location:
        meta["location"] = args.location
    if args.description:
        meta["description"] = args.description
    if args.coupon:
        meta["coupon_code"] = args.coupon
    if args.ticket:
        meta["ticket_url"] = args.ticket
    if args.promoter:
        meta["promoter_url"] = args.promoter

    write_json(event_dir / "meta.json", meta)

    # placeholder image file (replace with real cover.jpg)
    (event_dir / meta["image"]).touch(exist_ok=True)

    print("✅ Created:", event_dir)
    print("   - meta.json")
    print(f"   - {meta['image']} (placeholder – replace with real image)")
    print()
    print("Next:")
    print("  python tools/promogen.py build")

def cmd_build(_: argparse.Namespace) -> None:
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)

    items: list[tuple[datetime, str]] = []
    for d in EVENTS_DIR.iterdir():
        if not d.is_dir():
            continue
        meta_path = d / "meta.json"
        if not meta_path.exists():
            continue

        meta = read_json(meta_path)

        # validate required fields
        _ = meta.get("title", "")
        dt = parse_dt(meta)

        # warn if cover image missing
        image = meta.get("image", "cover.jpg")
        if not (d / image).exists():
            print(f"⚠️ Missing image in {d.name}: {image}")

        items.append((dt, d.name))

    # upcoming first in UI anyway; keep a stable chronological order here
    items.sort(key=lambda x: x[0])
    folders = [name for _, name in items]

    write_json(INDEX_JSON, folders)
    print(f"✅ Wrote {INDEX_JSON} with {len(folders)} events")

def cmd_serve(args: argparse.Namespace) -> None:
    import http.server
    import socketserver
    import os

    os.chdir(str(ROOT))
    port = args.port
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"✅ Serving on http://localhost:{port}")
        httpd.serve_forever()

def main() -> None:
    p = argparse.ArgumentParser(prog="promogen", description="Event promo site generator")
    sub = p.add_subparsers(required=True)

    p_new = sub.add_parser("new", help="Create a new event folder with meta.json")
    p_new.add_argument("--date", required=True, help="YYYY-MM-DD")
    p_new.add_argument("--title", required=True, help="Event title")
    p_new.add_argument("--time", help="HH:MM")
    p_new.add_argument("--location", help="Location text")
    p_new.add_argument("--description", help="Short description")
    p_new.add_argument("--coupon", help="Coupon code")
    p_new.add_argument("--ticket", help="Ticket URL")
    p_new.add_argument("--promoter", help="Your link (instagram/whatsapp/etc)")
    p_new.add_argument("--slug", help="Optional custom slug")
    p_new.set_defaults(func=cmd_new)

    p_build = sub.add_parser("build", help="Rebuild events/index.json from event folders")
    p_build.set_defaults(func=cmd_build)

    p_serve = sub.add_parser("serve", help="Local server for testing")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.set_defaults(func=cmd_serve)

    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()

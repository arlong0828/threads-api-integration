#!/usr/bin/env python3
"""Minimal Threads API CLI for Gary/Hermes workflows.

Usage:
  python threads_cli.py oauth-url
  python threads_cli.py exchange --code CODE
  python threads_cli.py refresh
  python threads_cli.py profile
  python threads_cli.py list --limit 5
  python threads_cli.py post "hello threads"

Secrets are read from .env in this directory by default.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import urllib.parse
from pathlib import Path

import requests

BASE = "https://graph.threads.net/v1.0"
AUTH_URL = "https://threads.net/oauth/authorize"
TOKEN_URL = "https://graph.threads.net/oauth/access_token"
ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
TOKEN_PATH = ROOT / "token.json"
DEFAULT_SCOPES = [
    "threads_basic",
    "threads_content_publish",
    "threads_read_replies",
    "threads_manage_replies",
    "threads_manage_insights",
]


def load_dotenv(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def need_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise SystemExit(f"Missing {name}. Copy .env.example to .env and fill it in.")
    return v


def read_token() -> str:
    token = os.getenv("THREADS_ACCESS_TOKEN")
    if token:
        return token
    if TOKEN_PATH.exists():
        data = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
        token = data.get("access_token")
        if token:
            return token
    raise SystemExit("Missing access token. Run exchange first or set THREADS_ACCESS_TOKEN in .env.")


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except Exception:
        pass


def request(method: str, url: str, **kwargs) -> dict:
    resp = requests.request(method, url, timeout=30, **kwargs)
    try:
        payload = resp.json()
    except Exception:
        payload = {"raw": resp.text}
    if resp.status_code >= 400:
        raise SystemExit(json.dumps({"status_code": resp.status_code, "error": payload}, ensure_ascii=False, indent=2))
    return payload


def cmd_oauth_url(args):
    client_id = need_env("THREADS_CLIENT_ID")
    redirect_uri = need_env("THREADS_REDIRECT_URI")
    scopes = args.scopes or DEFAULT_SCOPES
    qs = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": ",".join(scopes),
        "response_type": "code",
    })
    print(f"{AUTH_URL}?{qs}")


def cmd_exchange(args):
    code = args.code or os.getenv("THREADS_OAUTH_CODE") or getpass.getpass("Threads OAuth code: ")
    data = {
        "client_id": need_env("THREADS_CLIENT_ID"),
        "client_secret": need_env("THREADS_CLIENT_SECRET"),
        "grant_type": "authorization_code",
        "redirect_uri": need_env("THREADS_REDIRECT_URI"),
        "code": code,
    }
    short = request("POST", TOKEN_URL, data=data)
    save_json(ROOT / "token.short.json", short)
    access_token = short.get("access_token")
    if not access_token:
        print(json.dumps(short, ensure_ascii=False, indent=2))
        raise SystemExit("No access_token in exchange response")
    long_url = f"{BASE}/access_token"
    long_payload = request("GET", long_url, params={
        "grant_type": "th_exchange_token",
        "client_secret": need_env("THREADS_CLIENT_SECRET"),
        "access_token": access_token,
    })
    save_json(TOKEN_PATH, long_payload)
    print(json.dumps({"status": "token_saved", "path": str(TOKEN_PATH)}, ensure_ascii=False))


def cmd_refresh(args):
    payload = request("GET", f"{BASE}/refresh_access_token", params={
        "grant_type": "th_refresh_token",
        "access_token": read_token(),
    })
    save_json(TOKEN_PATH, payload)
    print(json.dumps({"status": "token_refreshed", "path": str(TOKEN_PATH)}, ensure_ascii=False))


def cmd_profile(args):
    fields = args.fields or "id,username,name,threads_profile_picture_url,threads_biography"
    payload = request("GET", f"{BASE}/me", params={"fields": fields, "access_token": read_token()})
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_list(args):
    fields = args.fields or "id,media_type,permalink,username,text,timestamp,shortcode"
    payload = request("GET", f"{BASE}/me/threads", params={"fields": fields, "limit": args.limit, "access_token": read_token()})
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_post(args):
    token = read_token()
    create = request("POST", f"{BASE}/me/threads", data={
        "media_type": "TEXT",
        "text": args.text,
        "access_token": token,
    })
    creation_id = create.get("id")
    if not creation_id:
        print(json.dumps(create, ensure_ascii=False, indent=2))
        raise SystemExit("No creation container id returned")
    published = request("POST", f"{BASE}/me/threads_publish", data={
        "creation_id": creation_id,
        "access_token": token,
    })
    print(json.dumps(published, ensure_ascii=False, indent=2))


def main(argv=None):
    load_dotenv()
    p = argparse.ArgumentParser(description="Threads API CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("oauth-url", help="Print Meta Threads OAuth authorization URL")
    s.add_argument("--scopes", nargs="*", help="Override scopes")
    s.set_defaults(func=cmd_oauth_url)

    s = sub.add_parser("exchange", help="Exchange OAuth code for long-lived token")
    s.add_argument("--code", help="OAuth code (prefer THREADS_OAUTH_CODE or hidden prompt)")
    s.set_defaults(func=cmd_exchange)

    s = sub.add_parser("refresh", help="Refresh long-lived token")
    s.set_defaults(func=cmd_refresh)

    s = sub.add_parser("profile", help="Get Threads profile")
    s.add_argument("--fields")
    s.set_defaults(func=cmd_profile)

    s = sub.add_parser("list", help="List own Threads posts")
    s.add_argument("--limit", type=int, default=5)
    s.add_argument("--fields")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("post", help="Publish text post")
    s.add_argument("text")
    s.set_defaults(func=cmd_post)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

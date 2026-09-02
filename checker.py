import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ENTRY_URL = "https://account.tbki.ru/login"
BASE = "https://account.tbki.ru"
STATE = "state.json"

ASSET_RE = re.compile(r"/assets/index-[A-Za-z0-9_-]+\.js")
PATH_RE = re.compile(r"^/[A-Za-z0-9_/-]{1,120}$")
SKIP_PATHS = {"/", "/api", "/img", "/assets", "/docs"}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/152.0 Safari/537.36"
            ),
            "X-Bug-Bounty": "ScopeSova",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def extract_paths(js: bytes) -> list:
    text = js.decode("utf-8", "replace")
    out = set()
    for m in re.finditer(r'["\'`]([^"\'`]{1,150})["\'`]', text):
        s = m.group(1)
        if PATH_RE.match(s) and s not in SKIP_PATHS:
            out.add(s)
    for m in re.finditer(r"`([^`]{1,300})`", text):
        for mm in re.finditer(r"/[A-Za-z0-9][A-Za-z0-9/_-]{0,100}", m.group(1)):
            frag = mm.group(0)
            if frag not in SKIP_PATHS:
                out.add(frag)
    return sorted(out)


def tg_send(text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat:
        print("telegram not configured, skipping send")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode(
        {"chat_id": chat, "text": text[:3900], "disable_web_page_preview": "true"}
    ).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()


def main() -> int:
    html = fetch(ENTRY_URL).decode("utf-8", "replace")
    m = ASSET_RE.search(html)
    if not m:
        print("bundle link not found on entry page")
        return 1

    asset = m.group(0)
    js = fetch(BASE + asset)
    digest = hashlib.sha256(js).hexdigest()
    paths = extract_paths(js)

    state = {}
    if os.path.exists(STATE):
        try:
            with open(STATE, encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}

    old_hash = state.get("hash")
    old_paths = set(state.get("paths", []))

    lines = []
    if old_hash is None:
        lines.append("Radar online.")
        lines.append(f"Bundle: {asset}")
        lines.append(f"sha256: {digest[:12]}")
        lines.append(f"api-ish paths found: {len(paths)}")
    elif old_hash != digest:
        lines.append(f"Bundle CHANGED: {state.get('asset', '?')} -> {asset}")
        lines.append(f"sha256: {str(old_hash)[:12]} -> {digest[:12]}")
        added = sorted(set(paths) - old_paths)
        removed = sorted(old_paths - set(paths))
        if added:
            lines.append("NEW paths:")
            lines += [f"+ {p}" for p in added]
        if removed:
            lines.append("REMOVED paths:")
            lines += [f"- {p}" for p in removed]
        if not added and not removed:
            lines.append("(path set unchanged)")
    else:
        print("no changes")
        return 0

    state["hash"] = digest
    state["asset"] = asset
    state["paths"] = paths
    state["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1, ensure_ascii=False)

    msg = "\n".join(lines)
    print(msg)
    try:
        tg_send(msg)
    except Exception as e:
        print("telegram error:", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, mimetypes, os, re, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

SOURCE_URL = "https://raw.githubusercontent.com/serhii-londar/open-source-mac-os-apps/master/applications.json"
ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "state.json"
FEEDS_DIR = ROOT / "feeds"
MAX_EVENTS = 500
MAX_FEED_ITEMS = 100

def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def load_source():
    req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "open-source-mac-apps-rss/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def load_state():
    if not STATE_FILE.exists():
        return {"version": 2, "initialized": False, "apps": {}, "events": []}
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))

def normalize(raw):
    a = dict(raw)
    a["title"] = str(a.get("title") or a.get("name") or "Untitled").strip()
    a["repo_url"] = str(a.get("repo_url") or "").strip()
    a["official_site"] = str(a.get("official_site") or "").strip()
    a["icon_url"] = str(a.get("icon_url") or "").strip()
    a["short_description"] = str(a.get("short_description") or a.get("description") or "").strip()
    cats = a.get("categories") or []
    if isinstance(cats, str):
        cats = [cats]
    a["categories"] = sorted({str(x).strip() for x in cats if str(x).strip()}, key=str.casefold)
    return a

def app_id(a):
    identity = a.get("repo_url") or a.get("official_site") or a.get("title") or "unknown"
    return hashlib.sha256(identity.lower().encode()).hexdigest()[:20]

def signature(a):
    keys = ["title", "short_description", "categories", "repo_url", "official_site", "icon_url", "languages", "screenshots"]
    payload = json.dumps({k: a.get(k) for k in keys}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def slug(s):
    x = re.sub(r"[^a-z0-9]+", "-", s.strip().lower())
    return re.sub(r"-+", "-", x).strip("-") or "uncategorized"

def link(a):
    return a.get("official_site") or a.get("repo_url") or SOURCE_URL

def event_title(e):
    return {"new": "New: ", "updated": "Updated: ", "removed": "Removed: "}[e["type"]] + e["title"]

def event_description(e):
    a = e.get("app") or {}
    prefix = {
        "new": "A new application was added to the source directory.",
        "updated": "An application entry changed in the source directory.",
        "removed": "An application was removed from the source directory."
    }[e["type"]]
    parts = [prefix]
    if a.get("short_description"):
        parts.append(a["short_description"])
    if a.get("categories"):
        parts.append("Categories: " + ", ".join(a["categories"]) + ".")
    return " ".join(parts)

def item_xml(e):
    a = e.get("app") or {}
    lines = [
        "    <item>",
        "      <title>" + escape(event_title(e)) + "</title>",
        "      <description>" + escape(event_description(e)) + "</description>",
        "      <link>" + escape(link(a)) + "</link>",
        '      <guid isPermaLink="false">open-source-mac-apps-rss:' + escape(e["id"]) + "</guid>",
        "      <pubDate>" + e["timestamp"] + "</pubDate>",
    ]
    for c in a.get("categories") or []:
        lines.append("      <category>" + escape(str(c)) + "</category>")
    icon = str(a.get("icon_url") or "")
    if icon.startswith(("http://", "https://")):
        mime = mimetypes.guess_type(icon.split("?", 1)[0])[0] or "image/jpeg"
        lines.append('      <enclosure url="' + escape(icon, {'"': "&quot;"}) + '" length="0" type="' + escape(mime) + '" />')
    lines.append("    </item>")
    return "\n".join(lines)

def write_feed(path, title, description, url, events):
    items = "\n".join(item_xml(e) for e in events[:MAX_FEED_ITEMS])
    xml = "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        "  <channel>",
        "    <title>" + escape(title) + "</title>",
        "    <description>" + escape(description) + "</description>",
        "    <link>" + escape(url) + "</link>",
        "    <lastBuildDate>" + now() + "</lastBuildDate>",
        "    <language>en</language>",
        items,
        "  </channel>",
        "</rss>",
        ""
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(xml, encoding="utf-8")

def main():
    raw = load_source()
    raw_apps = raw.get("applications", raw.get("apps", [])) if isinstance(raw, dict) else raw
    current = {}
    for raw_app in raw_apps:
        if isinstance(raw_app, dict):
            a = normalize(raw_app)
            current[app_id(a)] = a

    state = load_state()
    previous = state.get("apps", {})
    events = list(state.get("events", []))
    timestamp = now()

    if not state.get("initialized"):
        state["initialized"] = True
    else:
        for key, a in current.items():
            sig = signature(a)
            if key not in previous:
                kind = "new"
            elif previous[key].get("signature") != sig:
                kind = "updated"
            else:
                continue
            events.append({"id": f"{timestamp}-{key}-{kind}", "type": kind, "timestamp": timestamp, "title": a["title"], "app": a})
        for key, old in previous.items():
            if key not in current:
                a = old.get("app") or {}
                events.append({"id": f"{timestamp}-{key}-removed", "type": "removed", "timestamp": timestamp, "title": a.get("title") or key, "app": a})

    state["apps"] = {k: {"signature": signature(a), "app": a} for k, a in current.items()}
    state["events"] = events[-MAX_EVENTS:]
    state["last_run"] = timestamp
    state["source_url"] = SOURCE_URL
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    FEEDS_DIR.mkdir(parents=True, exist_ok=True)
    base = os.environ.get("FEED_BASE_URL", "https://OWNER.github.io/REPOSITORY").rstrip("/")
    ordered = list(reversed(state["events"]))
    write_feed(FEEDS_DIR / "feed.xml", "Open Source Mac Apps – Changes",
               "New, updated and removed applications from the open-source-mac-apps directory.",
               base + "/feeds/feed.xml", ordered)

    categories = sorted({c for e in state["events"] for c in (e.get("app") or {}).get("categories", [])}, key=str.casefold)
    for c in categories:
        ce = [e for e in ordered if c in (e.get("app") or {}).get("categories", [])]
        name = "category-" + slug(c) + ".xml"
        write_feed(FEEDS_DIR / name, "Open Source Mac Apps – " + c,
                   "Changes for the " + c + " category.", base + "/feeds/" + name, ce)
    print(f"Processed {len(current)} apps; generated {1 + len(categories)} feed(s).")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR:", exc, file=sys.stderr)
        raise

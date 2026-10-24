#!/usr/bin/env python3
import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape
from pathlib import Path

SOURCE_URLS = [
    os.environ.get("SOURCE_URL"),
    "https://raw.githubusercontent.com/serhii-londar/open-source-mac-os-apps/master/applications.json",
    "https://raw.githubusercontent.com/serhii-londar/open-source-mac-os-apps/main/applications.json",
]
FEED_URL = os.environ.get("FEED_URL", "https://example.github.io/open-source-mac-apps-rss/feed.xml")
SOURCE_PAGE = "https://serhii-londar.github.io/open-source-mac-os-apps/"
STATE_FILE = Path("state.json")
FEED_FILE = Path("feed.xml")
MAX_NEW_ITEMS = 50
MAX_TOTAL_ITEMS = 100

def fetch_applications():
    urls = [u for u in SOURCE_URLS if u]
    last_error = None
    for url in urls:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "open-source-mac-apps-rss/1.0"}
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                last_error = e
                continue
            raise
        except Exception as e:
            last_error = e
            continue
    if last_error:
        raise last_error
    raise RuntimeError("No source URL configured.")

def app_id(app):
    return app.get("repo_url") or app.get("official_site") or app.get("title", "").strip()

def app_date(app):
    # applications.json currently does not expose a reliable per-app date.
    # Therefore new entries get the time of discovery.
    return datetime.now(timezone.utc)

def load_state():
    if not STATE_FILE.exists():
        return {"known": [], "items": []}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"known": [], "items": []}

def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

def make_item(app, discovered):
    title = app.get("title") or app.get("name") or "Unnamed app"
    description = (app.get("short_description") or app.get("description") or "").strip()
    repo = (app.get("repo_url") or "").strip()
    official = (app.get("official_site") or "").strip()
    icon = (app.get("icon_url") or "").strip()
    categories = app.get("categories") or []
    languages = app.get("languages") or []

    parts = []
    if icon and icon.startswith(("http://", "https://")):
        parts.append(f'<p><img src="{escape(icon, quote=True)}" alt="{escape(title, quote=True)}" width="64" height="64" /></p>')
    if description:
        parts.append(f'<p>{escape(description)}</p>')
    if repo:
        parts.append(f'<p><strong>GitHub:</strong> <a href="{escape(repo, quote=True)}">{escape(repo)}</a></p>')
    if official and official.startswith(("http://", "https://")) and official != repo:
        parts.append(f'<p><strong>Website:</strong> <a href="{escape(official, quote=True)}">{escape(official)}</a></p>')

    meta = []
    if categories:
        meta.append("Kategorien: " + ", ".join(categories))
    if languages:
        meta.append("Sprachen: " + ", ".join(languages))
    if meta:
        parts.append("<p>" + escape(" · ".join(meta)) + "</p>")

    guid = repo or official or app_id(app)
    return {
        "title": title,
        "description": "".join(parts),
        "link": repo or official or SOURCE_PAGE,
        "guid": guid,
        "pubDate": format_datetime(discovered),
    }

def load_existing_items(state):
    if "feed_items" in state and isinstance(state["feed_items"], list):
        return state["feed_items"]

    if not FEED_FILE.exists():
        return []

    try:
        root = ET.fromstring(FEED_FILE.read_text(encoding="utf-8"))
        items = []
        for item in root.findall("./channel/item"):
            items.append({
                "title": item.findtext("title", ""),
                "description": item.findtext("description", ""),
                "link": item.findtext("link", ""),
                "guid": item.findtext("guid", ""),
                "pubDate": item.findtext("pubDate", ""),
            })
        return items
    except Exception:
        return []

def xml_item(item):
    desc = item.get("description", "").replace("]]>", "]]&gt;")
    return f"""    <item>
      <title>{escape(item.get("title", ""))}</title>
      <description><![CDATA[{desc}]]></description>
      <link>{escape(item.get("link", ""), quote=True)}</link>
      <guid isPermaLink="false">{escape(item.get("guid", ""))}</guid>
      <pubDate>{escape(item.get("pubDate", ""))}</pubDate>
    </item>"""

def write_feed(items):
    now = format_datetime(datetime.now(timezone.utc))
    body = "\n".join(xml_item(i) for i in items)
    if body:
        body = "\n" + body
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Open Source Mac Apps – Neue Apps</title>
    <description>Neue Open-Source-Mac-Apps aus der Sammlung von serhii-londar.</description>
    <link>{escape(SOURCE_PAGE, quote=True)}</link>
    <atom:link href="{escape(FEED_URL, quote=True)}" rel="self" type="application/rss+xml"/>
    <lastBuildDate>{now}</lastBuildDate>{body}
  </channel>
</rss>
"""
    FEED_FILE.write_text(xml, encoding="utf-8")

def main():
    data = fetch_applications()
    apps = data.get("applications", [])
    state = load_state()
    known = set(state.get("known", []))

    # First run: establish baseline without flooding the RSS reader.
    if not known:
        state["known"] = sorted({app_id(a) for a in apps if app_id(a)})
        state["items"] = []
        state["feed_items"] = []
        save_state(state)
        write_feed([])
        print(f"Initial baseline created: {len(state['known'])} apps.")
        return

    new_apps = [a for a in apps if app_id(a) and app_id(a) not in known]

    if not new_apps and FEED_FILE.exists():
        print(f"No new apps found. Current known count: {len(known)}.")
        return

    existing = load_existing_items(state)
    new_items = [make_item(a, app_date(a)) for a in new_apps[:MAX_NEW_ITEMS]]

    # newest first
    all_items = list(reversed(new_items)) + existing
    all_items = all_items[:MAX_TOTAL_ITEMS]

    for app in new_apps:
        ident = app_id(app)
        if ident:
            known.add(ident)

    state["known"] = sorted(known)
    state["items"] = [i["guid"] for i in all_items]
    state["feed_items"] = all_items
    save_state(state)
    write_feed(all_items)

    print(f"Found {len(new_apps)} new apps; published {len(new_items)}.")

if __name__ == "__main__":
    main()

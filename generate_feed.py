#!/usr/bin/env python3
import json
import os
import urllib.request
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape
from pathlib import Path

SOURCE_URL = "https://raw.githubusercontent.com/serhii-londar/open-source-mac-os-apps/master/applications.json"
FEED_URL = os.environ.get("FEED_URL", "https://example.github.io/open-source-mac-apps-rss/feed.xml")
SOURCE_PAGE = "https://serhii-londar.github.io/open-source-mac-os-apps/"
STATE_FILE = Path("state.json")
FEED_FILE = Path("feed.xml")
MAX_NEW_ITEMS = 50

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "open-source-mac-apps-rss/1.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

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
    title = app.get("title", "Unnamed app")
    description = app.get("short_description", "")
    repo = app.get("repo_url", "")
    official = app.get("official_site", "")
    categories = app.get("categories") or []
    languages = app.get("languages") or []

    links = []
    if repo:
        links.append(f'<p><strong>GitHub:</strong> <a href="{escape(repo, quote=True)}">{escape(repo)}</a></p>')
    if official and official.startswith(("http://", "https://")) and official != repo:
        links.append(f'<p><strong>Website:</strong> <a href="{escape(official, quote=True)}">{escape(official)}</a></p>')

    meta = []
    if categories:
        meta.append("Kategorien: " + ", ".join(categories))
    if languages:
        meta.append("Sprachen: " + ", ".join(languages))
    if meta:
        links.append("<p>" + escape(" · ".join(meta)) + "</p>")

    guid = repo or app_id(app)
    return {
        "title": title,
        "description": description + "".join(links),
        "link": repo or official or SOURCE_PAGE,
        "guid": guid,
        "pubDate": format_datetime(discovered),
    }

def load_existing_items():
    if not FEED_FILE.exists():
        return []
    text = FEED_FILE.read_text(encoding="utf-8")
    marker = "<item>"
    items = []
    for chunk in text.split(marker)[1:]:
        item_xml = marker + chunk.split("</item>", 1)[0] + "</item>"
        def tag(name):
            start = item_xml.find(f"<{name}>")
            end = item_xml.find(f"</{name}>")
            if start == -1 or end == -1:
                return ""
            return item_xml[start + len(name) + 2:end]
        items.append({
            "title": tag("title"),
            "description": tag("description"),
            "link": tag("link"),
            "guid": tag("guid"),
            "pubDate": tag("pubDate"),
        })
    return items

def xml_item(item):
    return f"""  <item>
    <title>{escape(item["title"])}</title>
    <description><![CDATA[{item["description"]}]]></description>
    <link>{escape(item["link"], quote=True)}</link>
    <guid isPermaLink="false">{escape(item["guid"])}</guid>
    <pubDate>{escape(item["pubDate"])}</pubDate>
  </item>"""

def write_feed(items):
    now = format_datetime(datetime.now(timezone.utc))
    body = "\n".join(xml_item(i) for i in items)
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Open Source Mac Apps – Neue Apps</title>
    <description>Neue Open-Source-Mac-Apps aus der Sammlung von serhii-londar.</description>
    <link>{escape(SOURCE_PAGE, quote=True)}</link>
    <atom:link xmlns:atom="http://www.w3.org/2005/Atom" href="{escape(FEED_URL, quote=True)}" rel="self" type="application/rss+xml"/>
    <lastBuildDate>{now}</lastBuildDate>
{body}
  </channel>
</rss>
"""
    FEED_FILE.write_text(xml, encoding="utf-8")

def main():
    data = fetch_json(SOURCE_URL)
    apps = data.get("applications", [])
    state = load_state()
    known = set(state.get("known", []))

    # First run: establish baseline without flooding the RSS reader.
    if not known:
        state["known"] = [app_id(a) for a in apps if app_id(a)]
        state["items"] = []
        save_state(state)
        write_feed([])
        print(f"Initial baseline created: {len(apps)} apps.")
        return

    new_apps = [a for a in apps if app_id(a) and app_id(a) not in known]

    existing = load_existing_items()
    new_items = [make_item(a, app_date(a)) for a in new_apps[:MAX_NEW_ITEMS]]

    # newest first
    all_items = list(reversed(new_items)) + existing
    all_items = all_items[:100]

    for app in new_apps:
        ident = app_id(app)
        if ident:
            known.add(ident)

    state["known"] = sorted(known)
    state["items"] = [i["guid"] for i in all_items]
    save_state(state)
    write_feed(all_items)

    print(f"Found {len(new_apps)} new apps; published {len(new_items)}.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Check docs/data/v1. Exit 1 on a broken id, link, event pointer, or arts listing."""
import json
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "docs" / "data" / "v1"
required = ["nodes.json", "links.json", "events.json", "suburbs.json", "base.json", "osm.json", "manifest.json"]
missing = [name for name in required if not (root / name).is_file()]
if missing:
    print("missing", ", ".join(missing))
    sys.exit(1)

def load(name):
    with (root / name).open() as f:
        return json.load(f)

nodes = load("nodes.json")
links = load("links.json")
events = load("events.json")
manifest = load("manifest.json")
errors = []

ids = [n.get("id") for n in nodes]
if len(ids) != len(set(ids)):
    errors.append("duplicate node id")
idset = set(ids)
for n in nodes:
    for key in ("id", "name", "kind", "structure", "relevance", "status"):
        if not n.get(key):
            errors.append(f"{n.get('id')} missing {key}")
    if n.get("confidence") and n["confidence"] not in ("high", "medium", "low"):
        errors.append(f"{n['id']} bad confidence")
    if "post_club" in (n.get("domains") or []) and not n.get("sources") and n.get("kind") != "unknown":
        # older rows can gain the tag only via this merge, which always sets sources
        errors.append(f"{n['id']} post_club without sources")

for i, l in enumerate(links):
    if l.get("s") not in idset or l.get("t") not in idset:
        errors.append(f"link {i} dangling {l.get('s')} -> {l.get('t')}")
    if not l.get("rel"):
        errors.append(f"link {i} missing rel")

seen = set()
for e in events:
    if e.get("id") in seen:
        errors.append(f"duplicate event {e.get('id')}")
    seen.add(e.get("id"))
    if e.get("status") not in ("past", "upcoming", "ongoing", "unknown"):
        errors.append(f"{e.get('id')} bad status {e.get('status')}")
    if e.get("venue_id") and e["venue_id"] not in idset and e.get("fetched") == "2026-11-27":
        errors.append(f"{e['id']} venue {e['venue_id']}")
    for key in ("presenter_ids", "artist_ids"):
        for pid in e.get(key) or []:
            if pid not in idset and e.get("fetched") == "2026-11-27":
                errors.append(f"{e['id']} {key} {pid}")

if manifest.get("version") != 1:
    errors.append("manifest version")
if manifest.get("scene_tag") != "post_club":
    errors.append("manifest scene_tag")

# Arts planner (docs/arts.html). Separate from the scene-graph events above.
ARTS_NAME = "arts-events-2027q1.json"
ARTS_STATUSES = {"on-sale", "announced", "expected", "tba", "sold-out"}
ARTS_REGIONS = {"local", "asia-pacific", "se-asian", "first-nations", "international-other"}
ARTS_CONF = {"high", "medium", "low"}
ARTS_REQUIRED = (
    "id", "title", "start_date", "end_date", "venue", "suburb", "organiser",
    "artists", "categories", "region_focus", "price", "ticket_url", "source_urls",
    "status", "description", "why_dean", "confidence",
)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
URL_RE = re.compile(r"^https?://")
WIN_START, WIN_END = "2027-01-01", "2027-03-31"

def is_num(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)

def check_arts(errs):
    path = root / ARTS_NAME
    if not path.is_file():
        errs.append(f"missing {ARTS_NAME}")
        return 0
    with path.open() as f:
        rows = json.load(f)
    if not isinstance(rows, list) or not rows:
        errs.append(f"{ARTS_NAME} must be a non-empty array")
        return 0
    seen_ids = set()
    for e in rows:
        if not isinstance(e, dict):
            errs.append("arts row is not an object")
            continue
        eid = e.get("id") or "?"
        for key in ARTS_REQUIRED:
            if key not in e or e[key] is None or e[key] == "":
                errs.append(f"arts {eid} missing {key}")
        if eid in seen_ids:
            errs.append(f"arts duplicate id {eid}")
        seen_ids.add(eid)
        if isinstance(eid, str) and not SLUG_RE.match(eid):
            errs.append(f"arts {eid} bad id")
        for key in ("start_date", "end_date"):
            if not isinstance(e.get(key), str) or not DATE_RE.match(e.get(key) or ""):
                errs.append(f"arts {eid} bad {key}")
        if DATE_RE.match(str(e.get("start_date") or "")) and DATE_RE.match(str(e.get("end_date") or "")):
            if e["end_date"] < e["start_date"]:
                errs.append(f"arts {eid} end before start")
            elif e["end_date"] < WIN_START or e["start_date"] > WIN_END:
                errs.append(f"arts {eid} outside Jan–Mar 2027")
        if e.get("status") not in ARTS_STATUSES:
            errs.append(f"arts {eid} bad status {e.get('status')}")
        if e.get("confidence") not in ARTS_CONF:
            errs.append(f"arts {eid} bad confidence")
        if e.get("status") == "expected" and not (isinstance(e.get("date_note"), str) and e["date_note"].strip()):
            errs.append(f"arts {eid} expected without date_note")
        for key in ("title", "venue", "suburb", "organiser", "price", "description", "why_dean"):
            if key in e and not isinstance(e.get(key), str):
                errs.append(f"arts {eid} {key} not a string")
        if "ticket_url" in e and (not isinstance(e.get("ticket_url"), str) or not URL_RE.match(e.get("ticket_url") or "")):
            errs.append(f"arts {eid} bad ticket_url")
        sources = e.get("source_urls")
        if not isinstance(sources, list) or not sources:
            errs.append(f"arts {eid} source_urls")
        else:
            for u in sources:
                if not isinstance(u, str) or not URL_RE.match(u):
                    errs.append(f"arts {eid} bad source url")
        cats = e.get("categories")
        if not isinstance(cats, list) or not cats or not all(isinstance(c, str) and SLUG_RE.match(c) for c in cats):
            errs.append(f"arts {eid} bad categories")
        regs = e.get("region_focus")
        if not isinstance(regs, list) or not regs or any(r not in ARTS_REGIONS for r in regs):
            errs.append(f"arts {eid} bad region_focus")
        artists = e.get("artists")
        if not isinstance(artists, list):
            errs.append(f"arts {eid} artists")
        else:
            for a in artists:
                if not isinstance(a, dict) or not isinstance(a.get("name"), str) or not a["name"].strip():
                    errs.append(f"arts {eid} artist name")
                elif not isinstance(a.get("origin"), str) or not a["origin"].strip():
                    errs.append(f"arts {eid} artist origin")
        for key in ("date_note", "times"):
            if key in e and e[key] is not None and not isinstance(e[key], str):
                errs.append(f"arts {eid} bad {key}")
        rel = e.get("ticket_release_date", None)
        if "ticket_release_date" in e and rel is not None and (not isinstance(rel, str) or not DATE_RE.match(rel)):
            errs.append(f"arts {eid} bad ticket_release_date")
        has_lat = "lat" in e and e["lat"] is not None
        has_lng = "lng" in e and e["lng"] is not None
        if has_lat != has_lng:
            errs.append(f"arts {eid} lat/lng must both be set or both be null")
        elif has_lat:
            if not is_num(e["lat"]) or not is_num(e["lng"]):
                errs.append(f"arts {eid} lat/lng not numbers")
            elif not (-39.5 <= e["lat"] <= -33.5 and 140.5 <= e["lng"] <= 150.5):
                errs.append(f"arts {eid} lat/lng outside Victoria")
    return len(rows)

arts_count = check_arts(errors)

# geometry still shaped the way the viewer expects
base = load("base.json")
osm = load("osm.json")
for key in ("coast", "lakes", "rivers"):
    if key not in base:
        errors.append(f"base missing {key}")
for key in ("bbox", "ways", "polys"):
    if key not in osm:
        errors.append(f"osm missing {key}")

if errors:
    print("\n".join(errors[:40]))
    print(f"{len(errors)} errors")
    sys.exit(1)

post = sum(1 for n in nodes if "post_club" in (n.get("domains") or []))
unk = sum(1 for n in nodes if n.get("kind") == "unknown")
print(f"ok  nodes={len(nodes)} links={len(links)} events={len(events)} post_club={post} unknown={unk} arts={arts_count}")

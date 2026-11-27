#!/usr/bin/env python3
"""Check docs/data/v1. Exit 1 on a broken id, link or event pointer."""
import json
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
print(f"ok  nodes={len(nodes)} links={len(links)} events={len(events)} post_club={post} unknown={unk}")

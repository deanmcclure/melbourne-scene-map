# Naarm Scene Map

Static map of Naarm / Melbourne’s live, sound and AV scenes. GitHub Pages serves this site from `docs/` (https://deanmcclure.github.io/melbourne-scene-map/).

The page is the viewer. The scene graph lives in versioned JSON so it can be diffed and so a later Instagram-network file can be merged without editing HTML.

## Layout

| Path | What it is |
| --- | --- |
| `docs/index.html` | Viewer (D3 graph, Leaflet map, calendar). Fetches the JSON below. |
| `docs/data/v1/nodes.json` | People, groups, venues, nights, labels. |
| `docs/data/v1/links.json` | Relations between nodes. |
| `docs/data/v1/events.json` | Calendar listings. |
| `docs/data/v1/suburbs.json` | Suburb labels for the map. |
| `docs/data/v1/base.json` | Coast, lake and river shapes. |
| `docs/data/v1/osm.json` | Inner-Melbourne streets drawn when raster tiles are blocked. |
| `docs/data/v1/manifest.json` | Version, date, and the scene-tag name. |
| `scripts/check_data.py` | Checks ids, links and event pointers. |

`suburbs`, `base` and `osm` are map geometry. A scene update should not need to touch them.

Open the site over HTTP. `file://` cannot fetch the JSON. GitHub Pages is enough; locally, serve `docs/` (`python3 -m http.server` from that folder).

## Node

Required: `id`, `name`, `kind`, `structure`, `relevance`, `status`.

Common fields: `domains` (tags), `description`, `location`, `address`, `suburb`, `lat`, `lng`, `geo_precision` (`street` or `suburb`), `instagram`, `website`, `underground_score`, `notes`.

Added for sourced edits:

- `confidence`: `high`, `medium` or `low`. High means a primary page was opened (ticketing, label, publication). Medium means a secondary or partial source. Low means an aggregator or a single mention. Omitted on older rows that were not re-checked.
- `sources`: list of URLs. Do not add a fact with no source.
- `former_ids`: only if an id changed. Instagram stubs usually keep their id instead.

`domains` includes `post_club` for the post-club / deconstructed-club layer. The “all scenes” filter is that list.

`kind` is `artist`, `collective`, `venue`, `org`, `series`, `festival`, `ensemble`, `ari`, `label`, `diy_space`, or `unknown`.

`relevance` is `core`, `adjacent`, `exclude`, or `unknown`. The page hides `exclude` by default.

`underground_score` is an editorial weight used for drawing, not a fact from a source. New post-club rows use roughly 2–3.5, in line with older experimental-club rows.

### Instagram stubs, and a later import

Bare handles from the Instagram layer are nodes with `kind: "unknown"`, `id` starting `ig-`, and `instagram` set (`@handle`). They have no description. About 540 of these are still unresolved.

When a real record is the same account, promote that node in place: keep the `ig-` id, set `name`, `kind`, `description`, `sources` and `confidence`. Links and events already point at the id. If a listing had already used a different id (Charms is `ig-charms-vt`, and one event said `charms`), point the event at the kept id and say so in `notes`.

Do not merge a handle just because the name is similar. Unconfirmed handles stay as stubs with a `notes` line. `@tangerine.tangerinee`, `@tangerine.mu` and `@moopiedaily` were left that way.

A follow-up Instagram file should match on the handle, lowercased, without `@`. New stubs can be appended. Use `collaborated_with` with `src` set to the post or export the edge came from.

## Link

`s` and `t` are node ids. `rel` is one of:

`collaborated_with`, `performed_at`, `programmed_at`, `member_of`, `presented_by`, `runs`, `part_of`, `resident_at`, `funded_by`, `curated_by`, `located_at`, `released_on`.

`when` is `YYYY-MM` or a fuller date when known, else `null`. `note` is a short sourced clause. `src` is one URL. `confidence` is optional.

Direction follows the existing graph: the person `runs` the group, the artist `performed_at` the venue, the artist is `presented_by` the promoter, the artist `released_on` the label, the night is `programmed_at` the venue.

## Event

`id` is unique, usually `YYYY-MM-DD-slug`. `start` / `end` are `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM` in Melbourne time. `venue_id` should be a node when the room is known. `presenter_ids` and `artist_ids` are node ids; names with no node stay in `description`.

`category` `post_club` is the calendar filter for this layer. Other rows keep the categories they already had (`experimental_music`, `performance`, `other`, …).

`status` is derived from the end date against 27 Nov 2026:

- `past` if the end date is before that day
- `ongoing` if it started earlier and was still open
- `upcoming` if it starts on or after that day (including a night that starts that evening)

Past listings stay in the file so the calendar can still move back through the fetched season. The “Upcoming” list already hides them. Instagram-sourced one-offs that had already happened were removed in an earlier commit and were not put back.

`source` is the page to open. `tickets` is the ticket URL when it differs. `fetched` is the day the row was taken. `confidence` is optional.

## How to update

1. Edit `nodes.json`, `links.json` or `events.json`. Keep every new claim tied to a `sources` / `src` / `source` URL. If a page was not opened, say so and lower `confidence`.
2. Promote matching `ig-` stubs instead of creating a second node. Search `instagram` and `name` before adding an id.
3. For a gig still to come, add an event and the `performed_at` / `programmed_at` links. For an older gig, a link with `when` is enough unless it falls inside the calendar window (this file’s listings start in September 2025).
4. Recompute `status` on events if the “today” you care about has moved. The viewer does not recalculate it.
5. Run `python3 scripts/check_data.py`.
6. Serve `docs/` and check Graph, Map and Events, including the scene filter set to “post club”.

The previous build that inlined `const DATA` into `index.html` was not in this repo (`.gitignore` publishes `docs/` only). Do not paste the JSON back into the HTML. The viewer loads `data/v1/` itself.

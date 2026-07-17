---
name: onsite-meta-images-extraction-multica
description: Uses Screaming Frog through a saved crawl, local headless CLI, Multica MCP connection, or existing CSV exports, then fills the meta tags + images portion of the FirstPage Onsite Checklist - items 17.x-20.x (page titles, meta descriptions, H1s, image alt text, oversized images). Use this skill whenever the user gives a site URL, sitemap, saved Screaming Frog crawl, or export folder and asks for a meta tag audit or checklist tabs 17, 18, 19, or 20. Covers ONLY items 17.x-20.x.
---

# Meta Tags + Images Extraction (Onsite Checklist items 17.x-20.x)

Gets crawl data from Screaming Frog, applies FirstPage house thresholds, and writes a checklist
`.xlsx` in the standard tab format with `✔`/`✖` marks on the `SEO Implementation Checklist`
tab. In Multica, Screaming Frog MCP is an optional way to obtain the crawl exports; it does not
replace the validated Python extraction and workbook logic.

**Scope: items 17.x-20.x only.** Everything else on the checklist is out of scope and is
left blank for a separate skill or a human.

---

## Four input routes

**A. From a crawl the user already ran (PREFERRED).** They crawl in the GUI as normal and save it
with `File > Save`. Ask them to provide the resulting Screaming Frog crawl file:

- **`.dbseospider`** — preferred; produced when Screaming Frog uses database storage mode.
- **`.seospider`** — also accepted; produced when Screaming Frog uses memory storage mode.

This is the raw saved crawl, not a `.seospiderconfig` settings file and not a CSV export. The
skill exports from that crawl file using its existing settings and crawl analysis. No config
file is needed, and the user can keep the crawl open while the skill works. Loading from a file
path works even while a crawl is open in the GUI — they do **not** need to close anything.

**B. Crawl through Screaming Frog MCP (Multica).** Use the connected `screaming-frog` MCP tools
to set the supplied sitemap under `Crawl These Sitemaps`, run a Spider-mode crawl and crawl
analysis, and export the exact CSV reports listed in *MCP export contract* below.
Then run the bundled Python script with `--exports-dir`. MCP is only the crawl/export transport;
do not ask an LLM to recreate Screaming Frog's filters or the workbook rules. This route is
conditional until tested inside Multica with the MCP server connected.

**C. Crawl from scratch with the local CLI.** The Python script starts Screaming Frog headlessly
in **Spider mode** from the website URL. It never uses `--crawl-sitemap`, because that creates a
List-mode crawl. Nothing appears on screen. The crawl is saved to SF's database as
`client - date` so it can be opened afterwards. **Uses Screaming Frog's defaults unless
`--config` is supplied** — see *Config* below. This route is for a website-only crawl and does
**not** conduct a full sitemap audit because the CLI cannot inject a client-specific URL into
`Crawl These Sitemaps`.

**D. From existing CSV exports.** If the user already has a complete Screaming Frog export
folder, run the Python script with `--exports-dir`. This performs no crawl and is also the route
used after MCP has produced the exports.

## Picking a route — infer, don't interrogate

Take what the user already gave you:

- They named a `.dbseospider` file, or said "my crawl" / "the crawl I just ran" -> **route A**.
- They gave an existing CSV export folder -> **route D**.
- They gave a URL plus a sitemap and the Screaming Frog MCP tools can set `Crawl These Sitemaps`
  and run crawl analysis -> **route B**.
- They gave a URL plus a sitemap but capable MCP tools are unavailable -> ask for a saved crawl
  configured with that sitemap (**route A**). Do not silently downgrade to route C.
- They gave only a website URL -> **route C** is allowed. Explain that it is a website-only
  headless crawl, not a full sitemap audit.
- They gave nothing -> ask whether they have a saved crawl, and if not, ask for the URL/sitemap.

Do not present both routes as a menu when the answer is already implied. Ask only for what is
genuinely missing.

## Inputs

1. **A saved `.dbseospider` or `.seospider` crawl file** (route A), **start URL + sitemap URL** (route B), **start URL**
   (route C), or **CSV export
   folder** (route D)
2. **Client name** — used in the output filename (required)
3. **Output folder** — where the .xlsx goes (defaults to the current directory)
4. **Config path** (optional for route C; route B may configure the crawl through MCP)

The template defaults to the copy bundled in this skill's `template/` folder. Only pass
`--template` to override it.

**Warn before overwriting.** The output filename is `Onsite Checklist - <client> - <date>.xlsx`.
A second run on the same day for the same client silently replaces the first. Check whether the
file exists and say so.

---

## Prerequisites

- **Screaming Frog must be installed and licensed wherever crawling is performed.** The local
  headless CLI does not run on the free version. For MCP, the MCP server must have access to a
  working licensed Screaming Frog installation or service.
- Screaming Frog does **not** need to be open — the script launches its own headless instance,
  which runs fine alongside a GUI window.
- `openpyxl` must be installed (`pip3 install openpyxl`).
- **Route C is macOS only.** The local Screaming Frog binary path is hardcoded. Routes B and D
  are not tied to that binary path.

For Multica, configure the MCP server in the agent settings. Strict JSON must not contain a
trailing comma:

```json
{
  "mcpServers": {
    "screaming-frog": {
      "type": "http",
      "url": "http://127.0.0.1:11435/mcp"
    }
  }
}
```

`127.0.0.1` means the machine or container running the Multica agent. Do not assume it points to
the user's laptop. Before choosing route B, confirm that the MCP tools are actually available.

## MCP export contract

MCP server implementations can expose different tool names. Inspect the connected tools at
runtime; do not invent a tool call. Route B is usable only if the available MCP tools can crawl
or open a crawl and write or return all of these Screaming Frog-native reports. For a full
sitemap audit, it must also be able to:

1. Keep the crawl in Spider mode.
2. Enable `Crawl Linked XML Sitemaps`.
3. Enable `Crawl These Sitemaps` and insert the exact sitemap URL supplied by the user.
4. Run post-crawl analysis so Screaming Frog's sitemap filters and issues are populated.

If any of those controls are unavailable, route B is not a valid full sitemap audit; request a
saved crawl instead.

**Export tabs:**

```text
Page Titles:All
Page Titles:Missing
Page Titles:Duplicate
Page Titles:Multiple
Meta Description:All
Meta Description:Missing
Meta Description:Duplicate
H1:All
H1:Missing
H1:Duplicate
H1:Multiple
Images:All
```

**Bulk exports:**

```text
Images:Images Missing Alt Attribute & Text Inlinks
Images:All Image Inlinks
```

The reports must be saved together as CSV files in a directory readable by the Python runtime.
Preserve Screaming Frog's headers and native filtered exports. Do not substitute a generic page
scrape, MCP summary, JSON issue list, or a recomputed duplicate report.

After the MCP export finishes:

1. Confirm `Page Titles:All` contains data rows. Header-only files mean the crawl failed.
2. Confirm all required reports are present. Empty issue reports are valid, but missing reports
   are not.
3. Run the Python build step with `--exports-dir`.
4. If the MCP server cannot provide the full contract, explain the limitation and use route A,
   C, or D instead. Never create a falsely clean workbook from incomplete MCP data.

---

## Running it

**Route A — from a saved crawl (preferred):**
```bash
python3 <skill-directory>/scripts/onsite_checklist.py \
  --crawl-file "/path/to/client-crawl.dbseospider" \
  --client "clientname" \
  --out-dir "/path/to/client/03_reports"
```
Seconds, not minutes — no crawling.

**Route B — after MCP crawl/export:**
```bash
python3 <skill-directory>/scripts/onsite_checklist.py \
  --exports-dir "/absolute/path/to/mcp-csv-exports" \
  --client "clientname" \
  --out-dir "/absolute/path/to/reports"
```

**Route C — local headless crawl from scratch:**
```bash
python3 <skill-directory>/scripts/onsite_checklist.py \
  --url "https://example.com/" \
  --client "clientname" \
  --config "/path/to/house.seospiderconfig" \
  --out-dir "/path/to/client/03_reports"
```
Route C saves the crawl to SF's database named `client - date`, so it can be opened in the GUI
afterwards in Spider mode. It is a website-only crawl. Do not pass a sitemap to this route; the
script refuses the run rather than presenting an incomplete sitemap audit as complete.

A ~600 URL site takes about 4 minutes to crawl.

**Route D — from existing CSV exports:** use the same command as route B, pointing
`--exports-dir` at the user's export folder.

Useful flags:

- `--exports-dir <dir>` — rebuild the spreadsheet from existing CSVs, no re-crawl. Use this
  when iterating on output format so you don't wait on a crawl each time.
- `--date YYYYMMDD` — override the filename date.
- `--keep-template-ticks` — leave the template's default `✔` on unverified items (default is to blank them).

After it runs, **read the output file back and verify** the counts match what the script
reported. Report the per-item table to the user.

---

## Config — route C only

Without `--config`, a from-scratch crawl uses Screaming Frog's own defaults, which are **not**
the user's GUI settings. Measured on cheersmaid.com.hk 2026-07-16: GUI crawl 602 URLs, headless
defaults 562. H1 Missing went 1 -> 0, flipping that item from `✖` to `✔`. Nothing errors; the
numbers are just quietly wrong.

This is why **route A is preferred** — a saved crawl carries the settings it was run with, so
the question never arises.

For route C, pass `--config`. To create one: `File > Configuration > Save As…` in Screaming Frog.
Even with a config, this skill treats route C as website-only because it cannot safely insert a
different sitemap per client. Use route A or capable MCP tools for a full sitemap audit.

Validation, 2026-07-16: route A against the user's own 602-URL crawl reproduced a hand-built
deliverable exactly on all 12 items (0/8/42/0, 32/4/68, 1/10/4, 30).

---

## House thresholds

Set in the script, **not** in Screaming Frog's config, so a stale GUI setting can never
silently change the numbers.

| Item | Threshold |
|---|---|
| 17.3 Page titles Too Long | **> 580 px** (per the 17.3 tab header) |
| 18.3 Descriptions Too Long | **> 880 px** (per the 18.3 tab note, "mobile max") |
| 20.2 Image Oversize | **> 200 kB** |

Pixels, not characters — this is a deliberate house choice, since pixel width is what governs
SERP truncation. Note the template's 18.3 question text still says "155 character maximum",
which contradicts its own tab note; 880 px is correct.

kB is treated as 1024 bytes. Screaming Frog's convention is unconfirmed — only affects images
within ~4.8 kB of the cutoff.

---

## Extraction rules (each one exists because of a real bug)

**Use Screaming Frog's native filters. Do not recompute.** Rebuilding "duplicate" logic on top
of the `All` export produced 16 rows where SF's own filter said 8 — it silently included
noindex pages and paginated children. SF excludes any page carrying `rel="prev"` from duplicate
detection, and excludes non-indexable pages. Only drop to `All` where a house threshold has no
matching filter (17.3, 18.3, 20.2), and filter to indexable-only when you do.

**19.2 H1 Duplicate drops PURE same-page collisions only.** SF's H1 `Duplicate` filter also
flags pages where `H1-1 == H1-2` on the same page. Drop such a row **only if that H1-1 value is
unique in the duplicate set** — a page can repeat its H1 on-page AND share that H1-1 with other
pages (crefit `/clearcardcredit/`, H1-1 "健康貸度 由你掌控" on 4 pages), which is a real
cross-page duplicate and must stay. Dropping every `H1-1 == H1-2` row (the original rule) wrongly
removed those: crefit gave 6 when the answer is 8. Do NOT instead group `h1_all` by H1-1 — that
pulls in noindex pages SF's filter omits and inflated cheersmaid from 10 to 24. Keep SF's
Duplicate as the base; only refine the drop.

**20.2 reads size straight from `All Image Inlinks`.** That bulk export carries a `Size (Bytes)`
column on every row, INCLUDING external-domain images, so read size from the inlink row and apply
the kB cutoff in code. Do NOT join to `Images:All` for size (an earlier version did) — `Images:All`
is internal-only, so the join silently dropped every external-CDN image. Do NOT use
`Images Over X kB Inlinks` either — its X comes from SF config, not our threshold. Sorted by size,
largest first.

**20.1 uses the combined export** (`Images Missing Alt Attribute & Text Inlinks`), matching the
established manual method. Caveat worth footnoting for the client: it includes `alt=""` images,
which are correct markup for decorative images, so the count overstates the real problem.

**Images marked `?` mean "not judged", not "clean".** Column D uses a third state for image
items, and the script prints why:
- **No images captured at all** (every image export empty) -> 20.1 AND 20.2 = `?`. The crawl ran
  without image crawling, or without JS rendering on a JS-loaded site. Never mark these `✔`.
- **Images found but no size data** -> 20.1 is valid, 20.2 = `?`. The site serves images from an
  external CDN (Prismic, Cloudinary...), which SF lists *outside* `Images:All`, so alt text is
  known but byte size isn't. Measured on crefit: `Images:All` empty, yet 17 missing-alt images on
  `prismic.io`. Do NOT use `Images:All` alone to decide whether images exist — check every image
  export.

When you see either, tell the user the item needs a re-crawl with image/external settings on,
rather than reporting it as passed.

**Rows are not issues.** 30 alt rows on cheersmaid were only 2 unique images repeated across
16 pages. Say so when reporting, or the client reads 30 fixes where there are 2.

---

## Deliverable format

- Rows 1-2 metadata, **row 3 headers, data from row 4**. Never touch rows 1-3.
- Column layouts vary per tab — the script's `TABS` map holds them.
- 17.2 / 18.2 / 19.2 group duplicates together, biggest group first. 17.3 / 18.3 sort by pixel
  width descending.
- Leave `New Title`, `Revised Title`, `Instructions`, `Remarks` **blank** — that's optimisation
  work, not extraction.
- `SEO Implementation Checklist` column D: `✔` = no issue, `✖` = issue found. Located by column B
  value at runtime, not hardcoded, because rows shift as the template gains items.
- **The template ships `✔` pre-filled on every item.** The script blanks all of them, then marks
  only the 12 it verified. Otherwise the file claims a clean pass on checks nobody ran.
- Empty tab + `✔` is the correct output for an item with no issues.

---

## Known quirks

- **`--output-folder` must be absolute.** The launcher resets cwd to the app bundle, so a
  relative path tries to write into `/Applications` and dies with a misleading
  `Operation not permitted`.
- **`--load-crawl` by database ID fails if that crawl is open in the GUI**
  (`Crawl is open in another SEO Spider instance`). **Loading a saved `.dbseospider` FILE does
  not** — tested 2026-07-16 with the crawl open in the GUI, exported 602 URLs fine. The script
  only ever loads by file path, so route A works with the GUI open. Never tell the user to close
  their crawl first.
- **A failed crawl still writes header-only CSVs**, which would otherwise produce an all-`✔`
  deliverable for a site nobody crawled. The script hard-exits if `Page Titles:All` is empty.
  Do not remove that guard.
- The CLI's filter names are generic (`Page Titles:Over X Pixels`) — X comes from config. Another
  reason thresholds live in code.

---

## Reporting back

Give the per-item table (item, rows, mark), then flag:

- Anything where rows are concentrated in few unique assets (see *Rows are not issues*).
- Standouts worth naming — e.g. an 18.2 MB image, or a title at 1111 px against a 580 budget.
- That the other ~47 checklist items are deliberately blank and still need doing.

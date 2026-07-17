# onsite-meta-images-extraction-multica

Fills the **meta tags + images** part of the Onsite Checklist (items 17.x–20.x) from Screaming
Frog data and writes the `.xlsx`. This Multica edition supports four input routes:

1. A saved Screaming Frog crawl (`.dbseospider` preferred; `.seospider` also accepted).
2. A crawl/export through a connected Screaming Frog MCP server.
3. A local background crawl through the Screaming Frog CLI.
4. An existing folder of Screaming Frog CSV exports.

Scope is 17.x–20.x **only** — page titles, meta descriptions, H1s, image alt text, oversized
images. The other ~47 checklist items are left blank.

---

## Multica MCP configuration

Add this to the Multica agent configuration:

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

The MCP server is optional. `127.0.0.1` refers to the machine or container running the agent,
so that runtime must actually host or be able to reach the Screaming Frog MCP service.

The skill checks the connected MCP tools at runtime. MCP is used only when it can produce all
required native Screaming Frog CSV reports. The Python script then processes those exports with
the same validated audit and workbook rules as the other routes.

## Local prerequisites

**Screaming Frog, licensed.** Headless mode does not work on the free version. Nothing here
works without it.

**Python + openpyxl:**
```bash
pip3 install openpyxl
```

The direct CLI route is macOS-only because the Screaming Frog path is hardcoded. MCP and
existing-export processing are not tied to that application path.

---

## Route A: Recommended saved crawl

**Crawl in Screaming Frog exactly as you always do**, then save the crawl (`File > Save`).
Provide the resulting **`.dbseospider`** file, or a **`.seospider`** file if Screaming Frog is
using memory storage mode. Do not provide a `.seospiderconfig` file here; that contains crawl
settings rather than the saved crawl data.
Then in Claude Code:

> run the meta tags and images extraction for xyz using my crawl at
> ~/clients/xyz/01_source/xyz.dbseospider, save it to ~/clients/xyz/03_reports

Takes seconds — no re-crawling. You keep your crawl open in the GUI to work through, and the
deliverable is built from **your** crawl with **your** settings.

Or directly:
```bash
python3 <skill-directory>/scripts/onsite_checklist.py \
  --crawl-file ~/clients/xyz/01_source/xyz.dbseospider \
  --client "xyz" \
  --out-dir ~/clients/xyz/03_reports
```

The template is bundled in `template/`, so you don't need to supply one.

---

## Route B: MCP full audit

When a sitemap URL is provided, the MCP tools must keep Screaming Frog in Spider mode, insert
the exact URL under `Crawl These Sitemaps`, and run post-crawl analysis. This route cannot be
tested in an environment where the Screaming Frog MCP tools are not connected. If those tools
cannot control the required settings, use a properly configured saved crawl instead.

After MCP writes the required CSV reports, run:

```bash
python3 <skill-directory>/scripts/onsite_checklist.py \
  --exports-dir "/absolute/path/to/sf-exports" \
  --client "xyz" \
  --out-dir "/absolute/path/to/reports"
```

## Route C: Direct background crawl

This route always opens as **Spider mode** in Screaming Frog. The script starts from the website
URL and never uses `--crawl-sitemap`, which would create a List-mode crawl. It is deliberately a
website-only crawl and does not claim to perform a full sitemap audit.

```bash
python3 <skill-directory>/scripts/onsite_checklist.py \
  --url "https://xyz.com/" \
  --client "xyz" --config /path/to/your.seospiderconfig \
  --out-dir ~/clients/xyz/03_reports
```

~4 minutes for a 600-URL site. Your Screaming Frog window can stay open — this runs a separate
headless instance and won't touch it. The crawl is saved to your database as `client - date`,
so you can open it in the GUI afterwards.

**The catch:** without `--config`, Screaming Frog uses its own defaults, **not** your settings.
Measured on cheersmaid.com.hk (2026-07-16): GUI crawl 602 URLs, headless defaults 562. H1
Missing went from 1 to 0 — the item flipped from ✖ to ✔. Nothing errored. The number was just
quietly wrong.

To fix: `File > Configuration > Save As…` and pass `--config`. **Or use your own saved
crawl through the recommended route and skip the problem entirely.**

When a sitemap audit is required, use a saved crawl configured with the exact sitemap under
`Crawl These Sitemaps`, or use MCP tools that can set that field and run post-crawl analysis.
The script rejects `--sitemap` on the local headless route instead of silently producing an
incomplete audit.

## Route D: Existing CSV exports

When complete Screaming Frog CSV exports already exist, run:

```bash
python3 <skill-directory>/scripts/onsite_checklist.py \
  --exports-dir "/absolute/path/to/sf-exports" \
  --client "xyz" \
  --out-dir "/absolute/path/to/reports"
```

See `SKILL.md` for the exact MCP export contract. A generic scrape or an MCP-generated summary
is not sufficient because the checklist relies on Screaming Frog's native filtered reports.

---

## What it does and doesn't decide

Fills the factual columns: Address, Title, Pixel Width, Source, Destination, Size.

Leaves `New Title`, `Revised Title`, `Instructions` and `Remarks` **blank** — that's the
optimisation work, and it's yours.

**Rows are not issues.** On cheersmaid, 30 alt-text rows turned out to be 2 unique images
repeated across 16 pages. Check unique assets before telling a client they have 30 fixes.

---

## House thresholds (in the script, deliberately)

| Item | Threshold |
|---|---|
| 17.3 Titles Too Long | > 580 px |
| 18.3 Descriptions Too Long | > 880 px |
| 20.2 Images Oversize | > 200 kB |

Pixels, not characters — pixel width is what governs SERP truncation. They live in the script
rather than Screaming Frog's config so a stale GUI setting can't silently change your results.

---

## If something looks wrong

- **`Operation not permitted` writing a CSV** — `--out-dir` must be an absolute path.
- **`Crawl is open in another SEO Spider instance`** — you should never see this. Loading a
  saved `.dbseospider` file works fine with that crawl open in your GUI; only loading by
  database ID hits the lock, and the script doesn't do that. You do **not** need to close
  anything in Screaming Frog to use `--crawl-file`.
- **Every item comes back ✔** — the script hard-exits if the crawl returned no pages, so this
  should be impossible. If you ever see it, stop and report it rather than sending the file.
- **A tab is blank but shouldn't be** — check the template hasn't had its row-3 headers renamed.

Useful while debugging: `--exports-dir <folder>` rebuilds the spreadsheet from CSVs already
exported, skipping the crawl entirely.

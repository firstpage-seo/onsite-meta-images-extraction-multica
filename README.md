# onsite-meta-images-extraction-multica

Fills or refreshes the **meta tags + images** part of the SEO or SEO/GEO Onsite Checklist
(items 17.1–20.2) from Screaming Frog data. It supports:

- **Begin Onsite:** build from the matching blank template.
- **Review Onsite:** update a previous completed onsite while preserving unrelated work and
  human annotations on persistent issues.

Four crawl input routes are available:

1. A saved Screaming Frog crawl (`.dbseospider` preferred; `.seospider` also accepted).
2. A crawl/export through a connected Screaming Frog MCP server.
3. A local background crawl through the Screaming Frog CLI.
4. An existing folder of Screaming Frog CSV exports.

SEO/GEO item 20.3 is deliberately unverified.

## Required opening questions

Before execution, ask and confirm:

1. SEO or SEO/GEO?
2. Begin Onsite or Review Onsite?
3. Canonical GitHub template for Begin, or previous completed workbook for Review.
4. Current crawl source, client name, and output destination.

See `MULTICA_AGENT_INSTRUCTIONS.md` for ready-to-paste agent-level instructions.

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

**Screaming Frog, licensed.** Required for saved-crawl, MCP, and local crawl routes. Existing
CSV exports can be processed without launching Screaming Frog.

**Python dependencies:**
```bash
pip3 install -r requirements.txt
```

The direct CLI route is macOS-only because the Screaming Frog path is hardcoded. MCP and
existing-export processing are not tied to that application path.

## Templates in Multica

Multica may omit binary `.xlsx` files when it imports this skill from GitHub. Begin mode no
longer depends on those files being included in the imported skill: after SEO or SEO/GEO is
selected, the script downloads the matching canonical template directly from this repository.

The download is restricted to HTTPS links under
`firstpage-seo/onsite-meta-images-extraction-multica`, capped at 5 MB, checked for an XLSX ZIP
signature, and checksum-verified for the canonical templates. The workbook is also checked
against the selected checklist family before it is used.

An attached local template remains supported with `--template` and takes precedence. An
alternative version in the approved repository can be supplied with `--template-url`. Review
mode never downloads a blank template; it requires the previous completed onsite workbook.

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
  --checklist-type seo \
  --mode begin \
  --out-dir ~/clients/xyz/03_reports
```

For Review, replace `--mode begin` with:

```text
--mode review --previous-workbook /path/to/previous-onsite.xlsx
```

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
  --checklist-type seo_geo \
  --mode begin \
  --out-dir "/absolute/path/to/reports"
```

## Route C: Direct background crawl

This route always opens as **Spider mode** in Screaming Frog. The script starts from the website
URL and never uses `--crawl-sitemap`, which would create a List-mode crawl. It is deliberately a
website-only crawl and does not claim to perform a full sitemap audit.

```bash
python3 <skill-directory>/scripts/onsite_checklist.py \
  --url "https://xyz.com/" \
  --client "xyz" \
  --checklist-type seo \
  --mode begin \
  --config /path/to/your.seospiderconfig \
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
  --checklist-type seo \
  --mode review \
  --previous-workbook "/path/to/previous-onsite.xlsx" \
  --out-dir "/absolute/path/to/reports"
```

See `SKILL.md` for the exact MCP export contract. A generic scrape or an MCP-generated summary
is not sufficient because the checklist relies on Screaming Frog's native filtered reports.

---

## What it does and doesn't decide

Fills the factual columns: Address, Title, Pixel Width, Source, Destination, Size.

Begin leaves `New Title`, `Revised Title`, `Instructions` and `Remarks` blank. Review preserves
those fields for persistent issues, removes resolved rows, adds current issues, and unhides tabs
that now contain issues.

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

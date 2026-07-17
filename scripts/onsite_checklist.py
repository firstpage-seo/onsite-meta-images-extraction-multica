#!/usr/bin/env python3
"""
Crawl a site with Screaming Frog (headless CLI) and produce the FirstPage
Onsite Checklist deliverable for items 17.x-20.x.

Two phases, independently runnable:
  crawl  -> Screaming Frog CLI writes CSV exports to a folder
  build  -> read those CSVs, apply house thresholds, write the .xlsx

Use --exports-dir to rebuild from an existing export folder without re-crawling.
"""

import argparse
import collections
import copy
import csv
import datetime
import glob
import os
import shutil
import subprocess
import sys

import openpyxl

SF_BIN = "/Applications/Screaming Frog SEO Spider.app/Contents/MacOS/ScreamingFrogSEOSpiderLauncher"

# ---- House thresholds. These live here, NOT in Screaming Frog's config, so a
# ---- stale GUI setting can never silently change the numbers.
TITLE_PX = 580          # 17.3  (per checklist tab header)
DESC_PX = 880           # 18.3  (per tab note: Config > Spider > Preferences > 880 mobile max)
IMG_KB = 200            # 20.2
KB = 1024               # SF's kB convention is unconfirmed (1000 vs 1024); 100kB export's
                        # smallest row was 102876 bytes, which exceeds both. Affects only
                        # images within ~4.8KB of the cutoff.

EXPORT_TABS = [
    "Page Titles:All", "Page Titles:Missing", "Page Titles:Duplicate", "Page Titles:Multiple",
    "Meta Description:All", "Meta Description:Missing", "Meta Description:Duplicate",
    "H1:All", "H1:Missing", "H1:Duplicate", "H1:Multiple",
    "Images:All",
]
BULK_EXPORTS = [
    "Images:Images Missing Alt Attribute & Text Inlinks",
    "Images:All Image Inlinks",
]


# --------------------------------------------------------------------------- crawl

def run_crawl(url, sitemap, outdir, config=None, client=None, date=None, crawl_file=None):
    outdir = os.path.abspath(outdir)          # MUST be absolute: the launcher resets cwd to
    os.makedirs(outdir, exist_ok=True)        # the app bundle, so relative paths hit /Applications
    if not os.path.exists(SF_BIN):
        sys.exit(f"Screaming Frog not found at {SF_BIN}")

    cmd = [SF_BIN, "--headless"]

    if crawl_file:
        # Export from a crawl the user already ran in the GUI. Their settings, their crawl
        # analysis, no config file needed. Loading from a FILE path works even when a crawl
        # is open in the GUI; loading by database ID does not.
        cmd += ["--load-crawl", os.path.abspath(crawl_file)]
        print(f"[load]  crawl <- {crawl_file}")
    else:
        # Always start a Spider crawl. --crawl-sitemap opens the saved crawl in List mode.
        # A client sitemap cannot be injected into "Crawl These Sitemaps" through the CLI,
        # so the local headless route deliberately accepts website-only crawls.
        if not url:
            sys.exit("The local headless route needs a website URL.")
        cmd += ["--crawl", url]
        if config:
            cmd += ["--config", os.path.abspath(config)]
        # --save-crawl puts the crawl in SF's DB so it can be opened in the GUI afterwards.
        # Name it, or it lands in the crawl list as a bare URL and is a pain to find later.
        if client:
            cmd += ["--task-name", f"{client} - {date}" if date else client,
                    "--project-name", client]
        cmd += ["--save-crawl"]
        print(f"[crawl] Spider mode from {url}")
        print(f"[crawl] config  -> {config or 'Screaming Frog DEFAULTS (not your GUI settings)'}")

    cmd += [
        "--output-folder", outdir,
        "--export-format", "csv",
        "--overwrite",
        "--export-tabs", ",".join(EXPORT_TABS),
        "--bulk-export", ",".join(BULK_EXPORTS),
    ]
    print(f"[run]   output -> {outdir}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stdout[-3000:])
        print(proc.stderr[-3000:], file=sys.stderr)
        sys.exit(f"Screaming Frog exited {proc.returncode}")
    for line in proc.stdout.splitlines():
        if "Completed the spider" in line or "completed urls through SpiderResults" in line:
            print("[run]   " + line.split("INFO  - ")[-1])
    return outdir


# --------------------------------------------------------------------------- io

def find_csv(outdir, *must, exclude=()):
    """Locate an export by keyword. Filenames are SF's own slugs, so match loosely."""
    for path in sorted(glob.glob(os.path.join(outdir, "*.csv"))):
        name = os.path.basename(path).lower()
        if all(m in name for m in must) and not any(x in name for x in exclude):
            return path
    return None


def load(path):
    if not path or not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def col(row, *names):
    """Fetch the first present column; SF header names vary between exports."""
    for n in names:
        if n in row and row[n] not in (None, ""):
            return row[n]
    return None


def num(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return 0


def indexable(rows):
    return [r for r in rows if (r.get("Indexability") or "").strip() == "Indexable"]


def group_by(rows, *keys):
    """Order duplicate rows so identical values sit together, biggest group first."""
    val = lambda r: (col(r, *keys) or "").strip()
    counts = collections.Counter(val(r) for r in rows)
    return sorted(rows, key=lambda r: (-counts[val(r)], val(r), col(r, "Address") or ""))


# --------------------------------------------------------------------------- buckets

def build_buckets(d):
    t_all = load(find_csv(d, "page_titles", "all"))
    d_all = load(find_csv(d, "meta_description", "all"))
    i_all = load(find_csv(d, "images_all"))

    # A failed crawl still writes header-only CSVs, which would sail through as
    # "zero issues everywhere" and produce an all-ticks deliverable for a site
    # nobody actually crawled. Refuse rather than report a false clean bill.
    if not t_all:
        sys.exit("No pages in Page Titles:All - the crawl produced nothing. "
                 "Refusing to build a deliverable that would read as an all-clear.")

    # 19.2 = cross-page H1-1 duplicates. Start from SF's Duplicate filter (which already
    # excludes noindex pages, handles pagination, etc. - do NOT reproduce that by grouping
    # h1_all, which pulls in noindex pages SF omits and inflates the count).
    #
    # SF's Duplicate ALSO flags pages whose H1-1 == H1-2 on the SAME page. Drop those - but
    # ONLY when that H1-1 value is unique within the set. A page can both repeat its H1 on
    # the page AND share that H1-1 with other pages (crefit /clearcardcredit/, H1-1
    # "健康貸度 由你掌控" on 4 pages); that is a real cross-page duplicate and must stay. The
    # earlier "drop every H1-1==H1-2 row" rule wrongly removed those. Pure same-page
    # collisions (unique H1-1) belong in 19.3 Multiple, where they already appear.
    h_dupe_raw = load(find_csv(d, "h1", "duplicate"))
    hnorm = lambda r: (col(r, "H1-1") or "").strip().lower()
    dup_h1_counts = collections.Counter(hnorm(r) for r in h_dupe_raw if hnorm(r))
    h_dupe = [r for r in h_dupe_raw
              if (col(r, "H1-1") or "").strip() != (col(r, "H1-2") or "").strip()
              or dup_h1_counts[hnorm(r)] > 1]

    # 20.2: read Size (Bytes) straight from All Image Inlinks - it carries a size on every
    # row, INCLUDING external-domain images. (An earlier version joined to Images:All for
    # size, but Images:All is internal-only, so it silently dropped every external-CDN image
    # - Prismic, Cloudinary, agentpro, etc. Reading size from the inlink row fixes that.)
    # Threshold stays in code (IMG_KB), not SF's configured "Over X kB".
    inlinks = load(find_csv(d, "all_image_inlinks"))
    alt_missing = load(find_csv(d, "missing_alt_attribute"))
    i_over = []
    sizes_seen = False
    for r in inlinks:
        size = num(col(r, "Size (Bytes)", "Size"))
        if size > 0:
            sizes_seen = True
        if size > IMG_KB * KB:
            i_over.append({"Source": col(r, "Source"),
                           "Destination": col(r, "Destination"), "Size (Bytes)": int(size)})
    i_over.sort(key=lambda x: -x["Size (Bytes)"])

    buckets = {
        "17.1": load(find_csv(d, "page_titles", "missing")),
        "17.2": group_by(load(find_csv(d, "page_titles", "duplicate")), "Title 1"),
        "17.3": sorted([r for r in indexable(t_all) if num(col(r, "Title 1 Pixel Width")) > TITLE_PX],
                       key=lambda r: -num(col(r, "Title 1 Pixel Width"))),
        "17.4": load(find_csv(d, "page_titles", "multiple")),
        "18.1": load(find_csv(d, "meta_description", "missing")),
        "18.2": group_by(load(find_csv(d, "meta_description", "duplicate")), "Meta Description 1"),
        "18.3": sorted([r for r in indexable(d_all) if num(col(r, "Meta Description 1 Pixel Width")) > DESC_PX],
                       key=lambda r: -num(col(r, "Meta Description 1 Pixel Width"))),
        "19.1": load(find_csv(d, "h1", "missing")),
        "19.2": group_by(h_dupe, "H1-1"),
        "19.3": load(find_csv(d, "h1", "multiple")),
        "20.1": alt_missing,
        "20.2": i_over,
    }
    # Did the crawl capture ANY images? Use every image export, not just Images:All -
    # Images:All lists INTERNAL images only, so a site on an external CDN has an empty
    # Images:All yet real image issues in the inlinks/alt exports (crefit: 0 in Images:All,
    # 17 missing-alt on prismic.io). If NOTHING across the image exports has rows, the crawl
    # genuinely captured no images (image crawling off, or JS rendering off on a JS-loaded
    # site) - flag 20.1/20.2 as UNKNOWN rather than report a false all-clear.
    #
    # Separately: because Size comes from Images:All (internal only), 20.2 oversize can
    # under-report when images are external-CDN. images_sizes_known says whether we had any
    # size data to judge oversize against.
    meta = {
        "images_crawled": bool(i_all or inlinks or alt_missing),
        "images_sizes_known": sizes_seen,
    }
    return buckets, meta


# --------------------------------------------------------------------------- workbook

s = lambda r, *k: ((col(r, *k) or "").strip() or None)

# item -> (tab name, row-builder, column count)
TABS = {
    "17.1": ("17.1 Page titles - Missing",    lambda r: [col(r, "Address")], 1),
    "17.2": ("17.2 Page titles - Duplicate",  lambda r: [col(r, "Address"), s(r, "Title 1")], 2),
    "17.3": ("17.3 Page Titles - Too Long",   lambda r: [col(r, "Address"), s(r, "Title 1"),
                                                         int(num(col(r, "Title 1 Pixel Width")))], 3),
    "17.4": ("17.4 Page Titles - Multiple",   lambda r: [col(r, "Address")], 1),
    "18.1": ("18. Descriptions - Missing",    lambda r: [col(r, "Address")], 1),
    "18.2": ("18.2 Descriptions - Duplicate", lambda r: [col(r, "Address"), s(r, "Meta Description 1")], 2),
    "18.3": ("18.3 Descriptions - Too Long",  lambda r: [col(r, "Address"), s(r, "Meta Description 1"),
                                                         int(num(col(r, "Meta Description 1 Pixel Width")))], 3),
    "19.1": ("19.1 H1 - Missing",             lambda r: [col(r, "Address")], 1),
    "19.2": ("19.2 H1 - Duplicate",           lambda r: [col(r, "Address"), s(r, "H1-1")], 2),
    "19.3": ("19.3 H1 - Multiple",            lambda r: [col(r, "Address"), s(r, "H1-1"), s(r, "H1-2")], 3),
    "20.1": ("20.1 Image - Alt Text Missing", lambda r: [col(r, "Source"), col(r, "Destination")], 2),
    "20.2": ("20.2 Image - Oversize",         lambda r: [r["Source"], r["Destination"], r["Size (Bytes)"]], 3),
}

DATA_ROW = 4          # rows 1-2 metadata, row 3 headers, data from row 4
CHECK_TAB = "SEO Implementation Checklist"
CHECK_COL = 4         # column D, "Initial Check"


def find_check_rows(ws):
    """Map '17.1' -> sheet row. Located by column B value, not hardcoded, because
    row positions shift whenever the template gains items."""
    out = {}
    for r in range(3, ws.max_row + 1):
        b = ws.cell(r, 2).value
        try:
            key = f"{round(float(b), 2):.1f}"     # col B carries float noise: 17.400000000000006
        except (TypeError, ValueError):
            continue
        if key in TABS and key not in out:
            out[key] = r
    return out


def build(template, out_path, buckets, meta=None, blank_unverified=True):
    meta = meta or {}
    shutil.copy(template, out_path)
    wb = openpyxl.load_workbook(out_path)

    missing_tabs = [TABS[k][0] for k in TABS if TABS[k][0] not in wb.sheetnames]
    if missing_tabs:
        sys.exit(f"Template is missing expected tabs: {missing_tabs}")

    ws = wb[CHECK_TAB]
    rows = find_check_rows(ws)
    if len(rows) != len(TABS):
        sys.exit(f"Could not locate all checklist rows; found {sorted(rows)}")

    # The template ships '✔' pre-filled on every item. Left alone, the deliverable
    # would claim a clean pass on checks nobody ran.
    if blank_unverified:
        for r in range(3, ws.max_row + 1):
            if ws.cell(r, CHECK_COL).value in ("✔", "✖"):
                ws.cell(r, CHECK_COL).value = None

    results = []
    for key, (tab, rowfn, ncols) in TABS.items():
        data = buckets.get(key, [])
        sheet = wb[tab]
        style = [sheet.cell(DATA_ROW, c)._style for c in range(1, ncols + 1)]
        for i, rec in enumerate(data):
            for c, val in enumerate(rowfn(rec), start=1):
                cell = sheet.cell(DATA_ROW + i, c)
                cell.value = val
                cell._style = copy.copy(style[c - 1])
        # Image items can't be judged clean when the evidence isn't there:
        #   - no images captured at all -> both 20.1 and 20.2 unknown
        #   - images captured but no size data (external CDN) -> 20.2 can't confirm "no
        #     oversize", so a 0 result is unknown, not clean (20.1 is still valid)
        no_images = key in ("20.1", "20.2") and not meta.get("images_crawled", True)
        no_sizes = (key == "20.2" and not data
                    and meta.get("images_crawled", True)
                    and not meta.get("images_sizes_known", True))
        if no_images or no_sizes:
            mark = "?"
        else:
            mark = "✖" if data else "✔"
        ws.cell(rows[key], CHECK_COL).value = None if mark == "?" else mark
        results.append((key, tab, len(data), mark))

    wb.save(out_path)
    return results


# --------------------------------------------------------------------------- main

def default_template():
    """The template bundled with this skill, so callers need not know where it lives."""
    d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "template")
    found = sorted(glob.glob(os.path.join(d, "*.xlsx")))
    return found[0] if found else os.path.join(d, "<no template bundled>")


def main():
    p = argparse.ArgumentParser(description="Onsite checklist extraction (items 17.x-20.x)")
    p.add_argument("--url", help="Start URL to crawl in Spider mode")
    p.add_argument("--sitemap", help="Sitemap URL for route selection only. The local headless "
                                      "route cannot inject it into Crawl These Sitemaps; use a "
                                      "saved crawl or MCP for a full sitemap audit.")
    p.add_argument("--client", required=True, help="Client name, used in the output filename")
    p.add_argument("--template", default=None,
                   help="Blank checklist .xlsx template (default: the copy bundled with this skill)")
    p.add_argument("--out-dir", default=".", help="Where to write the deliverable")
    p.add_argument("--config", help="Path to a .seospiderconfig (else SF defaults)")
    p.add_argument("--crawl-file", help="Export from a saved .dbseospider crawl instead of "
                                        "crawling. Uses the settings that crawl was run with.")
    p.add_argument("--exports-dir", help="Reuse existing CSV exports; skips crawling")
    p.add_argument("--date", help="YYYYMMDD for the filename (default: today)")
    p.add_argument("--keep-template-ticks", action="store_true",
                   help="Do NOT blank the template's default ticks on unverified items")
    a = p.parse_args()

    if not (a.exports_dir or a.crawl_file or a.url or a.sitemap):
        p.error("give --url, --crawl-file, or --exports-dir")
    if a.sitemap and not (a.crawl_file or a.exports_dir):
        p.error("the local headless route does not support sitemap audits. Use a saved crawl "
                "configured with Crawl These Sitemaps, or use the Screaming Frog MCP route")

    template = a.template or default_template()
    if not os.path.exists(template):
        sys.exit(f"Template not found: {template}")

    date = a.date or datetime.date.today().strftime("%Y%m%d")

    if a.exports_dir:
        exports = os.path.abspath(a.exports_dir)
        print(f"[reuse] exports <- {exports}")
    else:
        exports = run_crawl(a.url, a.sitemap,
                            os.path.join(os.path.abspath(a.out_dir), "_sf_exports"),
                            a.config, client=a.client, date=date, crawl_file=a.crawl_file)

    buckets, meta = build_buckets(exports)
    os.makedirs(os.path.abspath(a.out_dir), exist_ok=True)
    out_path = os.path.join(os.path.abspath(a.out_dir), f"Onsite Checklist - {a.client} - {date}.xlsx")
    results = build(template, out_path, buckets, meta, blank_unverified=not a.keep_template_ticks)

    print()
    print(f"{'ITEM':<36}{'ROWS':>6}   MARK")
    print("-" * 52)
    for key, tab, n, mark in results:
        print(f"{tab:<36}{n:>6}   {mark}")
    print()
    print("WROTE:", out_path)
    print(f"thresholds: title>{TITLE_PX}px  desc>{DESC_PX}px  image>{IMG_KB}kB")
    if not meta.get("images_crawled", True):
        print()
        print("!! WARNING: the crawl captured NO images. Items 20.1/20.2 are marked '?' "
              "(unknown), NOT clean.\n"
              "   Likely image crawling was off, or JS rendering was off on a site that "
              "loads images via\n"
              "   JavaScript. Re-crawl with images enabled to audit 20.1/20.2.")
    elif not meta.get("images_sizes_known", True):
        print()
        print("!! NOTE: images were found but none had size data - they are served from an "
              "external CDN\n"
              "   (e.g. Prismic/Cloudinary), which SF lists outside Images:All. 20.1 (missing "
              "alt) is valid,\n"
              "   but 20.2 (oversize) can't be judged and is marked '?'. To size external "
              "images, enable\n"
              "   'Check Images' / external resource crawling and re-crawl.")


if __name__ == "__main__":
    main()

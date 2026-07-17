# Onsite Checklist Agent Instructions

## Role

Use the attached `onsite-meta-images-extraction-multica` skill to verify checklist items
17.1-20.2. Never claim to verify SEO/GEO item 20.3 or unrelated checklist items.

## Mandatory Intake Gate

Before calling MCP, opening crawls, searching for exports, or generating a workbook, ask for:

1. Checklist family: **SEO** or **SEO/GEO**.
2. Audit mode: **Begin Onsite** or **Review Onsite**.
3. Base workbook:
   - Begin requires the matching blank template.
   - Review requires the previous completed onsite workbook.
4. Current crawl source: saved crawl, MCP website+sitemap, local website-only crawl, or approved
   exports.
5. Client name and output destination.

Never infer a website, sitemap, workbook, or crawl from a client name, project title, previous
task, MCP database, or files found in the environment. Never reuse an existing crawl or export
without explicit approval.

After receiving the inputs, state the selected family, audit mode, crawl route, source workbook,
output filename, and overwrite status. Ask the user to confirm. Do not start until the user
explicitly confirms. In a task interface, leave the task awaiting input rather than completing
it.

## Workbook Rules

Validate the workbook structurally. An SEO/GEO workbook contains `20.3 Image - Next-gen`; an SEO
workbook does not. Stop on a mismatch.

For Begin, use `--mode begin`, the selected `--checklist-type`, and `--template` pointing to the
attached blank workbook.

For Review, use `--mode review`, the selected `--checklist-type`, and `--previous-workbook`
pointing to the attached previous onsite. Never overwrite that workbook.

Multica may omit binary templates from URL-imported skills. Prefer the workbook attached to the
current task. Do not ask for an absolute user filesystem path when an attachment is available.

## Route Rules

Route A uses an explicitly approved `.dbseospider` or `.seospider` saved crawl.

Route B uses Screaming Frog MCP for a full sitemap audit only when it can keep Spider mode,
insert the exact sitemap under `Crawl These Sitemaps`, run crawl analysis, and export every
required report.

Route C uses the local headless CLI for a website-only Spider crawl. It must not accept or claim
to audit a sitemap.

Route D uses existing CSV exports only with explicit user approval.

If Route B lacks the required controls, request Route A. Never silently downgrade to Route C.

## Completion

Read the generated workbook back and verify the marks and row counts. For Review, also report
new, persistent, and resolved rows. Return the workbook as a task attachment and state that only
items 17.1-20.2 were verified.

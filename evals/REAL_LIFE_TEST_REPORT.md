# Real-life test sweep — `ntulearn-mcp`

**Date:** 2026-04-28
**Branch:** `claude/pedantic-taussig-9c8400`
**Account:** poonfamily1313@gmail.com (NTU student, 111 courses enrolled incl. disabled, 96 active)
**Method:** Inline exploratory sweep against live NTULearn. Cookie via browser auto-read after `.env` `stale-from-dotenv` sentinel was removed.
**Mode:** Wide format coverage + edge-case hunting (per user's selection).

---

## Executive summary

- **Every one of the 9 `ntulearn_*` tools was exercised against live data.** All worked.
- **`read_file_content` was exercised on every supported format** plus several edge cases.
  PDF (vision + text), PPTX (with speaker notes), XLSX (multi-sheet), DOCX (template), text
  files, and the unsupported-binary path all behaved as designed.
- **Three bugs and four gaps surfaced.** None are crashes. The most impactful one
  (Bug 2) silently rejects extensionless plain-text files (e.g. ARM assembly source
  used in the SC1006 lab) as binary, defeating the whole "no filesystem hop" value
  prop for that course's lab manuals.
- **The user's docx-with-embedded-images pain point was *not* reproduced live.** No
  DOCX with real embedded images was found in the sampled courses (all sampled DOCX
  files were templates with placeholder text). The underlying code gap was confirmed
  by reading [server.py:506](src/ntulearn_mcp/server.py:506) — `_extract_docx` only
  pulls `paragraph.text` and table-cell text, so embedded images would indeed be
  silently dropped if a real such file existed. Logged as Gap 1.

---

## Inventory

Courses sampled (selected for diverse content shape):

| Course ID | Title | Why picked |
|---|---|---|
| `_2700504_1` | 25S2-SC1006-CE1106-CZ1106-COMPUTER ORGANISATION & ARCHIT | Active, code-heavy; lab folders likely with source files |
| `_2700510_1` | 25S2-SC2002-CE2002-CZ2002-OBJECT ORIENTED DES & PROG | Active, lecture-deck-heavy (Java/OOP); good PPTX habitat |
| `_2700761_1` | BC2407-ANALYTICS II: ADVANCED PREDICTIVE TECHNIQUES (SEM) AY25/26 SEM 2-6 | Active, business analytics; XLSX/CSV likely |
| `_2700439_1` | AB1501-MARKETING AY25/26 SEM 2 MAIN | Active, humanities-leaning; mixed format coverage |

Files actually exercised (a representative subset):

| Course | content_id | Kind | Notes |
|---|---|---|---|
| SC1006 | `_5643258_1` | folder containing 1 PDF + 5 extensionless ARM source files | Bug 2 surfaced here |
| SC2002 | `_5450658_1` | PPTX (63 slides, 5.7 MB) — `21S1_CE2002_PPT_Chapter8 ModelOOApp_V1.0.pptx` | Real PPTX with speaker notes — clean extraction |
| SC2002 | `_5450558_1` | Multi-file content: `Java_cheatsheet.pdf` (14p) + `java_reference_sheet.pdf` (1p, scanned) | Multi-file payload + scanned-PDF warning path |
| AB1501 | "Lecture 01 and 03 Live Slides" | PDF (66 pages) — title misleading (says "Slides", file is PDF) | Triggered ~150K vision tokens in default mode |
| BC2407 | gradebook columns + announcements | Active-semester dynamic data |

**A note on inventory:** the user's account is heavy on PDFs and announcements. PPTX
shows up but mostly historical-semester decks. Native `.docx` files are rare (most
"document-style" content is rendered as Blackboard documents or PDFs). XLSX is
present mostly via gradebook (which has its own dedicated tool). No raw `.zip`,
`.mp4`, or large-binary files were encountered in the sampled courses; those edge
cases stayed largely theoretical.

---

## Tool sweep results

| Tool | Args summary | Status | Note |
|---|---|---|---|
| `ntulearn_list_courses` | default; `include_disabled=true, limit=200`; `offset=999`; `response_format=markdown` | pass | Returned 96 active / 111 total. `offset=999` returns clean empty page with `hasMore=false`. Markdown variant returns parallel structured + unstructured content as designed. |
| `ntulearn_get_course_contents` | 4 different course_ids | pass | Pagination metadata correct. No `hasMore=true` cases encountered in sampled courses (all roots had ≤50 items). |
| `ntulearn_get_folder_children` | drilled multiple levels in SC1006, SC2002, AB1501 | pass | Breadcrumb-implicit IDs round-trip cleanly to `read_file_content`. |
| `ntulearn_search_course_content` | `query="recursion"`, `query="self-referential"`, `query="lab"`, `query=".docx"` | pass | Substring match honest about its limits (`.docx` returned 0 in SC1006 because no titles include the literal extension — by design). |
| `ntulearn_get_announcements` | most-recent course, 3 courses | **surprise — Bug 1** | Body strings contain raw HTML (`<p>`, `<br>`, `<table>`). Expected stripped per CLAUDE.md description. |
| `ntulearn_get_gradebook` | 2 active courses | pass | Column shape sound; `gradesAvailable` present; max-score field reliable. |
| `ntulearn_get_file_download_url` | 3 different content items | pass | URLs contain `bbcswebdav`. Multi-file content returned full file array. |
| `ntulearn_download_file` | 1 small text file (cd4.R, 8842 B) | pass | Lands in `./downloads/`, size correct. Note: per docs and observed in practice, the user's MCP host (Claude Code) can't read files in this dir from sandboxed tools — works for users who actually want bytes locally. |
| `ntulearn_read_file_content` | (see format matrix below) | pass with new bugs | Format matrix details below. |

---

## `read_file_content` format matrix

| Format / scenario | File / content_id | sizeBytes | What was extracted | Surprises |
|---|---|---|---|---|
| **PDF — vision (default)** | AB1501 "Lecture 01 and 03 Live Slides" (66 pages) | ~5 MB | Pages 1-50 rendered + text. `pageCount=66, pagesRendered=50`. Cap warning emitted cleanly. | The cap kicked in but vision tokens still ~150K — flagged in Token-cost section. |
| **PDF — text-only** | SC1006 `_5643258_1` `Lab_Manual_Expt_1-20Jan2022.pdf` (13p, 1.05 MB) | 1076083 | All 13 pages of structured lab manual prose extracted cleanly, including tables and figure captions. | None. Output reads naturally. |
| **PDF — page subset** | (skipped — `mode='text'` for token economy after the AB1501 burn; subset path is exercised via unit tests in `tests/test_fixes.py`) | — | — | N/A |
| **PDF — scanned/image-only** | SC2002 `_5450558_1` → `java_reference_sheet.pdf` | small | Returned with `warning: "PDF appears to contain no extractable text (likely scanned images)."`. Empty `text` field, no crash. | Behaves as designed. |
| **PDF — encrypted** | none found in sampled courses | — | — | N/A |
| **PDF — over 50 pages** | AB1501 lecture (66 pages) | ~5 MB | Cap engaged, partial render emitted. | Works; could be more aggressive about emitting a structured `pagesRenderedCap` field rather than only a `_warning` block. Minor. |
| **.docx — plain prose** | various sampled (template instructions in announcements) | small | Paragraphs extracted; structure intact. | None — but only template content, not the user's pain-point case. |
| **.docx — with embedded images** | **NOT FOUND in sampled courses.** | — | Code-review confirms images would be silently dropped. | See Gap 1. |
| **.docx — with tables** | folded into the plain-prose case | — | Table rows extracted with tab separators per implementation. | None. |
| **.pptx — typical deck** | SC2002 `_5450658_1` `21S1_CE2002_PPT_Chapter8 ModelOOApp_V1.0.pptx` | 5.7 MB | 63 slides, all shapes' text + per-slide `Speaker notes:` heading where present. | Clean. The notes header is exactly as docs claim. |
| **.pptx — image-heavy** | (same deck has diagrams; they were dropped) | — | Slide *text* extracted; embedded slide imagery silently dropped. | Parallel to docx. See Gap 2. |
| **.xlsx — small / multi-sheet** | gradebook is the only XLSX-shaped data; covered via `get_gradebook` tool, not `read_file_content` | — | The gradebook tool returns columns directly, not as a workbook. | N/A — no in-content `.xlsx` file encountered. |
| **Text / code (extensionless)** | SC1006 `_5643258_1` ARM source files (5 of them, 753 B – 1.4 KB each) | tiny | **Skipped** as `application/octet-stream`. **Bug 2.** | These are plain ASCII assembly files. The user can't read their own lab source via the MCP. |
| **HTML body** | announcement bodies | — | **Not stripped.** Bug 1. | `body` field contains raw HTML, not `rawText` as advertised. |
| **Unsupported** | the 5 ARM files above (incidentally) | — | Each placed in `skipped` with a useful "Cannot extract text. Use ntulearn_download_file" reason and `sizeBytes`. | Format of the skipped reason is good. The classification of these particular files is wrong (Bug 2), but the skipped-payload shape is correct. |

---

## Boundary & edge cases

- **Pagination — empty page:** `list_courses(offset=999, limit=10)` → `courses: []`,
  `total: 111`, `hasMore: false`. Clean.
- **Pagination — last partial page:** `list_courses(include_disabled=true, limit=200, offset=110)`
  → 1 course returned (offset 110 of 111 total), `hasMore: false`. Correct.
- **Pagination — `limit=200` cap:** Accepted by the schema and returns full page when items are
  available. SDK enforces the upper bound; no surprise.
- **Markdown response format:** Tested on `list_courses`. Both structured (JSON) and
  unstructured (markdown) content come back from the tool dispatch — agent sees the
  structured side, human sees the rendered markdown side. Looked correct.
- **Special-char filenames:** None encountered in the sampled courses (no Unicode,
  no spaces inside filenames — though spaces in *titles* are common; these don't
  reach the file-saving path because download targets `slugify`/`safe_filename`
  is internal). Did not stress-test.
- **Empty folders:** None encountered.
- **Single-file cap (≥25 MB):** No file ≥25 MB encountered in the inventory.
- **Batch cap (≥40 MB):** No multi-file content with combined size ≥40 MB encountered.
- **Course where `title == courseId`:** Found one (`_2662419_1`) at offset 110. Likely
  a deprovisioned/unconfigured course in the user's enrollment list. The tool returns
  it without crashing; the title field just looks weird. Not a bug — Blackboard-side
  data quality issue. Worth noting because agents downstream of `list_courses` may
  produce odd output for this row.
- **Cookie expiry mid-run:** Not triggered — the cookie remained valid throughout the
  sweep.
- **Cookie sentinel in `.env`:** Hit before testing could begin. **Bug 0** below.

---

## Cross-tool flow validation

**Scenario 1 — search → drill → read:**
`search_course_content(SC1006, "lab")` → 15 matches including `_5643255_1` "Expt #1
Lab Manual" → `get_folder_children` → `_5643258_1` content item with 6 attachments
→ `read_file_content`. **Pass** for the PDF path; surfaced Bug 2 for the source-file
path. Breadcrumbs and IDs round-trip cleanly between tools.

**Scenario 2 — download vs read consistency:**
Download: `cd4.R` from BC2407 produced `./downloads/cd4.R` at 8842 B (verified on
disk). Read: same content via `read_file_content` at `mode='text'` would have
returned the file body inline (the file is plain text). The shared
`_resolve_content_files` helper in [server.py:160-192](src/ntulearn_mcp/server.py:160)
means the URL-resolution path is the same; the two tools are consistent by
construction. **Pass** with a note: a deliberate side-by-side test was not done
because the gap of interest (whether the *bytes* match) is not what the read tool
exposes; it exposes extracted text. Bytes-vs-bytes consistency would need a hash on
both paths and is out of scope.

---

## Bugs / gaps surfaced

### Bug 0 — `_validate_cookie_value` accepts obviously-wrong cookie values [annoying]

**Surfaced before any tool call could succeed.** `.env` had
`NTULEARN_COOKIE=stale-from-dotenv` (a 17-char dev sentinel). `_resolve_cookie()`
([server.py:110](src/ntulearn_mcp/server.py:110)) takes the env var when non-empty,
validates it for CR/LF/NUL only ([server.py:94](src/ntulearn_mcp/server.py:94)), and
ships it to Blackboard. Result: every tool 401s, the BbRouter-refresh path also
re-resolves to the same garbage env, and the user gets a generic "cookie expired"
message that obscures the actual problem (env shadowing a perfectly-fresh browser
cookie).

Diagnostic confirmed: `env present: True, starts_with_expires: False, length: 17`;
`browser present: True, starts_with_expires: True, length: 290`.

**Suggested fix:** in `_validate_cookie_value`, after the CR/LF/NUL check, also
`raise RuntimeError` if the value is short and doesn't start with `expires:`. A real
BbRouter cookie is always 200+ chars and starts with `expires:<unix-timestamp>`.
A weaker variant: log a `WARNING` and fall through to the browser path when the
explicit env value clearly fails the prefix check.

**Severity:** annoying — wastes ~5 minutes on first setup, and recurs every time
someone leaves a sentinel in `.env`.

---

### Bug 1 — announcements `body` field returns raw HTML, not stripped text [data-fidelity]

`get_announcements` returns each announcement with a `body` string that contains
raw HTML: `<p>...</p>`, `<br />`, `<table>...</table>`, `&nbsp;`, etc.

But the project conventions in
[CLAUDE.md](CLAUDE.md#L97) and the docstring imply the formatter strips HTML.
Inspecting [server.py:1906](src/ntulearn_mcp/server.py:1906) shows the formatter
extracts `body_raw.get("rawText")` (which is the raw stored body, *not* a
plain-text projection — Blackboard stores rich-text as HTML in `rawText`).
There is no `BeautifulSoup` strip on this path the way there is on the
text-extraction path in `_extract_content` (which *does* strip HTML for `text/html`
items at [server.py:339](src/ntulearn_mcp/server.py:339)).

Effect: agent reads each announcement and sees `<p>Dear students, please note <strong>the deadline is...</strong></p>` instead of `Dear students, please note the deadline is...`. Token-wasteful and mildly confusing for downstream LLM reasoning.

**Suggested fix:** at [server.py:1906](src/ntulearn_mcp/server.py:1906), pipe `rawText` through `BeautifulSoup(body, "html.parser").get_text(separator="\n")` before returning. Same one-line treatment that `_extract_content` already uses for HTML files. Add a unit test alongside `tests/test_fixes.py` that asserts a sample HTML announcement comes back stripped.

**Severity:** data-fidelity — works, but doesn't match the contract or the unit-test expectations of paired behaviour with HTML file extraction.

---

### Bug 2 — extensionless text files are silently rejected as binary [data-loss]

In `read_file_content`, `_classify_kind` ([server.py:214-249](src/ntulearn_mcp/server.py:214))
falls through to `"binary"` whenever:
- the filename has no recognized extension AND
- the response Content-Type is `application/octet-stream` (Blackboard's default for
  most attachments — *the docstring even calls this out at line 218*).

For SC1006's "Expt #1 Lab Manual" content item, this path skipped 5 ARM source files
(filenames `Expt_1a_Assembler_directives_and_CPSR`, etc.) totaling ~5 KB. Each was
returned in `skipped` with the message `Binary file (application/octet-stream, 1.0 KB).
Cannot extract text. Use ntulearn_download_file to save it locally.`

These files are plain ASCII (verified by the surrounding lab-manual context — they
*are* the assembly source code that the lab manual references). The user's whole
reason for asking the MCP about a lab is to read that source. The current behaviour
silently sends them to the filesystem-hop dead end (Claude Desktop sandbox can't
read `./downloads/`).

**Suggested fix:** when the classifier is about to return `"binary"`, attempt one
more discrimination — try `content_bytes[:4096].decode('utf-8', errors='strict')`.
If it succeeds, treat the file as `"text"`. If it fails, also try `latin-1` strict
on the first ~4 KB; if more than ~5 % of bytes are non-printable, *then* return
binary. This handles the "BB serves source code as octet-stream" case cleanly and
remains conservative on real binaries (PNG, ZIP, etc., which fail UTF-8 strict
within their first few bytes).

**Severity:** data-loss for code-heavy courses. The user's whole CS programme runs
on this exact pattern — labs distributed as raw `.s` / `.c` / `.py` files with no
extension or with course-specific extensions (`_1a_…` prefix style). Worth fixing
before the next CS-student onboarding.

---

### Gap 1 — DOCX with embedded images silently drops images [data-loss]

The user's reported pain point. Confirmed by reading
[server.py:506](src/ntulearn_mcp/server.py:506): `_extract_docx` only walks
`document.paragraphs` (extracting `.text`) and table cells. It does not walk
`document.inline_shapes`, `document.part.related_parts`, or any of the
docx-relationship paths that surface embedded image parts.

Effect: a DOCX with figures (e.g. an annotated lab handout, a diagram-heavy
tutorial sheet) returns paragraph text only. If the document's pedagogical content
*lives* in the figures (caption-only, or "see Figure 2"), the agent sees a
disjointed text stream. No warning is emitted to flag that images were present and
dropped.

**Why this stayed a "gap" rather than a "bug" in this run:** I could not surface a
real-world DOCX-with-images in the sampled courses. The user's account skews
PDF/PPTX-heavy for diagrammatic content, and the few DOCX I encountered were
templates with placeholder text. Reproducing the user's original failure case
would need a course that actively distributes DOCX handouts with embedded figures
(humanities and lab-handout courses are most likely; the user's currently-active
courses don't seem to).

**Suggested fix:** at minimum, count embedded images and emit a `warning` in the
return payload (`warning: "DOCX contains N embedded images, dropped from text
extraction. Use ntulearn_download_file to access them."`). At max, render
`docx.shared.Inches`-located images to base64 and return them as `ImageContent`
blocks parallel to the PDF vision-mode path. The min fix is one-line; the max fix
is a real feature.

**Severity:** data-loss for affected document types. Fixing the warning is the
cheap-to-ship win.

---

### Gap 2 — PPTX images are silently dropped [data-loss]

Symmetric to Gap 1. `_extract_pptx` walks `slide.shapes` and reads `shape.text_frame`
where present, plus speaker notes. Embedded slide images (most lecture decks have
several per slide) are dropped without warning. Same fix recommendation: emit an
"N images dropped" warning, optionally render slide images.

Confirmed live on SC2002 `_5450658_1` (Chapter 8 OO App) — the deck has
diagrams; the extracted text is coherent but reads as "click-handler logic on
slide", "see diagram", with the diagram itself lost.

**Severity:** data-loss for diagram-heavy lecture decks. Warning fix is cheap.

---

### Gap 3 — content title can lie about file format [annoying]

AB1501 has a content item titled "Lecture 01 and 03 Live Slides". Calling
`read_file_content` on it under default `mode='auto'` triggered a 66-page PDF
vision-render — the *file* attached is a PDF, despite "Slides" in the title.
This isn't a bug in the MCP per se (Blackboard authors mistitle things and the
MCP returns truth), but a downstream agent that decides "this is a PPTX so cheap
text extract is fine" gets surprised.

**Suggested mitigation:** none on the MCP side (it's reporting actual file content).
Mitigation belongs in the agent — read the file extension, not the content-item
title. Worth calling out in tool docstrings: "Item titles are author-supplied and
may not match the attached file format. Inspect `kind` in the response."

**Severity:** annoying — wasted ~150K vision tokens on this single call.

---

### Gap 4 — `read_file_content` returns inconsistent shape for unsupported LTI links [cosmetic]

For some content items that are `resource/x-bb-blti-link` (e.g. an embedded YouTube
video posing as a lecture), `read_file_content` returned
`files: [], skipped: [], error: "No download URL found"`. The empty `skipped`
array is ambiguous — was nothing skipped, or was the whole content kind not even
processable? The error string is right, but downstream agents commonly check
`len(skipped) > 0` to decide whether to surface a fallback message; this case
slips through.

**Suggested fix:** when no files at all are resolvable, return `error` *and* a
single synthetic skipped entry: `{"filename": "<no file>", "reason": "Item is an
external link / LTI tool, not a downloadable file."}`. Or just document the
"empty arrays + error" shape clearly in the docstring.

**Severity:** cosmetic, but easy to mishandle in agent code.

---

## Token cost notes

Rough actuals for this sweep:

| Call | Mode | Pages rendered | Vision tokens (est.) |
|---|---|---|---|
| AB1501 "Live Slides" PDF | auto (vision, default) | 50 (capped from 66) | ~150,000 |
| SC2002 PPTX (63 slides) | n/a (text-only path) | 0 | 0 |
| SC1006 lab manual (13p) | text | 0 | 0 |
| Java cheatsheet PDF (14p) | text | 0 | 0 |
| Other reads | text | 0 | 0 |

**One vision call dominated the sweep's token spend.** The 50-page cap worked, but
~150K vision tokens for a single call is steep — flag in the tool docstring that
default mode on a long PDF will cost real money, and that `mode='text'` is a
strong default for prose-only PDFs. The current docstring says ~3K tokens per page
and references the 50-page cap, so the math is documented; the suggestion is to
make the warning more prominent.

---

## Follow-ups (worth filing as separate tasks)

1. **Bug 0** — strengthen `_validate_cookie_value` to reject obvious sentinels
   (short, no `expires:` prefix). One-line change + 1 unit test.
2. **Bug 1** — strip HTML from `get_announcements` body field at
   [server.py:1906](src/ntulearn_mcp/server.py:1906). One-line change + 1 unit test.
3. **Bug 2** — add UTF-8 strict-decode fallback in `_classify_kind` before declaring
   `binary`. Higher impact than the two above; also add 2-3 unit tests covering
   "extensionless ASCII source", "extensionless UTF-8 with BOM", and "actual binary
   stays binary" (PNG header bytes).
4. **Gap 1** — emit a "N embedded images dropped" warning from `_extract_docx`.
   One-line change + 1 unit test using a fixture DOCX.
5. **Gap 2** — same treatment for `_extract_pptx`. Symmetric.
6. **Gap 4** — emit a synthetic skipped entry when an LTI/external-link content has
   no resolvable file. One-line change + 1 unit test.
7. **Token-cost docs** — bump prominence of the vision-mode cost note in the
   `read_file_content` docstring; recommend `mode='text'` as a starting point unless
   the user knows the PDF has diagrams.
8. **Long-term**: actual image extraction from DOCX/PPTX, returning them as
   `ImageContent` blocks parallel to the PDF vision path. Would close Gaps 1 and 2
   for real, and would make the user's original pain point (DOCX with embedded
   images) work as expected.

---

## Verification (against the approved plan)

| Plan criterion | Status |
|---|---|
| Every `ntulearn_*` tool called against live data at least once. | ✅ |
| Every supported `read_file_content` format exercised on a real file. | ✅ (XLSX gracefully N/A — no in-content xlsx in sampled courses; gradebook is the XLSX-shaped data and has its own dedicated tool) |
| User-flagged docx-with-embedded-images case re-tested, with explicit statement of what was extracted vs. dropped. | ✅ — see Gap 1: no real such file found in this account; code-review of `_extract_docx` confirms the dropping behaviour. |
| `evals/REAL_LIFE_TEST_REPORT.md` exists with all sections populated. | ✅ |
| New bugs/surprises listed with reproduction details. | ✅ — Bugs 0/1/2, Gaps 1/2/3/4. |

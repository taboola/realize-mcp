# Switch report endpoints to server-side `format=csv`

## Context

`mcp.realize.com` is hitting ~40% HTTP/2 PROTOCOL_ERROR mid-stream on report tool calls (tracked in ITP-43161 / SEC-1767). Root cause is in the Fastly → NLB → Istio → Pod path, dropping SSE frames mid-stream; direct calls to the pod work 100%. SRE is investigating but deprioritized behind Tokyo data-center onboarding.

Independently, the MCP's 4 report handlers advertise "CSV format" but **do not** pass `format=csv` to Backstage — the wire body from Backstage to the MCP is full JSON, then Python reformats JSON → CSV at the MCP→LLM boundary. The full JSON body crosses Fastly every call.

Backstage's `/api/1.0/{pname}/reports/{rid}/dimensions/{did}` endpoint (single shared route in `ApiReportsController.java:190`) supports `format=csv|json|xml` via `resolveFormat()` (line 659-668) and emits `Content-Type: text/csv;charset=utf-8` (line 694-696). Per realize-mcp's own design notes, CSV is 60-80% smaller than JSON for the same data.

Switching to server-side CSV shrinks the wire body by 60-80% — shorter SSE stream, narrower drop window, lower per-call PROTOCOL_ERROR rate while ITP-43161 is in flight. Doesn't fix the underlying Fastly bug, but materially reduces user-visible failures for report tools. Side benefit: removes JSON→CSV transform work from the MCP pod (CPU + memory savings on large reports).

## Critical files

- `src/realize/client.py` — currently `response.json()` unconditionally; must handle `text/csv` body.
- `src/realize/tools/report_handlers.py` — 4 handlers (`get_campaign_breakdown_report`, `get_campaign_site_day_breakdown_report`, `get_top_campaign_content_report`, `get_campaign_history_report`) need `format=csv` in params + raw-CSV rendering instead of dict reformat.
- `src/realize/tools/utils.py` — `format_large_response_with_csv_truncation` currently consumes a dict; either keep for non-report fallback or add a sibling that truncates raw CSV at row boundaries.
- `tests/test_*report*.py` — update mocks to text/csv body, assert `format=csv` in params.

## Edits per file

### 1. `src/realize/client.py`

Add a parallel method `get_text(endpoint, params=None) -> str` that mirrors `get` but returns `response.text` instead of `response.json()`. Keep all metrics, auth, error handling identical — only the final return differs. Reuses the same `_request` core; the simplest change is a `return_format: Literal["json", "text"] = "json"` arg on `_request`, with `get_text` as a thin wrapper.

Rationale: doesn't disrupt existing callers; one branch at the end of `_request`.

### 2. `src/realize/tools/report_handlers.py`

For each of the 4 handlers:
- Add `params["format"] = "csv"` after the existing params dict construction.
- Switch the `await client.get(endpoint, params=params)` call to `await client.get_text(endpoint, params=params)`.
- Drop the dict-mutation block that injects `metadata` into the response (CSV body has no `metadata` slot — pagination state is already echoed in the prefix).
- Replace `format_large_response_with_csv_truncation(response)` with a new `truncate_csv_text(csv_body, max_size_chars=25000)` helper that truncates at line boundaries and appends a clear marker.
- Keep the existing emoji prefix line (`"🏆 **Campaign Breakdown Report CSV** - Account: ... | Period: ..."`) for at-a-glance context.
- Append `Page: {page} | Size: {page_size}` to the prefix line so pagination state is visible to the LLM since it's no longer in body metadata.

### 3. `src/realize/tools/utils.py`

Add `truncate_csv_text(text: str, max_size_chars: int = 25000) -> str`:
- If body fits, return as-is.
- Otherwise, split on `\n`, accumulate lines until adding one more would exceed budget, append the existing truncation footer ("⚠️ TRUNCATED ..." block).

Keep `format_large_response_with_csv_truncation` and `format_response_as_csv` in place — other (non-report) callers may rely on them, and we don't need to ripple this change beyond reports.

### 4. `tests/test_*` (report-specific files only)

For every test that mocks `client.get` or asserts response shape on a report tool:
- Switch the patch target to `client.get_text` (or both, depending on existing test scaffolding).
- Mock return value: a CSV string instead of a dict.
- Add an assertion that the call passed `params["format"] == "csv"`.
- Drop assertions that index into JSON-shaped response (`response["results"]`, etc.) — those are server-side now.

Test files likely affected (verify when implementing):
- `tests/test_*campaign_breakdown*`
- `tests/test_*campaign_site_day*`
- `tests/test_*top_campaign_content*`
- `tests/test_*campaign_history*`
- Possibly `tests/test_production.py` if any report end-to-end tests live there.

## Reused functions (kept)

- `validate_account_id(account_id)` — `src/realize/tools/utils.py`
- `_request` core in `client.py:78+` — extended via new return-format branch.
- Existing emoji-prefix template lines in `report_handlers.py` — preserved for LLM legibility.
- `format_large_response_with_csv_truncation`, `format_response_as_csv` — left in place for any non-report consumers.

## Smoke test (BEFORE implementing)

Verify the assumption that Backstage's `format=csv` response is actually smaller and well-formed end-to-end:
1. `curl -sS -H "Authorization: Bearer $TOKEN" "https://backstage.taboola.com/backstage/api/1.0/{account}/reports/campaign-history/dimensions/by_account?start_date=...&end_date=...&page=1&page_size=20"` — capture JSON body size.
2. Same call with `&format=csv` — capture CSV body size + content-type.
3. Confirm size ratio (~60-80% reduction expected) and that body is parseable CSV with header row.
4. If CSV body is missing column headers or pagination markers, decide whether to add a tiny header line in the MCP prefix.

## Verification (AFTER implementing)

- `python3 -m pytest tests/ -v` — full suite.
- Manual: call each of the 4 report MCP tools via reconnected MCP and confirm:
  - Response is CSV-formatted text starting with the emoji prefix.
  - LLM-facing output is roughly 60-80% smaller than before for an equivalent date range / page_size.
  - Pagination state (`Page: N | Size: M`) appears in the prefix.
- Optional: re-run the script attached to ITP-43161 against `mcp.realize.com` to measure PROTOCOL_ERROR rate before vs after the switch (script uses `page_size=5` already; run 50 iterations each, compare drop counts).

## Open questions / risks

1. **Backstage CSV column shape** — verify schema matches what the LLM expects. If CSV columns drift between dimensions (e.g. `campaign_breakdown` vs `by_account`), the LLM may need a header hint per tool.
2. **Pagination "Total" exposure** — JSON body had `metadata.total`; CSV doesn't. If LLM relies on knowing total rows for "more data available" prompts, we need to surface this another way (e.g. a separate count call, or skip total-aware prompts).
3. **Other report consumers** — `tests/test_production.py` and any scripts under `scripts/` may assert JSON shape on the same endpoints. Audit before merging.
4. **No fix for underlying SSE drop** — this is a mitigation, not a fix. ITP-43161 still needs SRE attention. Worth re-running the repro script after this change to quantify the improvement.

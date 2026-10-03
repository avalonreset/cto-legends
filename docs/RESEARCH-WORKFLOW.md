# Collect once, inspect and review later

`legends-dataforseo`, `legends-firecrawl` and `legends-empire` have separate
responsibilities. Provider modules collect and preserve source responses.
Empire links reviewed knowledge into the user's chosen workspace. The agent
selects and interprets evidence; no provider response automatically becomes a
business conclusion.

## One workspace, several evidence sources

Choose the client or research workspace before collecting. Keep it outside the
managed module installation and any public source repository. An example is:

```text
client-workspace/
  evidence/
    dataforseo/<evidence-id>/
    firecrawl/<evidence-id>/
  notes/
  deliverables/
```

This is an example project layout, not a new mandatory vault format. An existing
Empire vault remains authoritative. Its inbox and capture/transaction workflow
provide the intake path; module updates do not replace client evidence. Reusable
module instructions are reference material, not a copy of the client's research.

## The evidence lifecycle

1. **Collect and retain.** Use the selected provider module's installed recipe.
   Save the complete response and actual request settings. Record its observation
   time, client/workspace identity and endpoint. Never manufacture missing settings
   or use export time as the observation time.
2. **Export and verify.** Export a portable package containing `response.json`,
   `manifest.json` and `README.md`. Verify it before use or handoff. New packages
   bind both raw response and intake note to a hashed manifest. Older supported
   packages can have weaker note-integrity coverage, which must remain visible.
3. **Find and inspect offline.** Inventory reads small manifests instead of every
   response. It does not certify the raw files. Verify a selected package, then
   inspect a summary, selected fields or the full response. A bounded display
   never truncates the stored evidence.
4. **Check reuse explicitly.** Match workspace, endpoint and complete request;
   select an appropriate maximum age. Pending, failed, stale or incompatible
   observations must not silently substitute for successful current research.
   Eligibility still requires semantic review. A failed reuse check makes no
   provider call and does not authorize a new paid submission.
5. **Bring evidence into Empire.** Load the Empire handoff recipe. Verify and
   plan intake against the selected client scope. Capture through the existing
   supported transaction path, then cite vault-relative sources from reviewed
   notes. Keep observations, hypotheses, proposed actions and measured outcomes
   distinct. Preserve source dates and contradictory evidence.

Use `cto-legends handoff` to load the current installed instructions. The catalog
identifier for `legends-dataforseo` remains `legends-dataforseo` for compatibility.
Offline evidence work needs no provider credentials. New collection still uses
the official providers and their normal authorization and pricing rules.

## What these checks establish

- Hashes detect changed package bytes; they do not authenticate the provider or
  prove a claim is true.
- Workspace labels prevent accidental cross-client matching; they are not access
  controls. Keep private evidence private.
- One complete saved response does not prove all pages or pagination were fetched.
- A recorded cost is a response snapshot, not a new charge on each export or poll.
- Local file benchmarks do not prove provider throughput, proxy protection or
  unlimited concurrency. The saved-response viewer may still load one selected
  response into memory.
- Interrupted exports remain visible for review. Never repurchase evidence just
  because its local indexing or note creation failed.

The advantage over a bare API call is repeatable execution, durable evidence,
selective retrieval and continuity between agents. It is not proprietary data,
automatic strategy, guaranteed savings or universal source coverage.

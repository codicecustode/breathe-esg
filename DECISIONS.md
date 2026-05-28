# Decisions

Every meaningful ambiguity I resolved, and what I'd ask the PM if I had the conversation.

---

## SAP: flat-file CSV over IDoc or OData

**What I chose:** Semicolon-delimited flat-file CSV (the SAP "ALV grid list" download from ME2N or MIGO transaction), German column headers.

**Why:** IDoc is the right choice for real-time integration but requires an RFC/IDoc partner profile configured on the SAP server — that's a two-week engagement with the client's Basis team before we see a single row. OData (via SAP Gateway) is cleaner but also requires the client to have the SAP Gateway component licensed and configured, which many mid-market SAP customers haven't done. The flat-file export is what every SAP user can produce today: go to ME2N, execute, press "Local File" in the ALV toolbar. This is what clients will actually send us while an EDI integration is being scoped.

**What I'd ask the PM:** "Does this client have a dedicated IT liaison who can configure an IDoc outbound channel, or are we working with a sustainability coordinator who can download a file? The answer determines whether flat-file is right long-term or just for the prototype." I'd also ask whether their SAP system locale is German (affects column headers and date formats).

**What I ignored:** Returns (MIGO movement type 122), credit memos, multi-currency POs. The parser handles one currency, one unit per row.

---

## SAP: which materials to treat as emission materials

**What I chose:** Substring match against known fuel keywords (diesel, HSD, natural gas, erdgas, LPG, furnace oil, petrol). Non-matching materials are silently skipped.

**Why:** A real SAP procurement export contains everything: office supplies, raw materials, spare parts. We cannot enumerate every material number. The keyword match catches the common fuel descriptions while skipping noise. It produces false negatives (a fuel described as "D-II Grade" would miss), not false positives.

**What I'd ask the PM:** "Can the client provide a list of SAP material numbers that correspond to fuel categories? A lookup table keyed on Materialnummer would be far more reliable than keyword matching on Materialbezeichnung." This is the single most important improvement for a production version.

---

## Utility: portal CSV over PDF or API

**What I chose:** CSV export from the utility portal billing dashboard.

**Why:** Very few Indian utilities expose a real API. MSEDCL, TPDDL, and BESCOM all have web portals where facility managers log in and download billing history as CSV. A PDF bill would require OCR for the consumption and date fields — OCR on utility bills is unreliable (different templates per utility, scanned vs. born-digital). The portal CSV is the most reliable channel that doesn't require a utility API agreement.

**What I'd ask the PM:** "How many meters does this client have, and are they all on the same utility? If it's 50+ meters across three utilities, we need to think about automated portal scraping or a utility data aggregator like Urjanet. Manual download won't scale."

**What I ignored:** Demand charges (kVA), power factor correction, renewable energy certificates (RECs), time-of-use tariff breakdowns. We only track kWh consumption for emissions purposes.

**The non-calendar billing period problem:** I store `period_start` and `period_end` on every utility record. I do not attempt to allocate consumption to calendar months. The analyst sees the actual billing period (e.g., 16-Dec to 15-Jan) and can make the allocation decision. Automated allocation would require assumptions about consumption uniformity that I shouldn't bake in silently.

---

## Travel: Concur JSON over CSV export or direct API

**What I chose:** Concur expense report batch JSON (the format the Concur v3 API returns, or what you get from the Concur standard extract configured in the Admin portal).

**Why:** Concur is the dominant corporate travel/expense platform in India for enterprise clients. The v3 API returns expense reports as JSON with a well-documented structure. The alternative — Concur's CSV "Standard Extract" — is configurable, meaning the columns vary by client, making a generic parser fragile. JSON via the API has a consistent schema.

For this prototype, the client uploads the JSON export rather than us calling the API directly, because OAuth setup with Concur requires the client's admin to authorize a connected app — that's not a day-one task.

**What I'd ask the PM:** "Is the client on Concur, Navan, or something else? Navan's export format is different. If they're on SAP Concur specifically, we can get a proper OAuth integration scoped for the production sprint."

**What I ignored:** Per-leg fare class (we use the cabin class of the first leg for a multi-stop itinerary), frequent flyer upgrades, actual fuel consumption data from airlines, ground transport categories other than car rental (taxi, ride-share, train).

---

## Flight distance: haversine fallback when Concur doesn't provide it

**What I chose:** Use the `Distance` field from the Concur segment if present; compute haversine great-circle distance from IATA coordinates as fallback.

**Why:** Concur does not guarantee the Distance field. Whether it's populated depends on whether the GDS (Amadeus, Sabre, Travelport) passed it through, and whether the Concur configuration includes it. Our IATA coordinate table covers the major airports relevant to Indian enterprise travel. Haversine underestimates actual flight path (airways routing, wind avoidance) by roughly 5-8% — acceptable for a Scope 3 estimate.

**Flagged as suspicious:** Records where we couldn't determine distance (unknown IATA code) and records over 16,000 km (a circumnavigation — almost certainly a data error).

---

## Emission factors: hardcoded at ingestion time

**What I chose:** Hardcoded emission factors from IPCC 2006 AR5 (fuel combustion), CEA India 2022-23 (grid electricity), DEFRA 2023 (travel), Cornell HSBI 2023 (hotels). Factors stored on the record at parse time.

**Why:** Emission factors must be stable for a given reporting period. If we looked up the factor dynamically at query time, a factor update would silently change all historical calculations — an auditor's approved figure would no longer match what the analyst saw. By storing the factor on the row, the calculation is frozen and reproducible.

**What I'd ask the PM:** "What reporting standard does this client's auditor require — GHG Protocol, ISO 14064, or something else? Some auditors require specific factor databases (e.g., ecoinvent, US EPA). We'd need to make the factor source configurable per client."

---

## Review workflow: flat approve/reject, no multi-step

**What I chose:** A single analyst can approve or reject any record. No concept of reviewer roles, secondary approval, or comment threads.

**Why:** The PM said "let analysts review and sign off before it goes to auditors." For a prototype, one approval step is sufficient. Multi-step workflows (preparer → reviewer → approver) would require a roles system, which is significant scope.

**What I'd ask the PM:** "Does the client's audit process require two signatures? Some auditors require a reviewer and an approver to be different people. If so, we need a two-step workflow before any submission goes to audit."

---

## Authentication: session auth, AllowAny for prototype

**What I chose:** Django session auth configured; API endpoints set to AllowAny for prototype ease.

**Why:** The assignment is a prototype. Enforcing authentication on every API call while there's no login UI would block testing. The production version would use JWT (djangorestframework-simplejwt) with tenant claim.

**What I'd ask the PM:** Nothing — this is clearly a prototype decision to be reversed before any production deployment.

---

## Deployment: single-server, SQLite not supported

**What I chose:** PostgreSQL mandatory (not SQLite) even for local dev.

**Why:** JSONField behavior differs between SQLite and PostgreSQL. `source_metadata` and `raw_data` use JSONField heavily — we need consistent behavior. PostgreSQL also gives us a clear path to row-level security policies.

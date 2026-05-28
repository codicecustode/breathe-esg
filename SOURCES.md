# Sources

For each of the three data sources: what real-world format I researched, what I learned, what the sample data looks like and why, and what would break in a real deployment.

---

## 1. SAP MM — fuel and procurement data

### What I researched

SAP Materials Management (MM) tracks procurement through Purchase Orders (ME2N transaction) and Goods Receipts (MIGO transaction). The flat-file export is what a user gets by executing ME2N or MB51 (material document list), filtering by material group, and clicking the "Local File" icon in the ALV grid — this produces a semicolon-delimited file.

Key real-world characteristics I learned:
- **Column headers are German by default** in SAP systems installed with the German language pack, which covers most European and many Indian enterprise deployments (SAP was installed by a German consulting partner). Common headers: `Belegnummer` (document number), `Belegdatum` (document date), `Menge` (quantity), `Einheit` (unit), `Materialbezeichnung` (material description), `Werksplatz` (plant).
- **Date format is YYYYMMDD** in German-locale systems. English-locale systems may use DD.MM.YYYY. Both formats appear in the wild in the same client.
- **Units are SAP internal codes**: `L` (liters), `KG`, `M3` (cubic meters — note the digit, not superscript), `TON`, `ST` (Stück, pieces). Some customers configure `LT` instead of `L`.
- **Material numbers are 18 characters, zero-padded**: `000000000000050001`. In the export, they appear as strings.
- **Plant codes are 4-digit numeric**: 1000 = headquarters manufacturing plant, 1100 = subsidiary. These mean nothing without the client's own plant code table.
- **Procurement amounts are in local currency** (INR for Indian subsidiaries) without a currency column unless added manually to the ALV layout.

The emission-relevant materials I chose to represent:
- Diesel HSD (High-Speed Diesel) — primary fuel for generators and vehicles
- Furnace Oil — heavy fuel oil for industrial furnaces (common in manufacturing plants)
- Natural Gas / Erdgas — piped gas for heating or process use
- LPG — fork-lifts, canteen

These are the top Scope 1 fuel categories for an Indian manufacturing/corporate client. I chose not to model coal (requires different unit logic — MT of coal has varying calorific value by grade) or aviation turbine fuel (ATF is a Scope 3 item when purchased for third-party flights, Scope 1 for company aircraft).

### What the sample data looks like

`sample_data/sap_fuel_procurement.csv` — 20 rows covering Jan–May 2025, two plants (1000 and 1100), four material types. I included one deliberately suspicious row: document 5000012312 has 52,000 L of diesel — above the 50,000 L threshold — which triggers the anomaly flag. Row 5000012315 is from plant 1100 (Furnace Oil, April) to add source diversity.

Amounts are realistic for Indian industrial procurement: diesel at ₹80/L, natural gas at ₹80/m3, LPG at ₹60/kg.

### What would break in a real deployment

1. **Material description as the only matching key.** The parser does substring matching on `Materialbezeichnung`. A site that calls diesel "D-II Grade Fuel" or "HSD-50 ppm" will miss. The only reliable key is material number, which requires a client-specific lookup table.
2. **Multi-plant, multi-currency.** If a client runs subsidiaries in Germany (EUR) and India (INR), amounts are in different currencies with no currency column. We'd need the plant-to-currency mapping to normalize amounts (we don't use amounts for emissions, but it matters for cost reporting).
3. **Returns and credit memos.** MIGO movement type 122 (return to vendor) has a negative quantity in the export. Our parser treats qty ≤ 0 as suspicious rather than subtracting from cumulative consumption. A real deployment needs to handle returns properly.
4. **ALV layout variation.** The column order and which columns are included depend on the user's saved ALV layout. Our parser maps by column header name, not position, but if a client has renamed columns in their layout, the mapping fails silently.

---

## 2. Utility portal CSV — electricity consumption

### What I researched

Major Indian utilities (MSEDCL covering Maharashtra, BESCOM covering Bengaluru, TPDDL covering Delhi) all have enterprise billing portals where a facility manager can log in, select a date range, and download a CSV of all bills for all meters registered to that consumer account.

Key real-world characteristics I learned:
- **Billing cycles do not align with calendar months.** MSEDCL bills HT (High Tension, industrial) consumers on approximately 30-day cycles starting from the meter installation date. A meter installed on the 15th will always bill from the 15th to the 14th of the following month. This is a known issue for ESG reporting, which requires calendar-month allocation. I chose to preserve the actual billing period and leave allocation to the analyst.
- **Meter IDs follow utility-specific formats.** MSEDCL uses `MR/H/{city}/{8-digit number}`. TPDDL uses `{zone code}/{sequence}`. We accept any string.
- **Opening and closing readings.** Most utility CSVs include both the opening meter reading (kWh at start of period) and the closing reading (kWh at end). Total consumption = closing − opening. Some exports include only total units. We handle both.
- **Tariff codes.** `HT-I` and `HT-II` are industrial high-tension tariffs. `LT-COM` is low-tension commercial. These affect the rate per kWh but not the emission calculation (we use grid emission factor regardless of tariff).
- **Column name variation.** MSEDCL's portal uses "Opening Reading" and "Closing Reading." BESCOM uses "Previous Reading" and "Current Reading." TPDDL uses "Opening (kWh)" and "Closing (kWh)." We handle all variants via COLUMN_ALIASES.

The emission factor I used: **0.716 kg CO2e/kWh** from the Central Electricity Authority (CEA) India Grid Emission Factor report for 2022-23. This is the national average (location-based). A market-based calculation using RECs would require a different approach.

### What the sample data looks like

`sample_data/utility_electricity.csv` — 15 rows across three meters: two industrial (HT-I, HT-II) and one commercial (LT-COM). The billing periods are deliberately offset from calendar months (16th-to-15th for the Pune HT-I meter, 19th-to-18th for the Mumbai meter) to reflect the real-world billing cycle problem. Consumption figures are realistic: 14,000–17,000 kWh/month for a mid-sized industrial meter, 3,000–3,500 kWh/month for an LTO commercial office.

### What would break in a real deployment

1. **Non-calendar billing periods require month-allocation logic.** A Scope 2 report requires calendar-month totals. The 16-Dec to 15-Jan billing period needs to be split as ~50% December, ~50% January. We store the period but don't split. This is deferred to the analyst.
2. **Multiple utilities.** A client with sites across Maharashtra, Karnataka, and Delhi has bills from MSEDCL, BESCOM, and TPDDL — each with slightly different CSV formats. Our COLUMN_ALIASES handles the common variations but not everything.
3. **Demand charges excluded.** Indian HT bills include both energy charges (₹/kWh) and demand charges (₹/kVA). We only capture kWh. Maximum demand (kVA) is irrelevant for emission calculations but matters for cost reporting.
4. **Rooftop solar net metering.** A building with solar panels will have a net metering bill where exported units are subtracted. Our parser will read the net consumption, which is correct for Scope 2 (we consume from the grid only the net), but the total generation should arguably be reported as an offset separately.

---

## 3. Concur corporate travel — flights, hotels, car rental

### What I researched

SAP Concur is the dominant expense management platform for Indian enterprise clients (Tata, Infosys, Wipro, HUL all use it). The Concur v3 API returns expense reports as JSON via the `/api/v3.0/expense/reports` endpoint, with entries nested under each report. The Concur Standard Extract (a batch file option for admins) also produces structured JSON or fixed-width files.

Key real-world characteristics I learned:
- **Distance is not always provided.** The `Distance` field on an air segment is populated only if the travel booking system (GDS: Amadeus, Sabre, or Travelport) included it and the Concur configuration maps it through. In practice, roughly 40-60% of air segments in a Concur export have a distance field. The rest require lookup or calculation.
- **Cabin class matters significantly for emission factors.** DEFRA 2023 economy class factor: 0.151 kg CO2e/pkm (includes radiative forcing). Business class: 0.429 — nearly 3× economy. First class: 0.604 — 4×. Many organizations have a policy of economy class for domestic and business class for long-haul; the split matters for Scope 3 accuracy.
- **Hotel emission factors are difficult.** There is no universally accepted per-night factor. The Cornell Hotel Sustainability Benchmarking (CHSB) index gives 31.4 kg CO2e/room-night as a global average. Property-level factors exist in some databases (HCMI) but require the hotel's own reporting. We use the CHSB global average with a flag that this is an estimate.
- **Car rental distance is almost never provided.** Concur captures the rental duration and vehicle class but not odometer readings. We fall back to 100 km/day as a heuristic (typical urban business travel day) and flag these records as suspicious.
- **JSON structure is nested.** One expense report contains multiple entries of different types. One AIRFARE entry can contain multiple air segments (outbound + return in one booking). Our parser creates one NormalizedEmissionRecord per segment.

### What the sample data looks like

`sample_data/travel_concur_export.json` — 4 expense reports:
1. **Domestic business trip (EMP-1042):** DEL→BOM economy return, 2 nights at Taj Lands End, car rental. BOM→DEL return segment intentionally has no Distance field to demonstrate the haversine fallback.
2. **International long-haul (EMP-2218):** BLR→LHR business class return, 7-night hotel in London. The LHR→BLR return also lacks a Distance field.
3. **Regional international (EMP-0887):** HYD→SIN economy return, 4-night hotel, car rental with no EstimatedKm (demonstrates the 100 km/day heuristic and suspicious flag).
4. **Domestic short-haul (EMP-1042 again):** DEL→CCU economy return, 2 nights. Both segments lack distance (CCU is in our IATA table, so haversine will compute it).

The cabin classes and routes are realistic for an Indian enterprise: domestic travel is mostly economy, international executive travel is business class. Airport codes are all in our IATA coordinate table except for the LHR test case (which is also in the table), so haversine fallback will produce a result in all cases.

### What would break in a real deployment

1. **Unknown IATA codes.** An export with a tier-2 airport (e.g., `BHO` for Bhopal, `IXC` for Chandigarh) not in our 17-airport table will produce a distance of 0 and be flagged suspicious. The IATA table needs to be extended or we need an external IATA distance API.
2. **Non-Concur platforms.** Navan (formerly TripActions), Egencia, and Happay are increasingly common in Indian startups and mid-market. Their export formats differ. A Navan CSV doesn't have a `Reports > Entries > AirSegments` structure.
3. **Multi-passenger bookings.** A group booking for 5 employees on one Concur report should produce 5× the flight emissions. Concur doesn't reliably flag whether a single report represents one or multiple travelers. We assume 1 pax per entry — this could materially undercount.
4. **Radiative forcing debate.** We apply DEFRA 2023 factors which include a radiative forcing index (RFI) multiplier. Some auditors require GHG Protocol Category 6 factors without RFI. The factor used is stored on every record, but there's no UI to re-run calculations with a different factor set.

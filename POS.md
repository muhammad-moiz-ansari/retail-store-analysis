# Pillar 2: Product Interaction + POS Conversion Funnel

Part of the retail analytics FYP (3-pillar platform: engagement tracking, product/POS funnel, trajectory+heatmap). This document covers **only Pillar 2**.

---

## 1. Scope & Ground Rules

- **No CV for product-level detection.** Product identification, quantity, and price come from **POS transaction data**, not from a camera model. This was a deliberate scope decision to avoid an unreliable shelf-level product-detection CV problem.
- Conversion analytics are built with a **traditional ML pipeline** on structured POS data (not deep learning).
- **No external trend data** (e.g. Google Trends). "Trend" is scoped to **in-house relative sales comparison** between competing SKUs (e.g. Knorr vs Maggi noodles) using only the store's own POS history.
- Full CV-driven footfall→purchase funnel and shelf-level product interaction as a standalone CV feature are **descoped**.
- Staffing/insight outputs use **zone/shift assignment** (e.g. "Zone A, 9am–1pm") rather than named-employee identity, to avoid Re-ID-to-identity linkage and privacy exposure.

---

## 2. Data Sources

| Source | Data | Notes |
|---|---|---|
| POS system | Transaction line items: SKU, qty, unit price, timestamp, till/counter ID | Primary source for this pillar — no CV involved |
| Entrance camera | Footfall count (timestamped) | Used only for store-level conversion rate (footfall → transactions), not per-product |
| Zone/shift roster | Zone ID, shift window, staff count per zone | Manually maintained or simple CSV/roster upload — no employee identity in the CV layer |

### Minimum POS schema
```
transaction_id | timestamp | till_id | sku_id | sku_name | category | qty | unit_price | total_price
```

### Implemented import contracts

The current implementation accepts separate CSV files named `transactions.csv`, `inventory.csv`, `footfall.csv`, and optionally `calendar.csv`, or one XLSX workbook with sheets named `transactions`, `inventory`, `footfall`, and `calendar`.

Transaction columns preserve the minimum POS schema and add optional `line_item_id`, `business_date`, `unit_cost`, and `transaction_type` (`sale`, `refund`, `void`). Refund signs are normalized once; inconsistent refund signs are rejected.

Inventory snapshots use `snapshot_at`, `sku_id`, and `on_hand`, with optional `on_order`, `receipt_due_at`, `lead_time_days`, `safety_stock_units`, `unit_cost`, and `comparison_group`. Dated incoming stock can affect projections; undated on-order stock is shown as a warning and is not used to prevent projected stockouts.

Footfall events use `event_id`, `timestamp`, `direction` (`in`/`out`), and `camera_id`. A deterministic fallback ID is accepted only when a stable source sequence column is supplied. Existing two-video sampled totals are not consumed as entrance events.

Opening calendar rows use `date` and `is_open`. Without a complete opening calendar, missing sales days are treated as unknown coverage and forecasts are marked low confidence.

---

## 3. Feature Set (Traditional ML)

Since there's no CV product detection, features are engineered entirely from POS + footfall timestamps:

- **Store-level conversion rate**: transactions / footfall count, per hour/day
- **Basket-level features**: basket size, average basket value, items per basket
- **SKU-level time series**: units sold per SKU per hour/day/week
- **Relative trend comparison**: normalized sales-share ratio between two or more competing SKUs over a rolling window (e.g. Knorr vs Maggi noodles weekly share)
- **Category-level seasonality**: day-of-week / hour-of-day sales patterns per category
- **Zone/shift correlation**: sales performance during a given zone's shift window (feeds the Recommendation agent, not raw CV)

---

## 4. Modeling Approach

| Task | Method |
|---|---|
| Sales forecasting (SKU/category level) | Seasonal naive and lag/weekly average fallback with rolling validation hooks |
| Relative trend / competing-SKU comparison | Rolling-window share-of-sales ratio + simple regression for trend direction |
| Anomaly detection (sales spikes/drops) | Statistical thresholding (z-score / IQR) or Isolation Forest on time series residuals |
| Conversion funnel (footfall → transaction) | Simple ratio metric — not a per-product CV funnel |

No deep learning is planned for this pillar — it's intentionally lightweight given the CV budget is spent on Pillars 1 and 3.

---

## 5. AI Agent Layer (on top of this pillar's outputs)

Per the project's agent layer plan, this pillar feeds at least these agents:

- **Insight Narration Agent** — turns SKU/category trend numbers into a plain-language summary (e.g. "Knorr noodles outsold Maggi by 18% this week, reversing last month's trend")
- **Anomaly Investigation Agent** — flags and explains sudden sales/conversion drops
- **NL Query Agent** — lets a manager ask "how did Zone A do during the morning shift?" against the POS + zone data
- **Recommendation/Planning Agent** — suggests staffing or restocking actions using zone/shift correlation, not employee identity

**LLM constraints:** paid APIs are not allowed for this layer.
- Main agent reasoning → Hugging Face free Inference API (per-store API keys)
- Real-time zone/shift assignment tasks → a smaller local 3B model

These agents sit **above** the deterministic ML/statistics code above — they narrate and reason over already-computed metrics, they don't replace the ML pipeline.

---

## 6. Current POS Analytics Implementation

- Persistent FastAPI service: `backend.pos_service:app`
- Versioned SQLite storage: `backend/pos_analytics.sqlite3` by default
- Next.js proxy routes: `/api/pos/templates`, `/api/pos/import/preview`, `/api/pos/import/commit`, `/api/pos/analysis`, `/api/pos/analytics`, `/api/pos/jobs/{id}`, and `/api/pos/query`
- Manager access: configured local manager credential creates a signed, expiring HttpOnly cookie; the POS backend proxy uses a server-held internal secret
- Deterministic outputs: net revenue, gross sold demand, refunds, sale transactions, basket metrics, category share, conversion buckets, low-history forecasts, anomaly flags, and `RESTOCK`/`MONITOR`/temporary `HOLD` recommendations
- RAG boundary: assistant answers retrieve evidence generated from analytics runs and cite internal evidence IDs; unsupported questions return insufficient evidence
- Defaults: PKR, `Asia/Karachi`, single-store, 7-day lead time, and derived safety stock when not supplied

## 7. Open / Unresolved Items

- Real-time dashboard vs. offline batch report as the primary deliverable format — current POS implementation runs local on-demand batch analysis.
- Exact roster format/ingestion method for zone/shift data — not yet finalized.
- Production forecasting model choice and calibration — the current implementation exposes rolling validation results and low-history fallback behavior, but does not yet ship ARIMA/Prophet.

---

## 8. Explicitly Out of Scope for This Pillar

- CV-based shelf/product detection
- Named-employee identity or Re-ID-to-identity linkage
- External trend signals (Google Trends, etc.)
- Multi-camera dedup (belongs to Pillar 3, not this one)
- Paid LLM APIs anywhere in the agent layer

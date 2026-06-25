# IHSG Fundamental Smart Screener (Beta Access)

## Original Problem Statement
- Build a single-page web application for stock screening based on fundamental data from the Indonesian Stock Exchange (IHSG).
- Public beta access with no login required.
- Use a static placeholder dataset for historical fundamental data in the MVP.
- Include collapsible filters, quick filter themes, reactive results table, sortable columns, and a company detail view with charts.
- Add a Beta Feedback form and a Premium Waitlist CTA.

## User Choices
- Use a realistic mock IHSG dataset seeded in the app.
- Save beta feedback into the app database.
- Save premium waitlist email plus optional note/company interest into the app database.
- Use the detail panel layout that best fits the design.
- Show the last-updated timestamp with automatic date and time.

## User Personas
- Retail investor Indonesia yang ingin memvalidasi ide investasi dengan cepat.
- Investor dividend/value yang butuh shortlist emiten dari filter fundamental.
- Calon pelanggan premium yang tertarik analisis AI dan riset sektoral lebih dalam.

## Architecture Decisions
- Frontend: React single-page dashboard with Tailwind and shadcn/ui components.
- Backend: FastAPI with MongoDB for feedback and waitlist persistence.
- Dataset: seeded static frontend mock dataset for IHSG companies, including quarter financials and yearly ratio trends.
- UI pattern: sticky header, left filter sidebar, right content area, slide-over sheet for company details.
- Charts: Recharts for mini financials and key ratio trends.

## Core Requirements
- Header with app branding, tagline, and beta feedback CTA.
- Collapsible filter groups for valuation, quality/health, dividend season, and quick filter presets.
- Reactive screener logic that updates results immediately on filter change.
- Sortable results table with the required stock/fundamental columns.
- Clickable company detail panel with profile and two charts.
- Automatic “Data terakhir diperbarui” timestamp.
- Premium waitlist CTA with email and optional note.

## What’s Been Implemented
- 2026-06-13: Built FastAPI endpoints for `/api/feedback`, `/api/waitlist`, and `/api/collections/summary` with MongoDB persistence.
- 2026-06-13: Created a realistic mock IHSG dataset with 18 companies and supporting chart series.
- 2026-06-13: Built the screener UI with collapsible filters, quick presets, reactive filtering, sortable results table, and detail slide-over.
- 2026-06-13: Added Beta Feedback dialog, Premium Waitlist card, automatic timestamp, summary counters, and toast feedback.
- 2026-06-13: Verified backend and frontend flows through self-tests plus testing agent; core tested scope passed.
- 2026-06-13: Expanded issuer detail view with richer seeded data, additional issuers, analyst angle, strengths/risks, valuation summary, dividend history, and 3-year financial tables.
- 2026-06-13: Added tabbed issuer detail sections (Overview, Financials, Dividend, Valuation), sector benchmark comparison, and color-coded quality insight badges.
- 2026-06-13: Cleaned up detail-sheet UX by fixing benchmark copy and deferring chart mount during tab transitions to reduce rendering warnings.
- 2026-06-14: Reworked the data path so the primary live screener reads the shared TradingView screen `https://www.tradingview.com/screener/AKYzoJyg/`, calls the TradingView scanner API, caches enriched results, and runs a local AI-style analysis agent to produce investment scores, key summaries, reasons to invest, and primary risks.

## Prioritized Backlog

### P0
- Add export/share actions for filtered results.
- Add more edge-case handling around empty result combinations and mobile density refinements.

### P1
- Add richer company detail tabs (cash flow, dividends, margin history, notes).
- Add saved screener presets in browser storage.
- Expand dataset coverage and sector-specific badges/insights.

### P2
- Add benchmark comparison against IHSG sector averages.
- Add premium teaser modules such as AI earnings projection preview cards.
- Add onboarding tips/tooltips for beginner investors.

## Next Tasks List
- Expand mock data fields for deeper company drill-down.
- Add export/watchlist-style convenience features.
- Strengthen analytics and conversion touchpoints around premium waitlist intent.

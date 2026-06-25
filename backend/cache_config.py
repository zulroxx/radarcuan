"""Centralised TTL (time‑to‑live) configuration for all cached JSON files.

Values are in **seconds**.  The scheduler and each agent should import this
module and use ``CACHE_TTL["<cache_key>"]`` instead of hard‑coding numbers.
"""

CACHE_TTL = {
    # Stock recommendation cache used by stock_recommender_agent
    "stock_recommendations": 3600,  # 1 hour
    # News‑flow cache used by news_flow_agent
    "news_flow": 1800,               # 30 minutes
    # Sector prediction cache used by sector_predictor_agent
    "sector_prediction": 1800,       # 30 minutes
}

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from db_cache import set_cached, set_cached_sector_recommendations

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent

SCHEDULE_INTERVAL = 14400  # 4 hours


async def store_tradingview_to_mongo(db) -> int:
    """Fetch TradingView data and store in MongoDB."""
    try:
        from tradingview_agent import fetch_and_analyze_tradingview_screen

        loop = asyncio.get_event_loop()
        records, summary, metadata = await loop.run_in_executor(
            None, lambda: fetch_and_analyze_tradingview_screen(limit=500)
        )

        if not records:
            logger.warning("TradingView: no records returned")
            return 0

        strong_buy_count = sum(
            1 for item in records if item.get("Rekomendasi Analis") == "Pembelian kuat"
        )
        await set_cached(db, "tradingview", {
            "data": records,
            "total": len(records),
            "strong_buy_count": strong_buy_count,
            "analysis_summary": summary,
            "metadata": metadata,
        })
        logger.info(f"TradingView: {len(records)} records stored")
        return len(records)
    except Exception as e:
        logger.error(f"TradingView fetch failed: {e}")
        return 0


async def store_macro_to_mongo(db) -> int:
    """Fetch macro indicators (parallel yfinance) and store in MongoDB."""
    try:
        from macro_agent import fetch_live_data_async, BASE_MACRO_DATA, now_iso

        live = await fetch_live_data_async()
        timestamp = now_iso()

        indicators = []
        for item in BASE_MACRO_DATA:
            indicator = dict(item)
            ind_id = indicator["id"]

            if ind_id in live and live[ind_id] is not None:
                live_val = live[ind_id]
                default_val = float(indicator["defaultValue"].replace(",", ""))
                if default_val != 0:
                    indicator["change"] = round(
                        ((live_val - default_val) / default_val) * 100, 2
                    )
                indicator["liveValue"] = live_val

                if ind_id in ("usd_idr",):
                    indicator["value"] = f"{live_val:,.0f}"
                elif ind_id in ("ihsg", "sp500"):
                    indicator["value"] = f"{live_val:,.1f}"
                elif ind_id in ("nikkei", "hsi"):
                    indicator["value"] = f"{live_val:,.0f}"
                elif ind_id == "oil_price":
                    indicator["value"] = f"${live_val:.2f}"
                else:
                    indicator["value"] = str(live_val)
            else:
                indicator["value"] = indicator["defaultValue"]

            indicator["updated_at"] = timestamp
            indicators.append(indicator)

        await set_cached(db, "macro", {
            "indicators": indicators,
            "total": len(indicators),
        })
        logger.info(f"Macro: {len(indicators)} indicators stored")
        return len(indicators)
    except Exception as e:
        logger.error(f"Macro fetch failed: {e}")
        return 0


async def store_news_to_mongo(db) -> int:
    """Fetch news + AI analysis and store in MongoDB."""
    try:
        from news_flow_agent import fetch_news_from_tradingview, analyze_news, LLM_MODEL
        from news_flow_agent import now_iso as news_now

        loop = asyncio.get_event_loop()
        news_items = await loop.run_in_executor(None, fetch_news_from_tradingview)
        logger.info(f"News: {len(news_items)} items fetched from TV")

        analysis = await loop.run_in_executor(None, analyze_news, news_items)

        result = {
            "news": news_items[:30],
            "analysis": analysis,
            "total_news": len(news_items),
            "generated_at": news_now(),
            "model": LLM_MODEL,
        }
        await set_cached(db, "news", result)
        logger.info(f"News: stored with AI analysis")
        return len(news_items)
    except Exception as e:
        logger.error(f"News fetch failed: {e}")
        return 0


async def store_sector_predictions_to_mongo(db) -> bool:
    """Generate AI sector predictions and store in MongoDB."""
    try:
        from sector_predictor_agent import predict_sectors

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: predict_sectors(refresh=True))

        await set_cached(db, "sector_predictions", result)
        logger.info("Sector predictions stored")
        return True
    except Exception as e:
        logger.error(f"Sector predictions failed: {e}")
        return False


async def store_stock_recommendations_to_mongo(db) -> int:
    """Generate AI stock recommendations per sector and store in MongoDB."""
    try:
        from sector_predictor_agent import TV_TO_IDX_SECTOR

        sectors = sorted(set(v for v in TV_TO_IDX_SECTOR.values()))
        stored_count = 0

        for sector in sectors:
            try:
                from stock_recommender_agent import recommend_stocks

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, lambda s=sector: recommend_stocks(sector_name=s, limit=10, refresh=True)
                )

                await set_cached_sector_recommendations(db, sector, result)
                stored_count += 1
                logger.info(f"Stock recommendations for {sector} stored")
            except Exception as e:
                logger.warning(f"Stock recommendations for {sector} failed: {e}")

        return stored_count
    except Exception as e:
        logger.error(f"Stock recommendations batch failed: {e}")
        return 0


async def run_scheduled_fetch(db) -> Dict[str, Any]:
    """Run all data fetches and store results in MongoDB."""
    logger.info("=" * 60)
    logger.info("SCHEDULED FETCH STARTING")
    logger.info("=" * 60)

    results = {}

    results["tradingview"] = await store_tradingview_to_mongo(db)
    results["macro"] = await store_macro_to_mongo(db)
    results["news"] = await store_news_to_mongo(db)
    results["sector_predictions"] = await store_sector_predictions_to_mongo(db)
    results["stock_recommendations"] = await store_stock_recommendations_to_mongo(db)

    logger.info("=" * 60)
    logger.info(f"SCHEDULED FETCH COMPLETE: {results}")
    logger.info("=" * 60)

    return results


async def initial_fetch_if_empty(db) -> bool:
    """Check if MongoDB has data, trigger initial fetch if empty."""
    from db_cache import COLLECTIONS

    needs_fetch = False
    for cache_key in COLLECTIONS:
        try:
            doc = await db[COLLECTIONS[cache_key]].find_one({"_id": "main"})
            if not doc:
                needs_fetch = True
                break
        except Exception:
            needs_fetch = True
            break

    if needs_fetch:
        logger.info("MongoDB cache empty, triggering initial fetch...")
        await run_scheduled_fetch(db)
        return True
    else:
        logger.info("MongoDB cache already populated")
        return False

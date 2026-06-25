import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_metrics import agent_metrics, ExecutionTimer
from agent_status import update_agent_status
from alert_manager import alert_manager
from cache_versioning import cache_version_manager
from circuit_breaker import circuit_breaker_registry
from db_cache import get_cached, set_cached, set_cached_sector_recommendations
from llm_audit_log import llm_audit_log
from llm_rate_limiter import global_llm_limiter
from rate_limiter import async_rate_delay

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent

SCHEDULE_INTERVAL = 14400  # 4 hours
_scheduler_lock = asyncio.Lock()
_SCHEDULER_RUN_ID: Optional[str] = None
_scheduler_cancelled = False
_scheduler_cancel_event = asyncio.Event()
_scheduler_lock_acquired_at: Optional[float] = None
_scheduler_start_time: Optional[float] = None
_scheduler_current_agent_idx: Optional[int] = None
_scheduler_agent_start_time: Optional[float] = None
_SCHEDULER_AGENTS_ORDER = [
    "tradingview", "macro", "news_flow", "sector_predictions",
    "stock_recommendations", "order_book",
]
MAX_LOCK_HOLD_SECONDS = 1800  # 30 menit, auto-release jika lock terlanjur korup
AGENT_TIMEOUT = 600  # 10 menit per agent, cegah stuck selamanya

CONCURRENCY_LIMIT = 4  # max concurrent LLM calls for stock recommendations


def is_scheduler_running() -> bool:
    """Public check: is a scheduled fetch currently in progress?"""
    return _scheduler_lock.locked()


def current_run_id() -> Optional[str]:
    """Public accessor for the active run ID."""
    return _SCHEDULER_RUN_ID


async def cancel_scheduler() -> bool:
    """Cancel the currently running scheduler fetch if any.
    
    Returns:
        bool: True if the scheduler was running and has been cancelled, False otherwise.
    """
    global _scheduler_cancelled
    if not is_scheduler_running():
        return False
    
    _scheduler_cancelled = True
    _scheduler_cancel_event.set()
    _SCHEDULER_RUN_ID = None
    update_agent_status("scheduler", "cancelled", "Scheduler cancelled by user")
    logger.info("Scheduler cancelled by user request")
    return True


def reset_scheduler_cancelled_flag() -> None:
    """Reset the cancelled flag for a new scheduler run."""
    global _scheduler_cancelled
    _scheduler_cancelled = False
    _scheduler_cancel_event.clear()


TV_FETCH_TIMEOUT = 300  # 5 menit untuk TradingView screen

async def store_tradingview_to_mongo(db) -> int:
    """Fetch TradingView data and store in MongoDB + file cache.
    Falls back to cached data if external API times out or fails."""
    breaker = await circuit_breaker_registry.get_breaker("tradingview")
    
    if not await breaker.can_execute():
        logger.warning("TradingView: circuit breaker OPEN, skipping")
        return 0

    if db is not None:
        cached = await get_cached(db, "tradingview")
        if cached and cached.get("data"):
            logger.info("TradingView: data sudah ada di MongoDB, skip fetch external API")
            return len(cached["data"])
    
    try:
        from tradingview_agent import fetch_and_analyze_tradingview_screen

        try:
            loop = asyncio.get_event_loop()
            records, summary, metadata = await asyncio.wait_for(
                loop.run_in_executor(
                    None, lambda: fetch_and_analyze_tradingview_screen(limit=500)
                ),
                timeout=TV_FETCH_TIMEOUT
            )
            logger.info("TradingView: fetch external API berhasil")
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"TradingView: fetch external API gagal/timeout, fallback ke cache: {e}")
            await breaker.record_failure()
            if cached and cached.get("data"):
                return len(cached["data"])
            return 0

        if not records:
            logger.warning("TradingView: no records returned")
            await breaker.record_failure()
            if cached and cached.get("data"):
                return len(cached["data"])
            return 0

        strong_buy_count = sum(
            1 for item in records if item.get("Rekomendasi Analis") == "Pembelian kuat"
        )
        cache_entry = {
            "data": records,
            "total": len(records),
            "strong_buy_count": strong_buy_count,
            "analysis_summary": summary,
            "metadata": metadata,
        }
        await set_cached(db, "tradingview", cache_entry)

        # Always save to file cache for within-container availability
        tv_cache_file = ROOT_DIR / "tradingview_cache.json"
        tv_cache_data = {
            "cached_at": datetime.now(timezone.utc).isoformat(),
            **cache_entry,
        }
        with open(tv_cache_file, "w", encoding="utf-8") as f:
            json.dump(tv_cache_data, f, ensure_ascii=False, indent=2)

        # Increment cache version
        version = await cache_version_manager.increment_version("tradingview")
        logger.info(f"TradingView: {len(records)} records stored, version={version}")
        await breaker.record_success()
        return len(records)
    except Exception as e:
        logger.error(f"TradingView fetch failed: {e}")
        await breaker.record_failure()
        if cached and cached.get("data"):
            return len(cached["data"])
        return 0


MACRO_FETCH_TIMEOUT = 120  # 2 menit untuk fetch external API

async def store_macro_to_mongo(db) -> int:
    """Fetch macro indicators (parallel yfinance) and store in MongoDB + file cache.
    Falls back to cached data if external API times out or fails."""
    breaker = await circuit_breaker_registry.get_breaker("macro")
    
    if not await breaker.can_execute():
        logger.warning("Macro: circuit breaker OPEN, skipping")
        return 0

    if db is not None:
        cached = await get_cached(db, "macro")
        if cached and cached.get("indicators"):
            logger.info("Macro: data sudah ada di MongoDB, skip fetch external API")
            return len(cached["indicators"])
    
    try:
        from macro_agent import fetch_live_data_async, BASE_MACRO_DATA, now_iso, save_cache as macro_save_cache

        try:
            live = await asyncio.wait_for(
                fetch_live_data_async(),
                timeout=MACRO_FETCH_TIMEOUT
            )
            logger.info("Macro: fetch external API berhasil")
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"Macro: fetch external API gagal/timeout, fallback ke cache: {e}")
            await breaker.record_failure()
            if cached and cached.get("indicators"):
                return len(cached["indicators"])
            return 0

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

        # Always save to file cache for within-container availability
        macro_save_cache(indicators)

        # Increment cache version
        version = await cache_version_manager.increment_version("macro")
        logger.info(f"Macro: {len(indicators)} indicators stored, version={version}")
        await breaker.record_success()
        return len(indicators)
    except Exception as e:
        logger.error(f"Macro fetch failed: {e}")
        await breaker.record_failure()
        if cached and cached.get("indicators"):
            return len(cached["indicators"])
        return 0


async def store_news_to_mongo(db) -> int:
    """Fetch news + AI analysis and store in MongoDB + file cache."""
    breaker = await circuit_breaker_registry.get_breaker("news_flow")
    
    if not await breaker.can_execute():
        logger.warning("News: circuit breaker OPEN, skipping")
        return 0
    
    try:
        from news_flow_agent import fetch_news_from_tradingview, analyze_news, LLM_MODEL
        from news_flow_agent import now_iso as news_now
        from news_flow_agent import save_cache as news_save_cache

        # Acquire LLM rate limiter
        llm_acquired = await global_llm_limiter.acquire()
        if not llm_acquired:
            logger.warning("News: LLM rate limit exceeded, skipping")
            return 0
        
        try:
            loop = asyncio.get_event_loop()
            news_items = await loop.run_in_executor(None, fetch_news_from_tradingview)
            logger.info(f"News: {len(news_items)} items fetched from TV")

            analysis = await loop.run_in_executor(None, analyze_news, news_items)

            is_error = (
                "Gagal" in analysis.get("ringkasan_1hari", "")
                or "Tidak ada" in analysis.get("ringkasan_1hari", "")
            )
            if is_error:
                logger.warning("News analysis returned error, skipping save")
                await breaker.record_failure()
                return len(news_items)

            used_model = analysis.pop("_model", LLM_MODEL) if isinstance(analysis, dict) else LLM_MODEL
            result = {
                "news": news_items[:30],
                "analysis": analysis,
                "total_news": len(news_items),
                "generated_at": news_now(),
                "model": used_model,
            }
            await set_cached(db, "news_flow", result)

            # Always save to file cache for within-container availability
            news_save_cache(result)

            # Increment cache version
            version = await cache_version_manager.increment_version("news_flow")
            logger.info(f"News: stored with AI analysis, version={version}")
            await breaker.record_success()
            await global_llm_limiter.record_success()
            return len(news_items)
        finally:
            await global_llm_limiter.release()
    except Exception as e:
        logger.error(f"News fetch failed: {e}")
        await breaker.record_failure()
        await global_llm_limiter.record_failure()
        return 0


async def store_sector_predictions_to_mongo(db) -> bool:
    """Generate AI sector predictions and store in MongoDB."""
    breaker = await circuit_breaker_registry.get_breaker("sector_predictions")
    
    if not await breaker.can_execute():
        logger.warning("Sector predictions: circuit breaker OPEN, skipping")
        return False
    
    try:
        from sector_predictor_agent import predict_sectors

        # Acquire LLM rate limiter
        llm_acquired = await global_llm_limiter.acquire()
        if not llm_acquired:
            logger.warning("Sector predictions: LLM rate limit exceeded, skipping")
            return False
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: predict_sectors(refresh=True))

            has_data = any(len(items) > 0 for items in result.get("predictions", {}).values())
            if has_data:
                await set_cached(db, "sector_predictions", result)
                version = await cache_version_manager.increment_version("sector_predictions")
                logger.info(f"Sector predictions stored, version={version}")
            else:
                logger.warning("Sector predictions empty, NOT saving to MongoDB cache")

            await breaker.record_success()
            await global_llm_limiter.record_success()
            return has_data
        finally:
            await global_llm_limiter.release()
    except Exception as e:
        logger.error(f"Sector predictions failed: {e}")
        await breaker.record_failure()
        await global_llm_limiter.record_failure()
        return False


async def store_stock_recommendations_to_mongo(db) -> int:
    """Generate AI stock recommendations per sector concurrently and store in MongoDB."""
    breaker = await circuit_breaker_registry.get_breaker("stock_recommendations")
    
    if not await breaker.can_execute():
        logger.warning("Stock recommendations: circuit breaker OPEN, skipping")
        return 0
    
    try:
        from stock_recommender_agent import recommend_stocks_batch
        from sector_constants import IDX_SECTORS

        run_id = _SCHEDULER_RUN_ID or uuid.uuid4().hex[:8]

        loop = asyncio.get_event_loop()
        batch_result = await loop.run_in_executor(
            None, lambda: recommend_stocks_batch(sectors=IDX_SECTORS, limit=5)
        )

        stored_count = batch_result.get("stored", 0)
        method = batch_result.get("method", "unknown")
        logger.info(f"[run={_SCHEDULER_RUN_ID or '?'}] Batch stock recs: {method} — {stored_count}/{len(IDX_SECTORS)} sectors stored")

        # Sync per-sector results to MongoDB
        sector_results = batch_result.get("sector_results", {})
        for sector, result in sector_results.items():
            try:
                await set_cached_sector_recommendations(db, sector, result)
            except Exception as e:
                logger.warning(f"Gagal sync MongoDB untuk {sector}: {e}")

        if stored_count > 0:
            version = await cache_version_manager.increment_version("stock_recommendations")
            logger.info(f"[run={_SCHEDULER_RUN_ID or '?'}] Stock recommendations version={version}")
            await breaker.record_success()
        else:
            await breaker.record_failure()

        return stored_count
    except Exception as e:
        logger.error(f"Stock recommendations batch failed: {e}")
        await breaker.record_failure()
        return 0


ORDER_BOOK_FILE = ROOT_DIR / "agent_cache" / "order_book_history.json"
TIMEFRAME_DAYS = {"1M": 30, "3M": 90, "6M": 180, "12M": 365}


def _validate_order_book_dependencies() -> tuple[bool, str]:
    """Validate dependencies for Order Book agent.
    
    Returns:
        (success, reason): True jika semua dependency valid
    """
    from sector_predictor_agent import load_cached_predictions
    from stock_recommender_agent import load_cached_recommendations
    from datetime import datetime, timezone
    
    # Check 1: Sector predictions harus ada
    predictions_data = load_cached_predictions()
    if not predictions_data:
        return False, "Sector predictions cache kosong"
    
    predictions = predictions_data.get("predictions", {})
    if not predictions or all(not v for v in predictions.values()):
        return False, "Sector predictions empty"
    
    # Check 2: Sector predictions cache masih fresh (< 1 jam)
    cached_at = predictions_data.get("generated_at")
    if cached_at:
        try:
            cached_time = datetime.fromisoformat(cached_at.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - cached_time).total_seconds()
            if age > 3600:
                return False, f"Sector predictions stale ({age:.0f}s > 3600s)"
        except (ValueError, TypeError):
            pass
    
    # Check 3: Top sector harus punya stock recommendations
    top_sector_name = None
    for tf in TIMEFRAME_DAYS:
        preds = predictions.get(tf, [])
        if preds:
            top_sector_name = preds[0].get("sector")
            break
    
    if top_sector_name:
        stock_recs = load_cached_recommendations(top_sector_name, 2)
        if not stock_recs or not stock_recs.get("recommendations"):
            return False, f"Stock recommendations untuk {top_sector_name} kosong"
    
    return True, "OK"


async def store_order_book_to_mongo(db) -> bool:
    """Generate order book snapshot — append-only, buy_price never changes."""
    breaker = await circuit_breaker_registry.get_breaker("order_book")
    
    if not await breaker.can_execute():
        logger.warning("Order book: circuit breaker OPEN, skipping")
        return False
    
    # Validate dependencies first
    deps_valid, deps_reason = _validate_order_book_dependencies()
    if not deps_valid:
        logger.warning(f"Order book: dependency check failed - {deps_reason}")
        await breaker.record_failure()
        return False
    
    from order_book_store import OrderBookStore

    store = OrderBookStore(mongo_db=db, file_path=ORDER_BOOK_FILE)

    try:
        from datetime import date, timedelta
        import uuid as uuid_mod

        import yfinance as yf
        _tz_dir = ROOT_DIR / "agent_cache" / "yfinance_tz"
        _tz_dir.mkdir(parents=True, exist_ok=True)
        yf.set_tz_cache_location(str(_tz_dir))

        from sector_predictor_agent import load_cached_predictions
        from stock_recommender_agent import load_cached_recommendations
        from macro_agent import get_macro_indicators

        predictions_data = load_cached_predictions()
        predictions = (predictions_data or {}).get("predictions", {})
        if not predictions or all(not v for v in predictions.values()):
            logger.warning("Order book: belum ada prediksi sektor")
            await breaker.record_failure()
            return False

        existing_map = await store.load_existing_order_map()

        all_new_tickers = set()
        timeframe_sectors = {}

        for tf in TIMEFRAME_DAYS:
            preds = predictions.get(tf, [])
            if not preds:
                continue
            top_sector = preds[0]
            sector_name = top_sector["sector"]
            stocks_data = load_cached_recommendations(sector_name, 2) or {}
            stock_recs = stocks_data.get("recommendations", [])[:2]
            for s in stock_recs:
                key = (tf, s["ticker"])
                if key not in existing_map:
                    all_new_tickers.add(s["ticker"])
            timeframe_sectors[tf] = {
                "sector": top_sector,
                "stocks": stock_recs,
            }

        all_tickers = set(all_new_tickers)
        for (ex_tf, ex_ticker) in existing_map.keys():
            if any(ex_tf == tf for tf in TIMEFRAME_DAYS):
                all_tickers.add(ex_ticker)

        async def _fetch_price(ticker: str):
            try:
                tk = await asyncio.to_thread(yf.Ticker, f"{ticker}.JK")
                hist = await asyncio.to_thread(lambda: tk.history(period="1d"))
                if not hist.empty:
                    return ticker, round(float(hist["Close"].iloc[-1]), 2)
                info = await asyncio.to_thread(lambda: tk.info)
                if info and "regularMarketPrice" in info:
                    return ticker, round(float(info["regularMarketPrice"]), 2)
            except Exception:
                pass
            return ticker, None

        tasks = [_fetch_price(t) for t in all_tickers]
        results = await asyncio.gather(*tasks)
        prices = dict(results)

        today = date.today()
        simulations = []
        for tf in TIMEFRAME_DAYS:
            existing_stocks = []
            new_stocks = []

            if tf in timeframe_sectors:
                info = timeframe_sectors[tf]
                top_sector = info["sector"]
                sector_name = top_sector["sector"]
                predicted_return = top_sector.get("predicted_return", 0)
                stocks_data = info["stocks"]
                buy_date = today.isoformat()
                sell_date = (today + timedelta(days=TIMEFRAME_DAYS[tf])).isoformat()
                pred_stock_tickers = {s["ticker"] for s in stocks_data[:2]}

                for stock in stocks_data[:2]:
                    ticker = stock["ticker"]
                    key = (tf, ticker)
                    if key in existing_map:
                        frozen = dict(existing_map[key])
                        frozen_bp = frozen.get("buy_price")
                        if frozen_bp is not None:
                            live_price = prices.get(ticker)
                            if live_price is not None:
                                frozen["current_price"] = live_price
                                if frozen.get("status") == "open":
                                    frozen["actual_return_pct"] = round(
                                        (live_price - frozen_bp) / frozen_bp * 100, 2
                                    )
                            frozen_sell_date = frozen.get("sell_date", "")
                            if frozen_sell_date and date.today() > date.fromisoformat(frozen_sell_date):
                                if not frozen.get("actual_sell_price"):
                                    try:
                                        start = date.fromisoformat(frozen_sell_date)
                                        end = start + timedelta(days=5)
                                        tk = await asyncio.to_thread(yf.Ticker, f"{ticker}.JK")
                                        hist = await asyncio.to_thread(
                                            lambda: tk.history(start=start.isoformat(), end=end.isoformat())
                                        )
                                        if not hist.empty:
                                            actual = round(float(hist["Close"].iloc[0]), 2)
                                            frozen["actual_sell_price"] = actual
                                            frozen["actual_return_pct"] = round(
                                                (actual - frozen_bp) / frozen_bp * 100, 2
                                            )
                                            frozen["status"] = "closed"
                                    except Exception:
                                        pass
                            logger.debug(
                                "Order book [%s %s]: buy_price=Rp%s (frozen), current_price=Rp%s",
                                tf, ticker, frozen_bp, frozen.get("current_price"),
                            )
                        existing_stocks.append(frozen)
                    else:
                        price = prices.get(ticker)
                        buy_price = price
                        estimated_sell_price = None
                        if buy_price and predicted_return:
                            estimated_sell_price = round(buy_price * (1 + predicted_return / 100), 2)

                        actual_sell_price = None
                        actual_return_pct = None
                        if date.today() > date.fromisoformat(sell_date):
                            try:
                                start = date.fromisoformat(sell_date)
                                end = start + timedelta(days=5)
                                tk = await asyncio.to_thread(yf.Ticker, f"{ticker}.JK")
                                hist = await asyncio.to_thread(
                                    lambda: tk.history(start=start.isoformat(), end=end.isoformat())
                                )
                                if not hist.empty:
                                    actual_sell_price = round(float(hist["Close"].iloc[0]), 2)
                                    if buy_price and actual_sell_price:
                                        actual_return_pct = round((actual_sell_price - buy_price) / buy_price * 100, 2)
                            except Exception:
                                pass

                        new_stocks.append({
                            "ticker": ticker,
                            "company_name": stock.get("company_name", ""),
                            "sector": sector_name,
                            "recommendation": stock.get("recommendation", ""),
                            "score": stock.get("score", 0),
                            "buy_date": buy_date,
                            "sell_date": sell_date,
                            "buy_price": buy_price,
                            "current_price": buy_price,
                            "estimated_sell_price": estimated_sell_price,
                            "actual_sell_price": actual_sell_price,
                            "predicted_return_pct": round(predicted_return, 2),
                            "actual_return_pct": actual_return_pct,
                            "status": "closed" if actual_sell_price is not None else "open",
                            "key_metrics": {
                                "per": stock.get("key_metrics", {}).get("per"),
                                "pbv": stock.get("key_metrics", {}).get("pbv"),
                                "roe": stock.get("key_metrics", {}).get("roe"),
                            },
                        })

                for ex_key, ex_stock in existing_map.items():
                    if ex_key[0] == tf and ex_key[1] not in pred_stock_tickers:
                        if ex_stock not in existing_stocks:
                            ex_frozen = dict(ex_stock)
                            existing_ticker = ex_key[1]
                            ex_bp = ex_frozen.get("buy_price")
                            if ex_bp is not None:
                                live_price = prices.get(existing_ticker)
                                if live_price is not None:
                                    ex_frozen["current_price"] = live_price
                                    if ex_frozen.get("status") == "open":
                                        ex_frozen["actual_return_pct"] = round(
                                            (live_price - ex_bp) / ex_bp * 100, 2
                                        )
                                ex_sell_date = ex_frozen.get("sell_date", "")
                                if ex_sell_date and date.today() > date.fromisoformat(ex_sell_date):
                                    if not ex_frozen.get("actual_sell_price"):
                                        try:
                                            start = date.fromisoformat(ex_sell_date)
                                            end = start + timedelta(days=5)
                                            tk = await asyncio.to_thread(yf.Ticker, f"{existing_ticker}.JK")
                                            hist = await asyncio.to_thread(
                                                lambda: tk.history(start=start.isoformat(), end=end.isoformat())
                                            )
                                            if not hist.empty:
                                                actual = round(float(hist["Close"].iloc[0]), 2)
                                                ex_frozen["actual_sell_price"] = actual
                                                ex_frozen["actual_return_pct"] = round(
                                                    (actual - ex_bp) / ex_bp * 100, 2
                                                )
                                                ex_frozen["status"] = "closed"
                                        except Exception:
                                            pass
                            existing_stocks.append(ex_frozen)

                sector_block = {
                    "name": sector_name,
                    "rank": 1,
                    "predicted_return": predicted_return,
                    "confidence": top_sector.get("confidence"),
                    "rationale": top_sector.get("rationale", ""),
                }
            else:
                sector_block = {
                    "name": "N/A — Tidak ada prediksi",
                    "rank": None,
                    "predicted_return": 0,
                    "confidence": None,
                    "rationale": None,
                }
                for ex_key, ex_stock in existing_map.items():
                    if ex_key[0] == tf:
                        ex_ticker = ex_key[1]
                        ex_frozen = dict(ex_stock)
                        ex_bp = ex_frozen.get("buy_price")
                        if ex_bp is not None:
                            live_price = prices.get(ex_ticker)
                            if live_price is not None:
                                ex_frozen["current_price"] = live_price
                                if ex_frozen.get("status") == "open":
                                    ex_frozen["actual_return_pct"] = round(
                                        (live_price - ex_bp) / ex_bp * 100, 2
                                    )
                            ex_sell_date = ex_frozen.get("sell_date", "")
                            if ex_sell_date and date.today() > date.fromisoformat(ex_sell_date):
                                if not ex_frozen.get("actual_sell_price"):
                                    try:
                                        start = date.fromisoformat(ex_sell_date)
                                        end = start + timedelta(days=5)
                                        tk = await asyncio.to_thread(yf.Ticker, f"{ex_ticker}.JK")
                                        hist = await asyncio.to_thread(
                                            lambda: tk.history(start=start.isoformat(), end=end.isoformat())
                                        )
                                        if not hist.empty:
                                            actual = round(float(hist["Close"].iloc[0]), 2)
                                            ex_frozen["actual_sell_price"] = actual
                                            ex_frozen["actual_return_pct"] = round(
                                                (actual - ex_bp) / ex_bp * 100, 2
                                            )
                                            ex_frozen["status"] = "closed"
                                    except Exception:
                                        pass
                        existing_stocks.append(ex_frozen)

            combined = existing_stocks + new_stocks
            combined.sort(key=lambda s: s.get("buy_date", ""), reverse=True)

            simulations.append({
                "timeframe": tf,
                "sector": sector_block,
                "stocks": combined,
            })

        # Macro snapshot
        macro_snapshot = {}
        try:
            macro_data = get_macro_indicators()
            for ind in macro_data.get("indicators", []):
                macro_snapshot[ind["id"]] = ind.get("liveValue") or ind.get("value")
        except Exception:
            pass

        snapshot = {
            "id": str(uuid_mod.uuid4()),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "snapshot_date": today.isoformat(),
            "predictions_used": {
                "generated_at": predictions_data.get("generated_at"),
                "model": predictions_data.get("model", "qwen/qwen3-32b"),
                "timeframes": list(predictions.keys()),
            },
            "simulations": simulations,
            "macro_snapshot": macro_snapshot,
            "model": predictions_data.get("model", "qwen/qwen3-32b"),
            "version": 2,
        }

        # Simpan via OrderBookStore (append-only, otomatis MongoDB + file fallback)
        saved = await store.append_snapshot(snapshot)
        if saved:
            # Increment cache version
            version = await cache_version_manager.increment_version("order_book")
            logger.info(f"Order book snapshot stored: {snapshot['id']}, version={version}")
            await breaker.record_success()
        else:
            logger.warning(f"Order book snapshot gagal disimpan: {snapshot['id']}")
            await breaker.record_failure()

        return saved
    except PermissionError:
        logger.error("DIBLOKIR: Operasi tidak diizinkan oleh append-only guard!")
        await breaker.record_failure()
        raise
    except Exception as e:
        logger.warning(f"Order book snapshot failed: {e}")
        await breaker.record_failure()
        return False


async def run_scheduled_fetch(db) -> Dict[str, Any]:
    """Run all data fetches and store results in MongoDB. Only one run at a time."""
    global _SCHEDULER_RUN_ID

    if db is None:
        logger.warning("MongoDB not connected — cannot run scheduled fetch")
        return {"skipped": True, "reason": "MongoDB not connected"}

    if _scheduler_lock.locked():
        logger.warning("Scheduler already running, skipping duplicate invocation")
        return {"skipped": True, "reason": "Already running"}

    async with _scheduler_lock:
        _scheduler_lock_acquired_at = time.monotonic()
        run_id = uuid.uuid4().hex[:8]
        _SCHEDULER_RUN_ID = run_id
        log = lambda msg: logger.info(f"[run={run_id}] {msg}")

        log("=" * 60)
        log(f"SCHEDULED FETCH STARTING")
        log("=" * 60)

        _scheduler_start_time = time.monotonic()
        _scheduler_current_agent_idx = None
        _scheduler_agent_start_time = None

        results = {}

        async def run_with_timeout(agent_name: str, coro):
            """Jalankan agent dengan timeout. Jika timeout, log dan skip."""
            try:
                return await asyncio.wait_for(
                    run_with_monitoring(agent_name, coro),
                    timeout=AGENT_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"[run={run_id}] Agent '{agent_name}' TIMEOUT setelah "
                    f"{AGENT_TIMEOUT}s — melanjutkan ke agent berikutnya"
                )
                update_agent_status(agent_name, "error", f"Timeout {AGENT_TIMEOUT}s")
                return None

        # Helper untuk menjalankan agent dengan monitoring
        async def run_with_monitoring(agent_name: str, coro):
            async with ExecutionTimer(agent_metrics, agent_name):
                result = await coro
            
            # Check health setelah eksekusi
            stats = await agent_metrics.get_agent_stats(agent_name)
            # Circuit breaker state
            breaker = await circuit_breaker_registry.get_breaker(agent_name)
            
            await alert_manager.check_agent_health(
                agent_name=agent_name,
                success_rate=stats['success_rate'],
                avg_execution_time=stats['avg_execution_time'],
                total_executions=stats['total_executions'],
                circuit_breaker_state=breaker.state
            )
            return result

        try:
            AGENTS = [
                ("tradingview", store_tradingview_to_mongo(db)),
                ("macro", store_macro_to_mongo(db)),
                ("news_flow", store_news_to_mongo(db)),
                ("sector_predictions", store_sector_predictions_to_mongo(db)),
                ("stock_recommendations", store_stock_recommendations_to_mongo(db)),
                ("order_book", store_order_book_to_mongo(db)),
            ]

            # Clear any stale "running" status from previous run
            for agent_name, _ in AGENTS:
                update_agent_status(agent_name, "idle")

            for idx, (name, coro) in enumerate(AGENTS):
                if _scheduler_cancel_event.is_set():
                    log(f"Cancelled sebelum agent '{name}', menghentikan scheduler")
                    update_agent_status(name, "skipped", "Scheduler cancelled")
                    break
                _scheduler_current_agent_idx = idx
                _scheduler_agent_start_time = time.monotonic()
                update_agent_status(name, "running")
                results[name] = await run_with_timeout(name, coro)
                await async_rate_delay(1.0)
                update_agent_status(name, "ok")
                update_agent_status("scheduler", "ok")
                if _scheduler_cancel_event.is_set():
                    log(f"Cancelled setelah agent '{name}', menghentikan scheduler")
                    break

            log("=" * 60)
            log(f"SCHEDULED FETCH COMPLETE: {results}")
            log("=" * 60)

            update_agent_status("scheduler", "ok")
        except Exception as e:
            logger.error(f"[run={run_id}] SCHEDULED FETCH FAILED: {e}")
            update_agent_status("scheduler", "error", str(e))
            raise
        finally:
            _SCHEDULER_RUN_ID = None
            _scheduler_lock_acquired_at = None
            _scheduler_start_time = None
            _scheduler_current_agent_idx = None
            _scheduler_agent_start_time = None

    return results


def get_scheduler_progress() -> Dict[str, Any]:
    """Return current scheduler progress info for frontend polling."""
    if _scheduler_start_time is None or _SCHEDULER_RUN_ID is None:
        return {"running": False}

    now = time.monotonic()
    elapsed_total = now - _scheduler_start_time
    idx = _scheduler_current_agent_idx if _scheduler_current_agent_idx is not None else 0
    current_agent = _SCHEDULER_AGENTS_ORDER[idx] if idx < len(_SCHEDULER_AGENTS_ORDER) else "unknown"

    STOCK_RECS_IDX = 4

    if idx < STOCK_RECS_IDX:
        remaining_agents = STOCK_RECS_IDX - idx
        estimated_seconds = remaining_agents * AGENT_TIMEOUT
    elif idx == STOCK_RECS_IDX:
        agent_elapsed = now - (_scheduler_agent_start_time or now)
        estimated_seconds = int(max(30, AGENT_TIMEOUT - agent_elapsed))
    else:
        estimated_seconds = 0

    return {
        "running": True,
        "run_id": _SCHEDULER_RUN_ID,
        "current_agent": current_agent,
        "current_agent_idx": idx,
        "estimated_seconds_remaining": int(estimated_seconds),
        "elapsed_total_seconds": int(elapsed_total),
    }


def get_stale_lock_seconds() -> Optional[float]:
    if _scheduler_lock_acquired_at is None:
        return None
    elapsed = time.monotonic() - _scheduler_lock_acquired_at
    return elapsed if elapsed > 0 else None


async def check_and_release_stale_lock() -> bool:
    """Check if scheduler lock has been held too long and release if stale.
    
    Returns True if a stale lock was released, False otherwise.
    """
    if not _scheduler_lock.locked():
        return False
    stale_seconds = get_stale_lock_seconds()
    if stale_seconds is None or stale_seconds < MAX_LOCK_HOLD_SECONDS:
        return False
    logger.warning(
        f"STALE LOCK DETECTED: lock held for {stale_seconds:.0f}s "
        f"(max {MAX_LOCK_HOLD_SECONDS}s). Auto-releasing."
    )
    try:
        _scheduler_lock.release()
        _scheduler_lock_acquired_at = None
        update_agent_status("scheduler", "error", "Auto-released stale lock")
        return True
    except RuntimeError as e:
        logger.error(f"Failed to release stale lock: {e}")
        return False


async def check_all_caches_exist(db) -> bool:
    """Check if all MongoDB collections have data — just for logging, no auto-trigger."""
    if db is None:
        logger.warning("MongoDB not connected")
        return False

    from db_cache import COLLECTIONS

    all_ok = True
    for cache_key in COLLECTIONS:
        collection_name = COLLECTIONS[cache_key]
        try:
            doc = await db[collection_name].find_one({})
            if not doc:
                logger.info("Cache '%s' (collection=%s) masih kosong — menunggu jadwal atau trigger manual admin", cache_key, collection_name)
                all_ok = False
        except Exception as e:
            logger.warning("Error checking cache '%s': %s", cache_key, e)
            all_ok = False

    if all_ok:
        logger.info("All caches already populated")
    return all_ok

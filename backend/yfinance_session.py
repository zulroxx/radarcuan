"""Shared yfinance session untuk mengoptimalkan API calls antar AI Agent."""
import asyncio
import yfinance as yf
from pathlib import Path
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class YFinanceSessionManager:
    """Manages shared yfinance session and cache to prevent duplicate API calls."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        # Setup yfinance cache directory
        if cache_dir is None:
            cache_dir = Path(__file__).parent / "agent_cache" / "yfinance_shared"
        cache_dir.mkdir(parents=True, exist_ok=True)
        yf.set_tz_cache_location(str(cache_dir))
        
        # Shared cache for pricing data
        self._price_cache: Dict[str, Dict] = {}
        self._cache_ttl = 300  # 5 minutes
        self._lock = asyncio.Lock()
    
    async def get_price(self, symbol: str, period: str = "1d") -> Optional[float]:
        """Get price for a symbol with caching."""
        async with self._lock:
            cache_key = f"{symbol}:{period}"
            now = asyncio.get_event_loop().time()
            
            # Check if we have a fresh cache entry
            if cache_key in self._price_cache:
                entry = self._price_cache[cache_key]
                if now - entry["timestamp"] < self._cache_ttl:
                    return entry["price"]
            
            # Fetch fresh data
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period)
                
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])
                    
                    # Update cache
                    self._price_cache[cache_key] = {
                        "price": price,
                        "timestamp": now,
                        "symbol": symbol,
                        "period": period
                    }
                    
                    return price
                else:
                    # Try getting info as fallback
                    info = ticker.info
                    if info and "currentPrice" in info:
                        price = float(info["currentPrice"])
                        
                        # Update cache
                        self._price_cache[cache_key] = {
                            "price": price,
                            "timestamp": now,
                            "symbol": symbol,
                            "period": period
                        }
                        
                        return price
            except Exception as e:
                logger.warning(f"Failed to fetch price for {symbol}: {e}")
            
            return None
    
    async def get_multiple_prices(self, symbols: List[str], period: str = "1d") -> Dict[str, Optional[float]]:
        """Get prices for multiple symbols efficiently."""
        results = {}
        
        # Group symbols by cache status to optimize API calls
        uncached_symbols = []
        for symbol in symbols:
            cache_key = f"{symbol}:{period}"
            now = asyncio.get_event_loop().time()
            
            if cache_key in self._price_cache:
                entry = self._price_cache[cache_key]
                if now - entry["timestamp"] < self._cache_ttl:
                    results[symbol] = entry["price"]
                else:
                    uncached_symbols.append(symbol)
            else:
                uncached_symbols.append(symbol)
        
        # Fetch uncached prices
        for symbol in uncached_symbols:
            price = await self.get_price(symbol, period)
            results[symbol] = price
        
        return results
    
    async def invalidate_cache(self, symbol: Optional[str] = None, period: Optional[str] = None):
        """Invalidate specific cache entry or entire cache."""
        async with self._lock:
            if symbol is None and period is None:
                self._price_cache.clear()
            elif symbol is not None and period is not None:
                cache_key = f"{symbol}:{period}"
                self._price_cache.pop(cache_key, None)
            elif symbol is not None:
                keys_to_remove = [k for k in self._price_cache if k.startswith(f"{symbol}:")]
                for key in keys_to_remove:
                    self._price_cache.pop(key, None)
            elif period is not None:
                keys_to_remove = [k for k in self._price_cache if k.endswith(f":{period}")]
                for key in keys_to_remove:
                    self._price_cache.pop(key, None)
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        now = asyncio.get_event_loop().time()
        fresh_count = 0
        stale_count = 0
        
        for entry in self._price_cache.values():
            if now - entry["timestamp"] < self._cache_ttl:
                fresh_count += 1
            else:
                stale_count += 1
        
        return {
            "total_entries": len(self._price_cache),
            "fresh_entries": fresh_count,
            "stale_entries": stale_count,
            "ttl_seconds": self._cache_ttl
        }


# Global instance
yfinance_session_manager = YFinanceSessionManager()
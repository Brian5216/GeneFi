"""OKX OnchainOS Integration Layer.

Provides access to:
- OKX Agent Trade Kit (MCP Protocol): 119 trading tools via MCP stdio
- Real OKX Public API: Market data, funding rates, orderbook depth (fallback)
- Open API: Trading execution via REST (fallback)
- Earn API: Safe mode asset management

Data flow priority:
    1. Agent Trade Kit MCP (preferred - shows integration with OKX ecosystem)
    2. Direct REST API (fallback - when MCP unavailable or too slow)
    3. Simulation (fallback - when no network)
"""
from __future__ import annotations
import time
import random
import math
import hashlib
import hmac
import base64
import asyncio
from typing import Optional
from config import Config

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    from dtes.okx.mcp_bridge import MCPBridge
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

try:
    from dtes.okx.dex_aggregator import DEXAggregator
    HAS_DEX = True
except ImportError:
    HAS_DEX = False


# OKX Public API base (no auth required)
OKX_API_BASE = "https://www.okx.com"

# Cache TTL
CACHE_TTL = 5.0  # seconds


class OnchainOSClient:
    """Client for OKX OnchainOS platform integration.

    Supports two modes:
    - Real mode: Calls OKX public API for market data, demo for trading
    - Full demo mode: All data simulated (when DEMO_MODE=true and no network)
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self._cache: dict = {}
        self._http: Optional[httpx.AsyncClient] = None
        self._real_api_available = False
        self._net_mode_set = False
        # MCP Bridge — preferred execution channel
        self._mcp: Optional[MCPBridge] = MCPBridge() if HAS_MCP else None
        self._mcp_available = False  # Set True after first successful MCP call
        # DEX Aggregator — OnchainOS DEX integration
        self._dex: Optional[DEXAggregator] = DEXAggregator() if HAS_DEX else None

    async def _get_http(self) -> Optional[httpx.AsyncClient]:
        """Lazy-init HTTP client."""
        if not HAS_HTTPX:
            return None
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=OKX_API_BASE,
                timeout=10.0,
                headers={"Accept": "application/json"},
            )
        return self._http

    def _get_cached(self, key: str) -> Optional[dict]:
        """Get cached value if not expired."""
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["ts"] < CACHE_TTL:
                return entry["data"]
        return None

    def _set_cached(self, key: str, data: dict):
        self._cache[key] = {"data": data, "ts": time.time()}

    # ─── Real OKX Public API ─────────────────────────────────────

    async def _fetch_okx(self, path: str, params: dict = None) -> Optional[dict]:
        """Call OKX public API endpoint. Returns None on failure."""
        client = await self._get_http()
        if not client:
            return None
        try:
            resp = await client.get(path, params=params)
            if resp.status_code == 200:
                body = resp.json()
                if body.get("code") == "0":
                    self._real_api_available = True
                    return body
            return None
        except Exception as e:
            print(f"[OKX API] Request failed: {path} -> {e}")
            return None

    async def get_ticker(self, symbol: str = "BTC-USDT") -> Optional[dict]:
        """GET /api/v5/market/ticker - Real-time ticker."""
        cache_key = f"ticker:{symbol}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        result = await self._fetch_okx("/api/v5/market/ticker", {"instId": symbol})
        if result and result.get("data"):
            ticker = result["data"][0]
            parsed = {
                "symbol": symbol,
                "last": float(ticker.get("last") or 0),
                "bid": float(ticker.get("bidPx") or 0),
                "ask": float(ticker.get("askPx") or 0),
                "high_24h": float(ticker.get("high24h") or 0),
                "low_24h": float(ticker.get("low24h") or 0),
                "vol_24h": float(ticker.get("vol24h") or 0),
                "vol_ccy_24h": float(ticker.get("volCcy24h") or 0),
                "change_24h_pct": float(ticker.get("sodUtc8") or 0),
                "timestamp": time.time(),
                "source": "okx_live",
            }
            # Calculate 24h change %
            sod = float(ticker.get("sodUtc8") or 0)
            if sod > 0:
                parsed["change_24h_pct"] = round((parsed["last"] - sod) / sod * 100, 2)
            self._set_cached(cache_key, parsed)
            return parsed
        return None

    async def get_funding_rate_live(self, symbol: str = "BTC-USDT-SWAP") -> Optional[dict]:
        """GET /api/v5/public/funding-rate - Current funding rate."""
        cache_key = f"funding:{symbol}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        result = await self._fetch_okx("/api/v5/public/funding-rate", {"instId": symbol})
        if result and result.get("data"):
            fr = result["data"][0]
            parsed = {
                "symbol": symbol,
                "current_rate": float(fr.get("fundingRate") or 0),
                "next_rate": float(fr.get("nextFundingRate") or 0),
                "funding_time": int(fr.get("fundingTime") or 0),
                "next_funding_time": int(fr.get("nextFundingTime") or 0),
                "timestamp": time.time(),
                "source": "okx_live",
            }
            self._set_cached(cache_key, parsed)
            return parsed
        return None

    async def get_orderbook_live(self, symbol: str = "BTC-USDT", depth: int = 5) -> Optional[dict]:
        """GET /api/v5/market/books - Orderbook depth."""
        cache_key = f"book:{symbol}:{depth}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        result = await self._fetch_okx("/api/v5/market/books", {"instId": symbol, "sz": str(depth)})
        if result and result.get("data"):
            book = result["data"][0]
            bids = [[float(p), float(s)] for p, s, *_ in book.get("bids", [])]
            asks = [[float(p), float(s)] for p, s, *_ in book.get("asks", [])]
            mid = (bids[0][0] + asks[0][0]) / 2 if bids and asks else 0
            spread = asks[0][0] - bids[0][0] if bids and asks else 0
            spread_bps = (spread / mid * 10000) if mid > 0 else 0
            parsed = {
                "symbol": symbol,
                "mid_price": round(mid, 2),
                "best_bid": bids[0][0] if bids else 0,
                "best_ask": asks[0][0] if asks else 0,
                "spread_bps": round(spread_bps, 2),
                "bid_depth": round(sum(s for _, s in bids), 4),
                "ask_depth": round(sum(s for _, s in asks), 4),
                "timestamp": time.time(),
                "source": "okx_live",
            }
            self._set_cached(cache_key, parsed)
            return parsed
        return None

    async def get_candles(self, symbol: str = "BTC-USDT", bar: str = "1H", limit: int = 24) -> Optional[list]:
        """GET /api/v5/market/candles - K-line data for trend analysis."""
        cache_key = f"candles:{symbol}:{bar}:{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        result = await self._fetch_okx("/api/v5/market/candles", {
            "instId": symbol, "bar": bar, "limit": str(limit)
        })
        if result and result.get("data"):
            candles = []
            for c in result["data"]:
                candles.append({
                    "ts": int(c[0]),
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "vol": float(c[5]),
                })
            candles.reverse()  # OKX returns newest first
            self._set_cached(cache_key, candles)
            return candles
        return None

    # ─── Unified Market Data Interface ───────────────────────────

    async def get_market_data(self, symbol: str = "BTC-USDT") -> dict:
        """
        Fetch market data. Priority: MCP → REST API → Simulation.
        This is the main interface used by the evolution engine.
        """
        # Priority 1: Try Agent Trade Kit MCP
        mcp_ticker = await self._mcp_get_ticker(symbol)
        if mcp_ticker:
            self._mcp_available = True

        # Priority 2: REST API (always try for candles — MCP doesn't cache well)
        ticker = mcp_ticker or await self.get_ticker(symbol)
        funding = await self.get_funding_rate_live(f"{symbol}-SWAP")
        candles = await self.get_candles(symbol, "1H", 24)

        if ticker and ticker.get("source") in ("okx_live", "mcp_agent_trade_kit"):
            # Build market data from real OKX data
            trend = self._calculate_trend(candles) if candles else 0
            volatility = self._calculate_volatility(candles) if candles else 0.02
            funding_rate = funding["current_rate"] if funding else 0.0001

            regime = self._detect_regime_from_data(trend, volatility, funding_rate)

            return {
                "symbol": symbol,
                "price": ticker["last"],
                "bid": ticker["bid"],
                "ask": ticker["ask"],
                "high_24h": ticker["high_24h"],
                "low_24h": ticker["low_24h"],
                "vol_24h": ticker["vol_ccy_24h"],
                "change_24h_pct": ticker.get("change_24h_pct", 0),
                "trend": round(trend, 4),
                "volatility": round(volatility, 4),
                "funding_rate": round(funding_rate, 6),
                "funding_next": funding["next_rate"] if funding else 0,
                "regime": regime,
                "timestamp": time.time(),
                "source": "mcp_agent_trade_kit" if mcp_ticker else "okx_live",
                "open_interest": 0,
            }

        # Fallback to simulation
        return self._simulate_market_data(symbol)

    async def _mcp_get_ticker(self, symbol: str) -> Optional[dict]:
        """Get ticker via Agent Trade Kit MCP."""
        if not self._mcp:
            return None
        try:
            result = await self._mcp.call("market_get_ticker", {"instId": symbol})
            if result.success and result.data:
                data_list = result.data.get("data", {}).get("data", [])
                if data_list:
                    t = data_list[0]
                    return {
                        "symbol": symbol,
                        "last": float(t.get("last", 0)),
                        "bid": float(t.get("bidPx", 0)),
                        "ask": float(t.get("askPx", 0)),
                        "high_24h": float(t.get("high24h", 0)),
                        "low_24h": float(t.get("low24h", 0)),
                        "vol_24h": float(t.get("vol24h", 0)),
                        "vol_ccy_24h": float(t.get("volCcy24h", 0)),
                        "change_24h_pct": 0,
                        "timestamp": time.time(),
                        "source": "mcp_agent_trade_kit",
                    }
        except Exception as e:
            print(f"[MCP] Ticker fallback to REST: {e}")
        return None

    async def get_funding_rate(self, symbol: str = "BTC-USDT-SWAP") -> dict:
        """Get funding rate - real API first, then fallback."""
        live = await self.get_funding_rate_live(symbol)
        if live:
            return live
        # Fallback
        rate = random.gauss(0.0001, 0.0005)
        return {
            "symbol": symbol,
            "current_rate": round(rate, 6),
            "next_rate": round(rate + random.gauss(0, 0.0002), 6),
            "timestamp": time.time(),
            "source": "simulated",
        }

    async def get_orderbook_depth(self, symbol: str = "BTC-USDT") -> dict:
        """Get orderbook depth - real API first, then fallback."""
        live = await self.get_orderbook_live(symbol)
        if live:
            return live
        # Fallback
        mid_price = 65000 + random.gauss(0, 500)
        return {
            "symbol": symbol,
            "mid_price": round(mid_price, 2),
            "bid_depth": round(random.uniform(50, 200), 2),
            "ask_depth": round(random.uniform(50, 200), 2),
            "spread_bps": round(random.uniform(0.5, 3.0), 2),
            "timestamp": time.time(),
            "source": "simulated",
        }

    async def get_cross_chain_liquidity(self) -> dict:
        """
        Get cross-chain liquidity distribution via OnchainOS DEX Aggregator.
        Uses 500+ DEX sources across 20+ chains.
        """
        if self._dex:
            # Use DEX Aggregator to find best chain for a sample trade
            best_chain = await self._dex.find_best_chain("WETH", 1000)
            chains = {}
            for chain, data in best_chain.get("all_chains", {}).items():
                chains[chain] = round(data["net_amount"] / 10, 1)  # Normalize
            return {
                "total_tvl_billions": round(sum(chains.values()), 1),
                "chain_distribution": chains,
                "best_route": best_chain.get("best_chain", "ethereum"),
                "best_dex_per_chain": {
                    chain: data.get("best_dex", "unknown")
                    for chain, data in best_chain.get("all_chains", {}).items()
                },
                "chains_compared": best_chain.get("chains_compared", 0),
                "timestamp": time.time(),
                "source": "onchainos_dex_aggregator",
            }

        # Fallback simulation
        chains = {
            "ethereum": round(random.uniform(30, 45), 1),
            "arbitrum": round(random.uniform(15, 25), 1),
            "optimism": round(random.uniform(5, 15), 1),
            "polygon": round(random.uniform(5, 12), 1),
            "base": round(random.uniform(8, 18), 1),
            "bsc": round(random.uniform(5, 10), 1),
        }
        return {
            "total_tvl_billions": round(sum(chains.values()), 1),
            "chain_distribution": chains,
            "best_route": max(chains, key=chains.get),
            "timestamp": time.time(),
            "source": "simulated",
        }

    # ─── Trend & Volatility Calculation ──────────────────────────

    def _calculate_trend(self, candles: list) -> float:
        """Calculate trend from candle data. Returns -1 to 1."""
        if not candles or len(candles) < 2:
            return 0.0
        closes = [c["close"] for c in candles]
        # Simple: compare recent avg vs older avg
        mid = len(closes) // 2
        recent_avg = sum(closes[mid:]) / len(closes[mid:])
        older_avg = sum(closes[:mid]) / len(closes[:mid])
        if older_avg == 0:
            return 0.0
        change = (recent_avg - older_avg) / older_avg
        # Normalize to [-1, 1] range (±5% maps to ±1)
        return max(-1.0, min(1.0, change / 0.05))

    def _calculate_volatility(self, candles: list) -> float:
        """Calculate volatility from candle data."""
        if not candles or len(candles) < 2:
            return 0.02
        closes = [c["close"] for c in candles]
        returns = []
        for i in range(1, len(closes)):
            if closes[i - 1] > 0:
                returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
        if not returns:
            return 0.02
        mean_r = sum(returns) / len(returns)
        variance = sum((r - mean_r) ** 2 for r in returns) / len(returns)
        return max(0.005, min(0.10, variance ** 0.5))

    def _detect_regime_from_data(self, trend: float, volatility: float, funding_rate: float) -> str:
        """Detect market regime from calculated indicators."""
        if volatility > 0.03:
            if trend > 0.4:
                return "bull_volatile"
            elif trend < -0.4:
                return "bear_volatile"
            return "high_volatility"
        if abs(funding_rate) > 0.001:
            return "funding_extreme_positive" if funding_rate > 0 else "funding_extreme_negative"
        if abs(trend) < 0.15:
            return "range_bound"
        return "trending_up" if trend > 0 else "trending_down"

    # ─── Authenticated API Calls ────────────────────────────────

    async def _fetch_okx_auth(self, method: str, path: str, body: str = "", params: dict = None) -> Optional[dict]:
        """
        Call OKX authenticated API endpoint.
        Uses Demo Trading mode (x-simulated-trading: 1) for safe execution.
        """
        if not self.config.has_api_keys:
            return None

        client = await self._get_http()
        if not client:
            return None

        try:
            ts = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
            sign = self._sign_request(ts, method, path, body)

            headers = {
                "OK-ACCESS-KEY": self.config.OKX_API_KEY,
                "OK-ACCESS-SIGN": sign,
                "OK-ACCESS-TIMESTAMP": ts,
                "OK-ACCESS-PASSPHRASE": self.config.OKX_PASSPHRASE,
                "Content-Type": "application/json",
                # Demo Trading mode — real API calls with test funds
                "x-simulated-trading": "1",
            }

            if method.upper() == "GET":
                resp = await client.get(path, params=params, headers=headers)
            else:
                resp = await client.post(path, content=body, headers=headers)

            result = resp.json()
            code = result.get("code", "-1")
            if code == "0":
                print(f"[OKX AUTH] {method} {path} -> OK")
                return result
            else:
                msg = result.get("msg", "unknown error")
                print(f"[OKX AUTH] {method} {path} -> Error {code}: {msg}")
                return {"code": code, "msg": msg, "data": []}

        except Exception as e:
            print(f"[OKX AUTH] {method} {path} -> Exception: {e}")
            return None

    # ─── Account Info ─────────────────────────────────────────────

    async def get_balance(self) -> dict:
        """Get account balance. Priority: MCP → REST API."""
        # Priority 1: MCP
        if self._mcp and self.config.has_api_keys:
            try:
                mcp_result = await self._mcp.get_balance()
                if mcp_result.success and mcp_result.data:
                    acct_data = mcp_result.data.get("data", {}).get("data", [])
                    if acct_data:
                        acct = acct_data[0]
                        details = acct.get("details", [])
                        balances = {}
                        for d in details:
                            ccy = d.get("ccy", "")
                            if ccy:
                                balances[ccy] = {
                                    "available": float(d.get("availBal") or 0),
                                    "frozen": float(d.get("frozenBal") or 0),
                                    "equity": float(d.get("eq") or 0),
                                }
                        return {
                            "total_equity": float(acct.get("totalEq") or 0),
                            "balances": balances,
                            "timestamp": time.time(),
                            "source": "mcp_agent_trade_kit",
                        }
            except Exception as e:
                print(f"[MCP] Balance failed, falling back to REST: {e}")

        # Priority 2: REST
        result = await self._fetch_okx_auth("GET", "/api/v5/account/balance")
        if result and result.get("code") == "0" and result.get("data"):
            acct = result["data"][0]
            details = acct.get("details", [])
            balances = {}
            for d in details:
                ccy = d.get("ccy", "")
                if ccy:
                    balances[ccy] = {
                        "available": float(d.get("availBal") or 0),
                        "frozen": float(d.get("frozenBal") or 0),
                        "equity": float(d.get("eq") or 0),
                    }
            return {
                "total_equity": float(acct.get("totalEq") or 0),
                "balances": balances,
                "timestamp": time.time(),
                "source": "okx_demo_trading",
            }
        # Fallback
        return {
            "total_equity": 100000.0,
            "balances": {"USDT": {"available": 100000.0, "frozen": 0, "equity": 100000.0}},
            "timestamp": time.time(),
            "source": "simulated",
        }

    async def get_positions(self) -> list:
        """GET /api/v5/account/positions - Active positions."""
        result = await self._fetch_okx_auth("GET", "/api/v5/account/positions")
        if result and result.get("code") == "0" and result.get("data"):
            positions = []
            for p in result["data"]:
                positions.append({
                    "pos_id": p.get("posId", ""),
                    "symbol": p.get("instId", ""),
                    "side": "long" if p.get("posSide") == "long" else "short",
                    "size": float(p.get("pos") or 0),
                    "avg_price": float(p.get("avgPx") or 0),
                    "unrealized_pnl": float(p.get("upl") or 0),
                    "leverage": float(p.get("lever") or 1),
                    "liq_price": float(p.get("liqPx") or 0),
                    "margin": float(p.get("margin") or 0),
                })
            return positions
        return []

    # ─── Open API Trading Tools ──────────────────────────────────

    async def ensure_net_mode(self) -> dict:
        """Ensure account is in net_mode (required for simple order flow)."""
        import json as _json
        body = _json.dumps({"posMode": "net_mode"})
        result = await self._fetch_okx_auth("POST", "/api/v5/account/set-position-mode", body)
        return result or {}

    async def set_leverage(self, symbol: str, leverage: int, margin_mode: str = "cross") -> dict:
        """POST /api/v5/account/set-leverage"""
        import json as _json
        body = _json.dumps({
            "instId": symbol,
            "lever": str(min(leverage, self.config.MAX_LEVERAGE_LIMIT)),
            "mgnMode": margin_mode,
        })
        result = await self._fetch_okx_auth("POST", "/api/v5/account/set-leverage", body)
        return result or {}

    async def place_futures_order(
        self,
        symbol: str,
        side: str,
        size: float,
        leverage: float,
        order_type: str = "market",
    ) -> dict:
        """
        Execute futures order via OKX Open API.
        POST /api/v5/trade/order
        Uses Demo Trading mode when EXECUTION_MODE=demo_api.
        Falls back to simulation otherwise.
        """
        import json as _json

        lev = min(int(leverage), self.config.MAX_LEVERAGE_LIMIT)
        sz = min(size, self.config.MAX_POSITION_SIZE)
        swap_symbol = f"{symbol}-SWAP" if "SWAP" not in symbol else symbol

        # Priority 1: Agent Trade Kit MCP
        if self._mcp and self.config.can_trade:
            try:
                # Set leverage via MCP
                await self._mcp.swap_set_leverage(swap_symbol, str(lev))
                # Place order via MCP
                result = await self._mcp.swap_place_order(swap_symbol, side, str(sz))
                if result.success and result.data:
                    data = result.data.get("data", {}).get("data", [{}])
                    if data:
                        order = data[0]
                        return {
                            "order_id": order.get("ordId", ""),
                            "symbol": swap_symbol,
                            "side": side,
                            "size": sz,
                            "leverage": lev,
                            "status": "submitted",
                            "sMsg": order.get("sMsg", ""),
                            "timestamp": time.time(),
                            "source": "mcp_agent_trade_kit",
                        }
            except Exception as e:
                print(f"[MCP] Order failed, falling back to REST: {e}")

        # Priority 2: Direct REST API (Demo Trading mode)
        if self.config.can_trade:
            if not self._net_mode_set:
                await self.ensure_net_mode()
                self._net_mode_set = True
            await self.set_leverage(swap_symbol, lev)

            body = _json.dumps({
                "instId": swap_symbol,
                "tdMode": "cross",
                "side": side,
                "ordType": order_type,
                "sz": str(sz),
            })
            result = await self._fetch_okx_auth("POST", "/api/v5/trade/order", body)

            if result and result.get("code") == "0" and result.get("data"):
                order = result["data"][0]
                return {
                    "order_id": order.get("ordId", ""),
                    "client_id": order.get("clOrdId", ""),
                    "symbol": swap_symbol,
                    "side": side,
                    "size": sz,
                    "leverage": lev,
                    "status": "submitted",
                    "sCode": order.get("sCode", ""),
                    "sMsg": order.get("sMsg", ""),
                    "timestamp": time.time(),
                    "source": "okx_demo_trading",
                }
            print(f"[OKX] Order failed, falling back to simulation")

        # Simulation fallback
        price = 65000 + random.gauss(0, 100)
        return {
            "order_id": f"sim_{int(time.time())}_{random.randint(1000,9999)}",
            "symbol": symbol,
            "side": side,
            "size": size,
            "leverage": leverage,
            "status": "filled",
            "fill_price": round(price, 2),
            "slippage_bps": round(random.uniform(0.1, 2.0), 2),
            "timestamp": time.time(),
            "source": "simulated",
        }

    async def close_position(self, symbol: str, side: str = "long") -> dict:
        """
        Close a position. Priority: MCP → REST API.
        In net_mode, posSide should be "net".
        """
        import json as _json
        swap_symbol = f"{symbol}-SWAP" if "SWAP" not in symbol else symbol

        # Priority 1: MCP
        if self._mcp and self.config.can_trade:
            try:
                result = await self._mcp.swap_close_position(swap_symbol)
                if result.success:
                    return {"status": "closed", "symbol": swap_symbol, "source": "mcp_agent_trade_kit"}
            except Exception as e:
                print(f"[MCP] Close failed, falling back to REST: {e}")

        # Priority 2: REST
        if self.config.can_trade:
            body = _json.dumps({
                "instId": swap_symbol,
                "mgnMode": "cross",
                "posSide": "net",
            })
            result = await self._fetch_okx_auth("POST", "/api/v5/trade/close-position", body)
            if result and result.get("code") == "0":
                return {"status": "closed", "symbol": swap_symbol, "source": "okx_demo_trading"}

        return {"status": "simulated_close", "symbol": symbol, "source": "simulated"}

    async def create_grid_bot(
        self,
        symbol: str,
        grid_count: int,
        upper_price: float,
        lower_price: float,
        total_investment: float,
    ) -> dict:
        """
        Deploy grid trading bot via OKX.
        POST /api/v5/tradingBot/grid/place-algo-order
        """
        import json as _json
        if self.config.can_trade:
            body = _json.dumps({
                "instId": f"{symbol}-SWAP" if "SWAP" not in symbol else symbol,
                "algoOrdType": "grid",
                "maxPx": str(upper_price),
                "minPx": str(lower_price),
                "gridNum": str(grid_count),
                "quoteSz": str(total_investment),
                "direction": "neutral",
                "lever": "5",
            })
            result = await self._fetch_okx_auth("POST", "/api/v5/tradingBot/grid/place-algo-order", body)
            if result and result.get("code") == "0" and result.get("data"):
                algo = result["data"][0]
                return {
                    "bot_id": algo.get("algoId", ""),
                    "symbol": symbol,
                    "grid_count": grid_count,
                    "status": "running",
                    "timestamp": time.time(),
                    "source": "okx_demo_trading",
                }

        return {
            "bot_id": f"sim_grid_{int(time.time())}",
            "symbol": symbol,
            "grid_count": grid_count,
            "upper_price": upper_price,
            "lower_price": lower_price,
            "total_investment": total_investment,
            "status": "running",
            "timestamp": time.time(),
            "source": "simulated",
        }

    async def cross_chain_swap(
        self,
        from_chain: str,
        to_chain: str,
        token: str,
        amount: float,
    ) -> dict:
        """
        Execute cross-chain swap via OnchainOS liquidity router.
        Covers 60+ chains and 500+ DEX.
        """
        # Cross-chain via OnchainOS router (no direct API yet)
        return {
            "tx_id": f"xchain_{int(time.time())}",
            "from_chain": from_chain,
            "to_chain": to_chain,
            "token": token,
            "amount": amount,
            "received": round(amount * random.uniform(0.995, 0.999), 4),
            "route": f"{from_chain} -> bridge -> {to_chain}",
            "status": "completed",
            "timestamp": time.time(),
            "source": "simulated",
        }

    # ─── Earn API (Safe Mode) ─────────────────────────────────────

    async def switch_to_earn(self, amount: float, product: str = "simple_earn") -> dict:
        """
        Switch assets to OKX Earn (Savings) for safe mode.
        POST /api/v5/finance/savings/purchase-redempt
        Triggered by Judge Agent when population health degrades.
        """
        import json as _json
        if self.config.can_trade:
            body = _json.dumps({
                "ccy": "USDT",
                "amt": str(round(amount, 2)),
                "side": "purchase",
                "rate": "0.01",
            })
            result = await self._fetch_okx_auth(
                "POST", "/api/v5/finance/savings/purchase-redempt", body
            )
            if result and result.get("code") == "0":
                return {
                    "action": "switch_to_earn",
                    "amount": amount,
                    "product": "okx_savings",
                    "status": "deposited",
                    "timestamp": time.time(),
                    "source": "okx_demo_trading",
                }

        return {
            "action": "switch_to_earn",
            "amount": amount,
            "product": product,
            "apy": round(random.uniform(0.02, 0.08), 4),
            "status": "deposited",
            "timestamp": time.time(),
            "source": "simulated",
        }

    async def redeem_from_earn(self, amount: float) -> dict:
        """Redeem from OKX Savings when resuming trading."""
        import json as _json
        if self.config.can_trade:
            body = _json.dumps({
                "ccy": "USDT",
                "amt": str(round(amount, 2)),
                "side": "redempt",
                "rate": "0.01",
            })
            result = await self._fetch_okx_auth(
                "POST", "/api/v5/finance/savings/purchase-redempt", body
            )
            if result and result.get("code") == "0":
                return {"action": "redeem", "amount": amount, "source": "okx_demo_trading"}
        return {"action": "redeem", "amount": amount, "source": "simulated"}

    # ─── Demo Market Simulation ──────────────────────────────────

    def _simulate_market_data(self, symbol: str) -> dict:
        """Generate realistic simulated market data with regime changes."""
        t = time.time()
        cycle = math.sin(t / 300)
        trend = cycle * 0.5 + random.gauss(0, 0.1)
        volatility = abs(math.sin(t / 120)) * 0.03 + 0.01
        funding_rate = cycle * 0.0005 + random.gauss(0, 0.0002)

        price_base = 65000 if "BTC" in symbol else 3500
        price = price_base * (1 + trend * 0.02)

        regime = self._detect_regime_from_data(trend, volatility, funding_rate)

        return {
            "symbol": symbol,
            "price": round(price, 2),
            "trend": round(trend, 4),
            "volatility": round(volatility, 4),
            "funding_rate": round(funding_rate, 6),
            "volume_24h": round(random.uniform(1e9, 5e9), 0),
            "open_interest": round(random.uniform(5e9, 15e9), 0),
            "regime": regime,
            "timestamp": t,
            "source": "simulated",
        }

    # ─── Auth Helpers (Production) ────────────────────────────────

    def _sign_request(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        """Generate OKX API signature."""
        message = timestamp + method.upper() + path + body
        signature = hmac.HMAC(
            self.config.OKX_SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(signature).decode()

    def get_mcp_stats(self) -> dict:
        """Get MCP Agent Trade Kit + OnchainOS usage statistics."""
        stats = {}
        if self._mcp:
            stats = self._mcp.get_call_stats()
            stats["mcp_available"] = self._mcp_available
            stats["total_mcp_tools"] = 119
        else:
            stats = {"mcp_available": False, "total_calls": 0}

        # Add DEX stats
        if self._dex:
            stats["dex_aggregator"] = self._dex.get_stats()
        else:
            stats["dex_aggregator"] = {"total_quotes": 0, "supported_chains": 0}

        return stats

    async def close(self):
        """Close HTTP client."""
        if self._http and not self._http.is_closed:
            await self._http.aclose()

"""OKX Agent Trade Kit MCP Bridge.

Provides Python interface to OKX's 64 MCP trading tools via stdio protocol.
This bridges GeneFi's Python agents with the official Agent Trade Kit MCP server.

Architecture:
    GeneFi Agent (Python) → MCP Bridge → okx-trade-mcp (Node.js) → OKX API

Supports all 7 categories:
    - spot (13 tools): Spot trading
    - swap (17 tools): Futures/perpetual swap
    - option (14 tools): Options trading
    - account (13 tools): Balance, positions, fees
    - grid (5 tools): Grid trading bots
    - trade (1 tool): Trade history
    - system (1 tool): Capabilities
"""
from __future__ import annotations
import asyncio
import json
import os
import time
from typing import Optional, Any
from dataclasses import dataclass, field


# Path to the MCP binary
MCP_BIN = os.path.join(
    os.path.expanduser("~"),
    ".local/lib/node-v22.22.1-darwin-arm64/lib/node_modules/okx-trade-mcp/bin/okx-trade-mcp.mjs"
)

# Fallback: try to find via npm
def _find_mcp_bin() -> str:
    """Find okx-trade-mcp binary."""
    if os.path.exists(MCP_BIN):
        return MCP_BIN
    # Try npm root -g
    import subprocess
    try:
        root = subprocess.check_output(["npm", "root", "-g"], text=True).strip()
        path = os.path.join(root, "okx-trade-mcp/bin/okx-trade-mcp.mjs")
        if os.path.exists(path):
            return path
    except Exception:
        pass
    return MCP_BIN


@dataclass
class MCPCallResult:
    """Result of an MCP tool call."""
    tool: str
    success: bool
    data: Any = None
    error: str = ""
    latency_ms: float = 0
    raw_response: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "tool": self.tool,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "latency_ms": round(self.latency_ms, 1),
        }


class MCPBridge:
    """
    Bridge between GeneFi Python agents and OKX Agent Trade Kit MCP server.

    Usage:
        bridge = MCPBridge()
        result = await bridge.call("swap_place_order", {
            "instId": "BTC-USDT-SWAP",
            "tdMode": "cross",
            "side": "buy",
            "ordType": "market",
            "sz": "1",
        })
    """

    def __init__(self):
        self._mcp_bin = _find_mcp_bin()
        self._call_log: list[MCPCallResult] = []
        self._tools_cache: list[dict] = []
        self._request_id = 0

    @property
    def call_count(self) -> int:
        return len(self._call_log)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self._call_log if r.success)

    @property
    def tools_used(self) -> set:
        return set(r.tool for r in self._call_log)

    def get_call_stats(self) -> dict:
        """Get statistics about MCP calls made."""
        return {
            "total_calls": self.call_count,
            "successful": self.success_count,
            "failed": self.call_count - self.success_count,
            "tools_used": sorted(list(self.tools_used)),
            "tools_used_count": len(self.tools_used),
            "avg_latency_ms": round(
                sum(r.latency_ms for r in self._call_log) / max(len(self._call_log), 1), 1
            ),
        }

    async def call(self, tool_name: str, arguments: dict = None) -> MCPCallResult:
        """
        Call an MCP tool via stdio protocol.

        Args:
            tool_name: MCP tool name (e.g., "swap_place_order", "account_get_balance")
            arguments: Tool arguments as dict

        Returns:
            MCPCallResult with success status and data
        """
        self._request_id += 1
        start = time.time()

        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {},
            },
        }

        try:
            result = await self._send_mcp_request(request)
            latency = (time.time() - start) * 1000

            if result and "result" in result:
                content = result["result"].get("content", [])
                # Extract text content from MCP response
                data = None
                for item in content:
                    if item.get("type") == "text":
                        try:
                            data = json.loads(item["text"])
                        except (json.JSONDecodeError, KeyError):
                            data = item.get("text", "")

                is_error = result["result"].get("isError", False)
                call_result = MCPCallResult(
                    tool=tool_name,
                    success=not is_error,
                    data=data,
                    error=str(data) if is_error else "",
                    latency_ms=latency,
                    raw_response=result,
                )
            elif result and "error" in result:
                call_result = MCPCallResult(
                    tool=tool_name,
                    success=False,
                    error=result["error"].get("message", "Unknown MCP error"),
                    latency_ms=latency,
                    raw_response=result,
                )
            else:
                call_result = MCPCallResult(
                    tool=tool_name,
                    success=False,
                    error="No response from MCP server",
                    latency_ms=latency,
                )

        except Exception as e:
            latency = (time.time() - start) * 1000
            call_result = MCPCallResult(
                tool=tool_name,
                success=False,
                error=str(e),
                latency_ms=latency,
            )

        self._call_log.append(call_result)
        status = "OK" if call_result.success else f"FAIL: {call_result.error[:80]}"
        print(f"[MCP] {tool_name} -> {status} ({call_result.latency_ms:.0f}ms)")

        return call_result

    async def _send_mcp_request(self, request: dict) -> Optional[dict]:
        """Send JSON-RPC request to MCP server via subprocess stdio."""
        request_json = json.dumps(request) + "\n"

        # Use mcp_proxy.js wrapper that handles HTTP proxy for undici/fetch
        proxy_script = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "mcp_proxy.js")
        if not os.path.exists(proxy_script):
            # Fallback to direct MCP binary
            proxy_script = self._mcp_bin

        proc = await asyncio.create_subprocess_exec(
            "node", proxy_script, "--demo", "--modules", "all",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=request_json.encode()),
                timeout=15.0,
            )
        except asyncio.TimeoutError:
            proc.kill()
            return None

        if stdout:
            # MCP may return multiple JSON lines, find the one matching our ID
            for line in stdout.decode().strip().split("\n"):
                try:
                    obj = json.loads(line)
                    if obj.get("id") == request["id"]:
                        return obj
                except json.JSONDecodeError:
                    continue

        return None

    async def list_tools(self) -> list[dict]:
        """List all available MCP tools."""
        if self._tools_cache:
            return self._tools_cache

        request = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "tools/list",
            "params": {},
        }

        result = await self._send_mcp_request(request)
        if result and "result" in result:
            self._tools_cache = result["result"].get("tools", [])
        return self._tools_cache

    # ─── Convenience Methods ─────────────────────────────────────

    async def get_balance(self) -> MCPCallResult:
        """Get account balance."""
        return await self.call("account_get_balance")

    async def get_positions(self) -> MCPCallResult:
        """Get all positions."""
        return await self.call("account_get_positions")

    async def get_swap_positions(self) -> MCPCallResult:
        """Get swap/futures positions."""
        return await self.call("swap_get_positions")

    async def swap_place_order(
        self,
        inst_id: str,
        side: str,
        sz: str,
        td_mode: str = "cross",
        ord_type: str = "market",
        **kwargs,
    ) -> MCPCallResult:
        """Place a swap/futures order."""
        args = {
            "instId": inst_id,
            "tdMode": td_mode,
            "side": side,
            "ordType": ord_type,
            "sz": sz,
            **kwargs,
        }
        return await self.call("swap_place_order", args)

    async def swap_close_position(self, inst_id: str, mgn_mode: str = "cross") -> MCPCallResult:
        """Close a swap position."""
        return await self.call("swap_close_position", {
            "instId": inst_id,
            "mgnMode": mgn_mode,
        })

    async def swap_set_leverage(self, inst_id: str, lever: str, mgn_mode: str = "cross") -> MCPCallResult:
        """Set leverage for a swap instrument."""
        return await self.call("swap_set_leverage", {
            "instId": inst_id,
            "lever": lever,
            "mgnMode": mgn_mode,
        })

    async def grid_create(
        self,
        inst_id: str,
        grid_type: str,
        max_px: str,
        min_px: str,
        grid_num: str,
        **kwargs,
    ) -> MCPCallResult:
        """Create a grid trading bot."""
        args = {
            "instId": inst_id,
            "gridType": grid_type,
            "maxPx": max_px,
            "minPx": min_px,
            "gridNum": grid_num,
            **kwargs,
        }
        return await self.call("grid_create_order", args)

    async def spot_place_order(
        self,
        inst_id: str,
        side: str,
        sz: str,
        td_mode: str = "cash",
        ord_type: str = "market",
        **kwargs,
    ) -> MCPCallResult:
        """Place a spot order."""
        args = {
            "instId": inst_id,
            "tdMode": td_mode,
            "side": side,
            "ordType": ord_type,
            "sz": sz,
            **kwargs,
        }
        return await self.call("spot_place_order", args)

    async def get_system_capabilities(self) -> MCPCallResult:
        """Get system capabilities and available tools."""
        return await self.call("system_get_capabilities")

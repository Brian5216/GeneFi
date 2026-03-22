#!/usr/bin/env node
/**
 * GeneFi MCP Proxy - Bridges okx-trade-mcp with HTTP proxy support.
 * Patches Node.js undici fetch dispatcher before loading MCP.
 *
 * Usage: node mcp_proxy.js --demo --modules all
 */
const path = require('path');
const { execSync } = require('child_process');
const mcpRoot = path.join(execSync('npm root -g', { encoding: 'utf8' }).trim(), 'okx-trade-mcp');

// Inject proxy if available
const proxy = process.env.HTTP_PROXY || process.env.HTTPS_PROXY || '';
if (proxy) {
    try {
        const { ProxyAgent, setGlobalDispatcher } = require(path.join(mcpRoot, 'node_modules/undici'));
        setGlobalDispatcher(new ProxyAgent(proxy));
    } catch (e) {
        process.stderr.write('[mcp_proxy] Proxy setup failed: ' + e.message + '\n');
    }
}

// Load MCP server
import(path.join(mcpRoot, 'bin/okx-trade-mcp.mjs')).catch(e => {
    process.stderr.write('[mcp_proxy] MCP load error: ' + e.message + '\n');
    process.exit(1);
});

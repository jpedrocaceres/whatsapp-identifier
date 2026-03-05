"""
WhatsApp Identifier - CSS Blur Injector via Chrome DevTools Protocol

Connects to WhatsApp Desktop's Electron debug port and injects/removes
CSS blur on specific elements (message previews, chat messages, etc.)

Usage:
    python blur_inject.py inject [blur_px] [port]
    python blur_inject.py remove [port]
    python blur_inject.py status [port]
"""

import sys
import json
import urllib.request
import asyncio

# Try to import websockets, fall back to simple HTTP approach
try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False


# CSS to blur specific WhatsApp elements
BLUR_CSS_TEMPLATE = """
/* WhatsApp Identifier - Privacy Blur */

/* === LISTA DE CONVERSAS (sidebar) === */
._ak8k span[title] {{
    filter: blur({blur}px) !important;
    transition: filter 0.2s ease !important;
}}
/* Hover na conversa revela o preview */
._ak8l:hover ._ak8k span[title] {{
    filter: blur(0px) !important;
}}

/* === MENSAGENS NO CHAT === */
.message-in .copyable-text,
.message-out .copyable-text {{
    filter: blur({blur}px) !important;
    transition: filter 0.2s ease !important;
}}
/* Hover no balao revela o texto */
.message-in:hover .copyable-text,
.message-out:hover .copyable-text {{
    filter: blur(0px) !important;
}}

/* === MIDIA (imagens, videos) === */
.message-in img, .message-out img,
.message-in video, .message-out video {{
    filter: blur({blur}px) !important;
    transition: filter 0.2s ease !important;
}}
.message-in:hover img, .message-out:hover img,
.message-in:hover video, .message-out:hover video {{
    filter: blur(0px) !important;
}}
"""

INJECT_JS = """
(function() {{
    var existingStyle = document.getElementById('wa-privacy-blur');
    if (existingStyle) existingStyle.remove();

    var style = document.createElement('style');
    style.id = 'wa-privacy-blur';
    style.textContent = `{css}`;
    document.head.appendChild(style);
    return 'injected';
}})();
"""

REMOVE_JS = """
(function() {
    var style = document.getElementById('wa-privacy-blur');
    if (style) {
        style.remove();
        return 'removed';
    }
    return 'not_found';
})();
"""

STATUS_JS = """
(function() {
    return document.getElementById('wa-privacy-blur') ? 'active' : 'inactive';
})();
"""


def get_ws_url(port):
    """Get WebSocket debugger URL from CDP HTTP endpoint."""
    try:
        url = f"http://localhost:{port}/json"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=2) as resp:
            pages = json.loads(resp.read().decode())
            # Find the main WhatsApp page (not devtools or service worker)
            for page in pages:
                if page.get("type") == "page" and "whatsapp" in page.get("url", "").lower():
                    return page.get("webSocketDebuggerUrl", "")
            # Fallback: first page type entry
            for page in pages:
                if page.get("type") == "page":
                    return page.get("webSocketDebuggerUrl", "")
            # Last resort: first entry
            if pages:
                return pages[0].get("webSocketDebuggerUrl", "")
    except Exception as e:
        print(f"ERROR: Cannot connect to CDP on port {port}: {e}", file=sys.stderr)
    return ""


async def send_cdp_command(ws_url, method, params=None):
    """Send a CDP command via WebSocket and return the result."""
    async with websockets.connect(ws_url) as ws:
        msg = {"id": 1, "method": method, "params": params or {}}
        await ws.send(json.dumps(msg))
        response = await asyncio.wait_for(ws.recv(), timeout=5)
        return json.loads(response)


async def execute_js(ws_url, expression):
    """Execute JavaScript in the page context via CDP."""
    result = await send_cdp_command(ws_url, "Runtime.evaluate", {
        "expression": expression,
        "returnByValue": True
    })
    return result


def send_cdp_http(port, expression):
    """Fallback: use HTTP endpoint to evaluate JS (limited but works without websockets)."""
    # This approach uses the /json/evaluate endpoint if available
    # Otherwise we need websockets
    print("ERROR: websockets module required. Install: pip install websockets", file=sys.stderr)
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python blur_inject.py inject|remove|status [blur_px] [port]")
        sys.exit(1)

    action = sys.argv[1].lower()
    blur_px = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 8
    port = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 9250

    if not HAS_WEBSOCKETS:
        print("ERROR: websockets module required. Run: pip install websockets", file=sys.stderr)
        sys.exit(1)

    ws_url = get_ws_url(port)
    if not ws_url:
        print("ERROR: Could not find WhatsApp page on CDP", file=sys.stderr)
        sys.exit(1)

    if action == "inject":
        css = BLUR_CSS_TEMPLATE.format(blur=blur_px)
        # Escape backticks and backslashes for JS template literal
        css_escaped = css.replace("\\", "\\\\").replace("`", "\\`")
        js = INJECT_JS.format(css=css_escaped)
        result = asyncio.run(execute_js(ws_url, js))
        value = result.get("result", {}).get("result", {}).get("value", "")
        print(value)

    elif action == "remove":
        result = asyncio.run(execute_js(ws_url, REMOVE_JS))
        value = result.get("result", {}).get("result", {}).get("value", "")
        print(value)

    elif action == "status":
        result = asyncio.run(execute_js(ws_url, STATUS_JS))
        value = result.get("result", {}).get("result", {}).get("value", "")
        print(value)

    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

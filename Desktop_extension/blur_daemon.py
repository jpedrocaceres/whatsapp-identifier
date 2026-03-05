"""
WhatsApp Identifier - Blur Daemon (persistent process)

Stays running and watches a command file for instant blur inject/remove.
Maintains a persistent WebSocket connection to WhatsApp's CDP.

Usage: pythonw blur_daemon.py [port]

Commands via command file (blur_cmd.txt in same directory):
  inject <blur_px>
  remove
  reconnect
  exit
"""

import sys
import os
import json
import asyncio
import time
import urllib.request

try:
    import websockets
except ImportError:
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
CMD_FILE = os.path.join(SCRIPT_DIR, "blur_cmd.txt")
STATUS_FILE = os.path.join(SCRIPT_DIR, "blur_status.txt")
LOG_FILE = os.path.join(SCRIPT_DIR, "blur_daemon.log")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9251


def log(msg):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except Exception:
        pass


def ws_is_open(ws):
    """Check if websocket is open, compatible with websockets 13+ and 15+."""
    if ws is None:
        return False
    try:
        # websockets 15.x: check protocol state
        state = ws.protocol.state
        return state.name == "OPEN"
    except AttributeError:
        pass
    try:
        # websockets 13.x: .closed attribute
        return not ws.closed
    except AttributeError:
        pass
    # Fallback: assume open
    return True


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
    var s = document.getElementById('wa-privacy-blur');
    if (s) s.remove();
    s = document.createElement('style');
    s.id = 'wa-privacy-blur';
    s.textContent = `{css}`;
    document.head.appendChild(s);
    return 'ok';
}})();
"""

REMOVE_JS = """
(function() {
    var s = document.getElementById('wa-privacy-blur');
    if (s) { s.remove(); return 'ok'; }
    return 'none';
})();
"""

CHECK_PAGE_JS = """
(function() {
    return window.location.href;
})();
"""


def write_status(status):
    try:
        with open(STATUS_FILE, "w") as f:
            f.write(status)
    except Exception:
        pass


def find_whatsapp_ws_url():
    """Find WhatsApp's WebSocket debugger URL using fast parallel scan."""
    try:
        from cdp_utils import find_whatsapp_ws_url as _find
        url = _find(preferred_port=PORT)
        if url:
            log(f"found WhatsApp ws url via fast scan")
        return url
    except ImportError:
        # Fallback if cdp_utils not available
        pass
    ports_to_try = [PORT] + [p for p in range(PORT, PORT + 20) if p != PORT]
    for port in ports_to_try:
        try:
            url = f"http://localhost:{port}/json"
            with urllib.request.urlopen(url, timeout=2) as resp:
                pages = json.loads(resp.read().decode())
                for p in pages:
                    if p.get("type") == "page" and "whatsapp" in p.get("url", "").lower():
                        ws_url = p.get("webSocketDebuggerUrl", "")
                        if ws_url:
                            log(f"found WhatsApp on port {port}")
                            return ws_url
        except Exception:
            continue
    return ""


async def verify_whatsapp_page(ws):
    """Verify the WebSocket is connected to a WhatsApp page."""
    try:
        await ws.send(json.dumps({
            "id": 99, "method": "Runtime.evaluate",
            "params": {"expression": CHECK_PAGE_JS, "returnByValue": True}
        }))
        response = await asyncio.wait_for(ws.recv(), timeout=3)
        data = json.loads(response)
        page_url = data.get("result", {}).get("result", {}).get("value", "")
        is_wa = "whatsapp" in page_url.lower()
        log(f"page verify: url={page_url}, is_whatsapp={is_wa}")
        return is_wa
    except Exception as e:
        log(f"page verify error: {e}")
        return False


async def run_daemon():
    ws = None
    connected = False
    pending_cmd = ""  # Queue command if not yet connected
    last_blur_px = 8  # Remember last blur intensity for auto-reinject
    blur_was_on = False  # Track if blur should be active

    log(f"daemon starting, port={PORT}")
    write_status("starting")

    # Clean command file
    try:
        os.remove(CMD_FILE)
    except FileNotFoundError:
        pass

    retry_connect_interval = 0  # Counter for connection retries

    while True:
        # Read command file
        cmd = ""
        try:
            if os.path.exists(CMD_FILE):
                with open(CMD_FILE, "r") as f:
                    cmd = f.read().strip()
                os.remove(CMD_FILE)
                if cmd:
                    log(f"cmd: {cmd}")
        except Exception:
            pass

        if cmd == "exit":
            log("exit received")
            write_status("exiting")
            if ws and ws_is_open(ws):
                await ws.close()
            break

        if cmd == "reconnect":
            log("reconnect requested")
            if ws and ws_is_open(ws):
                await ws.close()
            ws = None
            connected = False
            retry_connect_interval = 0
            # If blur was on, queue re-inject after reconnect
            if blur_was_on:
                pending_cmd = f"inject {last_blur_px}"
            await asyncio.sleep(0.1)
            continue

        # Queue command if we have one
        if cmd.startswith("inject"):
            parts = cmd.split()
            last_blur_px = int(parts[1]) if len(parts) > 1 else 8
            blur_was_on = True
            if not connected or not ws_is_open(ws):
                pending_cmd = cmd
                log(f"queued command (not connected): {cmd}")
            else:
                pending_cmd = cmd  # Will be processed below
        elif cmd == "remove":
            blur_was_on = False
            if not connected or not ws_is_open(ws):
                pending_cmd = cmd
                log(f"queued command (not connected): {cmd}")
            else:
                pending_cmd = cmd

        # Ensure connection to WhatsApp
        if not connected or not ws_is_open(ws):
            retry_connect_interval += 1
            # Don't spam connection attempts — try every ~2 seconds (20 * 100ms)
            if retry_connect_interval >= 20 or retry_connect_interval == 1:
                retry_connect_interval = 0
                new_url = find_whatsapp_ws_url()
                if new_url:
                    try:
                        if ws and ws_is_open(ws):
                            await ws.close()
                        ws = await asyncio.wait_for(
                            websockets.connect(new_url, max_size=10_000_000),
                            timeout=5
                        )
                        # Verify this is actually WhatsApp
                        if await verify_whatsapp_page(ws):
                            connected = True
                            log("connected to WhatsApp ok")
                            write_status("connected")
                            # Process any pending command now
                            if not pending_cmd and blur_was_on:
                                pending_cmd = f"inject {last_blur_px}"
                                log(f"auto-queuing inject after connect")
                        else:
                            log("connected but NOT WhatsApp page, closing")
                            await ws.close()
                            ws = None
                            connected = False
                            write_status("no_whatsapp")
                    except Exception as e:
                        connected = False
                        log(f"connect error: {e}")
                        write_status("disconnected")
                else:
                    connected = False
                    write_status("no_whatsapp")

            await asyncio.sleep(0.1)
            # If just connected and have pending command, continue to process it
            if not connected or not pending_cmd:
                continue

        # Process pending command
        if pending_cmd.startswith("inject") and connected and ws_is_open(ws):
            parts = pending_cmd.split()
            blur_px = int(parts[1]) if len(parts) > 1 else 8
            css = BLUR_CSS_TEMPLATE.format(blur=blur_px)
            css_escaped = css.replace("\\", "\\\\").replace("`", "\\`")
            js = INJECT_JS.format(css=css_escaped)
            try:
                await ws.send(json.dumps({
                    "id": 1, "method": "Runtime.evaluate",
                    "params": {"expression": js, "returnByValue": True}
                }))
                resp = await asyncio.wait_for(ws.recv(), timeout=3)
                data = json.loads(resp)
                value = data.get("result", {}).get("result", {}).get("value", "")
                log(f"inject result: {value}")
                if value == "ok":
                    write_status("blur_on")
                else:
                    log(f"inject unexpected result: {data}")
                    write_status("error_inject")
            except Exception as e:
                connected = False
                log(f"inject error: {e}")
                write_status("error_inject")
            pending_cmd = ""

        elif pending_cmd == "remove" and connected and ws_is_open(ws):
            try:
                await ws.send(json.dumps({
                    "id": 2, "method": "Runtime.evaluate",
                    "params": {"expression": REMOVE_JS, "returnByValue": True}
                }))
                await asyncio.wait_for(ws.recv(), timeout=3)
                log("remove ok")
                write_status("blur_off")
            except Exception as e:
                connected = False
                log(f"remove error: {e}")
                write_status("error_remove")
            pending_cmd = ""

        elif pending_cmd:
            # Unknown pending command, clear it
            pending_cmd = ""

        # Poll every 100ms
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    try:
        asyncio.run(run_daemon())
    except KeyboardInterrupt:
        pass
    finally:
        write_status("stopped")

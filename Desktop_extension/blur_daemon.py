"""
WhatsApp Identifier - Blur Daemon (persistent process)

Stays running and watches a command file for instant blur inject/remove.
Maintains a persistent WebSocket connection to WhatsApp's CDP.

Usage: pythonw blur_daemon.py [port]

Commands via command file (blur_cmd.txt in same directory):
  inject <blur_px>
  remove
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
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9250


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


def write_status(status):
    try:
        with open(STATUS_FILE, "w") as f:
            f.write(status)
    except Exception:
        pass


def get_ws_url():
    try:
        url = f"http://localhost:{PORT}/json"
        with urllib.request.urlopen(url, timeout=2) as resp:
            pages = json.loads(resp.read().decode())
            for p in pages:
                if p.get("type") == "page":
                    return p.get("webSocketDebuggerUrl", "")
    except Exception:
        pass
    return ""


async def run_daemon():
    ws = None
    connected = False

    log(f"daemon starting, port={PORT}")
    write_status("starting")

    # Clean command file
    try:
        os.remove(CMD_FILE)
    except FileNotFoundError:
        pass

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
            if ws:
                await ws.close()
            break

        # Ensure connection
        if not connected or not ws_is_open(ws):
            new_url = get_ws_url()
            if new_url:
                try:
                    if ws and ws_is_open(ws):
                        await ws.close()
                    ws = await asyncio.wait_for(
                        websockets.connect(new_url, max_size=10_000_000),
                        timeout=5
                    )
                    connected = True
                    log("connected ok")
                    write_status("connected")
                except Exception as e:
                    connected = False
                    log(f"connect error: {e}")
                    write_status("disconnected")
            else:
                connected = False
                write_status("no_whatsapp")

        # Process command
        if cmd.startswith("inject") and connected and ws_is_open(ws):
            parts = cmd.split()
            blur_px = int(parts[1]) if len(parts) > 1 else 8
            css = BLUR_CSS_TEMPLATE.format(blur=blur_px)
            css_escaped = css.replace("\\", "\\\\").replace("`", "\\`")
            js = INJECT_JS.format(css=css_escaped)
            try:
                await ws.send(json.dumps({
                    "id": 1, "method": "Runtime.evaluate",
                    "params": {"expression": js, "returnByValue": True}
                }))
                await asyncio.wait_for(ws.recv(), timeout=3)
                log("inject ok")
                write_status("blur_on")
            except Exception as e:
                connected = False
                log(f"inject error: {e}")
                write_status("error_inject")

        elif cmd == "remove" and connected and ws_is_open(ws):
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

        # Poll every 100ms
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    try:
        asyncio.run(run_daemon())
    except KeyboardInterrupt:
        pass
    finally:
        write_status("stopped")

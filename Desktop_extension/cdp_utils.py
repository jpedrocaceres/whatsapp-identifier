"""
Fast CDP port scanner for WhatsApp Desktop.

Uses socket connect_ex for instant port-open checks, then only
queries /json on ports that are actually listening.
Scans ports 9222-9269 in parallel using threads.
"""

import socket
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

DEFAULT_PORT_RANGE = (9222, 9270)


def _is_port_open(port, timeout=0.15):
    """Fast TCP check — returns True if port accepts connections."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False
    finally:
        s.close()


def _scan_open_ports(port_range=DEFAULT_PORT_RANGE, timeout=0.15):
    """Return list of open ports in range, checked in parallel."""
    open_ports = []
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = {
            pool.submit(_is_port_open, p, timeout): p
            for p in range(port_range[0], port_range[1])
        }
        for f in as_completed(futures):
            if f.result():
                open_ports.append(futures[f])
    return sorted(open_ports)


def _query_cdp_pages(port, timeout=1):
    """Query CDP /json endpoint. Returns list of pages or empty list."""
    try:
        url = f"http://localhost:{port}/json"
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return []


def find_whatsapp_port(preferred_port=None, port_range=DEFAULT_PORT_RANGE):
    """
    Find the CDP port where WhatsApp is running.

    1. If preferred_port is given, check it first (fast path).
    2. Parallel TCP scan to find open ports.
    3. Query /json only on open ports to find WhatsApp.

    Returns (port, pages) tuple or (None, []).
    """
    # Fast path: check preferred port first
    if preferred_port and _is_port_open(preferred_port):
        pages = _query_cdp_pages(preferred_port)
        for p in pages:
            if p.get("type") == "page" and "whatsapp" in p.get("url", "").lower():
                return preferred_port, pages

    # Parallel scan for open ports
    open_ports = _scan_open_ports(port_range)

    # Skip preferred port (already checked)
    if preferred_port:
        open_ports = [p for p in open_ports if p != preferred_port]

    # Query each open port for WhatsApp
    for port in open_ports:
        pages = _query_cdp_pages(port)
        for p in pages:
            if p.get("type") == "page" and "whatsapp" in p.get("url", "").lower():
                return port, pages

    return None, []


def find_whatsapp_ws_url(preferred_port=None, port_range=DEFAULT_PORT_RANGE):
    """
    Find WhatsApp's WebSocket debugger URL.
    Returns ws_url string or empty string.
    """
    port, pages = find_whatsapp_port(preferred_port, port_range)
    if port is None:
        return ""
    for p in pages:
        if p.get("type") == "page" and "whatsapp" in p.get("url", "").lower():
            return p.get("webSocketDebuggerUrl", "")
    return ""

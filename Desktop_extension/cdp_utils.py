"""
Fast CDP port scanner for WhatsApp Desktop.

Uses process-based discovery (primary) and socket scanning (fallback)
to find WhatsApp's CDP debugging port reliably.

Process-based discovery inspects msedgewebview2.exe command lines via WMI
and traces parent PIDs to confirm the process belongs to WhatsApp.
"""

import socket
import json
import re
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

DEFAULT_PORT_RANGE = (9222, 9400)

WHATSAPP_PROCESS_NAMES = {"whatsapp.exe", "whatsapp.root.exe"}


# ── Process-based CDP discovery (Layer 1) ──────────────────────────────

def _get_process_list():
    """Get all running processes via WMI.

    Returns dict mapping PID -> (name, parent_pid, command_line).
    Tries wmic first (faster), falls back to PowerShell.
    """
    processes = {}

    # Try wmic first (faster cold start)
    try:
        result = subprocess.run(
            ["wmic", "process", "get",
             "ProcessId,ParentProcessId,Name,CommandLine", "/format:csv"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if not line or line.startswith("Node,"):
                    continue
                # CSV format: Node,CommandLine,Name,ParentProcessId,ProcessId
                parts = line.split(",")
                if len(parts) < 5:
                    continue
                # CommandLine may contain commas, so we parse from the right
                pid_str = parts[-1].strip()
                ppid_str = parts[-2].strip()
                name = parts[-3].strip()
                cmd_line = ",".join(parts[1:-3]).strip()
                try:
                    pid = int(pid_str)
                    ppid = int(ppid_str)
                    processes[pid] = (name, ppid, cmd_line)
                except (ValueError, IndexError):
                    continue
            if processes:
                return processes
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    # Fallback: PowerShell
    try:
        ps_cmd = (
            "Get-CimInstance Win32_Process | "
            "Select-Object ProcessId, ParentProcessId, Name, CommandLine | "
            "ConvertTo-Json -Compress"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                data = [data]
            for proc in data:
                pid = proc.get("ProcessId")
                ppid = proc.get("ParentProcessId", 0)
                name = proc.get("Name", "")
                cmd = proc.get("CommandLine") or ""
                if pid is not None:
                    processes[int(pid)] = (name, int(ppid), cmd)
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass

    return processes


def _is_child_of_whatsapp(pid, process_map, max_depth=10):
    """Walk parent PID chain to check if process descends from WhatsApp."""
    visited = set()
    current = pid
    for _ in range(max_depth):
        if current in visited or current not in process_map:
            return False
        visited.add(current)
        name, ppid, _ = process_map[current]
        if name.lower() in WHATSAPP_PROCESS_NAMES:
            return True
        current = ppid
    return False


def find_whatsapp_cdp_port_by_process():
    """Find WhatsApp's CDP port by inspecting msedgewebview2.exe processes.

    Traces parent PIDs to confirm the WebView2 process belongs to WhatsApp,
    then extracts --remote-debugging-port from the command line.

    Returns int (port) or None.
    """
    process_map = _get_process_list()
    if not process_map:
        return None

    for pid, (name, ppid, cmd_line) in process_map.items():
        if name.lower() != "msedgewebview2.exe":
            continue
        if not cmd_line:
            continue

        # Check if this WebView2 process has a debug port argument
        match = re.search(r"--remote-debugging-port=(\d+)", cmd_line)
        if not match:
            continue

        # Verify it belongs to WhatsApp by tracing parent chain
        if _is_child_of_whatsapp(ppid, process_map):
            return int(match.group(1))

    return None


def diagnose_whatsapp_cdp():
    """Diagnose WhatsApp CDP status.

    Returns:
        'connected' - WhatsApp running with CDP port found
        'needs_restart' - WhatsApp running but no CDP port (env var not set at launch)
        'not_running' - WhatsApp is not running
    """
    process_map = _get_process_list()
    if not process_map:
        return "not_running"

    # Check if WhatsApp is running
    whatsapp_running = any(
        name.lower() in WHATSAPP_PROCESS_NAMES
        for name, _, _ in process_map.values()
    )

    if not whatsapp_running:
        return "not_running"

    # WhatsApp is running — check if any of its WebView2 processes have CDP
    for pid, (name, ppid, cmd_line) in process_map.items():
        if name.lower() != "msedgewebview2.exe":
            continue
        if not cmd_line:
            continue
        if "--remote-debugging-port=" not in cmd_line:
            continue
        if _is_child_of_whatsapp(ppid, process_map):
            return "connected"

    return "needs_restart"


# ── TCP port scanning (Layer 2 - fallback) ─────────────────────────────

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


# ── Main detection (process-based → port scan fallback) ────────────────

def find_whatsapp_port(preferred_port=None, port_range=DEFAULT_PORT_RANGE):
    """
    Find the CDP port where WhatsApp is running.

    1. Process-based discovery (inspects WebView2 command lines).
    2. If preferred_port is given, check it (fast path).
    3. Parallel TCP scan to find open ports.
    4. Query /json only on open ports to find WhatsApp.

    Returns (port, pages) tuple or (None, []).
    """
    # Layer 1: Process-based discovery (most reliable)
    process_port = find_whatsapp_cdp_port_by_process()
    if process_port and _is_port_open(process_port):
        pages = _query_cdp_pages(process_port)
        if pages:
            return process_port, pages

    # Layer 2 fallback: check preferred port
    if preferred_port and _is_port_open(preferred_port):
        pages = _query_cdp_pages(preferred_port)
        for p in pages:
            url = p.get("url", "").lower()
            if p.get("type") == "page" and ("whatsapp" in url or url.startswith("chrome-error://")):
                return preferred_port, pages

    # Layer 2 fallback: parallel scan for open ports
    open_ports = _scan_open_ports(port_range)

    # Skip ports already checked
    skip = set()
    if process_port:
        skip.add(process_port)
    if preferred_port:
        skip.add(preferred_port)
    open_ports = [p for p in open_ports if p not in skip]

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

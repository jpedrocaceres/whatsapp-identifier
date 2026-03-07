"""Check if WhatsApp page is available on a CDP port, or find a free port."""
import sys, json, urllib.request

port = int(sys.argv[1]) if len(sys.argv) > 1 else 9387
action = sys.argv[2] if len(sys.argv) > 2 else "check_wa"

if action == "check_wa":
    # Check if WhatsApp page exists on this port
    try:
        r = urllib.request.urlopen(f"http://localhost:{port}/json", timeout=2)
        pages = json.loads(r.read())
        has_wa = any("whatsapp" in p.get("url", "").lower() for p in pages if p.get("type") == "page")
        print("ok" if has_wa else "no_wa")
    except Exception:
        print("no_cdp")

elif action == "find_free":
    # Find a free port starting from the given port
    for p in range(port, port + 10):
        try:
            urllib.request.urlopen(f"http://localhost:{p}/json", timeout=1)
            continue  # Port is busy
        except Exception:
            print(p)
            sys.exit(0)
    print(port + 9)  # Fallback

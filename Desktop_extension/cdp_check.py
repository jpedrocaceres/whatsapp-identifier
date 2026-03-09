"""Check if WhatsApp page is available on a CDP port, or find a free port.

Exit codes for check_wa:
  0 = WhatsApp found on CDP port
  1 = CDP active but no WhatsApp page (another app using the port)
  2 = No CDP on this port
"""
import sys, json, urllib.request, socket

port = int(sys.argv[1]) if len(sys.argv) > 1 else 9351
action = sys.argv[2] if len(sys.argv) > 2 else "check_wa"

if action == "check_wa":
    # Check if WhatsApp page exists on this port
    try:
        r = urllib.request.urlopen(f"http://localhost:{port}/json", timeout=2)
        pages = json.loads(r.read())
        has_wa = any("whatsapp" in p.get("url", "").lower() for p in pages if p.get("type") == "page")
        if has_wa:
            print("ok")
            sys.exit(0)
        else:
            print("no_wa")
            sys.exit(1)
    except Exception:
        print("no_cdp")
        sys.exit(2)

elif action == "find_free":
    # Find a free port that is not in use
    for p in range(port, port + 20):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.15)
        try:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                print(p)
                sys.exit(0)
        except Exception:
            print(p)
            sys.exit(0)
        finally:
            s.close()
    print(port + 19)  # Fallback

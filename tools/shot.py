import sys, threading, http.server, socketserver, functools, os
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
from playwright.sync_api import sync_playwright
root = sys.argv[1]; page = sys.argv[2]; out = sys.argv[3]
w = int(sys.argv[4]) if len(sys.argv) > 4 else 1440; h = int(sys.argv[5]) if len(sys.argv) > 5 else 900
full = (sys.argv[6] == 'full') if len(sys.argv) > 6 else False
Handler = functools.partial(Q, directory=root)
Handler.log_message = lambda *a: None
srv = socketserver.TCPServer(('127.0.0.1', 0), Handler); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': w, 'height': h})
    pg.on('console', lambda m: print('console:', m.text))
    pg.on('pageerror', lambda e: print('pageerror:', e))
    pg.goto(f'http://127.0.0.1:{port}/{page}'); pg.wait_for_timeout(int(os.environ.get("WAIT", "1500")))
    pg.screenshot(path=out, full_page=full); b.close()
srv.shutdown(); print('saved', out)

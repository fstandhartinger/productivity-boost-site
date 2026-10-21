import sys, base64, threading, http.server, socketserver, functools, json
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
from playwright.sync_api import sync_playwright
root = sys.argv[1]; jobs = json.loads(sys.argv[2])
H = functools.partial(Q, directory=root); H.log_message = lambda *a: None
srv = socketserver.TCPServer(('127.0.0.1', 0), H); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.on('pageerror', lambda e: print('pageerror', e))
    for out, qs in jobs:
        pg.goto(f'http://127.0.0.1:{port}/tools/render.html?{qs}'); pg.wait_for_function('document.title=="done"', timeout=30000)
        data = pg.evaluate('window.__png').split(',', 1)[1]
        open(out, 'wb').write(base64.b64decode(data)); print('wrote', out)
    b.close()
srv.shutdown()

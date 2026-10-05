import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class DashboardHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()


port, directory = int(sys.argv[1]), sys.argv[2]
handler = partial(DashboardHandler, directory=directory)
ThreadingHTTPServer(('0.0.0.0', port), handler).serve_forever()

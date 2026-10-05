import http.server
import json
import socket
import threading
import time
import unittest

import requests

from evcc_service_loader import new_service_without_dbus

TEST_TIMEOUT_SECONDS = 0.5


class _FixedResponseHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(self.server.status)
        self.end_headers()
        self.wfile.write(self.server.body)

    def log_message(self, format, *args):
        pass


class EvccPollingTest(unittest.TestCase):
    def setUp(self):
        self.service = new_service_without_dbus()
        self.service._httpTimeout = TEST_TIMEOUT_SECONDS

    def _poll(self, url):
        self.service._getEvccChargerStatusUrl = lambda: url
        return self.service._getEvccChargerData()

    def _serve(self, status, payload):
        server = http.server.HTTPServer(("127.0.0.1", 0), _FixedResponseHandler)
        server.status = status
        server.body = json.dumps(payload).encode()
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_port}/api/state"

    def test_poll_gives_up_when_evcc_accepts_but_never_answers(self):
        listener = socket.socket()
        self.addCleanup(listener.close)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        url = f"http://127.0.0.1:{listener.getsockname()[1]}/api/state"

        started = time.monotonic()
        with self.assertRaises(requests.exceptions.Timeout):
            self._poll(url)

        self.assertLess(time.monotonic() - started, TEST_TIMEOUT_SECONDS * 4)

    def test_http_error_is_reported_with_url(self):
        url = self._serve(500, {})

        with self.assertRaises(ConnectionError) as raised:
            self._poll(url)

        self.assertEqual(str(raised.exception), f"No response from EVCC-Charger - {url}")

    def test_state_is_returned_as_sent_by_current_evcc(self):
        state = {"version": "0.316.2", "loadpoints": [{"title": "Wallbox"}]}

        self.assertEqual(self._poll(self._serve(200, state)), state)

    def test_result_wrapper_of_old_evcc_is_unwrapped(self):
        state = {"version": "0.200.0", "loadpoints": []}

        self.assertEqual(self._poll(self._serve(200, {"result": state})), state)


if __name__ == "__main__":
    unittest.main()

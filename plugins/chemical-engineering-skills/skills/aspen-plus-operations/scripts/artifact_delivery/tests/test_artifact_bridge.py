"""Synthetic HTTP/byte/lifecycle checks. No Codex UI or engineering solver runs."""
import hashlib
import http.client
import socket
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from urllib.parse import quote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from artifact_delivery.artifact_bridge import Artifact, ArtifactBridge, load_artifacts


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.payload = b"PK\x03\x04\x00\xff\x10\r\nsynthetic archive bytes"
        self.artifact = Artifact("结果 文件.zip", "模型 <文件>", self.payload)
        self.bridge = ArtifactBridge([self.artifact], idle_seconds=30, lifetime_seconds=30)
        self.bridge.start()

    def tearDown(self):
        self.bridge.close()

    def request(self, path=None, method="GET", host=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.bridge.port, timeout=2)
        try:
            headers = {} if host is None else {"Host": host}
            conn.request(method, path or f"/{self.bridge.token}/" + quote(self.artifact.name, safe=""), headers=headers)
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            conn.close()

    def test_exact_binary_bytes_and_digest(self):
        status, headers, body = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(body, self.payload)
        self.assertEqual(headers["X-Artifact-SHA256"], hashlib.sha256(body).hexdigest())
        self.assertEqual(int(headers["Content-Length"]), len(body))

    def test_unicode_download_filename(self):
        status, headers, _ = self.request()
        self.assertEqual(status, 200)
        self.assertIn("filename*=UTF-8''" + quote(self.artifact.name, safe=""), headers["Content-Disposition"])

    def test_head_has_no_body_but_actual_length(self):
        status, headers, body = self.request(method="HEAD")
        self.assertEqual((status, body), (200, b""))
        self.assertEqual(int(headers["Content-Length"]), len(self.payload))

    def test_index_escapes_label_and_contains_valid_link(self):
        status, _, body = self.request(f"/{self.bridge.token}/")
        text = body.decode()
        self.assertEqual(status, 200)
        self.assertIn("模型 &lt;文件&gt;", text)
        self.assertIn(quote(self.artifact.name, safe=""), text)
        self.assertNotIn("模型 <文件>", text)

    def test_unknown_file_not_exposed(self):
        status, _, _ = self.request(f"/{self.bridge.token}/unselected.txt")
        self.assertEqual(status, 404)

    def test_wrong_capability_not_accepted(self):
        self.assertEqual(self.request("/wrong-token/")[0], 404)

    def test_traversal_and_absolute_paths_not_resolved(self):
        for tail in ["../unselected.txt", "%2e%2e/unselected.txt", "C:/unselected.txt", "%2fetc%2fpasswd"]:
            with self.subTest(tail=tail):
                self.assertEqual(self.request(f"/{self.bridge.token}/" + tail)[0], 404)

    def test_foreign_host_rejected(self):
        self.assertEqual(self.request(host="unrelated.example")[0], 421)

    def test_post_cannot_modify_files(self):
        self.assertEqual(self.request(method="POST")[0], 405)

    def test_bound_only_to_loopback(self):
        self.assertEqual(self.bridge.server.server_address[0], "127.0.0.1")

    def test_explicit_close_releases_listener(self):
        self.bridge.close()
        with self.assertRaises((ConnectionError, OSError)):
            self.request()

    def test_partial_request_socket_is_reclaimed_by_close(self):
        conn = socket.create_connection(("127.0.0.1", self.bridge.port), timeout=2)
        conn.sendall(b"GET /unfinished HTTP/1.1\r\nHost:")
        deadline = time.monotonic() + 1
        while not self.bridge.server.connections and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(self.bridge.server.connections)
        self.bridge.close()
        try:
            self.assertFalse(self.bridge.server.connections)
            self.assertEqual(conn.recv(1), b"")
        finally:
            conn.close()

    def test_concurrent_close_returns_only_after_listener_closed(self):
        threads = [threading.Thread(target=self.bridge.close) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())
        self.assertTrue(self.bridge.closed.is_set())
        self.assertFalse(self.bridge._serving.is_alive())
        self.assertEqual(self.bridge.server.socket.fileno(), -1)


class SnapshotAndLifetimeTests(unittest.TestCase):
    def test_snapshot_stays_bound_to_original_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "report.zip"
            path.write_bytes(b"original snapshot")
            snapshot = load_artifacts([{"path": str(path)}])
            path.write_bytes(b"later source")
            self.assertEqual(snapshot[0].content, b"original snapshot")

    def test_size_limit_is_enforced_on_actual_read(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "report.zip"
            path.write_bytes(b"12345")
            with self.assertRaises(ValueError):
                load_artifacts([{"path": str(path)}], max_bytes=4)

    def test_duplicate_names_are_rejected(self):
        a = Artifact("same.zip", "one", b"one")
        with self.assertRaises(ValueError):
            ArtifactBridge([a, a])

    def test_directories_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                load_artifacts([{"path": temp}])

    def test_invalid_header_names_and_mutable_bytes_rejected(self):
        for name in ["", "a\r\nheader.zip", "../a.zip", "a\\b.zip", "a\x00.zip"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                Artifact(name, "label", b"x")
        with self.assertRaises(TypeError):
            Artifact("a.zip", "label", bytearray(b"x"))

    def test_nonfinite_and_nonpositive_lifetimes_rejected(self):
        for t in [float("nan"), float("inf"), -1, 0]:
            with self.subTest(t=t), self.assertRaises(ValueError):
                ArtifactBridge([Artifact("a", "a", b"a")], idle_seconds=t)

    def test_idle_expiry_releases_listener(self):
        bridge = ArtifactBridge([Artifact("a", "a", b"a")], idle_seconds=.2, lifetime_seconds=3)
        bridge.start()
        try:
            self.assertTrue(bridge.closed.wait(2))
            bridge._expiry.join(timeout=2)
            conn = http.client.HTTPConnection("127.0.0.1", bridge.port, timeout=.5)
            with self.assertRaises((ConnectionError, OSError)):
                conn.connect()
            conn.close()
        finally:
            bridge.close()

    def test_lifetime_caps_repeated_valid_access(self):
        bridge = ArtifactBridge([Artifact("a", "a", b"a")], idle_seconds=5, lifetime_seconds=.4)
        bridge.start()
        try:
            for _ in range(8):
                if bridge.closed.is_set():
                    break
                conn = http.client.HTTPConnection("127.0.0.1", bridge.port, timeout=.5)
                try:
                    conn.request("GET", urlsplit(bridge.url).path + "a")
                    conn.getresponse().read()
                except OSError:
                    break
                finally:
                    conn.close()
                time.sleep(.08)
            self.assertTrue(bridge.closed.wait(1))
        finally:
            bridge.close()


if __name__ == "__main__":
    unittest.main()

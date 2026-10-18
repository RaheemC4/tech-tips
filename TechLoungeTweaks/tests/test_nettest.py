import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import nettest

class NetworkTest(unittest.TestCase):
    def test_rate_limit_switches_shared_server_and_counts_received_bytes(self):
        stop = threading.Event()
        counter = [0, {"server": "Cloudflare"}]
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size):
                stop.set()
                return b"x" * 321
        error = HTTPError(nettest.DOWN_URL, 429, "Too Many Requests", {}, None)
        # Do not wait in this unit test; production uses an interruptible backoff.
        def wait(_): return False
        with patch.object(nettest.urllib.request, "urlopen", side_effect=[error, Response()]) as open_url, patch.object(stop, "wait", side_effect=wait), patch.object(nettest, "_ctx", return_value=None):
            nettest._download_worker(stop, counter, threading.Lock())
        self.assertEqual(counter[0], 321)
        self.assertEqual(counter[1]["server"], "OVHcloud")
        self.assertTrue(open_url.call_args_list[1].args[0].full_url.startswith(nettest.FALLBACK_DOWN_URL + "?tl="))
        self.assertEqual(open_url.call_count, 2)

    def test_no_retry_storm_when_backup_is_limited(self):
        stop = threading.Event()
        counter = [0, {"url": nettest.FALLBACK_DOWN_URL}]
        error = HTTPError(nettest.FALLBACK_DOWN_URL, 429, "Too Many Requests", {}, None)
        with patch.object(nettest.urllib.request, "urlopen", side_effect=error) as open_url, patch.object(stop, "wait", return_value=True) as wait, patch.object(nettest, "_ctx", return_value=None):
            nettest._download_worker(stop, counter, threading.Lock())
        self.assertEqual(open_url.call_count, 1)
        wait.assert_called_once_with(1.0)
        self.assertEqual(counter[0], 0)

    def test_each_phase_emits_its_own_results(self):
        events = []
        with patch.object(nettest.time, "perf_counter", side_effect=[0, 0, 5]), patch.object(nettest.time, "sleep"), patch.object(nettest, "tcp_ping", return_value=7), patch.object(nettest, "_run_phase", side_effect=[(850.4, [8]), (119.5, [11])]), patch.object(nettest, "select_download_server", return_value=("https://fixture.invalid", "Fixture")):
            result = nettest.run_test(on_partial=lambda stage, data: events.append((stage, data)))
        self.assertEqual([stage for stage, _ in events], ["idle", "download", "upload", "grade"])
        self.assertEqual(events[0][1]["idle_ms"], 7)
        self.assertNotIn("download_mbps", events[0][1])
        self.assertEqual(events[1][1]["download_mbps"], 850.4)
        self.assertNotIn("upload_mbps", events[1][1])
        self.assertEqual(result["grade"], "A+")

    def test_download_server_selection_uses_measured_latency(self):
        with patch.object(nettest, "DOWNLOAD_SERVERS", (("lon", "London"), ("ams", "Amsterdam"))), patch.object(nettest, "tcp_ping", side_effect=lambda host, *args, **kwargs: 7 if host.startswith("lon.") else 23):
            url, name = nettest.select_download_server()
        self.assertEqual(name, "Clouvider London")
        self.assertEqual(url, "https://lon.speedtest.clouvider.net/backend/garbage.php?ckSize=1024")
        with patch.object(nettest, "tcp_ping", return_value=None):
            self.assertEqual(nettest.select_download_server()[1], "Cloudflare")

    def test_live_samples_do_not_replace_final_measurements(self):
        live = []
        def phase(*args, **kwargs):
            kwargs["on_sample"](20, [9])
            kwargs["on_sample"](30, [11])
            return 25, [11]
        with patch.object(nettest.time, "perf_counter", side_effect=[0, 0, 5]), patch.object(nettest.time, "sleep"), patch.object(nettest, "tcp_ping", return_value=7), patch.object(nettest, "_run_phase", side_effect=phase), patch.object(nettest, "select_download_server", return_value=("https://fixture.invalid", "Fixture")):
            result = nettest.run_test(on_live=lambda stage, data: live.append((stage, data)))
        self.assertEqual([stage for stage, _ in live], ["idle", "download", "download", "upload", "upload"])
        self.assertEqual(live[1][1]["download_mbps"], 20)
        self.assertEqual(live[2][1]["download_mbps"], 30)
        self.assertEqual(live[-1][1]["upload_mbps"], 30)
        self.assertEqual(live[-1][1]["grade"], "A+")
        self.assertEqual(live[-1][1]["live_fields"], ["upload_mbps", "grade"])
        self.assertEqual(live[0][1]["idle_ms"], 7)
        self.assertNotIn("latency_live_ms", live[-1][1])
        self.assertNotIn("latency_phase", live[-1][1])
        self.assertEqual(live[-1][1]["idle_ms"], 7)
        self.assertEqual(result["idle_ms"], 7)
        self.assertNotIn("latency_live_ms", result)
        self.assertEqual(result["download_mbps"], 25)
        self.assertEqual(result["upload_mbps"], 25)
        self.assertNotIn("live_fields", result)

    def test_one_estimator_tracks_gigabit_bytes_and_does_not_reselect_an_old_peak(self):
        meter = nettest._Throughput(0)
        # Warm-up is excluded. Then 1 second at 1600 Mbps and 3 at 200 Mbps.
        meter.sample(2.5, 50_000_000)
        self.assertEqual(meter.sample(3.5, 250_000_000), 1600)
        self.assertEqual(meter.sample(4.5, 275_000_000), 900)
        self.assertEqual(meter.sample(5.5, 300_000_000), 2000 / 3)
        self.assertEqual(meter.sample(6.5, 325_000_000), 550)
        self.assertEqual(meter.rate, 550)  # Final is the latest live estimate, not 1600.

    def test_phase_last_live_sample_equals_final_result(self):
        clock = [0.0]
        def sleep(seconds): clock[0] += seconds
        def worker(stop, counter, lock): pass
        class Thread:
            def __init__(self, **kwargs): pass
            def start(self): pass
        class Sampler:
            samples = [7]
            def start(self): pass
            def stop(self): pass
        # Drive the real phase loop with a deterministic 100 MB/s counter.
        class Meter(nettest._Throughput):
            def sample(self, now, total):
                return super().sample(now, round(now * 100_000_000))
        live = []
        with patch.object(nettest.time, "perf_counter", side_effect=lambda: clock[0]), patch.object(nettest.time, "sleep", side_effect=sleep), patch.object(nettest.threading, "Thread", Thread), patch.object(nettest, "_Sampler", Sampler), patch.object(nettest, "_Throughput", Meter):
            result, latency = nettest._run_phase(worker, 5, 4, on_sample=lambda rate, samples: live.append(rate))
        self.assertAlmostEqual(result, 800)
        self.assertEqual(live[-1], result)
        self.assertGreater(len(live), 10)
        self.assertEqual(latency, [7])

    def test_upload_reports_blocks_before_post_finishes(self):
        stop = threading.Event(); counter = [0, {}]
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): stop.set()
        observations = []
        def send(request, **kwargs):
            for block in request.data:
                observations.append(counter[0])
                self.assertLessEqual(len(block), 64 * 1024)
            return Response()
        with patch.object(nettest.urllib.request, "urlopen", side_effect=send), patch.object(nettest, "_ctx", return_value=None):
            nettest._upload_worker(stop, counter, threading.Lock(), chunk=200_000)
        self.assertEqual(observations, [0, 65536, 131072, 196608])
        self.assertEqual(counter[0], 200_000)
        self.assertEqual(counter[1]["successful_uploads"], 1)


if __name__ == "__main__": unittest.main()

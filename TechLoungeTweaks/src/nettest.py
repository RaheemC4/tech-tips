"""Bufferbloat / latency-under-load test.

Live and final throughput share a time-weighted estimate from received/sent
bytes after connection warm-up. Parallel transfers start together;
completion never switches to an earlier peak window.
"""

import os
import uuid
import socket
import http.client
from concurrent.futures import ThreadPoolExecutor
import ssl
import threading
import time
import urllib.request
import urllib.error

DOWN_URL = "https://speed.cloudflare.com/__down?bytes={n}"
FALLBACK_DOWN_URL = "https://proof.ovh.net/files/100Mb.dat"
UP_URL = "https://speed.cloudflare.com/__up"
PING_HOST = "1.1.1.1"
PING_PORT = 443

UA = {"User-Agent": "TechLoungeTweaks/1.0"}

DOWN_THREADS = 8
UP_THREADS = 6
READ_CHUNK = 1 << 18          # Buffered reads avoid tiny TLS reads limiting gigabit throughput
WARMUP = 2.5                  # seconds of slow-start to discard
SAMPLE_INTERVAL = 0.2         # measured updates; UI interpolates between them


def tcp_ping(host=PING_HOST, port=PING_PORT, timeout=3.0):
    t0 = time.perf_counter()
    try:
        s = socket.create_connection((host, port), timeout)
        s.close()
        return (time.perf_counter() - t0) * 1000.0
    except Exception:
        return None


def median(vals):
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return None
    n = len(vals)
    m = n // 2
    return vals[m] if n % 2 else (vals[m - 1] + vals[m]) / 2.0


def percentile(vals, p):
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return None
    return vals[int(round((len(vals) - 1) * p))]


def jitter(vals):
    """Mean absolute difference between consecutive pings (RFC 3550 style).

    This is what people mean by jitter: not how high the ping is, but how
    much it jumps around from one packet to the next.
    """
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return None
    diffs = [abs(vals[i] - vals[i - 1]) for i in range(1, len(vals))]
    return sum(diffs) / len(diffs)


def stats(vals):
    raw = [v for v in vals if v is not None]
    vals = raw
    if not vals:
        return None
    return {
        "min": min(vals), "max": max(vals),
        "med": median(vals),
        "p25": percentile(vals, 0.25), "p75": percentile(vals, 0.75),
        "p95": percentile(vals, 0.95),
        "jitter": jitter(raw),
        "n": len(vals),
    }


class _Sampler(threading.Thread):
    def __init__(self, interval=0.2):
        super().__init__(daemon=True)
        self.interval = interval
        self.samples = []
        self._stop = threading.Event()

    def run(self):
        while not self._stop.is_set():
            v = tcp_ping()
            if v is not None:
                self.samples.append(v)
            self._stop.wait(self.interval)

    def stop(self):
        self._stop.set()


def _ctx():
    try:
        c = ssl.create_default_context()
        return c
    except Exception:
        return None


# Public LibreSpeed test nodes. Select by measured reachability, not IP geolocation.
DOWNLOAD_SERVERS = (
    ("lon", "London"), ("ams", "Amsterdam"), ("fra", "Frankfurt"),
    ("nyc", "New York"), ("atl", "Atlanta"), ("la", "Los Angeles"),
)

def select_download_server():
    def probe(server):
        code, city = server
        host = code + ".speedtest.clouvider.net"
        latency = tcp_ping(host, 443, timeout=1.5)
        return latency, "https://" + host + "/backend/garbage.php?ckSize=1024", "Clouvider " + city
    with ThreadPoolExecutor(max_workers=len(DOWNLOAD_SERVERS)) as pool:
        available = [item for item in pool.map(probe, DOWNLOAD_SERVERS) if item[0] is not None]
    if not available:
        return DOWN_URL.format(n=25_000_000), "Cloudflare"
    best = min(available, key=lambda item: item[0])
    return best[1], best[2]


def _download_worker(stop_evt, counter, lock, size=25_000_000):
    context = _ctx()
    while not stop_evt.is_set():
        with lock:
            url = counter[1].get("url", DOWN_URL.format(n=size))
        try:
            separator = "&" if "?" in url else "?"
            req = urllib.request.Request(url + separator + "tl=" + uuid.uuid4().hex,
                                         headers={**UA, "Accept-Encoding": "identity", "Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=3, context=context) as resp:
                received = 0
                while not stop_evt.is_set():
                    try:
                        buf = resp.read(READ_CHUNK)
                    except http.client.IncompleteRead as incomplete:
                        with lock:
                            counter[0] += len(incomplete.partial)
                        break
                    if not buf:
                        break
                    received += len(buf)
                    with lock:
                        counter[0] += len(buf)
                if not received and not stop_evt.is_set():
                    raise OSError("Download server returned no data")
        except Exception as exc:
            with lock:
                counter[1]["error"] = str(exc)
                # Share a one-way fallback across streams. A late failure from
                # the previous host must not overwrite a newer selection.
                if counter[1].get("url", DOWN_URL.format(n=size)) == url and url != FALLBACK_DOWN_URL:
                    limited = isinstance(exc, urllib.error.HTTPError) and exc.code == 429
                    use_ovh = limited or url.startswith("https://speed.cloudflare.com/")
                    counter[1]["url"] = FALLBACK_DOWN_URL if use_ovh else DOWN_URL.format(n=size)
                    counter[1]["server"] = "OVHcloud" if use_ovh else "Cloudflare"
            if stop_evt.wait(1.0):
                return


def _upload_worker(stop_evt, counter, lock, chunk=4_000_000):
    # Count each block after urllib sends it, instead of waiting for a whole POST.
    # Incompressible data avoids measuring compression instead of network capacity.
    payload = os.urandom(chunk)
    while not stop_evt.is_set():
        def blocks():
            for offset in range(0, chunk, 64 * 1024):
                if stop_evt.is_set():
                    raise InterruptedError("Upload stopped")
                block = payload[offset:offset + 64 * 1024]
                yield block
                with lock:
                    counter[0] += len(block)
        try:
            req = urllib.request.Request(UP_URL, data=blocks(), headers={
                **UA, "Content-Length": str(chunk), "Content-Type": "application/octet-stream"})
            with urllib.request.urlopen(req, timeout=10, context=_ctx()):
                with lock:
                    counter[1]["successful_uploads"] = counter[1].get("successful_uploads", 0) + 1
        except Exception as exc:
            with lock:
                counter[1]["error"] = str(exc)
            if stop_evt.wait(0.3):
                return


class _Throughput:
    """Time-weighted byte rate, shared by every live update and the final result."""
    def __init__(self, start):
        self.start = start
        self.origin = (start, 0)
        self.ready = False
        self.rate = 0.0
        self.first_data = False

    def sample(self, now, total):
        if not self.first_data:
            if total <= 0:
                return 0.0
            # DNS, TLS and failed-server delays are not transfer time. Begin
            # slow-start warm-up only when a stream actually delivers bytes.
            self.first_data = True
            self.start = now
            self.origin = (now, total)
            return 0.0
        if not self.ready and now - self.start >= WARMUP:
            self.origin = (now, total)
            self.ready = True
            return self.rate
        elapsed = now - self.origin[0]
        if elapsed > 0:
            self.rate = max(0, total - self.origin[1]) * 8 / elapsed / 1_000_000
        return self.rate


def _run_phase(worker, seconds, threads, progress=None, label="", diagnostics=None, download_server=None, on_sample=None):
    stop_evt = threading.Event()
    counter = [0, {"server": "Cloudflare"}]
    if download_server is not None:
        counter[1].update(url=download_server[0], server=download_server[1])
    lock = threading.Lock()
    sampler = _Sampler()
    workers = []
    def add_worker():
        thread = threading.Thread(target=worker, args=(stop_evt, counter, lock), daemon=True)
        workers.append(thread)
        thread.start()
    t0 = time.perf_counter()
    meter = _Throughput(t0)
    for _ in range(threads):
        add_worker()
    sampler_started = False
    last_live = t0
    try:
        while True:
            now = time.perf_counter()
            elapsed = now - t0
            with lock:
                total = counter[0]
            rate = meter.sample(now, total)
            if meter.ready and not sampler_started:
                sampler.start()
                sampler_started = True
            finished = elapsed >= seconds
            if on_sample and (now - last_live >= SAMPLE_INTERVAL or finished):
                confirmed = worker is not _upload_worker or counter[1].get("successful_uploads")
                on_sample(rate, list(sampler.samples) if rate > 0 and confirmed else [])
                last_live = now
            if progress:
                progress(label, min(1.0, elapsed / seconds))
            if finished:
                break
            time.sleep(0.05)
    finally:
        stop_evt.set()
        if sampler_started:
            sampler.stop()
    if diagnostics is not None:
        with lock:
            diagnostics.update(counter[1])
            diagnostics["bytes"] = total
            diagnostics["streams"] = len(workers)
    # Failed POSTs can have written into a socket buffer. Do not call that success.
    if worker is _upload_worker and not counter[1].get("successful_uploads"):
        return 0.0, sampler.samples
    return meter.rate, sampler.samples


def grade_for(increase_ms):
    if increase_ms is None:
        return "-", "Could not measure"
    for limit, letter, text in [
        (5,   "A+", "Excellent - no measurable lag under load"),
        (30,  "A",  "Great - stays responsive under load"),
        (60,  "B",  "Good - slight latency increase under load"),
        (200, "C",  "Fair - noticeable lag while downloading"),
        (400, "D",  "Poor - games will spike when the line is busy"),
    ]:
        if increase_ms < limit:
            return letter, text
    return "F", "Bad - heavy lag whenever anything downloads"


# What each activity needs: (max loaded latency ms, min Mbps down)
REQUIREMENTS = [
    ("Web browsing",       400, 5),
    ("Audio calls",        200, 1),
    ("4K video streaming", 500, 25),
    ("Video conferencing", 150, 5),
    ("Low latency gaming",  75, 5),
]


def verdicts(loaded_ms, down_mbps, up_mbps=0):
    """A measurement of 0 means the probe failed, not that the link is dead -
    fall back to whichever direction did report a figure."""
    speed = max(down_mbps or 0, 0)
    if speed <= 0:
        speed = max(up_mbps or 0, 0)
    out = []
    for name, max_ms, min_mbps in REQUIREMENTS:
        if loaded_ms is None or speed <= 0:
            out.append((name, None))     # unknown, not a failure
            continue
        out.append((name, loaded_ms <= max_ms and speed >= min_mbps))
    return out


def run_test(progress=None, duration=12, on_partial=None, on_live=None):
    """on_partial(stage, partial_result) fires as each stage completes."""
    result = {}

    def emit(stage):
        if on_partial:
            try:
                on_partial(stage, dict(result))
            except Exception:
                pass

    def live(stage, rate, latency):
        if not on_live:
            return
        snapshot = dict(result)
        field = "download_mbps" if stage == "download" else "upload_mbps"
        snapshot[field] = rate
        fields = [field]
        loaded = median(latency[-5:])
        complete_download = stage == "download" or (result.get("download_mbps") or 0) > 0
        if rate > 0 and complete_download and loaded is not None and result.get("idle_ms") is not None:
            worst = max(loaded, result.get("down_ms") or loaded)
            snapshot["grade"], _ = grade_for(max(0, worst - result["idle_ms"]))
            fields.append("grade")
        snapshot["live_fields"] = fields
        on_live(stage, snapshot)

    if progress:
        progress("Measuring idle latency", 0.0)
    idle = []
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 4.0:
        v = tcp_ping()
        if v is not None:
            idle.append(v)
            if on_live:
                on_live("idle", {"idle_ms": median(idle[-8:]), "latency_phase": "Idle", "live_fields": ["idle_ms"]})
        if progress:
            progress("Measuring idle latency",
                     (time.perf_counter() - t0) / 4.0)
        time.sleep(0.15)

    if not idle:
        result["error"] = ("No connection, or the test host is blocked by "
                           "your firewall.")
        return result

    result["idle"] = stats(idle)
    result["idle_ms"] = result["idle"]["med"]
    emit("idle")

    if progress:
        progress("Selecting download server", 0.0)
    download_server = select_download_server()
    result["download_server"] = download_server[1]
    download = {}
    down_mbps, down_lat = _run_phase(_download_worker, duration, DOWN_THREADS,
                                     progress, "Testing download", diagnostics=download, download_server=download_server,
                                     on_sample=lambda rate, latency: live("download", rate, latency))
    result["download_mbps"] = down_mbps if down_mbps > 0 else None
    result["download_server"] = download.get("server", "Cloudflare")
    if down_mbps <= 0:
        result["download_error"] = "Download unavailable. " + download.get("error", "No sustained data received.")
    result["down"] = stats(down_lat)
    result["down_ms"] = result["down"]["med"] if result["down"] and down_mbps > 0 else None
    emit("download")

    upload = {}
    up_mbps, up_lat = _run_phase(_upload_worker, duration, UP_THREADS,
                                 progress, "Testing upload", diagnostics=upload,
                                 on_sample=lambda rate, latency: live("upload", rate, latency))
    result["upload_mbps"] = up_mbps if up_mbps > 0 else None
    if up_mbps <= 0:
        result["upload_error"] = "Upload unavailable. " + upload.get("error", "No successful transfer.")
    result["up"] = stats(up_lat)
    result["up_ms"] = result["up"]["med"] if result["up"] and up_mbps > 0 else None
    emit("upload")

    js = [x["jitter"] for x in (result.get("idle"), result.get("down"),
                                result.get("up")) if x and x["jitter"]]
    result["jitter_ms"] = max(js) if js else None
    result["idle_jitter"] = (result["idle"] or {}).get("jitter")

    loaded = [v for v in (result["down_ms"], result["up_ms"]) if v]
    worst = max(loaded) if loaded else None
    result["loaded_ms"] = worst
    complete = down_mbps > 0 and up_mbps > 0 and result["down_ms"] is not None and result["up_ms"] is not None
    result["increase_ms"] = (worst - result["idle_ms"]) if complete else None
    result["grade"], result["verdict"] = grade_for(result["increase_ms"])
    if not complete:
        result["verdict"] = "Incomplete test - retry to measure latency under load"
    emit("grade")
    result["activities"] = verdicts(worst, down_mbps, up_mbps)
    return result

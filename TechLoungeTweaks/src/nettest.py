"""Bufferbloat / latency-under-load test.

Speed is taken as the best sustained window after TCP slow-start settles,
not a naive total/elapsed average - averaging in the ramp-up is what makes
a gigabit line measure like 800 Mbps.
"""

import socket
import ssl
import threading
import time
import urllib.request

DOWN_URL = "https://speed.cloudflare.com/__down?bytes={n}"
UP_URL = "https://speed.cloudflare.com/__up"
PING_HOST = "1.1.1.1"
PING_PORT = 443

UA = {"User-Agent": "TechLoungeTweaks/1.0"}

DOWN_THREADS = 12
UP_THREADS = 6
READ_CHUNK = 1 << 20          # 1 MiB reads keep Python out of the way
WARMUP = 2.5                  # seconds of slow-start to discard
WINDOW = 3.0                  # width of the sustained-rate window


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


DOWN_SIZES = (25_000_000, 10_000_000)


def _download_worker(stop_evt, counter, lock, size=25_000_000):
    sizes = list(DOWN_SIZES)
    while not stop_evt.is_set():
        ok = False
        for sz in sizes:
            if stop_evt.is_set():
                return
            try:
                req = urllib.request.Request(DOWN_URL.format(n=sz),
                                             headers=UA)
                with urllib.request.urlopen(req, timeout=25,
                                            context=_ctx()) as resp:
                    read = resp.read
                    while not stop_evt.is_set():
                        buf = read(READ_CHUNK)
                        if not buf:
                            break
                        with lock:
                            counter[0] += len(buf)
                ok = True
                break
            except Exception:
                continue
        if not ok and stop_evt.wait(0.3):
            return


def _upload_worker(stop_evt, counter, lock, chunk=4_000_000):
    payload = b"\0" * chunk
    while not stop_evt.is_set():
        try:
            req = urllib.request.Request(UP_URL, data=payload, headers=UA)
            with urllib.request.urlopen(req, timeout=25, context=_ctx()):
                pass
            with lock:
                counter[0] += chunk
        except Exception:
            if stop_evt.wait(0.3):
                return


def _best_window(marks):
    """marks = [(t, cumulative_bytes)]. Return best sustained Mbps."""
    if len(marks) < 3:
        return 0.0
    best = 0.0
    j = 0
    for i in range(len(marks)):
        t_i, b_i = marks[i]
        while j < i and t_i - marks[j][0] > WINDOW:
            j += 1
        dt = t_i - marks[j][0]
        if dt >= WINDOW * 0.6:
            rate = (b_i - marks[j][1]) * 8.0 / dt / 1_000_000.0
            best = max(best, rate)
    return best


def _run_phase(worker, seconds, threads, progress=None, label=""):
    stop_evt = threading.Event()
    counter = [0]
    lock = threading.Lock()
    sampler = _Sampler()

    workers = [threading.Thread(target=worker,
                                args=(stop_evt, counter, lock), daemon=True)
               for _ in range(threads)]
    for w in workers:
        w.start()

    t0 = time.perf_counter()
    marks = []
    sampler_started = False

    while True:
        now = time.perf_counter()
        el = now - t0
        if el >= seconds:
            break
        # start measuring only once slow-start is over
        if el >= WARMUP:
            if not sampler_started:
                sampler.start()
                sampler_started = True
            with lock:
                marks.append((now, counter[0]))
        if progress:
            progress(label, el / seconds)
        time.sleep(0.1)

    stop_evt.set()
    if sampler_started:
        sampler.stop()
    return _best_window(marks), sampler.samples


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


def run_test(progress=None, duration=12, on_partial=None):
    """on_partial(stage, partial_result) fires as each stage completes."""
    result = {}

    def emit(stage):
        if on_partial:
            try:
                on_partial(stage, dict(result))
            except Exception:
                pass

    if progress:
        progress("Measuring idle latency", 0.0)
    idle = []
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 4.0:
        v = tcp_ping()
        if v is not None:
            idle.append(v)
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

    down_mbps, down_lat = _run_phase(_download_worker, duration, DOWN_THREADS,
                                     progress, "Testing download")
    result["download_mbps"] = down_mbps
    result["down"] = stats(down_lat)
    result["down_ms"] = result["down"]["med"] if result["down"] else None
    emit("download")

    up_mbps, up_lat = _run_phase(_upload_worker, duration, UP_THREADS,
                                 progress, "Testing upload")
    result["upload_mbps"] = up_mbps
    result["up"] = stats(up_lat)
    result["up_ms"] = result["up"]["med"] if result["up"] else None
    emit("upload")

    js = [x["jitter"] for x in (result.get("idle"), result.get("down"),
                                result.get("up")) if x and x["jitter"]]
    result["jitter_ms"] = max(js) if js else None
    result["idle_jitter"] = (result["idle"] or {}).get("jitter")

    loaded = [v for v in (result["down_ms"], result["up_ms"]) if v]
    worst = max(loaded) if loaded else None
    result["loaded_ms"] = worst
    result["increase_ms"] = (worst - result["idle_ms"]) if worst else None
    result["grade"], result["verdict"] = grade_for(result["increase_ms"])
    emit("grade")
    result["activities"] = verdicts(worst, down_mbps, up_mbps)
    return result

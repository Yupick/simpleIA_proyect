import time
from typing import Dict
from threading import Lock

_lock = Lock()
_total_requests = 0
_path_counts: Dict[str, int] = {}
_latency_acc_ms: Dict[str, float] = {}
_latency_samples: Dict[str, int] = {}
_status_counts: Dict[int, int] = {}
_path_status_counts: Dict[str, Dict[int, int]] = {}


def record_request(path: str):
    global _total_requests
    with _lock:
        _total_requests += 1
        _path_counts[path] = _path_counts.get(path, 0) + 1


def record_latency(path: str, ms: float):
    with _lock:
        _latency_acc_ms[path] = _latency_acc_ms.get(path, 0.0) + ms
        _latency_samples[path] = _latency_samples.get(path, 0) + 1


def record_status(path: str, status_code: int):
    with _lock:
        _status_counts[status_code] = _status_counts.get(status_code, 0) + 1
        d = _path_status_counts.get(path)
        if d is None:
            d = {}
            _path_status_counts[path] = d
        d[status_code] = d.get(status_code, 0) + 1


def snapshot():
    with _lock:
        avg_latencies = {}
        for p, total in _latency_acc_ms.items():
            n = _latency_samples.get(p, 1)
            avg_latencies[p] = total / n if n else 0.0
        return {
            "total_requests": _total_requests,
            "path_counts": dict(_path_counts),
            "avg_latency_ms": avg_latencies,
            "status_counts": dict(_status_counts),
            "path_status_counts": {p: dict(sc) for p, sc in _path_status_counts.items()},
        }


class LatencyTimer:
    def __init__(self):
        self.start = time.perf_counter()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self.start) * 1000.0

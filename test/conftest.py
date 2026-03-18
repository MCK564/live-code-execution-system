import sys
from pathlib import Path
import types


APP_PATH = Path(__file__).resolve().parents[1] / "app"
if str(APP_PATH) not in sys.path:
    sys.path.insert(0, str(APP_PATH))


# Test-only shim to avoid platform-specific rq import issues on Windows.
rq_stub = types.ModuleType("rq")


class _Queue:
    def __init__(self, *_args, **_kwargs):
        self.count = 0

    def enqueue(self, *_args, **_kwargs):
        return None


class _Retry:
    def __init__(self, max=None, interval=None):
        self.max = max
        self.interval = interval


rq_stub.Queue = _Queue
rq_stub.Retry = _Retry
rq_stub.Worker = object
sys.modules["rq"] = rq_stub

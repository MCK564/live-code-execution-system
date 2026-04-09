import sys
from pathlib import Path
import types
import os


APP_PATH = Path(__file__).resolve().parents[1] / "app"
if str(APP_PATH) not in sys.path:
    sys.path.insert(0, str(APP_PATH))


os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-secret-key-should-be-at-least-thirty-two-bytes",
)
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_TTL_SECONDS", "900")
os.environ.setdefault("JWT_REFRESH_TTL_SECONDS", "2592000")
os.environ.setdefault("JWT_STATE_TTL_SECONDS", "300")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-google-client-secret")
os.environ.setdefault(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:8001/auth/oauth2/google/callback",
)
os.environ.setdefault(
    "AUTH_FRONTEND_SUCCESS_REDIRECT_URI",
    "http://localhost:3000/login/success",
)
os.environ.setdefault(
    "AUTH_REDIRECT_ALLOWLIST",
    "http://localhost:3000/login/success,http://localhost:5173/login/success",
)
os.environ.setdefault(
    "BACKEND_CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173",
)
os.environ.setdefault("AUTH_USER_CACHE_TTL_SECONDS", "3600")
os.environ.setdefault("AUTH_COOKIE_SECURE", "false")


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

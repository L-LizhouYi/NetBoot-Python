import logging
import traceback
from functools import wraps

def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="[%(asctime)s] [%(levelname)s] %(message)s",
    )

def safe_run(fn):
    """Decorator to trap and log all exceptions inside thread targets."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            logging.error("Unhandled error in %s: %s", fn.__name__, e)
            traceback.print_exc()
    return wrapper

import contextvars
import logging
import uuid

request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
github_delivery_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "github_delivery", default=None
)


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get() or "-"
        gh = github_delivery_ctx.get()
        record.github_delivery = gh if gh else "-"
        return True


def setup_slope_logging(level: int = logging.INFO) -> None:
    log = logging.getLogger("slope")
    log.setLevel(level)
    if log.handlers:
        return
    handler = logging.StreamHandler()
    handler.addFilter(RequestContextFilter())
    handler.setFormatter(
        logging.Formatter(
            "%(levelname)s [%(request_id)s] [gh:%(github_delivery)s] %(name)s: %(message)s"
        )
    )
    log.addHandler(handler)
    log.propagate = False


def new_request_id() -> str:
    return str(uuid.uuid4())

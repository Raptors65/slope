from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.logging_config import (
    github_delivery_ctx,
    new_request_id,
    request_id_ctx,
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Binds request id (and optional GitHub delivery id) for logging; echoes X-Request-ID on responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        header_rid = request.headers.get("x-request-id")
        request_id = header_rid.strip() if header_rid else new_request_id()
        github_delivery = request.headers.get("x-github-delivery")

        request.state.request_id = request_id
        if github_delivery:
            request.state.github_delivery = github_delivery

        rid_token = request_id_ctx.set(request_id)
        gh_token = github_delivery_ctx.set(github_delivery)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(rid_token)
            github_delivery_ctx.reset(gh_token)

        response.headers["X-Request-ID"] = request_id
        return response

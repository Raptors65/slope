from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.config import get_settings
from app.logging_config import setup_slope_logging
from app.middleware import RequestContextMiddleware


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_slope_logging()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title="slope", lifespan=lifespan)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestContextMiddleware)

    application.include_router(health_router)

    return application


app = create_app()

import logging
from pathlib import Path, PurePosixPath

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.types import Scope

from common.config import settings
from features.exercise.router import router as exercise_router
from features.rest_timer.router import router as rest_timer_router
from features.training_log.router import router as training_log_router

logger = logging.getLogger(__name__)


class SpaStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as e:
            is_api = path == "api" or path.startswith("api/")
            if e.status_code != 404 or is_api or PurePosixPath(path).suffix:
                raise
            return FileResponse(Path(str(self.directory)) / "index.html")


def create_app(*, frontend_dist_dir: Path | None) -> FastAPI:
    serves_frontend = frontend_dist_dir is not None
    app = FastAPI(
        docs_url=None if serves_frontend else "/docs",
        redoc_url=None if serves_frontend else "/redoc",
        openapi_url=None if serves_frontend else "/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s %s — %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "サーバーエラーが発生しました。"},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        # inf や nan を含む input と ctx は JSON にできないため、本文から除く
        errors = [{k: v for k, v in error.items() if k not in ("input", "ctx")} for error in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})

    app.include_router(exercise_router)
    app.include_router(training_log_router)
    app.include_router(rest_timer_router)

    # "/" の mount は全パスに一致するため、ルーターの登録はこの前に置く
    if frontend_dist_dir is not None:
        app.mount("/", SpaStaticFiles(directory=frontend_dist_dir, html=True))
    return app


app = create_app(frontend_dist_dir=settings.frontend_dist_dir)

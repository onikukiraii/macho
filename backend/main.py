import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.types import Scope

from common.config import settings

logger = logging.getLogger(__name__)


class SpaStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as e:
            if e.status_code != 404 or path.startswith("api/"):
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

    # "/" の mount は全パスに一致するため、ルーターの登録はこの前に置く
    if frontend_dist_dir is not None:
        app.mount("/", SpaStaticFiles(directory=frontend_dist_dir, html=True))
    return app


app = create_app(frontend_dist_dir=settings.frontend_dist_dir)

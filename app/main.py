from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from core.config import settings
from core.logging_config import setup_logging
from core.database import Base,engine
from api import analyzer as analyzer_api, auth as auth_api, code_session as code_session_api, execution as execution_api, users as users_api
from handlers import exception_handler
from models import code_session, executions, user
from services.redis_service import close_redis_client


app = FastAPI(title="Live Code Execution System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


# Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


app.include_router(code_session_api.router)
app.include_router(execution_api.router)
app.include_router(analyzer_api.router)
app.include_router(auth_api.router)
app.include_router(users_api.router)





setup_logging()
exception_handler.register_not_found_exception_handler(app)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await close_redis_client()

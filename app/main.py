from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.middleware.cors import CORSMiddleware

from core.logging_config import setup_logging
from core.database import Base,engine,get_db
from api import analyzer as analyzer_api, code_session as code_session_api, execution as execution_api
from handlers import exception_handler
from models import code_session, executions


app = FastAPI(title="Live Code Execution System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


app.include_router(code_session_api.router)
app.include_router(execution_api.router)
app.include_router(analyzer_api.router)





setup_logging()
exception_handler.register_not_found_exception_handler(app)

from fastapi import FastAPI
from core.database import Base,engine,get_db
from api import code_session as code_session_api, execution as execution_api
from handlers import exception_handler
from models import code_session, executions


app = FastAPI(title="Live Code Execution System")

Base.metadata.create_all(bind=engine)


app.include_router(code_session_api.router)
app.include_router(execution_api.router)


exception_handler.register_not_found_exception_handler(app)
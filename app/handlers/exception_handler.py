from starlette.responses import JSONResponse
from exceptions.DataNotFoundException import DataNotFoundException



def register_not_found_exception_handler(app):
    @app.exception_handler(DataNotFoundException)
    async def not_found_handler(request, exc: DataNotFoundException):
        return JSONResponse(
            status_code=404,
            content={
                "message": exc.message
            }
        )
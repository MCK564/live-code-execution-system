from starlette.responses import JSONResponse


class DataNotFoundException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
from fastapi import HTTPException

class ArenaError(ValueError):
    """A user-facing error: English text plus a stable code the UI translates."""
    def __init__(self, code: str, message: str, **params):
        super().__init__(message)
        self.code, self.params = code, params

class ArenaHTTPError(HTTPException):
    def __init__(self, status: int, code: str, message: str, **params):
        super().__init__(status, message)
        self.code, self.params = code, params

def body(message: str, code: str | None = None, params: dict | None = None) -> dict:
    out = {"detail": message}
    if code: out |= {"code": code, "params": params or {}}
    return out

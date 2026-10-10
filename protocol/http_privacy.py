"""Content-free HTTP errors and non-cacheable responses for selected services."""
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse


class PrivateResponses:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        started = False

        async def private_send(message):
            nonlocal started
            if message['type'] == 'http.response.start':
                started = True
                headers = [(k, v) for k, v in message.get('headers', [])
                           if k.lower() not in (b'cache-control', b'x-content-type-options')]
                message = {**message, 'headers': headers + [
                    (b'cache-control', b'no-store'),
                    (b'x-content-type-options', b'nosniff')]}
            await send(message)

        try:
            await self.app(scope, receive, private_send)
        except Exception:
            if started:
                raise
            # Exception strings can contain bodies, URLs or credentials. Never
            # reflect or log them; cancellation (BaseException) is not caught.
            await JSONResponse({'detail': 'The service could not complete the request'},
                               status_code=500)(scope, receive, private_send)


def install(app):
    async def validation_error(request, error):
        # Pydantic errors include input values and user-supplied field names.
        return JSONResponse({'detail': 'Request does not match the supported input contract'},
                            status_code=422)

    app.add_exception_handler(RequestValidationError, validation_error)
    # Install after body-limit middleware so its 413 responses are covered.
    app.add_middleware(PrivateResponses)


def application():
    """Uvicorn factory; wrap the service without changing detector identity."""
    from app import app
    install(app)
    return app

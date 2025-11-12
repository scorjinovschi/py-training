from litestar import Litestar, Request, Response
from litestar.openapi import OpenAPIConfig
from routes import chat_router, search_router
from src import Logger, Config
import uvicorn
import asyncio
from routes.utils import CORSHeadersGenerator


class WebApp:
    def __init__(self):
        # get config and logger instances
        self.config = Config()
        self.logger = Logger()

        # Configure OpenAPI
        self.openapi_config = OpenAPIConfig(
            title='py-training',
            version='1.0.0',
            description='An API for py-training chat and search functionalities.',
        )

        self.app = Litestar(
            route_handlers=[chat_router, search_router],
            openapi_config=self.openapi_config,
            debug=self.config.get('debug'),
            exception_handlers={Exception: self._runtime_exception_handler},
            cors_config=CORSHeadersGenerator.generate_cors_headers()
        )

        self.logger.log('remote_methods', 'warning',
                        f'API initialized with debug set to {self.config.get("debug")}')

        self.shutdown_event = asyncio.Event()

    async def run(self, host='127.0.0.1', port=8000):
        config = uvicorn.Config(self.app, host=host, port=port)
        self.server = uvicorn.Server(config)

        server_task = asyncio.create_task(self.server.serve())

        while not self.server.should_exit:
            await asyncio.sleep(0.1)

        await server_task
        self.shutdown_event.set()

    async def stop(self):
        self.server.should_exit = True
        await self.shutdown_event.wait()
        self.logger.log('remote_methods', 'warning',
                        'Web API stopped on request')

    async def _runtime_exception_handler(self, request: Request, exc: Exception) -> Response:
        self.logger.log('remote_methods', 'error',
                        'An unexpected error occurred', exc_info=True)

        http_error = self.config.get('http_codes').get('internal_server_error')
        code = http_error['code']
        message = http_error['message']
        return Response(content={'error': message}, status_code=code)

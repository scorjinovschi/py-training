from litestar import Router, get, HttpMethod, route, Response
from .utils import ResponseFormatter
import json
from src.connectors import OpenAIConnector, ChromaDBConnection, chroma_connection_factory, openai_connection_factory
from litestar.di import Provide
from src import Logger


class SearchRoutes:

    @staticmethod
    @get(path='/',
         dependencies={
             'chroma_connection': Provide(chroma_connection_factory),
             'openai_connection': Provide(openai_connection_factory)
         })
    async def search(q: str, chroma_connection: ChromaDBConnection, openai_connection: OpenAIConnector) -> dict:
        '''Endpoint to perform a search with a mandatory query parameter.'''
        logger = Logger()
        try:
            embeddings = openai_connection.get_embeddings(q)
            results = chroma_connection.query_by_embedding(embeddings)
            chroma_connection.release()
            logger.log('remote_methods', 'debug',
                       f'Results for {q} search: {results}')
            response = ResponseFormatter.generate_response(
                data=results['metadatas'][0], errors=[], status_code=200)
        except Exception as e:
            logger.log('remote_methods', 'error',
                       f'Error during search: {e}', exc_info=True)
            error_message = str(e)
            response = ResponseFormatter.generate_response(
                data=[], errors=[{'error': error_message}], status_code=500)

        return json.dumps(response)

    @staticmethod
    @route(path='/', http_method=HttpMethod.OPTIONS)
    async def options_search() -> dict:
        '''OPTIONS method to describe the /search endpoint.'''
        headers = {
            'Allow': 'GET, OPTIONS',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        }
        return Response(status_code=204, headers=headers)


search_router = Router(
    path='/search',
    route_handlers=[SearchRoutes.search, SearchRoutes.options_search]
)

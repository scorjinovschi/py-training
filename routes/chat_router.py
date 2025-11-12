from litestar import Router, get, HttpMethod, route, Response
from litestar.response import ServerSentEvent
from litestar.di import Provide
import asyncio
from src.connectors import OpenAIConnector, ChromaDBConnection, chroma_connection_factory, openai_connection_factory
from src import Logger
from .utils import ResponseFormatter
import json


class ChatRoutes:

    @staticmethod
    def format_metadata_for_context(metadata_list):
        '''
        Format metadata into a list of strings for use as context in OpenAI chat.

        Args:
            metadata_list (list): A list of metadata dictionaries.

        Returns:
            list: A list of formatted strings.
        '''
        formatted_context = []

        for metadata in metadata_list:
            # Extract metadata fields with default values if they are missing
            title = metadata.get('Title', 'Unknown Title')
            imdb_rating = metadata.get('IMDb Rating', 'N/A')
            year = metadata.get('Year', 'Unknown Year')
            url = metadata.get('URL', 'No URL')

            # Format the metadata into a string
            formatted_string = f'Title: {title}, IMDb Rating: {imdb_rating}, Year: {year}, URL: {url}'
            formatted_context.append(formatted_string)

        return formatted_context

    @staticmethod
    async def handle_message(query: str, chroma_connection: ChromaDBConnection, openai_connection: OpenAIConnector):
        '''
        Handle an incoming chat message asynchronously and stream responses.

        Args:
        query: The user's input message to process.
        chroma_connection: An active ChromaDBConnection instance for embedding queries.
        openai_connection: An OpenAIConnector instance for generating embeddings and chat completions.

        Yields:
        JSON-formatted strings representing the response, streamed as they become available.

        Raises:
        Any exceptions raised during embedding retrieval, database querying, or chat completion are propagated.
        '''
        message_queue = asyncio.Queue()
        stop_event = asyncio.Event()
        logger = Logger()

        try:
            def chat_callback(message: str, is_done: bool = False, is_error: bool = False):
                asyncio.create_task(message_queue.put(
                    (message, is_done, is_error)))

            embeddings = openai_connection.get_embeddings(query)
            results = chroma_connection.query_by_embedding(embeddings)
            chroma_connection.release()
            context_list = ChatRoutes.format_metadata_for_context(
                results['metadatas'][0])

            openai_connection.chat(query, context_list,
                                   chat_callback, stop_event)

            while True:
                message, is_done, is_error = await message_queue.get()
                response = ResponseFormatter.generate_response(
                    data=[message] if not is_error else [],
                    errors=[message] if is_error else [],
                    status_code=200 if not is_error else 500
                )
                yield f'{json.dumps(response)}'

                if is_done or is_error:
                    break

        except Exception as e:
            logger.log('remote_methods', 'error',
                       f'Failed to process message: {e}', exc_info=True)
            stop_event.set()
            response = ResponseFormatter.generate_response(
                data=[],
                errors=[str(e)],
                status_code=500
            )
            yield f'{json.dumps(response)}'

    @staticmethod
    @get(path='/', dependencies={
        'chroma_connection': Provide(chroma_connection_factory),
        'openai_connection': Provide(openai_connection_factory)
    })
    async def chat(q: str, chroma_connection: ChromaDBConnection,
                   openai_connection: OpenAIConnector) -> ServerSentEvent:
        '''SSE endpoint to stream events with a query parameter.'''
        return ServerSentEvent(content=ChatRoutes.handle_message(q, chroma_connection, openai_connection),
                               event_type='response',
                               retry_duration=1000)

    @staticmethod
    @route(path='/', http_method=HttpMethod.OPTIONS)
    async def options_chat() -> dict:
        '''OPTIONS method to describe the /chat endpoint.'''
        headers = {
            'Allow': 'GET, OPTIONS',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        }
        return Response(status_code=204, headers=headers)


chat_router = Router(
    path='/chat',
    route_handlers=[ChatRoutes.chat, ChatRoutes.options_chat]
)

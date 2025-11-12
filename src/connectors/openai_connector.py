import openai
from .. import Config, Logger
from typing import List, Dict, Callable
import asyncio
import random


class OpenAIConnector:
    """
    Provide an interface for interacting with the OpenAI API for embeddings and chat functionality.

    This connector handles authentication, logging, and communication with OpenAI's embedding and chat models.
    It supports streaming chat responses and error logging.

    Methods:
    get_embeddings(input_text): Retrieve embeddings for the given input text using
    the configured OpenAI embedding model.
    chat(question, context, callback): Initiate a chat session with the OpenAI chat model,
    streaming responses and invoking a callback for each content chunk.
    _get_chat_messages(question, context): Construct the message payload for the chat API
    based on the question and optional context.

    Attributes:
    config: Configuration object for accessing API keys and model names.
    logger: Logger instance for error and event logging.
    """

    def __init__(self):
        self.config = Config()
        self.logger = Logger()
        # redundant since the env is loaded but to keep a "way"
        openai.api_key = self.config.get('openai.api_key')

    def _generate_random_embedding(self, size: int = 512) -> List[float]:
        """Generate a random embedding of a given size."""
        return [random.uniform(-1, 1) for _ in range(size)]

    def get_embeddings(self, input_text: str) -> List[float]:
        return self._generate_random_embedding(size=1536)
        try:
            response = openai.embeddings.create(
                input=input_text, model=self.config.get('openai.embed_model'))
            return response['data'][0]['embedding']
        except Exception as e:
            self.logger.log(module_key='openai_connector', level='error',
                            message=f'Error getting embeddings: {e}')
            return []

    def chat(self, question: str, context: List[str], callback: Callable[[str, bool, bool], None],
             stop_event: asyncio.Event):
        try:
            messages = self._get_chat_messages(question, context)
            self.logger.log('openai_connector', 'debug', f'Messages for chat: {messages}')

            # Use the stream=True parameter to get a streaming response
            response_stream = openai.responses.create(
                model=self.config.get('openai.chat_model'), input=messages, stream=True
            )

            # Iterate over the events in the stream
            for event in response_stream:
                if stop_event.is_set():
                    callback('Interaction interrupted by user.', is_done=True)
                    break

                self.logger.log('openai_connector', 'debug', event)
                if (event.type == 'response.output_text.delta'):
                    callback(event.delta)
                elif (event.type == 'response.completed'):
                    callback('', is_done=True)
                    break
                elif (event.type == 'error'):
                    callback('Unable to communicate with openai', is_error=True)
                    break

        except Exception as e:
            self.logger.log(module_key='openai_connector', level='error',
                            message=f'Error during chat: {e}')
            callback('Unable to communicate with openai', is_error=True)

    def _get_chat_messages(self, question: str, context: List[str] = None) -> List[Dict[str, str]]:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question},
        ]
        if (context):
            for c in context:
                messages.append({"role": "assistant", "content": c})
        return messages


async def openai_connection_factory() -> OpenAIConnector:
    return OpenAIConnector()

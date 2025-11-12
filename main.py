import asyncio
from dotenv import load_dotenv
import os
import argparse
import json
from src import Config, Logger, TelnetConsole
from web_app import WebApp
from src.connectors import ChromaConnector
import signal

ARG_PROD_ENV = 'prod'
ARG_DEV_ENV = 'dev'

web_app = None
logger = None
app_console = None
db_connector = None
openai_connector = None
telnet_console = None


def load_environment(env):
    if env == ARG_PROD_ENV:
        load_dotenv('.env.prod')
    else:
        load_dotenv('.env.dev')


async def main(env):
    global logger, web_app, db_connector, openai_connector, telnet_console

    load_environment(env)

    # Initialize the configuration singleton
    conf_dict = {
        'debug': os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
    }

    conf_dict['data_ingester'] = {
        'csv_folder_path': os.path.normpath(os.path.join(
            os.path.dirname(__file__),
            os.getenv('CSV_PATH', './input')))
    }

    # Load logger config
    conf_dict['logging'] = {
        'config_path': os.path.normpath(os.path.join(
            os.path.dirname(__file__), 'src',
            'config',  os.getenv('LOGGING_CONFIG', 'logging.json')))
    }
    with open(conf_dict['logging']['config_path'], 'r',
              encoding='utf-8') as file:
        conf_dict['logging']['config'] = json.load(file)

    # Load the routes part
    conf_dict['routes'] = {}
    http_codes_path = os.path.normpath(os.path.join(
        os.path.dirname(__file__), 'src',
        'config', 'http_codes.json'))
    with open(http_codes_path, 'r', encoding='utf-8') as file:
        conf_dict['routes']['http_codes'] = json.load(file)

    # Load OpenAI related parts
    conf_dict['openai'] = {
        'api_key': os.getenv('OPENAI_API_KEY'),
        'embed_model': os.getenv('OPENAI_EMBEDDING_MODEL',
                                 'text-embedding-3-small'),
        'chat_model': os.getenv('OPENAI_CHAT_MODEL', 'gpt-4o-mini')
    }

    # Load ChromaDB related parts
    conf_dict['chromadb'] = {
        'persist_directory': os.getenv('CHROMA_DB_PATH', 'db'),
        'collection_name': os.getenv('CHROMA_DB_COLLECTION_NAME',
                                     'py_movies'),
        'connection_pool_max': int(os.getenv('CHROMA_DB_CONNECTION_POOL_MAX',
                                             10))
    }

    config_instance = Config()
    config_instance.initialize(conf_dict)

    # Initialize the logger
    logger = Logger()

    # initialize ChromaDB connector
    db_connector = ChromaConnector()

    telnet_console = TelnetConsole()
    asyncio.create_task(telnet_console.start())

    # Start the API
    web_app = WebApp()
    await web_app.run()  # Await the coroutine


async def handle_shutdown():
    logger.log(module_key='__main__',
               level='warning',
               message='Process shutting down due to signal.')
    if web_app:
        await web_app.stop()
    if db_connector:
        db_connector.close_all()
    if telnet_console:
        await telnet_console.stop()
    logger.log(module_key='__main__', level='warning',
               message='Resources freed')


def signal_handler(sig, frame):
    asyncio.create_task(handle_shutdown())


if __name__ == '__main__':
    # Make sure that resources are released
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser(description='Accepted params')
    parser.add_argument('--env', type=str,
                        help='Specify the environment : prod or dev (default)')

    args = parser.parse_args()
    env = args.env if args.env else ARG_DEV_ENV

    asyncio.run(main(env))

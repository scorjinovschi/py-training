import telnetlib3
from .config import Config
from .logger import Logger
from .utils.data_ingester import DataIngester
import asyncio


class TelnetConsole:
    def __init__(self, host='127.0.0.1', port=8023):
        self.host = host
        self.port = port
        self.server = None
        self.clients = set()
        self.config = Config()
        self.logger = Logger()

    async def shell(self, reader, writer):
        self.clients.add(writer)
        try:
            writer.write('Welcome to the Telnet console!\n')
            while True:
                writer.write('Enter command: ')
                command = await reader.readline()
                command = command.strip()

                if command.lower() == 'exit':
                    writer.write('Goodbye!\n')
                    break
                elif command.lower() == 'run ingest':
                    await self.run_ingest_script(reader, writer)
                else:
                    writer.write(f'Unknown command: {command.lower()}\n')
        finally:
            self.clients.remove(writer)
            writer.close()
            await writer.wait_closed()

    async def run_ingest_script(self, reader, writer):
        try:
            writer.write('Running ingest script... Type "cancel" to stop.\n')
            self.logger.log('ingest_console', 'warning',
                            'Running ingest script via Telnet console.')

            # Create a task for the ingest process
            data_ingester = DataIngester()
            ingest_task = asyncio.create_task(data_ingester.ingest())

            while not ingest_task.done():
                writer.write('Enter command: ')
                command = await reader.readline()
                command = command.strip()

                if command.lower() == 'cancel':
                    data_ingester.stop_ingestion()
                    ingest_task.cancel()
                    writer.write('Ingest script canceled.\n')
                    self.logger.log('ingest_console', 'warning',
                                    'Ingest script canceled by user.')
                    return

            # Await the task to handle any exceptions
            result = await ingest_task
            writer.write(f'Ingest script completed: {result}\n')
        except asyncio.CancelledError:
            writer.write('Ingest script was canceled.\n')
        except Exception as e:
            self.logger.log('ingest_console', 'error',
                            f'Error running ingest script: {e}')
            writer.write('Error running ingest script.\n')
            return

    async def start(self):
        self.server = await telnetlib3.create_server(
            host=self.host,
            port=self.port,
            shell=self.shell
        )
        self.logger.log('ingest_console', 'warning',
                        f'Telnet server listening on {self.host}:{self.port}')
        await self.server.serve_forever()

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.logger.log('ingest_console', 'warning',
                            'Server has been shut down.')

        # Close all client connections
        for writer in self.clients:
            writer.write('Server is shutting down.')
            writer.close()
            await writer.wait_closed()
        self.clients.clear()
        self.logger.log('ingest_console', 'warning',
                        'All client connections have been closed.')

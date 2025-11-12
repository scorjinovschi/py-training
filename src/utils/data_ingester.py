import csv
import os
from ..connectors import openai_connection_factory, chroma_connection_factory, OpenAIConnector, ChromaDBConnection
from .. import Config, Logger
from typing import List


class DataIngester:
    """
    Provide functionality for ingesting CSV data, processing records, generating embeddings, and upserting data into
    a ChromaDB collection.

    This class handles reading CSV files, validating and parsing records, obtaining embeddings using an OpenAI
    connector, batching and upserting data into a ChromaDB collection, and logging progress or errors.
    It also supports stopping the ingestion process and can process multiple CSV files from a configured directory.

    Attributes:
    config: The configuration object for accessing settings.
    logger: The logger instance for logging messages.
    stop_event: Boolean flag to indicate if ingestion should stop.
    semaphore: The maximum number of concurrent tasks (not used in synchronous version).

    Methods:
    parse_csv(file_path): Parse a CSV file and return a list of valid records as dictionaries.
    process_file(file_path): Process a CSV file, generate embeddings, and upsert data into ChromaDB in batches.
    upsert_batch(ids, embeddings, metadatas): Upsert a batch of embeddings and metadata into ChromaDB.
    ingest(): Asynchronously ingest all CSV files in the configured folder and return a list of results.
    stop_ingestion(): Set the stop event to halt the ingestion process.
    _is_record_valid(record): Validate a record's required fields and value ranges.
    """

    def __init__(self):
        self.config = Config()
        self.logger = Logger()
        self.stop_event = False  # Use a simple boolean for stopping
        # Limit to 10 concurrent tasks (not used in sync version)
        self.semaphore = 10

    def parse_csv(self, file_path: str) -> List[dict]:
        records = []
        self.logger.log('ingest_console', 'debug',
                        f'Reading file: {file_path}')
        with open(file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if self.stop_event:
                    self.logger.log('ingest_console', 'info',
                                    'Ingestion stopped.')
                    break
                try:
                    record = {
                        'Const': row['Const'],
                        'Year': int(row['Year']),
                        'IMDb Rating': float(row['IMDb Rating']),
                        'URL': row['URL'],
                        'Title': row['Title']
                    }
                    if self._is_record_valid(record):
                        records.append(record)
                except ValueError as e:
                    self.logger.error(f"Error parsing row {row}: {e}")
        return records

    def process_file(self, file_path: str) -> dict:
        try:
            if not self.chroma_connection or not self.chroma_connection.collection:
                self.logger.log('ingest_console', 'error',
                                'ChromaDB connection or collection is not initialized.')
                return {
                    'total_rows_read': 0,
                    'total_rows_added': 0,
                    'error': 'ChromaDB connection or collection is not initialized.'
                }

            records = self.parse_csv(file_path)  # Synchronous call

            batch_size = 100
            ids_batch = []
            embeddings_batch = []
            metadatas_batch = []

            for record in records:
                if self.stop_event:
                    self.logger.log('ingest_console', 'info',
                                    'Ingestion stopped.')
                    break

                text = f"{record['Title']}"
                embedding = self.openai_connection.get_embeddings(
                    input_text=text)

                if embedding:
                    if record['Const'] in ids_batch:
                        self.logger.log('ingest_console', 'warning',
                                        f"Duplicate ID found: {record['Const']}.")
                        continue

                    ids_batch.append(record['Const'])
                    embeddings_batch.append(embedding)
                    metadatas_batch.append({
                        'Year': record['Year'],
                        'IMDb Rating': record['IMDb Rating'],
                        'URL': record['URL'],
                        'Title': record['Title']
                    })

                    # If batch size is reached, upsert the batch
                    if len(ids_batch) == batch_size:
                        self.upsert_batch(
                            ids_batch, embeddings_batch, metadatas_batch)
                        ids_batch, embeddings_batch, metadatas_batch = [], [], []

                else:
                    self.logger.log(
                        'ingest_console', 'error', f"Unable to get embedding for {record['Title']}.")

            # Upsert any remaining records that didn't fill a complete batch
            if ids_batch:
                self.upsert_batch(ids_batch, embeddings_batch, metadatas_batch)

            self.chroma_connection.release()

            return {
                'total_rows_read': len(records),
                'total_rows_added': len(ids_batch)
            }
        except Exception as e:
            self.logger.log('ingest_console', 'error',
                            f'Error processing file {file_path}: {e}', exc_info=True)
            return {
                'total_rows_read': 0,
                'total_rows_added': 0,
                'error': str(e)
            }

    def upsert_batch(self, ids, embeddings, metadatas):
        if self.chroma_connection:
            self.logger.log('ingest_console', 'error', 'connection is true')
        self.chroma_connection.upsert_embeddings(ids, embeddings, metadatas)
        self.logger.log('ingest_console', 'debug',
                        f"Upsert-ed batch of {len(ids)} records into ChromaDB.")

    async def ingest(self) -> List[dict]:
        try:
            self.chroma_connection: ChromaDBConnection = await chroma_connection_factory()
            self.openai_connection: OpenAIConnector = await openai_connection_factory()
            results = []
            for file_name in os.listdir(self.config.get('data_ingester.csv_folder_path')):
                if file_name.endswith('.csv'):
                    file_path = os.path.join(self.config.get('data_ingester.csv_folder_path'), file_name)
                    self.logger.log('ingest_console', 'info', f'Processing file: {file_path}')
                    result = self.process_file(file_path)
                    self.logger.log('ingest_console', 'debug', f'Finished: {file_path} with result: {result}')
                    results.append(result)
            return results
        except Exception as e:
            self.logger.log('ingest_console', 'error', f'Error during ingestion: {e}', exc_info=True)
            return []

    def stop_ingestion(self):
        self.stop_event = True

    def _is_record_valid(self, record: dict) -> bool:
        if not record['Title'] or not record['URL'] or not record['Const']:
            return False
        if not record['Year'] or record['Year'] < 1000:
            return False
        if not record['IMDb Rating'] or record['IMDb Rating'] < 0 or record['IMDb Rating'] > 10:
            return False
        return True

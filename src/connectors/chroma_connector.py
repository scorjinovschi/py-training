import queue
import threading
from chromadb import PersistentClient
from chromadb.config import Settings
from .. import Config, Logger


class ChromaDBConnection:
    """
    Manage a connection to a ChromaDB collection, providing methods for connecting, disconnecting, upserting embeddings,
    and querying by embedding.

    This class handles the lifecycle of a ChromaDB client, including establishing a connection, managing collections,
    and performing upsert and query operations on embeddings. It also supports logging
    and optional resource release callbacks.

    Attributes:
    logger: Logger instance for logging connection and operation events.
    config: Configuration object for retrieving ChromaDB settings.
    index: Unique identifier for the connection instance.
    collection: The ChromaDB collection object.
    collection_name: Name of the ChromaDB collection.
    on_free_callback: Optional callback to be called when the connection is released.

    Methods:
    connect():
    Establish a connection to the ChromaDB client and retrieve or create the collection.
    _disconnect():
    Disconnect from the ChromaDB client and clean up resources.
    release():
    Invoke the on_free_callback if provided to release the connection.
    upsert_embeddings(ids, embeddings, metadatas):
    Upsert embeddings and their metadata into the collection.
    query_by_embedding(embedding, top_k=10):
    Query the collection for the top_k most similar embeddings.

    Raises:
    Exception: If connection or collection creation fails.
    """

    def __init__(self, index, on_free_callback=None):
        self.logger = Logger()
        self.config = Config()
        self.index = index
        self.collection = None
        self.collection_name = self.config.get('chromadb.collection_name')
        self.on_free_callback = on_free_callback
        self.connect()

    def connect(self):
        if self.collection:
            return self.collection

        # set cache limit to 1GB
        settings = Settings(chroma_segment_cache_policy='LRU',
                            chroma_memory_limit_bytes=1073741824)
        try:
            self.client = PersistentClient(settings=settings,
                                           path=self.config.get('chromadb.persist_directory'))
            self.logger.log('db_connector', 'info',
                            f'ChromaDB client with ID {self.index} connected')
        except Exception as e:
            self.logger.log('db_connector', 'error',
                            f'Client {self.index} failed to connect to ChromaDB: {e}',
                            exc_info=True)
            raise e

        try:
            self.collection = self.client.get_or_create_collection(
                self.collection_name)
            return self.collection
        except Exception as e:
            self.logger.log('db_connector', 'error',
                            f'Client {self.index} failed to get or create the collection: {e}',
                            exc_info=True)
            raise e

    def _disconnect(self):
        if self.client:
            try:
                self.collection = None
                self.client = None
                self.logger.log('db_connector', 'info',
                                f'ChromaDB client with ID {self.index} disconnected')
            except Exception as e:
                self.logger.log('db_connector', 'error',
                                f'Client {self.index} failed to disconnect from ChromaDB: {e}',
                                exc_info=True)

    def release(self):
        if self.on_free_callback:
            self.on_free_callback(self)

    def upsert_embeddings(self, ids, embeddings, metadatas):
        if not self.collection:
            self.logger.log('db_connector', 'error',
                            'No collection available for upsert.')
            return

        try:
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas
            )
            self.logger.log('db_connector', 'debug',
                            f"Upsert-ed {len(ids)} embeddings into the collection.")
        except Exception as e:
            self.logger.log('db_connector', 'error',
                            f"Failed to upsert embeddings: {e}", exc_info=True)
            raise e

    def query_by_embedding(self, embedding, top_k=10):
        try:
            results = self.collection.query(
                query_embeddings=embedding,
                n_results=top_k
            )
            self.logger.log('db_connector', 'debug',
                            f"Queried collection with embedding, returning {len(results)} results.")
            return results
        except Exception as e:
            self.logger.log('db_connector', 'error',
                            f"Failed to query by embedding: {e}", exc_info=True)
            raise e


class ChromaConnector:
    """
    Manage a thread-safe singleton connection pool for ChromaDB connections.

    This class implements a singleton pattern to ensure only one instance manages the connection pool.
    It provides methods to acquire and release connections, as well as to close all connections gracefully.
    Thread safety is ensured using locks and events.

    Attributes:
    _instance: The singleton instance of the class.
    _instance_lock: A lock to synchronize singleton creation.
    _pool: A queue holding available ChromaDBConnection objects.
    _lock: A lock to synchronize pool operations.
    _close_event: An event to signal when the pool is closing.

    Methods:
    acquire(): Acquire a connection from the pool, or return None if closing.
    release(connection): Release a connection back to the pool and log the action.
    close_all(): Close all connections in the pool and log the closure.
    """
    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._instance_lock:
                if not cls._instance:
                    cls._instance = super(ChromaConnector, cls).__new__(cls)
        return cls._instance

    def __init__(self, pool_size=5):
        if not hasattr(self, '_initialized'):
            self._pool = queue.Queue(pool_size)
            self._lock = threading.Lock()
            self._close_event = threading.Event()  # Event to signal closing
            self._initialize_pool(pool_size)
            self._initialized = True
            self.logger = Logger()

    def _initialize_pool(self, pool_size):
        for i in range(pool_size):
            connection = ChromaDBConnection(
                index=i, on_free_callback=self.release)
            self._pool.put(connection)

    def acquire(self):
        if self._close_event.is_set():
            return
        return self._pool.get()

    def release(self, connection):
        with self._lock:
            self._pool.put(connection)
            self.logger.log('db_connector', 'info',
                            f'Connection {connection.index} released back to pool')

    def close_all(self):
        self._close_event.set()
        with self._lock:
            while not self._pool.empty():
                connection = self._pool.get()
                connection._disconnect()
            self.logger.log('db_connector', 'info',
                            'All connections have been closed.')


async def chroma_connection_factory() -> ChromaDBConnection:
    """
    Factory function to create a ChromaDBConnection.
    """
    connector = ChromaConnector()
    return connector.acquire()

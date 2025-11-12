import logging
import logging.config
from .config import Config


class Logger:
    '''
    Provide a singleton logger utility for configuring and using
    Python's logging framework.
    Initializes logging configuration from a custom Config object and exposes a
    method to log messages
    at various levels for different modules.

    Attributes:
    _instance: Singleton instance of the Logger class.
    config: Configuration object containing logging settings.

    Methods:
    log(module_key, level, message, exc_info=None): Log a message at the
    specified level for the given module.
    '''
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance.config = Config().get('logging')
            cls._instance._setup_logging(cls._instance.
                                         config.get('config'))
        return cls._instance

    def _setup_logging(self, config: dict) -> None:
        logging.config.dictConfig(config)  # Corrected method name

    def log(self, module_key: str, level: str, message: str,
            exc_info=None) -> None:
        logger = logging.getLogger(module_key)

        log_method = getattr(logger, level.lower(), None)
        if callable(log_method):
            log_method(message, exc_info=exc_info)

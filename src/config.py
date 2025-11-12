from typing import Union, List


class Config:
    '''
    Provide singleton-style access to a configuration object.

    This class ensures only one instance exists and provides methods to
    initialize and access configuration values.

    Attributes:
    _instance: The singleton instance of the class.
    _initialized: Indicates whether the configuration has been initialized.
    config: The configuration object.

    Methods:
    initialize(config): Initialize the singleton with a configuration object.
    get(key): Retrieve a configuration value by keys in an hierarchical view.
    _reset(): Reset the initialization state and configuration. Should be used
    only for testing purposes only.

    Raises:
    Exception: If attempting to access configuration before initialization.
    '''
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def initialize(self, config: dict) -> None:
        if not self._initialized:
            self.config = config
            self._initialized = True

    def get(self, keys: Union[str, List[str]]) -> Union[bool, str, int, float, dict, None]:
        if not self._initialized:
            raise Exception('Config has not been initialized yet.')

        if isinstance(keys, str):
            keys = keys.split('.')

        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value

    def _reset(self) -> None:
        self._initialized = False
        self.config = None

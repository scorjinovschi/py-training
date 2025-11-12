class CORSHeadersGenerator:
    @staticmethod
    def generate_cors_headers(
        allow_origins=None,
        allow_methods=None,
        allow_headers=None,
        allow_credentials=False,
        expose_headers=None,
        max_age=None
    ):
        """
        Generate CORS headers based on the provided configuration.

        :param allow_origins: List of allowed origins.
        :param allow_methods: List of allowed HTTP methods.
        :param allow_headers: List of allowed headers.
        :param allow_credentials: Whether to allow credentials.
        :param expose_headers: List of headers to expose.
        :param max_age: Maximum age for the CORS preflight request.
        :return: Dictionary of CORS headers.
        """
        # Set default values
        if allow_methods is None:
            allow_methods = ["GET", "OPTIONS"]
        if allow_headers is None:
            allow_headers = ["Content-Type", "Authorization"]
        if allow_origins is None:
            allow_origins = ["http://localhost"]
        if expose_headers is None:
            expose_headers = ["X-Custom-Header"]
        if max_age is None:
            max_age = 3600

        headers = {}

        headers["Access-Control-Allow-Origin"] = ", ".join(allow_origins)
        headers["Access-Control-Allow-Methods"] = ", ".join(allow_methods)
        headers["Access-Control-Allow-Headers"] = ", ".join(allow_headers)
        if allow_credentials:
            headers["Access-Control-Allow-Credentials"] = "true"
        headers["Access-Control-Expose-Headers"] = ", ".join(expose_headers)
        headers["Access-Control-Max-Age"] = str(max_age)

        return headers

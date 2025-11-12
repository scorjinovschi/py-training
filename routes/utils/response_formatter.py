class ResponseFormatter:
    @staticmethod
    def generate_response(data=None, errors=None, status_code=200):
        """
        Generate a formatted response.

        Args:
            data (list): The data to include in the response.
            errors (list): The errors to include in the response.
            status_code (int): The HTTP status code for the response.

        Returns:
            dict: A dictionary representing the formatted response.
        """
        if data is None:
            data = []
        if errors is None:
            errors = []

        response = {
            "data": data,
            "errors": errors,
            "meta": {
                "count": len(data),
                "code": status_code
            }
        }
        return response

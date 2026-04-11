class ClientError(Exception):
    """Raised when a downstream call fails (network, 4xx, 5xx)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code

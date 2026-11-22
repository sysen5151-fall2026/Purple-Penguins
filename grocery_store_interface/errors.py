"""Safe errors raised by grocery price providers."""


class GroceryPricingError(RuntimeError):
    """A user-reportable grocery pricing failure without provider details."""

    def __init__(
        self,
        public_message: str,
        *,
        status_code: int,
        log_message: str,
        provider_status_code: int | None = None,
    ) -> None:
        super().__init__(log_message)
        self.public_message = public_message
        self.status_code = status_code
        self.log_message = log_message
        self.provider_status_code = provider_status_code

"""Errors raised while generating recipes through the configured provider."""


class RecipeGenerationServiceError(RuntimeError):
    """A safe, user-reportable recipe-generation failure."""

    def __init__(
        self,
        public_message: str,
        *,
        status_code: int,
        log_message: str,
    ) -> None:
        super().__init__(log_message)
        self.public_message = public_message
        self.status_code = status_code
        self.log_message = log_message

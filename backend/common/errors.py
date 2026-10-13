class AppError(Exception): ...


class NotFound(AppError): ...


class Forbidden(AppError): ...


class BusinessRuleViolation(AppError): ...


class Conflict(AppError): ...


class StorageError(AppError): ...


class RenderError(AppError): ...


class LLMError(AppError):
    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable

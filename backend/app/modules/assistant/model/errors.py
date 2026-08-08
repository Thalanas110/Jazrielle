class ModelNotConfiguredError(RuntimeError):
    """Raised when inference is requested before a model file is configured."""


class ModelRuntimeUnavailableError(RuntimeError):
    """Raised when the configured model runtime is not installed."""

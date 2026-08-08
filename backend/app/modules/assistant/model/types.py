from dataclasses import dataclass


@dataclass(frozen=True)
class ModelStatus:
    configured: bool
    ready: bool

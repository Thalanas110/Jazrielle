from pydantic import BaseModel, Field


class Capability(BaseModel):
    id: str
    label: str
    description: str
    examples: list[str]


class CapabilitiesResponse(BaseModel):
    assistant: str
    localMode: bool
    llmConfigured: bool
    capabilities: list[Capability]


class CommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=500)


class CommandResult(BaseModel):
    message: str
    handled: bool
    app: str | None = None
    launchUrl: str | None = None


class InferenceRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=10_000)
    system: str = Field(default="", max_length=10_000)


class InferenceResult(BaseModel):
    model: str | None = None
    response: str

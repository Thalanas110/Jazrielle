from datetime import datetime

from app.modules.assistant.schemas import Capability, CommandResult


CAPABILITIES = [
    Capability(
        id="calendar",
        label="Open calendar",
        description="Open the local calendar.",
        examples=["open calendar"],
    ),
    Capability(
        id="downloads",
        label="Open downloads",
        description="Open the local downloads folder.",
        examples=["open downloads"],
    ),
    Capability(
        id="time",
        label="Time check",
        description="Read the current local time.",
        examples=["what time is it"],
    ),
]


def get_capabilities() -> list[Capability]:
    return CAPABILITIES.copy()


def execute_command(command: str) -> CommandResult:
    normalized = " ".join(command.strip().lower().split())
    if normalized == "what time is it":
        return CommandResult(message=f"It is {datetime.now().astimezone():%I:%M %p}.", handled=True)
    if normalized == "open calendar":
        return CommandResult(message="Calendar is ready to open.", handled=True, app="Calendar")
    if normalized == "open downloads":
        return CommandResult(message="Downloads is ready to open.", handled=True, app="Downloads")
    return CommandResult(message="I do not have a safe action for that command.", handled=False)

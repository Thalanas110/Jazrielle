from app.core.system_prompt import SystemPromptConfigurationError


def test_system_prompt_configuration_error_is_a_runtime_error():
    assert issubclass(SystemPromptConfigurationError, RuntimeError)

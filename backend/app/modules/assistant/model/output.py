import re


def clean_chat_response(content: str) -> str:
    return re.sub(r"<think>.*?</think>", "", content, flags=re.IGNORECASE | re.DOTALL).strip()

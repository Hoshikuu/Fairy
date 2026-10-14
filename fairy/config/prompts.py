"""Read the assistant prompt without depending on the current directory."""
from .paths import PROMPT_FILE

def system_prompt():
    return PROMPT_FILE.read_text(encoding="utf-8")

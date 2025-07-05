# config/settings.py

import os
from pathlib import Path

# Paths
BASE_DIR     = Path(__file__).parent.parent
PERSONA_YAML = BASE_DIR / "data" / "persona.yaml"
RESUME_PDF   = BASE_DIR / "data" / "resume.pdf"

# OpenAI settings
OPENAI_MODEL       = "gpt-3.5-turbo"
OPENAI_TEMPERATURE = 0.7
OPENAI_MAX_TOKENS  = 500

# Cover-letter style
AI_TONE    = "warm, conversational, and slightly playful"

# Language: "auto", "sv" (Swedish) or "en" (English)
LETTER_LANG = "auto"

# Personal footer details to append to each letter
PERSONAL_WEBSITE = "https://battleprogrammersimon.com/"
GITHUB_URL      = "https://github.com/crtneko97"
BOT_NOTE = (
    "P.S. Apologies for the automated application—"
    "as a developer I thought it would be both fun and fitting to demonstrate my skills. "
    "I truly love coding, though I must admit that job hunting isn’t my favorite part, haha."
)

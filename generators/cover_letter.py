
import os
import openai
from langdetect import detect
from config.settings import (
    AI_TONE, LETTER_LANG,
    OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS,
    PERSONAL_WEBSITE, GITHUB_URL, BOT_NOTE
)

# ensure your OPENAI_API_KEY is in the environment
openai.api_key = os.getenv("OPENAI_API_KEY")

def decide_language(description: str) -> str:
    if LETTER_LANG == "auto":
        code = detect(description)
        return "Swedish" if code.startswith("sv") else "English"
    return "Swedish" if LETTER_LANG == "sv" else "English"

def make_prompt(persona: dict, resume: str, job: dict) -> str:
    lang = decide_language(job["description"])
    print(f"🗣️  Generating a {lang}-language letter in a {AI_TONE} tone")

    # Flatten persona
    ptxt = f"{persona['name']}, {persona['headline']}\n\n"
    ptxt += persona.get("summary", "") + "\n\n"
    ptxt += "Skills: " + ", ".join(persona.get("skills", [])) + "\n\n"

    return f"""\
You are a cover‐letter assistant. Write a {AI_TONE}, {lang}-language cover letter in first person (4 paragraphs),
using the candidate’s background and the job details provided below.

--- Candidate Resume ---
{resume}

--- Candidate Persona ---
{ptxt}

--- Job Opening ---
Title: {job['title']}
Company: {job['company']}
Location: {job['location']}
Description:
{job['description']}
URL: {job['url']}

Begin the letter with “Dear Hiring Team,” and end the main body with your name.
"""

def generate_cover_letter(persona: dict, resume: str, job: dict) -> str:
    """Generate a cover letter and append your personal footer."""
    prompt = make_prompt(persona, resume, job)
    resp = openai.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role":"user","content":prompt}],
        temperature=OPENAI_TEMPERATURE,
        max_tokens=OPENAI_MAX_TOKENS
    )
    letter = resp.choices[0].message.content.strip()

    # Manually append the guaranteed footer
    footer = (
        "\n\n---\n"
        f"Please feel free to check out my work:\n"
        f"• Website: {PERSONAL_WEBSITE}\n"
        f"• GitHub: {GITHUB_URL}\n\n"
        f"{BOT_NOTE}"
    )
    return letter + footer


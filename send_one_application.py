#!/usr/bin/env python3
# send_one_application.py

import sys
from pathlib import Path

# ─── 0) Make sure the script folder is on sys.path ───────────────────────────
# This must come *before* any imports of your local packages.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# ─── 1) Load env & libs ──────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()  # loads OPENAI_API_KEY, GMAIL_USER, GMAIL_APP_PASS

import yaml
import openai

# ─── 2) Now import your local modules ────────────────────────────────────────
from data.resume_utils       import extract_resume_text
from generators.cover_letter import generate_cover_letter
from emailer.gmail_sender    import send_application
from config.settings         import PERSONA_YAML, RESUME_PDF

# ─── 3) Job‐parsing helper ────────────────────────────────────────────────────
def parse_job(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    job = {}
    for i, line in enumerate(lines):
        if line.startswith("Title:"):
            job["title"] = line.split("Title:",1)[1].strip()
        elif line.startswith("Company:"):
            job["company"] = line.split("Company:",1)[1].strip() or "Hiring Team"
        elif line.startswith("Location:"):
            job["location"] = line.split("Location:",1)[1].strip()
        elif line.startswith("Description:"):
            desc = []
            for dl in lines[i+1:]:
                if dl.startswith("Contact Email:") or dl.startswith("URL:"):
                    break
                desc.append(dl)
            job["description"] = "\n".join(desc).strip()
        elif line.startswith("Contact Email:"):
            job["email"] = line.split("Contact Email:",1)[1].strip()
        elif line.startswith("URL:"):
            job["url"] = line.split("URL:",1)[1].strip()
    return job

# ─── 4) Main flow ─────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) != 2:
        print("Usage: python send_one_application.py <PATH_TO_JOB_TXT>")
        sys.exit(1)

    job_path = Path(sys.argv[1])
    if not job_path.exists():
        print(f"Error: file not found: {job_path}")
        sys.exit(1)

    # Load persona
    with open(PERSONA_YAML, encoding="utf-8") as f:
        persona = yaml.safe_load(f)

    # Extract resume text
    resume_text = extract_resume_text(str(RESUME_PDF))

    # Parse the job file
    job = parse_job(job_path)
    print(f"🔍 Parsed job: {job['title']} at {job['company']} → {job['email']}")

    # Generate the letter
    print("📝 Generating cover letter…")
    cover_letter = generate_cover_letter(persona, resume_text, job)

    # Send the email
    subject = f"Application for {job['title']} at {job['company']}"
    print(f"✉️  Sending to {job['email']}…")
    send_application(
        to_address      = job["email"],
        subject         = subject,
        body_text       = cover_letter,
        attachment_path = str(RESUME_PDF)
    )

    print("Done!")

if __name__ == "__main__":
    main()


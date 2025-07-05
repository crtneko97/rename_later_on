#!/usr/bin/env python3
# send_applications.py

import os
import re
import time
import yaml
import openai
from dotenv import load_dotenv
from pathlib import Path

# ─── Local modules ────────────────────────────────────────────────────────────
from data.resume_utils       import extract_resume_text
from generators.cover_letter import generate_cover_letter
from emailer.gmail_sender    import send_application
from config.settings         import PERSONA_YAML, RESUME_PDF

# ─── 0) Load env & OpenAI key ─────────────────────────────────────────────────
load_dotenv()  # loads OPENAI_API_KEY, GMAIL_USER, GMAIL_APP_PASS

openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("Set OPENAI_API_KEY in your .env")

# ─── 1) Load persona.yaml ────────────────────────────────────────────────────
persona_path = Path(PERSONA_YAML)
if not persona_path.exists():
    raise RuntimeError(f"Persona file not found: {persona_path}")
with persona_path.open(encoding="utf-8") as f:
    persona = yaml.safe_load(f)

# ─── 2) Extract resume text once ──────────────────────────────────────────────
resume_path = Path(RESUME_PDF)
if not resume_path.exists():
    raise RuntimeError(f"Resume PDF not found: {resume_path}")
resume_text = extract_resume_text(str(resume_path))

# ─── 3) Discover latest scrape folder ─────────────────────────────────────────
raw_root = Path("output") / "raw"
date_dirs = sorted(raw_root.glob("[0-9]"*4 + "-" + "[0-9]"*2 + "-" + "[0-9]"*2))
if not date_dirs:
    raise RuntimeError(f"No dated folders found in {raw_root}")
date_folder = date_dirs[-1]
print(f"Sending applications for jobs in: {date_folder}")

# ─── 4) Email‐validation regex ────────────────────────────────────────────────
EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")

# ─── 5) Helper: parse a single job file ───────────────────────────────────────
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

# ─── 6) Loop & send ───────────────────────────────────────────────────────────
job_files = sorted(date_folder.glob("*.txt"))
print(f"Found {len(job_files)} job files. Starting…\n")

for idx, job_file in enumerate(job_files, start=1):
    print(f"[{idx}/{len(job_files)}] {job_file.name}")
    job = parse_job(job_file)

    # — Validate email address —
    email = job.get("email", "").strip()
    if not EMAIL_RE.fullmatch(email):
        print(f"  ⚠️ Skipping {job_file.name}: invalid or missing email ({email!r}) ⚠️ ")
        continue

    try:
        # Generate the letter
        print("Generating cover letter…")
        cover_letter = generate_cover_letter(persona, resume_text, job)

        # Prepare subject
        subject = f"Application for {job['title']} at {job['company']}"

        # Send email (attaches your resume automatically)
        send_application(
            to_address      = email,
            subject         = subject,
            body_text       = cover_letter,
            attachment_path = str(resume_path)
        )

        print("  ✅ Sent!")
    except Exception as e:
        print(f"  ❌ Error on {job_file.name}: {e}")

    # brief pause to avoid rate limits
    time.sleep(3)

print("\n ✅ All done sending applications! ✅ ")


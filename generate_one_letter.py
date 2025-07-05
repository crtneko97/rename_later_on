#!/usr/bin/env python3

from dotenv import load_dotenv
load_dotenv()  # loads OPENAI_API_KEY from .env

import yaml
import openai
from pathlib import Path
from data.resume_utils import extract_resume_text
from generators.cover_letter import generate_cover_letter
from config.settings import PERSONA_YAML, RESUME_PDF

# 1) Load persona.yaml
persona_path = Path(PERSONA_YAML)
if not persona_path.exists():
    raise RuntimeError(f"Persona file not found: {persona_path}")
with persona_path.open(encoding="utf-8") as f:
    persona = yaml.safe_load(f)

# 2) Extract resume text
resume_path = Path(RESUME_PDF)
if not resume_path.exists():
    raise RuntimeError(f"Resume PDF not found: {resume_path}")
resume_text = extract_resume_text(str(resume_path))

# 3) Discover the latest date folder under output/raw/
raw_root = Path("output") / "raw"
date_dirs = sorted(raw_root.glob("[0-9]"*4 + "-" + "[0-9]"*2 + "-" + "[0-9]"*2))
if not date_dirs:
    raise RuntimeError(f"No dated folders found in {raw_root}")
date_folder = date_dirs[-1]
print(f"📂 Using date folder: {date_folder}")

# 4) Pick the first scraped job file
job_files = sorted(date_folder.glob("*.txt"))
if not job_files:
    raise RuntimeError(f"No .txt files in {date_folder}")
job_file = job_files[0]
print(f"🔍 Testing with: {job_file}")

# 5) Parse that job file
def parse_job(path: str) -> dict:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    job = {}
    for i, line in enumerate(lines):
        if line.startswith("Title:"):
            job["title"] = line.split("Title:",1)[1].strip()
        elif line.startswith("Company:"):
            job["company"] = line.split("Company:",1)[1].strip()
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

job = parse_job(str(job_file))

# 6) Generate the cover letter via AI
print("📝 Generating cover letter…")
cover_letter = generate_cover_letter(persona, resume_text, job)

# 7) Print it out
print("\n—— Generated Cover Letter ——\n")
print(cover_letter)


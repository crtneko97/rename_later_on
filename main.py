import os
import re
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.firefox import GeckoDriverManager

# Configuration
START_URL = (
    "https://arbetsformedlingen.se/platsbanken/annonser"
    "?p=5:DJh5_yyF_hEM;5:Fv7d_YhP_YmS&l=2:CifL_Rzy_Mku"
)

# 1) Create a folder named by today’s date (YYYY-MM-DD)
today_str = datetime.date.today().isoformat()
OUTPUT_DIR = today_str
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -- Selenium setup --
options = Options()
options.headless = True
options.page_load_strategy = "eager"
options.add_argument("--width=1680")
options.add_argument("--height=940")

service = Service(GeckoDriverManager().install())
driver  = webdriver.Firefox(service=service, options=options)
driver.set_page_load_timeout(60)

def safe_get(driver, url, retries=1):
    for attempt in range(retries + 1):
        try:
            driver.get(url)
            return
        except TimeoutException:
            if attempt < retries:
                print(f"[Retry] timeout loading {url}…")
            else:
                print(f"[Error] giving up on {url}")

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text or "job"

try:
    # 2) Load listing page
    safe_get(driver, START_URL, retries=2)

    # 3) Accept cookies if needed
    try:
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Jag godkänner')]"))
        ).click()
    except:
        pass

    # 4) Wait for first job link
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/platsbanken/annonser/')]"))
    )

    # 5) Load all pages via “Visa fler”
    while True:
        try:
            more = driver.find_element(By.XPATH, "//button[contains(text(),'Visa fler')]")
        except:
            break
        driver.execute_script("arguments[0].click()", more)
        WebDriverWait(driver, 10).until(
            lambda d: len(d.find_elements(By.XPATH, "//a[contains(@href, '/platsbanken/annonser/')]")) > 0
        )

    # 6) Collect unique job URLs
    seen = set()
    job_links = []
    for a in driver.find_elements(By.XPATH, "//a[contains(@href, '/platsbanken/annonser/')]"):
        href = a.get_attribute("href")
        if href and href not in seen:
            seen.add(href)
            job_links.append(href)

    # 7) Scrape each job and write one file per listing
    main_win = driver.current_window_handle

    for idx, link in enumerate(job_links, 1):
        driver.execute_script("window.open(arguments[0])", link)
        driver.switch_to.window(driver.window_handles[-1])

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
        except:
            driver.close()
            driver.switch_to.window(main_win)
            continue

        # Extract fields
        title = driver.find_element(By.TAG_NAME, "h1").text.strip() if driver.find_elements(By.TAG_NAME, "h1") else ""
        try:
            company = driver.find_element(By.XPATH, "//strong[contains(@class, 'pb-company')]").text.strip()
        except:
            try:
                company = driver.find_element(By.XPATH, "//h1/following-sibling::*[1]").text.strip()
            except:
                company = ""
        try:
            loc_txt = driver.find_element(By.XPATH, "//*[contains(text(), 'Kommun:')]").text
            location = loc_txt.split("Kommun:")[-1].strip()
        except:
            location = ""
        body_text = driver.find_element(By.TAG_NAME, "body").text
        content = body_text.split("Kontakt", 1)[0] if "Kontakt" in body_text else body_text
        desc_idx = 0
        i1, i2 = content.find("Kvalifikationer"), content.find("Om jobbet")
        if i1 != -1 and (i2 == -1 or i1 < i2):
            desc_idx = i1
        elif i2 != -1:
            desc_idx = i2
        description = content[desc_idx:].strip()
        try:
            mailto = driver.find_element(By.XPATH, "//a[starts-with(@href,'mailto:')]").get_attribute("href")
            contact_email = mailto.split("mailto:")[-1].strip()
        except:
            contact_email = ""

        # Build per-job filename and save
        slug = slugify(title)
        fname = f"{idx:03d}-{slug}.txt"
        path  = os.path.join(OUTPUT_DIR, fname)
        with open(path, "w", encoding="utf-8") as out:
            out.write(f"Title: {title}\n")
            out.write(f"Company: {company}\n")
            out.write(f"Location: {location}\n\n")
            out.write("Description:\n")
            out.write(description + "\n\n")
            out.write(f"Contact Email: {contact_email}\n")
            out.write(f"URL: {link}\n")

        print(f"[Saved] {path}")
        driver.close()
        driver.switch_to.window(main_win)

    print(f"All done – {len(job_links)} files in ./{OUTPUT_DIR}/")

finally:
    driver.quit()


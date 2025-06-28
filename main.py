import os
import re
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.firefox import GeckoDriverManager

# ─── Configuration ────────────────────────────────────────────────────────────
START_URL = (
    "https://arbetsformedlingen.se/platsbanken/annonser"
    "?p=5:DJh5_yyF_hEM;5:Fv7d_YhP_YmS&l=2:CifL_Rzy_Mku"
)
today_str  = datetime.date.today().isoformat()
OUTPUT_DIR = today_str
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── Selenium setup ───────────────────────────────────────────────────────────
options = Options()
options.headless            = True
options.page_load_strategy  = "eager"
options.add_argument("--width=1680")
options.add_argument("--height=940")

service = Service(GeckoDriverManager().install())
driver  = webdriver.Firefox(service=service, options=options)
driver.set_page_load_timeout(60)

def safe_get(url, retries=1):
    for i in range(retries+1):
        try:
            driver.get(url)
            return
        except TimeoutException:
            if i < retries:
                print(f"[Retry] loading {url}")
            else:
                print(f"[Error] could not load {url}")

def slugify(text: str) -> str:
    s = text.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s or "job"

# ─── Main scraping logic ──────────────────────────────────────────────────────
try:
    # 1) Load first page of listings
    safe_get(START_URL, retries=2)

    # 2) Accept cookies if prompted
    try:
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Jag godkänner')]"))
        ).click()
    except:
        pass

    # 3) Prepare global counters
    file_counter = 1
    page_number  = 1

    # 4) Paginate through all listing pages
    while True:
        print(f"=== Page {page_number} ===")

        # Wait for all job cards to appear
        cards = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//a[contains(@href,'/platsbanken/annonser/')]")
            )
        )

        # 5) Loop over each card on this page
        for card in cards:
            link = card.get_attribute("href")
            if not link:
                continue

            # Open detail in new tab
            driver.execute_script("window.open(arguments[0]);", link)
            driver.switch_to.window(driver.window_handles[-1])

            # Wait for content
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "h1"))
                )
            except:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                continue

            # — Extract fields —
            title = driver.find_element(By.TAG_NAME, "h1").text.strip()

            try:
                company = driver.find_element(
                    By.XPATH, "//strong[contains(@class,'pb-company')]"
                ).text.strip()
            except:
                company = ""

            try:
                loc_txt = driver.find_element(
                    By.XPATH, "//*[contains(text(),'Kommun:')]"
                ).text
                location = loc_txt.split("Kommun:")[-1].strip()
            except:
                location = ""

            body = driver.find_element(By.TAG_NAME, "body").text
            content = body.split("Kontakt", 1)[0] if "Kontakt" in body else body
            # Start description at “Kvalifikationer” or “Om jobbet”
            idx1, idx2 = content.find("Kvalifikationer"), content.find("Om jobbet")
            start = 0
            if idx1 != -1 and (idx2 == -1 or idx1 < idx2):
                start = idx1
            elif idx2 != -1:
                start = idx2
            description = content[start:].strip()

            try:
                mailto = driver.find_element(
                    By.XPATH, "//a[starts-with(@href,'mailto:')]"
                ).get_attribute("href")
                contact_email = mailto.split("mailto:")[-1].strip()
            except:
                contact_email = ""

            # — Save to its own file —
            slug  = slugify(title)
            fname = f"{file_counter:03d}-{slug}.txt"
            path  = os.path.join(OUTPUT_DIR, fname)
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"Title: {title}\n")
                f.write(f"Company: {company}\n")
                f.write(f"Location: {location}\n\n")
                f.write("Description:\n")
                f.write(description + "\n\n")
                f.write(f"Contact Email: {contact_email}\n")
                f.write(f"URL: {link}\n")

            print(f"[Saved] {path}")
            file_counter += 1

            # Close tab and switch back
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

        # 6) Try to click the “Nästa” button
        try:
            nxt = driver.find_element(
                By.XPATH,
                "//button[.//span[contains(text(),'Nästa')]]"
            )
            driver.execute_script("arguments[0].click()", nxt)
            page_number += 1
            # Wait for the previous first card to become stale
            WebDriverWait(driver, 10).until(EC.staleness_of(cards[0]))
        except NoSuchElementException:
            # No more pages left
            break

    print(f"Done! Scraped {file_counter-1} jobs into ./{OUTPUT_DIR}/")

finally:
    driver.quit()


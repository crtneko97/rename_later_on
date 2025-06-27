import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.firefox import GeckoDriverManager

# Configuration
START_URL  = (
    "https://arbetsformedlingen.se/platsbanken/annonser"
    "?p=5:DJh5_yyF_hEM;5:Fv7d_YhP_YmS&l=2:CifL_Rzy_Mku"
)
OUTPUT_CSV = "platsbanken_jobs.csv"

# 1) Initialize headless Firefox with webdriver-manager
options = Options()
options.headless = True                   # no GUI
options.page_load_strategy = "eager"      # load until DOMInteractive
options.add_argument("--width=1680")      # ensure desktop layout
options.add_argument("--height=940")

service = Service(GeckoDriverManager().install())
driver  = webdriver.Firefox(service=service, options=options)

# 2) Give pages up to 60s before throwing TimeoutException
driver.set_page_load_timeout(60)

def safe_get(driver, url, retries=1):
    """Try driver.get(url) with optional retry(s) on timeout."""
    for attempt in range(retries + 1):
        try:
            driver.get(url)
            return
        except TimeoutException:
            if attempt < retries:
                print(f"[Retry] timeout loading {url}…")
            else:
                print(f"[Error] failed to load {url} after {retries+1} attempts")

try:
    # 3) Load the listing page
    safe_get(driver, START_URL, retries=2)

    # 4) Accept cookies if prompted
    try:
        btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Jag godkänner')]"))
        )
        btn.click()
    except Exception:
        pass  # no banner or already accepted

    # 5) Wait for at least one job link
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/platsbanken/annonser/')]"))
    )

    # 6) Click “Visa fler” until everything’s loaded
    while True:
        try:
            more_btn = driver.find_element(By.XPATH, "//button[contains(text(),'Visa fler')]")
        except:
            break
        driver.execute_script("arguments[0].click()", more_btn)
        WebDriverWait(driver, 10).until(
            lambda d: len(d.find_elements(By.XPATH, "//a[contains(@href, '/platsbanken/annonser/')]")) > 0
        )

    # 7) Gather unique job URLs
    seen = set()
    job_links = []
    for a in driver.find_elements(By.XPATH, "//a[contains(@href, '/platsbanken/annonser/')]"):
        href = a.get_attribute("href")
        if href and href not in seen:
            seen.add(href)
            job_links.append(href)

    # 8) Scrape each job detail and write CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Title", "Company", "Location", "Description", "ContactEmail"])

        main_win = driver.current_window_handle

        for link in job_links:
            # open detail in new tab
            driver.execute_script("window.open(arguments[0])", link)
            driver.switch_to.window(driver.window_handles[-1])

            # wait for the title to appear
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "h1"))
                )
            except:
                driver.close()
                driver.switch_to.window(main_win)
                continue

            # — Extract fields —

            # Title
            try:
                title = driver.find_element(By.TAG_NAME, "h1").text.strip()
            except:
                title = ""

            # Company
            try:
                company = driver.find_element(
                    By.XPATH,
                    "//strong[contains(@class, 'pb-company')]"
                ).text.strip()
            except:
                try:
                    company = driver.find_element(
                        By.XPATH,
                        "//h1/following-sibling::*[1]"
                    ).text.strip()
                except:
                    company = ""

            # Location
            try:
                loc_txt = driver.find_element(
                    By.XPATH,
                    "//*[contains(text(), 'Kommun:')]"
                ).text
                location = loc_txt.split("Kommun:")[-1].strip()
            except:
                location = ""

            # Description (everything up to “Kontakt”)
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if "Kontakt" in body_text:
                content = body_text.split("Kontakt", 1)[0]
            else:
                content = body_text

            # Try to start at “Kvalifikationer” or “Om jobbet”
            desc_idx = 0
            i1 = content.find("Kvalifikationer")
            i2 = content.find("Om jobbet")
            if i1 != -1 and (i2 == -1 or i1 < i2):
                desc_idx = i1
            elif i2 != -1:
                desc_idx = i2
            description = content[desc_idx:].strip()

            # Contact email
            try:
                mailto = driver.find_element(
                    By.XPATH,
                    "//a[starts-with(@href,'mailto:')]"
                ).get_attribute("href")
                contact_email = mailto.split("mailto:")[-1].strip()
            except:
                contact_email = ""

            # Write row
            writer.writerow([title, company, location, description, contact_email])

            # Close tab & return
            driver.close()
            driver.switch_to.window(main_win)

    print(f"Done! Scraped {len(job_links)} jobs → {OUTPUT_CSV}")

finally:
    driver.quit()


import os
import re
import time
import pandas as pd
import pytesseract
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

AGENCY_URL = "https://www.transit.dot.gov/ntd/transit-agency-profiles/centre-area-transportation-authority"
BASE_URL = "https://www.transit.dot.gov"
OUTPUT_CSV = "CA_tran_before_text.csv"
SCREENSHOT_DIR = os.path.join(os.getcwd(), "pdf_screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"

chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1600,1200")

print("Launching Chrome browser...")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

print(f"Opening {AGENCY_URL} ...")
driver.get(AGENCY_URL)
time.sleep(8)

pdf_links = []
for a in driver.find_elements("tag name", "a"):
    href = a.get_attribute("href")
    if href and href.lower().endswith(".pdf"):
        if not href.startswith("http"):
            href = BASE_URL + href
        pdf_links.append(href)

pdf_links = list(dict.fromkeys(pdf_links))
print(f"Found {len(pdf_links)} PDF files.")

pattern_year = re.compile(r"(20\d{2})")

pattern_pmt_before =pattern_upt_annual = re.compile(r"(\d[\d,\.]*)\s+Average\s+Weekday\s+Unlinked\s+Trips\s", re.IGNORECASE)

data = []

for idx, url in enumerate(pdf_links, start=1):
    print(f"\nOpening PDF {idx}/{len(pdf_links)}: {url}")
    try:
        driver.get(url)
        time.sleep(6)

        screenshot_path = os.path.join(SCREENSHOT_DIR, f"page_{idx}.png")
        driver.save_screenshot(screenshot_path)

        image = Image.open(screenshot_path)
        ocr_text = pytesseract.image_to_string(image, config="--psm 6")

        year_match = pattern_year.search(url) or pattern_year.search(ocr_text)
        year = year_match.group(1) if year_match else "Unknown"

        pmt_match = pattern_pmt_before.search(ocr_text)
        if pmt_match:
            pmt_value = re.sub(r"[^\d]", "", pmt_match.group(1))
            print(f"✔ {year}: PMT = {pmt_value}")
            data.append({
                "Year": year,
                "PMT": pmt_value,
                "Source": url
            })
        else:
            print(f"⚠ {year}: PMT not found before phrase.")

        os.remove(screenshot_path)

    except Exception as e:
        print(f"❌ Error reading {url}: {e}")

driver.quit()
try:
    os.rmdir(SCREENSHOT_DIR)
except OSError:
    pass

if data:
    df = pd.DataFrame(data)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\n✅ Done! PMT data saved to {OUTPUT_CSV}")
else:
    print("\n⚠ No PMT data found in any PDF.")

import time
import csv
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

from backend.nlp.review_analyser import analyze_reviews
from backend.database.save_reviews import save_reviews


# ================== DRIVER SETUP ==================
def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)


# ================== RATING EXTRACTION ==================
def extract_rating(block):
    stars = block.select("i.sd-icon-star.active, span.sd-icon-star.active")
    if stars:
        return len(stars)

    aria = block.select_one("[aria-label*='out of 5']")
    if aria:
        try:
            return int(aria.get("aria-label").split()[0])
        except:
            pass

    return None


# ================== SCRAPE ONE PAGE ==================
def scrape_reviews_from_page(driver, url, seen_reviews):
    driver.get(url)
    time.sleep(3)

    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # ✅ ONLY main review container
    reviews_container = soup.select_one("#defaultReviewsCard")
    if not reviews_container:
        return []

    blocks = reviews_container.select("div.commentlist")

    page_reviews = []

    for block in blocks:
        review_p = block.select_one("p.comment") or block.find("p")
        review_text = review_p.text.strip() if review_p else None
        rating = extract_rating(block)

        if not review_text:
            continue

        # ✅ extra safety normalization
        normalized = review_text.lower().strip()

        if normalized not in seen_reviews:
            seen_reviews.add(normalized)
            page_reviews.append({
                "rating": rating,
                "review": review_text
            })

    return page_reviews

# ================== SCRAPE ALL PAGES ==================
def scrape_snapdeal_reviews(product_url):
    driver = setup_driver()
    all_reviews = []
    seen_reviews = set()
    page = 1

    print("🔎 Scraping Snapdeal reviews...")

    try:
        while True:
            url = f"{product_url}/reviews?page={page}&sortBy=RECENCY#defRevPDP"
            reviews = scrape_reviews_from_page(driver, url, seen_reviews)

            if not reviews:
                break

            all_reviews.extend(reviews)
            page += 1

    finally:
        driver.quit()

    print(f"✅ Total Reviews Scraped: {len(all_reviews)}")
    return all_reviews


# ================== SAVE TO CSV ==================
def save_to_csv(reviews, filename="snapdeal_reviews.csv"):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["S.No", "Rating", "Review", "Sentiment", "Score"])

        for i, r in enumerate(reviews, start=1):
            writer.writerow([
                i,
                r["rating"],
                r["review"],
                r.get("sentiment"),
                r.get("compound")
            ])


# ================== MAIN ==================
if __name__ == "__main__":
    PRODUCT_URL = "https://www.snapdeal.com/product/cat-bunny-woollen-high-neck/683340287753"

    reviews = scrape_snapdeal_reviews(PRODUCT_URL)

    enriched_reviews, analytics = analyze_reviews(reviews)

    save_to_csv(enriched_reviews)

    save_reviews(enriched_reviews, PRODUCT_URL)

    df = pd.DataFrame(enriched_reviews)
    print(df.head())

    print("\n📊 Sentiment Distribution:")
    print(analytics["sentiment_distribution"])
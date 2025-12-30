from flask import Flask, request, jsonify
from flask_cors import CORS

from backend.scraper.scraper import scrape_snapdeal_reviews
from backend.nlp.review_analyser import analyze_reviews
from backend.database.save_reviews import save_reviews
from backend.database.mongo_connection import reviews_collection

app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET"])
def home():
    return {"status": "Backend API running successfully"}


# 🔹 Trigger scraping + NLP + DB save
@app.route("/analyze", methods=["POST"])
def analyze_product():
    data = request.get_json()
    product_url = data.get("product_url")

    if not product_url:
        return {"error": "Product URL is required"}, 400

    reviews = scrape_snapdeal_reviews(product_url)
    enriched_reviews, analytics = analyze_reviews(reviews)

    save_reviews(enriched_reviews, product_url)

    return {
        "message": "Scraping and analysis completed",
        "total_reviews": len(enriched_reviews),
        "sentiment_distribution": analytics["sentiment_distribution"],
        "top_words": analytics["top_words"]
    }


# 🔹 Fetch stored reviews
@app.route("/reviews", methods=["GET"])
def get_reviews():
    product_url = request.args.get("product_url")

    query = {}
    if product_url:
        query["product_url"] = product_url

    reviews = list(reviews_collection.find(query, {"_id": 0}))
    return jsonify(reviews)


if __name__ == "__main__":
    app.run(debug=True)

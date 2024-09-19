from flask import Flask, request, jsonify
import requests
import json
import re
import time
from google_play_scraper import Sort, reviews
from app_store_scraper import AppStore

app = Flask(__name__)


def extract_id_from_url(url):
    # Regular expression to match the package ID in the URL
    pattern = r"https://play.google.com/store/apps/details\?id=([^&]+)"
    
    # Search for the package ID in the URL
    match = re.search(pattern, url)

    if match:
        return match.group(1)
    else:
        return None
    
def fetch_all_reviews(url, count=200, stars=5):
    package_id = extract_id_from_url(url)
    if not package_id:
        raise ValueError("Invalid URL: Could not extract package ID.")

    results = []
    continuation_token = None

    while len(results) < count:
        result, continuation_token = reviews(
            package_id,
            lang='en',
            country='us',
            sort=Sort.NEWEST,
            filter_score_with=stars,
            count=min(count - len(results), 100),  # Adjust count to avoid fetching too many at once
            continuation_token=continuation_token
        )

        results.extend(result)
        time.sleep(1)  # Add a delay to avoid rate limiting

    return results

    
def extract_app_info(url):
    pattern = r"https://apps\.apple\.com/(\w+)/app/([^/]+)/id(\d+)"
    match = re.match(pattern, url)
    if match:
        country, app_name, app_id = match.groups()
        app_name = app_name.replace('-', ' ')  # Convert hyphens to spaces
        return country, app_name, app_id
    return None, None, None

@app.route("/test")
def test():
    return jsonify({"message": "Hello World"})


@app.route('/api/get-playstore-reviews', methods=['GET'])
def fetch_reviews():
    """API endpoint to fetch reviews for a given Google Play Store app."""
    url = request.args.get('url')
    count = int(request.args.get('count', 200))
    stars = int(request.args.get('stars', 5))
    
    if not url:
        return jsonify({"error": "Please provide a Google Play Store URL."}), 400
    
    try:
        reviews_data = fetch_all_reviews(url, count=count, stars=stars)
        return jsonify({"reviews": reviews_data, "platform": "PlayStore"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "An error occurred while fetching reviews."}), 

@app.route('/api/get-appstore-reviews', methods=['GET'])
def get_reviews():
    url = request.args.get('url')
    num_reviews = request.args.get('num_reviews', default=20, type=int)

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    country, app_name, app_id = extract_app_info(url)

    if not all([country, app_name, app_id]):
        return jsonify({"error": "Invalid App Store URL"}), 400

    try:
        app = AppStore(country=country, app_name=app_name, app_id=app_id)
        app.review(how_many=num_reviews)
        return jsonify({"reviews": app.reviews, "platform": "AppStore"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
   
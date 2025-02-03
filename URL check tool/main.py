from flask import Flask, request, jsonify, send_from_directory, render_template
import requests
from concurrent.futures import ThreadPoolExecutor
import os

app = Flask(__name__)

# Directory to store output files
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Lists to store results
live_urls = []
not_found_urls = []
redirected_urls = []

# Function to check a single URL
def check_url(url):
    try:
        response = requests.get(url, timeout=10, allow_redirects=True)

        final_url = response.url
        if final_url != url:
            redirected_urls.append(f"{url} → {final_url}")

        if response.status_code == 404:
            not_found_urls.append(url)
        elif "page not found" in response.text.lower() or "404" in response.text.lower():
            not_found_urls.append(url)
        else:
            live_urls.append(url)

    except requests.exceptions.RequestException:
        not_found_urls.append(url)

# Function to process URLs in parallel
def process_urls(url_list):
    global live_urls, not_found_urls, redirected_urls
    live_urls, not_found_urls, redirected_urls = [], [], []

    with ThreadPoolExecutor(max_workers=50) as executor:
        executor.map(check_url, url_list)

    # Save results to files
    with open(os.path.join(OUTPUT_DIR, "live_urls.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(live_urls))

    with open(os.path.join(OUTPUT_DIR, "404_urls.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(not_found_urls))

    with open(os.path.join(OUTPUT_DIR, "redirected_urls.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(redirected_urls))

# Route to serve frontend
@app.route("/")
def home():
    return render_template("index.html")

# API to check URLs
@app.route("/check_urls", methods=["POST"])
def check_urls():
    data = request.get_json()
    urls = data.get("urls", [])

    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    process_urls(urls)
    return jsonify({"message": "URLs processed successfully"})

# Route to download files
@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)

# Run Flask app
if __name__ == "__main__":
    app.run(debug=True)

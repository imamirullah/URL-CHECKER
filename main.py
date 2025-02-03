from flask import Flask, request, jsonify, send_from_directory, render_template
import requests
from concurrent.futures import ThreadPoolExecutor
import os

app = Flask(__name__)

# Directory to store output files
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Function to check a single URL
def check_url(url, live_urls, not_found_urls, redirected_urls):
    try:
        response = requests.get(url, timeout=10, allow_redirects=True)
        final_url = response.url

        if final_url != url:
            redirected_urls.append(final_url)

        if response.status_code == 404 or "page not found" in response.text.lower():
            not_found_urls.append(url)
        else:
            live_urls.append(url)
    except requests.exceptions.RequestException:
        not_found_urls.append(url)

# Function to process URLs in parallel
def process_urls(url_list):
    live_urls, not_found_urls, redirected_urls = [], [], []

    with ThreadPoolExecutor(max_workers=50) as executor:
        executor.map(lambda url: check_url(url, live_urls, not_found_urls, redirected_urls), url_list)

    # Save results to files
    file_paths = {
        "live_urls.txt": live_urls,
        "404_urls.txt": not_found_urls,
        "redirected_urls.txt": redirected_urls,
    }

    for filename, data in file_paths.items():
        with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
            f.write("\n".join(data))

    return file_paths  # Return file names for frontend

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

    file_paths = process_urls(urls)

    return jsonify({
        "message": "URLs processed successfully",
        "files": list(file_paths.keys())  # Send filenames in response
    })

# Route to download files
@app.route("/download/<filename>")
def download_file(filename):
    filepath = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(filepath):
        return send_from_directory(OUTPUT_DIR, filename, as_attachment=True, mimetype="text/plain")
    return jsonify({"error": "File not found"}), 404

# Run Flask app
if __name__ == "__main__":
    app.run(debug=True)

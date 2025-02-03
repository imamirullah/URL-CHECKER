from flask import Flask, request, jsonify, send_from_directory, render_template
import requests
from concurrent.futures import ThreadPoolExecutor
import os

app = Flask(__name__)

# Attempt to use a known writable directory (/tmp) if available, otherwise fallback to a local directory.
def get_writable_output_dir():
    test_dir = "/tmp"
    test_file = os.path.join(test_dir, "test.txt")
    try:
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return test_dir
    except Exception as e:
        print(f"/tmp is not writable, falling back to local 'output' directory. Error: {e}")
        fallback_dir = os.path.join(os.getcwd(), "output")
        return fallback_dir

OUTPUT_DIR = get_writable_output_dir()
os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"[DEBUG] Files will be written to: {OUTPUT_DIR}")

# Function to check a single URL
def check_url(url, live_urls, not_found_urls, redirected_urls):
    print(f"[DEBUG] Processing URL: {url}")
    try:
        response = requests.get(url, timeout=10, allow_redirects=True)
        final_url = response.url
        print(f"[DEBUG] Final URL for {url}: {final_url}")
        if final_url != url:
            redirected_urls.append(final_url)

        if response.status_code == 404 or "page not found" in response.text.lower():
            not_found_urls.append(url)
        else:
            live_urls.append(url)
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error processing {url}: {e}")
        not_found_urls.append(url)

# Function to process URLs in parallel
def process_urls(url_list):
    live_urls, not_found_urls, redirected_urls = [], [], []

    with ThreadPoolExecutor(max_workers=50) as executor:
        # Using a lambda to call check_url for each URL
        executor.map(lambda url: check_url(url, live_urls, not_found_urls, redirected_urls), url_list)

    # Prepare file data
    file_data = {
        "live_urls.txt": live_urls,
        "404_urls.txt": not_found_urls,
        "redirected_urls.txt": redirected_urls,
    }

    created_files = {}

    # Save results to files with error logging
    for filename, data in file_data.items():
        file_path = os.path.join(OUTPUT_DIR, filename)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(data))
            created_files[filename] = data  # Save the data for reference
            print(f"[DEBUG] Successfully wrote to {file_path}")
        except Exception as e:
            print(f"[ERROR] Error writing to {file_path}: {e}")

    return created_files  # Return dict with filenames and their data

# Route to serve the frontend
@app.route("/")
def home():
    return render_template("index.html")

# API to check URLs
@app.route("/check_urls", methods=["POST"])
def check_urls_api():
    data = request.get_json()
    urls = data.get("urls", [])
    print(f"[DEBUG] Received data: {data}")

    if not urls:
        print("[ERROR] No URLs provided in the request")
        return jsonify({"error": "No URLs provided"}), 400

    files_created = process_urls(urls)
    print(f"[DEBUG] Files created: {list(files_created.keys())}")
    
    return jsonify({
        "message": "URLs processed successfully",
        "files": list(files_created.keys())
    })

# Route to download files
@app.route("/download/<filename>")
def download_file(filename):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(file_path):
        print(f"[DEBUG] Serving file: {file_path}")
        return send_from_directory(OUTPUT_DIR, filename, as_attachment=True, mimetype="text/plain")
    print(f"[ERROR] File not found: {file_path}")
    return jsonify({"error": "File not found"}), 404

# Run Flask app
if __name__ == "__main__":
    print("Server running...")
    app.run(debug=True)

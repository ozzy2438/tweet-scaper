import requests
import json
import os

# Replace with your Bright Data API Token
API_TOKEN = "YOUR_API_TOKEN"

# Replace with your desired folder path to save the data
OUTPUT_FOLDER = "/path/to/your/folder"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def fetch_and_save_data(query, output_file_name):
    url = "https://api.brightdata.com/datasets/v3/trigger"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "url": query,  # Input query
        "max_rows": 300,  # Limit to 300 rows
        "include_errors": True
    }

    # API request
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()
        # Save data to file
        output_file = os.path.join(OUTPUT_FOLDER, output_file_name)
        with open(output_file, "w") as f:
            json.dump(data, f, indent=4)
        print(f"Data successfully saved to {output_file}")
    else:
        print(f"Failed to fetch data. Status Code: {response.status_code}, Response: {response.text}")

# Input your query and file name
query = "https://www.youtube.com/@MrBeast/about"
output_file_name = "youtube_data.json"

# Fetch data and save to the folder
fetch_and_save_data(query, output_file_name)
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
import requests
import pandas as pd

# Function to convert IPFS links to HTTP format
def ipfs_to_http(ipfs_link):
    if ipfs_link.startswith("ipfs://"):
        # Convert to HTTP gateway format
        http_link = f"https://gateway.ipfs.io/ipfs/{ipfs_link[7:]}"
        # Convert to specific fxhash2 gateway format
        fxhash_link = f"https://gateway.fxhash2.xyz/ipfs/{ipfs_link[7:]}"
        return http_link, fxhash_link
    return ipfs_link, ipfs_link

# Function to fetch data from the fxhash public API
def fetch_artwork_from_api(artwork_id):
    api_url = f"https://api.fxhash.xyz/v1/tokens/{artwork_id}"
    try:
        response = requests.get(api_url, timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.exceptions.RequestException:
        return None

# Function to fetch and analyze an artwork page
def analyze_artwork(url, artwork_id):
    # First, try to fetch data from the API
    api_data = fetch_artwork_from_api(artwork_id)
    if api_data and 'token' in api_data:
        token = api_data['token']
        description_text = token.get('description', '-')
        ipfs_link = token.get('ipfs', '-')
        
        # Attempt to fetch the code from the IPFS link
        code_content = fetch_ipfs_code(ipfs_link)

        # Extract p5.js version and other libraries
        p5_version_summary, other_libraries = extract_libraries(code_content)

        # Extract additional URIs
        artifact_uri = token.get('artifactUri', '-')
        display_uri = token.get('displayUri', '-')
        thumbnail_uri = token.get('thumbnailUri', '-')
        generative_uri = token.get('generativeUri', '-')

        # Convert IPFS URIs to HTTP format
        artifact_uri_http, artifact_uri_fxhash = ipfs_to_http(artifact_uri)
        display_uri_http, display_uri_fxhash = ipfs_to_http(display_uri)
        thumbnail_uri_http, thumbnail_uri_fxhash = ipfs_to_http(thumbnail_uri)
        generative_uri_http, generative_uri_fxhash = ipfs_to_http(generative_uri)

        return ("working", description_text, ipfs_link, p5_version_summary, other_libraries,
                artifact_uri_http, artifact_uri_fxhash,
                display_uri_http, display_uri_fxhash,
                thumbnail_uri_http, thumbnail_uri_fxhash,
                generative_uri_http, generative_uri_fxhash)

    # If API data is not available, fall back to web scraping
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            library_description = soup.find('div', class_="Clamp_container__xOFme GenerativeDisplay_description__NweHb")

            # Extract the description
            description_text = library_description.get_text(separator=" ").strip() if library_description else "-"
            
            # Find the IPFS link
            ipfs_link_tag = soup.find('a', href=lambda x: x and 'ipfs' in x)
            ipfs_link = ipfs_link_tag['href'].split(',')[0].strip() if ipfs_link_tag else "-"

            # Ensure it's a proper IPFS link
            if ipfs_link.startswith('/ipfs/') or ipfs_link.startswith('https://gateway.fxhash2.xyz/ipfs/'):
                if not ipfs_link.startswith('https://'):
                    ipfs_link = f"https://gateway.fxhash2.xyz/ipfs/{ipfs_link.split('/')[-1]}"

            # Attempt to fetch the code from the IPFS link
            code_content = fetch_ipfs_code(ipfs_link)

            # Extract p5.js version and other libraries
            p5_version_summary, other_libraries = extract_libraries(code_content)
            
            # Extract additional URIs
            artifact_uri = extract_uri_data(soup, 'artifactUri')
            display_uri = extract_uri_data(soup, 'displayUri')
            thumbnail_uri = extract_uri_data(soup, 'thumbnailUri')
            generative_uri = extract_uri_data(soup, 'generativeUri')

            # Convert IPFS URIs to HTTP format
            artifact_uri_http, artifact_uri_fxhash = ipfs_to_http(artifact_uri)
            display_uri_http, display_uri_fxhash = ipfs_to_http(display_uri)
            thumbnail_uri_http, thumbnail_uri_fxhash = ipfs_to_http(thumbnail_uri)
            generative_uri_http, generative_uri_fxhash = ipfs_to_http(generative_uri)

            return ("working", description_text, ipfs_link, p5_version_summary, other_libraries,
                    artifact_uri_http, artifact_uri_fxhash,
                    display_uri_http, display_uri_fxhash,
                    thumbnail_uri_http, thumbnail_uri_fxhash,
                    generative_uri_http, generative_uri_fxhash)
        else:
            return ("not working", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-")
    except requests.exceptions.RequestException:
        return ("not working", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-")

def fetch_ipfs_code(ipfs_link):
    try:
        code_response = requests.get(ipfs_link)
        return code_response.text if code_response.status_code == 200 else None
    except Exception:
        return None

def extract_libraries(code_content):
    if not code_content:
        return "No p5.js found", "No other libraries found"
    
    p5_versions = re.findall(r'(p5(\.min)?\.js)[^\s]*', code_content)
    version_numbers = re.findall(r'(v?\d+\.\d+\.\d+|p5@\d+\.\d+\.\d+)', code_content)
    
    # Collect other libraries
    other_libraries = re.findall(r'(https?://[^"\'\s]+)', code_content)

    # Combine and return unique versions
    p5_version_summary = " / ".join(set(version_numbers)) if version_numbers else "No p5.js found"
    other_libraries_summary = " / ".join(set(other_libraries)) if other_libraries else "No other libraries found"

    return p5_version_summary, other_libraries_summary

def extract_uri_data(soup, uri_type):
    script_tag = soup.find('script', string=lambda x: x and uri_type in x)
    if script_tag:
        match = re.search(rf'"{uri_type}":"(ipfs://[^"]+)"', script_tag.string)
        return match.group(1) if match else "-"
    return "-"

# Function to open the browser and navigate to the artwork URL
def open_artwork_in_browser(driver, url):
    driver.get(url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
    print(f"Opened artwork URL: {url}")

# Main function
def main():
    start_id = 30661
    end_id = 31300
    artwork_links = [f"https://www.fxhash.xyz/generative/{artwork_id}" for artwork_id in range(start_id, end_id + 1)]
    
    # Initialize the browser once
    options = Options()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # Data containers
    link_status = []
    creative_coding_libraries = []
    ipfs_codes = []
    p5_versions = []
    other_libraries = []
    artifact_uris_http = []
    artifact_uris_fxhash = []
    display_uris_http = []
    display_uris_fxhash = []
    thumbnail_uris_http = []
    thumbnail_uris_fxhash = []
    generative_uris_http = []
    generative_uris_fxhash = []
    
    # Analyze each artwork
    for artwork_id, artwork_url in enumerate(artwork_links, start=start_id):
        results = analyze_artwork(artwork_url, artwork_id)
        link_status.append(results[0])
        creative_coding_libraries.append(results[1])
        ipfs_codes.append(results[2])
        p5_versions.append(results[3])
        other_libraries.append(results[4])
        artifact_uris_http.append(results[5])
        artifact_uris_fxhash.append(results[6])
        display_uris_http.append(results[7])
        display_uris_fxhash.append(results[8])
        thumbnail_uris_http.append(results[9])
        thumbnail_uris_fxhash.append(results[10])
        generative_uris_http.append(results[11])
        generative_uris_fxhash.append(results[12])

        # Open the artwork in the same browser instance
        open_artwork_in_browser(driver, artwork_url)

    # Save results to a CSV file
    df = pd.DataFrame({
        'Generative Art Link': artwork_links,
        'Link Status': link_status,
        'Generative Library': creative_coding_libraries,
        'IPFS Code Link': ipfs_codes,
        'p5.js Version': p5_versions,
        'Other Libraries': other_libraries,
        'Artifact URI (HTTP)': artifact_uris_http,
        'Artifact URI (FXHash)': artifact_uris_fxhash,
        'Display URI (HTTP)': display_uris_http,
        'Display URI (FXHash)': display_uris_fxhash,
        'Thumbnail URI (HTTP)': thumbnail_uris_http,
        'Thumbnail URI (FXHash)': thumbnail_uris_fxhash,
        'Generative URI (HTTP)': generative_uris_http,
        'Generative URI (FXHash)': generative_uris_fxhash
    })
    
    csv_file_path = 'fxhash_data_auto_generated.csv'
    df.to_csv(csv_file_path, index=False)
    print(f"DataFrame has been successfully saved to {csv_file_path}")

    # Close the browser after processing
    driver.quit()

# Run the main function
if __name__ == "__main__":
    main()

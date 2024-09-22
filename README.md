FXHash Artwork Analyzer
This project automates the analysis of generative artworks on the FXHash platform. It retrieves data about artworks, including descriptions, IPFS links, p5.js versions, and additional libraries used in the artworks. The data is collected via the FXHash public API and web scraping techniques, and is saved in a CSV format for further analysis.

Features
Fetch Artwork Data: Retrieves artwork details from the FXHash public API based on artwork IDs.
IPFS Link Conversion: Converts IPFS links to HTTP format for easy access.
Library Detection: Extracts p5.js versions and other libraries used in the generative art code.
Data Storage: Saves collected data in a structured CSV file.
Web Scraping: Uses Selenium and BeautifulSoup to scrape additional information from artwork pages.
Requirements
1. Python 3.x
2. Required libraries:
3. selenium
4. webdriver-manager
5. beautifulsoup4
6. requests
7. pandas

from selenium import webdriver
import logging
import json
from datetime import datetime
from bbc_scraper import BBCNewsScraper
from cnn_scraper import CNNNewsScraper
from google_news_scraper import GoogleNewsScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsScraperManager:
    def __init__(self):
        self.setup_driver()
        self.scrapers = {
            'bbc': BBCNewsScraper(self.driver),
            'cnn': CNNNewsScraper(self.driver),
            'google': GoogleNewsScraper(self.driver)
        }
        self.results = {}

    def setup_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)
        logger.info("Browser initialized")

    def scrape_all(self, query: str, target_count: int = 200):
        try:
            for site, scraper in self.scrapers.items():
                logger.info(f"\nStarting scraping from {site.upper()}...")
                scraper.scrape(query, target_count)
                self.results[site] = scraper.results
                self.save_results(site)
                logger.info(f"Completed scraping from {site.upper()}")
                
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
        finally:
            self.driver.quit()

    def save_results(self, site: str):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{site}_news_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results[site], f, indent=2, ensure_ascii=False)
            
        logger.info(f"Results saved to {filename}")

def main():
    scraper = NewsScraperManager()
    query = input("Enter search query: ")
    target_count = int(input("Enter target number of articles per site (default 200): ") or "200")
    
    scraper.scrape_all(query, target_count)

if __name__ == "__main__":
    main() 
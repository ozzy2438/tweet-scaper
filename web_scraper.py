import logging
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup
import json
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self):
        self.setup_driver()
        self.results = {}

    def setup_driver(self):
        """Selenium driver'ı hazırla"""
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)
        logger.info("Browser initialized")

    def scrape_amazon(self, search_query: str, num_products: int = 50):
        """
        Amazon'dan ürün verilerini çek
        
        Args:
            search_query: Arama sorgusu
            num_products: Toplanacak ürün sayısı
        """
        try:
            # Amazon'a git ve arama yap
            url = f"https://www.amazon.com/s?k={search_query.replace(' ', '+')}"
            self.driver.get(url)
            time.sleep(2)
            
            products = []
            page = 1
            
            while len(products) < num_products:
                logger.info(f"Scraping page {page}")
                
                # Sayfadaki tüm ürünleri yükle
                self._scroll_page()
                
                # Ürün elementlerini bul
                product_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, 
                    "div[data-component-type='s-search-result']"
                )
                
                for product in product_elements:
                    if len(products) >= num_products:
                        break
                        
                    try:
                        product_data = self._extract_amazon_product(product)
                        if product_data:
                            products.append(product_data)
                            logger.info(f"Extracted product {len(products)}/{num_products}")
                    except Exception as e:
                        logger.error(f"Error extracting product: {str(e)}")
                        continue
                
                # Sonraki sayfa
                try:
                    next_button = self.driver.find_element(
                        By.CSS_SELECTOR, 
                        "a.s-pagination-next"
                    )
                    if not next_button.is_enabled():
                        break
                    next_button.click()
                    time.sleep(2)
                    page += 1
                except:
                    logger.info("No more pages available")
                    break
            
            self.results["amazon"] = products
            self._save_results()
            return products
            
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            return []

    def _extract_amazon_product(self, product_element) -> Optional[Dict]:
        """Amazon ürün elementinden veri çıkar"""
        try:
            # Ürünü görünür yap
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                product_element
            )
            time.sleep(0.5)
            
            # Temel bilgiler
            title = product_element.find_element(
                By.CSS_SELECTOR, 
                "h2 span.a-text-normal"
            ).text.strip()
            
            # Fiyat
            try:
                price = product_element.find_element(
                    By.CSS_SELECTOR,
                    "span.a-price-whole"
                ).text.strip()
                cents = product_element.find_element(
                    By.CSS_SELECTOR,
                    "span.a-price-fraction"
                ).text.strip()
                price = f"${price}.{cents}"
            except:
                price = "Price not available"
            
            # Rating
            try:
                rating = product_element.find_element(
                    By.CSS_SELECTOR,
                    "span.a-icon-alt"
                ).get_attribute("textContent")
            except:
                rating = None
            
            # Reviews count
            try:
                reviews = product_element.find_element(
                    By.CSS_SELECTOR,
                    "span.a-size-base.s-underline-text"
                ).text.strip()
            except:
                reviews = "0"
            
            # Image
            try:
                image = product_element.find_element(
                    By.CSS_SELECTOR,
                    "img.s-image"
                ).get_attribute("src")
            except:
                image = None
            
            # Link
            try:
                link = product_element.find_element(
                    By.CSS_SELECTOR,
                    "h2 a"
                ).get_attribute("href")
            except:
                link = None
            
            return {
                "title": title,
                "price": price,
                "rating": rating,
                "reviews_count": reviews,
                "image_url": image,
                "product_url": link
            }
            
        except Exception as e:
            logger.error(f"Error extracting product data: {str(e)}")
            return None

    def _scroll_page(self):
        """Sayfayı aşağı kaydır"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while True:
            # Scroll down
            self.driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1)
            
            # Yeni yüksekliği kontrol et
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def _save_results(self):
        """Sonuçları kaydet"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f'scraping_results_{timestamp}.json'
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {filename}")

    def close(self):
        """Browser'ı kapat"""
        if self.driver:
            self.driver.quit()

def main():
    scraper = WebScraper()
    try:
        # Amazon'dan laptop ara
        products = scraper.scrape_amazon("laptop", num_products=50)
        logger.info(f"Found {len(products)} products")
    finally:
        scraper.close()

if __name__ == "__main__":
    main()

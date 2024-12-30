import logging
import json
from datetime import datetime
from typing import Dict, Any, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import re
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EbayScraper:
    def __init__(self):
        self.driver = None
        self.search_query = "apple macbook"
        self.products = []
        self.base_url = "https://www.ebay.com"

    def setup_driver(self):
        logger.info("Opening eBay...")
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        self.driver = webdriver.Chrome(options=options)
        logger.info("Chrome driver successfully initialized")
        
        # Go to eBay main page
        self.driver.get(self.base_url)
        time.sleep(2)

    def extract_product_details(self, product_element) -> Dict[str, Any]:
        """Extract details from a product element"""
        try:
            # Basic product info
            product_link = product_element.find_element(By.CSS_SELECTOR, "a.s-item__link")
            url = product_link.get_attribute('href')
            product_id = re.search(r'/itm/(\d+)', url).group(1) if url else None
            
            title = product_element.find_element(By.CSS_SELECTOR, "div.s-item__title").text.strip()
            logger.info(f"Processing: {title}")
            
            # Price info
            try:
                price_elem = product_element.find_element(By.CSS_SELECTOR, "span.s-item__price")
                price = price_elem.text
                currency = "USD" if "$" in price else None
            except:
                price = "Price not available"
                currency = None
                
            # Seller info
            try:
                seller_elem = product_element.find_element(By.CSS_SELECTOR, "span.s-item__seller-info")
                seller_name = seller_elem.text
                seller_rating = re.search(r'(\d+\.?\d*)%', seller_elem.text).group(1) if "%" in seller_elem.text else None
                seller_reviews = re.search(r'\((\d+)\)', seller_elem.text).group(1) if "(" in seller_elem.text else None
            except:
                seller_name = "Unknown seller"
                seller_rating = None
                seller_reviews = None
                
            # Condition
            try:
                condition = product_element.find_element(By.CSS_SELECTOR, "span.SECONDARY_INFO").text
            except:
                condition = None
                
            # Shipping
            try:
                shipping_elem = product_element.find_element(By.CSS_SELECTOR, "span.s-item__shipping")
                shipping = shipping_elem.text
            except:
                shipping = None
                
            # Location
            try:
                location = product_element.find_element(By.CSS_SELECTOR, "span.s-item__location").text
            except:
                location = None
                
            # Click for more details
            product_link.click()
            time.sleep(2)
            
            # Get images
            images = []
            try:
                img_elements = self.driver.find_elements(By.CSS_SELECTOR, "img.img_image")
                for img in img_elements:
                    src = img.get_attribute('src')
                    if src and not src.endswith('gif'):
                        images.append(src)
            except:
                pass
                
            # Get specifications
            specs = []
            try:
                spec_table = self.driver.find_element(By.CSS_SELECTOR, "div.ux-labels-values")
                rows = spec_table.find_elements(By.CSS_SELECTOR, "div.ux-labels-values__labels-content")
                for row in rows:
                    name = row.find_element(By.CSS_SELECTOR, "div.ux-labels-values__labels").text
                    value = row.find_element(By.CSS_SELECTOR, "div.ux-labels-values__values").text
                    specs.append({
                        "specification_name": name,
                        "specification_value": value
                    })
            except:
                pass

            # Go back to results
            self.driver.back()
            time.sleep(1)
            
            return {
                "url": url,
                "product_id": product_id,
                "title": title,
                "price": price,
                "currency": currency,
                "condition": condition,
                "seller_name": seller_name,
                "seller_rating": seller_rating,
                "seller_reviews": seller_reviews,
                "shipping": shipping,
                "item_location": location,
                "images": images,
                "product_specifications": specs
            }
            
        except Exception as e:
            logger.error(f"Error extracting product details: {str(e)}")
            return None

    def perform_search(self):
        try:
            logger.info("Starting search...")
            logger.info(f"Search query: {self.search_query}")
            
            # Find and use search box
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "_nkw"))
            )
            search_box.clear()
            search_box.send_keys(self.search_query)
            search_box.send_keys(Keys.RETURN)
            time.sleep(3)
            
            # Wait for results
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ul.srp-results"))
            )
            
            # Process products
            products_found = 0
            target_products = 400
            page = 1
            
            while products_found < target_products:
                logger.info(f"Processing page {page}...")
                
                # Scroll down to load all products on the page
                last_height = self.driver.execute_script("return document.body.scrollHeight")
                while True:
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height
                
                # Find all products on current page
                product_elements = self.driver.find_elements(By.CSS_SELECTOR, "li.s-item")
                logger.info(f"Found {len(product_elements)} products on page {page}")
                
                for product in product_elements:
                    if products_found >= target_products:
                        break
                        
                    try:
                        # Scroll element into view
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", product)
                        time.sleep(0.5)
                        
                        # Extract basic info without clicking
                        product_data = self.extract_basic_info(product)
                        if product_data:
                            self.products.append(product_data)
                            products_found += 1
                            logger.info(f"Extracted product {products_found}/{target_products}")
                    except Exception as e:
                        logger.error(f"Error processing product: {str(e)}")
                        continue
                
                # Try next page if we need more products
                if products_found < target_products:
                    try:
                        next_button = self.driver.find_element(By.CSS_SELECTOR, "a.pagination__next")
                        if not next_button.is_displayed() or not next_button.is_enabled():
                            logger.info("No more pages available")
                            break
                        next_button.click()
                        time.sleep(2)
                        page += 1
                    except:
                        logger.info("No more pages available")
                        break
            
            self.save_products()
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}")

    def extract_basic_info(self, product_element) -> Dict[str, Any]:
        """Extract basic info without clicking into product details"""
        try:
            # Get product URL and ID
            product_link = product_element.find_element(By.CSS_SELECTOR, "a.s-item__link")
            url = product_link.get_attribute('href')
            product_id = re.search(r'/itm/(\d+)', url).group(1) if url else None
            
            # Get title
            title = product_element.find_element(By.CSS_SELECTOR, "div.s-item__title").text.strip()
            logger.info(f"Processing: {title}")
            
            # Get price
            try:
                price_elem = product_element.find_element(By.CSS_SELECTOR, "span.s-item__price")
                price = price_elem.text
                currency = "USD" if "$" in price else None
            except:
                price = "Price not available"
                currency = None
            
            # Get condition
            try:
                condition = product_element.find_element(By.CSS_SELECTOR, "span.SECONDARY_INFO").text
            except:
                condition = None
            
            # Get seller info
            try:
                seller_elem = product_element.find_element(By.CSS_SELECTOR, "span.s-item__seller-info")
                seller_name = seller_elem.text
                seller_rating = re.search(r'(\d+\.?\d*)%', seller_elem.text).group(1) if "%" in seller_elem.text else None
                seller_reviews = re.search(r'\((\d+)\)', seller_elem.text).group(1) if "(" in seller_elem.text else None
            except:
                seller_name = "Unknown seller"
                seller_rating = None
                seller_reviews = None
            
            # Get shipping
            try:
                shipping_elem = product_element.find_element(By.CSS_SELECTOR, "span.s-item__shipping")
                shipping = shipping_elem.text
            except:
                shipping = None
            
            # Get location
            try:
                location = product_element.find_element(By.CSS_SELECTOR, "span.s-item__location").text
            except:
                location = None
            
            return {
                "url": url,
                "product_id": product_id,
                "title": title,
                "price": price,
                "currency": currency,
                "condition": condition,
                "seller_name": seller_name,
                "seller_rating": seller_rating,
                "seller_reviews": seller_reviews,
                "shipping": shipping,
                "item_location": location
            }
            
        except Exception as e:
            logger.error(f"Error extracting basic info: {str(e)}")
            return None

    def save_products(self):
        """Save products to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ebay_products_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.products, f, indent=2, ensure_ascii=False)
            
        logger.info(f"{len(self.products)} products saved to {filename}")

    def run(self):
        try:
            self.setup_driver()
            self.perform_search()
        except Exception as e:
            logger.error(f"Error during execution: {str(e)}")
        finally:
            input("\nPress Enter to close the browser...")
            if self.driver:
                self.driver.quit()

def main():
    scraper = EbayScraper()
    scraper.run()

if __name__ == "__main__":
    main() 
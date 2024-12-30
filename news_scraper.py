from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import logging
import json
from datetime import datetime
import time
import re
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseNewsScraper:
    def __init__(self, driver):
        self.driver = driver
        self.results = []

    def _scroll_page(self):
        """Sayfayı yavaşça scroll et"""
        try:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            while True:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
        except Exception as e:
            logger.error(f"Scroll error: {str(e)}")

class BBCNewsScraper(BaseNewsScraper):
    def scrape(self, query: str, target_count: int = 200):
        try:
            articles_found = 0
            page = 1
            
            while articles_found < target_count:
                # BBC'nin arama URL yapısı
                url = f"https://www.bbc.co.uk/search?q={query}&page={page}"
                self.driver.get(url)
                time.sleep(3)
                
                # Sayfadaki makaleleri bul - BBC'nin doğru selektörü
                articles = self.driver.find_elements(By.CSS_SELECTOR, "div.ssrcss-1v7bxtk-StyledContainer")
                
                if not articles:
                    logger.info(f"No more articles found on page {page}")
                    break
                
                for article in articles:
                    try:
                        # Makale başlığı ve URL'ini al
                        article_link = article.find_element(By.CSS_SELECTOR, "a.ssrcss-1ynlzyd-PromoLink")
                        article_url = article_link.get_attribute("href")
                        
                        # Detay sayfasına git
                        self.driver.execute_script("window.open('');")
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        self.driver.get(article_url)
                        time.sleep(2)
                        
                        data = {
                            "id": str(uuid.uuid4().hex[:12]),
                            "url": article_url,
                            "headline": self._get_headline(),
                            "publication_date": self._get_publication_date(),
                            "content": self._get_content(),
                            "topics": self._get_topics(),
                            "author": self._get_author(),
                            "images": self._get_images(),
                            "related_articles": self._get_related_articles(),
                            "keyword": query
                        }
                        
                        # Ana pencereye geri dön
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                        
                        self.results.append(data)
                        articles_found += 1
                        logger.info(f"BBC News: Extracted {articles_found}/{target_count} from page {page}")
                        
                        if articles_found >= target_count:
                            break
                            
                    except Exception as e:
                        logger.error(f"Error extracting BBC article: {str(e)}")
                        continue
                
                # Sonraki sayfa kontrolü
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, "a[aria-label='Next page']")
                    if next_button and next_button.is_enabled():
                        page += 1
                    else:
                        logger.info("Reached last page")
                        break
                except:
                    logger.info("No more pages available")
                    break
                    
        except Exception as e:
            logger.error(f"BBC scraping error: {str(e)}")

    def _get_headline(self):
        try:
            return self.driver.find_element(By.CSS_SELECTOR, "h1#main-heading").text
        except:
            return None

    def _get_content(self):
        try:
            paragraphs = self.driver.find_elements(By.CSS_SELECTOR, "article p")
            return " ".join([p.text for p in paragraphs])
        except:
            return None

    def _get_publication_date(self):
        try:
            return self.driver.find_element(By.CSS_SELECTOR, "time").get_attribute("datetime")
        except:
            return None

    def _get_topics(self):
        topics = []
        try:
            topic_elements = self.driver.find_elements(By.CSS_SELECTOR, "a[data-testid='internal-link']")
            topics = [topic.text for topic in topic_elements if topic.text]
        except:
            pass
        return topics

    def _get_author(self):
        try:
            return self.driver.find_element(By.CSS_SELECTOR, "div[data-component='byline-block']").text
        except:
            return None

    def _get_images(self):
        images = []
        try:
            img_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.article-body img")
            for img in img_elements:
                images.append({
                    "image_description": img.get_attribute("alt"),
                    "image_url": img.get_attribute("src")
                })
        except:
            pass
        return images

    def _get_related_articles(self):
        related = []
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, "div.related-items a")
            for element in elements:
                related.append({
                    "article_title": element.text,
                    "article_url": element.get_attribute("href")
                })
        except:
            pass
        return related

class CNNNewsScraper(BaseNewsScraper):
    def scrape(self, query: str, target_count: int = 200):
        try:
            articles_found = 0
            page = 1
            size = 10
            
            while articles_found < target_count:
                # CNN'in arama URL yapısı
                url = f"https://edition.cnn.com/search?q={query}&from={(page-1)*size}&size={size}&page={page}&sort=newest&types=article"
                self.driver.get(url)
                time.sleep(3)
                
                # Arama sonuçlarını bul
                articles = self.driver.find_elements(By.CSS_SELECTOR, "div.cnn-search__result")
                
                if not articles:
                    logger.info(f"No more articles found on page {page}")
                    break
                
                for article in articles:
                    try:
                        # Makale URL'ini al
                        article_url = article.find_element(By.CSS_SELECTOR, "h3.cnn-search__result-headline a").get_attribute("href")
                        
                        # Detay sayfasına git
                        self.driver.execute_script("window.open('');")
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        self.driver.get(article_url)
                        time.sleep(2)
                        
                        data = {
                            "id": article_url,
                            "url": article_url,
                            "author": self._get_author(),
                            "headline": self._get_headline(),
                            "topics": self._get_topics(),
                            "publication_date": self._get_publication_date(),
                            "updated_last": self._get_updated_date(),
                            "content": self._get_content(),
                            "videos": None,
                            "images": self._get_images(),
                            "related_articles": self._get_related_articles(),
                            "keyword": query
                        }
                        
                        # Ana pencereye geri dön
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                        
                        self.results.append(data)
                        articles_found += 1
                        logger.info(f"CNN News: Extracted {articles_found}/{target_count} from page {page}")
                        
                        if articles_found >= target_count:
                            break
                            
                    except Exception as e:
                        logger.error(f"Error extracting CNN article: {str(e)}")
                        continue
                
                # Sonraki sayfa kontrolü
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, "div.pagination-bar button[data-testid='pagination-button-next']")
                    if next_button and next_button.is_enabled():
                        page += 1
                    else:
                        logger.info("Reached last page")
                        break
                except:
                    logger.info("No more pages available")
                    break
                    
        except Exception as e:
            logger.error(f"CNN scraping error: {str(e)}")

    def _get_author(self):
        try:
            author = self.driver.find_element(By.CSS_SELECTOR, "span.byline__name").text
            # Yıldızlarla gizleme işlemi
            parts = author.split()
            masked_parts = [p[:3] + "*" * (len(p)-3) + p[-3:] for p in parts]
            return " ".join(masked_parts)
        except:
            return None

    def _get_headline(self):
        try:
            return self.driver.find_element(By.CSS_SELECTOR, "h1.headline").text
        except:
            return None

    def _get_topics(self):
        try:
            topics = self.driver.find_elements(By.CSS_SELECTOR, "meta[property='article:section']")
            return [topic.get_attribute("content") for topic in topics]
        except:
            return []

    def _get_publication_date(self):
        try:
            return self.driver.find_element(By.CSS_SELECTOR, "meta[property='article:published_time']").get_attribute("content")
        except:
            return None

    def _get_updated_date(self):
        try:
            return self.driver.find_element(By.CSS_SELECTOR, "meta[property='article:modified_time']").get_attribute("content")
        except:
            return None

    def _get_content(self):
        try:
            paragraphs = self.driver.find_elements(By.CSS_SELECTOR, "div.article__content p")
            return " ".join([p.text for p in paragraphs])
        except:
            return None

    def _get_images(self):
        images = []
        try:
            img_containers = self.driver.find_elements(By.CSS_SELECTOR, "div.image__container")
            for container in img_containers:
                try:
                    images.append({
                        "image_description": container.find_element(By.CSS_SELECTOR, "div.image__caption").text,
                        "image_url": container.find_element(By.CSS_SELECTOR, "img").get_attribute("src")
                    })
                except:
                    continue
        except:
            pass
        return images

    def _get_related_articles(self):
        related = []
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, "div.related-content a")
            for element in elements:
                related.append({
                    "article_title": element.text,
                    "article_url": element.get_attribute("href")
                })
        except:
            pass
        return related

class ReutersNewsScraper(BaseNewsScraper):
    def scrape(self, query: str, target_count: int = 200):
        try:
            url = f"https://www.reuters.com/search/news?blob={query}"
            self.driver.get(url)
            time.sleep(3)
            
            articles_found = 0
            while articles_found < target_count:
                self._scroll_page()
                
                articles = self.driver.find_elements(By.CSS_SELECTOR, "div.search-result-content")
                for article in articles[:target_count]:
                    try:
                        data = {
                            "id": article.get_attribute("data-id") or str(uuid.uuid4().hex[:12]),
                            "url": article.find_element(By.CSS_SELECTOR, "a").get_attribute("href"),
                            "author": self._get_author(),
                            "headline": article.find_element(By.CSS_SELECTOR, "h3").text,
                            "topics": self._get_topics(article),
                            "publication_date": self._get_publication_date(),
                            "updated_last": self._get_update_date(),
                            "description": self._get_description(),
                            "content": self._get_full_content(),
                            "videos": None,
                            "images": self._get_images(),
                            "related_articles": self._get_related_articles(),
                            "keyword": query
                        }
                        
                        self.results.append(data)
                        articles_found += 1
                        logger.info(f"Reuters News: Extracted {articles_found}/{target_count}")
                        
                    except Exception as e:
                        logger.error(f"Error extracting Reuters article: {str(e)}")
                        continue
                        
        except Exception as e:
            logger.error(f"Reuters scraping error: {str(e)}")

class GoogleNewsScraper(BaseNewsScraper):
    def scrape(self, query: str, target_count: int = 200):
        try:
            url = f"https://news.google.com/search?q={query}"
            self.driver.get(url)
            time.sleep(3)
            
            articles_found = 0
            while articles_found < target_count:
                self._scroll_page()
                
                articles = self.driver.find_elements(By.CSS_SELECTOR, "article")
                for article in articles[:target_count]:
                    try:
                        data = {
                            "url": article.find_element(By.CSS_SELECTOR, "a").get_attribute("href"),
                            "title": article.find_element(By.CSS_SELECTOR, "h3").text,
                            "publisher": self._get_publisher(article),
                            "date": self._get_date(article),
                            "category": self._get_category(article),
                            "keyword": query,
                            "country": "US",
                            "image": self._get_image(article)
                        }
                        
                        self.results.append(data)
                        articles_found += 1
                        logger.info(f"Google News: Extracted {articles_found}/{target_count}")
                        
                    except Exception as e:
                        logger.error(f"Error extracting Google News article: {str(e)}")
                        continue
                        
        except Exception as e:
            logger.error(f"Google News scraping error: {str(e)}")

class NewsScraperManager:
    def __init__(self):
        self.setup_driver()
        self.scrapers = {
            'bbc': BBCNewsScraper(self.driver),
            'cnn': CNNNewsScraper(self.driver),
            'reuters': ReutersNewsScraper(self.driver),
            'google': GoogleNewsScraper(self.driver)
        }
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

    def scrape_all(self, query: str, target_count: int = 200):
        """Tüm haber sitelerinden veri çek"""
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
        """Sonuçları JSON dosyasına kaydet"""
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
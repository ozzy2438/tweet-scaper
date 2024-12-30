from base_news_scraper import BaseNewsScraper, logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
import time
import json
from selenium.webdriver.common.keys import Keys

class CNNNewsScraper(BaseNewsScraper):
    def __init__(self):
        # Driver'ı başlat
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)
        self.results = []
        logger.info("CNN Scraper initialized")

    def scrape(self, query: str, target_count: int = 200):
        try:
            articles_found = 0
            page = 1
            
            while articles_found < target_count:
                # CNN'in sayfalama yapısı
                from_param = (page - 1) * 10
                url = f"https://edition.cnn.com/search?q={query}&size=10&from={from_param}&page={page}&sort=newest&types=all&sections="
                self.driver.get(url)
                time.sleep(3)
                
                try:
                    # Sayfadaki makaleleri bul - Doğru selektörler
                    articles = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".cnn-search__results-list .cnn-search__result"))
                    )
                    
                    if not articles:
                        logger.info("No articles found on this page")
                        break
                        
                    logger.info(f"Found {len(articles)} articles on page {page}")
                    
                    for article in articles:
                        try:
                            # Makaleyi görünür yap
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", article)
                            time.sleep(1)
                            
                            # Makale bilgilerini al - Doğru selektörler
                            link = article.find_element(By.CSS_SELECTOR, ".cnn-search__result-headline a")
                            headline = link.text
                            article_url = link.get_attribute("href")
                            
                            # Tarih bilgisini al
                            try:
                                date = article.find_element(By.CSS_SELECTOR, ".cnn-search__result-publish-date").text
                            except:
                                date = None
                                
                            logger.info(f"Processing: {headline}")
                            
                            # Detay sayfasına git
                            self.driver.execute_script("window.open('');")
                            self.driver.switch_to.window(self.driver.window_handles[-1])
                            self.driver.get(article_url)
                            time.sleep(2)
                            
                            data = {
                                "id": article_url,
                                "url": article_url,
                                "author": self._get_author(),
                                "headline": headline,
                                "topics": self._get_topics(),
                                "publication_date": date or self._get_publication_date(),
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
                            logger.info(f"CNN News: Extracted {articles_found}/{target_count} articles")
                            
                            if articles_found >= target_count:
                                break
                                
                        except Exception as e:
                            logger.error(f"Error extracting article: {str(e)}")
                            continue
                    
                    # Hedef sayıya ulaşmadıysak sonraki sayfaya geç
                    if articles_found < target_count:
                        page += 1
                        logger.info(f"Moving to page {page}")
                    else:
                        break
                        
                except Exception as e:
                    logger.error(f"Error processing page {page}: {str(e)}")
                    logger.error(f"Full error: {str(e.__class__.__name__)}: {str(e)}")  # Daha detaylı hata mesajı
                    break
                
        except Exception as e:
            logger.error(f"CNN scraping error: {str(e)}")

    def _get_author(self):
        try:
            authors = self.driver.find_elements(By.CSS_SELECTOR, "div.byline__names span.byline__name")
            return ", ".join([author.text for author in authors])
        except:
            return None

    def _get_headline(self):
        try:
            return self.driver.find_element(By.CSS_SELECTOR, "h1.headline__text").text
        except:
            return None

    def _get_topics(self):
        try:
            topics = []
            topic_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.metadata span.metadata__item")
            for topic in topic_elements:
                if topic.text and topic.text not in topics:
                    topics.append(topic.text)
            return topics
        except:
            return []

    def _get_publication_date(self):
        try:
            return self.driver.find_element(By.CSS_SELECTOR, "div.timestamp").get_attribute("data-date")
        except:
            return None

    def _get_updated_date(self):
        try:
            update_element = self.driver.find_element(By.CSS_SELECTOR, "div.timestamp--updated")
            return update_element.get_attribute("data-date")
        except:
            return None

    def _get_content(self):
        try:
            paragraphs = self.driver.find_elements(By.CSS_SELECTOR, "div.article__content p")
            return " ".join([p.text for p in paragraphs if p.text])
        except:
            return None

    def _get_images(self):
        images = []
        try:
            image_containers = self.driver.find_elements(By.CSS_SELECTOR, "div.image__container")
            for container in image_containers:
                try:
                    image = {
                        "image_description": container.find_element(By.CSS_SELECTOR, "div.image__caption").text,
                        "image_url": container.find_element(By.CSS_SELECTOR, "img.image__picture").get_attribute("src")
                    }
                    images.append(image)
                except:
                    continue
        except:
            pass
        return images

    def _get_related_articles(self):
        related = []
        try:
            related_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.el__storyelement__related a")
            for element in related_elements:
                related.append({
                    "article_title": element.text,
                    "article_url": element.get_attribute("href")
                })
        except:
            pass
        return related 

    def close(self):
        """Driver'ı kapat"""
        if self.driver:
            self.driver.quit()
            logger.info("Driver closed")

def main():
    try:
        # Scraper'ı başlat
        scraper = CNNNewsScraper()
        
        # Kullanıcıdan girdi al
        query = input("Enter search query: ")
        target_count = int(input("Enter number of articles to scrape (default 200): ") or "200")
        
        # Scraping işlemini başlat
        logger.info(f"Starting to scrape CNN News for query: {query}")
        scraper.scrape(query, target_count)
        
        # Sonuçları kaydet
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"cnn_news_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(scraper.results, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Results saved to {filename}")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
    finally:
        # Driver'ı kapat
        scraper.close()

if __name__ == "__main__":
    main() 
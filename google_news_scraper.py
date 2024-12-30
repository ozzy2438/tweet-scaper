from base_news_scraper import BaseNewsScraper, logger
from selenium.webdriver.common.by import By
import time

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

    # Google News'in yardımcı metodları... 
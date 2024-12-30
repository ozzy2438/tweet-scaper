from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os
import random
from collections import defaultdict

class BBCNewsScraper:
    def __init__(self):
        self.setup_driver()
        self.results = []
        
    def setup_driver(self):
        """Tarayıcı ayarlarını yapılandır"""
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--remote-debugging-port=9222")
        
        # Mac için Chrome profil yolu
        user_home = os.path.expanduser('~')
        chrome_profile = os.path.join(user_home, "Library/Application Support/Google/Chrome")
        
        if os.path.exists(chrome_profile):
            chrome_options.add_argument(f"--user-data-dir={chrome_profile}")
            chrome_options.add_argument("--profile-directory=Default")
        
        # Bot tespitini engellemek için ek ayarlar
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        
        try:
            # Önce mevcut Chrome işlemlerini sonlandır
            os.system("pkill -f Chrome")
            time.sleep(2)
            
            # Chrome'u başlat
            service = Service("/opt/homebrew/bin/chromedriver")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 20)
            print("Browser initialized successfully")
            
        except Exception as e:
            print(f"\nChrome sürücüsü başlatılırken hata: {str(e)}")
            print("Alternatif yol deneniyor...")
            
            try:
                # Alternatif ayarlarla dene
                chrome_options = Options()
                chrome_options.add_argument("--start-maximized")
                chrome_options.add_argument("--remote-debugging-port=9222")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                
                service = Service("/opt/homebrew/bin/chromedriver")
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.wait = WebDriverWait(self.driver, 20)
                print("Browser initialized with alternative settings")
                
            except Exception as e:
                print(f"Chrome başlatılamadı: {str(e)}")
                raise

    def smooth_scroll(self):
        """Sayfayı daha doğal bir şekilde kaydır"""
        try:
            # Görünür pencere yüksekliğini al
            window_height = self.driver.execute_script("return window.innerHeight")
            # Toplam sayfa yüksekliğini al
            scroll_height = self.driver.execute_script("return document.documentElement.scrollHeight")
            
            # Küçük adımlarla kaydır
            current_position = self.driver.execute_script("return window.pageYOffset")
            scroll_step = window_height // 4  # Daha küçük adımlar
            
            target_position = min(current_position + window_height, scroll_height - window_height)
            
            while current_position < target_position:
                current_position = min(current_position + scroll_step, target_position)
                self.driver.execute_script(f"window.scrollTo(0, {current_position})")
                time.sleep(random.uniform(0.1, 0.3))  # Daha doğal görünen bekleme
                
        except Exception as e:
            print(f"Scroll hatası: {str(e)}")

    def extract_article_data(self, article):
        """Makale verilerini çıkar"""
        try:
            # Makale linkini ve başlığını al
            article_link = article.find_element(By.CSS_SELECTOR, "a.ssrcss-1mrs5ns-PromoLink")
            article_url = article_link.get_attribute("href")
            headline = article.find_element(By.CSS_SELECTOR, "p.ssrcss-6arcww-PromoHeadline").text.strip()
            
            # Detay sayfasına git
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(article_url)
            time.sleep(random.uniform(2, 4))
            
            data = {
                "url": article_url,
                "author": self._get_author(),
                "headline": headline,
                "topics": self._get_topics(),
                "publication_date": self._get_publication_date(),
                "content": self._get_content()
            }
            
            # Ana pencereye geri dön
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            
            return data
            
        except Exception as e:
            print(f"Error extracting article data: {str(e)}")
            return None

    def scrape(self, query: str = "Generative AI", target_count: int = 200):
        try:
            articles_found = 0
            processed_urls = set()
            page = 1
            
            while articles_found < target_count:
                # URL'yi oluştur
                encoded_query = query.replace(' ', '+')
                url = f"https://www.bbc.com/search?q={encoded_query}"
                if page > 1:
                    url += f"&page={page}"
                
                print(f"\nAccessing page {page}: {url}")
                
                try:
                    self.driver.get(url)
                    time.sleep(5)  # Sayfanın yüklenmesi için bekle
                    
                    # Önce ana container'ın yüklenmesini bekle
                    try:
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".ssrcss-1020bd1-Stack"))
                        )
                    except:
                        print("Main container not found, trying alternative selector...")
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "main"))
                        )
                    
                    # Scroll işlemi
                    scroll_count = 0
                    last_height = self.driver.execute_script("return document.documentElement.scrollHeight")
                    
                    while scroll_count < 5:  # En fazla 5 kez scroll yap
                        print(f"\nPerforming scroll {scroll_count + 1}/5")
                        
                        # Sayfayı parça parça scroll yap
                        current_height = 0
                        target_height = last_height / 4  # Sayfayı 4 parçada scroll et
                        
                        while current_height < last_height:
                            scroll_step = min(target_height, last_height - current_height)
                            self.driver.execute_script(f"window.scrollTo(0, {current_height + scroll_step})")
                            time.sleep(0.5)  # Her scroll adımında kısa bekle
                            current_height += scroll_step
                        
                        time.sleep(2)  # Yeni içeriğin yüklenmesi için bekle
                        
                        # Yeni yüksekliği kontrol et
                        new_height = self.driver.execute_script("return document.documentElement.scrollHeight")
                        
                        # Makaleleri bul
                        articles = self.driver.find_elements(By.CSS_SELECTOR, ".ssrcss-1v7bxtk-StyledContainer")
                        print(f"Found {len(articles)} articles after scroll")
                        
                        if new_height == last_height:
                            print("Reached end of page")
                            break
                            
                        last_height = new_height
                        scroll_count += 1
                    
                    # Tüm makaleleri topla
                    articles = self.driver.find_elements(By.CSS_SELECTOR, ".ssrcss-1v7bxtk-StyledContainer")
                    
                    if not articles:
                        print("No articles found on this page")
                        break
                    
                    print(f"\nProcessing {len(articles)} articles on page {page}")
                    
                    # Makaleleri işle
                    for article in articles:
                        try:
                            data = self.extract_article_data(article)
                            if data and data["url"] not in processed_urls:
                                processed_urls.add(data["url"])
                                self.results.append(data)
                                articles_found += 1
                                print(f"Extracted {articles_found}/{target_count} articles")
                                
                                if articles_found >= target_count:
                                    break
                        except Exception as e:
                            print(f"Error processing article: {str(e)}")
                            continue
                    
                    if articles_found >= target_count:
                        break
                    
                    # Sonraki sayfaya geç
                    page += 1
                    
                except Exception as e:
                    print(f"Error on page {page}: {str(e)}")
                    page += 1  # Hata alınsa da sonraki sayfaya geç
                    continue
                
        except Exception as e:
            print(f"Scraping error: {str(e)}")
        finally:
            self.save_results()

    def save_results(self):
        """Sonuçları dosyaya kaydet"""
        if self.results:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"bbc_news_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
                
            print(f"\nSuccessfully saved {len(self.results)} articles to {filename}")
        else:
            print("\nNo articles were scraped!")

    def _get_author(self):
        try:
            author = self.driver.find_element(By.CSS_SELECTOR, "div[data-component='byline-block']").text
            parts = author.split()
            masked_parts = [part[:3] + "*" * (len(part)-3) for part in parts]
            return " ".join(masked_parts)
        except:
            return None

    def _get_topics(self):
        topics = []
        try:
            topic_elements = self.driver.find_elements(By.CSS_SELECTOR, "li.ssrcss-1fh2k3v-MetadataItem")
            topics = [topic.text for topic in topic_elements if topic.text]
        except:
            pass
        return topics

    def _get_publication_date(self):
        try:
            time_element = self.driver.find_element(By.CSS_SELECTOR, "time")
            return time_element.get_attribute("datetime")
        except:
            return None

    def _get_content(self):
        try:
            article = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "article"))
            )
            paragraphs = article.find_elements(By.CSS_SELECTOR, "p")
            return " ".join([p.text for p in paragraphs if p.text])
        except:
            return None

def main():
    scraper = BBCNewsScraper()
    scraper.scrape()
    scraper.driver.quit()

if __name__ == "__main__":
    main() 
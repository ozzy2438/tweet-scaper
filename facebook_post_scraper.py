from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import json
import time
from datetime import datetime
import re

class FacebookPostScraper:
    def __init__(self, email, password):
        self.email = "osmanorka2410@yahoo.com"
        self.password = "osmanorka2410"
        self.setup_driver()
        
    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        
        try:
            service = Service("/opt/homebrew/bin/chromedriver")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 20)
            print("Browser başlatıldı")
        except Exception as e:
            print(f"Chrome başlatılamadı: {str(e)}")
            raise

    def login(self):
        try:
            self.driver.get("https://www.facebook.com")
            time.sleep(2)
            
            # Login
            email_input = self.wait.until(EC.presence_of_element_located((By.ID, "email")))
            email_input.send_keys(self.email)
            
            password_input = self.driver.find_element(By.ID, "pass")
            password_input.send_keys(self.password)
            password_input.send_keys(Keys.RETURN)
            
            time.sleep(5)  # Login için bekle
            print("Facebook'a giriş yapıldı")
            
        except Exception as e:
            print(f"Login hatası: {str(e)}")
            raise

    def scrape_page_posts(self, page_url, post_count=50):
        try:
            print(f"\n'{page_url}' sayfasından gönderiler toplanıyor...")
            self.driver.get(page_url)
            time.sleep(3)
            
            # Sayfa bilgilerini topla
            page_info = self.get_page_info()
            
            posts = []
            processed_posts = set()
            
            while len(posts) < post_count:
                # Scroll yap
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # Post kartlarını bul
                post_cards = self.driver.find_elements(By.CSS_SELECTOR, "div[role='article']")
                
                for card in post_cards:
                    try:
                        # Post ID'sini al
                        post_url = card.find_element(By.CSS_SELECTOR, "a[href*='/posts/']").get_attribute("href")
                        post_id = re.search(r'/posts/(\d+)', post_url).group(1)
                        
                        if post_id in processed_posts:
                            continue
                            
                        # Post detaylarını topla
                        post = {
                            'url': post_url,
                            'post_id': post_id,
                            'user_url': page_url,
                            'user_username_raw': page_info.get('page_name'),
                            'content': self.get_post_content(card),
                            'date_posted': self.get_post_date(card),
                            'hashtags': self.extract_hashtags(card),
                            'num_comments': self.get_interaction_count(card, 'comment'),
                            'num_shares': self.get_interaction_count(card, 'share'),
                            'num_likes_type': self.get_reactions(card),
                            'page_name': page_info.get('page_name'),
                            'page_intro': page_info.get('page_intro'),
                            'page_category': page_info.get('page_category'),
                            'page_logo': page_info.get('page_logo'),
                            'page_external_website': page_info.get('page_external_website'),
                            'page_likes': page_info.get('page_likes'),
                            'page_followers': page_info.get('page_followers'),
                            'page_is_verified': page_info.get('page_is_verified'),
                            'attachments': self.get_attachments(card),
                            'post_type': 'Post'
                        }
                        
                        posts.append(post)
                        processed_posts.add(post_id)
                        print(f"\rToplam {len(posts)} gönderi toplandı", end='', flush=True)
                        
                        if len(posts) >= post_count:
                            break
                            
                    except Exception as e:
                        continue
                        
                # Sayfa sonuna gelindi mi kontrol et
                if self.is_end_of_page():
                    break
                    
            # Sonuçları kaydet
            if posts:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"facebook_posts_{timestamp}.json"
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(posts, f, ensure_ascii=False, indent=2)
                
                print(f"\n\nVeriler kaydedildi: {filename}")
                print(f"Toplam {len(posts)} gönderi toplandı")
                
        except Exception as e:
            print(f"\nHata oluştu: {str(e)}")
            
        finally:
            self.driver.quit()
            
    def get_page_info(self):
        """Sayfa bilgilerini topla"""
        try:
            return {
                'page_name': self.get_text("h1"),
                'page_intro': self.get_text("div[data-key='page_intro']"),
                'page_category': self.get_text("div[data-key='page_category']"),
                'page_logo': self.get_attribute("img.x1rg5ohu", "src"),
                'page_external_website': self.get_attribute("a[data-key='page_website']", "href"),
                'page_likes': self.extract_number(self.get_text("div[data-key='page_likes']")),
                'page_followers': self.extract_number(self.get_text("div[data-key='page_followers']")),
                'page_is_verified': bool(self.driver.find_elements(By.CSS_SELECTOR, "div[aria-label='Verified']"))
            }
        except:
            return {}
            
    def get_post_content(self, card):
        """Post içeriğini al"""
        try:
            return card.find_element(By.CSS_SELECTOR, "div[data-ad-preview='message']").text
        except:
            return None
            
    def get_post_date(self, card):
        """Post tarihini al ve ISO formatına çevir"""
        try:
            date_element = card.find_element(By.CSS_SELECTOR, "a[href*='/posts/'] span")
            return self.parse_facebook_date(date_element.text)
        except:
            return None
            
    def get_attachments(self, card):
        """Post eklerini topla"""
        attachments = []
        try:
            media_elements = card.find_elements(By.CSS_SELECTOR, "a[href*='photo'], a[href*='video']")
            for element in media_elements:
                attachment = {
                    'id': element.get_attribute("href").split('/')[-1],
                    'type': 'Photo' if 'photo' in element.get_attribute("href") else 'Video',
                    'url': element.get_attribute("href"),
                    'video_url': None
                }
                attachments.append(attachment)
        except:
            pass
        return attachments
            
    def get_reactions(self, card):
        """Beğeni ve tepki sayılarını al"""
        try:
            reactions = card.find_element(By.CSS_SELECTOR, "span[role='toolbar']")
            count = self.extract_number(reactions.text)
            return {'num': count, 'type': 'Like'}
        except:
            return {'num': 0, 'type': 'Like'}
            
    def extract_hashtags(self, text):
        """Metinden hashtag'leri çıkar"""
        if not text:
            return None
        hashtags = re.findall(r'#\w+', text)
        return hashtags if hashtags else None
        
    def get_interaction_count(self, card, interaction_type):
        """Yorum ve paylaşım sayılarını al"""
        try:
            selector = f"span[data-testid='{interaction_type}s']"
            element = card.find_element(By.CSS_SELECTOR, selector)
            return self.extract_number(element.text)
        except:
            return 0
            
    def is_end_of_page(self):
        """Sayfa sonuna gelinip gelinmediğini kontrol et"""
        old_height = self.driver.execute_script("return document.body.scrollHeight")
        time.sleep(2)
        new_height = self.driver.execute_script("return document.body.scrollHeight")
        return old_height == new_height
        
    def get_text(self, selector):
        """CSS seçici ile element metnini al"""
        try:
            return self.driver.find_element(By.CSS_SELECTOR, selector).text
        except:
            return None
            
    def get_attribute(self, selector, attribute):
        """CSS seçici ile element özelliğini al"""
        try:
            return self.driver.find_element(By.CSS_SELECTOR, selector).get_attribute(attribute)
        except:
            return None
            
    def extract_number(self, text):
        """Metinden sayı çıkar"""
        if not text:
            return 0
        match = re.search(r'[\d,]+', text)
        return int(match.group().replace(',', '')) if match else 0
        
    def parse_facebook_date(self, date_text):
        """Facebook tarih formatını ISO formatına çevir"""
        try:
            # Facebook'un göreceli tarihlerini işle
            now = datetime.now()
            if 'hr' in date_text:
                hours = int(date_text.split()[0])
                date = now.replace(hour=now.hour - hours)
            elif 'min' in date_text:
                minutes = int(date_text.split()[0])
                date = now.replace(minute=now.minute - minutes)
            else:
                # Diğer tarih formatları için...
                date = now
            return date.isoformat()
        except:
            return None

def main():
    email = "your_email@example.com"  # Facebook email
    password = "your_password"  # Facebook password
    page_url = "https://www.facebook.com/example.page"  # Hedef sayfa URL'si
    
    scraper = FacebookPostScraper(email, password)
    scraper.login()
    scraper.scrape_page_posts(page_url, post_count=50)

if __name__ == "__main__":
    main() 
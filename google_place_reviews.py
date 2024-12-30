from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import pandas as pd
import time
import random
from datetime import datetime
import json

class GooglePlaceReviewScraper:
    def __init__(self):
        self.setup_driver()
        
    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
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

    def scrape_place_reviews(self, place_name, target_count=400):
        try:
            print(f"\n'{place_name}' için yorumlar toplanıyor...")
            
            # Google Maps'te mekanı ara
            self.driver.get("https://www.google.com/maps")
            time.sleep(2)
            
            search_box = self.wait.until(EC.presence_of_element_located((By.NAME, "q")))
            search_box.clear()
            search_box.send_keys(place_name)
            search_box.send_keys(Keys.RETURN)
            time.sleep(3)
            
            # İlk sonuca tıkla
            first_result = self.wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, "div.Nv2PK"
            )))
            first_result.click()
            time.sleep(3)

            reviews = []
            last_review_count = 0
            no_new_reviews = 0
            
            print("\nYorumlar yükleniyor...")
            
            # Ana scroll container'ı bul
            main_container = self.wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR, "div.m6QErb"
            )))
            
            while len(reviews) < target_count and no_new_reviews < 5:
                # Ana container'da scroll yap
                self.driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight", 
                    main_container
                )
                time.sleep(2)
                
                # Tüm review kartlarını bul
                review_cards = main_container.find_elements(
                    By.CSS_SELECTOR, 
                    "div.jftiEf"  # Review kartlarının ana class'ı
                )
                
                if len(review_cards) > last_review_count:
                    # Sadece yeni kartları işle
                    for card in review_cards[last_review_count:]:
                        try:
                            # Her karta scroll yap
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", card)
                            time.sleep(0.3)
                            
                            # "Daha fazla" butonuna tıkla
                            try:
                                more_button = card.find_element(By.CSS_SELECTOR, "button.w8nwRe")
                                self.driver.execute_script("arguments[0].click();", more_button)
                                time.sleep(0.3)
                            except:
                                pass
                            
                            review = {
                                'author': card.find_element(By.CSS_SELECTOR, "div.d4r55").text,
                                'rating': len(card.find_elements(By.CSS_SELECTOR, "span.kvMYJc img[src*='star_']")),
                                'date': card.find_element(By.CSS_SELECTOR, "span.rsqaWe").text,
                                'text': card.find_element(By.CSS_SELECTOR, "span.wiI7pd").text
                            }
                            
                            # Yorum fotoğrafları varsa ekle
                            try:
                                images = card.find_elements(By.CSS_SELECTOR, "button[jsaction*='click:markReviewHelpful'] img")
                                review['images'] = [img.get_attribute("src") for img in images]
                            except:
                                review['images'] = []
                                
                            # İşletme yanıtı varsa ekle
                            try:
                                owner_reply = card.find_element(By.CSS_SELECTOR, "div.d4r55 + div.wiI7pd").text
                                review['owner_reply'] = owner_reply
                            except:
                                review['owner_reply'] = None
                            
                            reviews.append(review)
                            print(f"\rToplam {len(reviews)} yorum toplandı", end='', flush=True)
                            
                            if len(reviews) >= target_count:
                                break
                                
                        except Exception as e:
                            continue
                    
                    last_review_count = len(review_cards)
                    no_new_reviews = 0
                else:
                    no_new_reviews += 1
                    time.sleep(1)
                    
                # Scroll pozisyonunu kontrol et
                scroll_height = self.driver.execute_script("return arguments[0].scrollHeight", main_container)
                scroll_position = self.driver.execute_script("return arguments[0].scrollTop", main_container)
                
                # Sayfa sonuna gelindiyse ve yeni yorum yoksa çık
                if scroll_position + main_container.size['height'] >= scroll_height and no_new_reviews >= 3:
                    print("\nTüm yorumlar yüklendi")
                    break
            
            # Sonuçları kaydet
            if reviews:
                result = {
                    'place_info': {
                        'name': place_name,
                        'total_reviews': last_review_count
                    },
                    'reviews': reviews
                }
                
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"google_reviews_{timestamp}.json"
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                print(f"\n\nVeriler kaydedildi: {filename}")
                print(f"Toplam {len(reviews)} yorum toplandı")
                
        except Exception as e:
            print(f"\nHata oluştu: {str(e)}")
        
        finally:
            self.driver.quit()
            
    def get_place_info(self):
        """Mekan bilgilerini topla"""
        try:
            return {
                'title': self.driver.find_element(By.CSS_SELECTOR, 'h1.DUwDvf').text,
                'address': self.driver.find_element(By.CSS_SELECTOR, 'button[data-item-id="address"]').text,
                'rating': float(self.driver.find_element(By.CSS_SELECTOR, 'div.F7nice').text.split()[0]),
                'reviews': int(self.driver.find_element(By.CSS_SELECTOR, 'div.F7nice').text.split()[1].replace('(', '').replace(')', ''))
            }
        except:
            return {}
            
    def extract_topics(self, reviews):
        """Yorumlardan konuları çıkar"""
        from collections import Counter
        words = []
        for review in reviews:
            words.extend(review['body'].lower().split())
        
        # En çok geçen kelimeleri bul
        common_words = Counter(words).most_common(10)
        return [{'keyword': word, 'mentions': count} for word, count in common_words]
        
    def print_statistics(self, result):
        """İstatistikleri göster"""
        reviews = result['place_reviews_results']
        ratings = [r['rating'] for r in reviews]
        
        print("\nPuan İstatistikleri:")
        print(f"Ortalama Puan: {sum(ratings)/len(ratings):.1f}")
        print(f"5 Yıldız: {ratings.count(5)}")
        print(f"4 Yıldız: {ratings.count(4)}")
        print(f"3 Yıldız: {ratings.count(3)}")
        print(f"2 Yıldız: {ratings.count(2)}")
        print(f"1 Yıldız: {ratings.count(1)}")
        
        print("\nPopüler Konular:")
        for topic in result['topics'][:5]:
            print(f"{topic['keyword']}: {topic['mentions']} kez")

def main():
    scraper = GooglePlaceReviewScraper()
    place_name = "Slice Pizza New York"  # İstediğiniz mekanın adını girin
    target_count = 400
    scraper.scrape_place_reviews(place_name, target_count)

if __name__ == "__main__":
    main() 
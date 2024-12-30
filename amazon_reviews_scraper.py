from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import json
import time
import re
from datetime import datetime

class AmazonReviewScraper:
    def __init__(self):
        self.setup_driver()
        
    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-automation")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        try:
            service = Service("/opt/homebrew/bin/chromedriver")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 30)
            self.driver.implicitly_wait(10)
            print("Browser başlatıldı")
        except Exception as e:
            print(f"Chrome başlatılamadı: {str(e)}")
            raise

    def scrape_product_reviews(self, query="macbook pro m4", target_count=800):
        try:
            print(f"\n'{query}' için ürünler aranıyor...")
            
            # Önce amazon.com ana sayfasına git ve bölge seçimini yap
            self.driver.get("https://www.amazon.com")
            time.sleep(3)
            
            try:
                # Bölge popup'ı varsa kapat
                self.driver.find_element(By.ID, "nav-global-location-popover-link").click()
                time.sleep(2)
                # US seç
                self.driver.find_element(By.CSS_SELECTOR, "input[data-action='GLUXPostalInputAction']").send_keys("10001")
                time.sleep(1)
                self.driver.find_element(By.CSS_SELECTOR, "span[data-action='GLUXPostalInputAction']").click()
                time.sleep(2)
            except:
                pass  # Popup yoksa devam et
            
            # Arama yap
            search_box = self.wait.until(EC.presence_of_element_located((
                By.ID, "twotabsearchtextbox"
            )))
            search_box.clear()
            search_box.send_keys(query)
            search_box.send_keys(Keys.RETURN)
            time.sleep(5)
            
            # İlk ürüne tıkla
            first_product = self.wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, ".s-result-item div[data-component-type='s-search-result'] h2 a"
            )))
            product_url = first_product.get_attribute("href")
            first_product.click()
            time.sleep(3)

            # Tüm yorumları gör butonuna tıkla
            see_all_reviews = self.wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, "a[data-hook='see-all-reviews-link-foot']"
            )))
            see_all_reviews.click()
            time.sleep(3)

            reviews = []
            page = 1
            
            while len(reviews) < target_count:
                print(f"\nSayfa {page} işleniyor...")
                
                # Sayfadaki tüm yorumları topla
                review_cards = self.wait.until(EC.presence_of_all_elements_located((
                    By.CSS_SELECTOR, "div[data-hook='review']"
                )))
                
                # Her yorumu işle
                for card in review_cards:
                    try:
                        review_data = {
                            'url': product_url,
                            'review_id': card.get_attribute("id"),
                            'rating': len(card.find_elements(By.CSS_SELECTOR, "i[class*='a-star-']")),
                            'review_text': card.find_element(By.CSS_SELECTOR, "span[data-hook='review-body']").text,
                            'review_header': card.find_element(By.CSS_SELECTOR, "a[data-hook='review-title']").text,
                            'author_name': card.find_element(By.CSS_SELECTOR, "span.a-profile-name").text,
                            'review_date': card.find_element(By.CSS_SELECTOR, "span[data-hook='review-date']").text
                        }
                        reviews.append(review_data)
                        print(f"\rToplanan yorum sayısı: {len(reviews)}", end='', flush=True)
                        
                        if len(reviews) >= target_count:
                            break
                            
                    except Exception as e:
                        continue
                
                # Sonraki sayfaya geç
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, "li.a-last a")
                    if "a-disabled" not in next_button.get_attribute("class"):
                        next_button.click()
                        time.sleep(3)
                        page += 1
                    else:
                        print("\nSon sayfaya ulaşıldı")
                        break
                except:
                    print("\nDaha fazla sayfa yok")
                    break

            # Sonuçları kaydet
            if reviews:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"amazon_reviews_{timestamp}.json"
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(reviews, f, ensure_ascii=False, indent=2)
                
                print(f"\n\nVeriler kaydedildi: {filename}")
                print(f"Toplam {len(reviews)} yorum toplandı")
                
        except Exception as e:
            print(f"\nHata oluştu: {str(e)}")
        finally:
            self.driver.quit()
            
    def get_product_info(self):
        """Ürün bilgilerini topla"""
        try:
            info = {
                'name': self.wait.until(EC.presence_of_element_located((
                    By.CSS_SELECTOR, "span#productTitle"
                ))).text.strip(),
                
                'brand': self.get_text("a#bylineInfo") or self.get_text("a#brand"),
                
                'rating': float(self.get_text("span.a-icon-alt").split()[0]),
                
                'total_ratings': int(self.get_text("span#acrCustomerReviewText")
                    .replace(',', '').split()[0]),
                
                'rating_breakdown': self.get_rating_breakdown()
            }
            return info
        except:
            return {}
            
    def get_rating_breakdown(self):
        """Yıldız dağılımını al"""
        try:
            breakdown = {}
            ratings_table = self.driver.find_element(By.ID, "histogramTable")
            rows = ratings_table.find_elements(By.CSS_SELECTOR, "tr")
            
            for row in rows:
                stars = row.find_element(By.CSS_SELECTOR, "a").text.split()[0]
                count = int(row.find_element(By.CSS_SELECTOR, "a[title]")
                    .get_attribute("title").split()[0].replace(',', ''))
                    
                if stars == "5":
                    breakdown['five_star'] = count
                elif stars == "4":
                    breakdown['four_star'] = count
                elif stars == "3":
                    breakdown['three_star'] = count
                elif stars == "2":
                    breakdown['two_star'] = count
                elif stars == "1":
                    breakdown['one_star'] = count
                    
            return breakdown
        except:
            return {}
            
    def get_review_title(self, card):
        return self.get_element_text(card, "a[data-hook='review-title']")
        
    def get_review_text(self, card):
        return self.get_element_text(card, "span[data-hook='review-body']")
        
    def get_review_rating(self, card):
        try:
            rating_text = card.find_element(By.CSS_SELECTOR, 
                "i[data-hook='review-star-rating']").get_attribute("class")
            return int(re.search(r'a-star-(\d)', rating_text).group(1))
        except:
            return None
            
    def get_review_date(self, card):
        return self.get_element_text(card, "span[data-hook='review-date']")
        
    def get_author_name(self, card):
        name = self.get_element_text(card, "span.a-profile-name")
        return self.mask_name(name) if name else None
        
    def get_author_id(self, card):
        try:
            profile_link = card.find_element(By.CSS_SELECTOR, "a.a-profile")
            return re.search(r'account\.(.+?)/', profile_link.get_attribute("href")).group(1)
        except:
            return None
            
    def get_author_link(self, card):
        return self.get_element_attribute(card, "a.a-profile", "href")
        
    def get_helpful_count(self, card):
        try:
            helpful_text = self.get_element_text(card, "span[data-hook='helpful-vote-statement']")
            return int(re.search(r'(\d+)', helpful_text).group(1))
        except:
            return 0
            
    def get_review_images(self, card):
        try:
            images = card.find_elements(By.CSS_SELECTOR, "img[data-hook='review-image']")
            return [img.get_attribute("src") for img in images]
        except:
            return None
            
    def get_badge(self, card):
        return self.get_element_text(card, "span[data-hook='avp-badge']")
        
    def is_verified_purchase(self, card):
        return bool(card.find_elements(By.CSS_SELECTOR, "span[data-hook='avp-badge']"))
        
    def is_vine_review(self, card):
        return "Vine Customer Review" in card.text
        
    def go_to_next_page(self):
        """Sonraki sayfaya git"""
        try:
            next_button = self.driver.find_element(By.CSS_SELECTOR, "li.a-last a")
            if "a-disabled" not in next_button.get_attribute("class"):
                next_button.click()
                time.sleep(2)
                return True
            return False
        except:
            return False
            
    def get_element_text(self, element, selector):
        """Element metnini güvenli şekilde al"""
        try:
            return element.find_element(By.CSS_SELECTOR, selector).text.strip()
        except:
            return None
            
    def get_element_attribute(self, element, selector, attribute):
        """Element özelliğini güvenli şekilde al"""
        try:
            return element.find_element(By.CSS_SELECTOR, selector).get_attribute(attribute)
        except:
            return None
            
    def extract_asin(self, url):
        """URL'den ASIN'i çıkar"""
        try:
            return re.search(r'/dp/([A-Z0-9]{10})', url).group(1)
        except:
            return None
            
    def mask_name(self, name):
        """İsmi maskele"""
        if not name:
            return None
        parts = name.split()
        return "***".join(p[:1] + p[-1:] for p in parts)

def main():
    scraper = AmazonReviewScraper()
    scraper.scrape_product_reviews()  # Varsayılan olarak "macbook pro m4" araması yapacak

if __name__ == "__main__":
    main() 
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
import hashlib

class YouTubeChannelScraper:
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
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        
        try:
            service = Service("/opt/homebrew/bin/chromedriver")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 30)
            self.driver.implicitly_wait(10)
            print("Browser başlatıldı")
        except Exception as e:
            print(f"Chrome başlatılamadı: {str(e)}")
            raise

    def search_channels(self, query="Generative AI", max_channels=200):
        """Verilen sorgu için YouTube kanallarını ara ve temel bilgileri topla"""
        try:
            search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
            self.driver.get(search_url)
            time.sleep(5)
            
            print(f"\n'{query}' için kanallar aranıyor...")
            
            channels_data = []
            scroll_count = 0
            max_scrolls = 50
            
            while len(channels_data) < max_channels and scroll_count < max_scrolls:
                try:
                    # Scroll yap
                    self.driver.execute_script("window.scrollBy(0, 1000);")
                    time.sleep(2)
                    
                    # Video kartlarını bul (kanal bilgileri burada)
                    video_elements = self.driver.find_elements(
                        By.CSS_SELECTOR, 
                        "ytd-video-renderer"
                    )
                    
                    for element in video_elements:
                        try:
                            channel_data = {}
                            
                            # Kanal URL ve handle
                            channel_link = element.find_element(
                                By.CSS_SELECTOR, 
                                "a.yt-formatted-string[href*='/@']"
                            )
                            channel_url = channel_link.get_attribute("href")
                            handle = channel_url.split('/@')[-1]
                            
                            # Eğer bu kanal daha önce eklendiyse atla
                            if any(c["handle"] == handle for c in channels_data):
                                continue
                            
                            channel_data["url"] = channel_url
                            channel_data["handle"] = f"@{handle}"
                            
                            # Kanal adı
                            channel_data["name"] = channel_link.text
                            
                            # Abone sayısı
                            try:
                                subscriber_element = element.find_element(
                                    By.CSS_SELECTOR, 
                                    "span.ytd-video-meta-block"
                                )
                                channel_data["subscribers"] = self._convert_subscriber_count(subscriber_element.text)
                            except:
                                channel_data["subscribers"] = 0
                            
                            # Video sayısı ve görüntülenme
                            try:
                                meta_elements = element.find_elements(
                                    By.CSS_SELECTOR, 
                                    "span.inline-metadata-item"
                                )
                                for meta in meta_elements:
                                    text = meta.text.lower()
                                    if 'video' in text:
                                        channel_data["videos_count"] = int(''.join(filter(str.isdigit, text)))
                                    elif 'view' in text:
                                        channel_data["views"] = int(''.join(filter(str.isdigit, text)))
                            except:
                                channel_data["videos_count"] = 0
                                channel_data["views"] = 0
                            
                            # Açıklama
                            try:
                                description = element.find_element(
                                    By.CSS_SELECTOR, 
                                    "yt-formatted-string.metadata-snippet-text"
                                ).text
                                channel_data["Description"] = description
                            except:
                                channel_data["Description"] = None
                            
                            channels_data.append(channel_data)
                            print(f"Kanal bulundu ({len(channels_data)}): {channel_data['name']}")
                            
                            if len(channels_data) >= max_channels:
                                print("\nHedef kanal sayısına ulaşıldı!")
                                return channels_data
                                
                        except Exception as e:
                            print(f"Veri çıkarma hatası: {str(e)}")
                            continue
                    
                    scroll_count += 1
                    
                except Exception as e:
                    print(f"Scroll sırasında hata: {str(e)}")
                    continue
            
            print(f"\nToplam {len(channels_data)} kanal bulundu.")
            return channels_data
            
        except Exception as e:
            print(f"Arama hatası: {str(e)}")
            return []

    def _convert_subscriber_count(self, sub_text):
        """Abone sayısını metinden sayıya çevir"""
        try:
            if not sub_text:
                return 0
                
            # "1.2M subscribers" gibi metni sayıya çevir
            number = float(re.search(r'[\d.]+', sub_text).group())
            multiplier = {
                'K': 1000,
                'M': 1000000,
                'B': 1000000000
            }.get(sub_text[-1].upper(), 1)
            
            return int(number * multiplier)
        except:
            return 0

    def scrape_channel_info(self, query="Generative AI", max_channels=200):
        """Ana scraping fonksiyonu"""
        try:
            # Kanal bilgilerini topla
            channels_data = self.search_channels(query, max_channels)
            
            # Sonuçları kaydet
            if channels_data:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"youtube_channels_{query}_{timestamp}.json"
                
                results = {
                    "query": query,
                    "timestamp": timestamp,
                    "channel_count": len(channels_data),
                    "channels": channels_data
                }
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                
                print(f"\nVeriler kaydedildi: {filename}")
                print(f"Toplam {len(channels_data)} kanal bilgisi toplandı")
                
        except Exception as e:
            print(f"\nHata oluştu: {str(e)}")
        finally:
            self.driver.quit()

def main():
    scraper = YouTubeChannelScraper()
    # Generative AI ile ilgili kanalları tara
    scraper.scrape_channel_info(query="Generative AI", max_channels=200)

if __name__ == "__main__":
    main() 
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from collections import defaultdict
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys
import getpass
import random
import os

class SmartScraper:
    def __init__(self):
        self.setup_driver()
        self.all_data = defaultdict(list)
        
    def setup_driver(self):
        """Tarayıcı ayarlarını yapılandır"""
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-notifications")
        
        # Mac için Chrome profil yolu
        user_home = os.path.expanduser('~')  # Kullanıcı klasörünü otomatik bul
        chrome_profile = os.path.join(user_home, "Library/Application Support/Google/Chrome")
        
        if os.path.exists(chrome_profile):
            chrome_options.add_argument(f"--user-data-dir={chrome_profile}")
            chrome_options.add_argument("--profile-directory=Default")
        else:
            print("\nChrome profili bulunamadı. Yeni profil oluşturuluyor...")
        
        # Bot tespitini engellemek için ek ayarlar
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # User agent değiştir
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            service = Service("/opt/homebrew/bin/chromedriver")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            print(f"\nChrome sürücüsü başlatılırken hata: {str(e)}")
            print("Alternatif yol deneniyor...")
            try:
                # Alternatif olarak yeni profil oluştur
                chrome_options = Options()
                chrome_options.add_argument("--start-maximized")
                service = Service("/opt/homebrew/bin/chromedriver")
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e:
                print(f"Chrome başlatılamadı: {str(e)}")
                raise
        
        self.wait = WebDriverWait(self.driver, 20)
    
    def scroll_to_bottom(self):
        print("\nScrolling to load all content...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        max_scrolls = 10
        
        while scroll_count < max_scrolls:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            scroll_count += 1
            print("Loading more content...")

    def click_next_page(self):
        """Try different methods to find and click the next page button"""
        try:
            # Try URL parameter modification first
            current_url = self.driver.current_url
            
            # Check if we're on page 1 (no page parameter)
            if 'page=' not in current_url:
                if '#/?' in current_url:
                    next_url = current_url.replace('#/?', '#/?page=2&')
                else:
                    next_url = current_url + ('&' if '?' in current_url else '?') + 'page=2'
                print(f"\nTrying URL modification: {next_url}")
                self.driver.get(next_url)
                time.sleep(3)
                return True
            
            # If already on a page number
            if 'page=' in current_url:
                current_page = int(re.search(r'page=(\d+)', current_url).group(1))
                next_url = re.sub(r'page=\d+', f'page={current_page + 1}', current_url)
                print(f"\nTrying URL modification: {next_url}")
                self.driver.get(next_url)
                time.sleep(3)
                return True
            
            # Try finding numbered page links
            page_patterns = [
                f"//a[text()='{i}']" for i in range(2, 6)
            ]
            
            for pattern in page_patterns:
                try:
                    page_link = self.driver.find_element(By.XPATH, pattern)
                    if page_link.is_displayed() and page_link.is_enabled():
                        print(f"\nFound page link: {pattern}")
                        try:
                            # Try JavaScript click
                            self.driver.execute_script("arguments[0].click();", page_link)
                        except Exception as e1:
                            try:
                                # Try regular click
                                page_link.click()
                            except Exception as e2:
                                continue
                        time.sleep(3)
                        return True
                except NoSuchElementException:
                    continue
            
            return False
            
        except Exception as e:
            print(f"Error navigating to next page: {str(e)}")
            return False

    def get_similar_keywords(self, keyword):
        """Get list of similar keywords based on common variations"""
        keyword = keyword.lower()
        
        
        for key, values in variations.items():
            if keyword in values or key.startswith(keyword):
                return values
        return [keyword]

    def find_elements_by_keywords(self, keywords, soup):
        """Find elements that match any of the given keywords"""
        elements = []
        
        all_keywords = []
        for keyword in keywords:
            all_keywords.extend(self.get_similar_keywords(keyword))
        
        all_keywords = [k.lower() for k in all_keywords]
        
        if 'date' in all_keywords:
            time_elements = soup.find_all(['time'])
            elements.extend(time_elements)
            
        if 'source' in all_keywords or 'author' in all_keywords:
            meta_elements = soup.find_all('meta', attrs={'name': ['author', 'publisher', 'source']})
            elements.extend(meta_elements)
        
        for element in soup.find_all(['div', 'span', 'p', 'h1', 'h2', 'h3', 'h4', 'a', 'article']):
            if not element.text.strip():
                continue
            
            classes = ' '.join(element.get('class', [])).lower()
            element_id = element.get('id', '').lower()
            data_attrs = ' '.join([v for k, v in element.attrs.items() if k.startswith('data-')]).lower()
            
            if 'date' in all_keywords:
                date_pattern = r'\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}'
                if re.search(date_pattern, element.text, re.I):
                    elements.append(element)
                    continue
            
            element_text = element.text.lower()
            for keyword in all_keywords:
                if (keyword in classes or 
                    keyword in element_id or 
                    keyword in data_attrs or
                    keyword in element_text):
                    if element not in elements:
                        elements.append(element)
                        break
        
        return elements

    def clean_text(self, text):
        """Clean extracted text"""
        text = ' '.join(text.split())
        if len(text) > 500:
            text = text[:497] + "..."
        return text

    def extract_data_from_current_page(self, data_types, soup):
        """Extract data from the current page"""
        for data_type in data_types:
            print(f"\nExtracting {data_type} from current page...")
            elements = self.find_elements_by_keywords([data_type], soup)
            
            if elements:
                texts = [self.clean_text(elem.text) for elem in elements if elem.text.strip()]
                texts = list(dict.fromkeys(texts))  # Remove duplicates
                self.all_data[data_type].extend(texts)  # Append to existing data
                print(f"Found {len(texts)} {data_type} items")
            else:
                print(f"No {data_type} found on this page")

    def scrape_website(self):
        try:
            url = input("\nEnter the website URL to scrape: ")
            print(f"\nNavigating to {url}")
            self.driver.get(url)
            time.sleep(5)
            
            print("\nPage is loaded. Please look at the browser window.")
            print("What information would you like to extract?")
            print("Example input: title, date, source, description")
            
            data_types = input("\nEnter keywords (comma-separated): ").split(',')
            data_types = [dt.strip() for dt in data_types if dt.strip()]
            
            page_count = 1
            max_pages = 10  # Limit to prevent infinite loops
            
            while page_count <= max_pages:
                print(f"\nProcessing page {page_count}...")
                self.scroll_to_bottom()
                
                # Extract data from current page
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                self.extract_data_from_current_page(data_types, soup)
                
                # Try to go to next page
                if not self.click_next_page():
                    print("\nNo more pages found or reached the end.")
                    break
                    
                page_count += 1
                time.sleep(3)  # Wait between pages
            
            # Save all collected data
            if self.all_data:
                # Create DataFrame
                max_length = max(len(items) for items in self.all_data.values())
                df_data = {}
                
                for data_type, items in self.all_data.items():
                    padded_items = items + [''] * (max_length - len(items))
                    df_data[data_type] = padded_items
                
                df = pd.DataFrame(df_data)
                filename = "extracted_data.csv"
                df.to_csv(filename, index=False, encoding='utf-8')
                print(f"\nSuccessfully saved data from {page_count} pages to {filename}")
            else:
                print("\nNo data found for the specified keywords.")
            
        except Exception as e:
            print(f"Error during scraping: {str(e)}")
        finally:
            self.driver.quit()

class MediumScraper(SmartScraper):
    def __init__(self):
        super().__init__()
        self.is_member = False
        
    def login_to_medium(self):
        """Medium'a giriş yap"""
        try:
            print("\nMevcut Chrome profili kullanılıyor...")
            self.driver.get("https://medium.com")
            time.sleep(3)
            
            # Giriş kontrolü
            try:
                # Avatar kontrolü
                avatar = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "img[alt*='Avatar']")
                ))
                print("Başarıyla giriş yapıldı!")
                return True
            except:
                print("\nOtomatik giriş başarısız. Manuel giriş yapmanız gerekiyor.")
                print("1. Tarayıcıda Medium hesabınıza giriş yapın")
                print("2. Giriş yaptıktan sonra Enter'a basın")
                input()
                return True
            
        except Exception as e:
            print(f"Giriş hatası: {str(e)}")
            return False

    def check_membership_status(self):
        """Medium üyelik durumunu kontrol et"""
        try:
            # Profil sayfasına git
            self.driver.get("https://medium.com/me/settings")
            time.sleep(3)
            
            # Membership durumunu kontrol et
            membership_element = self.driver.find_elements(By.XPATH, "//span[contains(text(), 'Member')]")
            self.is_member = len(membership_element) > 0
            
            print(f"\nMembership durumu: {'Aktif' if self.is_member else 'Aktif değil'}")
            return self.is_member
            
        except Exception as e:
            print(f"Membership kontrolü sırasında hata: {str(e)}")
            return False
            
    def extract_medium_article_data(self, soup):
        """Medium makalelerinden veri çıkar"""
        articles_data = {
            'headline': [],
            'author': [],
            'published': [],
            'description': [],
            'read_time': [],
            'claps': [],
            'tags': []
        }
        
        # Tüm makale kartlarını bul
        articles = soup.find_all('article')
        print(f"\nBulunan makale sayısı: {len(articles)}")
        
        for article in articles:
            try:
                # Başlık - farklı class'ları dene
                title = (
                    article.find('h2') or 
                    article.find('h3') or 
                    article.find('a', class_='ae')  # Medium'un yeni class'ı
                )
                articles_data['headline'].append(title.text.strip() if title else '')
                
                # Yazar - "by" ile başlayan text'i bul
                author = (
                    article.find('div', string=lambda x: x and x.startswith('by ')) or
                    article.find('a', class_='au') or  # Yazar linki
                    article.find('span', class_='author')
                )
                if author:
                    author_text = author.text.replace('by ', '').strip()
                    articles_data['author'].append(author_text)
                else:
                    articles_data['author'].append('')
                
                # Yayın tarihi - farklı formatları dene
                date = (
                    article.find('time') or
                    article.find('span', class_='published-date') or
                    article.find('span', class_='pw-published-date')
                )
                articles_data['published'].append(
                    date['datetime'] if date and date.has_attr('datetime') 
                    else date.text.strip() if date 
                    else ''
                )
                
                # Özet/Açıklama
                description = (
                    article.find('p', class_='preview-content') or
                    article.find('h3', class_='preview-content') or
                    article.find('div', class_='preview-content')
                )
                articles_data['description'].append(description.text.strip() if description else '')
                
                # Okuma süresi
                read_time = (
                    article.find('span', string=re.compile(r'\d+\s*min read')) or
                    article.find('span', class_='reading-time')
                )
                articles_data['read_time'].append(read_time.text.strip() if read_time else '')
                
                # Alkış sayısı
                claps = (
                    article.find('span', {'data-testid': 'clapCount'}) or
                    article.find('span', class_='clap-count') or
                    article.find('button', class_='clap-button')
                )
                articles_data['claps'].append(
                    re.sub(r'[^\d]', '', claps.text) if claps and claps.text 
                    else '0'
                )
                
                # Etiketler
                tags = article.find_all(['a', 'div'], class_=lambda x: x and 'tag' in x.lower())
                articles_data['tags'].append(
                    ','.join([tag.text.strip() for tag in tags]) if tags 
                    else ''
                )
                
                print(f"Makale işlendi: {title.text.strip() if title else 'Başlıksız'}")
                
            except Exception as e:
                print(f"Makale verisi çıkarılırken hata: {str(e)}")
                # Boş değerler ekle
                for key in articles_data.keys():
                    if len(articles_data[key]) < len(articles_data['headline']):
                        articles_data[key].append('')
        
        # Sonuçları göster
        print("\nToplanan veriler:")
        for key, values in articles_data.items():
            non_empty = len([v for v in values if v])
            print(f"{key}: {non_empty}/{len(values)} dolu")
        
        return articles_data
        
    def scrape_medium(self, topic=None):
        """Medium'dan makale verilerini topla"""
        try:
            if not self.login_to_medium():
                return
            
            if topic:
                topics = [t.strip() for t in topic.split(',')]
                for single_topic in topics:
                    print(f"\n{single_topic} konusu için scraping başlıyor...")
                    try:
                        # URL'yi doğru formatta oluştur ve aramayı yap
                        encoded_topic = single_topic.replace(' ', '%20')
                        search_url = f"https://medium.com/search?q={encoded_topic}"
                        
                        print(f"URL: {search_url}")
                        self.driver.get(search_url)
                        time.sleep(5)
                        
                        # "Articles" sekmesine geç
                        try:
                            articles_tab = self.wait.until(EC.element_to_be_clickable(
                                (By.XPATH, "//span[text()='Articles']")
                            ))
                            articles_tab.click()
                            time.sleep(3)
                        except:
                            print("Articles sekmesi bulunamadı, devam ediliyor...")
                        
                        # Sayfayı yükle ve scroll yap
                        all_articles_data = defaultdict(list)
                        scroll_count = 0
                        max_scrolls = 10
                        
                        while scroll_count < max_scrolls:
                            print(f"\nScroll {scroll_count + 1}/{max_scrolls}")
                            
                            # Sayfayı analiz et
                            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                            page_data = self.extract_medium_article_data(soup)
                            
                            # Yeni makaleler var mı kontrol et
                            new_articles = False
                            for key, values in page_data.items():
                                current_count = len(all_articles_data[key])
                                new_values = values[current_count:]
                                if new_values:
                                    new_articles = True
                                    all_articles_data[key].extend(new_values)
                            
                            if not new_articles:
                                print("Yeni makale bulunamadı.")
                                break
                            
                            # Scroll yap
                            self.smooth_scroll()
                            time.sleep(random.uniform(2, 4))
                            scroll_count += 1
                        
                        # Verileri kaydet
                        if all_articles_data:
                            df = pd.DataFrame(all_articles_data)
                            filename = f"medium_articles_{single_topic.replace(' ', '_')}.csv"
                            df.to_csv(filename, index=False, encoding='utf-8')
                            print(f"\n{len(df)} makale kaydedildi: {filename}")
                            print("\nÖrnek veriler:")
                            print(df.head())
                        else:
                            print("\nHiç makale bulunamadı!")
                        
                    except Exception as e:
                        print(f"Hata: {str(e)}")
                        continue
                
            else:
                print("Lütfen en az bir konu belirtin.")
                
        except Exception as e:
            print(f"Scraping hatası: {str(e)}")
        
        finally:
            user_input = input("\nProgramı kapatmak için 'q', devam etmek için Enter: ")
            if user_input.lower() == 'q':
                self.driver.quit()

    def smooth_scroll(self):
        """Sayfayı daha doğal bir şekilde kaydır"""
        try:
            # Görünür pencere yüksekliğini al
            window_height = self.driver.execute_script("return window.innerHeight")
            # Toplam sayfa yüksekliğini al
            scroll_height = self.driver.execute_script("return document.documentElement.scrollHeight")
            
            # Küçük adımlarla kaydır
            current_pvariations = {
            'title': ['title', 'heading', 'header', 'name', 'headline'],
            'date': ['date', 'time', 'published', 'posted', 'updated', 'datetime'],
            'source': ['source', 'author', 'publisher', 'by', 'from', 'origin'],
            'web_source': ['website', 'domain', 'url', 'link', 'web', 'site'],
            'news_title': ['news', 'article', 'story', 'headline', 'post'],
            'description': ['desc', 'description', 'content', 'text', 'body', 'summary'],
            'price': ['price', 'cost', 'amount', 'value', 'fee'],
            'rating': ['rating', 'score', 'stars', 'review-score'],
            'review': ['review', 'comment', 'feedback', 'testimonial'],
            'category': ['category', 'type', 'genre', 'group', 'section']
        }osition = self.driver.execute_script("return window.pageYOffset")
            scroll_step = window_height // 4  # Daha küçük adımlar
            
            target_position = min(current_position + window_height, scroll_height - window_height)
            
            while current_position < target_position:
                current_position = min(current_position + scroll_step, target_position)
                self.driver.execute_script(f"window.scrollTo(0, {current_position})")
                time.sleep(random.uniform(0.1, 0.3))  # Daha doğal görünen bekleme
                
        except Exception as e:
            print(f"Scroll hatası: {str(e)}")

def main():
    # ABC News scraping
    abc_scraper = SmartScraper()
    abc_scraper.scrape_website()
    
    # Medium scraping - artık email/password gerektirmiyor
    medium_scraper = MediumScraper()
    topic = input("\nBelirli bir konu için scraping yapmak ister misiniz? (boş bırakabilirsiniz): ")
    medium_scraper.scrape_medium(topic if topic else None)

if __name__ == "__main__":
    main()
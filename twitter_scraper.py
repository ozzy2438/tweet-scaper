from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import csv
import logging
from datetime import datetime, timezone
from tqdm import tqdm
from urllib.parse import urljoin
from typing import Dict, Any, List
import json
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TwitterScraper:
    def __init__(self):
        self.driver = None
        self.search_query = "AI agent"
        self.tweets = []
        self.base_url = "https://twitter.com"
        self.user_profile = {}

    def setup_driver(self):
        logger.info("Opening Twitter homepage...")
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        self.driver = webdriver.Chrome(options=options)
        logger.info("Chrome driver successfully initialized")
        
        self.driver.get('https://twitter.com/login')
        logger.info("Please login manually...")
        input("Press Enter after logging in...")

    def convert_to_number(self, value):
        try:
            # Remove any commas first
            value = value.replace(',', '')
            
            if value.isdigit():
                return int(value)
                
            # Handle K (thousands)
            if 'K' in value.upper():
                number = float(value.upper().replace('K', ''))
                return int(number * 1000)
                
            # Handle M (millions)
            if 'M' in value.upper():
                number = float(value.upper().replace('M', ''))
                return int(number * 1000000)
                
            # Handle B (billions)
            if 'B' in value.upper():
                number = float(value.upper().replace('B', ''))
                return int(number * 1000000000)
                
            return 0
        except:
            return 0

    def get_tweet_stats(self, tweet):
        try:
            stats = tweet.find_elements(By.CSS_SELECTOR, '[role="group"] span[data-testid="app-text-transition-container"]')
            replies = self.convert_to_number(stats[0].text) if len(stats) > 0 else 0
            reposts = self.convert_to_number(stats[1].text) if len(stats) > 1 else 0
            likes = self.convert_to_number(stats[2].text) if len(stats) > 2 else 0
            views = self.convert_to_number(stats[3].text) if len(stats) > 3 else 0
            return {
                "replies": str(replies),
                "reposts": str(reposts),
                "likes": str(likes),
                "views": str(views)
            }
        except:
            return {
                "replies": "0",
                "reposts": "0",
                "likes": "0",
                "views": "0"
            }

    def parse_twitter_date(self, time_text):
        """Parse Twitter date format: '9:54 pm · 15 Oct 2018'"""
        try:
            logger.info(f"Raw time text: {time_text}")
            
            # Handle relative time formats
            if any(word in time_text.lower() for word in ['now', 'min', 'hour', 'day', 'week', 'month', 'year']):
                logger.info("Found relative time, using current time as fallback")
                now = datetime.now()
                return now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S')
            
            # Split by middle dot to separate time and date
            if '·' not in time_text:
                logger.info("No middle dot found in time text")
                return None, None
                
            parts = [p.strip() for p in time_text.split('·')]
            if len(parts) != 2:
                logger.info(f"Unexpected number of parts after split: {len(parts)}")
                return None, None
                
            time_part = parts[0]
            date_part = parts[1]
            
            logger.info(f"Time part: '{time_part}', Date part: '{date_part}'")
            
            # Parse time (e.g., "9:54 pm" or "09:54")
            try:
                if 'pm' in time_part.lower() or 'am' in time_part.lower():
                    time_obj = datetime.strptime(time_part, '%I:%M %p')
                else:
                    time_obj = datetime.strptime(time_part, '%H:%M')
                time_str = time_obj.strftime('%H:%M:%S')
                logger.info(f"Parsed time: {time_str}")
            except Exception as e:
                logger.error(f"Time parsing error: {str(e)}")
                return None, None
            
            # Parse date (e.g., "15 Oct 2018" or "Oct 15, 2018")
            try:
                if ',' in date_part:
                    date_obj = datetime.strptime(date_part, '%b %d, %Y')
                else:
                    date_obj = datetime.strptime(date_part, '%d %b %Y')
                date_str = date_obj.strftime('%Y-%m-%d')
                logger.info(f"Parsed date: {date_str}")
            except Exception as e:
                logger.error(f"Date parsing error: {str(e)}")
                return None, None
            
            return date_str, time_str
            
        except Exception as e:
            logger.error(f"Date parsing error: {str(e)}")
            return None, None

    def perform_search(self):
        try:
            logger.info("Starting search...")
            logger.info(f"Search query: {self.search_query}")
            
            logger.info("Entering search term...")
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-testid="SearchBox_Search_Input"]'))
            )
            search_box.click()
            search_box.send_keys(self.search_query)
            search_box.send_keys(Keys.RETURN)
            
            logger.info("Search completed, loading results...")
            time.sleep(3)
            
            # Switch to Latest tab for more results
            try:
                latest_tab = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//span[text()='Latest']"))
                )
                latest_tab.click()
                logger.info("Switched to Latest tab")
                time.sleep(2)
            except:
                logger.info("Continuing with Top tab")

            scroll_pause_time = 0.5
            no_new_tweets_count = 0
            last_tweet_count = 0
            target_tweets = 400
            
            with tqdm(total=target_tweets, desc="Collecting tweets", unit="tweet/s") as pbar:
                while len(self.tweets) < target_tweets:
                    # Aggressive scrolling
                    for _ in range(3):
                        self.driver.execute_script(
                            "window.scrollTo(0, document.documentElement.scrollHeight);"
                        )
                        time.sleep(scroll_pause_time)
                    
                    # Find all tweets
                    tweet_elements = self.driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
                    
                    # Process new tweets
                    new_tweets_added = 0
                    seen_texts = {t["text"].strip() for t in self.tweets}
                    
                    for tweet in tweet_elements:
                        if len(self.tweets) >= target_tweets:
                            break
                            
                        try:
                            # Extract tweet text first to check for duplicates
                            text = tweet.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]').text.strip()
                            
                            # Skip if we've seen this tweet
                            if not text or text in seen_texts:
                                continue
                                
                            username = tweet.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"]').text.split('\n')[0]
                            tweet_url = urljoin(self.base_url, tweet.find_element(By.CSS_SELECTOR, 'a[role="link"]').get_attribute("href"))
                            
                            # Get time element text and parse it
                            time_element = tweet.find_element(By.TAG_NAME, "time")
                            time_text = time_element.text.strip()
                            timestamp = time_element.get_attribute("datetime")
                            
                            logger.info(f"\nProcessing tweet time:")
                            logger.info(f"Time text: {time_text}")
                            logger.info(f"Timestamp: {timestamp}")
                            
                            # First try parsing the displayed text
                            date_str, time_str = self.parse_twitter_date(time_text)
                            
                            # If that fails, try using the datetime attribute
                            if not date_str or not time_str:
                                logger.info("Falling back to datetime attribute")
                                try:
                                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                    date_str = dt.strftime('%Y-%m-%d')
                                    time_str = dt.strftime('%H:%M:%S')
                                    logger.info(f"Parsed from attribute - Date: {date_str}, Time: {time_str}")
                                except Exception as e:
                                    logger.error(f"Datetime attribute parsing error: {str(e)}")
                            
                            # Use current time as last resort
                            if not date_str or not time_str:
                                logger.info("Using current time as last resort")
                                now = datetime.now()
                                date_str = now.strftime('%Y-%m-%d')
                                time_str = now.strftime('%H:%M:%S')
                            
                            stats = self.get_tweet_stats(tweet)
                            
                            self.tweets.append({
                                "username": username,
                                "text": text,
                                "replies": stats.get('replies', '0'),
                                "reposts": stats.get('reposts', '0'),
                                "likes": stats.get('likes', '0'),
                                "views": stats.get('views', '0'),
                                "url": tweet_url,
                                "time": time_str,
                                "date": date_str,
                                "raw_time": time_text  # Store raw time for debugging
                            })
                            
                            seen_texts.add(text)
                            new_tweets_added += 1
                            pbar.update(1)
                            
                        except Exception as e:
                            logger.error(f"Tweet processing error: {str(e)}")
                            continue
                    
                    # Check if we're still finding new tweets
                    if new_tweets_added == 0:
                        no_new_tweets_count += 1
                    else:
                        no_new_tweets_count = 0
                    
                    # If we haven't found new tweets in several attempts
                    if no_new_tweets_count >= 3:
                        if len(self.tweets) == last_tweet_count:
                            percentage = (len(self.tweets) / target_tweets) * 100
                            logger.info(f"\nReached {percentage:.1f}% of target ({len(self.tweets)} tweets)")
                            user_input = input("Would you like to try a different search query? (y/n): ")
                            
                            if user_input.lower() == 'y':
                                new_query = input("Enter new search query: ")
                                self.search_query = new_query
                                self.driver.get('https://twitter.com')
                                time.sleep(2)
                                return self.perform_search()  # Restart search with new query
                            else:
                                logger.info(f"Ending search with {len(self.tweets)} tweets collected")
                                break
                        else:
                            logger.info(f"Found total of {len(self.tweets)} tweets. No more tweets available.")
                            break
                    
                    last_tweet_count = len(self.tweets)
                    
                    # Dynamic scroll pause adjustment
                    if new_tweets_added > 5:
                        scroll_pause_time = max(0.2, scroll_pause_time - 0.1)
                    else:
                        scroll_pause_time = min(1.0, scroll_pause_time + 0.1)

            self.save_tweets()
            
        except Exception as e:
            logger.error(f"Error: {str(e)}")

    def get_user_profile(self, username: str) -> Dict[str, Any]:
        """Extract user profile information"""
        try:
            # Navigate to user profile
            self.driver.get(f"https://twitter.com/{username}")
            time.sleep(2)
            
            profile = {
                "x_id": "",  # Twitter API olmadan bunu almak zor
                "url": f"https://twitter.com/{username}",
                "id": username,
                "profile_name": "",
                "biography": "",
                "is_verified": False,
                "profile_image_link": "",
                "external_link": "",
                "date_joined": "",
                "following": 0,
                "followers": 0,
                "subscriptions": 0,
                "location": "",
                "birth_date": None,
                "posts_count": 0
            }

            try:
                header = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="UserName"]')
                profile["profile_name"] = header.text.split('\n')[0]
                
                # Biyografi
                bio = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="UserDescription"]')
                if bio:
                    profile["biography"] = bio[0].text

                # Profil resmi
                img = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="UserAvatar"] img')
                if img:
                    profile["profile_image_link"] = img[0].get_attribute("src")

                # İstatistikler
                stats = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="UserProfileStats"] span')
                if len(stats) >= 3:
                    profile["posts_count"] = self.convert_to_number(stats[0].text)
                    profile["following"] = self.convert_to_number(stats[1].text)
                    profile["followers"] = self.convert_to_number(stats[2].text)

                # Verified badge kontrolü
                verified = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="UserVerifiedBadge"]')
                profile["is_verified"] = len(verified) > 0

            except Exception as e:
                logger.error(f"Error extracting profile details: {str(e)}")

            return profile

        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return {}

    def format_tweet(self, tweet_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format tweet data according to new structure"""
        # ISO format'ta tarih oluştur
        dt = datetime.strptime(f"{tweet_data['date']} {tweet_data['time']}", '%Y-%m-%d %H:%M:%S')
        dt = dt.replace(tzinfo=timezone.utc)
        
        return {
            "date_posted": dt.isoformat(),
            "description": tweet_data["text"],
            "hashtags": re.findall(r'#(\w+)', tweet_data["text"]),
            "likes": self.convert_to_number(tweet_data["likes"]),
            "photos": None,  # Şimdilik None, ileride eklenebilir
            "post_id": tweet_data["url"].split("/")[-1],
            "post_url": tweet_data["url"],
            "replies": self.convert_to_number(tweet_data["replies"]),
            "reposts": self.convert_to_number(tweet_data["reposts"]),
            "videos": None,  # Şimdilik None, ileride eklenebilir
            "views": self.convert_to_number(tweet_data["views"])
        }

    def save_tweets(self):
        """Save tweets in CSV format with all fields"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tweets_data_science_{timestamp}.csv"
        
        # CSV için field isimleri
        fieldnames = [
            "date_posted",
            "description",
            "hashtags",
            "likes",
            "photos",
            "post_id",
            "post_url",
            "replies",
            "reposts",
            "videos",
            "views"
        ]
        
        # Tweetleri yeni formata dönüştür
        formatted_tweets = []
        for tweet in self.tweets:
            # ISO format'ta tarih oluştur
            dt = datetime.strptime(f"{tweet['date']} {tweet['time']}", '%Y-%m-%d %H:%M:%S')
            dt = dt.replace(tzinfo=timezone.utc)
            
            formatted_tweet = {
                "date_posted": dt.isoformat(),
                "description": tweet["text"],
                "hashtags": ','.join(re.findall(r'#(\w+)', tweet["text"])),  # hashtag'leri string olarak birleştir
                "likes": self.convert_to_number(tweet["likes"]),
                "photos": None,
                "post_id": tweet["url"].split("/")[-1],
                "post_url": tweet["url"],
                "replies": self.convert_to_number(tweet["replies"]),
                "reposts": self.convert_to_number(tweet["reposts"]),
                "videos": None,
                "views": self.convert_to_number(tweet["views"])
            }
            formatted_tweets.append(formatted_tweet)
        
        # CSV olarak kaydet
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(formatted_tweets)
        
        logger.info(f"{len(self.tweets)} tweets saved to {filename}")
        logger.info("Scraping completed successfully!")
        logger.info("Process completed/error occurred, waiting 30 seconds...")
        time.sleep(30)

    def run(self):
        self.setup_driver()
        self.perform_search()
        if self.driver:
            self.driver.quit()

def main():
    scraper = TwitterScraper()
    scraper.run()

if __name__ == "__main__":
    main()
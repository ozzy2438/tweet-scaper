from selenium import webdriver
from selenium.webdriver.common.by import By
import logging
import time

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
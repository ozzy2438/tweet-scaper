import http.client
import json
from datetime import datetime
import logging
import csv
import pandas as pd
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScholarScraper:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "google.serper.dev"
        self.results = []

    def search(self, query: str, page: int = 1, country: str = "au", time_range: str = "qdr:d"):
        """Google Scholar'dan arama yap"""
        try:
            conn = http.client.HTTPSConnection(self.base_url)
            
            payload = json.dumps({
                "q": query,
                "gl": country,
                "tbs": time_range,
                "page": page
            })
            
            headers = {
                'X-API-KEY': self.api_key,
                'Content-Type': 'application/json'
            }
            
            logger.info(f"Searching for: {query} (Page {page})")
            conn.request("POST", "/scholar", payload, headers)
            
            response = conn.getresponse()
            data = json.loads(response.read().decode("utf-8"))
            
            # Sonuçları kaydet
            if "organic" in data:
                self.results.extend(data["organic"])
                logger.info(f"Found {len(data['organic'])} results")
            
            return data
            
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            return None
        finally:
            conn.close()

    def save_results(self, format: str = "json"):
        """
        Sonuçları kaydet
        
        Args:
            format: Dosya formatı ("json" veya "csv")
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            if format.lower() == "json":
                filename = f"scholar_results_{timestamp}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.results, f, indent=2, ensure_ascii=False)
                    
            elif format.lower() == "csv":
                filename = f"scholar_results_{timestamp}.csv"
                
                # CSV başlıklarını belirle
                fieldnames = [
                    'title', 'link', 'snippet', 'year', 'citation_count',
                    'author', 'publication', 'position'
                ]
                
                # Sonuçları düzenle
                csv_data = []
                for idx, result in enumerate(self.results, 1):
                    row = {
                        'title': result.get('title', ''),
                        'link': result.get('link', ''),
                        'snippet': result.get('snippet', ''),
                        'year': result.get('year', ''),
                        'citation_count': result.get('citation_count', ''),
                        'author': result.get('author', ''),
                        'publication': result.get('publication', ''),
                        'position': idx
                    }
                    csv_data.append(row)
                
                # CSV olarak kaydet
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(csv_data)
                
                # Pandas ile Excel'e de kaydet
                df = pd.DataFrame(csv_data)
                excel_filename = f"scholar_results_{timestamp}.xlsx"
                df.to_excel(excel_filename, index=False)
                logger.info(f"Results also saved to Excel: {excel_filename}")
                
            logger.info(f"Results saved to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}")

def main():
    # API anahtarı
    API_KEY = "XXXX-XXX-XXXX"
    
    # Scraper'ı başlat
    scraper = ScholarScraper(API_KEY)
    
    # Arama yap
    queries = [
        "artificial intelligence developments",
        "machine learning innovations",
        "deep learning advancements",
        "neural networks progress",
        "AI technology evolution",
        "data science breakthroughs"
    ]
    
    total_queries = len(queries)
    
    for query_idx, query in enumerate(queries, 1):
        logger.info(f"\nProcessing query {query_idx}/{total_queries}: {query}")
        
        # İlk 20 sayfayı tara
        for page in range(1, 21):  # 20 sayfa
            logger.info(f"Fetching page {page}/20...")
            results = scraper.search(query, page=page)
            
            if not results:
                logger.warning(f"No results found for page {page}, moving to next query")
                break
                
            # Rate limiting için kısa bekleme
            time.sleep(2)  # Her sayfa arasında 2 saniye bekle
    
    logger.info("\nAll queries completed!")
    
    # Sonuçları hem JSON hem CSV olarak kaydet
    scraper.save_results(format="json")
    scraper.save_results(format="csv")
    
    logger.info(f"Total results collected: {len(scraper.results)}")

if __name__ == "__main__":
    main() 
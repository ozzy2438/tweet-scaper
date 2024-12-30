import requests
import pandas as pd
import time
from datetime import datetime

def serpstack_news_to_csv():
    # API parametreleri
    base_params = {
        'access_key': '712f89554e66adda0e7de2430a18665d',
        'query': 'artificial intelligence news',
        'type': 'news',
        'gl': 'us',
        'hl': 'en',
        'num': 100  # Her sayfada 100 sonuç
    }
    
    all_news_results = []
    target_count = 400
    offset = 0
    
    try:
        while len(all_news_results) < target_count:
            # Sayfalama için offset ekle
            params = base_params.copy()
            params['offset'] = offset
            
            print(f"\nSayfa {(offset//100) + 1} getiriliyor...")
            
            # API isteği
            response = requests.get('https://api.serpstack.com/search', params)
            data = response.json()
            
            if 'news_results' in data:
                page_results = data['news_results']
                if not page_results:  # Sonuç yoksa döngüyü bitir
                    break
                    
                all_news_results.extend(page_results)
                print(f"Toplam {len(all_news_results)} haber bulundu")
                
                offset += 100  # Sonraki sayfa için offset'i artır
                
                if len(all_news_results) >= target_count:
                    break
            else:
                print("Bu sayfada sonuç bulunamadı")
                break
            
            time.sleep(1)  # API rate limit'e takılmamak için bekle
        
        if all_news_results:
            # DataFrame oluştur
            df = pd.DataFrame(all_news_results)
            
            # CSV dosya adını oluştur
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"serpstack_news_{timestamp}.csv"
            
            # CSV'ye kaydet
            df.to_csv(filename, index=False, encoding='utf-8')
            print(f"\nHaber sonuçları başarıyla kaydedildi: {filename}")
            print(f"Toplam {len(all_news_results)} haber bulundu")
            
            # İlk birkaç sonucu göster
            print("\nÖrnek haberler:")
            print(df[['title', 'source_name', 'uploaded']].head())
        else:
            print("\nHiç haber sonucu bulunamadı!")

    except Exception as e:
        print(f"Hata oluştu: {str(e)}")
        if hasattr(e, 'response'):
            print(f"API Yanıt: {e.response.text}")

def main():
    serpstack_news_to_csv()

if __name__ == "__main__":
    main() 
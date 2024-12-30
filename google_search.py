import requests
import json
import pandas as pd
import time
from datetime import datetime

def google_search_to_csv():
    # AI agent/RAG için faydalı query
    query = "data science projects"
    
    # API parametreleri
    params = {
        'api_key': '6D20A484CBB2400E9F04C8CD2776405E',
        'q': query,
        'location': '98146, Washington, United States',
        'gl': 'us',
        'hl': 'en',
        'google_domain': 'google.com',
        'include_ai_overview': 'true',
        'num': 100,  # Maksimum sonuç sayısı
        'output': 'json',
        'page': 1
    }

    try:
        # API isteği
        response = requests.get('https://api.scaleserp.com/search', params)
        data = response.json()

        # Faydalı alanları çıkar
        search_results = []
        
        # Organik sonuçları işle
        if 'organic_results' in data:
            for result in data['organic_results']:
                search_result = {
                    'title': result.get('title', ''),
                    'url': result.get('link', ''),
                    'snippet': result.get('snippet', ''),
                    'position': result.get('position', ''),
                    'date_published': result.get('date', ''),
                    'source': result.get('source', ''),
                }
                
                # Varsa ek bilgileri ekle
                if 'rich_snippet' in result:
                    search_result['rich_snippet'] = result['rich_snippet']
                if 'related_pages' in result:
                    search_result['related_pages'] = result['related_pages']
                
                search_results.append(search_result)

        # AI özetini ekle
        if 'ai_overview' in data:
            ai_overview = {
                'title': 'AI Overview',
                'url': 'AI Generated',
                'snippet': data['ai_overview'].get('text', ''),
                'position': 0,
                'date_published': datetime.now().strftime('%Y-%m-%d'),
                'source': 'AI Overview'
            }
            search_results.insert(0, ai_overview)

        # DataFrame oluştur
        df = pd.DataFrame(search_results)

        # CSV dosya adını oluştur
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"rag_agent_search_{timestamp}.csv"

        # CSV'ye kaydet
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"\nVeriler başarıyla kaydedildi: {filename}")
        print(f"Toplam {len(search_results)} sonuç bulundu")
        
        # İlk birkaç sonucu göster
        print("\nÖrnek sonuçlar:")
        print(df[['title', 'source', 'date_published']].head())

    except Exception as e:
        print(f"Hata oluştu: {str(e)}")

if __name__ == "__main__":
    google_search_to_csv()
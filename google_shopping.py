import requests
import pandas as pd
import time
from datetime import datetime

def google_shopping_to_csv(queries):
    """
    Birden fazla ürün için Google Shopping sonuçlarını çeker
    queries: Liste olarak arama sorguları ["macbook pro m3", "macbook pro m4"] gibi
    """
    all_results = {}
    
    for query in queries:
        print(f"\n{query} için arama yapılıyor...")
        
        base_params = {
            'api_key': '6D20A484CBB2400E9F04C8CD2776405E',
            'q': query,
            'search_type': 'shopping',
            'location': 'United States',
            'gl': 'us',
            'hl': 'en',
            'num': 100,
            'output': 'json',
            'sort_by': 'price_low_to_high'  # Fiyata göre sıralama
        }
        
        all_shopping_results = []
        target_count = 500
        offset = 0
        
        try:
            while len(all_shopping_results) < target_count:
                params = base_params.copy()
                params['start'] = offset
                
                print(f"Sayfa {(offset//100) + 1} getiriliyor...")
                
                response = requests.get('https://api.scaleserp.com/search', params)
                data = response.json()
                
                if 'shopping_results' in data:
                    page_results = data['shopping_results']
                    if not page_results:
                        break
                        
                    for item in page_results:
                        shopping_item = {
                            'query': query,  # Hangi sorgudan geldiğini ekle
                            'position': item.get('position', ''),
                            'title': item.get('title', ''),
                            'link': item.get('link', ''),
                            'price': item.get('price', ''),
                            'currency': item.get('currency', ''),
                            'rating': item.get('rating', ''),
                            'reviews': item.get('reviews', ''),
                            'store_name': item.get('store_name', ''),
                            'store_rating': item.get('store_rating', ''),
                            'shipping': item.get('shipping', ''),
                            'on_sale': item.get('on_sale', ''),
                            'original_price': item.get('original_price', '')
                        }
                        all_shopping_results.append(shopping_item)
                    
                    print(f"Toplam {len(all_shopping_results)} ürün bulundu")
                    
                    offset += 100
                    if len(all_shopping_results) >= target_count:
                        break
                else:
                    print("Bu sayfada sonuç bulunamadı")
                    break
                
                time.sleep(1)
            
            all_results[query] = all_shopping_results
            
        except Exception as e:
            print(f"Hata oluştu ({query}): {str(e)}")
            continue
    
    # Tüm sonuçları tek bir DataFrame'de birleştir
    if all_results:
        all_data = []
        for query_results in all_results.values():
            all_data.extend(query_results)
            
        df = pd.DataFrame(all_data)
        
        # Fiyat ve rating sütunlarını sayısal değere çevir
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
        
        # CSV'ye kaydet
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"google_shopping_comparison_{timestamp}.csv"
        df.to_csv(filename, index=False, encoding='utf-8')
        
        print(f"\nTüm sonuçlar kaydedildi: {filename}")
        
        # Basit özet istatistikler
        summary = pd.DataFrame()
        summary['Ürün Sayısı'] = df.groupby('query')['price'].count()
        summary['Ortalama Fiyat'] = df.groupby('query')['price'].mean()
        summary['Minimum Fiyat'] = df.groupby('query')['price'].min()
        summary['Maximum Fiyat'] = df.groupby('query')['price'].max()
        summary['Ortalama Puan'] = df.groupby('query')['rating'].mean()
        
        # Sonuçları yuvarla
        summary = summary.round(2)
        print("\nÜrün Karşılaştırma Özeti:")
        print(summary)
        
        # Fiyat dağılımını göster
        print("\nFiyat Aralıkları:")
        price_ranges = pd.cut(df['price'], 
                            bins=[0, 1000, 2000, 3000, 4000, float('inf')],
                            labels=['0-1000', '1000-2000', '2000-3000', '3000-4000', '4000+'])
        distribution = pd.crosstab(df['query'], price_ranges)
        print(distribution)
        
        # İstatistiksel karşılaştırma
        print("\nDetaylı Fiyat Analizi:")
        for query in queries:
            query_data = df[df['query'] == query]
            print(f"\n{query}:")
            print(f"Medyan Fiyat: ${query_data['price'].median():.2f}")
            print(f"Standart Sapma: ${query_data['price'].std():.2f}")
            print(f"25% Kartil: ${query_data['price'].quantile(0.25):.2f}")
            print(f"75% Kartil: ${query_data['price'].quantile(0.75):.2f}")
        
    else:
        print("\nHiç sonuç bulunamadı!")

def main():
    queries = [
        "macbook pro m3",
        "macbook pro m4"
    ]
    google_shopping_to_csv(queries)

if __name__ == "__main__":
    main() 
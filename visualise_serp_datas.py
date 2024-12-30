import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
from wordcloud import WordCloud
from collections import Counter
from nltk.corpus import stopwords
import nltk
import matplotlib.pyplot as plt

# Stil ayarları
plt.style.use('seaborn-v0_8')
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = [12, 8]
plt.rcParams['font.size'] = 12
plt.rcParams['font.family'] = 'sans-serif'

# NLTK stopwords
nltk.download('stopwords', quiet=True)

# Veriyi yükle ve temizle
df = pd.read_csv('merged_scholar_results.csv')
df = df.dropna(subset=['year', 'citation_count'])
df['year'] = pd.to_numeric(df['year'], errors='coerce')
df['citation_count'] = pd.to_numeric(df['citation_count'], errors='coerce')
df = df[(df['year'] >= 1980) & (df['year'] <= 2024)]

def create_yearly_publications_plot():
    """Yıllara göre yayın dağılımı - İnteraktif"""
    yearly_data = df['year'].value_counts().sort_index()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=yearly_data.index,
        y=yearly_data.values,
        mode='lines+markers',
        line=dict(width=3, color='#1f77b4'),
        marker=dict(size=8),
        hovertemplate='Yıl: %{x}<br>Yayın Sayısı: %{y}<extra></extra>'
    ))
    
    fig.update_layout(
        title={
            'text': 'Yıllara Göre Yayın Dağılımı',
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=24)
        },
        xaxis_title="Yıl",
        yaxis_title="Yayın Sayısı",
        template='plotly_white',
        hovermode='x unified',
        showlegend=False,
        width=1200,
        height=600
    )
    
    return fig

def create_top_cited_plot():
    """En çok atıf alan yayınlar - İnteraktif"""
    top_10 = df.nlargest(10, 'citation_count')
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=top_10['citation_count'],
        y=top_10['title'],
        orientation='h',
        marker_color='#2ecc71',
        hovertemplate='Atıf Sayısı: %{x}<extra></extra>'
    ))
    
    fig.update_layout(
        title={
            'text': 'En Çok Atıf Alan 10 Yayın',
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=24)
        },
        xaxis_title="Atıf Sayısı",
        yaxis_title=None,
        template='plotly_white',
        width=1200,
        height=800,
        margin=dict(l=10, r=10, t=100, b=50)
    )
    
    return fig

def create_wordcloud():
    """Gelişmiş WordCloud"""
    combined_snippets = ' '.join(df['snippet'].dropna().astype(str))
    
    wordcloud = WordCloud(
        width=1600, 
        height=800,
        background_color='white',
        colormap='viridis',
        max_words=100,
        stopwords=set(stopwords.words('english')),
        collocations=False,
        contour_width=3,
        contour_color='steelblue'
    ).generate(combined_snippets)
    
    fig = plt.figure(figsize=(20,10))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title("Araştırma Konuları Word Cloud", fontsize=24, pad=20)
    
    return fig

def create_trend_analysis():
    """Trend Analizi - İnteraktif"""
    recent_years = df[df['year'] >= 2020]
    recent_trends = recent_years['snippet'].str.cat(sep=' ').lower()
    words = [word for word in recent_trends.split() 
             if word.isalpha() and word not in stopwords.words('english')]
    word_freq = Counter(words)
    
    top_words = pd.DataFrame(word_freq.most_common(15), 
                           columns=['Kelime', 'Frekans'])
    
    fig = px.bar(top_words, 
                x='Frekans', 
                y='Kelime',
                orientation='h',
                color='Frekans',
                color_continuous_scale='Viridis')
    
    fig.update_layout(
        title={
            'text': 'Son Yıllardaki Trend Konular',
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=24)
        },
        yaxis={'categoryorder':'total ascending'},
        template='plotly_white',
        width=1200,
        height=800
    )
    
    return fig

def create_citation_year_scatter():
    """Atıf-Yıl İlişkisi Scatter Plot"""
    fig = px.scatter(df, 
                    x='year', 
                    y='citation_count',
                    size='citation_count',
                    color='citation_count',
                    hover_data=['title'],
                    color_continuous_scale='Viridis',
                    title='Yıllara Göre Atıf Dağılımı')
    
    fig.update_layout(
        template='plotly_white',
        title={
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=24)
        },
        width=1200,
        height=600
    )
    
    return fig

def main():
    # Tüm grafikleri oluştur ve kaydet
    print("Görselleştirmeler oluşturuluyor...")
    
    yearly_fig = create_yearly_publications_plot()
    yearly_fig.write_html("yearly_publications.html")
    print("1/5: Yıllık yayın dağılımı grafiği oluşturuldu")
    
    cited_fig = create_top_cited_plot()
    cited_fig.write_html("top_cited_papers.html")
    print("2/5: En çok atıf alan yayınlar grafiği oluşturuldu")
    
    wordcloud_fig = create_wordcloud()
    wordcloud_fig.savefig('wordcloud.png', dpi=300, bbox_inches='tight', facecolor='white')
    print("3/5: Word cloud görseli oluşturuldu")
    
    trend_fig = create_trend_analysis()
    trend_fig.write_html("trend_analysis.html")
    print("4/5: Trend analizi grafiği oluşturuldu")
    
    scatter_fig = create_citation_year_scatter()
    scatter_fig.write_html("citation_scatter.html")
    print("5/5: Atıf-yıl ilişkisi grafiği oluşturuldu")
    
    print("\nTüm görselleştirmeler başarıyla oluşturuldu!")
    print("\nOluşturulan dosyalar:")
    print("- yearly_publications.html")
    print("- top_cited_papers.html")
    print("- wordcloud.png")
    print("- trend_analysis.html")
    print("- citation_scatter.html")

if __name__ == "__main__":
    main()

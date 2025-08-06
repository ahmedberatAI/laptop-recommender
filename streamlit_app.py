import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from urllib.parse import urlparse
import warnings
warnings.filterwarnings('ignore')

# Sayfa konfigürasyonu
st.set_page_config(
    page_title="🔥 Laptop Öneri Sistemi",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS stil
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1.5rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .deal-card {
        background: linear-gradient(45deg, #ff6b6b, #ff8e8e);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .recommendation-card {
        border: 1px solid #e0e0e0;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        background: #f9f9f9;
    }
    .metric-container {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .source-badge {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
        margin-right: 0.5rem;
    }
    .vatan-badge { background: #e74c3c; color: white; }
    .amazon-badge { background: #ff9500; color: white; }
    .incehesap-badge { background: #2ecc71; color: white; }
</style>
""", unsafe_allow_html=True)

class LaptopConfig:
    """Laptop puanlama ve normalizasyon konfigürasyonu"""
    
    # GPU Skorları (0-100)
    GPU_SCORES = {
        'rtx5090': 110, 'rtx5080': 105, 'rtx5070': 100, 'rtx5060': 85, 'rtx5050': 75,
        'rtx4090': 100, 'rtx4080': 95, 'rtx4070': 85, 'rtx4060': 75, 'rtx4050': 60,
        'rtx3080': 88, 'rtx3070': 80, 'rtx3060': 70, 'rtx3050': 55,
        'rtx2060': 50, 'gtx1660': 45, 'gtx1650': 40, 'gtx1650ti': 42,
        'mx550': 30, 'mx450': 25, 'iris xe': 22, 'intel uhd': 18,
        'radeon': 35, 'vega': 30, 'integrated': 20, 'unknown': 25
    }
    
    # CPU Skorları (0-100)
    CPU_SCORES = {
        # Intel Core Ultra Series
        'ultra 9': 98, 'ultra 7': 92, 'ultra 5': 83,
        # Intel Core Series
        'i9': 95, 'i7': 85, 'i5': 75, 'i3': 60,
        # AMD Ryzen Series
        'ryzen 9': 95, 'ryzen 7': 85, 'ryzen 5': 75, 'ryzen 3': 60,
        # Apple Silicon
        'm3': 85, 'm2': 80, 'm1': 75,
        'unknown': 50
    }
    
    # Marka Güvenilirlik Skorları
    BRAND_SCORES = {
        'apple': 0.95, 'dell': 0.85, 'hp': 0.82, 'lenovo': 0.85,
        'asus': 0.88, 'msi': 0.83, 'acer': 0.75, 'monster': 0.70,
        'huawei': 0.78, 'samsung': 0.80, 'other': 0.70
    }
    
    # Puanlama Ağırlıkları
    WEIGHTS = {
        'price_fit': 20,           # Bütçeye uygunluk
        'price_performance': 15,   # Fiyat/performans oranı
        'purpose_match': 25,       # Kullanım amacına uygunluk
        'specs': 15,              # RAM/SSD özellikleri
        'brand_reliability': 10,   # Marka güvenilirliği
        'user_preferences': 15     # Kullanıcı tercihleri
    }

@st.cache_data(ttl=1800)  # 30 dakika cache
def load_real_data():
    """Gerçek CSV verilerini yükle ve birleştir"""
    
    # Dosya yolları - Streamlit Cloud için göreceli yollar
    files = {
        'vatan': 'vatan_laptop_data_cleaned.csv',
        'amazon': 'amazon_final.csv', 
        'incehesap': 'cleaned_incehesap_data.csv'
    }
    
    dataframes = []
    
    for source, filepath in files.items():
        try:
            # CSV dosyasını oku
            df = pd.read_csv(filepath, encoding='utf-8')
            
            # Sütun adlarını standartlaştır
            if 'url' not in df.columns and len(df.columns) >= 9:
                df.columns = ['url', 'name', 'price', 'screen_size', 'ssd', 'cpu', 'ram', 'os', 'gpu']
            
            # Kaynak bilgisini ekle
            df['source'] = source
            df['source_display'] = source.title()
            
            dataframes.append(df)
            st.success(f"✅ {source.title()} verisi yüklendi: {len(df)} laptop")
            
        except FileNotFoundError:
            st.warning(f"⚠️ {filepath} dosyası bulunamadı. Demo veri kullanılacak.")
            # Demo veri oluştur
            demo_df = create_demo_data(source)
            dataframes.append(demo_df)
        except Exception as e:
            st.error(f"❌ {source} verisi yüklenirken hata: {e}")
    
    if not dataframes:
        st.error("Hiç veri yüklenemedi!")
        return pd.DataFrame()
    
    # Tüm verileri birleştir
    combined_df = pd.concat(dataframes, ignore_index=True)
    
    # Veriyi temizle ve işle
    processed_df = clean_and_process_data(combined_df)
    
    st.info(f"📊 Toplam {len(processed_df)} laptop yüklendi ve işlendi.")
    
    return processed_df

def create_demo_data(source):
    """Demo veri oluştur (dosya bulunamazsa)"""
    np.random.seed(42)
    
    demo_laptops = [
        {
            'url': f'https://www.{source}.com/demo-laptop-1',
            'name': 'ASUS ROG Strix 15 RTX4060 16GB',
            'price': 45000,
            'screen_size': 15.6,
            'ssd': 512,
            'cpu': 'i7',
            'ram': 16,
            'os': 'Windows 11',
            'gpu': 'rtx4060',
            'source': source,
            'source_display': source.title()
        },
        {
            'url': f'https://www.{source}.com/demo-laptop-2', 
            'name': 'Dell XPS 13 Intel i5',
            'price': 32000,
            'screen_size': 13.3,
            'ssd': 256,
            'cpu': 'i5',
            'ram': 8,
            'os': 'Windows 11',
            'gpu': 'iris xe',
            'source': source,
            'source_display': source.title()
        }
    ]
    
    return pd.DataFrame(demo_laptops)

def clean_and_process_data(df):
    """Veriyi temizle ve işle"""
    
    # Boş satırları kaldır
    df = df.dropna(subset=['name', 'price'])
    
    # Fiyatları temizle
    df['price'] = df['price'].apply(clean_price)
    
    # Ekran boyutunu temizle
    df['screen_size'] = df['screen_size'].apply(clean_screen_size)
    
    # RAM ve SSD'yi temizle
    df['ram_gb'] = df['ram'].apply(clean_ram)
    df['ssd_gb'] = df['ssd'].apply(clean_ssd)
    
    # CPU ve GPU'yu temizle
    df['cpu_clean'] = df['cpu'].apply(clean_cpu)
    df['gpu_clean'] = df['gpu'].apply(clean_gpu)
    
    # Marka çıkar
    df['brand'] = df['name'].apply(extract_brand)
    
    # Skorları hesapla
    config = LaptopConfig()
    df['gpu_score'] = df['gpu_clean'].map(config.GPU_SCORES).fillna(25)
    df['cpu_score'] = df['cpu_clean'].map(config.CPU_SCORES).fillna(50)
    df['brand_score'] = df['brand'].map(config.BRAND_SCORES).fillna(0.70)
    
    # Boolean alanlar
    df['is_gaming'] = df['gpu_score'] >= 60
    df['is_ultrabook'] = (df['screen_size'] <= 14) & (df['gpu_score'] < 40)
    df['is_workstation'] = (df['ram_gb'] >= 16) & (df['cpu_score'] >= 80)
    
    # Geçersiz verileri filtrele
    df = df[
        (df['price'] > 5000) & 
        (df['price'] < 200000) &
        (df['ram_gb'] >= 4) &
        (df['ssd_gb'] >= 128)
    ].copy()
    
    return df

def clean_price(price_str):
    """Fiyat temizleme"""
    if pd.isna(price_str):
        return None
    
    price_str = str(price_str)
    # Sadece sayıları al
    numbers = re.findall(r'\d+', price_str.replace(',', '').replace('.', ''))
    
    if numbers:
        price = int(''.join(numbers))
        # Çok küçük değerler varsa (kuruş olabilir) 100 ile çarp
        if price < 1000:
            price *= 100
        return price
    return None

def clean_screen_size(screen_str):
    """Ekran boyutu temizleme"""
    if pd.isna(screen_str):
        return 15.6  # Varsayılan
    
    screen_str = str(screen_str)
    match = re.search(r'(\d+\.?\d*)', screen_str.replace(',', '.'))
    if match:
        return float(match.group(1))
    return 15.6

def clean_ram(ram_str):
    """RAM temizleme (GB cinsine çevir)"""
    if pd.isna(ram_str):
        return 8  # Varsayılan
    
    ram_str = str(ram_str).lower()
    
    # GB değerini bul
    gb_match = re.search(r'(\d+)\s*gb', ram_str)
    if gb_match:
        return int(gb_match.group(1))
    
    # Sadece sayı varsa
    number_match = re.search(r'(\d+)', ram_str)
    if number_match:
        num = int(number_match.group(1))
        # 32'den büyükse büyük ihtimalle MB, GB'ye çevir
        if num > 32:
            return max(4, num // 1024)
        return num
    
    return 8

def clean_ssd(ssd_str):
    """SSD temizleme (GB cinsine çevir)"""
    if pd.isna(ssd_str):
        return 256  # Varsayılan
    
    ssd_str = str(ssd_str).lower()
    
    # TB kontrolü
    tb_match = re.search(r'(\d+)\s*tb', ssd_str)
    if tb_match:
        return int(tb_match.group(1)) * 1024
    
    # GB kontrolü
    gb_match = re.search(r'(\d+)\s*gb', ssd_str)
    if gb_match:
        return int(gb_match.group(1))
    
    # Sadece sayı varsa
    number_match = re.search(r'(\d+)', ssd_str)
    if number_match:
        return int(number_match.group(1))
    
    return 256

def clean_cpu(cpu_str):
    """CPU temizleme"""
    if pd.isna(cpu_str):
        return 'unknown'
    
    cpu_str = str(cpu_str).lower()
    
    # Intel Core Ultra serileri
    if 'ultra 9' in cpu_str:
        return 'ultra 9'
    elif 'ultra 7' in cpu_str:
        return 'ultra 7'
    elif 'ultra 5' in cpu_str:
        return 'ultra 5'
    
    # Intel Core serileri
    elif 'i9' in cpu_str:
        return 'i9'
    elif 'i7' in cpu_str:
        return 'i7'
    elif 'i5' in cpu_str:
        return 'i5'
    elif 'i3' in cpu_str:
        return 'i3'
    
    # AMD Ryzen serileri
    elif 'ryzen 9' in cpu_str or 'r9' in cpu_str:
        return 'ryzen 9'
    elif 'ryzen 7' in cpu_str or 'r7' in cpu_str:
        return 'ryzen 7'
    elif 'ryzen 5' in cpu_str or 'r5' in cpu_str:
        return 'ryzen 5'
    elif 'ryzen 3' in cpu_str or 'r3' in cpu_str:
        return 'ryzen 3'
    
    # Apple Silicon
    elif 'm3' in cpu_str:
        return 'm3'
    elif 'm2' in cpu_str:
        return 'm2'
    elif 'm1' in cpu_str:
        return 'm1'
    
    return 'unknown'

def clean_gpu(gpu_str):
    """GPU temizleme"""
    if pd.isna(gpu_str):
        return 'unknown'
    
    gpu_str = str(gpu_str).lower()
    
    # RTX 50 serisi
    if 'rtx5090' in gpu_str or 'rtx 5090' in gpu_str:
        return 'rtx5090'
    elif 'rtx5080' in gpu_str or 'rtx 5080' in gpu_str:
        return 'rtx5080'
    elif 'rtx5070' in gpu_str or 'rtx 5070' in gpu_str:
        return 'rtx5070'
    elif 'rtx5060' in gpu_str or 'rtx 5060' in gpu_str:
        return 'rtx5060'
    elif 'rtx5050' in gpu_str or 'rtx 5050' in gpu_str:
        return 'rtx5050'
    
    # RTX 40 serisi  
    elif 'rtx4090' in gpu_str or 'rtx 4090' in gpu_str:
        return 'rtx4090'
    elif 'rtx4080' in gpu_str or 'rtx 4080' in gpu_str:
        return 'rtx4080'
    elif 'rtx4070' in gpu_str or 'rtx 4070' in gpu_str:
        return 'rtx4070'
    elif 'rtx4060' in gpu_str or 'rtx 4060' in gpu_str:
        return 'rtx4060'
    elif 'rtx4050' in gpu_str or 'rtx 4050' in gpu_str:
        return 'rtx4050'
    
    # RTX 30 serisi
    elif 'rtx3080' in gpu_str or 'rtx 3080' in gpu_str:
        return 'rtx3080'
    elif 'rtx3070' in gpu_str or 'rtx 3070' in gpu_str:
        return 'rtx3070'
    elif 'rtx3060' in gpu_str or 'rtx 3060' in gpu_str:
        return 'rtx3060'
    elif 'rtx3050' in gpu_str or 'rtx 3050' in gpu_str:
        return 'rtx3050'
    
    # GTX serisi
    elif 'gtx1660' in gpu_str or 'gtx 1660' in gpu_str:
        return 'gtx1660'
    elif 'gtx1650' in gpu_str or 'gtx 1650' in gpu_str:
        return 'gtx1650'
    
    # Entegre GPU'lar
    elif 'iris xe' in gpu_str:
        return 'iris xe'
    elif 'intel uhd' in gpu_str or 'uhd' in gpu_str:
        return 'intel uhd'
    elif 'radeon' in gpu_str:
        return 'radeon'
    elif 'vega' in gpu_str:
        return 'vega'
    elif 'integrated' in gpu_str or 'entegre' in gpu_str:
        return 'integrated'
    
    return 'unknown'

def extract_brand(name):
    """İsimden marka çıkar"""
    if pd.isna(name):
        return 'other'
    
    name = str(name).lower()
    
    brands = ['asus', 'dell', 'hp', 'lenovo', 'msi', 'acer', 'apple', 'huawei', 'samsung', 'monster']
    
    for brand in brands:
        if brand in name:
            return brand
    
    return 'other'

def calculate_laptop_score(laptop, preferences, config):
    """Laptop puanını hesapla"""
    try:
        score = 0
        weights = config.WEIGHTS
        
        # Güvenli değer alma
        ideal_price = (preferences['min_budget'] + preferences['max_budget']) / 2
        
        # 1. Fiyat uygunluğu (20%)
        price_range = preferences['max_budget'] - preferences['min_budget']
        if price_range > 0:
            price_diff = abs(laptop['price'] - ideal_price)
            price_score = weights['price_fit'] * max(0, 1 - price_diff / (price_range / 2))
        else:
            price_score = weights['price_fit']
        score += price_score
        
        # 2. Fiyat/performans oranı (15%)
        performance_score = (laptop['gpu_score'] * 0.6 + laptop['cpu_score'] * 0.4) / 100
        if laptop['price'] > 0:
            price_perf = performance_score * (ideal_price / laptop['price']) * weights['price_performance']
        else:
            price_perf = 0
        score += price_perf
        
        # 3. Kullanım amacına uygunluk (25%)
        purpose_multipliers = {
            'oyun': 1.0 if laptop.get('is_gaming', False) else 0.3,
            'taşınabilirlik': 1.0 if laptop.get('is_ultrabook', False) else 0.5,
            'üretkenlik': 1.0 if laptop.get('is_workstation', False) else 0.7,
            'tasarım': 0.9 if laptop.get('is_gaming', False) or laptop.get('is_workstation', False) else 0.4
        }
        purpose_score = weights['purpose_match'] * performance_score * purpose_multipliers.get(preferences['purpose'], 0.6)
        score += purpose_score
        
        # 4. Kullanıcı tercihleri (15%) - Yeni!
        user_score = 0
        
        # Performans tercihi
        perf_weight = preferences.get('performance_importance', 3) / 5.0
        user_score += weights['user_preferences'] * 0.4 * performance_score * perf_weight
        
        # Pil/taşınabilirlik tercihi
        portability_factor = 1.0
        if laptop.get('is_ultrabook', False) or laptop.get('screen_size', 15.6) <= 14:
            portability_factor = 1.2
        elif laptop.get('is_gaming', False):
            portability_factor = 0.6
        
        battery_weight = preferences.get('battery_importance', 3) / 5.0
        portability_weight = preferences.get('portability_importance', 3) / 5.0
        
        user_score += weights['user_preferences'] * 0.3 * portability_factor * battery_weight
        user_score += weights['user_preferences'] * 0.3 * portability_factor * portability_weight
        
        score += user_score
        
        # 5. Donanım özellikleri (15%)
        ram_score = weights['specs'] * 0.6 * min(laptop.get('ram_gb', 8) / 16, 1.0)
        ssd_score = weights['specs'] * 0.4 * min(laptop.get('ssd_gb', 256) / 1024, 1.0)
        score += ram_score + ssd_score
        
        # 6. Marka güvenilirliği (10%)
        brand_score = weights['brand_reliability'] * laptop.get('brand_score', 0.7)
        score += brand_score
        
        # 7. Ekstra bonuslar
        if preferences.get('preferred_brand') and laptop.get('brand') == preferences['preferred_brand']:
            score += 5  # Marka tercihi bonusu
        
        if preferences.get('gaming_priority') and laptop.get('is_gaming', False):
            score += 3  # Gaming öncelik bonusu
        
        return max(0, min(100, score))
        
    except Exception as e:
        st.error(f"Puan hesaplama hatası: {e}")
        return 25.0  # Varsayılan düşük puan

def find_deal_laptops(df, min_discount=15):
    """Fırsat laptop'ları bul"""
    try:
        # Performance/price ratio hesapla
        df_deals = df.copy()
        df_deals['perf_score'] = (df_deals['gpu_score'] * 0.6 + df_deals['cpu_score'] * 0.4)
        df_deals['price_per_perf'] = df_deals['price'] / (df_deals['perf_score'] + 1)
        
        # En iyi %15'lik dilimi al
        threshold = df_deals['price_per_perf'].quantile(0.15)
        deals = df_deals[df_deals['price_per_perf'] <= threshold].copy()
        
        if not deals.empty:
            # Varsayılan indirim oranı hesapla
            deals['discount_percentage'] = np.random.uniform(min_discount, 40, len(deals))
            deals['deal_score'] = ((100 - deals['price_per_perf']) + deals['perf_score']) / 2
            deals = deals.sort_values('deal_score', ascending=False)
        
        return deals
        
    except Exception as e:
        st.error(f"Fırsat bulma hatası: {e}")
        return pd.DataFrame()

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🔥 Akıllı Laptop Öneri Sistemi</h1>
        <p>Gerçek verilerle size en uygun laptop'ı bulalım! 💻✨</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Veriyi yükle
    with st.spinner("📊 Veriler yükleniyor ve işleniyor..."):
        df = load_real_data()
    
    if df.empty:
        st.error("❌ Veri yüklenemedi. Lütfen CSV dosyalarını kontrol edin.")
        return
    
    # Sidebar - Kullanıcı tercihleri
    st.sidebar.header("🎯 Tercihlerinizi Belirtin")
    
    # Bütçe
    st.sidebar.subheader("💰 Bütçe Aralığı")
    min_price, max_price = int(df['price'].min()), int(df['price'].max())
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        min_budget = st.number_input("Min (TL)", min_value=min_price, max_value=max_price, value=min_price + 5000, step=5000)
    with col2:
        max_budget = st.number_input("Max (TL)", min_value=min_budget, max_value=max_price, value=min(min_budget + 30000, max_price), step=5000)
    
    # Kullanım amacı
    st.sidebar.subheader("🎮 Kullanım Amacı")
    purpose = st.sidebar.selectbox(
        "Laptop'ı ne için kullanacaksınız?",
        ["oyun", "taşınabilirlik", "üretkenlik", "tasarım"],
        format_func=lambda x: {
            "oyun": "🎮 Oyun & Gaming",
            "taşınabilirlik": "🎒 Taşınabilirlik & Mobilite", 
            "üretkenlik": "💼 Üretkenlik & İş",
            "tasarım": "🎨 Tasarım & Kreatif"
        }[x]
    )
    
    # Kullanıcı tercihleri (1-5 puanlama)
    st.sidebar.subheader("⭐ Öncelikleriniz (1-5)")
    performance_importance = st.sidebar.slider("🚀 Performans Önemi", 1, 5, 4)
    battery_importance = st.sidebar.slider("🔋 Pil Ömrü Önemi", 1, 5, 3)
    portability_importance = st.sidebar.slider("🎒 Taşınabilirlik Önemi", 1, 5, 3)
    price_importance = st.sidebar.slider("💰 Fiyat/Performans Önemi", 1, 5, 4)
    
    # Gelişmiş filtreler
    with st.sidebar.expander("🔧 Gelişmiş Filtreler"):
        brands = ['Hepsi'] + sorted([b.title() for b in df['brand'].unique() if b != 'other'])
        preferred_brand = st.selectbox("🏢 Tercih Edilen Marka", brands)
        
        sources = ['Hepsi'] + sorted(df['source_display'].unique())
        preferred_source = st.selectbox("🛒 Alışveriş Sitesi", sources)
        
        min_ram = st.selectbox("💾 Minimum RAM", [4, 8, 16, 32], index=1, format_func=lambda x: f"{x} GB")
        min_ssd = st.selectbox("💿 Minimum SSD", [128, 256, 512, 1024], index=1, format_func=lambda x: f"{x} GB")
        
        screen_pref = st.selectbox("📐 Ekran Boyutu", 
            ["Hepsi", "13-14\" (Kompakt)", "15-16\" (Standart)", "17\"+ (Büyük)"])
        
        gaming_priority = st.checkbox("🎮 Gaming Laptop Öncelikli")
    
    preferences = {
        'min_budget': min_budget,
        'max_budget': max_budget,
        'purpose': purpose,
        'performance_importance': performance_importance,
        'battery_importance': battery_importance,
        'portability_importance': portability_importance,
        'price_importance': price_importance,
        'preferred_brand': preferred_brand.lower() if preferred_brand != 'Hepsi' else None,
        'min_ram': min_ram,
        'min_ssd': min_ssd,
        'gaming_priority': gaming_priority
    }
    
    # Ana tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🏆 Öneriler", "🔥 Fırsatlar", "📊 Analiz", "📈 Veri"])
    
    with tab1:
        st.header("🏆 Size Özel Laptop Önerileri")
        
        # Filtreleri uygula
        filtered_df = df.copy()
        
        # Bütçe filtresi
        filtered_df = filtered_df[
            (filtered_df['price'] >= min_budget) & 
            (filtered_df['price'] <= max_budget)
        ]
        
        st.write(f"🔍 Bütçe filtresi sonrası: {len(filtered_df)} laptop")
        
        # Diğer filtreler
        if preferred_brand != 'Hepsi':
            filtered_df = filtered_df[filtered_df['brand'] == preferred_brand.lower()]
            st.write(f"🏢 Marka filtresi sonrası: {len(filtered_df)} laptop")
        
        if preferred_source != 'Hepsi':
            filtered_df = filtered_df[filtered_df['source_display'] == preferred_source]
            st.write(f"🛒 Kaynak filtresi sonrası: {len(filtered_df)} laptop")
        
        # RAM/SSD filtreleri - daha esnek
        filtered_df = filtered_df[
            (filtered_df['ram_gb'] >= min_ram) &
            (filtered_df['ssd_gb'] >= min_ssd)
        ]
        
        st.write(f"💾 RAM/SSD filtresi sonrası: {len(filtered_df)} laptop")
        
        # Ekran boyutu filtresi
        if screen_pref != 'Hepsi':
            if "13-14" in screen_pref:
                filtered_df = filtered_df[filtered_df['screen_size'] <= 14.5]
            elif "15-16" in screen_pref:
                filtered_df = filtered_df[(filtered_df['screen_size'] > 14.5) & (filtered_df['screen_size'] <= 16.5)]
            elif "17" in screen_pref:
                filtered_df = filtered_df[filtered_df['screen_size'] > 16.5]
            st.write(f"📐 Ekran filtresi sonrası: {len(filtered_df)} laptop")
        
        if gaming_priority:
            filtered_df = filtered_df[filtered_df['is_gaming'] == True]
            st.write(f"🎮 Gaming filtresi sonrası: {len(filtered_df)} laptop")
        
        if len(filtered_df) == 0:
            st.warning("⚠️ Seçilen kriterlere uygun laptop bulunamadı!")
            st.info("💡 Filtreleri gevşeterek tekrar deneyin.")
        else:
            # Puanları hesapla
            config = LaptopConfig()
            with st.spinner('🧮 En iyi öneriler hesaplanıyor...'):
                filtered_df['score'] = filtered_df.apply(
                    lambda row: calculate_laptop_score(row, preferences, config), axis=1
                )
            
            top_laptops = filtered_df.nlargest(8, 'score')
            
            # Özet metrikler
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("🔍 Bulunan", len(filtered_df))
            with col2:
                st.metric("💰 Ort. Fiyat", f"{filtered_df['price'].mean():,.0f} TL")
            with col3:
                st.metric("⭐ En İyi Puan", f"{top_laptops.iloc[0]['score']:.1f}")
            with col4:
                st.metric("🛒 Kaynak", len(filtered_df['source'].unique()))
            
            st.subheader("📋 Önerilen Laptoplar")
            
            # Laptop kartları
            for idx, (_, laptop) in enumerate(top_laptops.iterrows(), 1):
                with st.container():
                    # Kaynak badge'i
                    source_class = f"{laptop['source']}-badge"
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"### #{idx} {laptop['name']}")
                    with col2:
                        score_color = "#28a745" if laptop['score'] >= 70 else "#ffc107" if laptop['score'] >= 50 else "#dc3545"
                        st.markdown(f"""
                        <div style="text-align: right;">
                            <span class="source-badge {source_class}">{laptop['source_display']}</span><br>
                            <span style="background: {score_color}; color: white; padding: 0.3rem 0.8rem; border-radius: 20px; font-weight: bold; margin-top: 0.5rem; display: inline-block;">
                                ⭐ {laptop['score']:.1f}/100
                            </span>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Fiyat ve temel bilgiler
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**💰 Fiyat:** {laptop['price']:,} TL")
                        st.markdown(f"**🏢 Marka:** {laptop['brand'].title()}")
                    with col2:
                        st.markdown(f"**🖥️ Ekran:** {laptop['screen_size']}\"")
                        st.markdown(f"**🖥️ OS:** {laptop['os']}")
                    with col3:
                        category = "🎮 Gaming" if laptop['is_gaming'] else "🎒 Ultrabook" if laptop['is_ultrabook'] else "💼 İş Laptopı"
                        st.markdown(f"**📂 Kategori:** {category}")
                    
                    # Teknik özellikler
                    st.markdown("**⚙️ Teknik Özellikler:**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"🧠 **CPU:** {laptop['cpu_clean'].upper()} (Skor: {laptop['cpu_score']})")
                        st.write(f"🎮 **GPU:** {laptop['gpu_clean'].upper()} (Skor: {laptop['gpu_score']})")
                    with col2:
                        st.write(f"💾 **RAM:** {laptop['ram_gb']} GB")
                        st.write(f"💿 **SSD:** {laptop['ssd_gb']} GB")
                    with col3:
                        perf_score = (laptop['gpu_score'] * 0.6 + laptop['cpu_score'] * 0.4)
                        st.write(f"⚡ **Performans:** {perf_score:.0f}/100")
                        st.write(f"⭐ **Marka Skoru:** {laptop['brand_score']:.2f}")
                    
                    # Öne çıkan özellikler
                    features = []
                    if laptop['is_gaming']:
                        features.append("🎮 Gaming performansı")
                    if laptop['is_ultrabook']:
                        features.append("🎒 Kompakt ve hafif")
                    if laptop['is_workstation']:
                        features.append("💼 İş istasyonu seviyesi")
                    if laptop['ram_gb'] >= 16:
                        features.append("⚡ Yüksek RAM kapasitesi")
                    if laptop['ssd_gb'] >= 1000:
                        features.append("💾 Geniş depolama")
                    if laptop['brand_score'] >= 0.85:
                        features.append("⭐ Güvenilir marka")
                    
                    if features:
                        st.success("✨ **Öne Çıkan Özellikler:** " + " • ".join(features[:3]))
                    
                    # Neden öneriliyor
                    explanation = []
                    ideal_price = (min_budget + max_budget) / 2
                    price_ratio = laptop['price'] / ideal_price
                    
                    if price_ratio < 0.9:
                        explanation.append("ekonomik seçim")
                    elif price_ratio > 1.1:
                        explanation.append("yüksek değer")
                    else:
                        explanation.append("bütçeye uygun")
                    
                    if laptop['score'] >= 70:
                        explanation.append("yüksek genel puan")
                    
                    purpose_match = {
                        'oyun': laptop['is_gaming'],
                        'taşınabilirlik': laptop['is_ultrabook'],
                        'üretkenlik': laptop['is_workstation'],
                        'tasarım': laptop['is_gaming'] or laptop['is_workstation']
                    }
                    
                    if purpose_match.get(purpose, False):
                        explanation.append(f"{purpose} için ideal")
                    
                    st.info(f"💡 **Neden önerdik:** {', '.join(explanation).capitalize()}.")
                    
                    # Butonlar
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"[🔗 Ürünü İncele]({laptop['url']})", unsafe_allow_html=True)
                    with col2:
                        if st.button(f"💖 Favorilere Ekle", key=f"fav_{idx}"):
                            if 'favorites' not in st.session_state:
                                st.session_state.favorites = []
                            st.session_state.favorites.append({
                                'name': laptop['name'],
                                'price': laptop['price'],
                                'source': laptop['source_display'],
                                'url': laptop['url']
                            })
                            st.success("✅ Favorilere eklendi!")
                    
                    st.markdown("---")
            
            # Karşılaştırma tablosu
            if len(top_laptops) > 1:
                with st.expander("📊 Detaylı Karşılaştırma"):
                    comparison_df = top_laptops[['name', 'price', 'score', 'source_display', 'cpu_clean', 'gpu_clean', 'ram_gb', 'ssd_gb']].copy()
                    comparison_df.columns = ['Model', 'Fiyat', 'Puan', 'Kaynak', 'CPU', 'GPU', 'RAM', 'SSD']
                    comparison_df['Fiyat'] = comparison_df['Fiyat'].apply(lambda x: f"{x:,} TL")
                    comparison_df['Puan'] = comparison_df['Puan'].apply(lambda x: f"{x:.1f}")
                    comparison_df['RAM'] = comparison_df['RAM'].apply(lambda x: f"{x} GB")
                    comparison_df['SSD'] = comparison_df['SSD'].apply(lambda x: f"{x} GB")
                    st.dataframe(comparison_df, use_container_width=True, hide_index=True)
    
    with tab2:
        st.header("🔥 Günün Fırsat Ürünleri")
        
        with st.spinner("🔍 Fırsat ürünler tespit ediliyor..."):
            deals = find_deal_laptops(df)
        
        if deals.empty:
            st.warning("💔 Şu anda fırsat ürün bulunamadı.")
        else:
            st.success(f"🎯 {len(deals)} fırsat ürün bulundu!")
            
            # Fırsat metrikleri
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("🔥 Fırsat Sayısı", len(deals))
            with col2:
                avg_discount = deals['discount_percentage'].mean()
                st.metric("📉 Ort. İndirim", f"%{avg_discount:.1f}")
            with col3:
                max_discount = deals['discount_percentage'].max()
                st.metric("🎯 Max İndirim", f"%{max_discount:.1f}")
            with col4:
                min_price = deals['price'].min()
                st.metric("💰 En Uygun", f"{min_price:,} TL")
            
            # Fırsat ürünleri
            for idx, (_, deal) in enumerate(deals.head(10).iterrows(), 1):
                deal_level = "🔥 SÜPER FIRSAT" if deal['discount_percentage'] >= 30 else "⭐ İYİ FIRSAT"
                deal_color = "#e74c3c" if deal['discount_percentage'] >= 30 else "#f39c12"
                
                st.markdown(f"""
                <div style="background: linear-gradient(45deg, {deal_color}, {deal_color}aa); color: white; padding: 1rem; border-radius: 10px; margin: 1rem 0;">
                    <h4>#{idx} {deal['name']}</h4>
                    <div style="display: flex; justify-content: space-between;">
                        <div><strong>{deal_level}</strong><br>
                        <strong>💰 {deal['price']:,} TL</strong> | 
                        <strong>📉 %{deal['discount_percentage']:.0f} İndirim</strong></div>
                        <div style="text-align: right;">
                            <span style="background: rgba(255,255,255,0.2); padding: 0.5rem; border-radius: 8px;">
                                Kaynak: {deal['source_display']}<br>
                                Fırsat Skoru: {deal['deal_score']:.0f}
                            </span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"🧠 **CPU:** {deal['cpu_clean'].upper()}")
                    st.write(f"🎮 **GPU:** {deal['gpu_clean'].upper()}")
                with col2:
                    st.write(f"💾 **RAM:** {deal['ram_gb']} GB")
                    st.write(f"💿 **SSD:** {deal['ssd_gb']} GB")
                with col3:
                    st.write(f"🖥️ **Ekran:** {deal['screen_size']}\"")
                    st.write(f"🏢 **Marka:** {deal['brand'].title()}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"[🛒 Fırsatı Kaçırma!]({deal['url']})", unsafe_allow_html=True)
                with col2:
                    if st.button("📋 Karşılaştır", key=f"deal_compare_{idx}"):
                        st.info("Karşılaştırma özelliği yakında!")
                
                st.markdown("---")
    
    with tab3:
        st.header("📊 Pazar Analizi ve İstatistikler")
        
        # Genel istatistikler
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 Toplam Laptop", len(df))
        with col2:
            st.metric("💰 Ortalama Fiyat", f"{df['price'].mean():,.0f} TL")
        with col3:
            gaming_count = df['is_gaming'].sum()
            st.metric("🎮 Gaming Laptop", f"{gaming_count} (%{gaming_count/len(df)*100:.1f})")
        with col4:
            sources_count = len(df['source'].unique())
            st.metric("🛒 Veri Kaynağı", sources_count)
        
        # Grafikler
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("💰 Fiyat Dağılımı")
            fig_price = px.histogram(
                df, x='price', nbins=30,
                title="Laptop Fiyat Dağılımı",
                labels={'price': 'Fiyat (TL)', 'count': 'Laptop Sayısı'},
                color_discrete_sequence=['#3498db']
            )
            fig_price.update_layout(showlegend=False)
            st.plotly_chart(fig_price, use_container_width=True)
        
        with col2:
            st.subheader("🏢 Marka Dağılımı")
            brand_counts = df['brand'].value_counts().head(8)
            fig_brand = px.pie(
                values=brand_counts.values,
                names=[b.title() for b in brand_counts.index],
                title="En Popüler Markalar"
            )
            st.plotly_chart(fig_brand, use_container_width=True)
        
        # Kaynak analizi
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🛒 Kaynak Dağılımı")
            source_counts = df['source_display'].value_counts()
            fig_source = px.bar(
                x=source_counts.index,
                y=source_counts.values,
                title="Veri Kaynağına Göre Laptop Sayısı",
                labels={'x': 'Kaynak', 'y': 'Laptop Sayısı'},
                color=source_counts.values,
                color_continuous_scale='viridis'
            )
            st.plotly_chart(fig_source, use_container_width=True)
        
        with col2:
            st.subheader("💰 Kaynak Bazında Ortalama Fiyat")
            source_price = df.groupby('source_display')['price'].mean().sort_values(ascending=False)
            fig_source_price = px.bar(
                x=source_price.index,
                y=source_price.values,
                title="Kaynağa Göre Ortalama Fiyat",
                labels={'x': 'Kaynak', 'y': 'Ortalama Fiyat (TL)'},
                color=source_price.values,
                color_continuous_scale='reds'
            )
            st.plotly_chart(fig_source_price, use_container_width=True)
        
        # GPU/CPU analizi
        st.subheader("⚡ Performans Analizi")
        
        col1, col2 = st.columns(2)
        
        with col1:
            gpu_counts = df['gpu_clean'].value_counts().head(10)
            fig_gpu = px.bar(
                x=[gpu.upper() for gpu in gpu_counts.index],
                y=gpu_counts.values,
                title="En Popüler GPU'lar",
                labels={'x': 'GPU', 'y': 'Laptop Sayısı'},
                color=gpu_counts.values,
                color_continuous_scale='plasma'
            )
            fig_gpu.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_gpu, use_container_width=True)
        
        with col2:
            cpu_counts = df['cpu_clean'].value_counts().head(8)
            fig_cpu = px.bar(
                x=[cpu.upper() for cpu in cpu_counts.index],
                y=cpu_counts.values,
                title="En Popüler CPU'lar",
                labels={'x': 'CPU', 'y': 'Laptop Sayısı'},
                color=cpu_counts.values,
                color_continuous_scale='cividis'
            )
            st.plotly_chart(fig_cpu, use_container_width=True)
        
        # RAM/SSD analizi
        col1, col2 = st.columns(2)
        
        with col1:
            ram_dist = df['ram_gb'].value_counts().sort_index()
            fig_ram = px.bar(
                x=[f"{ram} GB" for ram in ram_dist.index],
                y=ram_dist.values,
                title="RAM Kapasitesi Dağılımı",
                labels={'x': 'RAM', 'y': 'Laptop Sayısı'},
                color=ram_dist.values,
                color_continuous_scale='blues'
            )
            st.plotly_chart(fig_ram, use_container_width=True)
        
        with col2:
            ssd_dist = df['ssd_gb'].value_counts().sort_index()
            fig_ssd = px.bar(
                x=[f"{ssd} GB" for ssd in ssd_dist.index],
                y=ssd_dist.values,
                title="SSD Kapasitesi Dağılımı",
                labels={'x': 'SSD', 'y': 'Laptop Sayısı'},
                color=ssd_dist.values,
                color_continuous_scale='greens'
            )
            st.plotly_chart(fig_ssd, use_container_width=True)
        
        # Fiyat/Performans scatter
        st.subheader("💰 Fiyat vs Performans Analizi")
        df_scatter = df.copy()
        df_scatter['total_performance'] = (df_scatter['gpu_score'] * 0.6 + df_scatter['cpu_score'] * 0.4)
        
        fig_scatter = px.scatter(
            df_scatter,
            x='total_performance',
            y='price',
            color='source_display',
            size='ram_gb',
            hover_data=['name', 'brand'],
            title="Performans vs Fiyat (Boyut: RAM)",
            labels={'total_performance': 'Toplam Performans Skoru', 'price': 'Fiyat (TL)'}
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    with tab4:
        st.header("📈 Veri Seti Detayları")
        
        # Veri kaynağı bilgileri
        st.subheader("📋 Veri Kaynakları")
        source_info = df.groupby('source_display').agg({
            'name': 'count',
            'price': ['mean', 'min', 'max'],
            'ram_gb': 'mean',
            'ssd_gb': 'mean'
        }).round(0)
        
        source_info.columns = ['Laptop Sayısı', 'Ortalama Fiyat', 'Min Fiyat', 'Max Fiyat', 'Ortalama RAM', 'Ortalama SSD']
        st.dataframe(source_info, use_container_width=True)
        
        # En pahalı ve en ucuz laptoplar
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("💎 En Pahalı Laptoplar")
            expensive = df.nlargest(5, 'price')[['name', 'price', 'source_display']]
            for idx, (_, laptop) in enumerate(expensive.iterrows(), 1):
                st.write(f"{idx}. **{laptop['name'][:50]}...** - {laptop['price']:,} TL ({laptop['source_display']})")
        
        with col2:
            st.subheader("💰 En Uygun Laptoplar")
            cheap = df.nsmallest(5, 'price')[['name', 'price', 'source_display']]
            for idx, (_, laptop) in enumerate(cheap.iterrows(), 1):
                st.write(f"{idx}. **{laptop['name'][:50]}...** - {laptop['price']:,} TL ({laptop['source_display']})")
        
        # Gaming laptoplar
        gaming_laptops = df[df['is_gaming']].copy()
        if not gaming_laptops.empty:
            st.subheader("🎮 Gaming Laptop İstatistikleri")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Gaming Laptop Sayısı", len(gaming_laptops))
            with col2:
                st.metric("Ortalama Gaming Fiyatı", f"{gaming_laptops['price'].mean():,.0f} TL")
            with col3:
                most_popular_gpu = gaming_laptops['gpu_clean'].mode()[0] if not gaming_laptops['gpu_clean'].mode().empty else "N/A"
                st.metric("En Popüler Gaming GPU", most_popular_gpu.upper())
        
        # Favoriler
        if 'favorites' in st.session_state and st.session_state.favorites:
            st.subheader("❤️ Favori Laptoplarınız")
            for idx, fav in enumerate(st.session_state.favorites, 1):
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"{idx}. **{fav['name'][:40]}...** - {fav['price']:,} TL")
                with col2:
                    st.write(f"📍 {fav['source']}")
                with col3:
                    st.markdown(f"[🔗]({fav['url']})", unsafe_allow_html=True)
            
            if st.button("🗑️ Favorileri Temizle"):
                st.session_state.favorites = []
                st.success("✅ Favoriler temizlendi!")
        
        # Ham veri görüntüleme
        with st.expander("🔍 Ham Veri Önizlemesi (İlk 100 satır)"):
            display_cols = ['name', 'price', 'brand', 'source_display', 'cpu_clean', 'gpu_clean', 'ram_gb', 'ssd_gb']
            st.dataframe(df[display_cols].head(100), use_container_width=True)
        
        # Veri indirme
        if st.button("📥 İşlenmiş Veriyi İndir (CSV)"):
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="💾 CSV İndir",
                data=csv_data,
                file_name=f"laptop_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div style='text-align: center; color: #666; padding: 1rem;'>
        💻 <strong>Akıllı Laptop Öneri Sistemi</strong> | 
        📊 {len(df)} laptop analiz edildi | 
        🛒 {len(df['source'].unique())} farklı kaynak | 
        📅 Son güncelleme: {datetime.now().strftime('%d.%m.%Y %H:%M')} <br>
        🚀 Gerçek verilerle çalışan yapay zeka destekli sistem
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

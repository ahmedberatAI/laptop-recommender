import streamlit as st
import pandas as pd
import numpy as np
import re
import pickle
import time
from datetime import datetime, timedelta
from typing import Union, Optional, Dict, Any, List, Tuple
import warnings
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
from sklearn.ensemble import IsolationForest
import plotly.express as px
import plotly.graph_objects as go
warnings.filterwarnings('ignore')

# Streamlit sayfa konfigürasyonu
st.set_page_config(
    page_title="💻 Akıllı Laptop Öneri Sistemi",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS ile stil düzenlemeleri
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .deal-card {
        border: 2px solid #ff4b4b;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        background-color: #fff5f5;
    }
    
    .recommendation-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        background-color: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

class Config:
    """Uygulama konfigürasyonu"""
    # GitHub'daki veri dosyaları
    DATASET_PATHS = [
        'data/vatan_laptop_data_cleaned.csv',
        'data/amazon_final.csv', 
        'data/cleaned_incehesap_data.csv'
    ]
    
    # GPU skorları
    GPU_SCORES = {
        'rtx5090': 110, 'rtx5080': 105, 'rtx5070': 100, 'rtx5060': 85, 'rtx5050': 75,
        'rtx5000': 96, 'rtx4090': 100, 'rtx4080': 95, 'rtx3080': 88, 'rtx4070': 85,
        'rtx3070': 80, 'rtx4060': 75, 'rtx3060': 70, 'rtx4050': 60,
        'rtx3050': 55, 'rtx2060': 50, 'rtx': 45, 'gtx': 40,
        'mx550': 38, 'intel arc': 45, 'apple integrated': 35, 'intel uhd': 22,
        'intel iris xe graphics': 25, 'iris xe': 25, 'integrated': 20,
        'unknown': 30
    }
    
    # CPU skorları
    CPU_SCORES = {
        'ultra 9 275hx': 98, 'ultra 9': 100, 'ultra 7 255h': 92, 'ultra 7': 90,
        'ultra 5 155h': 83, 'ultra 5': 80, 'core ultra 9': 98, 'core ultra 7': 90,
        'core ultra 5': 83, 'ryzen ai 9 hx370': 95, 'core 5 210h': 75,
        'i9': 95, 'i7': 85, 'i5': 75, 'i3': 60,
        'ryzen 9': 95, 'ryzen 7': 85, 'ryzen 5': 75, 'ryzen 3': 60,
        'm4 pro': 94, 'm4': 88, 'm3': 85, 'm2': 80, 'm1': 75,
        'snapdragon x': 78, 'unknown': 50
    }
    
    # Marka skorları
    BRAND_SCORES = {
        'apple': 0.95, 'dell': 0.85, 'hp': 0.80, 'lenovo': 0.85,
        'asus': 0.82, 'msi': 0.80, 'acer': 0.75, 'monster': 0.70,
        'huawei': 0.78, 'samsung': 0.83, 'lg': 0.77, 'gigabyte': 0.76
    }
    
    # Puanlama ağırlıkları
    WEIGHTS = {
        'price_fit': 15,
        'price_performance': 10,
        'purpose': {
            'base': 30,
            'oyun': {'dedicated': 1.0, 'integrated': 0.1, 'apple': 0.5},
            'taşınabilirlik': {'dedicated': 0.2, 'integrated': 1.0, 'apple': 0.9},
            'üretkenlik': {'dedicated': 0.6, 'integrated': 0.4, 'apple': 1.0},
            'tasarım': {'dedicated': 0.8, 'integrated': 0.5, 'apple': 1.0},
        },
        'user_preferences': {
            'performance': 12,
            'battery': 12,
            'portability': 8,
        },
        'specs': {
            'ram': 5,
            'ssd': 5,
        },
        'brand_reliability': 8,
    }

@st.cache_data(ttl=3600)
def load_and_process_data():
    """Veriyi yükle ve işle"""
    datasets = []
    
    for i, path in enumerate(Config.DATASET_PATHS, 1):
        try:
            df = pd.read_csv(path, encoding='utf-8')
            df['data_source'] = f'dataset_{i}'
            datasets.append(df)
        except Exception as e:
            st.error(f"Veri dosyası yüklenemedi: {path} - {e}")
            continue
    
    if not datasets:
        st.error("Hiçbir veri dosyası yüklenemedi!")
        return pd.DataFrame()
    
    # Veriyi birleştir
    combined_df = pd.concat(datasets, ignore_index=True)
    
    # RTX5060 filtreleme sayacı
    rtx5060_count_before = len(combined_df[(combined_df['gpu'].str.contains('rtx5060', case=False, na=False)) & 
                                           (combined_df['price'] < 50000)])
    
    # Veri temizleme
    processed_df = clean_and_process_data(combined_df)
    
    # Session state'e filtrelenen sayıyı kaydet
    if 'rtx5060_filtered' not in st.session_state:
        st.session_state['rtx5060_filtered'] = rtx5060_count_before
    
    return processed_df

def clean_and_process_data(df):
    """Veri temizleme ve işleme"""
    # Sütun isimlerini temizle
    df.columns = df.columns.str.strip().str.lower().str.replace(r'[\s\-]+', '_', regex=True)
    
    # Duplikatları kaldır
    df = df.drop_duplicates(subset=['name', 'price'], keep='first')
    
    # Fiyatları temizle
    df['price'] = df['price'].apply(clean_price)
    
    # Ekran boyutunu temizle
    df['screen_size'] = df['screen_size'].apply(clean_screen_size)
    
    # Depolama ve RAM'i temizle
    df['ssd_gb'] = df['ssd'].apply(lambda x: normalize_storage_ram(x, is_ssd=True))
    df['ram_gb'] = df['ram'].apply(lambda x: normalize_storage_ram(x, is_ssd=False))
    
    # GPU ve CPU temizleme
    df['gpu_clean'] = df['gpu'].apply(normalize_gpu)
    df['cpu_clean'] = df['cpu'].apply(normalize_cpu)
    
    # Marka çıkarma
    df['brand'] = df['name'].apply(extract_brand)
    
    # Puanlama için sütunlar
    df['gpu_score'] = df['gpu_clean'].apply(lambda x: Config.GPU_SCORES.get(x, 30))
    df['cpu_score'] = df['cpu_clean'].apply(lambda x: Config.CPU_SCORES.get(x, 50))
    df['brand_score'] = df['brand'].apply(lambda x: Config.BRAND_SCORES.get(x, 0.70))
    
    df['is_apple'] = df['brand'] == 'apple'
    df['has_dedicated_gpu'] = ~df['gpu_clean'].isin(['integrated', 'apple integrated', 'iris xe', 'intel uhd', 'unknown'])
    
    # ⚡ RTX5060 FİLTRELEME - 50.000 TL altındaki RTX5060'ları şüpheli say
    suspicious_rtx5060 = (df['gpu_clean'] == 'rtx5060') & (df['price'] < 50000)
    df['is_suspicious_rtx5060'] = suspicious_rtx5060
    
    # Eksik verileri temizle
    df = df.dropna(subset=['price', 'ram_gb', 'ssd_gb'])
    df = df[df['price'] > 1000]  # Minimum fiyat filtresi
    
    # 🚨 RTX5060 şüphelilerini çıkar
    df = df[~df['is_suspicious_rtx5060']]
    
    return df

def clean_price(val):
    """Fiyat temizleme"""
    if pd.isna(val):
        return None
    
    price_str = str(val).strip()
    price_str = re.sub(r'[^\d,.]', '', price_str)
    
    try:
        if ',' in price_str:
            price_str = price_str.replace(',', '')
        return float(price_str)
    except:
        return None

def clean_screen_size(val):
    """Ekran boyutu temizleme"""
    if pd.isna(val):
        return None
    
    screen_str = str(val).replace('"', '').replace("'", '')
    match = re.search(r'(\d+(?:\.\d+)?)', screen_str)
    if match:
        return float(match.group(1))
    return None

def normalize_storage_ram(val, is_ssd=True):
    """SSD ve RAM normalizasyonu"""
    if pd.isna(val):
        return None
    
    val_str = str(val).upper().strip()
    
    # TB dönüşümü
    tb_match = re.search(r'(\d+(?:\.\d+)?)\s*TB', val_str)
    if tb_match:
        return int(float(tb_match.group(1)) * 1024)
    
    # GB dönüşümü
    gb_match = re.search(r'(\d+(?:\.\d+)?)\s*GB', val_str)
    if gb_match:
        return int(float(gb_match.group(1)))
    
    # Sadece sayı
    number_match = re.search(r'(\d+)', val_str)
    if number_match:
        return int(number_match.group(1))
    
    return None

def normalize_gpu(gpu_str):
    """GPU normalizasyonu"""
    if pd.isna(gpu_str):
        return 'unknown'
    
    g_low = str(gpu_str).lower()
    
    for key in sorted(Config.GPU_SCORES.keys(), key=len, reverse=True):
        if key in g_low:
            return key
    
    return 'unknown'

def normalize_cpu(cpu_str):
    """CPU normalizasyonu"""
    if pd.isna(cpu_str):
        return 'unknown'
    
    c_low = str(cpu_str).lower()
    
    for key in sorted(Config.CPU_SCORES.keys(), key=len, reverse=True):
        if key in c_low:
            return key
    
    return 'unknown'

def extract_brand(name):
    """İsimden marka çıkar"""
    name_lower = str(name).lower()
    for brand in Config.BRAND_SCORES.keys():
        if brand in name_lower:
            return brand
    return 'other'

def calculate_laptop_score(row, preferences):
    """Laptop puanını hesapla"""
    try:
        score = 0
        weights = Config.WEIGHTS
        
        # 1. Fiyat uygunluğu
        price_range = preferences['max_budget'] - preferences['min_budget']
        if price_range > 0:
            price_diff = abs(row['price'] - preferences['ideal_price'])
            price_score = weights['price_fit'] * max(0, 1 - price_diff / (price_range / 2))
        else:
            price_score = weights['price_fit']
        
        score += price_score
        
        # 2. Fiyat/performans
        performance_score = (row['gpu_score'] * 0.6 + row['cpu_score'] * 0.4) / 100
        price_ratio = preferences['ideal_price'] / row['price'] if row['price'] > 0 else 0
        score += performance_score * price_ratio * weights['price_performance']
        
        # 3. Kullanım amacı
        purpose_weights = weights['purpose'][preferences['purpose']]
        if row['is_apple']:
            multiplier = purpose_weights['apple']
        elif row['has_dedicated_gpu']:
            multiplier = purpose_weights['dedicated']
        else:
            multiplier = purpose_weights['integrated']
        
        combined_performance = (row['gpu_score'] * 0.7 + row['cpu_score'] * 0.3) / 100
        score += weights['purpose']['base'] * combined_performance * multiplier
        
        # 4. Kullanıcı tercihleri
        user_weights = weights['user_preferences']
        
        # Performans
        perf_score = (row['gpu_score'] * 0.6 + row['cpu_score'] * 0.4) / 100
        score += user_weights['performance'] * perf_score * (preferences['performance_importance'] / 5)
        
        # Taşınabilirlik ve pil
        portability_factor = 1.0
        if row['is_apple']:
            portability_factor = 0.9
        elif row['has_dedicated_gpu']:
            portability_factor = 0.4
        elif row['screen_size'] <= 14:
            portability_factor = 1.2
        
        score += user_weights['battery'] * portability_factor * (preferences['battery_importance'] / 5)
        score += user_weights['portability'] * portability_factor * (preferences['portability_importance'] / 5)
        
        # 5. Donanım puanları
        ram_score = weights['specs']['ram'] * min(row['ram_gb'] / 16, 1.0)
        ssd_score = weights['specs']['ssd'] * min(row['ssd_gb'] / 1024, 1.0)
        score += ram_score + ssd_score
        
        # 6. Marka güvenilirlik
        score += weights['brand_reliability'] * row['brand_score']
        
        return max(0, min(100, score))
        
    except Exception as e:
        return 0.0

def apply_filters(df, preferences):
    """Filtreleri uygula"""
    filtered_df = df.copy()
    
    # Fiyat filtresi
    filtered_df = filtered_df[
        (filtered_df['price'] >= preferences['min_budget']) &
        (filtered_df['price'] <= preferences['max_budget'])
    ]
    
    # Ekran boyutu filtresi
    if preferences.get('screen_preference') != 'Farketmez':
        if preferences['screen_preference'] == 'Kompakt (13-14")':
            filtered_df = filtered_df[(filtered_df['screen_size'] >= 13) & (filtered_df['screen_size'] <= 14)]
        elif preferences['screen_preference'] == 'Standart (15-16")':
            filtered_df = filtered_df[(filtered_df['screen_size'] >= 15) & (filtered_df['screen_size'] <= 16)]
        elif preferences['screen_preference'] == 'Büyük (17"+)':
            filtered_df = filtered_df[filtered_df['screen_size'] >= 17]
    
    # İşletim sistemi filtresi
    if preferences.get('os_preference') != 'Farketmez':
        if preferences['os_preference'] == 'Windows':
            filtered_df = filtered_df[filtered_df['os'].str.contains('Windows', case=False, na=False)]
        elif preferences['os_preference'] == 'macOS':
            filtered_df = filtered_df[filtered_df['is_apple'] == True]
    
    # Marka filtresi
    if preferences.get('brand_preference') and preferences['brand_preference'] != 'Farketmez':
        filtered_df = filtered_df[filtered_df['brand'] == preferences['brand_preference'].lower()]
    
    # Minimum donanım
    if preferences.get('min_ram'):
        filtered_df = filtered_df[filtered_df['ram_gb'] >= preferences['min_ram']]
    if preferences.get('min_ssd'):
        filtered_df = filtered_df[filtered_df['ssd_gb'] >= preferences['min_ssd']]
    
    return filtered_df

def get_recommendations(df, preferences):
    """Önerileri getir"""
    # Filtreleri uygula
    filtered_df = apply_filters(df, preferences)
    
    if filtered_df.empty:
        return pd.DataFrame()
    
    # Puanları hesapla
    filtered_df = filtered_df.copy()
    filtered_df['score'] = filtered_df.apply(lambda row: calculate_laptop_score(row, preferences), axis=1)
    
    # En iyileri seç
    top_laptops = filtered_df.nlargest(10, 'score')
    
    return top_laptops

def find_deal_products(df, discount_threshold=20):
    """Fırsat ürünlerini bul"""
    deals_df = df.copy()
    
    # Performans skorunu hesapla
    deals_df['performance_score'] = (deals_df['gpu_score'] * 0.6 + deals_df['cpu_score'] * 0.4)
    
    # Piyasa fiyatını hesapla
    deals_df['market_price'] = deals_df.apply(lambda row: calculate_market_price(row, deals_df), axis=1)
    
    # İndirim oranını hesapla
    deals_df['discount_percentage'] = (
        (deals_df['market_price'] - deals_df['price']) / deals_df['market_price'] * 100
    ).clip(lower=0)
    
    # Fırsatları filtrele
    deals = deals_df[deals_df['discount_percentage'] >= discount_threshold]
    
    if not deals.empty:
        deals['deal_score'] = (
            deals['discount_percentage'] + 
            (deals['performance_score'] / 100) * 10 +
            (deals['ram_gb'] / 32) * 5 +
            (deals['ssd_gb'] / 1024) * 3
        ).clip(0, 100)
        
        deals = deals.sort_values('deal_score', ascending=False)
    
    return deals

def calculate_market_price(target_row, df):
    """Piyasa fiyatını hesapla"""
    # Benzer ürünleri bul
    similar = df[
        (df['performance_score'].between(
            target_row['performance_score'] * 0.8,
            target_row['performance_score'] * 1.2
        )) &
        (df['ram_gb'].between(
            max(4, target_row['ram_gb'] - 4),
            target_row['ram_gb'] + 4
        )) &
        (df['name'] != target_row['name'])
    ]
    
    if len(similar) >= 3:
        # Aykırı değerleri temizle
        Q1 = similar['price'].quantile(0.25)
        Q3 = similar['price'].quantile(0.75)
        IQR = Q3 - Q1
        
        if IQR > 0:
            filtered_prices = similar['price'][
                (similar['price'] >= Q1 - 1.5 * IQR) &
                (similar['price'] <= Q3 + 1.5 * IQR)
            ]
            if len(filtered_prices) >= 2:
                return filtered_prices.mean()
    
    return target_row['price'] * 1.2  # Varsayılan %20 ekle

# Ana uygulama
def main():
    # Başlık
    st.markdown('<h1 class="main-header">💻 Akıllı Laptop Öneri Sistemi</h1>', unsafe_allow_html=True)
    
    # Veriyi yükle
    with st.spinner('Veriler yükleniyor...'):
        df = load_and_process_data()
    
    if df.empty:
        st.error("Veri yüklenemedi!")
        return
    
    # RTX5060 filtreleme bilgisi
    rtx5060_filtered = st.session_state.get('rtx5060_filtered', 0)
    if rtx5060_filtered > 0:
        st.info(f"ℹ️ {rtx5060_filtered} adet şüpheli RTX5060 laptop (50.000 TL altı) filtrelendi.")
    
    st.success(f"✅ {len(df)} laptop başarıyla yüklendi!")
    
    # Sidebar - Kullanıcı tercihleri
    st.sidebar.header("🔧 Tercihlerinizi Belirtin")
    
    # Bütçe
    st.sidebar.subheader("💰 Bütçe")
    min_budget = st.sidebar.number_input("Minimum Bütçe (TL)", min_value=1000, max_value=200000, value=20000, step=1000)
    max_budget = st.sidebar.number_input("Maksimum Bütçe (TL)", min_value=min_budget, max_value=300000, value=50000, step=1000)
    
    # Kullanım amacı
    st.sidebar.subheader("🎯 Kullanım Amacı")
    purpose = st.sidebar.selectbox(
        "Ne için kullanacaksınız?",
        ['oyun', 'taşınabilirlik', 'üretkenlik', 'tasarım'],
        format_func=lambda x: {
            'oyun': '🎮 Oyun (Yüksek performans)',
            'taşınabilirlik': '🎒 Taşınabilirlik (Hafif, uzun pil)',
            'üretkenlik': '💼 Üretkenlik (Ofis, geliştirme)',
            'tasarım': '🎨 Tasarım (Grafik, video)'
        }[x]
    )
    
    # Önem dereceleri
    st.sidebar.subheader("⭐ Önem Dereceleri")
    performance_importance = st.sidebar.slider("Performans", 1, 5, 4)
    battery_importance = st.sidebar.slider("Pil Ömrü", 1, 5, 3)
    portability_importance = st.sidebar.slider("Taşınabilirlik", 1, 5, 3)
    
    # Gelişmiş filtreler
    with st.sidebar.expander("🔧 Gelişmiş Filtreler"):
        screen_preference = st.selectbox(
            "Ekran Boyutu",
            ['Farketmez', 'Kompakt (13-14")', 'Standart (15-16")', 'Büyük (17"+)']
        )
        
        os_preference = st.selectbox(
            "İşletim Sistemi",
            ['Farketmez', 'Windows', 'macOS']
        )
        
        brands = ['Farketmez'] + [brand.title() for brand in Config.BRAND_SCORES.keys()]
        brand_preference = st.selectbox("Marka Tercihi", brands)
        
        min_ram = st.selectbox("Minimum RAM (GB)", [4, 8, 16, 32], index=1)
        min_ssd = st.selectbox("Minimum SSD (GB)", [128, 256, 512, 1024], index=1)
    
    # Tercihleri topla
    preferences = {
        'min_budget': min_budget,
        'max_budget': max_budget,
        'ideal_price': (min_budget + max_budget) / 2,
        'purpose': purpose,
        'performance_importance': performance_importance,
        'battery_importance': battery_importance,
        'portability_importance': portability_importance,
        'screen_preference': screen_preference,
        'os_preference': os_preference,
        'brand_preference': brand_preference,
        'min_ram': min_ram,
        'min_ssd': min_ssd
    }
    
    # Ana sekmeler
    tab1, tab2, tab3 = st.tabs(["🏆 Öneriler", "🎯 Fırsatlar", "📊 İstatistikler"])
    
    with tab1:
        st.header("🏆 Size Özel Laptop Önerileri")
        
        if st.button("✨ Önerileri Getir", type="primary"):
            with st.spinner('En iyi laptoplar aranıyor...'):
                recommendations = get_recommendations(df, preferences)
            
            if recommendations.empty:
                st.warning("Kriterlere uygun laptop bulunamadı. Filtrelerinizi gevşetmeyi deneyin.")
            else:
                st.success(f"✅ {len(recommendations)} öneri bulundu!")
                
                # Önerileri göster
                for i, (_, laptop) in enumerate(recommendations.head(5).iterrows(), 1):
                    with st.container():
                        st.markdown(f"""
                        <div class="recommendation-card">
                            <h3>🥇 {i}. {laptop['name']}</h3>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2, col3 = st.columns([1, 1, 1])
                        
                        with col1:
                            st.metric("💰 Fiyat", f"{laptop['price']:,.0f} TL")
                            st.metric("⭐ Puan", f"{laptop['score']:.1f}/100")
                        
                        with col2:
                            st.metric("🖥️ Ekran", f"{laptop['screen_size']}\"")
                            st.metric("🧠 İşlemci", laptop['cpu_clean'].upper())
                        
                        with col3:
                            st.metric("🎮 Grafik", laptop['gpu_clean'].upper())
                            st.metric("💾 RAM/SSD", f"{int(laptop['ram_gb'])}GB / {int(laptop['ssd_gb'])}GB")
                        
                        # Özellikler
                        features = []
                        if laptop['is_apple']:
                            features.append("🍎 Apple Ekosistemi")
                        if laptop['has_dedicated_gpu'] and laptop['gpu_score'] >= 80:
                            features.append("🚀 Üst Düzey Oyun")
                        elif laptop['has_dedicated_gpu']:
                            features.append("🎮 Oyun Uyumlu")
                        else:
                            features.append("🔋 Uzun Pil Ömrü")
                        
                        if laptop['ram_gb'] >= 16:
                            features.append("⚡ Güçlü Bellek")
                        if laptop['screen_size'] <= 14:
                            features.append("🎒 Taşınabilir")
                        elif laptop['screen_size'] >= 17:
                            features.append("🖥️ Büyük Ekran")
                        
                        st.markdown("**Öne Çıkan Özellikler:** " + " • ".join(features))
                        
                        # URL buton düzeltme
                        url_button_col1, url_button_col2 = st.columns([1, 3])
                        with url_button_col1:
                            if st.button(f"🔗 Ürünü İncele", key=f"btn_{i}"):
                                st.balloons()
                        with url_button_col2:
                            st.markdown(f"[🛒 **Satın Almak İçin Tıklayın**]({laptop['url']})", unsafe_allow_html=True)
                        
                        st.markdown("---")
    
    with tab2:
        st.header("🎯 Günün Fırsat Ürünleri")
        st.caption("Piyasa fiyatına göre en iyi fırsatlar")
        
        discount_threshold = st.slider("Minimum İndirim Oranı (%)", 10, 50, 20)
        
        if st.button("🔍 Fırsatları Bul", type="primary"):
            with st.spinner('Fırsatlar analiz ediliyor...'):
                deals = find_deal_products(df, discount_threshold)
            
            if deals.empty:
                st.info(f"🤷‍♂️ %{discount_threshold} ve üzeri indirimli ürün bulunamadı.")
            else:
                st.success(f"✅ {len(deals)} fırsat ürün bulundu!")
                
                # Fırsat özeti
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("🎯 Toplam Fırsat", len(deals))
                with col2:
                    st.metric("📈 Ortalama İndirim", f"%{deals['discount_percentage'].mean():.1f}")
                with col3:
                    st.metric("🔥 Maksimum İndirim", f"%{deals['discount_percentage'].max():.1f}")
                with col4:
                    total_savings = (deals['market_price'] - deals['price']).sum()
                    st.metric("💰 Toplam Tasarruf", f"{total_savings:,.0f} TL")
                
                # En iyi fırsatları göster
                st.subheader("🔥 En İyi Fırsatlar")
                
                for i, (_, deal) in enumerate(deals.head(5).iterrows(), 1):
                    with st.container():
                        # Fırsat seviyesi
                        if deal['deal_score'] >= 80:
                            deal_level = "🔥 MUHTEŞEM FIRSAT"
                            border_color = "#ff4b4b"
                        elif deal['deal_score'] >= 60:
                            deal_level = "⭐ ÇOK İYİ FIRSAT"
                            border_color = "#ff8c00"
                        else:
                            deal_level = "✨ İYİ FIRSAT"
                            border_color = "#ffa500"
                        
                        st.markdown(f"""
                        <div style="border: 2px solid {border_color}; border-radius: 10px; padding: 1.5rem; margin: 1rem 0; background-color: #fff5f5;">
                            <h3>{deal_level} - {deal['name']}</h3>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2, col3 = st.columns([1, 1, 1])
                        
                        with col1:
                            st.metric("💰 Fiyat", f"{deal['price']:,.0f} TL")
                            st.metric("📊 Piyasa Fiyatı", f"{deal['market_price']:,.0f} TL")
                        
                        with col2:
                            st.metric("📉 İndirim", f"%{deal['discount_percentage']:.1f}")
                            st.metric("🏆 Fırsat Skoru", f"{deal['deal_score']:.1f}/100")
                        
                        with col3:
                            savings = deal['market_price'] - deal['price']
                            st.metric("💵 Tasarruf", f"{savings:,.0f} TL")
                            st.metric("🎮 GPU/CPU", f"{deal['gpu_score']}/{deal['cpu_score']}")
                        
                        # Neden fırsat?
                        reasons = []
                        if deal['discount_percentage'] > 20:
                            reasons.append(f"Piyasadan %{deal['discount_percentage']:.0f} ucuz")
                        if deal['gpu_score'] >= 70 and deal['price'] < 40000:
                            reasons.append("Oyun performansı uygun fiyat")
                        if deal['ram_gb'] >= 16:
                            reasons.append("Yüksek RAM kapasitesi")
                        
                        st.markdown("**💡 Neden fırsat?** " + " • ".join(reasons))
                        
                        # URL buton düzeltme - Fırsatlar
                        deal_url_col1, deal_url_col2 = st.columns([1, 3])
                        with deal_url_col1:
                            if st.button(f"🛒 Ürünü İncele", key=f"deal_{i}"):
                                st.balloons()
                        with deal_url_col2:
                            st.markdown(f"[🔥 **FIRSATI KAÇIRMA - TİKLA!**]({deal['url']})", unsafe_allow_html=True)
                        
                        st.markdown("---")
    
    with tab3:
        st.header("📊 Pazar İstatistikleri")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Fiyat Dağılımı")
            
            # Fiyat histogram
            fig_price = px.histogram(df, x='price', nbins=30, 
                                   title='Laptop Fiyat Dağılımı',
                                   labels={'price': 'Fiyat (TL)', 'count': 'Adet'})
            fig_price.update_layout(showlegend=False)
            st.plotly_chart(fig_price, use_container_width=True)
            
            # Marka dağılımı
            brand_counts = df['brand'].value_counts().head(10)
            fig_brand = px.pie(values=brand_counts.values, names=brand_counts.index,
                              title='En Popüler Markalar')
            st.plotly_chart(fig_brand, use_container_width=True)
        
        with col2:
            st.subheader("🎮 Performans İstatistikleri")
            
            # GPU skorları
            gpu_avg = df.groupby('gpu_clean')['gpu_score'].mean().sort_values(ascending=False).head(10)
            fig_gpu = px.bar(x=gpu_avg.values, y=gpu_avg.index,
                            title='Ortalama GPU Skorları',
                            labels={'x': 'GPU Skoru', 'y': 'GPU Modeli'},
                            orientation='h')
            st.plotly_chart(fig_gpu, use_container_width=True)
            
            # RAM/SSD dağılımı
            st.subheader("💾 Donanım Dağılımı")
            
            col_ram, col_ssd = st.columns(2)
            with col_ram:
                ram_dist = df['ram_gb'].value_counts().sort_index()
                fig_ram = px.bar(x=ram_dist.index, y=ram_dist.values,
                               title='RAM Dağılımı',
                               labels={'x': 'RAM (GB)', 'y': 'Adet'})
                st.plotly_chart(fig_ram, use_container_width=True)
            
            with col_ssd:
                ssd_dist = df['ssd_gb'].value_counts().sort_index()
                fig_ssd = px.bar(x=ssd_dist.index, y=ssd_dist.values,
                               title='SSD Dağılımı',
                               labels={'x': 'SSD (GB)', 'y': 'Adet'})
                st.plotly_chart(fig_ssd, use_container_width=True)
        
        # Genel istatistikler
        st.subheader("📋 Genel İstatistikler")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📱 Toplam Laptop", len(df))
            st.metric("💰 Ortalama Fiyat", f"{df['price'].mean():,.0f} TL")
        
        with col2:
            st.metric("🔥 En Pahalı", f"{df['price'].max():,.0f} TL")
            st.metric("💸 En Ucuz", f"{df['price'].min():,.0f} TL")
        
        with col3:
            gaming_count = len(df[df['has_dedicated_gpu']])
            st.metric("🎮 Oyun Laptopları", f"{gaming_count} (%{gaming_count/len(df)*100:.1f})")
            st.metric("🍎 Apple Laptopları", len(df[df['is_apple']]))
        
        with col4:
            avg_screen = df['screen_size'].mean()
            st.metric("📺 Ortalama Ekran", f"{avg_screen:.1f}\"")
            premium_count = len(df[df['price'] > 50000])
            st.metric("💎 Premium (50K+)", f"{premium_count} adet")
        
        # Fiyat/performans analizi
        st.subheader("📊 Fiyat/Performans Analizi")
        
        # Fiyat vs performans scatter plot
        df['total_performance'] = (df['gpu_score'] + df['cpu_score']) / 2
        
        fig_scatter = px.scatter(df, x='price', y='total_performance',
                               color='brand', size='ram_gb',
                               hover_data=['name', 'gpu_clean', 'cpu_clean'],
                               title='Fiyat vs Performans',
                               labels={'price': 'Fiyat (TL)', 'total_performance': 'Toplam Performans Skoru'})
        
        st.plotly_chart(fig_scatter, use_container_width=True)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 2rem;'>
        <p>💻 <strong>Akıllı Laptop Öneri Sistemi</strong></p>
        <p>AI destekli analiz ile size en uygun laptop'u bulun!</p>
        <p><small>Veriler gerçek zamanlı olarak güncellenmektedir.</small></p>
    </div>
    """,
    unsafe_allow_html=True
)

if __name__ == "__main__":
    main()

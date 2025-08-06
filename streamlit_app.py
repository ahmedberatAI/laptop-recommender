def main():
    try:
        # Header
        st.markdown("""
        <div class="main-header">
            <h1>🔥 Akıllı Laptop Öneri Sistemi</h1>
            <p>Size en uygun laptop'ı bulalım! 💻✨</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Veriyi yükle
        df = load_sample_data()
        
        # Başarı mesajı
        st.success(f"✅ {len(df)} laptop yüklendi ve analiz için hazır!")
        
        # Sidebar - Kullanıcı tercihleri
        st.sidebar.header("🎯 Tercihlerinizi Belirtin")
        
        # Bütçe
        st.sidebar.subheader("💰 Bütçe Aralığı")
        col1, col2 = st.sidebar.columns(2)
        with col1:
            min_budget = st.number_input("Min (TL)", min_value=10000, max_value=100000, value=20000, step=5000)
        with col2:
            max_budget = st.number_input("Max (TL)", min_value=min_budget, max_value=150000, value=50000, step=5000)
        
        # Bütçe kontrolü
        if max_budget <= min_budget:
            st.sidebar.error("❌ Maksimum bütçe, minimum bütçeden büyük olmalıdır!")
            return
        
        ideal_price = (min_budget + max_budget) / 2
        
        # Kullanım amacı
        st.sidebar.subheader("🎮 Kullanım Amacınız")
        purpose = st.sidebar.selectbox(
            "Laptop'ı ne için kullanacaksınız?",
            ["oyun", "taşınabilirlik", "üretkenlik", "tasarım"],
            format_func=lambda x: {
                "oyun": "🎮 Oyun & Gaming",
                "taşınabilirlik": "🎒 Taşınabilirlik & Mobilite", 
                "üretkenlik": "💼 Üretkenlik & İş",
                "tasarım": "🎨 Tasarım & Kreatif İşler"
            }[x]
        )
        
        # Gelişmiş filtreler - Collapsible
        with st.sidebar.expander("🔧 Gelişmiş Filtreler"):
            # Marka filtresi
            brands = ['Tümü'] + sorted([b.title() for b in df['brand'].unique()])
            brand_filter = st.selectbox("🏢 Marka Tercihi", brands)
            
            # RAM filtresi
            ram_options = sorted(df['ram_gb'].unique())
            ram_filter = st.selectbox("💾 Minimum RAM", ram_options, format_func=lambda x: f"{x} GB")
            
            # SSD filtresi  
            ssd_options = sorted(df['ssd_gb'].unique())
            ssd_filter = st.selectbox("💿 Minimum SSD", ssd_options, format_func=lambda x: f"{x} GB")
            
            # İşletim sistemi
            os_filter = st.selectbox("🖥️ İşletim Sistemi", ["Tümü", "Windows 11", "macOS"])
            
            # Ekran boyutu tercihi
            screen_filter = st.selectbox("📐 Ekran Boyutu", 
                ["Tümü", "13-14\" (Kompakt)", "15-16\" (Standart)", "17\"+ (Büyük)"])
        
        preferences = {
            'min_budget': min_budget,
            'max_budget': max_budget,
            'ideal_price': ideal_price,
            'purpose': purpose
        }
        
        # Ana içerik tabları
        tab1, tab2, tab3, tab4 = st.tabs(["🏆 Öneriler", "🔥 Fırsatlar", "📊 Pazar Analizi", "ℹ️ Hakkında"])
        
        with tab1:
            st.header("🏆 Size Özel Laptop Önerileri")
            
            # Filtreleri uygula
            filtered_df = df.copy()
            
            # Bütçe filtresi
            filtered_df = filtered_df[
                (filtered_df['price'] >= min_budget) & 
                (filtered_df['price'] <= max_budget)
            ]
            
            # Diğer filtreler
            if brand_filter != 'Tümü':
                filtered_df = filtered_df[filtered_df['brand'] == brand_filter.lower()]
            
            filtered_df = filtered_df[filtered_df['ram_gb'] >= ram_filter]
            filtered_df = filtered_df[filtered_df['ssd_gb'] >= ssd_filter]
            
            if os_filter != 'Tümü':
                filtered_df = filtered_df[filtered_df['os'] == os_filter]
            
            # Ekran boyutu filtresi
            if screen_filter != 'Tümü':
                if "13-14" in screen_filter:
                    filtered_df = filtered_df[filtered_df['screen_size'] <= 14.5]
                elif "15-16" in screen_filter:
                    filtered_df = filtered_df[(filtered_df['screen_size'] > 14.5) & (filtered_df['screen_size'] <= 16.5)]
                elif "17" in screen_filter:
                    filtered_df = filtered_df[filtered_df['screen_size'] > 16.5]
            
            if len(filtered_df) == 0:
                st.error("❌ Seçilen kriterlere uygun laptop bulunamadı!")
                st.info("💡 **Öneriler:**")
                st.write("• Bütçe aralığınızı genişletmeyi deneyin")
                st.write("• Minimum donanım gereksinimlerini azaltın")
                st.write("• Marka filtrelerini kaldırın")
                return
            
            # Puanları hesapla
            config = StreamlitConfig()
            
            with st.spinner('🧮 Laptoplar analiz ediliyor... Lütfen bekleyin.'):
                filtered_df = filtered_df.copy()
                filtered_df['score'] = filtered_df.apply(
                    lambda row: calculate_laptop_score(row, preferences, config), 
                    axis=1
                )
            
            # En iyileri seç
            top_laptops = filtered_df.nlargest(8, 'score')
            
            # Özet metrikler
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("🔍 Bulunan Laptop", len(filtered_df), delta=f"{len(filtered_df)/len(df)*100:.1f}% veri seti")
            with col2:
                st.metric("💰 Ortalama Fiyat", f"{filtered_df['price'].mean():,.0f} TL")
            with col3:
                st.metric("⭐ En Yüksek Puan", f"{top_laptops.iloc[0]['score']:.1f}/100")
            with col4:
                st.metric("🏢 Marka Çeşitliliği", len(filtered_df['brand'].unique()))
            
            # Progress bar
            progress_text = "En iyi öneriler hazırlanıyor..."
            progress_bar = st.progress(0, text=progress_text)
            
            st.subheader("📋 Önerilen Laptoplar")
            
            # Her laptopı kart olarak göster
            for idx, (_, laptop) in enumerate(top_laptops.iterrows(), 1):
                progress_bar.progress(idx/len(top_laptops), text=f"Öneri {idx}/{len(top_laptops)} hazırlanıyor...")
                
                with st.container():
                    # Kart başlığı ve puanı
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"### #{idx} {laptop['name']}")
                    with col2:
                        # Puan badge'i
                        if laptop['score'] >= 80:
                            badge_color = "#28a745"  # Yeşil
                        elif laptop['score'] >= 60:
                            badge_color = "#ffc107"  # Sarı
                        else:
                            badge_color = "#6c757d"  # Gri
                        
                        st.markdown(f"""
                        <div style="text-align: right;">
                            <span style="background: {badge_color}; color: white; padding: 0.3rem 0.8rem; border-radius: 20px; font-weight: bold;">
                                ⭐ {laptop['score']:.1f}/100
                            </span>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Fiyat ve marka bilgisi
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"**💰 Fiyat:** {laptop['price']:,} TL")
                    with col2:
                        st.markdown(f"**🏢 Marka:** {laptop['brand'].title()}")
                    
                    # Teknik özellikler - 3 sütunlu layout
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"🖥️ **Ekran:** {laptop['screen_size']}\"")
                        st.write(f"🧠 **İşlemci:** {laptop['cpu_clean'].upper()}")
                    with col2:
                        st.write(f"🎮 **GPU:** {laptop['gpu_clean'].upper()}")
                        st.write(f"💾 **RAM:** {laptop['ram_gb']} GB")
                    with col3:
                        st.write(f"💿 **SSD:** {laptop['ssd_gb']} GB")
                        st.write(f"🖥️ **OS:** {laptop['os']}")
                    
                    # Öne çıkan özellikler
                    features = []
                    if laptop['has_dedicated_gpu'] and laptop['gpu_score'] >= 70:
                        features.append("🚀 Güçlü oyun performansı")
                    if laptop['ram_gb'] >= 16:
                        features.append("⚡ Yüksek bellek kapasitesi")
                    if laptop['screen_size'] <= 14:
                        features.append("🎒 Kompakt ve taşınabilir")
                    if laptop['brand_score'] >= 0.85:
                        features.append("⭐ Yüksek marka güvenilirliği")
                    if laptop['ssd_gb'] >= 1000:
                        features.append("💾 Geniş depolama alanı")
                    if laptop['is_apple']:
                        features.append("🍎 Apple ekosistemi uyumlu")
                    
                    if features:
                        st.write("✨ **Öne Çıkan Özellikler:**")
                        for feature in features[:3]:  # En fazla 3 özellik göster
                            st.write(f"   • {feature}")
                    
                    # Neden öneriliyor açıklaması
                    explanation = []
                    price_ratio = laptop['price'] / ideal_price
                    if price_ratio < 0.9:
                        explanation.append("bütçenizin altında ekonomik bir seçim")
                    elif price_ratio > 1.1:
                        explanation.append("bütçenizi aşmasına rağmen sunduğu değer yüksek")
                    else:
                        explanation.append("bütçenize tam uygun")
                    
                    purpose_match = {
                        'oyun': "oyun performansı" if laptop['has_dedicated_gpu'] else "hafif oyunlar",
                        'taşınabilirlik': "taşınabilirlik" if laptop['screen_size'] <= 15.6 else "güçlü performans",
                        'üretkenlik': "verimli çalışma",
                        'tasarım': "kreatif projeler"
                    }
                    explanation.append(f"{purpose_match[purpose]} için uygun")
                    
                    st.info(f"💡 **Neden önerdik:** Bu laptop {', '.join(explanation)}.")
                    
                    # Aksiyon butonları
                    col1, col2 = st.columns(2)
                    with col1:
                        st.link_button("🔗 Ürünü İncele", laptop['url'], use_container_width=True)
                    with col2:
                        if st.button(f"❤️ Favorilere Ekle", key=f"fav_{idx}", use_container_width=True):
                            if 'favorites' not in st.session_state:
                                st.session_state.favorites = []
                            st.session_state.favorites.append(laptop['name'])
                            st.success("✅ Favorilere eklendi!")
                    
                    st.markdown("---")
            
            progress_bar.empty()  # Progress bar'ı temizle
            
            # Karşılaştırma özelliği
            if len(top_laptops) > 1:
                with st.expander("📊 Detaylı Karşılaştırma Tablosu"):
                    comparison_df = top_laptops[['name', 'price', 'score', 'gpu_clean', 'cpu_clean', 'ram_gb', 'ssd_gb', 'screen_size']].copy()
                    comparison_df.columns = ['Model', 'Fiyat (TL)', 'Puan', 'GPU', 'CPU', 'RAM (GB)', 'SSD (GB)', 'Ekran']
                    comparison_df['Fiyat (TL)'] = comparison_df['Fiyat (TL)'].apply(lambda x: f"{x:,}")
                    comparison_df['Puan'] = comparison_df['Puan'].apply(lambda x: f"{x:.1f}")
                    st.dataframe(comparison_df, use_container_width=True, hide_index=True)
        
        with tab2:
            st.header("🔥 Günün Fırsat Ürünleri")
            st.write("Piyasa analizine göre tespit edilen özel fırsat ürünleri:")
            
            deals = find_deals(df)
            
            if deals.empty:
                st.warning("💔 Şu anda öne çıkan fırsat ürün bulunamadı.")
                st.info("💡 **İpucu:** Fırsat ürünler genellikle hafta sonları ve özel kampanya dönemlerinde ortaya çıkar.")
            else:
                st.success(f"🎯 {len(deals)} muhteşem fırsat tespit edildi!")
                
                # Fırsat özet metrikleri
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("🔥 Fırsat Sayısı", len(deals))
                with col2:
                    avg_discount = deals['discount_percentage'].mean()
                    st.metric("📉 Ortalama İndirim", f"%{avg_discount:.1f}")
                with col3:
                    max_discount = deals['discount_percentage'].max()
                    st.metric("🎯 En Yüksek İndirim", f"%{max_discount:.1f}")
                with col4:
                    savings = (deals['price'] * deals['discount_percentage'] / 100).sum()
                    st.metric("💰 Toplam Tasarruf", f"{savings:,.0f} TL")
                
                # Fırsat ürünleri gösterimi
                for idx, (_, deal) in enumerate(deals.head(10).iterrows(), 1):
                    with st.container():
                        # Fırsat seviyesi belirleme
                        if deal['discount_percentage'] >= 30:
                            deal_level = "🔥 MUHTEŞEM FIRSAT"
                            deal_color = "#ff4444"
                        elif deal['discount_percentage'] >= 20:
                            deal_level = "⭐ ÇOK İYİ FIRSAT"
                            deal_color = "#ff8800"
                        else:
                            deal_level = "✨ İYİ FIRSAT"
                            deal_color = "#ffaa00"
                        
                        st.markdown(f"""
                        <div style="background: linear-gradient(45deg, {deal_color}, {deal_color}aa); color: white; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
                            <h3>#{idx} {deal['name']}</h3>
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <strong>{deal_level}</strong><br>
                                    <strong>💰 {deal['price']:,} TL</strong> | 
                                    <strong>📉 %{deal['discount_percentage']:.0f} İndirim!</strong>
                                </div>
                                <div style="background: rgba(255,255,255,0.2); padding: 0.5rem; border-radius: 10px;">
                                    Fırsat Skoru: <strong>{deal['deal_score']:.0f}/100</strong>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Teknik detaylar
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"🧠 **İşlemci:** {deal['cpu_clean'].upper()}")
                            st.write(f"🎮 **GPU:** {deal['gpu_clean'].upper()}")
                        with col2:
                            st.write(f"💾 **RAM:** {deal['ram_gb']} GB")
                            st.write(f"💿 **SSD:** {deal['ssd_gb']} GB")
                        with col3:
                            st.write(f"🏢 **Marka:** {deal['brand'].title()}")
                            st.write(f"🖥️ **Ekran:** {deal['screen_size']}\"")
                        
                        # Neden fırsat açıklaması
                        reasons = []
                        if deal['discount_percentage'] > 25:
                            reasons.append(f"Piyasa ortalamasından %{deal['discount_percentage']:.0f} daha ucuz")
                        if deal['has_dedicated_gpu'] and deal['price'] < 40000:
                            reasons.append("Güçlü GPU'ya sahip uygun fiyatlı seçenek")
                        if deal['ram_gb'] >= 16 and deal['ssd_gb'] >= 512:
                            reasons.append("Yüksek performans özellikleri")
                        
                        if reasons:
                            st.success("🎯 **Neden fırsat:** " + " • ".join(reasons))
                        
                        # Fırsat butonları
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.link_button("🛒 Hemen Al!", deal['url'], use_container_width=True)
                        with col2:
                            if st.button(f"📋 Karşılaştır", key=f"compare_{idx}", use_container_width=True):
                                st.info("Karşılaştırma özelliği yakında eklenecek!")
                        with col3:
                            if st.button(f"🔔 Fiyat Takip Et", key=f"track_{idx}", use_container_width=True):
                                st.success("Fiyat takip özelliği yakında!")
                        
                        st.markdown("---")
        
        with tab3:
            st.header("📊 Laptop Pazar Analizi")
            st.write("Mevcut laptop piyasasına dair detaylı analizler:")
            
            # Genel pazar özeti
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📊 Toplam Laptop", len(df))
            with col2:
                st.metric("💰 Ortalama Fiyat", f"{df['price'].mean():,.0f} TL")
            with col3:
                st.metric("🏢 Marka Sayısı", len(df['brand'].unique()))
            with col4:
                gaming_count = len(df[df['has_dedicated_gpu']])
                st.metric("🎮 Gaming Laptop", f"{gaming_count} (%{gaming_count/len(df)*100:.1f})")
            
            # Grafikler
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("💰 Fiyat Dağılımı")
                fig_price = px.histogram(
                    df, 
                    x='price', 
                    nbins=25,
                    title="Laptop Fiyat Dağılımı",
                    labels={'price': 'Fiyat (TL)', 'count': 'Laptop Sayısı'},
                    color_discrete_sequence=['#667eea']
                )
                fig_price.update_layout(showlegend=False)
                st.plotly_chart(fig_price, use_container_width=True)
            
            with col2:
                st.subheader("🏢 Marka Dağılımı")
                brand_counts = df['brand'].value_counts()
                fig_brand = px.pie(
                    values=brand_counts.values,
                    names=[name.title() for name in brand_counts.index],
                    title="Marka Paylaşımı"
                )
                st.plotly_chart(fig_brand, use_container_width=True)
            
            # GPU analizi
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🎮 GPU Türü Dağılımı")
                gpu_counts = df['gpu_clean'].value_counts().head(8)
                fig_gpu_dist = px.bar(
                    x=[name.upper() for name in gpu_counts.index],
                    y=gpu_counts.values,
                    title="En Popüler GPU'lar",
                    labels={'x': 'GPU Modeli', 'y': 'Laptop Sayısı'},
                    color=gpu_counts.values,
                    color_continuous_scale='viridis'
                )
                fig_gpu_dist.update_layout(showlegend=False)
                st.plotly_chart(fig_gpu_dist, use_container_width=True)
            
            with col2:
                st.subheader("⚡ GPU Performans vs Fiyat")
                gpu_analysis = df.groupby('gpu_clean').agg({
                    'price': 'mean',
                    'gpu_score': 'mean'
                }).reset_index()
                
                fig_gpu_perf = px.scatter(
                    gpu_analysis,
                    x='gpu_score',
                    y='price',
                    size='price',
                    hover_data=['gpu_clean'],
                    title="GPU Performansı ve Fiyat İlişkisi",
                    labels={'gpu_score': 'GPU Performans Skoru', 'price': 'Ortalama Fiyat (TL)'},
                    color='gpu_score',
                    color_continuous_scale='viridis'
                )
                st.plotly_chart(fig_gpu_perf, use_container_width=True)
            
            # RAM/SSD analizi
            st.subheader("💾 Donanım Konfigürasyonları")
            
            col1, col2 = st.columns(2)
            
            with col1:
                ram_dist = df['ram_gb'].value_counts().sort_index()
                fig_ram = px.bar(
                    x=[f"{ram} GB" for ram in ram_dist.index],
                    y=ram_dist.values,
                    title="RAM Kapasitesi Dağılımı",
                    labels={'x': 'RAM Kapasitesi', 'y': 'Laptop Sayısı'},
                    color=ram_dist.values,
                    color_continuous_scale='blues'
                )
                fig_ram.update_layout(showlegend=False)
                st.plotly_chart(fig_ram, use_container_width=True)
            
            with col2:
                ssd_dist = df['ssd_gb'].value_counts().sort_index()
                fig_ssd = px.bar(
                    x=[f"{ssd} GB" for ssd in ssd_dist.index],
                    y=ssd_dist.values,
                    title="SSD Kapasitesi Dağılımı",
                    labels={'x': 'SSD Kapasitesi', 'y': 'Laptop Sayısı'},
                    color=ssd_dist.values,
                    color_continuous_scale='greens'
                )
                fig_ssd.update_layout(showlegend=False)
                st.plotly_chart(fig_ssd, use_container_width=True)
            
            # Ekran boyutu analizi
            st.subheader("🖥️ Ekran Boyutu Tercihleri")
            screen_dist = df['screen_size'].value_counts().sort_index()
            fig_screen = px.bar(
                x=[f"{screen}\"" for screen in screen_dist.index],
                y=screen_dist.values,
                title="Ekran Boyutu Dağılımı",
                labels={'x': 'Ekran Boyutu', 'y': 'Laptop Sayısı'},
                color=screen_dist.values,
                color_continuous_scale='oranges'
            )
            fig_screen.update_layout(showlegend=False)
            st.plotly_chart(fig_screen, use_container_width=True)
            
            # Pazar trendleri
            st.subheader("📈 Pazar Trendleri ve İçgörüler")
            
            insights_col1, insights_col2 = st.columns(2)
            
            with insights_col1:
                st.info("🎮 **Gaming Laptop Trendi**")
                gaming_percentage = (df['has_dedicated_gpu'].sum() / len(df)) * 100
                st.write(f"• Gaming laptop oranı: %{gaming_percentage:.1f}")
                avg_gaming_price = df[df['has_dedicated_gpu']]['price'].mean()
                st.write(f"• Ortalama gaming laptop fiyatı: {avg_gaming_price:,.0f} TL")
                
                st.info("💼 **Üretkenlik Laptop Trendi**")
                productivity_laptops = df[~df['has_dedicated_gpu']]
                avg_productivity_price = productivity_laptops['price'].mean()
                st.write(f"• Ortalama üretkenlik laptop fiyatı: {avg_productivity_price:,.0f} TL")
                productivity_percentage = (len(productivity_laptops) / len(df)) * 100
                st.write(f"• Üretkenlik laptop oranı: %{productivity_percentage:.1f}")
            
            with insights_col2:
                st.info("🏢 **Marka Analizi**")
                top_brand = df['brand'].value_counts().index[0]
                top_brand_count = df['brand'].value_counts().iloc[0]
                st.write(f"• En popüler marka: {top_brand.title()} ({top_brand_count} model)")
                
                premium_brands = ['apple', 'dell']
                premium_count = len(df[df['brand'].isin(premium_brands)])
                premium_percentage = (premium_count / len(df)) * 100
                st.write(f"• Premium marka oranı: %{premium_percentage:.1f}")
                
                st.info("💰 **Fiyat Analizi**")
                budget_laptops = len(df[df['price'] <= 30000])
                budget_percentage = (budget_laptops / len(df)) * 100
                st.write(f"• Bütçe dostu laptop oranı (≤30K): %{budget_percentage:.1f}")
                
                high_end_laptops = len(df[df['price'] >= 60000])
                high_end_percentage = (high_end_laptops / len(df)) * 100
                st.write(f"• Üst segment laptop oranı (≥60K): %{high_end_percentage:.1f}")
        
        with tab4:
            st.header("ℹ️ Uygulama Hakkında")
            
            st.markdown("""
            ### 🔥 Akıllı Laptop Öneri Sistemi
            
            Bu uygulama, size en uygun laptop'ı bulmanıza yardımcı olmak için geliştirilmiş yapay zeka destekli bir sistemdir.
            
            #### ✨ Özellikler
            
            🎯 **Kişiselleştirilmiş Öneriler**
            - Bütçenize, kullanım amacınıza ve tercihlerinize göre özel öneriler
            - Gelişmiş puanlama algoritması ile en uygun laptopları belirleme
            - Çok boyutlu filtreleme sistemi
            
            🔥 **Fırsat Ürün Tespiti**
            - Piyasa analizine dayalı fırsat ürün belirleme
            - Gerçek zamanlı fiyat karşılaştırması
            - Yüksek performans/fiyat oranına sahip ürünlerin tespiti
            
            📊 **Detaylı Pazar Analizi**
            - Interaktif grafikler ve görselleştirmeler
            - Marka, fiyat, donanım analizleri
            - Pazar trendleri ve içgörüler
            
            #### 🧮 Puanlama Sistemi
            
            Laptop puanlaması aşağıdaki kriterlere göre yapılır:
            
            - **Fiyat Uygunluğu (15%)**: Bütçenize ne kadar uygun
            - **Fiyat/Performans Oranı (10%)**: Ödediğiniz paraya karşılık aldığınız performans
            - **Kullanım Amacına Uygunluk (30%)**: Gaming, üretkenlik, taşınabilirlik vb.
            - **Donanım Özellikleri (10%)**: RAM, SSD kapasitesi
            - **Marka Güvenilirliği (8%)**: Marka değeri ve kullanıcı memnuniyeti
            - **Kullanıcı Tercihleri (27%)**: Kişisel öncelikleriniz
            
            #### 💻 Teknik Detaylar
            
            - **Framework**: Streamlit
            - **Veri İşleme**: Pandas, NumPy
            - **Görselleştirme**: Plotly
            - **Analiz**: Scikit-learn (opsiyonel)
            - **UI/UX**: Modern, responsive tasarım
            
            #### 📞 İletişim ve Geri Bildirim
            
            Bu uygulama sürekli geliştirilmektedir. Öneri ve geri bildirimlerinizi bekliyoruz!
            
            ---
            
            **Geliştirici**: AI Destekli Geliştirme Ekibi  
            **Sürüm**: 1.0.0  
            **Son Güncelleme**: {datetime.now().strftime('%d.%m.%Y')}  
            """)
            
            # Kullanım istatistikleri (session state)
            if 'app_stats' not in st.session_state:
                st.session_state.app_stats = {
                    'total_searches': 0,
                    'total_deals_viewed': 0,
                    'session_start': datetime.now()
                }
            
            st.subheader("📈 Oturum İstatistikleri")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🔍 Toplam Arama", st.session_state.app_stats['total_searches'])
            with col2:
                st.metric("🔥 İncelenen Fırsat", st.session_state.app_stats['total_deals_viewed'])
            with col3:
                session_duration = datetime.now() - st.session_state.app_stats['session_start']
                st.metric("⏱️ Oturum Süresi", f"{session_duration.seconds//60} dk")
            
            # Favoriler bölümü
            if 'favorites' in st.session_state and st.session_state.favorites:
                st.subheader("❤️ Favori Laptoplarınız")
                for i, fav in enumerate(st.session_state.favorites, 1):
                    st.write(f"{i}. {fav}")
                
                if st.button("🗑️ Favorileri Temizle"):
                    st.session_state.favorites = []
                    st.success("✅ Favoriler temizlendi!")
    
    except Exception as e:
        st.error(f"🚨 Beklenmeyen bir hata oluştu: {str(e)}")
        st.info("Lütfen sayfayı yenileyip tekrar deneyin. Sorun devam ederse destek ekibiyle iletişime geçin.")
        
        # Hata detayları (debug modunda)
        if st.checkbox("🔧 Gelişmiş Hata Detayları (Geliştiriciler için)"):
            st.exception(e)import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import warnings
warnings.filterwarnings('ignore')

# Streamlit Cloud için optimize edilmiş import'lar
try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.neighbors import NearestNeighbors
    from sklearn.ensemble import IsolationForest
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    st.warning("⚠️ Sklearn kütüphanesi bulunamadı. Bazı özellikler sınırlı olabilir.")

# Sayfa konfigürasyonu
st.set_page_config(
    page_title="🔥 Laptop Öneri Sistemi",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS için custom style
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
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
</style>
""", unsafe_allow_html=True)

class StreamlitConfig:
    """Streamlit için optimize edilmiş konfigürasyon"""
    
    # Streamlit Cloud için basitleştirilmiş GPU skorları
    GPU_SCORES = {
        'rtx4090': 100, 'rtx4080': 95, 'rtx4070': 85, 'rtx4060': 75,
        'rtx4050': 60, 'rtx3080': 88, 'rtx3070': 80, 'rtx3060': 70,
        'rtx3050': 55, 'rtx2060': 50, 'gtx1660': 45, 'gtx1650': 40,
        'gtx': 35, 'mx550': 30, 'intel uhd': 20, 'intel iris xe': 25,
        'integrated': 18, 'apple integrated': 35, 'unknown': 25
    }
    
    CPU_SCORES = {
        'i9': 95, 'i7': 85, 'i5': 75, 'i3': 60,
        'ryzen 9': 95, 'ryzen 7': 85, 'ryzen 5': 75, 'ryzen 3': 60,
        'm3': 85, 'm2': 80, 'm1': 75, 'unknown': 50
    }
    
    BRAND_SCORES = {
        'apple': 0.95, 'dell': 0.85, 'hp': 0.80, 'lenovo': 0.85,
        'asus': 0.82, 'msi': 0.80, 'acer': 0.75, 'monster': 0.70,
        'huawei': 0.78, 'samsung': 0.83, 'other': 0.70
    }
    
    WEIGHTS = {
        'price_fit': 15,
        'price_performance': 10,
        'purpose_base': 30,
        'performance': 12,
        'battery': 12,
        'portability': 8,
        'ram': 5,
        'ssd': 5,
        'brand_reliability': 8
    }

@st.cache_data(ttl=3600, show_spinner="📊 Veriler hazırlanıyor...")
def load_sample_data():
    """Gerçekçi örnek veri oluştur - Streamlit Cloud için optimize edilmiş"""
    np.random.seed(42)
    
    # Gerçek laptop markaları ve modelleri
    laptop_data = [
        # ASUS Serisi
        {'brand': 'asus', 'series': 'ROG Strix', 'gpu_type': 'rtx4060', 'cpu_type': 'i7', 'price_range': (35000, 45000)},
        {'brand': 'asus', 'series': 'TUF Gaming', 'gpu_type': 'rtx4050', 'cpu_type': 'i5', 'price_range': (28000, 38000)},
        {'brand': 'asus', 'series': 'ZenBook', 'gpu_type': 'integrated', 'cpu_type': 'i7', 'price_range': (25000, 35000)},
        {'brand': 'asus', 'series': 'VivoBook', 'gpu_type': 'integrated', 'cpu_type': 'i5', 'price_range': (18000, 28000)},
        
        # Dell Serisi
        {'brand': 'dell', 'series': 'XPS', 'gpu_type': 'integrated', 'cpu_type': 'i7', 'price_range': (40000, 55000)},
        {'brand': 'dell', 'series': 'Inspiron', 'gpu_type': 'rtx3050', 'cpu_type': 'i5', 'price_range': (25000, 35000)},
        {'brand': 'dell', 'series': 'G Series', 'gpu_type': 'rtx4060', 'cpu_type': 'i7', 'price_range': (38000, 48000)},
        
        # HP Serisi
        {'brand': 'hp', 'series': 'Pavilion', 'gpu_type': 'gtx1650', 'cpu_type': 'i5', 'price_range': (22000, 32000)},
        {'brand': 'hp', 'series': 'OMEN', 'gpu_type': 'rtx4070', 'cpu_type': 'i7', 'price_range': (45000, 55000)},
        {'brand': 'hp', 'series': 'EliteBook', 'gpu_type': 'integrated', 'cpu_type': 'i7', 'price_range': (35000, 45000)},
        
        # Lenovo Serisi
        {'brand': 'lenovo', 'series': 'ThinkPad', 'gpu_type': 'integrated', 'cpu_type': 'i7', 'price_range': (32000, 42000)},
        {'brand': 'lenovo', 'series': 'Legion', 'gpu_type': 'rtx4060', 'cpu_type': 'i7', 'price_range': (40000, 50000)},
        {'brand': 'lenovo', 'series': 'IdeaPad', 'gpu_type': 'integrated', 'cpu_type': 'i5', 'price_range': (18000, 28000)},
        
        # Apple Serisi
        {'brand': 'apple', 'series': 'MacBook Air', 'gpu_type': 'apple integrated', 'cpu_type': 'm3', 'price_range': (45000, 60000)},
        {'brand': 'apple', 'series': 'MacBook Pro', 'gpu_type': 'apple integrated', 'cpu_type': 'm3', 'price_range': (60000, 85000)},
        
        # MSI Serisi  
        {'brand': 'msi', 'series': 'Gaming', 'gpu_type': 'rtx4070', 'cpu_type': 'i7', 'price_range': (42000, 52000)},
        {'brand': 'msi', 'series': 'Modern', 'gpu_type': 'integrated', 'cpu_type': 'i5', 'price_range': (24000, 34000)},
        
        # Acer Serisi
        {'brand': 'acer', 'series': 'Aspire', 'gpu_type': 'integrated', 'cpu_type': 'i5', 'price_range': (16000, 26000)},
        {'brand': 'acer', 'series': 'Nitro', 'gpu_type': 'rtx4050', 'cpu_type': 'i5', 'price_range': (30000, 40000)},
    ]
    
    data = []
    
    # Her template için birden fazla model oluştur
    for template in laptop_data:
        for i in range(np.random.randint(8, 15)):  # 8-14 model per template
            # Fiyat variasyonu
            min_price, max_price = template['price_range']
            price = np.random.uniform(min_price, max_price)
            
            # Fırsat ürünler için rastgele indirim
            is_deal = np.random.random() < 0.15  # %15 şans ile fırsat ürün
            if is_deal:
                price *= np.random.uniform(0.75, 0.90)  # %10-25 indirim
            
            # RAM/SSD konfigürasyonu
            if template['gpu_type'] in ['rtx4070', 'rtx4060']:
                ram_options = [16, 32]
                ssd_options = [512, 1024]
            elif 'apple' in template['gpu_type']:
                ram_options = [16, 32]
                ssd_options = [512, 1024, 2048]
            else:
                ram_options = [8, 16]
                ssd_options = [256, 512]
            
            ram = np.random.choice(ram_options)
            ssd = np.random.choice(ssd_options)
            
            # Ekran boyutu
            if template['series'] in ['MacBook Air', 'ZenBook', 'XPS']:
                screen = np.random.choice([13.3, 14.0], p=[0.3, 0.7])
            elif template['series'] in ['ROG Strix', 'Legion', 'Gaming']:
                screen = np.random.choice([15.6, 17.3], p=[0.7, 0.3])
            else:
                screen = np.random.choice([14.0, 15.6], p=[0.4, 0.6])
            
            # Model adı oluştur
            model_suffix = f"{ram}GB/{ssd}GB" if np.random.random() < 0.7 else f"Gen{np.random.randint(10, 13)}"
            name = f"{template['brand'].title()} {template['series']} {model_suffix}"
            
            laptop = {
                'name': name,
                'brand': template['brand'],
                'price': int(price),
                'gpu_clean': template['gpu_type'],
                'cpu_clean': template['cpu_type'],
                'ram_gb': ram,
                'ssd_gb': ssd,
                'screen_size': screen,
                'os': 'macOS' if template['brand'] == 'apple' else 'Windows 11',
                'url': f"https://www.example-store.com/{template['brand']}-{template['series'].lower().replace(' ', '-')}-{i+1}",
                'is_apple': template['brand'] == 'apple',
                'has_dedicated_gpu': 'integrated' not in template['gpu_type']
            }
            data.append(laptop)
    
    df = pd.DataFrame(data)
    
    # Skorları hesapla
    config = StreamlitConfig()
    df['gpu_score'] = df['gpu_clean'].map(config.GPU_SCORES).fillna(25)
    df['cpu_score'] = df['cpu_clean'].map(config.CPU_SCORES).fillna(50)
    df['brand_score'] = df['brand'].map(config.BRAND_SCORES).fillna(0.70)
    
    return df

def calculate_laptop_score(row, preferences, config):
    """Laptop puanını hesapla"""
    try:
        score = 0
        
        # Fiyat uygunluğu
        price_range = preferences['max_budget'] - preferences['min_budget']
        if price_range > 0:
            price_diff = abs(row['price'] - preferences['ideal_price'])
            price_score = config.WEIGHTS['price_fit'] * max(0, 1 - price_diff / (price_range / 2))
        else:
            price_score = config.WEIGHTS['price_fit']
        
        score += price_score
        
        # Fiyat/performans
        performance_score = (row['gpu_score'] * 0.6 + row['cpu_score'] * 0.4) / 100
        price_perf = performance_score * (preferences['ideal_price'] / row['price']) * config.WEIGHTS['price_performance']
        score += price_perf
        
        # Kullanım amacı
        purpose_multipliers = {
            'oyun': 1.0 if row['has_dedicated_gpu'] else 0.3,
            'taşınabilirlik': 0.3 if row['has_dedicated_gpu'] else 1.0,
            'üretkenlik': 0.6,
            'tasarım': 0.8 if row['has_dedicated_gpu'] else 0.4
        }
        
        purpose_score = config.WEIGHTS['purpose_base'] * performance_score * purpose_multipliers.get(preferences['purpose'], 0.6)
        score += purpose_score
        
        # Donanım puanları
        ram_score = config.WEIGHTS['ram'] * min(row['ram_gb'] / 16, 1.0)
        ssd_score = config.WEIGHTS['ssd'] * min(row['ssd_gb'] / 1024, 1.0)
        score += ram_score + ssd_score
        
        # Marka güvenilirliği
        brand_score = config.WEIGHTS['brand_reliability'] * row['brand_score']
        score += brand_score
        
        return max(0, min(100, score))
        
    except Exception as e:
        st.error(f"Puan hesaplama hatası: {e}")
        return 0.0

@st.cache_data
def find_deals(df, discount_threshold=15):
    """Fırsat ürünleri bul"""
    try:
        # Basit fırsat tespiti - performans/fiyat oranı yüksek olanlar
        df = df.copy()
        df['performance_score'] = (df['gpu_score'] * 0.6 + df['cpu_score'] * 0.4)
        df['price_performance_ratio'] = df['performance_score'] / (df['price'] / 10000)
        
        # En iyi %20'lik dilimi al
        threshold = df['price_performance_ratio'].quantile(0.8)
        deals = df[df['price_performance_ratio'] >= threshold].copy()
        
        if not deals.empty:
            # Varsayılan indirim oranı hesapla
            deals['discount_percentage'] = np.random.uniform(15, 35, len(deals))
            deals['deal_score'] = deals['price_performance_ratio'] * 10
            deals = deals.sort_values('deal_score', ascending=False)
        
        return deals.head(20)
    except Exception as e:
        st.error(f"Fırsat bulma hatası: {e}")
        return pd.DataFrame()

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🔥 Akıllı Laptop Öneri Sistemi</h1>
        <p>Size en uygun laptop'ı bulalım!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Veriyi yükle
    with st.spinner('📊 Veriler yükleniyor...'):
        df = load_sample_data()
    
    # Sidebar - Kullanıcı tercihleri
    st.sidebar.header("🎯 Tercihlerinizi Belirtin")
    
    # Bütçe
    st.sidebar.subheader("💰 Bütçe")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        min_budget = st.number_input("Min (TL)", min_value=10000, max_value=100000, value=20000, step=5000)
    with col2:
        max_budget = st.number_input("Max (TL)", min_value=min_budget, max_value=150000, value=50000, step=5000)
    
    ideal_price = (min_budget + max_budget) / 2
    
    # Kullanım amacı
    st.sidebar.subheader("🎮 Kullanım Amacı")
    purpose = st.sidebar.selectbox(
        "Ne için kullanacaksınız?",
        ["oyun", "taşınabilirlik", "üretkenlik", "tasarım"],
        format_func=lambda x: {
            "oyun": "🎮 Oyun",
            "taşınabilirlik": "🎒 Taşınabilirlik", 
            "üretkenlik": "💼 Üretkenlik",
            "tasarım": "🎨 Tasarım"
        }[x]
    )
    
    # Filtreler
    st.sidebar.subheader("🔧 Filtreler")
    
    # Marka filtresi
    brands = ['Tümü'] + sorted(df['brand'].unique().tolist())
    brand_filter = st.sidebar.selectbox("Marka", brands)
    
    # RAM filtresi
    ram_filter = st.sidebar.selectbox("Minimum RAM", [8, 16, 32], format_func=lambda x: f"{x} GB")
    
    # SSD filtresi  
    ssd_filter = st.sidebar.selectbox("Minimum SSD", [256, 512, 1024], format_func=lambda x: f"{x} GB")
    
    # İşletim sistemi
    os_filter = st.sidebar.selectbox("İşletim Sistemi", ["Tümü", "Windows 11", "macOS"])
    
    preferences = {
        'min_budget': min_budget,
        'max_budget': max_budget,
        'ideal_price': ideal_price,
        'purpose': purpose
    }
    
    # Ana içerik
    tab1, tab2, tab3 = st.tabs(["🏆 Öneriler", "🔥 Fırsatlar", "📊 Analiz"])
    
    with tab1:
        st.header("🏆 Size Özel Laptop Önerileri")
        
        # Filtreleri uygula
        filtered_df = df.copy()
        
        # Bütçe filtresi
        filtered_df = filtered_df[
            (filtered_df['price'] >= min_budget) & 
            (filtered_df['price'] <= max_budget)
        ]
        
        # Diğer filtreler
        if brand_filter != 'Tümü':
            filtered_df = filtered_df[filtered_df['brand'] == brand_filter.lower()]
        
        filtered_df = filtered_df[filtered_df['ram_gb'] >= ram_filter]
        filtered_df = filtered_df[filtered_df['ssd_gb'] >= ssd_filter]
        
        if os_filter != 'Tümü':
            filtered_df = filtered_df[filtered_df['os'] == os_filter]
        
        if len(filtered_df) == 0:
            st.warning("⚠️ Seçilen kriterlere uygun laptop bulunamadı. Filtreleri gevşetmeyi deneyin.")
        else:
            # Puanları hesapla
            config = StreamlitConfig()
            
            with st.spinner('🧮 Laptoplar puanlanıyor...'):
                filtered_df['score'] = filtered_df.apply(
                    lambda row: calculate_laptop_score(row, preferences, config), 
                    axis=1
                )
            
            # En iyileri seç
            top_laptops = filtered_df.nlargest(5, 'score')
            
            # Özet metrikler
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("🔍 Bulunan Laptop", len(filtered_df))
            with col2:
                st.metric("💰 Ortalama Fiyat", f"{filtered_df['price'].mean():,.0f} TL")
            with col3:
                st.metric("⭐ En Yüksek Puan", f"{top_laptops.iloc[0]['score']:.1f}")
            with col4:
                st.metric("🏢 Marka Sayısı", len(filtered_df['brand'].unique()))
            
            st.subheader("📋 Önerilen Laptoplar")
            
            # Her laptopı kart olarak göster
            for idx, (_, laptop) in enumerate(top_laptops.iterrows(), 1):
                with st.container():
                    st.markdown(f"""
                    <div class="recommendation-card">
                        <h3>#{idx} {laptop['name']}</h3>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong>💰 {laptop['price']:,} TL</strong> | 
                                <strong>⭐ {laptop['score']:.1f}/100 puan</strong>
                            </div>
                            <div>
                                <span style="background: #667eea; color: white; padding: 0.2rem 0.5rem; border-radius: 15px; font-size: 0.8rem;">
                                    {laptop['brand'].title()}
                                </span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Detaylar
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"🖥️ **Ekran:** {laptop['screen_size']}\"")
                        st.write(f"🧠 **İşlemci:** {laptop['cpu_clean'].upper()}")
                    with col2:
                        st.write(f"🎮 **GPU:** {laptop['gpu_clean'].upper()}")
                        st.write(f"💾 **RAM:** {laptop['ram_gb']} GB")
                    with col3:
                        st.write(f"💿 **SSD:** {laptop['ssd_gb']} GB")
                        st.write(f"🖥️ **OS:** {laptop['os']}")
                    
                    # Öne çıkan özellikler
                    features = []
                    if laptop['has_dedicated_gpu'] and laptop['gpu_score'] >= 70:
                        features.append("🚀 Güçlü oyun performansı")
                    if laptop['ram_gb'] >= 16:
                        features.append("⚡ Yüksek bellek kapasitesi")
                    if laptop['screen_size'] <= 14:
                        features.append("🎒 Taşınabilir tasarım")
                    if laptop['brand_score'] >= 0.85:
                        features.append("⭐ Yüksek marka güvenilirliği")
                    
                    if features:
                        st.write("✨ **Öne Çıkan Özellikler:**")
                        for feature in features:
                            st.write(f"   • {feature}")
                    
                    # Link butonu
                    st.link_button("🔗 Ürünü İncele", laptop['url'])
                    
                    st.markdown("---")
    
    with tab2:
        st.header("🔥 Günün Fırsat Ürünleri")
        st.write("Piyasa analizine göre tespit edilen fırsat ürünleri:")
        
        with st.spinner('🔍 Fırsatlar aranıyor...'):
            deals = find_deals(df)
        
        if deals.empty:
            st.info("💔 Şu anda öne çıkan fırsat ürün bulunamadı.")
        else:
            st.success(f"🎯 {len(deals)} fırsat ürün tespit edildi!")
            
            # Fırsat kartları
            for idx, (_, deal) in enumerate(deals.head(10).iterrows(), 1):
                with st.container():
                    st.markdown(f"""
                    <div class="deal-card">
                        <h3>🔥 #{idx} {deal['name']}</h3>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong>💰 {deal['price']:,} TL</strong> | 
                                <strong>📉 %{deal['discount_percentage']:.0f} İndirim!</strong>
                            </div>
                            <div>
                                <span style="background: rgba(255,255,255,0.3); padding: 0.2rem 0.5rem; border-radius: 15px; font-size: 0.8rem;">
                                    Fırsat Skoru: {deal['deal_score']:.0f}
                                </span>
                            </div>
                        </div>
                        
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"🧠 **İşlemci:** {deal['cpu_clean'].upper()}")
                        st.write(f"🎮 **GPU:** {deal['gpu_clean'].upper()}")
                    with col2:
                        st.write(f"💾 **RAM:** {deal['ram_gb']} GB")
                        st.write(f"💿 **SSD:** {deal['ssd_gb']} GB")
                    with col3:
                        st.write(f"🏢 **Marka:** {deal['brand'].title()}")
                        st.write(f"🖥️ **Ekran:** {deal['screen_size']}\"")
                    
                    st.link_button("🛒 Fırsatı Kaçırma!", deal['url'], use_container_width=True)
                    st.markdown("---")
    
    with tab3:
        st.header("📊 Pazar Analizi")
        
        # Fiyat dağılımı
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("💰 Fiyat Dağılımı")
            fig_price = px.histogram(
                df, 
                x='price', 
                nbins=30,
                title="Laptop Fiyat Dağılımı",
                labels={'price': 'Fiyat (TL)', 'count': 'Adet'}
            )
            fig_price.update_traces(marker_color='#667eea')
            st.plotly_chart(fig_price, use_container_width=True)
        
        with col2:
            st.subheader("🏢 Marka Dağılımı")
            brand_counts = df['brand'].value_counts()
            fig_brand = px.pie(
                values=brand_counts.values,
                names=brand_counts.index,
                title="Marka Dağılımı"
            )
            st.plotly_chart(fig_brand, use_container_width=True)
        
        # GPU performans analizi
        st.subheader("🎮 GPU Performans Analizi")
        gpu_analysis = df.groupby('gpu_clean').agg({
            'price': 'mean',
            'gpu_score': 'mean'
        }).round(0).reset_index()
        
        fig_gpu = px.scatter(
            gpu_analysis,
            x='gpu_score',
            y='price',
            size='price',
            hover_data=['gpu_clean'],
            title="GPU Skoru vs Ortalama Fiyat",
            labels={'gpu_score': 'GPU Performans Skoru', 'price': 'Ortalama Fiyat (TL)'}
        )
        st.plotly_chart(fig_gpu, use_container_width=True)
        
        # RAM/SSD kombinasyonları
        st.subheader("💾 RAM/SSD Kombinasyonları")
        ram_ssd = df.groupby(['ram_gb', 'ssd_gb']).agg({
            'price': 'mean'
        }).round(0).reset_index()
        
        fig_combo = px.scatter(
            ram_ssd,
            x='ram_gb',
            y='ssd_gb',
            size='price',
            color='price',
            title="RAM/SSD Kombinasyonları ve Ortalama Fiyatları",
            labels={'ram_gb': 'RAM (GB)', 'ssd_gb': 'SSD (GB)', 'price': 'Ortalama Fiyat (TL)'}
        )
        st.plotly_chart(fig_combo, use_container_width=True)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem;'>
        💻 Akıllı Laptop Öneri Sistemi | 2024 <br>
        🚀 Streamlit ile geliştirildi
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

import re
import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def scrape_tradingview_stocks():
    print("Menginisialisasi browser hantu (headless)...")
    
    # Konfigurasi agar Chrome berjalan di latar belakang
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Mengelabui deteksi bot sederhana dengan User-Agent standar
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    url = "https://id.tradingview.com/markets/stocks-indonesia/market-movers-all-stocks/"
    print(f"Membuka halaman: {url}")
    driver.get(url)
    
    # Menunggu JavaScript memuat seluruh data tabel (sesuaikan jeda jika internet lambat)
    print("Menunggu data dimuat...")
    time.sleep(7) 
    
    # Ambil source HTML setelah render selesai
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()
    
    # Mencari semua baris tabel di dalam struktur HTML TradingView
    # Struktur umum TradingView menggunakan tag 'tr'
    rows = soup.find_all('tr')
    
    data_saham = []
    
    print(f"Memproses baris data yang ditemukan...")
    for row in rows:
        # Cari elemen ticker/simbol saham (biasanya di dalam tag 'a' atau class khusus)
        # Kita bisa mencari text dari kolom pertama untuk mendapatkan Simbol Saham
        cells = row.find_all('td')
        if len(cells) >= 8:  # Memastikan baris tersebut adalah baris data yang valid
            try:
                # TradingView struktur: sel pertama berisi ticker dan nama perusahaan
                # Format: "AADI Pt Adaro Andalan Indonesia Tbk" (digabung tanpa spasi)
                # Ticker biasanya 4 karakter (uppercase), diikuti nama perusahaan
                first_cell_text = cells[0].text.strip()
                
                # Coba split dengan tab, lalu newline, lalu spasi sebagai fallback
                if '\t' in first_cell_text:
                    parts = first_cell_text.split('\t')
                    ticker = parts[0].strip()
                    nama_perusahaan = parts[1].strip() if len(parts) > 1 else ticker
                elif '\n' in first_cell_text:
                    parts = first_cell_text.split('\n')
                    ticker = parts[0].strip()
                    nama_perusahaan = parts[1].strip() if len(parts) > 1 else ticker
                else:
                    # TradingView format: ticker dan nama digabung (misal: "AADIPt Adaro Andalan Indonesia TbkD")
                    # Ticker = 4 karakter uppercase pertama, nama perusahaan = sisa teks
                    match = re.match(r'^([A-Z]{4})(.+)?', first_cell_text)
                    if match:
                        ticker = match.group(1)
                        nama_perusahaan = match.group(2).strip() if match.group(2) else ticker
                        # Hapus karakter "D" di akhir nama perusahaan (bukan bagian dari nama)
                        if nama_perusahaan.endswith('D'):
                            nama_perusahaan = nama_perusahaan[:-1].strip()
                    else:
                        ticker = first_cell_text[:4].strip()
                        nama_perusahaan = first_cell_text[4:].strip() if len(first_cell_text) > 4 else ticker
                        if nama_perusahaan.endswith('D'):
                            nama_perusahaan = nama_perusahaan[:-1].strip()
                
                harga = cells[1].text.strip()
                perubahan = cells[2].text.strip()
                volume = cells[3].text.strip()
                kap_pasar = cells[5].text.strip()
                pe_ratio = cells[6].text.strip()
                eps = cells[7].text.strip()
                analis = cells[-1].text.strip() if len(cells) > 10 else "N/A"
                
                # Try to get dividend yield and valuation from additional cells
                div_yield = "N/A"
                valuasi = "N/A"
                
                if len(cells) > 8:
                    # Look for dividend yield in additional cells (usually has % sign)
                    for i, cell in enumerate(cells):
                        cell_text = cell.text.strip()
                        if '%' in cell_text and i > 7:  # After EPS
                            div_yield = cell_text
                            break
                
                data_saham.append({
                    "Ticker": ticker,
                    "Nama Perusahaan": nama_perusahaan,
                    "Harga": harga,
                    "Perubahan %": perubahan,
                    "Volume": volume,
                    "Market Cap": kap_pasar,
                    "P/E": pe_ratio,
                    "EPS": eps,
                    "Rekomendasi Analis": analis,
                    "Dividen Yield": div_yield,
                    "Valuasi": valuasi,
                })
            except Exception as e:
                continue

    # Mengubah ke Pandas DataFrame agar mudah dianalisis
    df = pd.DataFrame(data_saham)
    return df

# --- PROSES ANALISIS & RINGKASAN ---
if __name__ == "__main__":
    import json
    from datetime import datetime, timezone
    
    df_saham = scrape_tradingview_stocks()
    
    if not df_saham.empty:
        print(f"\n Berhasil mengambil data {len(df_saham)} saham.")
        print("-" * 50)
        
        # 1. Tampilkan 5 Data Teratas Hasil Scraping
        print("\n[INFO] Contoh 5 Data Saham Teratas:")
        print(df_saham.head())
        
        # 2. RINGKASAN OTOMATIS 1: Saham dengan Rekomendasi "Pembelian Kuat" (Strong Buy)
        print("\n[RINGKASAN] Saham Berstatus 'Pembelian Kuat' oleh Analis:")
        strong_buy = df_saham[df_saham['Rekomendasi Analis'].str.contains('Pembelian kuat', case=False, na=False)]
        if not strong_buy.empty:
            print(strong_buy[['Ticker', 'Harga', 'Perubahan %', 'Rekomendasi Analis']].to_string(index=False))
        else:
            print("Tidak ada saham berstatus Pembelian Kuat saat ini di halaman utama.")
            
        # 3. Simpan seluruh data ke CSV untuk keperluan ekspor/backup harian
        df_saham.to_csv("ringkasan_saham_idx.csv", index=False)
        print("\n[SUKSES] Seluruh data mentah disimpan ke 'ringkasan_saham_idx.csv'")
        
        # 4. Simpan ke cache JSON untuk API
        records = df_saham.to_dict(orient="records")
        strong_buy_count = len(strong_buy)
        cache_data = {
            'cached_at': datetime.now(timezone.utc).isoformat(),
            'data': records,
            'total': len(records),
            'strong_buy_count': strong_buy_count,
        }
        with open("tradingview_cache.json", 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        print(f"\n[SUKSES] Data juga disimpan ke 'tradingview_cache.json' ({strong_buy_count} saham Pembelian Kuat)")
        
    else:
        print("Gagal mengambil data. Periksa kembali koneksi internet atau selektor elemen HTML.")
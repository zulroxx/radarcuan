import json
import re
import time
from datetime import datetime, timezone

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def scrape_tradingview_screener_data():
    """
    Scrape IHSG stock data from TradingView including valuation and dividend info.
    Returns list of dicts with Ticker, Nama Perusahaan, Harga, Perubahan, Volume, 
    Market Cap, P/E, EPS, Rekomendasi Analis, Dividen Yield, and Valuasi.
    """
    print("Menginisialisasi browser hantu (headless)...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    url = "https://id.tradingview.com/markets/stocks-indonesia/market-movers-all-stocks/"
    print(f"Membuka halaman: {url}")
    driver.get(url)
    
    print("Menunggu data dimuat...")
    time.sleep(7)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()
    
    rows = soup.find_all('tr')
    data_saham = []
    
    print(f"Memproses baris data yang ditemukan...")
    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 8:
            try:
                first_cell_text = cells[0].text.strip()
                
                # Extract ticker (4 uppercase chars) and company name
                if '\t' in first_cell_text:
                    parts = first_cell_text.split('\t')
                    ticker = parts[0].strip()
                    nama_perusahaan = parts[1].strip() if len(parts) > 1 else ticker
                elif '\n' in first_cell_text:
                    parts = first_cell_text.split('\n')
                    ticker = parts[0].strip()
                    nama_perusahaan = parts[1].strip() if len(parts) > 1 else ticker
                else:
                    match = re.match(r'^([A-Z]{4})(.+)?', first_cell_text)
                    if match:
                        ticker = match.group(1)
                        nama_perusahaan = match.group(2).strip() if match.group(2) else ticker
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
                
                # Try to get dividend yield and valuation from additional cells if available
                # TradingView typically has more columns, check if they exist
                div_yield = "N/A"
                valuasi = "N/A"
                
                if len(cells) > 8:
                    # Look for dividend yield in additional cells
                    for i, cell in enumerate(cells):
                        cell_text = cell.text.strip().lower()
                        if 'div' in cell_text or '%' in cell_text:
                            if i > 7:  # After EPS
                                div_yield = cell.text.strip()
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
    
    df = pd.DataFrame(data_saham)
    return df


def save_screener_cache(df):
    """Save screener data to cache file."""
    records = df.to_dict(orient="records")
    strong_buy_count = len(df[df['Rekomendasi Analis'].str.contains('Pembelian kuat', case=False, na=False)])
    
    cache_data = {
        'cached_at': datetime.now(timezone.utc).isoformat(),
        'data': records,
        'total': len(records),
        'strong_buy_count': strong_buy_count,
    }
    
    with open("tradingview_cache.json", 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
    
    print(f"Cache disimpan: {len(records)} saham, {strong_buy_count} Pembelian Kuat")


if __name__ == "__main__":
    df_saham = scrape_tradingview_screener_data()
    
    if not df_saham.empty:
        print(f"\nBerhasil mengambil data {len(df_saham)} saham.")
        print("-" * 50)
        
        # Show strong buy stocks
        strong_buy = df_saham[df_saham['Rekomendasi Analis'].str.contains('Pembelian kuat', case=False, na=False)]
        if not strong_buy.empty:
            print("\n[RINGKASAN] Saham Berstatus 'Pembelian Kuat' oleh Analis:")
            print(strong_buy[['Ticker', 'Nama Perusahaan', 'Harga', 'Perubahan %', 'Rekomendasi Analis']].to_string(index=False))
        
        # Save to cache
        save_screener_cache(df_saham)
        
        # Also save to CSV
        df_saham.to_csv("ringkasan_saham_idx.csv", index=False)
        print("\nData juga disimpan ke 'ringkasan_saham_idx.csv'")
    else:
        print("Gagal mengambil data. Periksa koneksi internet atau selektor elemen HTML.")
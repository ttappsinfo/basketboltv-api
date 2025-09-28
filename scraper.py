import requests
from bs4 import BeautifulSoup
import json
from flask import Flask
from datetime import datetime
import pytz

# --- 1. YENİ SATIR: Gerekli kütüphaneyi içeri aktarıyoruz ---
from flask_cors import CORS

# Flask ile web uygulamamızı oluşturuyoruz
app = Flask(__name__)

# --- 2. YENİ SATIR: CORS izinlerini tüm adreslere açıyoruz ---
# Bu satır, tarayıcıların API'nizden veri çekmesine izin verir.
CORS(app)

def get_match_data():
    url = "https://www.sporekrani.com/home/sport/basketbol"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    print("DEBUG: Web sitesine istek gönderiliyor...")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print("DEBUG: Web sitesinden başarılı bir şekilde cevap alındı.")
    except requests.exceptions.RequestException as e:
        print(f"HATA: Web sitesine bağlanılamadı. Hata: {e}")
        return {"error": str(e)}

    soup = BeautifulSoup(response.content, 'html.parser')
    maclar_listesi = []

    script_tag = soup.find('script', {'type': 'application/ld+json'})

    if not script_tag:
        print("HATA: Sayfa kaynağında JSON-LD script etiketi bulunamadı.")
        return []

    try:
        data = json.loads(script_tag.string)
        print(f"DEBUG: JSON verisi başarıyla okundu. Toplam {len(data)} etkinlik bulundu.")
    except json.JSONDecodeError:
        print("HATA: JSON verisi ayrıştırılamadı.")
        return []
    
    turkey_tz = pytz.timezone('Europe/Istanbul')
    gun_map = {
        'Mon': 'Pzt', 'Tue': 'Sal', 'Wed': 'Çar', 'Thu': 'Per',
        'Fri': 'Cum', 'Sat': 'Cmt', 'Sun': 'Paz'
    }

    for event in data:
        try:
            match_details = event.get("broadcastOfEvent", {})
            takimlar = match_details.get("name", "N/A")
            
            start_date_str = match_details.get("startDate")
            if start_date_str:
                dt_object = datetime.fromisoformat(start_date_str)
                dt_turkey = dt_object.astimezone(turkey_tz)
                day_eng = dt_turkey.strftime("%a")
                day_tr = gun_map.get(day_eng, day_eng)
                
                today = datetime.now(turkey_tz).date()
                match_date = dt_turkey.date()
                if match_date == today:
                    tarih_str = "Bugün"
                elif (match_date - today).days == 1:
                    tarih_str = "Yarın"
                else:
                    tarih_str = dt_turkey.strftime(f"%d.%m {day_tr}")
                
                saat_str = dt_turkey.strftime("%H:%M")
                tarih_saat = f"{tarih_str} {saat_str}"
            else:
                tarih_saat = "Tarih/Saat Yok"

            broadcast_channel = event.get("broadcastChannel", [{}])[0]
            kanal = broadcast_channel.get("name", "Kanal Yok")
            
            mac_bilgisi = f"{tarih_saat} | {takimlar} | {kanal}"
            maclar_listesi.append(mac_bilgisi)

        except (KeyError, IndexError, TypeError) as e:
            print(f"--> HATA: Bir etkinlik işlenirken hata oluştu, atlanıyor. Hata: {e}")
            continue
            
    return maclar_listesi

@app.route('/')
def api_endpoint():
    data = get_match_data()
    print(f"\nDEBUG: API sonucu olarak {len(data)} adet maç gönderiliyor.")
    return json.dumps(data, ensure_ascii=False), 200, {'Content-Type': 'application/json; charset=utf-8'}

if __name__ == '__main__':
    app.run(debug=True)

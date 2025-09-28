import requests
from bs4 import BeautifulSoup
import json
from flask import Flask
from datetime import datetime
import pytz # Saat dilimi yönetimi için gerekli

# Flask ile web uygulamamızı oluşturuyoruz
app = Flask(__name__)

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

    # --- YENİ VE KESİN YÖNTEM ---
    # Sayfa içeriği JavaScript ile oluşturulduğu için, verileri HTML'in içindeki
    # yapısal JSON verisinden (JSON-LD) çekiyoruz. Bu çok daha güvenilir bir yöntemdir.
    script_tag = soup.find('script', {'type': 'application/ld+json'})

    if not script_tag:
        print("HATA: Sayfa kaynağında JSON-LD script etiketi bulunamadı.")
        return []

    try:
        # Script etiketinin içindeki JSON verisini alıp Python listesine çeviriyoruz
        data = json.loads(script_tag.string)
        print(f"DEBUG: JSON verisi başarıyla okundu. Toplam {len(data)} etkinlik bulundu.")
    except json.JSONDecodeError:
        print("HATA: JSON verisi ayrıştırılamadı.")
        return []
    
    # Türkiye saat dilimini ve günlerin Türkçe kısaltmalarını belirliyoruz
    turkey_tz = pytz.timezone('Europe/Istanbul')
    gun_map = {
        'Mon': 'Pzt', 'Tue': 'Sal', 'Wed': 'Çar', 'Thu': 'Per',
        'Fri': 'Cum', 'Sat': 'Cmt', 'Sun': 'Paz'
    }

    for event in data:
        try:
            # Gerekli bilgileri JSON verisinden çekiyoruz
            match_details = event.get("broadcastOfEvent", {})
            takimlar = match_details.get("name", "N/A")
            
            # Tarih ve saati alıp formatlıyoruz (Örnek: "2025-09-28T13:00:00+03:00")
            start_date_str = match_details.get("startDate")
            if start_date_str:
                dt_object = datetime.fromisoformat(start_date_str)
                dt_turkey = dt_object.astimezone(turkey_tz)
                day_eng = dt_turkey.strftime("%a")
                day_tr = gun_map.get(day_eng, day_eng)
                # App Inventor için özel olarak tarihi bugünün ve yarının tarihiyle karşılaştırıyoruz
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

            # Kanal bilgisini alıyoruz. Birden fazla kanal olabilir, ilkini alıyoruz.
            broadcast_channel = event.get("broadcastChannel", [{}])[0]
            kanal = broadcast_channel.get("name", "Kanal Yok")
            
            # App Inventor'da kolayca göstermek için bilgileri tek bir satırda birleştiriyoruz
            mac_bilgisi = f"{tarih_saat} | {takimlar} | {kanal}"
            maclar_listesi.append(mac_bilgisi)

        except (KeyError, IndexError, TypeError) as e:
            # Eğer bir etkinlikte beklenen yapı yoksa atlayıp devam ediyoruz.
            print(f"--> HATA: Bir etkinlik işlenirken hata oluştu, atlanıyor. Hata: {e}")
            continue
            
    return maclar_listesi

@app.route('/')
def api_endpoint():
    data = get_match_data()
    print(f"\nDEBUG: API sonucu olarak {len(data)} adet maç gönderiliyor.")
    # Tarayıcının Türkçe karakterleri doğru göstermesi için 'ensure_ascii=False' ekliyoruz.
    return json.dumps(data, ensure_ascii=False), 200, {'Content-Type': 'application/json; charset=utf-8'}

if __name__ == '__main__':
    app.run(debug=True)
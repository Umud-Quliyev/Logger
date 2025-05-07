from flask import Flask, request
import re
from datetime import datetime, timedelta
import requests

app = Flask(__name__)

DJANGO_API_URL = os.getenv("DJANGO_API_URL")

def send_whatsapp_message(to, message):
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

    data = {
        "To": f"whatsapp:{to}",
        "From": from_number,
        "Body": message
    }

    try:
        response = requests.post(url, data=data, auth=(account_sid, auth_token))
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        print(f"WhatsApp Göndərmə Xətası: {err}")

def create_person(name):
    person_data = {"name": name}
    response = requests.post("http://localhost:8000/api/person/", json=person_data)
    if response.status_code == 201:
        return response.json()
    else:
        print(f"Kişi əlavə edilə bilmədi: {response.text}")
        return None

@app.route('/webhook', methods=['POST'])
def webhook():
    allowed_ips = ['185.118.51.27']
    requester_ip = request.remote_addr

    from_number = request.values.get('From', '').replace('whatsapp:', '')
    body = request.values.get('Body', '').strip()

    # IP bloklaması və WhatsApp xəbərdarlığı
    if requester_ip not in allowed_ips:
        send_whatsapp_message(from_number, "❌ Bu sistemə giriş icazəniz yoxdur.")
        return '❌ İcazəsiz IP', 403

    current_date = datetime.now().strftime('%Y-%m-%d')
    now = datetime.now()

    match_entry = re.match(r'(\w+)\s*\(Giriş\):\s*(\d{2}:\d{2})', body)
    match_exit = re.match(r'(\w+)\s*\(Çıxış\):\s*(\d{2}:\d{2})', body)

    # GİRİŞ
    if match_entry:
        name, time = match_entry.groups()
        try:
            entry_time = datetime.strptime(time, '%H:%M')
        except ValueError:
            send_whatsapp_message(from_number, "⚠️ Saat formatı səhvdir. Məsələn: 09:00")
            return '', 200

        # 15 dəqiqəlik interval yoxlanışı
        if abs((now - entry_time.replace(year=now.year, month=now.month, day=now.day)).total_seconds()) > 900:
            send_whatsapp_message(from_number, "⏳ Giriş vaxtı real saatdan maksimum 15 dəqiqə fərqli ola bilər.")
            return '', 200

        person_response = requests.get(f"http://localhost:8000/api/person/?name={name}")
        if person_response.status_code == 200 and not person_response.json():
            new_person = create_person(name)
            if new_person is None:
                return "Yeni şəxs yaradılmadı", 500
            person_id = new_person['id']
        else:
            person_id = person_response.json()[0]['id']

        existing_entry_response = requests.get(
            f"{DJANGO_API_URL}?person={person_id}&exit_time__isnull=true"
        )

        if existing_entry_response.status_code == 200 and existing_entry_response.json():
            for entry in existing_entry_response.json():
                if entry["date"] == current_date:
                    send_whatsapp_message(from_number, f"⚠️ {name.capitalize()}, bu gün üçün artıq giriş edilib.")
                    return '', 200

        data = {
            "person": person_id,
            "date": current_date,
            "entry_time": entry_time.strftime("%H:%M:%S")
        }
        response = requests.post(DJANGO_API_URL, json=data)
        if response.status_code == 201:
            send_whatsapp_message(from_number, f"👋 Salam {name.capitalize()}! Girişiniz uğurla qeydə alındı.")
            return '', 200
        else:
            return f"Error saving entry: {response.text}", 500

    # ÇIXIŞ
    if match_exit:
        name, time = match_exit.groups()
        try:
            exit_time_obj = datetime.strptime(time, '%H:%M')
        except ValueError:
            send_whatsapp_message(from_number, "⚠️ Saat formatı səhvdir. Məsələn: 18:00")
            return '', 200

        # 15 dəqiqəlik interval yoxlanışı
        if abs((now - exit_time_obj.replace(year=now.year, month=now.month, day=now.day)).total_seconds()) > 900:
            send_whatsapp_message(from_number, "⏳ Çıxış vaxtı real saatdan maksimum 15 dəqiqə fərqli ola bilər.")
            return '', 200

        person_response = requests.get("http://localhost:8000/api/person/")
        person_list = person_response.json()
        person_id = next((p["id"] for p in person_list if p["name"].lower() == name.lower()), None)

        if not person_id:
            send_whatsapp_message(from_number, "⚠️ Bu adla sistemdə şəxs tapılmadı.")
            return '', 200

        response = requests.get(f"{DJANGO_API_URL}?person={person_id}&exit_time__isnull=true")
        if response.status_code == 200 and response.json():
            matched_record = next((
                r for r in response.json()
                if r["person"] == person_id and r["exit_time"] is None and r["date"] == current_date
            ), None)

            if matched_record:
                entry_time_obj = datetime.strptime(matched_record['entry_time'], '%H:%M:%S')
                work_duration = datetime.combine(datetime.today(), exit_time_obj.time()) - datetime.combine(datetime.today(), entry_time_obj.time())
                work_hours = work_duration.total_seconds() / 3600

                data = {
                    "exit_time": exit_time_obj.strftime("%H:%M:%S"),
                    "work_hours": work_hours
                }
                patch_response = requests.patch(f"{DJANGO_API_URL}{matched_record['id']}/", json=data)
                if patch_response.status_code == 200:
                    send_whatsapp_message(from_number, f"📤 {name.capitalize()}, çıxışınız uğurla qeydə alındı.")
                    return '', 200
                else:
                    return f"Error updating exit: {patch_response.text}", 500
            else:
                send_whatsapp_message(from_number, f"⚠️ {name.capitalize()}, aktiv giriş tapılmadı və ya artıq çıxış etmisiniz.")
                return '', 200

    # DÜZGÜN FORMAT DEYİLSƏ
    send_whatsapp_message(
        from_number,
        "⚠️ *Mesaj formatı düzgün deyil.*\n\nZəhmət olmasa aşağıdakı formatda yazın:\n\n📥 *Giriş üçün:*\nUmud (Giriş): 09:00\n\n📤 *Çıxış üçün:*\nUmud (Çıxış): 18:00"
    )
    return 'Invalid message format', 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)

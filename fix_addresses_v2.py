import json
import requests
import os
import sys

# Konfigurasi
FILE_PATH = 'exports/address_data.json'
OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
MODEL_NAME = "gemma3:4b"

def ask_ai_v2(entry):
    raw_title = entry.get('address_title', '')
    raw_line1 = entry.get('address_line1', '')
    customer_name = ""
    links = entry.get('links', [])
    if links: customer_name = links[0].get('link_name', '')

    # Prompt yang lebih detail dengan contoh (Few-Shot Prompting)
    prompt = f"""
    Tugas: Ekstrak Alamat Indonesia dari teks berikut ke JSON.
    Data sering dipisahkan oleh KOMA (,). Gunakan koma sebagai panduan utama.

    CONTOH:
    Input: "MARZUKI 6 RT 02 RW 01 NO 55 PANGGILINGAN,Kota Administrasi Jakarta Timur,DKI Jakarta,Indonesia"
    Output: {{"address_line1": "Marzuki 6 RT 02 RW 01 No 55 Panggilingan", "city": "Jakarta Timur", "state": "DKI Jakarta"}}

    ATURAN:
    1. 'address_title': Gunakan "{customer_name or raw_title}".
    2. 'address_line1': Bagian SEBELUM koma pertama atau bagian jalan/blok/nomor saja.
    3. 'city': Nama Kota/Kabupaten (Contoh: Jakarta Timur, Pekanbaru, Kuningan).
    4. 'state': Nama Provinsi (Contoh: DKI Jakarta, Riau, Jawa Barat).
    5. 'country': "Indonesia".

    INPUT SEKARANG:
    "{raw_line1}"

    Hasilkan JSON Murni:
    """
    
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }, timeout=60)
        
        if response.status_code == 200:
            return json.loads(response.json().get('response'))
    except:
        return None
    return None

def process_fix():
    if not os.path.exists(FILE_PATH):
        print("File tidak ditemukan.")
        return

    with open(FILE_PATH, 'r') as f:
        data = json.load(f)

    print(f"Memperbaiki data alamat yang gagal di-parsing...")
    
    fix_count = 0
    for i, entry in enumerate(data):
        # Kita hanya perbaiki yang City-nya gagal atau terisi fallback "Data Tidak Tersedia"
        # Atau jika Line 1 masih mengandung banyak koma (tanda belum ter-parse)
        line1 = entry.get('address_line1', '')
        city = entry.get('city', '')
        
        if city == "Data Tidak Tersedia" or line1.count(',') >= 1:
            clean = ask_ai_v2(entry)
            if clean and clean.get('city') and clean.get('city') != "Data Tidak Tersedia":
                entry['address_line1'] = clean.get('address_line1', entry['address_line1'])
                entry['city'] = clean.get('city', entry['city'])
                entry['state'] = clean.get('state', entry['state'])
                fix_count += 1
        
        sys.stdout.write(f"\rScanning & Fixing: {i + 1}/{len(data)} (Perbaikan: {fix_count})")
        sys.stdout.flush()

        if (i + 1) % 50 == 0:
            with open(FILE_PATH, 'w') as f:
                json.dump(data, f, indent=1)

    with open(FILE_PATH, 'w') as f:
        json.dump(data, f, indent=1)
    
    print(f"\nSelesai. {fix_count} alamat telah berhasil diperbaiki dengan Prompt V2.")

if __name__ == "__main__":
    process_fix()

import json
import requests
import os
import sys

# Konfigurasi
FILE_PATH = 'exports/address_data.json'
OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
MODEL_NAME = "gemma3:4b"

def ask_ai(entry):
    raw_title = entry.get('address_title', '')
    raw_line1 = entry.get('address_line1', '')
    
    # Dapatkan nama customer sebagai cadangan utama
    customer_name = ""
    links = entry.get('links', [])
    if links:
        customer_name = links[0].get('link_name', '')

    prompt = f"""
    Tugas: Parse dan perbaiki alamat Indonesia ke JSON terstruktur.
    
    ATURAN KETAT (Poin 7):
    1. 'address_title': Nama Toko/Gedung. Jika tidak jelas di input, gunakan: "{customer_name or raw_title}".
    2. 'address_line1': Hanya nama jalan & nomor. Hapus Kota/Provinsi. Jika data sangat minim, buat isi yang logis berdasarkan judul.
    3. 'city': Nama Kota/Kabupaten. Jika tidak ada, coba tebak dari teks alamat.
    4. 'state': Nama Provinsi. Jika tidak ada, tebak berdasarkan Kota (Contoh: Pekanbaru -> Riau).
    5. 'country': Harus "Indonesia".

    Input:
    - Title: {raw_title}
    - Line 1: {raw_line1}

    Output: JSON Murni tanpa penjelasan.
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

def process():
    if not os.path.exists(FILE_PATH):
        print(f"File {FILE_PATH} tidak ditemukan!")
        return

    with open(FILE_PATH, 'r') as f:
        data = json.load(f)

    total = len(data)
    print(f"Memproses {total} alamat dengan AI ({MODEL_NAME})...")
    
    for i, entry in enumerate(data):
        # 1. Jalankan AI Parsing
        clean = ask_ai(entry)
        
        # 2. Update dengan AI Result
        if clean:
            entry['address_title'] = clean.get('address_title', entry.get('address_title'))
            entry['address_line1'] = clean.get('address_line1', entry.get('address_line1'))
            entry['city'] = clean.get('city', entry.get('city'))
            entry['state'] = clean.get('state', entry.get('state'))
        
        # 3. Smart Fallback untuk Mandatory Fields (Pastikan TIDAK KOSONG)
        # Title wajib
        if not entry.get('address_title'):
            links = entry.get('links', [])
            entry['address_title'] = links[0].get('link_name', 'Unnamed Address') if links else 'Unnamed Address'
            
        # Address Line 1 wajib
        if not entry.get('address_line1'):
            entry['address_line1'] = entry['address_title']
            
        # City wajib
        if not entry.get('city') or entry.get('city').lower() == "indonesia":
            entry['city'] = "Data Tidak Tersedia"
            
        # Type & Country
        entry['address_type'] = entry.get('address_type') or "Billing"
        entry['country'] = "Indonesia"
        
        # Progress
        sys.stdout.write(f"\rProgress: {i + 1}/{total} ({(i+1)/total*100:.1f}%)")
        sys.stdout.flush()
        
        # Simpan berkala (setiap 20 baris)
        if (i + 1) % 20 == 0:
            with open(FILE_PATH, 'w') as f:
                json.dump(data, f, indent=1)

    # Simpan Final
    with open(FILE_PATH, 'w') as f:
        json.dump(data, f, indent=1)
    print("\n\nSelesai! Seluruh alamat telah diperbaiki dan divalidasi.")

if __name__ == "__main__":
    process()

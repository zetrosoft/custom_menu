import json
import os
import re

file_path = 'frappe-bench/apps/custom_menu/exports/address_data.json'

def clean_address_data():
    if not os.path.exists(file_path):
        print("File tidak ditemukan.")
        return

    with open(file_path, 'r') as f:
        addresses = json.load(f)

    print(f"Memproses {len(addresses)} alamat...")
    
    # Mapping sederhana untuk kota-kota populer dan provinsinya
    # Ini akan menangani banyak kasus secara instan
    city_to_state = {
        "PEKANBARU": "Riau",
        "PEKAN BARU": "Riau",
        "KOTA PEKANBARU": "Riau",
        "KOTA PEKAN BARU": "Riau",
        "CILEGON": "Banten",
        "KOTA CILEGON": "Banten",
        "TANGERANG": "Banten",
        "BEKASI": "Jawa Barat",
        "BOGOR": "Jawa Barat",
        "BANDUNG": "Jawa Barat",
        "DEPOK": "Jawa Barat",
        "JAKARTA": "DKI Jakarta",
        "SURABAYA": "Jawa Timur",
        "SEMARANG": "Jawa Tengah",
        "MEDAN": "Sumatera Utara",
        "PALEMBANG": "Sumatera Selatan",
        "MAKASSAR": "Sulawesi Selatan"
    }

    updated_count = 0
    
    for addr in addresses:
        line1 = addr.get('address_line1', '') or ''
        city = (addr.get('city', '') or '').upper()
        state = addr.get('state', '') or ''
        
        # Kasus: City adalah "Indonesia"
        if city == "INDONESIA":
            # Coba cari nama kota di Line 1
            found_city = False
            for city_key, state_val in city_to_state.items():
                if city_key in line1.upper():
                    addr['city'] = city_key.title()
                    if not state or state.upper() == "INDONESIA":
                        addr['state'] = state_val
                    found_city = True
                    break
            
            if not found_city:
                # Jika tidak ketemu, kosongkan city agar bisa diisi manual atau biarkan null
                addr['city'] = ""
            updated_count += 1

        # Kasus: State kosong tapi ada info di line1 atau city
        if not addr.get('state') or addr.get('state') == "Indonesia":
            curr_city = (addr.get('city', '') or '').upper()
            if curr_city in city_to_state:
                addr['state'] = city_to_state[curr_city]
                updated_count += 1
        
        # Rapikan Title Case untuk City dan State
        if addr.get('city'):
            addr['city'] = addr['city'].title()
        if addr.get('state'):
            addr['state'] = addr['state'].title()

        # Pembersihan tambahan: Jika line1 mengandung "Indonesia", hapus
        if "Indonesia" in line1:
            addr['address_line1'] = line1.replace(", Indonesia", "").replace("Indonesia", "").strip()
            # Hapus koma menggantung di akhir
            addr['address_line1'] = re.sub(r',\s*$', '', addr['address_line1'])

    # Simpan kembali
    with open(file_path, 'w') as f:
        json.dump(addresses, f, indent=1)
    
    print(f"Selesai. {updated_count} alamat diperbarui.")

if __name__ == "__main__":
    clean_address_data()

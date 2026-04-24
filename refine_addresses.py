import json
import os
import re

file_path = 'frappe-bench/apps/custom_menu/exports/address_data.json'

def refine_address_line1():
    if not os.path.exists(file_path):
        print("File tidak ditemukan.")
        return

    with open(file_path, 'r') as f:
        addresses = json.load(f)

    print(f"Membersihkan {len(addresses)} baris alamat...")
    
    refined_count = 0
    
    for addr in addresses:
        line1 = addr.get('address_line1') or ""
        city = addr.get('city') or ""
        state = addr.get('state') or ""
        
        original_line1 = line1
        
        # Daftar kata yang harus dihapus dari line1 jika sudah ada di kolom city/state
        to_remove = []
        if city:
            to_remove.extend([city, f"Kota {city}", f"Kabupaten {city}", f"Kab {city}", f"KOTA {city.upper()}", f"KABUPATEN {city.upper()}"])
        if state:
            to_remove.extend([state, f"Provinsi {state}", f"Prov {state}", f"PROVINSI {state.upper()}"])
            
        # Hapus kata-kata tersebut dari line1 (case insensitive)
        for word in to_remove:
            if not word or len(word) < 3: continue
            # Gunakan regex untuk menghapus kata sebagai word boundary atau bagian dari string alamat
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            line1 = pattern.sub("", line1)
            
        # Bersihkan karakter pemisah yang tertinggal (koma, titik, spasi berlebih)
        line1 = re.sub(r'^[,\s.-]+', '', line1) # Awal string
        line1 = re.sub(r'[,\s.-]+$', '', line1) # Akhir string
        line1 = re.sub(r'\s{2,}', ' ', line1)   # Spasi ganda
        line1 = re.sub(r',\s*,', ',', line1)    # Koma ganda
        
        if line1 != original_line1:
            addr['address_line1'] = line1
            refined_count += 1

    # Simpan kembali
    with open(file_path, 'w') as f:
        json.dump(addresses, f, indent=1)
    
    print(f"Selesai. {refined_count} baris alamat telah dirapikan.")

if __name__ == "__main__":
    refine_address_line1()

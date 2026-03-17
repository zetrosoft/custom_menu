# Custom Menu & AI Smart Importer

Aplikasi kustomisasi untuk ekosistem **Frappe Framework** yang dirancang untuk meningkatkan pengalaman pengguna melalui manajemen branding yang dinamis, otomatisasi pembersihan data, dan integrasi kecerdasan buatan (AI) untuk proses import data yang lebih cerdas.

## 🚀 Fitur Utama

### 1. Custom Branding Settings
Memungkinkan administrator untuk mengubah identitas visual sistem tanpa perlu menyentuh kode program:
*   **Dynamic Navbar & Logo:** Mengubah logo navbar dan sidebar secara real-time.
*   **Login Page Customization:** Mengatur tampilan halaman login termasuk gambar latar belakang dan pesan selamat datang.
*   **Brand Colors:** Penyesuaian skema warna dasar sistem agar sesuai dengan identitas perusahaan.

### 2. AI Smart Importer (Local LLM Integration)
Fitur unggulan untuk melakukan import data masal (seperti Customer, Supplier, atau Item) dengan bantuan AI:
*   **Data Cleaning:** Secara otomatis membersihkan data dari format yang tidak konsisten (misal: "DISTRIBUTOR BATAM" menjadi "Distributor Batam").
*   **Pattern Recognition:** Mengenali data sampah atau duplikat sebelum masuk ke database.
*   **Local LLM Processing:** Menggunakan model bahasa lokal (seperti Llama 3 atau Mistral via Ollama) untuk memproses ribuan baris data tanpa mengirim data sensitif ke server eksternal (OpenAI/Claude).

### 3. Clear Transactions Utility
Halaman khusus untuk membersihkan data transaksi dalam fase pengembangan atau sebelum sistem *Go-Live*:
*   Penghapusan data secara aman tanpa merusak integritas tabel master.
*   Log pembersihan yang terdokumentasi.

### 4. Automated Export/Import Data
Script utilitas untuk melakukan sinkronisasi data antar site atau backup data tertentu dalam format JSON yang bersih.

---

## 🛠 Panduan Instalasi

Pastikan Anda berada di dalam folder `frappe-bench` sebelum menjalankan perintah ini:

1.  **Dapatkan aplikasi dari repositori:**
    ```bash
    bench get-app https://bitbucket.org/bijaktechno/custom_menu.git
    ```

2.  **Instal aplikasi ke site target:**
    ```bash
    bench --site [nama-site-anda] install-app custom_menu
    ```

3.  **Migrasi database:**
    ```bash
    bench --site [nama-site-anda] migrate
    ```

---

## 🤖 Integrasi LLM Lokal

Fitur **AI Smart Importer** menggunakan API lokal untuk privasi data maksimal.

### Persyaratan:
*   **Ollama** terinstal di server.
*   Model yang direkomendasikan: `llama3` atau `mistral`.

### Cara Kerja:
1.  Aplikasi mengirimkan potongan data JSON ke endpoint Ollama lokal.
2.  LLM melakukan pembersihan teks, standarisasi casing (Title Case), dan validasi struktur.
3.  Data yang telah "bersih" dikembalikan ke Frappe untuk divalidasi oleh `Document API`.

---

## 📂 Struktur Direktori Penting

*   `/custom_menu`: Logika inti aplikasi (Python & JS).
*   `/exports`: Berisi data master (Customer, Address, Contact) yang telah dibersihkan.
*   `/public/js`: File kustomisasi frontend untuk branding.

---

## 📝 Catatan Tambahan
*   **Branch:** Selalu gunakan branch `main` untuk versi stabil.
*   **Data Integrity:** Gunakan fitur *Clear Transactions* dengan hati-hati karena bersifat destruktif pada data transaksi.

---
Dikembangkan oleh **Bijak Techno** untuk efisiensi manajemen data ERP.

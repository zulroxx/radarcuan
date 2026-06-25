# Contoh Pesan ke AI Agent

Dokumen ini berisi contoh-contoh pesan yang dapat dikirimkan ke AI agent untuk berbagai skenario pengembangan perangkat lunak.

## Daftar Isi

1. [Refactoring Kode](#1-refactoring-kode)
2. [Bug Fixing](#2-bug-fixing)
3. [Menambahkan Fitur Baru](#3-menambahkan-fitur-baru)
4. [Code Review](#4-code-review)
5. [Menulis Unit Test](#5-menulis-unit-test)
6. [Debugging](#6-debugging)
7. [Optimasi Kinerja](#7-optimasi-kinerja)
8. [Eksplorasi Codebase](#8-eksplorasi-codebase)
9. [Dokumentasi](#9-dokumentasi)
10. [Refactoring Database](#10-refactoring-database)

---

## 1. Refactoring Kode

### Refactor fungsi menjadi lebih modular

```
Fungsi handleSubmit di src/components/CheckoutForm.js terlalu panjang (~120 baris).
Refactor fungsi ini dengan cara:
1. Ekstrak validasi form ke fungsi terpisah
2. Ekstrak logika pembayaran ke custom hook useCheckout
3. Ekstrak error handling ke fungsi terpisah
Pastikan semua fungsionalitas yang ada tetap berjalan dengan benar.
```

### Mengganti state management

```
Saat ini proyek menggunakan Context API untuk state management.
Pindahkan semua state global ke Zustand.
Stores yang perlu dibuat:
- store/authStore.js
- store/cartStore.js
- store/uiStore.js
Hapus semua file Context yang sudah tidak terpakai setelah migrasi.
```

### Refactor class component ke functional component

```
Refactor komponen ProfilePage yang masih menggunakan class component
menjadi functional component dengan hooks.
File: src/pages/ProfilePage.js
Gunakan useState, useEffect, dan useCallback sesuai kebutuhan.
```

---

## 2. Bug Fixing

### Bug login tidak konsisten

```
**Bug:** Login kadang berhasil kadang gagal tanpa pesan error yang jelas.
**Langkah reproduksi:**
1. Buka halaman login
2. Masukkan email: user@example.com, password: correctpassword
3. Klik tombol Login
4. Kadang redirect ke dashboard, kadang stuck di halaman login

**Environment:**
- Browser: Chrome 120, Firefox 119
- Mode: Development

Cari penyebabnya di auth flow dan perbaiki.
```

### Data binding issue pada form

```
Field "tanggal lahir" di halaman EditProfile tidak menampilkan
data yang sudah tersimpan. Sebaliknya, field tersebut selalu kosong
meskipun data ada di database.

Cek alur data dari API → state → form component.
Perbaiki binding agar data tampil dengan benar.
```

---

## 3. Menambahkan Fitur Baru

### Dark mode toggle

```
Tambahkan fitur dark mode ke aplikasi.
Requirements:
1. Tombol toggle di header (ikon matahari/bulan)
2. Menggunakan CSS custom properties untuk tema
3. Simpan preferensi user ke localStorage
4. Terapkan tema saat halaman pertama kali dimuat (sebelum render)
5. File yang perlu diubah:
   - src/App.js
   - src/components/Header.js
   - src/styles/themes.css (buat baru)
   - src/hooks/useTheme.js (buat baru)
```

### Export to CSV

```
Tambah fitur export data transaksi ke CSV di halaman laporan.
Requirements:
- Tombol "Export CSV" di atas tabel
- Kolom yang diexport: ID, Tanggal, Deskripsi, Jumlah, Status
- Nama file: transactions_YYYYMMDD_HHmmss.csv
- Gunakan library existing (papa parse atau file-saver jika sudah ada)
- Tampilkan loading state selama proses export
```

### Pagination untuk tabel

```
Tabel user di halaman Admin saat ini menampilkan semua data sekaligus.
Tambahkan pagination server-side dengan ketentuan:
- 10 data per halaman
- Tampilkan tombol Previous/Next dan nomor halaman
- URL API menggunakan query params: ?page=1&limit=10
- Tampilkan total data dan total halaman
- File terkait: src/pages/admin/UsersPage.js, src/api/users.js
```

---

## 4. Code Review

### Review pull request

```
Review PR #42 yang menambahkan fitur reset password.
Periksa:
1. Apakah ada security vulnerability?
2. Apakah token reset password sudah expired?
3. Apakah validasi input sudah benar?
4. Apakah ada error handling yang kurang?
5. Apakah kode mengikuti style guide yang ada?
6. Apakah unit test sudah mencakup skenario penting?
Beri komentar pada baris yang perlu diperbaiki.
```

### Review implementasi API

```
Review implementasi endpoint GET /api/products.
File terkait:
- controllers/productController.js
- services/productService.js
- models/Product.js

Perhatikan:
- N+1 query problem
- Error handling
- Validasi query params
- Response format yang konsisten
```

---

## 5. Menulis Unit Test

### Test untuk utility functions

```
Buat unit test untuk semua fungsi di src/utils/validators.js menggunakan Jest.
Fungsi yang ada:
- validateEmail(email) → return boolean
- validatePhone(phone) → return boolean
- sanitizeInput(input) → return string tanpa karakter berbahaya
- formatCurrency(amount) → return string format Rp x.xxx

Coverage target: 100% untuk semua fungsi.
Gunakan describe/it pattern yang sudah ada di proyek ini.
```

### Integration test untuk API endpoint

```
Buat integration test untuk autentikasi API menggunakan supertest.
Endpoint yang perlu di-test:
- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/refresh-token
- POST /api/auth/logout

Test skenario:
1. Register sukses
2. Register dengan email sudah terdaftar
3. Login dengan password salah
4. Refresh token dengan token valid
5. Refresh token dengan token expired
6. Logout tanpa token
```

---

## 6. Debugging

### Memory leak terdeteksi

```
Terjadi memory leak setelah halaman dashboard dibuka selama 30+ menit.
Gunakan Chrome DevTools heap snapshot untuk investigasi.
Periksa:
- Apakah ada setInterval/setTimeout yang tidak di-clear?
- Apakah ada event listener yang tidak di-remove?
- Apakah ada WebSocket connection yang tidak di-close?
- Apakah ada infinite loop di useEffect?

File yang paling mungkin bermasalah: src/pages/Dashboard.js dan komponen di dalamnya.
```

### Production bug: 404 untuk semua route

```
Setelah deploy ke Vercel, semua halaman selain halaman utama
mengembalikan 404. Di local development tidak ada masalah.

Ini sudah dipastikan terjadi di production, bukan development.
Cari solusi untuk static site hosting (Vercel).
```

---

## 7. Optimasi Kinerja

### Mengurangi bundle size

```
Bundle size saat ini 2.3 MB (production). Target maksimal 500 KB.

Langkah optimasi:
1. Analisis bundle dengan webpack-bundle-analyzer
2. Lazy load komponen yang tidak langsung terlihat
3. Cek apakah ada library yang bisa diganti dengan alternatif lebih ringan
4. Implement code splitting untuk route-based chunks
5. Optimasi gambar (format, ukuran, lazy loading)
```

### Optimasi render ulang tidak perlu

```
Komponen ProductList di halaman katalog merender ulang
setiap kali state apapun berubah di aplikasi.

Perbaiki dengan:
1. Memoize komponen dengan React.memo
2. Gunakan useMemo untuk computed values
3. Gunakan useCallback untuk fungsi yang di-pass sebagai props
4. Pastikan selector Redux/Zustand spesifik (tidak mengambil seluruh state)
```

---

## 8. Eksplorasi Codebase

### Memahami alur autentikasi

```
Jelaskan alur autentikasi dari login sampai logout di proyek ini.
Saya perlu tahu:
1. Dimana token JWT disimpan?
2. Bagaimana cara token dikirim ke server?
3. Siapa yang handle token expiration?
4. Apakah ada refresh token mechanism?
5. Dimana letak guard/protected route?

Berikan ringkasan beserta path file yang relevan.
```

### Dependency graph antar modul

```
Buat dependency graph untuk modul-modul di folder src/services/.
Saya ingin tahu:
1. Service mana yang paling banyak digunakan?
2. Apakah ada circular dependency?
3. Service mana yang tergantung pada service lain?
Tampilkan dalam format teks tree.
```

---

## 9. Dokumentasi

### Dokumentasi API

```
Buat dokumentasi API untuk semua endpoint di folder routes/api/.
Format: OpenAPI/Swagger YAML.
Setiap endpoint harus mencakup:
- Method dan path
- Request body schema
- Response schema (success dan error)
- Contoh request dan response
- Authentication requirements (jika ada)
```

### Setup guide untuk developer baru

```
Buat SETUP.md untuk developer baru yang akan bekerja di proyek ini.
Cakupan:
1. Prerequisites (Node version, database, tools)
2. Langkah instalasi (clone, install dependencies, environment variables)
3. Cara menjalankan development server
4. Cara menjalankan test
5. Cara build untuk production
6. Troubleshooting umum
```

---

## 10. Refactoring Database

### Migrasi database

```
Buat migration script untuk menambahkan kolom berikut ke tabel users:
- last_login_at (datetime, nullable)
- login_count (integer, default 0)
- avatar_url (varchar(500), nullable)
- is_verified (boolean, default false)

Gunakan migration tool yang sudah ada di proyek (Knex/Sequelize/TypeORM).
Buat juga rollback script.
```

### Optimasi query

```
Query berikut slow (>5 detik) di production:
SELECT * FROM orders WHERE status = 'pending' ORDER BY created_at DESC;

Analisis dengan EXPLAIN dan berikan solusi:
1. Apakah perlu index tambahan?
2. Apakah query bisa direfactor?
3. Apakah perlu denormalisasi?

File: repositories/orderRepository.js, baris 45-60.
```

---

## Format Pesan yang Efektif

| Komponen | Keterangan | Contoh |
|----------|------------|--------|
| **Konteks** | Latar belakang masalah/tugas | "Saat ini proyek menggunakan Context API..." |
| **Tujuan** | Apa yang ingin dicapai | "Pindahkan semua state global ke Zustand" |
| **Batasan** | Aturan yang harus diikuti | "Gunakan library yang sudah ada" |
| **File Terkait** | Path file yang relevan | "File: src/pages/ProfilePage.js" |
| **Kriteria Sukses** | Bagaimana mengecek keberhasilan | "Build production harus tetap sukses" |

---

*Dokumen ini dibuat sebagai referensi untuk memberikan instruksi yang jelas dan terstruktur kepada AI agent.*

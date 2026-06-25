# Append-Only Guard — Order Book Protection

Dokumen ini menjelaskan sistem proteksi **append-only** pada Order Book,
yang mencegah AI agent atau kode apapun mengubah/menghapus data yang sudah
tersimpan di database.

## Arsitektur

```
┌─────────────────────────────────────────────────────┐
│                   API Layer                          │
│  GET /api/order-book/*  (read-only endpoints)        │
└──────────────┬──────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────┐
│             OrderBookStore                           │
│  - append_snapshot()  ← satu-satunya method write    │
│  - get_latest_snapshot()                             │
│  - get_history()                                     │
│  - get_snapshot_by_id()                              │
│  - get_all_snapshots()                               │
│  - load_existing_order_map()                         │
└──────┬──────────────────────────┬───────────────────┘
       │                          │
┌──────▼──────────┐    ┌─────────▼──────────┐
│  MongoDB         │    │  File (JSON)       │
│  AppendOnly-     │    │  Append + Validasi │
│  Collection      │    │                    │
└─────────────────┘    └────────────────────┘
```

## Layer 1 — MongoDB: `AppendOnlyCollection` (`backend/db_guard.py`)

Membungkus collection MongoDB dan **memblokir semua operasi destruktif**:

| Operasi | Status | Keterangan |
|---------|--------|------------|
| `find()`, `find_one()` | ✅ Diizinkan | Read |
| `count_documents()`, `aggregate()` | ✅ Diizinkan | Read |
| `insert_one()`, `insert_many()` | ✅ Diizinkan | Insert |
| `update_one()`, `update_many()` | ❌ Diblokir | `PermissionError` |
| `delete_one()`, `delete_many()` | ❌ Diblokir | `PermissionError` |
| `replace_one()`, `find_one_and_replace()` | ❌ Diblokir | `PermissionError` |
| `find_one_and_delete()`, `find_one_and_update()` | ❌ Diblokir | `PermissionError` |
| `bulk_write()` | ❌ Diblokir | `PermissionError` |
| `drop()` | ❌ Diblokir | `PermissionError` |

Jika ada kode yang mencoba memanggil operasi yang diblokir, akan muncul error:

```
PermissionError: Operasi 'update_one' tidak diizinkan pada collection
append-only. Hanya operasi read dan insert yang diperbolehkan.
```

### Cara Kerja

```python
class AppendOnlyCollection:
    _ALLOWED_OPS = _READ_OPS | _WRITE_OPS

    def __getattr__(self, name):
        if name not in _ALLOWED_OPS:
            raise PermissionError(...)
        return getattr(self._col, name)
```

Semua attribute lookup pada collection akan dicek terhadap daftar operasi
yang diizinkan. Operasi yang tidak dikenal (termasuk method baru dari
driver MongoDB di masa depan) otomatis diblokir.

## Layer 2 — Storage Manager: `OrderBookStore` (`backend/order_book_store.py`)

Abstraction layer antara API endpoints dan storage. Memiliki **satu
method write**:

### Write method

```python
async def append_snapshot(snapshot: Dict) -> bool:
```

Method ini bertanggung jawab menyimpan snapshot baru ke:
1. MongoDB (via `AppendOnlyCollection.insert_one`)
2. File JSON fallback (via `_append_to_file`)

Tidak ada method `update_snapshot()`, `delete_snapshot()`, atau `replace_snapshot()`.

### Read methods

```python
async def get_latest_snapshot() -> Optional[Dict]
async def get_history(limit=50, offset=0) -> Dict
async def get_snapshot_by_id(snapshot_id) -> Optional[Dict]
async def get_all_snapshots() -> List[Dict]
async def load_existing_order_map() -> Dict[Tuple[str, str], Dict]
```

Semua method read mencoba MongoDB terlebih dahulu, fallback ke file JSON.

### File Validation

```python
def _append_to_file(self, snapshot):
    old_data = self._load_file()
    old_ids = {s["id"] for s in old_data}
    new_data = old_data + [snapshot]
    self._save_file(new_data)

    # Validasi: pastikan tidak ada entry lama yang hilang
    saved = self._load_file()
    saved_ids = {s["id"] for s in saved}
    missing = old_ids - saved_ids
    if missing:
        self._save_file(old_data)  # rollback
        raise RuntimeError("Data corruption detected")
```

Setelah write, diverifikasi bahwa semua entry dari data lama masih ada
di data baru. Jika ada yang hilang, file di-rollback ke state sebelumnya.

## Layer 3 — API: Read-Only Endpoints

Semua endpoint Order Book adalah **read-only GET**:

| Endpoint | Fungsi |
|----------|--------|
| `GET /api/order-book/simulation` | Mendapatkan snapshot terbaru |
| `GET /api/order-book/history` | Riwayat snapshot (paginasi) |
| `GET /api/order-book/history/{snapshot_id}` | Detail snapshot |
| `GET /api/order-book/accuracy` | Metrik akurasi posisi closed |

Tidak ada `POST`, `PUT`, `PATCH`, atau `DELETE` endpoint untuk order book.

## Layer 4 — Frontend: Read-Only Display

Komponen `OrderBook.jsx` di frontend hanya membaca data via
`GET /api/order-book/simulation`. Tidak ada form input atau tombol
untuk mengubah/menghapus data.

Price update dilakukan via merge `buy_price` dari fetch pertama dengan
data real-time dari fetch berikutnya — tanpa menyentuh database.

## Menambahkan Proteksi ke Collection Lain

Untuk menerapkan proteksi yang sama ke collection MongoDB lain:

```python
from db_guard import AppendOnlyCollection

# Bungkus collection
collection = AppendOnlyCollection(db["nama_collection"])

# Hanya read + insert yang diizinkan
data = await collection.find({"status": "active"}).to_list(100)
await collection.insert_one({...})
collection.update_one(...)  # → PermissionError!
```

## Pengujian

Untuk memverifikasi proteksi berfungsi:

```python
from db_guard import AppendOnlyCollection

# Mock collection
class MockCol:
    name = "test"
    async def find_one(self, *a, **kw): return {}
    async def update_one(self, *a, **kw): return None

col = AppendOnlyCollection(MockCol())
await col.find_one({})           # OK
col.update_one({}, {"$set": {}}) # PermissionError
```

## Catatan untuk Developer

- Jangan bypass `AppendOnlyCollection` — selalu gunakan `OrderBookStore`
  untuk akses order book
- Jika perlu menambahkan fitur baru yang membutuhkan write ke order book,
  tambahkan method baru di `OrderBookStore` yang tetap menggunakan
  `AppendOnlyCollection.insert_one` (bukan `update`/`delete`)
- Untuk backup/restore data, gunakan MongoDB tools langsung
  (`mongodump`/`mongorestore`), bukan melalui aplikasi

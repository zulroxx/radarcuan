# Plan: Hapus On-Demand Stock Recommendations, Ganti dengan Batch-Only + Polling

## Masalah
Endpoint `/api/sector/{sector_name}/stocks` di `server.py:1981-2002` saat cache kosong akan **generate on-demand per-sektor** via `recommend_stocks()` yang call Mistral API. Ini yang bikin timeout 30s di frontend. Yang diinginkan: **hanya batch scheduler** yang boleh generate rekomendasi, endpoint cuma baca cache.

---

## 1. `backend/scheduler.py` — Progress Tracking

### 1a. Tambah variabel global (sekitar baris 29-31)

```python
_scheduler_start_time: Optional[float] = None
_scheduler_current_agent_idx: Optional[int] = None
_scheduler_agent_start_time: Optional[float] = None
_SCHEDULER_AGENTS_ORDER = [
    "tradingview", "macro", "news", "sector_predictions",
    "stock_recommendations", "order_book",
]
```

Pindahkan `AGENT_TIMEOUT = 600` ke scope global (sekarang di dalam fungsi `run_scheduled_fetch`).

### 1b. Set start time di awal `run_scheduled_fetch`

Sesudah baris `_SCHEDULER_RUN_ID = run_id` (baris 768), tambah:

```python
_scheduler_start_time = time.monotonic()
_scheduler_current_agent_idx = None
_scheduler_agent_start_time = None
```

### 1c. Update index sebelum tiap agent jalan

Di loop agents (baris 827), ganti:

```python
for name, coro in AGENTS:
```

menjadi:

```python
for idx, (name, coro) in enumerate(AGENTS):
    _scheduler_current_agent_idx = idx
    _scheduler_agent_start_time = time.monotonic()
```

### 1d. Reset di `finally` block (baris 851-852)

Tambah:

```python
_scheduler_start_time = None
_scheduler_current_agent_idx = None
_scheduler_agent_start_time = None
```

### 1e. Fungsi helper `get_scheduler_progress()`

Tambah fungsi baru (sebelum `get_stale_lock_seconds`):

```python
def get_scheduler_progress() -> Dict[str, Any]:
    """Return current scheduler progress info for frontend polling."""
    if _scheduler_start_time is None or _SCHEDULER_RUN_ID is None:
        return {"running": False}
    
    now = time.monotonic()
    elapsed_total = now - _scheduler_start_time
    idx = _scheduler_current_agent_idx if _scheduler_current_agent_idx is not None else 0
    current_agent = _SCHEDULER_AGENTS_ORDER[idx] if idx < len(_SCHEDULER_AGENTS_ORDER) else "unknown"
    
    # Cari index stock_recommendations (selalu index 4)
    STOCK_RECS_IDX = 4
    
    if idx < STOCK_RECS_IDX:
        # Belum sampai stock recs — estimasi conservative
        remaining_agents = STOCK_RECS_IDX - idx
        estimated_seconds = remaining_agents * AGENT_TIMEOUT
    elif idx == STOCK_RECS_IDX:
        # Stock recs sedang jalan — estimasi sisa waktu agent ini
        agent_elapsed = now - (_scheduler_agent_start_time or now)
        estimated_seconds = max(30, AGENT_TIMEOUT - agent_elapsed)
    else:
        # Stock recs sudah selesai
        estimated_seconds = 0
    
    return {
        "running": True,
        "run_id": _SCHEDULER_RUN_ID,
        "current_agent": current_agent,
        "current_agent_idx": idx,
        "estimated_seconds_remaining": int(estimated_seconds),
        "elapsed_total_seconds": int(elapsed_total),
    }
```

---

## 2. `backend/server.py` — Ubah Endpoint `/sector/{sector_name}/stocks`

### 2a. Ganti blok "No cache — generate on-demand" (baris 1945-2002)

**Yang dihapus:**
- Per-sector lock (`_rec_locks_lock`, `_rec_locks`)
- Double-check cache
- Call `recommend_stocks(...)` on-demand
- Save to MongoDB

**Yang baru:**

```python
        # No cache — cek apakah batch scheduler sedang berjalan
        from scheduler import get_scheduler_progress, is_scheduler_running, AGENT_TIMEOUT, _SCHEDULER_AGENTS_ORDER
        from agent_status import AGENT_STATUS

        progress = get_scheduler_progress()
        stock_rec_status = AGENT_STATUS.get("stock_recommendations", {}).get("status", "unknown")

        if progress.get("running") or stock_rec_status == "running":
            # Scheduler sedang jalan — kasih estimasi ke frontend
            estimated = progress.get("estimated_seconds_remaining", AGENT_TIMEOUT * 2)
            return {
                "success": False,
                "processing": True,
                "run_id": progress.get("run_id"),
                "estimated_seconds_remaining": estimated,
                "message": (
                    f"Batch agent sedang menyusun rekomendasi saham untuk semua sektor. "
                    f"Estimasi selesai dalam ~{max(1, estimated // 60)} menit. "
                    f"Halaman akan merefresh otomatis."
                ),
            }
        else:
            # Scheduler tidak jalan — data memang belum ada
            return {
                "success": False,
                "processing": False,
                "message": (
                    "Rekomendasi saham belum tersedia. "
                    "Sistem akan memperbarui secara otomatis sesuai jadwal. "
                    "Admin dapat memicu generate manual melalui panel Admin."
                ),
            }
```

Hapus juga variabel `_rec_locks` dan `_rec_locks_lock` serta `_MAX_LOCK_DICT_SIZE` jika tidak dipakai di endpoint lain (cek dulu).

---

## 3. `frontend/src/components/AgentDashboard/PredictionDashboard.jsx`

### 3a. Tambah state baru

```js
const [stockProcessing, setStockProcessing] = useState(null);
// stockProcessing = { estimated_seconds: 300, run_id: "abc" } | null
```

### 3b. Tambah `useRef` untuk auto-retry timer

```js
const stockRetryRef = useRef(null);
```

### 3c. Update `handleSectorSelect` (baris 438-465)

```js
const handleSectorSelect = useCallback(async (prediction) => {
    setSelectedSector(prediction);
    setStockProcessing(null);
    
    // Clear retry timer
    if (stockRetryRef.current) clearTimeout(stockRetryRef.current);
    
    const cacheKey = LS_STOCK_PREFIX + prediction.sector;
    const cached = lsGet(cacheKey, STOCK_CACHE_TTL);
    if (cached) {
      setStockRecs(cached);
      return;
    }
    setStockLoading(true);
    setStockRecs([]);
    try {
      const response = await axios.get(
        `${API_BASE}/sector/${encodeURIComponent(prediction.sector)}/stocks`,
        { params: { limit: 10 } }
      );
      if (response.data.success) {
        const recs = response.data.recommendations || [];
        setStockRecs(recs);
        setStockProcessing(null);
        lsSet(cacheKey, recs);
        toast.success(`Rekomendasi saham sektor ${prediction.sector} dimuat.`);
      } else if (response.data.processing) {
        // Batch sedang jalan — tampilkan estimasi + auto-retry
        setStockProcessing({
          estimated_seconds: response.data.estimated_seconds_remaining || 300,
          run_id: response.data.run_id,
        });
        toast.info(response.data.message || "Data masih diproses...");
        // Auto-retry dalam 30 detik
        stockRetryRef.current = setTimeout(() => {
          handleSectorSelect(prediction);
        }, 30000);
      } else {
        // Data memang belum ada
        setStockProcessing(null);
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Gagal memuat rekomendasi";
      toast.error(msg);
    } finally {
      setStockLoading(false);
    }
  }, []);
```

> **Catatan**: `handleSectorSelect` dipanggil ulang dari dalam closure. Pastikan `useCallback` dependencies tidak berubah tak terduga. Alternatif: gunakan `useRef` untuk menyimpan callback.

### 3d. Cleanup retry timer di `useEffect`

```js
useEffect(() => {
  return () => {
    if (stockRetryRef.current) clearTimeout(stockRetryRef.current);
  };
}, []);
```

### 3e. UI baru untuk `stockProcessing` (ganti bagian baris 557-573)

```jsx
{stockLoading ? (
  <LoadingState message="Agent sedang menganalisis fundamental saham..." />
) : stockProcessing ? (
  <Card className="border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20">
    <CardContent className="flex flex-col items-center py-8 text-center">
      <ClockClockwise className="mb-3 h-8 w-8 text-amber-500" />
      <p className="text-sm font-medium text-amber-800 dark:text-amber-300">
        Batch Agent Sedang Memproses
      </p>
      <p className="mt-2 text-xs text-amber-600 dark:text-amber-400 max-w-md">
        Sistem sedang menyusun rekomendasi saham untuk seluruh sektor secara bersamaan.
        Halaman akan refresh otomatis saat data tersedia.
      </p>
      <div className="mt-4 flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400">
        <ArrowClockwise className="h-3 w-3 animate-spin" />
        Estimasi selesai: ~{Math.ceil(stockProcessing.estimated_seconds / 60)} menit
      </div>
      <p className="mt-1 text-[10px] text-amber-400 dark:text-amber-500">
        Run ID: {stockProcessing.run_id}
      </p>
    </CardContent>
  </Card>
) : stockRecs.length === 0 ? (
  <Card className="border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
    <CardContent className="flex flex-col items-center py-10">
      <p className="text-sm text-slate-600 dark:text-slate-400">
        Belum ada rekomendasi saham untuk sektor ini.
      </p>
      <p className="mt-2 text-xs text-slate-400 dark:text-slate-500">
        Rekomendasi akan tersedia setelah scheduler batch selesai dijalankan.
      </p>
    </CardContent>
  </Card>
) : ...
```

### 3f. Import tambahan

Tambah `ClockClockwise` dari `@phosphor-icons/react`:

```js
import {
  // ... existing imports
  ClockClockwise,
} from "@phosphor-icons/react";
```

---

## 4. Verifikasi

1. Cek apakah `_rec_locks`, `_rec_locks_lock`, `_MAX_LOCK_DICT_SIZE` dipakai di endpoint lain (`grep -r "_rec_locks" backend/`)
2. Restart backend
3. Restart frontend
4. Test: klik sektor saat cache kosong → lihat UI estimasi → tunggu auto-retry → data muncul
5. Test: klik sektor saat cache ada → langsung muncul (tidak berubah)
6. Cek log backend untuk `get_scheduler_progress` dan endpoint response

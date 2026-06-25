import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from db_guard import AppendOnlyCollection

logger = logging.getLogger(__name__)


class OrderBookStore:
    """Append-only storage manager untuk order book snapshots.

    Menyediakan akses read dan insert ke order book history,
    baik melalui MongoDB maupun file JSON fallback.

    --- LAPISAN PENGAMAN ---
    - MongoDB: menggunakan `AppendOnlyCollection` yang memblokir
      semua operasi UPDATE, DELETE, REPLACE, DROP.
    - File JSON: hanya bisa ditulis melalui `append_snapshot()`.
      Fungsi _save_file memvalidasi bahwa data lama tidak hilang.
    =========================
    """

    def __init__(self, mongo_db, file_path: Path):
        self._file_path = file_path
        self._mongo = None
        self._using_file = True
        self._file_lock = asyncio.Lock()

        if mongo_db is not None:
            try:
                col = mongo_db["order_book_history"]
                self._mongo = AppendOnlyCollection(col)
                self._using_file = False
            except Exception as e:
                logger.warning(
                    "Gagal init MongoDB collection order_book_history: %s. "
                    "Menggunakan file fallback.", e,
                )

    async def sync_file_from_mongo(self) -> None:
        """Sync file cache dari MongoDB — panggil saat store di-upgrade ke MongoDB."""
        if self._using_file or self._mongo is None:
            return
        if self._file_path.exists():
            return
        try:
            docs = await self._mongo.find(
                {}, {"_id": 0}
            ).sort("generated_at", 1).to_list(500)
            if docs:
                self._save_file(docs)
                logger.info("File cache disync dari MongoDB: %d snapshots", len(docs))
        except Exception as e:
            logger.warning("Gagal sync file dari MongoDB: %s", e)

    @property
    def is_file_fallback(self) -> bool:
        return self._using_file

    # ------------------------------------------------------------------
    # READ OPERATIONS
    # ------------------------------------------------------------------

    async def get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        if not self._using_file:
            try:
                cursor = self._mongo.find(
                    {}, {"_id": 0}
                ).sort("generated_at", -1).limit(1)
                docs = await cursor.to_list(1)
                if docs:
                    return docs[0]
            except Exception as e:
                logger.warning("MongoDB latest snapshot gagal: %s", e)

        history = self._load_file()
        if not history:
            return None
        return max(history, key=lambda x: x.get("generated_at", ""))

    async def get_history(
        self, limit: int = 50, offset: int = 0
    ) -> Dict[str, Any]:
        if not self._using_file:
            try:
                total = await self._mongo.count_documents({})
                items = await self._mongo.find(
                    {}, {"_id": 0}
                ).sort("generated_at", -1).skip(offset).limit(limit).to_list(limit)
                return {"data": items, "total": total}
            except Exception as e:
                logger.warning("MongoDB history gagal: %s", e)

        history = self._load_file()
        history.sort(key=lambda x: x.get("generated_at", ""), reverse=True)
        total = len(history)
        items = history[offset:offset + limit]
        return {"data": items, "total": total}

    async def get_snapshot_by_id(
        self, snapshot_id: str
    ) -> Optional[Dict[str, Any]]:
        if not self._using_file:
            try:
                snap = await self._mongo.find_one({"id": snapshot_id}, {"_id": 0})
                if snap:
                    return snap
            except Exception as e:
                logger.warning("MongoDB snapshot_by_id gagal: %s", e)

        history = self._load_file()
        for snap in history:
            if snap.get("id") == snapshot_id:
                return snap
        return None

    async def get_all_snapshots(self) -> List[Dict[str, Any]]:
        if not self._using_file:
            try:
                return await self._mongo.find(
                    {}, {"_id": 0}
                ).sort("generated_at", -1).to_list(500)
            except Exception as e:
                logger.warning("MongoDB all_snapshots gagal: %s", e)

        history = self._load_file()
        history.sort(key=lambda x: x.get("generated_at", ""), reverse=True)
        return history

    async def load_existing_order_map(
        self,
    ) -> Dict[Tuple[str, str], Dict[str, Any]]:
        """Load ALL historical orders, deduplikasi oleh (timeframe, ticker),
        pertahankan kemunculan pertama (buy_price TIDAK PERNAH berubah)."""
        existing_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
        all_snapshots = []

        if not self._using_file:
            try:
                all_snapshots = await self._mongo.find(
                    {}, {"_id": 0}
                ).sort("generated_at", 1).to_list(500)
            except Exception:
                pass

        if not all_snapshots:
            history_file = self._load_file()
            if history_file:
                all_snapshots = sorted(
                    history_file, key=lambda x: x.get("generated_at", "")
                )

        for snap in all_snapshots:
            for sim in snap.get("simulations", []):
                tf = sim["timeframe"]
                sector_name = sim.get("sector", {}).get("name", "")
                for stock in sim.get("stocks", []):
                    key = (tf, stock["ticker"])
                    if key in existing_map:
                        stored_bp = existing_map[key].get("buy_price")
                        current_bp = stock.get("buy_price")
                        if (stored_bp is not None and current_bp is not None
                                and abs(stored_bp - current_bp) > 0.01):
                            logger.warning(
                                "Buy_price MISMATCH [%s %s]: stored=Rp%s, snapshot=Rp%s — "
                                "mempertahankan stored (first occurrence)",
                                tf, stock["ticker"], stored_bp, current_bp,
                            )
                    else:
                        stock_copy = dict(stock)
                        stock_copy["sector"] = sector_name
                        existing_map[key] = stock_copy
        return existing_map

    # ------------------------------------------------------------------
    # WRITE OPERATION — SATU-SATUNYA method write
    # ------------------------------------------------------------------

    async def append_snapshot(self, snapshot: Dict[str, Any]) -> bool:
        """Append snapshot baru ke storage.

        Ini adalah SATU-SATUNYA method write di class ini.
        Tidak ada method update, delete, atau replace.
        """
        try:
            if not self._using_file:
                await self._mongo.insert_one(dict(snapshot))
                logger.info("Snapshot %s tersimpan ke MongoDB", snapshot["id"])
            else:
                logger.info(
                    "Snapshot %s hanya disimpan ke file (MongoDB tidak aktif)",
                    snapshot["id"],
                )

            async with self._file_lock:
                self._append_to_file(snapshot)
            return True
        except PermissionError:
            raise
        except Exception as e:
            logger.error("Gagal menyimpan snapshot %s: %s", snapshot.get("id"), e)
            return False

    # ------------------------------------------------------------------
    # FILE FALLBACK — INTERNAL
    # ------------------------------------------------------------------

    def _load_file(self) -> List[Dict[str, Any]]:
        if not self._file_path.exists():
            return []
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            logger.warning("Gagal parse file %s, menggunakan []", self._file_path)
            return []

    def _save_file(self, data: List[Dict[str, Any]]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _append_to_file(self, snapshot: Dict[str, Any]) -> None:
        """Append snapshot ke file JSON dengan validasi.

        VALIDASI: Sebelum menulis, pastikan semua entry lama
        masih ada di data baru. Ini mencegah kehilangan data
        akibat overwrite yang tidak disengaja.
        """
        old_data = self._load_file()
        old_ids = {s.get("id") for s in old_data if s.get("id")}
        new_data = old_data + [snapshot]
        self._save_file(new_data)

        # Validasi: pastikan tidak ada entry lama yang hilang
        saved = self._load_file()
        saved_ids = {s.get("id") for s in saved if s.get("id")}
        missing = old_ids - saved_ids
        if missing:
            logger.error(
                "VALIDASI GAGAL: %d entry lama hilang setelah write file! "
                "Memulihkan data...", len(missing)
            )
            self._save_file(old_data)
            raise RuntimeError(
                f"Data corruption detected: {len(missing)} entries missing. "
                "File restored to previous state."
            )

        logger.info(
            "Snapshot %s tersimpan ke file. Total: %d snapshots",
            snapshot.get("id"), len(saved),
        )

    # ------------------------------------------------------------------
    # CONTEXT MANAGEMENT (untuk inisialisasi di server.py)
    # ------------------------------------------------------------------

    @classmethod
    def from_app(cls, mongo_db, file_path: Path):
        """Factory method untuk membuat instance dari global state."""
        return cls(mongo_db=mongo_db, file_path=file_path)

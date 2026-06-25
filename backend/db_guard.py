import logging

logger = logging.getLogger(__name__)

_READ_OPS = {
    "find", "find_one", "count_documents", "aggregate",
    "distinct", "estimated_document_count",
    "list_indexes", "index_information", "options", "watch",
}

_WRITE_OPS = {"insert_one", "insert_many"}

_ALLOWED_OPS = _READ_OPS | _WRITE_OPS

_BLOCKED_MSG = (
    "Operasi '{}' tidak diizinkan pada collection append-only. "
    "Hanya operasi read (find, find_one, count_documents, aggregate) "
    "dan insert (insert_one, insert_many) yang diperbolehkan. "
    "Data yang sudah tersimpan tidak dapat diubah atau dihapus."
)


class AppendOnlyCollection:
    """Wrapper MongoDB collection yang hanya mengizinkan read & insert.

    Setiap operasi update, delete, replace, drop, atau bulk_write
    akan memunculkan PermissionError. Ini untuk memastikan data
    order book yang sudah tersimpan tidak bisa diubah atau dihapus
    oleh AI agent atau kode lain.
    """

    def __init__(self, collection):
        self._col = collection
        self._name = collection.name if hasattr(collection, "name") else str(collection)

    def __getattr__(self, name):
        if name not in _ALLOWED_OPS:
            logger.warning(
                "DIBLOKIR: Operasi '%s' pada collection '%s' dicegah "
                "(append-only guard)",
                name, self._name,
            )
            raise PermissionError(_BLOCKED_MSG.format(name))
        return getattr(self._col, name)

from typing import Dict, List

TV_TO_IDX_SECTOR: Dict[str, str] = {
    "Electronic Technology": "Teknologi",
    "Technology Services": "Teknologi",
    "Health Technology": "Kesehatan",
    "Health Services": "Kesehatan",
    "Communications": "Telekomunikasi",
    "Finance": "Keuangan",
    "Consumer Non-Durables": "Konsumer Non-Primer",
    "Consumer Durables": "Konsumer",
    "Energy Minerals": "Energi",
    "Non-Energy Minerals": "Bahan Baku",
    "Utilities": "Infrastruktur",
    "Transportation": "Transportasi & Logistik",
    "Retail Trade": "Konsumer",
    "Commercial Services": "Jasa & Perdagangan",
    "Producer Manufacturing": "Industri",
    "Process Industries": "Bahan Baku",
    "Distribution Services": "Distribusi",
    "Industrial Services": "Industri",
    "Consumer Services": "Konsumer Non-Primer",
    "Miscellaneous": "Lainnya",
}

IDX_SECTORS: List[str] = sorted(set(v for v in TV_TO_IDX_SECTOR.values()))

IDX_TO_TV_SECTORS: Dict[str, List[str]] = {}
for tv_name, idx_name in TV_TO_IDX_SECTOR.items():
    if idx_name not in IDX_TO_TV_SECTORS:
        IDX_TO_TV_SECTORS[idx_name] = []
    IDX_TO_TV_SECTORS[idx_name].append(tv_name)

SECTOR_ALIASES: Dict[str, str] = {
    "Perbankan": "Keuangan",
    "Banking": "Keuangan",
    "Consumer": "Konsumer",
    "Properti": "Lainnya",
    "Real Estate": "Lainnya",
    "Property": "Lainnya",
    "Pertambangan": "Bahan Baku",
    "Mining": "Bahan Baku",
    "Farmasi": "Kesehatan",
    "Pharmaceutical": "Kesehatan",
    "Asuransi": "Keuangan",
    "Insurance": "Keuangan",
    "Perkebunan": "Bahan Baku",
    "Plantation": "Bahan Baku",
}

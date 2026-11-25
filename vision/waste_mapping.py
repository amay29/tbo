"""
Konfigurasi tunggal pemetaan kelas dataset mentah -> kelas FST ('organic' / 'inorganic').
Ubah atau tambahkan entri di WASTE_CLASS_MAPPING sesuai nama kelas dataset Anda.
"""

from __future__ import annotations

# Pemetaan ke 2 kelas akhir sistem FST: "organic" dan "inorganic"
WASTE_CLASS_MAPPING: dict[str, str] = {
    # Dataset Kaggle "Waste Classification data" (techsash): O = Organic, R = Recyclable
    "o": "organic",
    "r": "inorganic",
    "organic": "organic",
    "recyclable": "inorganic",

    # Label Bahasa Indonesia / Inggris umum untuk sampah organik
    "organik": "organic",
    "sisa_makanan": "organic",
    "food_waste": "organic",
    "food": "organic",
    "buah": "organic",
    "fruit": "organic",
    "sayur": "organic",
    "vegetable": "organic",
    "daun": "organic",
    "leaf": "organic",
    "leaves": "organic",
    "kertas_basah": "organic",
    "wet_paper": "organic",
    "biodegradable": "organic",

    # Label Bahasa Indonesia / Inggris umum untuk sampah anorganik
    "inorganic": "inorganic",
    "anorganik": "inorganic",
    "plastik": "inorganic",
    "plastic": "inorganic",
    "plastic_bottle": "inorganic",
    "botol": "inorganic",
    "bottle": "inorganic",
    "kaleng": "inorganic",
    "can": "inorganic",
    "metal_can": "inorganic",
    "logam": "inorganic",
    "metal": "inorganic",
    "kaca": "inorganic",
    "glass": "inorganic",
    "kardus": "inorganic",
    "cardboard": "inorganic",
    "kertas_kering": "inorganic",
    "paper": "inorganic",
    "kemasan": "inorganic",
    "packaging": "inorganic",
    "trash": "inorganic",
    "non_biodegradable": "inorganic",
}

SERIAL_COMMAND_BY_CLASS: dict[str, str] = {
    "organic": "CLS:organic",
    "inorganic": "CLS:inorganic",
    "unknown": "CLS:unknown",
}


def normalize_label(raw_label: str) -> str:
    """Menormalisasi nama kelas menjadi huruf kecil dengan garis bawah."""
    return raw_label.strip().lower().replace("-", "_").replace(" ", "_")


def map_label_to_bin_class(raw_label: str) -> str:
    """
    Memetakan nama kelas mentah dari model atau dataset ke:
    'organic', 'inorganic', atau 'unknown' jika tidak dikenali.
    """
    norm = normalize_label(raw_label)
    if norm in WASTE_CLASS_MAPPING:
        return WASTE_CLASS_MAPPING[norm]
    return "unknown"


def to_serial_command(mapped_class: str) -> str:
    """Mengubah hasil pemetaan ('organic'/'inorganic'/'unknown') ke protokol serial ESP32."""
    return SERIAL_COMMAND_BY_CLASS.get(mapped_class, "CLS:unknown")

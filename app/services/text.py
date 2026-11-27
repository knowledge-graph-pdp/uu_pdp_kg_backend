import re

STOPWORDS = {
    "apa", "apakah", "yang", "dan", "atau", "di", "ke", "dari", "pada", "untuk", "dengan", "dalam",
    "itu", "ini", "oleh", "adalah", "ada", "akan", "bagaimana", "berapa", "siapa", "kapan", "mana",
    "saya", "kami", "kita", "anda", "jika", "bila", "apabila", "sertakan", "pasalnya", "ketentuan",
    "jelaskan", "isi", "mengatur", "uu", "pdp", "undang", "boleh", "harus", "wajib", "apa saja",
    "saja", "para", "tersebut", "sebuah", "suatu", "tentang", "terhadap", "secara", "agar", "bagi",
    "atas", "sudah", "telah", "lagi", "juga", "serta", "lama", "batas", "waktu", "kena", "terkena",
    "dinyatakan", "pihak", "ayat", "pasal", "huruf", "tanpa", "mau", "bisa", "dapat",
}

SYNONYMS = {
    "kebocoran": "kegagalan pelindungan",
    "bocor": "kegagalan pelindungan",
    "dpo": "pejabat pelindungan data pribadi",
    "data protection officer": "pejabat pelindungan data pribadi",
    "luar negeri": "transfer negara tujuan",
    "server": "transfer negara tujuan",
    "dibubarkan": "pembubaran",
    "pelanggan": "subjek data",
    "karyawan": "setiap orang",
    "menjual": "mengungkapkan melawan hukum",
    "tanpa izin": "melawan hukum",
    "ancaman pidana": "pidana penjara denda",
    "orang tua": "orang tua wali",
    "perusahaan": "pengendali",
    "konsekuensi": "sanksi",
    "dihapus": "menghapus",
    "dipenjara": "pidana penjara",
}

OUT_OF_SCOPE = re.compile(
    r"\b(gdpr|uu ite|pp\s*\d+|pph|ppn|iso\s*\d+|hak cipta|merek dagang|kontrak kerja|"
    r"perlindungan konsumen|tenaga kerja|putusan|yurisprudensi|ccpa|hipaa|"
    r"peraturan pemerintah|peraturan menteri|peraturan pelaksana)\b"
)

EXCEPTIONS = {
    "pemrosesan": "proses",
    "memproses": "proses",
    "diproses": "proses",
    "pemroses": "proses",
    "pemusnahan": "musnah",
    "memusnahkan": "musnah",
    "dimusnahkan": "musnah",
    "pemusnah": "musnah",
}

PREFIXES = ("meng", "meny", "peng", "peny", "mem", "men", "pem", "pen", "ber", "ter", "per", "me", "di", "ke", "pe", "se")
SUFFIXES = ("nya", "kan", "lah", "kah", "an", "i")


def stem(token: str) -> str:
    if any(ch.isdigit() for ch in token):
        return token
    if token in EXCEPTIONS:
        return EXCEPTIONS[token]
    word = token
    for prefix in PREFIXES:
        if word.startswith(prefix) and len(word) - len(prefix) >= 4:
            word = word[len(prefix):]
            break
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            word = word[: -len(suffix)]
            break
    return word


def expand(text: str) -> str:
    lowered = text.lower()
    for phrase, replacement in SYNONYMS.items():
        if re.search(rf"\b{re.escape(phrase)}\b", lowered):
            lowered = f"{lowered} {replacement}"
    return lowered


def tokenize(text: str) -> list[str]:
    raw = re.findall(r"[a-z0-9]+", expand(text))
    return [stem(t) for t in raw if t not in STOPWORDS and len(t) > 1]


def tokenize_raw(text: str) -> list[str]:
    raw = re.findall(r"[a-z0-9]+", text.lower())
    return [stem(t) for t in raw if t not in STOPWORDS and len(t) > 1]


def synonym_vocab() -> set[str]:
    words: set[str] = set()
    for phrase in SYNONYMS:
        words.update(tokenize_raw(phrase))
    return words

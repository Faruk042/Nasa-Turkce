# -*- coding: utf-8 -*-
"""
ALTAR-NASA Akıllı Konu Kapsamı Kontrolü, Fiziksel Kavram Düzeltmesi ve Eylem Önerici (scope_guard.py).
- Yalnızca standart kütüphane kullanır (< 1 ms çalışma süresi).
- Karma cümle ayıklama, karakter üçlüleri (char 3-gram) + harf yer değiştirme toleransı içerir.
- Geçmiş zehirlenmesine karşı korumalı takip sorusu desteği sağlar.
- Arayüzde ve yanıtlarda sade, kısa, doğal mühendislik dili kullanır.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

_TR_ASCII_TABLE = str.maketrans(
    {
        "ı": "i",
        "İ": "i",
        "ğ": "g",
        "Ğ": "g",
        "ü": "u",
        "Ü": "u",
        "ş": "s",
        "Ş": "s",
        "ö": "o",
        "Ö": "o",
        "ç": "c",
        "Ç": "c",
        "â": "a",
        "Â": "a",
        "î": "i",
        "Î": "i",
        "û": "u",
        "Û": "u",
        "₂": "2",
        "²": "2",
        "₀": "0",
        "₁": "1",
        "₃": "3",
        "µ": "u",
    }
)

# Yazım hatası toleransı için çekirdek terim sözlüğü (yazım hatalı kelime -> standart terim)
_CANONICAL_DOMAIN_VOCAB: Tuple[Tuple[str, str], ...] = (
    ("saffire", "saffire"),
    ("sofie", "sofie"),
    ("spalding", "spalding"),
    ("sherwood", "sherwood"),
    ("reynolds", "reynolds"),
    ("grashof", "grashof"),
    ("rayleigh", "rayleigh"),
    ("richardson", "richardson"),
    ("damkohler", "damkohler"),
    ("schumann", "schumann"),
    ("semenov", "semenov"),
    ("kamenetskii", "kamenetskii"),
    ("mikrocekim", "mikrocekim"),
    ("microgravity", "microgravity"),
    ("yercekimi", "yercekimi"),
    ("oksijen", "oksijen"),
    ("oxygen", "oxygen"),
    ("metanol", "metanol"),
    ("methanol", "methanol"),
    ("heptan", "heptan"),
    ("heptane", "heptane"),
    ("etanol", "etanol"),
    ("ethanol", "ethanol"),
    ("hidrojen", "hidrojen"),
    ("hydrogen", "hydrogen"),
    ("propan", "propan"),
    ("propane", "propane"),
    ("toluen", "toluen"),
    ("nomex", "nomex"),
    ("sibal", "sibal"),
    ("kapton", "kapton"),
    ("teflon", "teflon"),
    ("halon", "halon"),
    ("yangin", "yangin"),
    ("tutusma", "tutusma"),
    ("yanma", "yanma"),
    ("combustion", "combustion"),
    ("flammability", "flammability"),
    ("sondurme", "sondurme"),
    ("sondurucu", "sondurucu"),
    ("havalandirma", "havalandirma"),
    ("ventilation", "ventilation"),
    ("karbonmonoksit", "karbonmonoksit"),
    ("radyometre", "radyometre"),
    ("termokupl", "termokupl"),
    ("thermocouple", "thermocouple"),
    ("dedektor", "dedektor"),
    ("detector", "detector"),
    ("piroliz", "piroliz"),
    ("pyrolysis", "pyrolysis"),
    ("konveksiyon", "konveksiyon"),
    ("convection", "convection"),
    ("difuzyon", "difuzyon"),
    ("diffusion", "diffusion"),
    ("radyatif", "radyatif"),
    ("radiative", "radiative"),
    ("spacesuit", "spacesuit"),
    ("orion", "orion"),
    ("gateway", "gateway"),
    ("cygnus", "cygnus"),
    ("artemis", "artemis"),
    ("camras", "camras"),
    ("eclss", "eclss"),
)

# Doğrudan kapsam içi anahtar ifadeler (normalize edilmiş ASCII üzerinde aranır)
_DIRECT_DOMAIN_PHRASES: Tuple[str, ...] = (
    "yanma",
    "alev",
    "yangin",
    "tutusma",
    "tutustur",
    "sondur",
    "su sisi",
    "water mist",
    "soguk alev",
    "cool flame",
    "kuresel alev",
    "kuresel yanma",
    "mum alevi",
    "sifir yercekimi",
    "zero gravity",
    "zero-g",
    "vakumda alev",
    "vakumda ates",
    "vakumda yanma",
    "uzay boslugunda alev",
    "uzay boslugunda ates",
    "uzay boslugunda yanar",
    "uzay araci",
    "spacecraft",
    "mikrocekim",
    "mikro yercekimi",
    "microgravity",
    "freefall",
    "kismi yercekimi",
    "partial gravity",
    "0g",
    "0.0g",
    "0.16g",
    "0.38g",
    "1g",
    "oksijen",
    "oxygen",
    "basinc",
    "pressure",
    "psia",
    "kpa",
    "cm/s",
    "mm2/s",
    "kw/m2",
    "karbonmonoksit",
    "carbon monoxide",
    "co ppm",
    "smac",
    "eclss",
    "camras",
    "fdir",
    "spalding",
    "b_oq",
    "boq",
    "sherwood",
    "reynolds",
    "grashof",
    "rayleigh",
    "richardson",
    "damkohler",
    "d2 yasasi",
    "d2-law",
    "de ris",
    "burke-schumann",
    "burke schumann",
    "chi_r",
    "radyatif",
    "radiative",
    "konveksiyon",
    "convection",
    "difuzyon",
    "diffusion",
    "piroliz",
    "pyrolysis",
    "kurum",
    "soot",
    "standoff",
    "rf/rd",
    "r_f",
    "hrrpua",
    "semenov",
    "kamenetskii",
    "heptan",
    "heptane",
    "metanol",
    "methanol",
    "etanol",
    "ethanol",
    "propan",
    "propane",
    "hidrojen",
    "hydrogen",
    "toluen",
    "toluene",
    "pmma",
    "nomex",
    "sibal",
    "kapton",
    "teflon",
    "ptfe",
    "peek",
    "xlpe",
    "halon",
    "saffire",
    "sofie",
    "flex-2",
    "bass-ii",
    "spice",
    "slice",
    "daft",
    "cfi-g",
    "cfig",
    "luci",
    "fm2",
    "ntrs",
    "osdr",
    "nasa psi",
    "psi-",
    "6001b",
    "20584",
    "uzay giysisi",
    "eva giysi",
    "eva suit",
    "spacesuit",
    "ay gezgini",
    "lunar rover",
    "pressurized rover",
    "ay ussu",
    "mars kabini",
    "orion",
    "gateway",
    "cygnus",
    "uzay istasyonu",
    "space station",
    "kabin",
    "cabin",
    "kapak",
    "hatch",
    "menfez",
    "hava kanali",
    "fan hizi",
    "akis hizi",
    "airflow",
    "termal kamera",
    "thermal camera",
    "optik kamera",
    "duman",
    "smoke",
    "regolit",
    "lunar dust",
    "ay tozu",
    "yeniden tutusma",
    "re-ignition",
    "reignition",
    "belirsizlik",
    "ozel denklem",
    "custom equation",
    "ozel malzeme",
    "custom material",
    "itfaiye",
    "firefighter",
    "scba",
)

_RE_DOMAIN_SHORT_TOKENS = re.compile(
    r"\b(?:flex|bass|acme|same|cfi|moc|iss|eva|mie|fed|ntc|psd|cir|msg|mdca|halo|ihab|ppe|o2|co2|n2|r2|rmse)\b"
)

_RE_NATURAL_COMBUSTION_TOKENS = re.compile(
    r"\b(?:ates|atesin|ateste|atesle|yanar|yaniyor|yanmak|yanmaz|yanici|yakici|"
    r"tutusur|tutustu|soner|sondu|sondurme|sondurucu|mum|mumun|mumda|mumlar|"
    r"agirliksiz|agirliksizlik|vakumda|flame|flames|fire|fires|burn|burns|burning|"
    r"burned|candle|candles|ignite|ignites|ignited|ignition|extinguish|extinguisher|"
    r"extinguishing|quench|quenches|quenching|smolder|smoldering|buoyancy|convective|"
    r"weightless|weightlessness)\b"
)

_RE_STRONG_SPACE_ANCHORS = re.compile(
    r"(?:^|\b)(?:0g|0\.0g|0\.16g|0\.38g|mikrocekim|microgravity|freefall|saffire|sofie|"
    r"flex|bass|moc|spalding|sherwood|damkohler|orion|iss|nasa|kabin|cabin)(?:\b|$)"
)

_STRONG_SPACE_ANCHOR_PHRASES: Tuple[str, ...] = (
    "mikro yercekimi",
    "uzay araci",
    "spacecraft",
    "su sisi",
    "water mist",
)

_SHORT_GREETINGS: Tuple[str, ...] = (
    "merhaba",
    "selam",
    "gunaydin",
    "iyi gunler",
    "iyi aksamlar",
    "hello",
    "hi",
    "hey",
)

_RE_CASUAL_GREETING_TOKENS = re.compile(r"\b(?:hello|hi|hey)\b")

# Uygulama tanıtım / yetenek soruları (kapsam içi kabul edilir)
_PLATFORM_INTRO_PHRASES: Tuple[str, ...] = (
    "neler yapabilir",
    "ne yapabilir",
    "ne ise yarar",
    "nasil kullan",
    "ozelliklerin",
    "ozellikleri",
    "hangi ozellik",
    "yeteneklerin",
    "modullerin",
    "bu uygulama",
    "bu ekran",
    "bu platform",
    "altar-nasa",
    "flame in freefall",
    "sen kimsin",
    "kendini tanit",
    "what can you do",
    "how to use",
    "platform features",
    "capabilities",
    "who are you",
    "what is this app",
)

# Açıkça konu dışı kelimeler (takip sorusu iznini de keser)
_EXPLICIT_OFF_TOPIC_PHRASES: Tuple[str, ...] = (
    "corba",
    "corbasi",
    "mercimek",
    "tarif",
    "tarifi",
    "pilav",
    "makarna",
    "kek ",
    "kurabiye",
    "borek",
    "kebap",
    "tatli tarif",
    "yemek yap",
    "pisir",
    "recipe",
    "soup",
    "pasta recipe",
    "bake a cake",
    "mac kac",
    "mac skoru",
    "mac sonucu",
    "futbol",
    "ofsayt",
    "penalti",
    "sampiyonlar ligi",
    "super lig",
    "fenerbahce",
    "galatasaray",
    "besiktas",
    "trabzonspor",
    "basketbol",
    "match score",
    "football",
    "soccer",
    "world cup",
    "dolar kac",
    "euro kac",
    "altin fiyati",
    "borsa",
    "hisse senedi",
    "kripto",
    "bitcoin",
    "ethereum",
    "stock price",
    "crypto",
    "burc yorumu",
    "astroloji",
    "horoscope",
    "magazin",
    "dedikodu",
    "gossip",
    "film oner",
    "dizi oner",
    "sarki sozu",
    "siir yaz",
    "masal anlat",
    "fikra anlat",
    "movie recommendation",
    "write a poem",
    "tell a joke",
    "yilan oyunu",
    "tetris",
    "oyun yaz",
    "oyun kodu",
    "web sitesi yap",
    "alisveris sitesi",
    "snake game",
    "flappy bird",
    "write a game",
    "evlilik",
    "sevgili",
    "siyaset",
    "secim sonucu",
    "hava durumu",
    "weather forecast",
    "ates dusurucu",
    "atesim var",
    "atesi var",
    "atesi cikti",
    "yuksek ates",
    "ates olcer",
    "ateskes",
    "ates ac",
    "silah ates",
    "ilac oner",
    "mide yanma",
    "icim yaniyor",
    "canim yaniyor",
    "bilet yanar",
    "biletim yanar",
    "garanti yanar",
    "kalori yak",
    "kisik ateste",
    "orta ateste",
    "yuksek ateste",
    "tencerede",
    "firinda kek",
    "burn calories",
    "calorie",
    "heartburn",
    "sunburn",
    "burnout",
    "free fire",
    "fire someone",
    "got fired",
    "high fever",
    "fever medicine",
)

# Karma cümlede elenecek günlük/hava durumu yan cümlecikleri
_CASUAL_CLAUSE_PHRASES: Tuple[str, ...] = (
    "bugun hava",
    "hava durumu",
    "disarida hava",
    "hava cok guzel",
    "hava guzel",
    "hava yagmurlu",
    "hava soguk",
    "hava sicak",
    "hava bulutlu",
    "gunaydin",
    "iyi gunler",
    "iyi aksamlar",
    "iyi geceler",
    "merhaba",
    "selam",
    "nasilsin",
    "keyifler nasil",
    "umarim iyisindir",
    "kolay gelsin",
    "weather forecast",
    "weather is nice",
    "weather is rainy",
    "it is raining today",
    "good morning",
    "good evening",
    "how are you",
    "hope you are well",
)

# Takip sorusu kalıpları (yalnızca bir önceki geçerli kapsam içi sorudan sonra izin verilir)
_FOLLOWUP_PATTERNS: Tuple[str, ...] = (
    "bunu ",
    "bunun ",
    "sunu ",
    "bu sonucu",
    "bu degeri",
    "bu tabloyu",
    "yukaridaki",
    "az onceki",
    "ozetle",
    "kisaca",
    "daha kisa",
    "daha sade",
    "basit anlat",
    "sadelestir",
    "detaylandir",
    "acikla",
    "tabloya dok",
    "tablo yap",
    "tablo halinde",
    "tabloda goster",
    "maddeler halinde",
    "1. satir",
    "2. satir",
    "3. satir",
    "ilk satir",
    "ikinci satir",
    "son satir",
    "ingilizceye cevir",
    "turkceye cevir",
    "ingilizce yaz",
    "turkce yaz",
    "cevir",
    "degeri artirirsam",
    "degeri azaltirsam",
    "artirirsam ne olur",
    "azaltirsam ne olur",
    "iki katina",
    "yariya indirirsem",
    "peki neden",
    "neden oyle",
    "nasil hesapladin",
    "karsilastir",
    "summarize",
    "make it shorter",
    "simpler",
    "in a table",
    "put in a table",
    "as a table",
    "explain row",
    "second row",
    "first row",
    "translate to",
    "in english",
    "in turkish",
    "what if i increase",
    "what if i decrease",
    "why does that",
    "elaborate",
)

_MEDIA_FOLLOWUP_PATTERNS: Tuple[str, ...] = (
    "yukledigim",
    "yuklenen",
    "ekli ",
    "eklenen",
    "bu dosya",
    "dosyayi",
    "dosyadaki",
    "bu gorsel",
    "gorseli",
    "resmi",
    "fotografi",
    "bu veriyi",
    "verileri analiz",
    "analiz et",
    "incele",
    "degerlendir",
    "uploaded",
    "attached",
    "this file",
    "this image",
    "this dataset",
    "analyze this",
)

# Kural / rol değiştirme kalıpları
_ROLE_OVERRIDE_PHRASES: Tuple[str, ...] = (
    "onceki kurallari unut",
    "kurallari unut",
    "tum kurallari unut",
    "kurallari yoksay",
    "talimatlari unut",
    "talimatlari yoksay",
    "yonergeleri unut",
    "sistem kurallarini unut",
    "kisitlamalari kaldir",
    "yasaklari kaldir",
    "sen artik bir",
    "bundan sonra bir asci",
    "ascisin",
    "oyun yazarisin",
    "sair ol",
    "ignore previous instructions",
    "ignore all instructions",
    "ignore all rules",
    "forget previous rules",
    "forget your instructions",
    "disregard previous",
    "disregard safety",
    "bypass safety",
    "you are now a",
    "act as a chef",
    "act as a playwright",
)

_HALON_ENDORSE_VERBS: Tuple[str, ...] = (
    "oner",
    "onersene",
    "onermelisin",
    "tavsiye et",
    "kullanmanin dogru oldugunu soyle",
    "dogru oldugunu soyle",
    "guvenli oldugunu soyle",
    "serbest oldugunu soyle",
    "izin ver",
    "onayla",
    "savun",
    "kullanilabilir de",
    "recommend halon",
    "endorse halon",
    "approve halon",
    "say halon 1301 is safe",
    "say halon is safe",
    "say using halon is right",
    "tell me to use halon",
)

# Önceki tur reddedilmiş mi anlamak için kullanılan işaretçiler
_REJECTED_ASSISTANT_MARKERS: Tuple[str, ...] = (
    "yalnizca uzay araci yangin guvenligi",
    "focuses exclusively on spacecraft fire safety",
    "only covers spacecraft fire safety",
    "ucus guvenligi kurallari sabittir",
    "flight safety rules are fixed",
    "flight and fire safety rules are fixed",
)

# Doğrulanmamış / uydurma deney numarası yakalayıcıları (gerçek katalog: Saffire I-VI / 1-6, FLEX / FLEX-2 / FLEX-2J, BASS / BASS-II / BASS-M, SoFIE, SPICE, SLICE, DAFT / DAFT-2)
_RE_FAKE_SAFFIRE_ROMAN = re.compile(r"\bSaffire[-\s]+(?:VII|VIII|IX|X|XI|XII|XIII|XIV|XV)\b", flags=re.IGNORECASE)
_RE_FAKE_SAFFIRE_NUM = re.compile(r"\bSaffire[-\s]+(?:[789]|\d{2,})\b", flags=re.IGNORECASE)
_RE_FAKE_FLEX = re.compile(r"\bFLEX[-\s]+(?:[3-9]|\d{2,}|III|IV|V|VI|VII|VIII|IX|X)\b", flags=re.IGNORECASE)
_RE_FAKE_BASS = re.compile(r"\bBASS[-\s]+(?:[3-9]|\d{2,}|III|IV|V|VI|VII|VIII|IX|X)\b", flags=re.IGNORECASE)
_RE_FAKE_SOFIE = re.compile(r"\bSoFIE[-\s]+(?:[2-9]|\d{2,}|II|III|IV|V|VI|VII|VIII|IX|X)\b", flags=re.IGNORECASE)
_RE_FAKE_SPICE_SLICE = re.compile(r"\b(SPICE|SLICE|ACME)[-\s]+(?:[2-9]|\d{2,}|II|III|IV|V|VI|VII|VIII|IX|X)\b", flags=re.IGNORECASE)


def normalize_scope_text(raw: str) -> str:
    txt = str(raw or "").translate(_TR_ASCII_TABLE).lower()
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def _char_trigrams(word: str) -> Set[str]:
    padded = f"^{word}$"
    if len(padded) < 3:
        return {padded}
    return {padded[i : i + 3] for i in range(len(padded) - 2)}


def _trigram_dice(a: str, b: str) -> float:
    ga = _char_trigrams(a)
    gb = _char_trigrams(b)
    if not ga or not gb:
        return 0.0
    return (2.0 * len(ga & gb)) / float(len(ga) + len(gb))


def _damerau_levenshtein(a: str, b: str) -> int:
    la, lb = len(a), len(b)
    if a == b:
        return 0
    if la == 0:
        return lb
    if lb == 0:
        return la
    d = [[0] * (lb + 1) for _ in range(la + 1)]
    for i in range(la + 1):
        d[i][0] = i
    for j in range(lb + 1):
        d[0][j] = j
    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            val = min(
                d[i - 1][j] + 1,
                d[i][j - 1] + 1,
                d[i - 1][j - 1] + cost,
            )
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                val = min(val, d[i - 2][j - 2] + 1)
            d[i][j] = val
    return d[la][lb]


_PRECOMPUTED_VOCAB = tuple((term, canon, _char_trigrams(term)) for term, canon in _CANONICAL_DOMAIN_VOCAB)
_EXACT_VOCAB_MAP = {term: canon for term, canon in _CANONICAL_DOMAIN_VOCAB}


def _match_fuzzy_domain_tokens(norm_text: str) -> Tuple[List[Tuple[str, str]], str]:
    """
    Hızlı karakter üçlüsü (char 3-gram) + Damerau-Levenshtein benzerliği ile
    'sfafire', 'spaldng', 'mikrocekm', 'haln', 'metnol', 'nomks', 'okijen' gibi yazım hatalarını tanır.
    """
    tokens = re.findall(r"[a-z0-9_]+", norm_text)
    matched: List[Tuple[str, str]] = []
    repaired_words: Dict[str, str] = {}

    for tok in tokens:
        if len(tok) < 4 or tok.isdigit():
            continue
        if tok in _EXACT_VOCAB_MAP:
            matched.append((tok, _EXACT_VOCAB_MAP[tok]))
            continue

        # Türkçe fonetik 'ks' -> 'x' uyumu (ör. 'nomks' -> 'nomx' ~ 'nomex')
        phonetic_tok = tok.replace("ks", "x")
        tok_grams = _char_trigrams(tok)
        best_canon = ""
        best_score = 0.0

        for term, canon, term_grams in _PRECOMPUTED_VOCAB:
            if abs(len(tok) - len(term)) > 2 and abs(len(phonetic_tok) - len(term)) > 2:
                continue
            shared_grams = len(tok_grams & term_grams)
            if shared_grams == 0 and phonetic_tok == tok:
                continue
            dice_raw = (2.0 * shared_grams) / float(len(tok_grams) + len(term_grams))
            max_len = float(max(len(tok), len(term)))
            if max_len <= 5 and tok[0] != term[0]:
                continue
            if dice_raw < 0.22 and tok[0] != term[0] and phonetic_tok == tok:
                continue
            dist = _damerau_levenshtein(tok, term)
            if phonetic_tok != tok and dist > 1:
                dist = min(dist, _damerau_levenshtein(phonetic_tok, term))
            edit_sim = 1.0 - (dist / max_len)
            combined = 0.45 * dice_raw + 0.55 * edit_sim

            # Kısa kelimelerde (4-5 harf) en fazla 1 harf hatası ve ilk harf uyumu ara
            if max_len <= 5:
                is_hit = dist <= 1 and tok[0] == term[0]
            else:
                is_hit = (dist <= 1 and edit_sim >= 0.78) or (dist <= 2 and dice_raw >= 0.42 and combined >= 0.64 and tok[0] == term[0])

            if is_hit and combined > best_score:
                best_score = combined
                best_canon = canon

        if best_canon:
            matched.append((tok, best_canon))
            repaired_words[tok] = best_canon

    if not repaired_words:
        return matched, norm_text

    repaired_norm = norm_text
    for wrong_w, right_w in repaired_words.items():
        repaired_norm = re.sub(rf"\b{re.escape(wrong_w)}\b", right_w, repaired_norm)
    return matched, repaired_norm


def _has_any(text: str, phrases: Sequence[str]) -> bool:
    return any(p in text for p in phrases)


def _has_strong_space_anchor(norm_text: str) -> bool:
    if _RE_STRONG_SPACE_ANCHORS.search(norm_text):
        return True
    return _has_any(norm_text, _STRONG_SPACE_ANCHOR_PHRASES)


def _clause_has_domain_signal(clause_norm: str) -> bool:
    if _has_any(clause_norm, _EXPLICIT_OFF_TOPIC_PHRASES) and not _has_strong_space_anchor(clause_norm):
        return False
    if _has_any(clause_norm, _DIRECT_DOMAIN_PHRASES):
        return True
    if _RE_DOMAIN_SHORT_TOKENS.search(clause_norm):
        return True
    if _RE_NATURAL_COMBUSTION_TOKENS.search(clause_norm):
        return True
    fuzzy_hits, _ = _match_fuzzy_domain_tokens(clause_norm)
    return len(fuzzy_hits) > 0


def _strip_casual_clauses(raw_message: str) -> Tuple[str, bool]:
    """
    Karma cümlelerde ('Bugün hava yağmurlu, bu arada 0G'de metanol neden soğuk aleve geçer?')
    günlük sohbet yan cümlesini sessizce ayıklayıp yalnızca bilimsel soruyu bırakır.
    """
    parts = re.split(
        r"(?:[.!?;]+|,\s*(?=(?:bu arada|peki|ayrica|fakat|ama|ancak|neyse|by the way|anyway|also|however|so\b))|\b(?:bu arada|by the way|anyway)\b|,)",
        raw_message,
        flags=re.IGNORECASE,
    )
    if len(parts) <= 1:
        return raw_message.strip(), False

    kept_parts: List[str] = []
    dropped_any = False
    for raw_p in parts:
        p_clean = raw_p.strip(" ,;:-")
        if not p_clean:
            continue
        p_norm = normalize_scope_text(p_clean)
        has_dom = _clause_has_domain_signal(p_norm)
        is_casual = _has_any(p_norm, _CASUAL_CLAUSE_PHRASES) or bool(_RE_CASUAL_GREETING_TOKENS.search(p_norm))
        if is_casual and not has_dom:
            dropped_any = True
            continue
        kept_parts.append(p_clean)

    if dropped_any and kept_parts:
        joined = ", ".join(kept_parts).strip()
        joined = re.sub(r"^(?:peki|bu arada|ayrica|ama|fakat|ancak|so|and|but)\s+", "", joined, flags=re.IGNORECASE).strip()
        if _clause_has_domain_signal(normalize_scope_text(joined)):
            return joined, True
    return raw_message.strip(), False


def detect_physical_misconception(norm_text: str) -> Optional[Dict[str, str]]:
    """
    Kapsam içi sorularda sık yapılan 4 temel fiziksel yanılgıyı yakalar ve tek cümlelik doğal düzeltme üretir.
    """
    # 1) 0G / mikroçekim / uzay istasyonunda tavanda biriken duman veya yukarı çıkan sıcak hava
    has_zero_g_ctx = _has_any(
        norm_text,
        (
            "0g",
            "0.0g",
            "sifir yercekimi",
            "zero gravity",
            "zero-g",
            "agirliksiz",
            "weightless",
            "mikrocekim",
            "mikro yercekimi",
            "microgravity",
            "freefall",
            "uzay istasyonu",
            "space station",
            "iss",
        ),
    )
    has_ceiling_rise = _has_any(
        norm_text,
        (
            "tavanda biriken",
            "tavana yukselen",
            "tavana cikan",
            "tavana cikar",
            "tavandaki duman",
            "tavanda duman",
            "tavana duman",
            "tavana duman dedektor",
            "duman yukselir",
            "sicak hava yukselir",
            "yukari cikan duman",
            "yukari cikan sicak",
            "yukselen duman",
            "yukselen sicak hava",
            "ceiling smoke",
            "ceiling smoke detector",
            "ceiling smoke detectors",
            "smoke on the ceiling",
            "smoke rising",
            "rising hot air",
            "rise to the ceiling",
            "rises to the ceiling",
            "collects on the ceiling",
            "accumulates at the ceiling",
        ),
    ) or bool(
        re.search(
            r"\b(?:smoke|hot\s+air|heat|fumes)\b.{0,28}\b(?:rise|rises|rising|collect|collects|accumulate|accumulates)\b",
            norm_text,
        )
    )
    if has_zero_g_ctx and has_ceiling_rise:
        return {
            "code": "zero_g_ceiling_smoke",
            "correction_tr": (
                "0G mikroçekim ortamında kaldırma kuvveti oluşmadığı için duman ve sıcak gaz tavanda birikmez; "
                "kabin havalandırma akışını izleyerek emiş menfezlerine doğru sürüklenir, bu nedenle sensörler "
                "tavan yerine havalandırma dönüş kanallarına yerleştirilir."
            ),
            "correction_en": (
                "In 0G microgravity, buoyancy vanishes so smoke and hot gas do not rise or collect at the ceiling; "
                "they drift with cabin airflow toward return ducts, which is where smoke sensors are mounted."
            ),
        }

    # 2) %0 oksijende veya vakumda normal gaz fazı alevi / mum yanması
    has_zero_o2 = bool(
        re.search(r"(?:%\s*0\s*(?:o2|oksijen)|0\s*%\s*(?:o2|oxygen)|sifir\s+oksijen|zero\s+oxygen|oksijensiz\s+ortamda\s+alev)", norm_text)
        or (
            (
                _has_any(
                    norm_text,
                    (
                        "vakumda alev",
                        "vakumda yanma",
                        "vakumda ates",
                        "vakumda mum",
                        "vakumda yanar",
                        "uzay boslugunda alev",
                        "uzay boslugunda ates",
                        "uzay boslugunda mum",
                        "uzay boslugunda yanar",
                        "flame in vacuum",
                        "burn in vacuum",
                        "fire in vacuum",
                        "candle in vacuum",
                    ),
                )
                or bool(re.search(r"\b(?:flame|fire|candle)\b.{0,32}\b(?:in\s+(?:space\s+)?vacuum|zero\s+oxygen|0\s*%\s*oxygen)", norm_text))
            )
            and not _has_any(norm_text, ("roket", "rocket", "itici", "thruster", "oksitleyici", "oxidizer"))
        )
    )
    if has_zero_o2 and not _has_any(norm_text, ("soner", "sonumlenir", "yanmaz", "quench", "cannot burn")):
        return {
            "code": "vacuum_or_zero_o2_flame",
            "correction_tr": (
                "Oksijen oranı kritik tutuşma sınırının (`O₂ < MOC`) altına indiğinde veya dış oksitleyici olmayan "
                "vakum ortamında gaz fazı alevi kararlı biçimde yanamaz ve sönümlenir."
            ),
            "correction_en": (
                "Below the minimum oxygen concentration (`O₂ < MOC`) or in vacuum without a supplied oxidizer, "
                "a gas-phase flame cannot sustain combustion and quenches."
            ),
        }

    # 3) Sıcak yüzey / çekirdek soğumadan kapağı hemen açıp havalandırmak
    has_hot_premature_open = _has_any(
        norm_text, ("kapagi", "kapak", "hatch", "havalandir", "ventilat", "odayi ac", "bolmeyi ac", "unseal")
    ) and (
        _has_any(
            norm_text,
            (
                "sogumadan",
                "hemen ac",
                "aninda ac",
                "soner sonmez ac",
                "sicakken ac",
                "before cooling",
                "while still hot",
                "open immediately",
                "right after extinguishing",
            ),
        )
        or bool(re.search(r"\b(?:open|unseal)\b.{0,25}\b(?:immediately|right\s+away|instantly|before\s+cooling)\b", norm_text))
        or bool(re.search(r"\b(?:immediately|right\s+away|instantly)\b.{0,20}\b(?:open|unseal|ventilate)\b", norm_text))
        or bool(re.search(r"\b(?:hemen|aninda|beklemeden|sogumadan)\b.{0,20}\b(?:ac|acalim|acilir|acmak|havalandir)", norm_text))
    )
    if has_hot_premature_open:
        return {
            "code": "premature_hatch_reignition",
            "correction_tr": (
                "Alev söndükten hemen sonra sıcak çekirdek (`≥ 525 K`) soğumadan bölme kapağını açıp taze oksijen "
                "vermek ani yeniden tutuşmaya yol açar; kapak yalnızca çekirdek soğuduktan ve hava temizlendikten sonra açılmalıdır."
            ),
            "correction_en": (
                "Opening the compartment hatch to admit fresh oxygen before the hot core cools below `525 K` "
                "triggers flash re-ignition; keep the bay sealed until cooling and air scrubbing finish."
            ),
        }

    # 4) 0G / kabin yangınında kova, bardak veya doğrudan kaba sıvı su dökmek
    has_space_cabin_ctx = _has_any(
        norm_text,
        (
            "0g",
            "0.0g",
            "sifir yercekimi",
            "zero gravity",
            "zero-g",
            "agirliksiz",
            "weightless",
            "mikrocekim",
            "mikro yercekimi",
            "microgravity",
            "freefall",
            "uzay araci",
            "uzay istasyonu",
            "uzayda",
            "in space",
            "spacecraft",
            "space station",
            "iss",
            "orion",
            "kabin",
            "cabin",
        ),
    )
    has_bulk_water = (
        _has_any(
            norm_text,
            (
                "su dok",
                "kova ile su",
                "kovayla su",
                "bardakla su",
                "su firlat",
                "pour water",
                "pouring water",
                "bucket of water",
                "splash water",
                "throw water",
            ),
        )
        or bool(re.search(r"\b(?:pour|pouring|splash|splashing|throw|throwing|dump|dumping)\b.{0,22}\bwater\b", norm_text))
        or bool(re.search(r"\b(?:kova|kovayla|bardak|bardakla)\b.{0,20}\bsu\b", norm_text))
    )
    if (
        has_space_cabin_ctx
        and has_bulk_water
        and not _has_any(norm_text, ("yag", "tava", "mutfak", "oil", "grease", "kitchen"))
        and not _has_any(norm_text, ("su sisi", "water mist", "sofie-mist"))
    ):
        return {
            "code": "zero_g_bulk_water",
            "correction_tr": (
                "0G mikroçekim ortamında dökülen kaba sıvı su yüzey gerilimiyle serbest küreler halinde dağılıp "
                "alev cephesine tutunamaz ve elektronik hatlarda kısa devre riski yaratır; bu nedenle kabin "
                "yangınlarında 25–40 µm ince su sisi (`SoFIE-MIST`) kullanılır."
            ),
            "correction_en": (
                "In 0G microgravity, poured bulk water forms floating spheres under surface tension that miss the "
                "flame sheet and risk shorting cabin electronics, so crews deploy 25–40 µm fine water mist (`SoFIE-MIST`) instead."
            ),
        }

    return None


def _detect_boundary_category(norm_text: str) -> Optional[str]:
    """
    Sınır soruları:
    - 'rocket_engine': Yüksek hızlı roket motoru / itici yanması (CON-08)
    - 'space_equipment': Uzay istasyonunda yemek ısıtıcısı, uyku tulumu, güneş paneli vb. günlük ekipmanlar
    - 'terrestrial_fire': Evde yağ/mutfak yangınına su dökülmesi, ev tipi duman dedektörü, bina yangını
    """
    if _has_any(
        norm_text,
        (
            "roket motor",
            "roket itici",
            "roket yanma",
            "roket nozul",
            "sivi yakitli roket",
            "kati yakitli roket",
            "rocket engine",
            "rocket motor",
            "rocket thruster",
            "rocket combustion",
            "thruster plume",
            "propellant engine",
        ),
    ) or (
        _has_any(norm_text, ("roket", "rocket", "thruster", "itici"))
        and _has_any(norm_text, ("yanma", "alev", "yakit", "motor", "combustion", "flame", "nozzle"))
    ):
        return "rocket_engine"

    if _has_any(
        norm_text,
        (
            "yemek isiticisi",
            "yemek isitici",
            "uyku tulumu",
            "gunes paneli",
            "gunes panelleri",
            "mikrodalga",
            "kahve makinesi",
            "astronot yemegi",
            "food warmer",
            "galley oven",
            "sleeping bag",
            "solar panel",
            "solar array",
            "crew laptop",
        ),
    ):
        return "space_equipment"

    has_space_ctx_for_water = _has_any(
        norm_text,
        (
            "0g",
            "0.0g",
            "sifir yercekimi",
            "zero gravity",
            "zero-g",
            "agirliksiz",
            "weightless",
            "mikrocekim",
            "mikro yercekimi",
            "microgravity",
            "freefall",
            "uzay",
            "space",
            "iss",
            "orion",
            "kabin",
            "cabin",
        ),
    )

    if _has_any(
        norm_text,
        (
            "yag yangini",
            "kizgin yag",
            "tava yangini",
            "mutfak yangini",
            "evde yangin",
            "ev yangini",
            "evdeki duman dedektor",
            "apartman yangin",
            "orman yangini",
            "fabrika yangin",
            "grease fire",
            "cooking oil fire",
            "kitchen fire",
            "house fire",
            "pour water on oil",
            "home smoke detector",
        ),
    ) or (_has_any(norm_text, ("su dokulur mu", "su dokulmez")) and not has_space_ctx_for_water):
        return "terrestrial_fire"

    # Evde duman dedektörü sorusu (uzay/0G bağlamı yoksa sınır bağlantısıyla yanıtla)
    if _has_any(norm_text, ("duman dedektoru nasil calisir", "how does a smoke detector work", "how do smoke detectors work")) and not _has_any(
        norm_text, ("0g", "iss", "uzay", "space", "daft", "same")
    ):
        return "terrestrial_fire"

    return None


def build_boundary_response(
    boundary_kind: str,
    norm_text: str,
    active_sim: Optional[Dict[str, Any]] = None,
    lang: str = "tr",
) -> str:
    """
    Sınır sorularını geri çevirmez: İlk cümlede sınırı doğal ve kısa biçimde belirtir,
    hemen ardından uzay aracı yangın güvenliğiyle somut fiziksel bağlantısını açıklar.
    """
    is_en = str(lang).lower() == "en"
    inp = (active_sim or {}).get("inputs") or {}
    tel = (active_sim or {}).get("telemetry") or {}
    u_cms = inp.get("airflow_cms", 2.0)
    re_val = tel.get("reynolds_number", 18.0)
    ri_val = tel.get("richardson_number", 0.0)

    if boundary_kind == "rocket_engine":
        if is_en:
            return (
                "High-velocity rocket engines and external thrusters sit outside cabin combustion testing, "
                "yet they link to spacecraft fire safety through flow-regime scaling and pressurized oxidizer line protection.\n\n"
                f"- **High-Speed Jet vs. Cabin Airflow (`Ri = Gr / Re²`):** Rocket chambers inject propellants at `100–3000 m/s` (`Re > 10⁵`, `Ri < 10⁻⁶`), so momentum dominates and gravity has virtually no effect on the flame. Inside crew cabins (`U = {u_cms} cm/s`, `Re = {re_val}`, `Ri = {ri_val}`), gentle ventilation means removing buoyancy turns flames spherical, increases radiative loss (`χ_r`), and shifts `MOC`.\n"
                "- **Cabin Leak Hazard:** Service-module and docking oxidizer/fuel lines are isolated by sealed bulkheads and continuous pressure/gas sensors so a line leak cannot enrich cabin `P_O₂` or lower minimum ignition energy (`MIE`)."
            )
        return (
            "Yüksek hızlı roket motorları ve dış iticiler kabin içi yanma deneylerinin doğrudan kapsamı dışındadır; "
            "ancak akış rejimi farkı ve basınçlı hat sızıntı güvenliği üzerinden uzay aracı yangın emniyetiyle doğrudan ilişkilidir.\n\n"
            f"- **Yüksek Hızlı İtki ve Kabin Havalandırması Farkı (`Ri = Gr / Re²`):** Roket yanma odasında gaz hızları `100–3000 m/s` düzeyinde olduğu için (`Re > 10⁵`, `Ri < 10⁻⁶`) yanma yerçekiminden bağımsızdır. Mürettebat kabinindeki düşük hava akışında ise (`U = {u_cms} cm/s`, `Re = {re_val}`, `Ri = {ri_val}`) yerçekiminin kalkması alevi küreselleştirir, radyatif ısı kaybını (`χ_r`) büyütür ve `MOC` sınırını düşürür.\n"
            "- **Kabin İçi Sızıntı Riski:** Servis modülü veya kenetlenme hatlarındaki oksijen/yakıt sızıntıları kabin kısmi oksijen basıncını (`P_O₂`) yükseltip tutuşma enerjisini düşürebileceği için bölme kapakları ve gaz sensörleriyle izlenir."
        )

    if boundary_kind == "space_equipment":
        if _has_any(norm_text, ("uyku tulumu", "sleeping bag")):
            if is_en:
                return (
                    "Crew sleeping-bag comfort design belongs to general cabin outfitting, but in spacecraft fire safety "
                    "it is evaluated as a large textile surface exposed to low-velocity cabin ventilation.\n\n"
                    "- **Material Behavior (`Nomex / SIBAL`):** Gentle `0G` airflow (`3–8 cm/s`) feeds fresh oxygen to thin fabric edges and can lower `MOC` below `1G` Earth limits (`BASS` and `Saffire` findings), so crew sleep stations use flame-resistant `Nomex` weaves certified under `NASA-STD-6001B`.\n"
                    "- **Early Smoldering Protection:** Sleep bays monitor `CO` accumulation continuously; if overheating or smoldering starts, closing ventilation ducts starves the reaction zone of oxygen."
                )
            return (
                "Mürettebat uyku tulumlarının genel konfor tasarımı günlük yaşam donanımı konusudur; ancak uzay aracı yangın "
                "güvenliğinde kabin içindeki geniş tekstil yüzeylerinden biri olarak doğrudan tutuşma testlerine tabi tutulur.\n\n"
                "- **Malzeme Davranışı (`Nomex / SIBAL`):** `0G` ortamında düşük hızlı kabin havalandırması (`3–8 cm/s`) ince kumaş kenarlarına taze oksijen taşıyarak `MOC` sınırını Dünya'dakinin altına çekebildiği için (`BASS` ve `Saffire` bulguları), uyku bölmelerinde `NASA-STD-6001B` sertifikalı alev geciktirici `Nomex` dokumalar kullanılır.\n"
                "- **Aşırı Isınma ve İçten Yanma Kontrolü:** Uyku kabinlerinde olası kablo ısınması veya içten yanma (`smoldering`) `CO` sensörleriyle izlenir ve ilk adımda hava kanalları kapatılır."
            )

        if _has_any(norm_text, ("gunes panel", "solar panel", "solar array")):
            if is_en:
                return (
                    "External solar arrays operate in hard vacuum where gas-phase flames cannot burn, yet they connect directly "
                    "to cabin fire safety through high-power `120V DC` electrical distribution.\n\n"
                    "- **Internal Bus Overheating & Arc Risk:** Power generated by the arrays enters pressurized modules through switching units (`PCDU / SSPC`), where overloaded harnesses in stagnant `0G` air (`Ra = 0`) can overheat and pyrolyze `Kapton / PTFE` wire insulation.\n"
                    "- **Preventive Isolation:** When thermal or ultrasonic arc sensors detect pre-ignition heating, cutting bay `120V DC` power and cabin airflow stops ignition before open flame develops."
                )
            return (
                "Dış güneş panelleri uzay boşluğunda çalıştığı için vakumda gaz fazı alevi oluşmaz; ancak ürettikleri gücün kabin "
                "içine taşınması nedeniyle uzay aracı yangın güvenliğiyle doğrudan elektriksel koruma üzerinden bağlantılıdır.\n\n"
                "- **Aşırı Isınma ve Kablo Yalıtımı Riski:** Panellerden gelen `120V DC` güç kabin içi dağıtım hatlarından (`PCDU / SSPC`) geçerken, `0G` ortamında doğal soğuma (`Ra = 0`) olmadığı için aşırı akım yerel ısınma ve kablo yalıtımında gaz çıkışına yol açabilir.\n"
                "- **Önleyici Kesme:** Aşırı ısınma veya ark belirtisi algılandığında alev oluşmadan önce ilgili bölümün elektriği (`120V DC`) ve hava akışı kesilir."
            )

        if is_en:
            return (
                "Everyday crew appliances such as cabin food warmers sit outside combustion experiments as routine hardware, "
                "but in spacecraft fire safety they are treated as localized overheating and ignition sources.\n\n"
                "- **`0G` Stagnant-Heat Buildup (`Ra = 0`):** Without buoyancy to carry warm air upward, heat concentrates around heating elements and wiring harnesses (`Semenov` thermal runaway risk).\n"
                "- **Containment & Response:** Enclosures use flame-retardant `Nomex` and metallic barriers (`NASA-STD-6001B`); if temperature or `CO` rises, bay `120V DC` power and ventilation fans are shut off immediately."
            )
        return (
            "ISS'deki yemek ısıtıcısı gibi günlük mürettebat ekipmanlarının rutin kullanımı doğrudan yanma deneyi konusu değildir; "
            "ancak kabin yangın güvenliğinde bu cihazlar birincil aşırı ısınma ve tutuşma noktası olarak izlenir.\n\n"
            "- **`0G` Ortamında Isı Birikimi (`Ra = 0`):** Mikroçekimde ısınan hava yükselip dağılamadığı için ısıtıcı yüzeyler ve besleme kabloları çevresinde yerel sıcaklık hızla yükselebilir (`Semenov` ısıl kaçak riski).\n"
            "- **Yalıtım ve Müdahale:** Cihaz gövdelerinde `NASA-STD-6001B` uyumlu yanmaz metal ve `Nomex` katmanlar kullanılır; aşırı ısınma algılandığında ilk adımda bölüm elektriği (`120V DC`) ve havalandırma fanı kapatılır."
        )

    # terrestrial_fire
    if _has_any(norm_text, ("duman dedektor", "smoke detector")) and not _has_any(norm_text, ("yag", "oil", "grease", "su dok")):
        if is_en:
            return (
                "Household smoke detectors belong to everyday building safety, yet their light-scattering physics directly "
                "connects to spacecraft fire detection and NASA's terrestrial technology transfers.\n\n"
                "- **Earth vs. `0G` Soot & Cool Flames:** Standard photoelectric detectors sense visible soot particles, but in `0G` flames can transition into soot-free `550–780 K` cool flames that optical sensors miss, requiring `CO` gas analyzers and `UV/IR` radiometers.\n"
                "- **Space-to-Earth Transfer (`SAME / DAFT`):** Multi-angle laser scattering developed for ISS and Lunar dust rejection now reduces false alarms from dust and steam in terrestrial buildings, mines, and aircraft cargo bays."
            )
        return (
            "Ev tipi duman dedektörleri günlük bina güvenliği konusudur; ancak çalışma prensibi uzay aracı yangın algılama "
            "sistemleri ve Dünya'ya aktarılan NASA sensör teknolojileriyle doğrudan bağlantılıdır.\n\n"
            "- **Kurum Boyutu ve Görünmez Soğuk Alev Farkı:** Klasik optik dedektörler görünür duman parçacıklarını algılar; `0G` ortamında ise kurumsuz `550–780 K` soğuk alev oluşabildiği için optik sensörler `CO` gaz analizörü ve termal/kızılötesi algılayıcılarla birlikte kullanılır.\n"
            "- **Dünya'ya Teknoloji Transferi (`SAME / DAFT`):** Uzay kabinlerinde Ay tozunu gerçek yangın dumanından ayırmak için geliştirilen çok açılı lazer sensörler, bugün Dünya'da toz ve su buharı kaynaklı yanlış alarmları önlemektedir."
        )

    if is_en:
        return (
            "Household kitchen and grease fires belong to terrestrial safety rather than orbital testing, yet water droplet "
            "size physics directly explains both why bulk water fails on hot oil and how spacecraft water-mist extinguishers work.\n\n"
            "- **Bulk Water vs. `25–40 µm` Fine Water Mist:** Pouring bulk liquid water onto burning oil sinks and flashes into steam (`~1700x` expansion), splattering burning fuel—so kitchen grease fires must be smothered by cutting oxygen with a lid. Crewed spacecraft never spray bulk water; they deploy **`25–40 µm` fine water mist (`SoFIE-MIST / ISS PFE`)**, whose micro-droplets evaporate directly in the flame front to absorb heat and dilute oxygen without splashing or damaging electronics.\n"
            "- **Space-to-Earth Transfer:** NASA micro-mist nozzle designs (`SoFIE-MIST`) and `Nomex / PBI` protective fabrics are now widely used in terrestrial cleanrooms, battery rooms, and firefighting gear."
        )
    return (
        "Evdeki yağ ve mutfak yangınları doğrudan yeryüzü güvenliği konusudur; ancak suyun damlacık boyutu ve buharlaşma "
        "fiziği uzay aracı yangın söndürme sistemleriyle birebir bağlantılıdır.\n\n"
        "- **Kaba Su ile `25–40 µm` İnce Su Sisi Farkı:** Kızgın yağa dökülen kaba sıvı su yağın altına çöküp aniden buharlaşarak (`~1700 kat` hacim genleşmesi) alevli yağı etrafa sıçratır; bu nedenle tavadaki yağ yangınında su dökülmez, kapak kapatılarak oksijen kesilir. Uzay araçlarında ise kaba su yerine **`25–40 µm` ince su sisi (`SoFIE-MIST / ISS PFE`)** kullanılır; mikro damlacıklar daha alev cephesindeyken buharlaşıp ısıyı çeker ve elektronikleri ıslatmadan alevi boğar.\n"
        "- **Dünya'ya Teknoloji Transferi:** Uzay kabinleri için geliştirilen bu ince su sisi başlıkları ve `Nomex / PBI` koruyucu kumaşlar günümüzde veri merkezleri, batarya odaları ve itfaiye ekipmanlarında güvenle kullanılmaktadır."
    )


def _is_previous_turn_valid_in_scope(history: Optional[Sequence[Dict[str, str]]]) -> bool:
    """
    Geçmiş zehirlenmesi koruması:
    Yalnızca bir önceki kullanıcı mesajı gerçekten kapsam içi / sınır bağlantılı ise
    VE bir önceki asistan mesajı konu dışı / kural kilidi reddi değilse takip sorusuna izin verir.
    """
    if not history:
        return False

    last_user_msg = ""
    last_assistant_msg = ""
    for item in reversed(list(history)):
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").lower()
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        if role == "assistant" and not last_assistant_msg:
            last_assistant_msg = content
        elif role == "user" and not last_user_msg:
            last_user_msg = content
            break

    if not last_user_msg:
        return False

    if last_assistant_msg:
        norm_asst = normalize_scope_text(last_assistant_msg)
        if _has_any(norm_asst, _REJECTED_ASSISTANT_MARKERS):
            return False

    prev_eval = evaluate_query_scope(
        user_message=last_user_msg,
        history=None,
        sim_params=None,
        media_context="",
        image_base64=None,
        lang="tr",
        _allow_followup=False,
    )
    return prev_eval.get("status") in ("in_scope", "boundary_context")


def evaluate_query_scope(
    user_message: str,
    history: Optional[Sequence[Dict[str, str]]] = None,
    sim_params: Optional[Dict[str, Any]] = None,
    media_context: str = "",
    image_base64: Optional[str] = None,
    lang: str = "tr",
    _allow_followup: bool = True,
) -> Dict[str, Any]:
    """
    Kullanıcı mesajını < 1 ms içinde sınıflandırır:
    - status: 'in_scope' | 'boundary_context' | 'rule_locked' | 'off_topic'
    - cleaned_query: Günlük sohbet yan cümlesi ayıklanmış ve yazım hataları düzeltilmiş soru metni
    - misconception: Fiziksel yanılgı yakalandıysa tek cümlelik TR/EN düzeltme sözlüğü
    - physics_note: bool (Fiziksel Düzeltme etiketi gösterilsin mi)
    - reply_tr / reply_en: Erken çıkış ('off_topic', 'rule_locked') veya 'boundary_context' için hazır doğal yanıt
    """
    raw_msg = str(user_message or "").strip()
    is_en = str(lang).lower() == "en"
    full_norm = normalize_scope_text(raw_msg)
    fuzzy_full, repaired_full_norm = _match_fuzzy_domain_tokens(full_norm)

    # 1) KURAL VE GÜVENLİK KİLİDİ ('rule_locked') — Her şeyden önce tam metin üzerinde denetlenir
    has_role_override = _has_any(repaired_full_norm, _ROLE_OVERRIDE_PHRASES)
    has_halon_endorse = ("halon" in repaired_full_norm) and _has_any(repaired_full_norm, _HALON_ENDORSE_VERBS)
    if has_role_override or has_halon_endorse:
        mentions_halon = "halon" in repaired_full_norm
        if mentions_halon:
            rep_tr = (
                "Uçuş güvenliği kuralları sabittir ve değiştirilemez. "
                "Halon 1301 yüksek alev sıcaklığında zehirli `HF` ve `HBr` gazı ürettiği için kapalı uzay aracı kabinlerinde "
                "kullanılmaz; bunun yerine hava akışı kesilir ve ince su sisi uygulanır."
            )
            rep_en = (
                "Flight safety rules are fixed and cannot be overridden. "
                "Halon 1301 is not used in enclosed spacecraft cabins because it produces toxic `HF` and `HBr` gases at flame "
                "temperatures; crews cut cabin airflow and apply fine water mist instead."
            )
        else:
            rep_tr = (
                "Uçuş ve yangın güvenliği kuralları sabittir; bu ekran yalnızca uzay aracı yangın güvenliği ve yanma fiziği "
                "analizleri için çalışır. Aktif 3B yanma odası veya Orion bölmeleri üzerinden teknik bir soru sorabilirsiniz."
            )
            rep_en = (
                "Flight and fire safety rules are fixed; this console operates strictly for spacecraft fire safety and combustion "
                "physics analysis. You can ask a technical question based on the active 3D chamber or Orion compartments."
            )
        return {
            "status": "rule_locked",
            "badge_tr": "Konu Dışı",
            "badge_en": "Off-Topic",
            "physics_note": False,
            "is_followup": False,
            "mixed_stripped": False,
            "cleaned_query": raw_msg,
            "typo_corrections": [c for _, c in fuzzy_full],
            "misconception": None,
            "boundary_kind": None,
            "reply_tr": rep_tr,
            "reply_en": rep_en,
            "reply": rep_en if is_en else rep_tr,
        }

    # 2) KARMA CÜMLE AYIKLAMA VE YAZIM HATASI ONARIMI
    stripped_msg, mixed_stripped = _strip_casual_clauses(raw_msg)
    clause_norm = normalize_scope_text(stripped_msg)
    if clause_norm == full_norm:
        fuzzy_hits, repaired_norm = fuzzy_full, repaired_full_norm
    else:
        fuzzy_hits, repaired_norm = _match_fuzzy_domain_tokens(clause_norm)

    # Yazım hatası düzeltilmiş metni alt motorlara da yardımcı olacak şekilde oluştur
    cleaned_query = stripped_msg
    if fuzzy_hits:
        missing_canon = [canon for orig, canon in fuzzy_hits if orig != canon and canon not in clause_norm]
        if missing_canon:
            cleaned_query = f"{stripped_msg} ({' '.join(dict.fromkeys(missing_canon))})"

    # 3) SINIR BAĞLANTISI ('boundary_context') — Günlük ISS ekipmanı, ev/mutfak yangını, roket motoru
    boundary_kind = _detect_boundary_category(repaired_norm)
    if boundary_kind:
        miscon = detect_physical_misconception(repaired_norm)
        return {
            "status": "boundary_context",
            "badge_tr": "Yangın Güvenliği Bağlantısı",
            "badge_en": "Fire Safety Context",
            "physics_note": bool(miscon),
            "is_followup": False,
            "mixed_stripped": mixed_stripped,
            "cleaned_query": cleaned_query,
            "typo_corrections": [c for _, c in fuzzy_hits],
            "misconception": miscon,
            "boundary_kind": boundary_kind,
            "reply_tr": "",
            "reply_en": "",
            "reply": "",
        }

    # 4) DOĞRUDAN KAPSAM İÇİ ('in_scope') KONTROLÜ
    has_explicit_off_topic = _has_any(repaired_norm, _EXPLICIT_OFF_TOPIC_PHRASES)
    has_strong_space_anchor = _has_strong_space_anchor(repaired_norm)
    blocked_by_off_topic = has_explicit_off_topic and not has_strong_space_anchor

    has_direct_domain = (
        _has_any(repaired_norm, _DIRECT_DOMAIN_PHRASES)
        or bool(_RE_DOMAIN_SHORT_TOKENS.search(repaired_norm))
        or bool(_RE_NATURAL_COMBUSTION_TOKENS.search(repaired_norm))
        or len(fuzzy_hits) > 0
    )
    clean_greeting_norm = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", repaired_norm)).strip()
    has_intro_intent = (
        _has_any(repaired_norm, _PLATFORM_INTRO_PHRASES)
        or clean_greeting_norm in ("yardim", "help")
        or clean_greeting_norm in _SHORT_GREETINGS
    )

    if not blocked_by_off_topic and (has_direct_domain or has_intro_intent):
        miscon = detect_physical_misconception(repaired_norm)
        return {
            "status": "in_scope",
            "badge_tr": "Doğrudan Analiz",
            "badge_en": "Direct Analysis",
            "physics_note": bool(miscon),
            "is_followup": False,
            "mixed_stripped": mixed_stripped,
            "cleaned_query": cleaned_query,
            "typo_corrections": [c for _, c in fuzzy_hits],
            "misconception": miscon,
            "boundary_kind": None,
            "reply_tr": "",
            "reply_en": "",
            "reply": "",
        }

    # 5) GÜVENLİ TAKİP SORUSU VE EKLİ DOSYA/GÖRSEL DESTEĞİ (Geçmiş Zehirlenmesi Korumalı)
    has_media = bool((media_context and str(media_context).strip()) or (image_base64 and str(image_base64).strip()))
    if not has_explicit_off_topic:
        if has_media and (
            _has_any(repaired_norm, _MEDIA_FOLLOWUP_PATTERNS)
            or _has_any(repaired_norm, _FOLLOWUP_PATTERNS)
            or len(repaired_norm.split()) <= 6
        ):
            return {
                "status": "in_scope",
                "badge_tr": "Doğrudan Analiz",
                "badge_en": "Direct Analysis",
                "physics_note": False,
                "is_followup": True,
                "mixed_stripped": mixed_stripped,
                "cleaned_query": cleaned_query,
                "typo_corrections": [],
                "misconception": None,
                "boundary_kind": None,
                "reply_tr": "",
                "reply_en": "",
                "reply": "",
            }

        if _allow_followup and _has_any(repaired_norm, _FOLLOWUP_PATTERNS) and _is_previous_turn_valid_in_scope(history):
            return {
                "status": "in_scope",
                "badge_tr": "Doğrudan Analiz",
                "badge_en": "Direct Analysis",
                "physics_note": False,
                "is_followup": True,
                "mixed_stripped": mixed_stripped,
                "cleaned_query": cleaned_query,
                "typo_corrections": [],
                "misconception": None,
                "boundary_kind": None,
                "reply_tr": "",
                "reply_en": "",
                "reply": "",
            }

    # 6) KONU DIŞI ('off_topic') — Erken Çıkış (< 1 ms, sıfır dış kaynak harcaması, 1-2 sade cümle)
    fuel_id = str((sim_params or {}).get("fuel_id") or "n_heptane")
    fuel_labels_tr = {
        "n_heptane": "n-Heptan",
        "methanol": "Metanol",
        "ethanol": "Etanol",
        "pmma": "PMMA",
        "nomex": "Nomex",
        "sibal": "SIBAL kumaş",
        "propane_cfig": "Propan",
        "hydrogen": "Hidrojen",
        "custom_material": "özel malzeme",
    }
    fuel_labels_en = {
        "n_heptane": "n-Heptane",
        "methanol": "Methanol",
        "ethanol": "Ethanol",
        "pmma": "PMMA",
        "nomex": "Nomex",
        "sibal": "SIBAL fabric",
        "propane_cfig": "Propane",
        "hydrogen": "Hydrogen",
        "custom_material": "custom material",
    }
    f_tr = fuel_labels_tr.get(fuel_id, "yanma odası")
    f_en = fuel_labels_en.get(fuel_id, "combustion chamber")

    off_tr = (
        "Bu ekran yalnızca uzay aracı yangın güvenliği, kabin içi müdahale ve mikroçekim yanma fiziği sorularına odaklanır. "
        f"Aktif `{f_tr}` sahnesi için aşağıdaki hazır işlemlerden birini seçebilir veya doğrudan teknik bir soru yazabilirsiniz."
    )
    off_en = (
        "This console focuses exclusively on spacecraft fire safety, cabin response, and microgravity combustion physics. "
        f"You can pick one of the quick actions below for the active `{f_en}` scene or type a technical question."
    )

    return {
        "status": "off_topic",
        "badge_tr": "Konu Dışı",
        "badge_en": "Off-Topic",
        "physics_note": False,
        "is_followup": False,
        "mixed_stripped": False,
        "cleaned_query": raw_msg,
        "typo_corrections": [],
        "misconception": None,
        "boundary_kind": None,
        "reply_tr": off_tr,
        "reply_en": off_en,
        "reply": off_en if is_en else off_tr,
    }


def prepend_misconception_correction(reply_text: str, misconception: Optional[Dict[str, str]], lang: str = "tr") -> str:
    """
    Fiziksel yanlış varsayım yakalandığında yanıtın en başına kısa ve net mühendislik düzeltmesini ekler.
    """
    if not misconception:
        return reply_text
    is_en = str(lang).lower() == "en"
    corr = str(misconception.get("correction_en" if is_en else "correction_tr") or "").strip()
    if not corr:
        return reply_text
    norm_rep = normalize_scope_text(reply_text[:320])
    norm_corr_head = normalize_scope_text(corr[:60])
    if norm_corr_head and norm_corr_head in norm_rep:
        return reply_text
    prefix_lbl = "**Physics Note:**" if is_en else "**Fiziksel Düzeltme:**"
    return f"{prefix_lbl} {corr}\n\n{reply_text.lstrip()}"


def sanitize_unverified_experiment_names(reply_text: str, lang: str = "tr") -> Tuple[str, bool]:
    """
    Harici veya yerel dil modellerinin üretebileceği katalog dışı uydurma deney numaralarını
    (örn. Saffire-IX, Saffire-7, FLEX-9, BASS-4, SoFIE-9) gerçek NASA program adlarıyla temizler.
    """
    if not reply_text:
        return reply_text, False

    cleaned = reply_text
    changed = False

    for pat, repl in (
        (_RE_FAKE_SAFFIRE_ROMAN, "Saffire (I–VI)"),
        (_RE_FAKE_SAFFIRE_NUM, "Saffire (I–VI)"),
        (_RE_FAKE_FLEX, "FLEX / FLEX-2"),
        (_RE_FAKE_BASS, "BASS / BASS-II"),
        (_RE_FAKE_SOFIE, "SoFIE"),
        (_RE_FAKE_SPICE_SLICE, r"\1"),
    ):
        new_txt = pat.sub(repl, cleaned)
        if new_txt != cleaned:
            cleaned = new_txt
            changed = True

    return cleaned, changed


def build_suggested_actions(
    scope_result: Dict[str, Any],
    active_sim: Optional[Dict[str, Any]] = None,
    lang: str = "tr",
) -> List[Dict[str, Any]]:
    """
    Yanıt balonunun altında gösterilecek kısa, doğal, çift dilli (TR/EN) tıklanabilir eylem ve örnek soru butonlarını üretir:
    - apply_3d_sim ('3B Odaya Uygula' / 'Load in 3D')
    - run_orion_sequence ('Sıralı Müdahaleyi Başlat' / 'Start Fire Response')
    - ask_prompt (aktif 3B sahneye uygun 4-7 kelimelik sade sorular)
    """
    inp = (active_sim or {}).get("inputs") or {}
    comp_net = (active_sim or {}).get("compartment_network") or {}
    norm_q = normalize_scope_text(str(scope_result.get("cleaned_query") or ""))

    cur_fuel = str(inp.get("fuel_id") or "n_heptane")
    cur_g = float(inp.get("gravity_g") if inp.get("gravity_g") is not None else 0.0)
    cur_o2 = float(inp.get("oxygen_pct") if inp.get("oxygen_pct") is not None else 21.0)
    cur_p = float(inp.get("pressure_psia") if inp.get("pressure_psia") is not None else 14.7)
    cur_u = float(inp.get("airflow_cms") if inp.get("airflow_cms") is not None else 2.0)
    fire_comp = str(comp_net.get("fire_compartment_id") or "ORION_CM").upper()
    if fire_comp not in ("ORION_CM", "IHAB", "HALO", "AIRLOCK", "PPE"):
        fire_comp = "ORION_CM"

    # Sorunun konusuna göre en uygun 3B sahne parametresi
    if "metanol" in norm_q or "methanol" in norm_q:
        target_sim = {
            "fuel_id": "methanol",
            "gravity_g": 0.0,
            "oxygen_pct": 16.0,
            "pressure_psia": 14.7,
            "airflow_cms": 0.4,
            "droplet_d0_mm": 3.8,
            "diluent": "N2",
        }
    elif "soguk alev" in norm_q or "cool flame" in norm_q:
        target_sim = {
            "fuel_id": "n_heptane",
            "gravity_g": 0.0,
            "oxygen_pct": 15.5,
            "pressure_psia": 14.7,
            "airflow_cms": 0.2,
            "droplet_d0_mm": 4.2,
            "diluent": "N2",
        }
    elif "uzay giysisi" in norm_q or "spacesuit" in norm_q or "eva" in norm_q:
        target_sim = {
            "fuel_id": "nomex",
            "gravity_g": 0.16,
            "oxygen_pct": 100.0,
            "pressure_psia": 4.3,
            "airflow_cms": 4.0,
            "droplet_d0_mm": 3.2,
            "diluent": "N2",
            "habitat_id": "eva_suit",
        }
    elif "pmma" in norm_q or "saffire" in norm_q or "bass" in norm_q:
        target_sim = {
            "fuel_id": "pmma",
            "gravity_g": 0.0,
            "oxygen_pct": 21.0,
            "pressure_psia": 14.7,
            "airflow_cms": 5.5,
            "droplet_d0_mm": 3.5,
            "diluent": "N2",
        }
    else:
        target_sim = {
            "fuel_id": cur_fuel,
            "gravity_g": cur_g,
            "oxygen_pct": cur_o2,
            "pressure_psia": cur_p,
            "airflow_cms": max(0.2, cur_u) if cur_u != 0 else 4.5,
            "droplet_d0_mm": float(inp.get("droplet_d0_mm") or 3.2),
            "diluent": str(inp.get("diluent") or "N2"),
        }

    actions: List[Dict[str, Any]] = [
        {
            "type": "apply_3d_sim",
            "label_tr": "3B Odaya Uygula",
            "label_en": "Load in 3D",
            "sim_params": target_sim,
        },
        {
            "type": "run_orion_sequence",
            "label_tr": "Sıralı Müdahaleyi Başlat",
            "label_en": "Start Fire Response",
            "compartment_id": fire_comp,
        },
    ]

    # Aktif sahneye duyarlı 4-7 kelimelik doğal örnek sorular
    prompt_candidates: List[Tuple[str, str]] = []
    if cur_fuel == "methanol" or "metanol" in norm_q:
        prompt_candidates.append(("0G'de metanol neden soğuk yanar?", "How does methanol burn in 0G?"))
    elif cur_g == 0.16:
        prompt_candidates.append(("Ay yerçekiminde tutuşma sınırı nasıl değişir?", "How does lunar gravity shift flammability?"))
    elif cur_o2 >= 50.0:
        prompt_candidates.append(("Uzay giysisinde neden saf oksijen kullanılır?", "Why do spacesuits use pure oxygen?"))
    else:
        prompt_candidates.append(("0G'de metanol nasıl yanar?", "How does methanol burn in 0G?"))

    prompt_candidates.append(("Su sisi alevi nasıl söndürür?", "How does water mist quench fire?"))
    prompt_candidates.append(("Kapak ne zaman güvenle açılır?", "When is hatch opening safe?"))

    for p_tr, p_en in prompt_candidates[:2]:
        actions.append(
            {
                "type": "ask_prompt",
                "label_tr": p_tr,
                "label_en": p_en,
                "prompt_tr": p_tr,
                "prompt_en": p_en,
            }
        )

    return actions

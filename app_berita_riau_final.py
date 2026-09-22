
import sys
import re
from urllib.parse import quote
from datetime import datetime

import pandas as pd
import requests
import feedparser
import streamlit as st

# ============================================================
# KONFIGURASI
# ============================================================
SHEET_ID = "1q4AMGQzc0qjm0VQ1X9VnMn2wrJW8z9wnHPcvbeX1Nts"
SHEET_NAME = "DATABASE_BERITA"

# Tempel URL Web App Apps Script Anda di sini.
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxcEw9GT4USdRs7v4ZGxhCCTGcx9QxKfV05l-vIMDT1xoJ9_8t-xeLOYSgBQeaG43zD/exec"

RSS_URL = (
    "https://news.google.com/rss/search?q={query}"
    "&hl=id&gl=ID&ceid=ID:id"
)

COLUMNS = [
    "Tanggal", "Judul", "Sumber", "Link", "Kabupaten/Kota",
    "Perusahaan/Bisnis", "Kode Sektor", "Sektor PDRB",
    "Sentimen", "Skor Sentimen", "Kata Kunci", "Query Sektor"
]

SEKTOR = {
    "A": "Pertanian, Kehutanan dan Perikanan",
    "B": "Pertambangan dan Penggalian",
    "C": "Industri Pengolahan",
    "D": "Pengadaan Listrik dan Gas",
    "E": "Pengadaan Air, Pengelolaan Sampah, Limbah dan Daur Ulang",
    "F": "Konstruksi",
    "G": "Perdagangan Besar dan Eceran; Reparasi Mobil dan Sepeda Motor",
    "H": "Transportasi dan Pergudangan",
    "I": "Penyediaan Akomodasi dan Makan Minum",
    "J": "Informasi dan Komunikasi",
    "K": "Jasa Keuangan dan Asuransi",
    "L": "Real Estat",
    "M,N": "Jasa Perusahaan",
    "O": "Administrasi Pemerintahan, Pertahanan dan Jaminan Sosial Wajib",
    "P": "Jasa Pendidikan",
    "Q": "Jasa Kesehatan dan Kegiatan Sosial",
    "R,S,T,U": "Jasa Lainnya"
}

SEKTOR_TERMS = {
    "A": ["pertanian", "perkebunan", "sawit", "CPO", "karet", "perikanan", "nelayan", "petani", "padi"],
    "B": ["pertambangan", "tambang", "batubara", "batu bara", "mineral", "migas", "minyak bumi", "gas bumi", "galian"],
    "C": ["industri", "pabrik", "manufaktur", "pengolahan", "hilirisasi", "produksi", "semen", "pulp", "kertas"],
    "D": ["listrik", "PLN", "pembangkit", "energi", "gas", "kelistrikan"],
    "E": ["air bersih", "sampah", "limbah", "daur ulang", "sanitasi", "persampahan"],
    "F": ["konstruksi", "proyek", "jalan", "jembatan", "infrastruktur", "gedung", "pembangunan"],
    "G": ["perdagangan", "ritel", "grosir", "pasar", "toko", "supermarket", "minimarket", "dealer", "otomotif", "penjualan"],
    "H": ["transportasi", "pelabuhan", "Pelindo", "bandara", "penerbangan", "logistik", "pergudangan", "kargo", "ekspedisi"],
    "I": ["hotel", "restoran", "kuliner", "wisata", "pariwisata", "akomodasi", "kafe", "cafe"],
    "J": ["telekomunikasi", "internet", "digital", "teknologi", "data center", "aplikasi", "startup", "operator seluler"],
    "K": ["bank", "perbankan", "asuransi", "pegadaian", "leasing", "kredit", "pembiayaan", "keuangan", "investasi", "fintech"],
    "L": ["properti", "property", "real estat", "real estate", "apartemen", "mal", "ruko", "perumahan", "developer"],
    "M,N": ["konsultan", "jasa perusahaan", "akuntansi", "hukum", "arsitektur", "outsourcing"],
    "O": ["pemerintah", "pemda", "APBD", "anggaran", "dinas", "kebijakan", "pelayanan publik"],
    "P": ["pendidikan", "sekolah", "kampus", "universitas", "guru", "siswa", "pelatihan"],
    "Q": ["rumah sakit", "puskesmas", "klinik", "kesehatan", "dokter", "obat", "farmasi", "pasien"],
    "R,S,T,U": ["hiburan", "olahraga", "budaya", "organisasi", "salon", "laundry", "bengkel", "jasa"]
}

KABKOTA = [
    "Pekanbaru", "Dumai", "Kampar", "Pelalawan", "Siak", "Bengkalis",
    "Rokan Hulu", "Rokan Hilir", "Indragiri Hilir", "Indragiri Hulu",
    "Kuantan Singingi", "Kepulauan Meranti"
]

POSITIVE = [
    "naik", "meningkat", "tumbuh", "positif", "untung", "laba",
    "investasi", "ekspansi", "dibuka", "membaik", "surplus",
    "menjanjikan", "berkembang", "peningkatan", "mendorong"
]

NEGATIVE = [
    "turun", "menurun", "merosot", "rugi", "kerugian", "phk",
    "bangkrut", "tutup", "ditutup", "defisit", "lesu", "anjlok",
    "terkendala", "gagal", "penurunan", "melemah"
]


# ============================================================
# DATABASE
# ============================================================
def sheet_csv_url():
    return (
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/"
        f"gviz/tq?tqx=out:csv&sheet={quote(SHEET_NAME)}"
    )


def read_database():
    try:
        df = pd.read_csv(sheet_csv_url())
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df[COLUMNS]
    except Exception as e:
        print("Gagal membaca Google Sheet:", e)
        return pd.DataFrame(columns=COLUMNS)


def normalize_title(title):
    title = str(title).lower()
    title = re.sub(r"\[[^\]]*\]", "", title)
    title = re.sub(r"\s+", " ", title)
    return title.strip()


# ============================================================
# KLASIFIKASI
# ============================================================
def extract_company(text):
    patterns = [
        r"\bPT\.?\s+[A-Z][A-Za-z0-9&.,' -]{2,80}",
        r"\bCV\.?\s+[A-Z][A-Za-z0-9&.,' -]{2,80}",
        r"\bPerum\s+[A-Z][A-Za-z0-9&.,' -]{2,80}",
        r"\bPersero\s+[A-Z][A-Za-z0-9&.,' -]{2,80}",
        r"\bBank\s+[A-Z][A-Za-z0-9&.,' -]{2,60}"
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).strip(" .,")
    return ""


def extract_kabkota(text):
    low = text.lower()
    found = [k for k in KABKOTA if k.lower() in low]
    return ", ".join(found[:3]) if found else "Riau"


def classify(text, query_sector):
    low = text.lower()
    scores = {}
    hits_by_sector = {}

    for code, terms in SEKTOR_TERMS.items():
        hits = [term for term in terms if term.lower() in low]
        scores[code] = len(hits)
        hits_by_sector[code] = hits

    if query_sector in scores:
        scores[query_sector] += 2

    best = max(scores, key=scores.get)

    if scores[best] == 0:
        return "", "Belum terklasifikasi", "", 0

    return best, SEKTOR[best], ", ".join(hits_by_sector[best]), scores[best]


def get_sentiment(text):
    low = text.lower()
    pos = sum(1 for word in POSITIVE if word in low)
    neg = sum(1 for word in NEGATIVE if word in low)

    if pos > neg:
        return "Positif", 1
    if neg > pos:
        return "Negatif", -1
    return "Netral", 0


# ============================================================
# COLLECTOR
# ============================================================
def build_queries():
    queries = []

    for code, terms in SEKTOR_TERMS.items():
        for term in terms:
            queries.append((code, f'Riau "{term}"'))

    for kab in KABKOTA:
        for code, terms in SEKTOR_TERMS.items():
            for term in terms[:3]:
                queries.append((code, f'"{kab}" "{term}"'))

    general = [
        "ekonomi Riau", "bisnis Riau", "usaha Riau", "investasi Riau",
        "perusahaan Riau", "ekspor Riau", "impor Riau", "produksi Riau",
        "industri Riau", "perdagangan Riau", "lapangan kerja Riau",
        "tenaga kerja Riau", "harga komoditas Riau",
        "ekspansi perusahaan Riau", "pembangunan Riau"
    ]

    for q in general:
        queries.append(("", q))

    return list(dict.fromkeys(queries))


def collect_news(progress_callback=None):
    rows = []
    seen_links = set()
    seen_titles = set()

    queries = build_queries()
    total = len(queries)

    for i, (query_sector, query) in enumerate(queries, start=1):
        try:
            url = RSS_URL.format(query=quote(query))
            feed = feedparser.parse(url)

            # Semua entry yang dikembalikan RSS diproses.
            for entry in feed.entries:
                title = str(getattr(entry, "title", "") or "").strip()
                link = str(getattr(entry, "link", "") or "").strip()

                if not title:
                    continue

                title_key = normalize_title(title)

                if link and link in seen_links:
                    continue
                if title_key in seen_titles:
                    continue

                try:
                    source = str(entry.source.get("title", "") or "")
                except Exception:
                    source = ""

                published = str(
                    getattr(entry, "published", "") or ""
                ).strip()

                summary = re.sub(
                    r"<[^>]+>", " ",
                    str(getattr(entry, "summary", "") or "")
                )
                content = f"{title} {summary}"

                kode, sektor, keywords, _ = classify(
                    content, query_sector
                )
                sentimen, skor = get_sentiment(content)

                rows.append({
                    "Tanggal": published,
                    "Judul": title,
                    "Sumber": source,
                    "Link": link,
                    "Kabupaten/Kota": extract_kabkota(content),
                    "Perusahaan/Bisnis": extract_company(content),
                    "Kode Sektor": kode,
                    "Sektor PDRB": sektor,
                    "Sentimen": sentimen,
                    "Skor Sentimen": skor,
                    "Kata Kunci": keywords,
                    "Query Sektor": query_sector
                })

                if link:
                    seen_links.add(link)
                seen_titles.add(title_key)

        except Exception:
            pass

        if progress_callback:
            progress_callback(i, total)

    df = pd.DataFrame(rows, columns=COLUMNS)

    if df.empty:
        return df

    df["_title_key"] = df["Judul"].map(normalize_title)

    # Dedup berdasarkan link.
    nonempty = df["Link"].fillna("").astype(str).str.strip() != ""
    df = pd.concat([
        df[nonempty].drop_duplicates("Link", keep="first"),
        df[~nonempty]
    ], ignore_index=True)

    # Dedup berdasarkan judul.
    df = df.drop_duplicates("_title_key", keep="first")
    return df.drop(columns=["_title_key"])


def push_to_google_sheet(df):
    if APPS_SCRIPT_URL.startswith("TEMPEL_"):
        return False, "URL Apps Script belum diisi."

    payload = {
        "rows": df.fillna("").astype(str).values.tolist()
    }

    try:
        response = requests.post(
            APPS_SCRIPT_URL,
            json=payload,
            timeout=120,
            allow_redirects=True
        )

        raw = response.text.strip()

        if response.status_code != 200:
            return False, f"HTTP {response.status_code}: {raw[:500]}"

        if not raw:
            return False, "Respons Apps Script kosong."

        try:
            result = response.json()
        except ValueError:
            return False, (
                "Apps Script tidak mengembalikan JSON. "
                f"Respons: {raw[:500]}"
            )

        if not result.get("ok"):
            return False, result.get("message", "Apps Script gagal.")

        return True, result.get(
            "message", f"{len(df)} berita berhasil disimpan."
        )

    except Exception as e:
        return False, str(e)


def collect_and_save(progress_callback=None, logger=print):
    db = read_database()

    logger(f"Database saat ini: {len(db):,} berita")
    logger("Mengumpulkan berita...")

    collected = collect_news(progress_callback)

    logger(f"Kandidat unik: {len(collected):,}")

    if collected.empty:
        return {
            "ok": True, "new": 0, "duplicates": 0,
            "message": "Tidak ada berita ditemukan."
        }

    existing_links = set(
        db["Link"].fillna("").astype(str).str.strip()
    ) if len(db) else set()

    existing_titles = set(
        db["Judul"].fillna("").astype(str).map(normalize_title)
    ) if len(db) else set()

    new_df = collected[
        ~collected["Link"].fillna("").astype(str).str.strip().isin(
            existing_links
        )
        & ~collected["Judul"].fillna("").astype(str).map(
            normalize_title
        ).isin(existing_titles)
    ].copy()

    duplicates = len(collected) - len(new_df)

    logger(f"Duplikat dilewati: {duplicates:,}")
    logger(f"Berita baru: {len(new_df):,}")

    if new_df.empty:
        return {
            "ok": True, "new": 0, "duplicates": duplicates,
            "message": "Database sudah mutakhir."
        }

    ok, message = push_to_google_sheet(new_df)

    return {
        "ok": ok,
        "new": len(new_df) if ok else 0,
        "duplicates": duplicates,
        "message": message
    }


# ============================================================
# MODE OTOMATIS: file yang sama dijalankan oleh Task Scheduler
# python app_berita_riau_final.py --collect
# ============================================================
if "--collect" in sys.argv:
    print("=" * 70)
    print("AUTO UPDATE BERITA RIAU")
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)

    result = collect_and_save(logger=print)
    print(result["message"])

    if not result["ok"]:
        raise SystemExit(1)

    raise SystemExit(0)


# ============================================================
# DASHBOARD STREAMLIT
# ============================================================
st.set_page_config(
    page_title="Business Activity Signal — Riau",
    page_icon="📰",
    layout="wide"
)

st.title("📰 Business Activity Signal — Riau")
st.caption(
    "Google News → 17 sektor PDRB → deduplikasi → Google Spreadsheet"
)

if APPS_SCRIPT_URL.startswith("TEMPEL_"):
    st.warning(
        "⚠️ Tempel URL Web App Apps Script yang berakhiran /exec "
        "pada variabel APPS_SCRIPT_URL."
    )


@st.cache_data(ttl=60, show_spinner=False)
def load_db():
    return read_database()


db = load_db()

if len(db):
    db["Tanggal_dt"] = pd.to_datetime(
        db["Tanggal"],
        errors="coerce",
        utc=True
    ).dt.tz_convert("Asia/Jakarta").dt.tz_localize(None)
else:
    db["Tanggal_dt"] = pd.Series(dtype="datetime64[ns]")


# ============================================================
# FILTER
# ============================================================
st.subheader("🎛️ Filter")

f1, f2, f3, f4 = st.columns(4)

years = []
if len(db) and db["Tanggal_dt"].notna().any():
    years = sorted(
        db.loc[db["Tanggal_dt"].notna(), "Tanggal_dt"].dt.year.unique(),
        reverse=True
    )

with f1:
    selected_year = st.selectbox(
        "Tahun",
        ["Semua"] + [str(int(y)) for y in years]
    )

month_names = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}

with f2:
    selected_month = st.selectbox(
        "Bulan",
        ["Semua"] + list(month_names.values())
    )

categories = sorted([
    x for x in db["Sektor PDRB"].fillna("").astype(str).unique()
    if x.strip()
])

with f3:
    selected_category = st.selectbox(
        "Kategori / Sektor PDRB",
        ["Semua"] + categories
    )

with f4:
    selected_sentiment = st.selectbox(
        "Sentimen",
        ["Semua", "Positif", "Netral", "Negatif"]
    )

filtered = db.copy()

if selected_year != "Semua":
    filtered = filtered[
        filtered["Tanggal_dt"].dt.year == int(selected_year)
    ]

if selected_month != "Semua":
    month_number = next(
        k for k, v in month_names.items() if v == selected_month
    )
    filtered = filtered[
        filtered["Tanggal_dt"].dt.month == month_number
    ]

if selected_category != "Semua":
    filtered = filtered[
        filtered["Sektor PDRB"].astype(str) == selected_category
    ]

if selected_sentiment != "Semua":
    filtered = filtered[
        filtered["Sentimen"].astype(str) == selected_sentiment
    ]


# ============================================================
# METRIC
# ============================================================
m1, m2, m3, m4 = st.columns(4)

m1.metric("Total database", f"{len(db):,}")
m2.metric("Sesuai filter", f"{len(filtered):,}")
m3.metric(
    "Positif",
    f"{int((filtered['Sentimen'] == 'Positif').sum()):,}"
    if len(filtered) else "0"
)
m4.metric(
    "Negatif",
    f"{int((filtered['Sentimen'] == 'Negatif').sum()):,}"
    if len(filtered) else "0"
)


# ============================================================
# COLLECT MANUAL
# ============================================================
if st.button(
    "🔎 KUMPULKAN BERITA RIAU",
    type="primary",
    use_container_width=True
):
    status = st.empty()
    progress = st.progress(0, text="Menyiapkan pencarian...")

    def ui_progress(current, total):
        progress.progress(
            current / total,
            text=f"Mencari berita: {current}/{total} query"
        )

    with st.spinner("Mengumpulkan berita..."):
        result = collect_and_save(progress_callback=ui_progress)

    progress.empty()

    if result["ok"]:
        st.success(
            f"✅ {result['new']:,} berita baru disimpan. "
            f"{result['duplicates']:,} duplikat dilewati."
        )
        load_db.clear()
        st.rerun()
    else:
        st.error(f"❌ Gagal menyimpan: {result['message']}")


st.divider()


# ============================================================
# DASHBOARD
# ============================================================
if len(filtered):

    left, right = st.columns(2)

    with left:
        st.subheader("📊 Distribusi Sektor PDRB")
        sector_chart = (
            filtered["Sektor PDRB"]
            .replace("", "Belum terklasifikasi")
            .fillna("Belum terklasifikasi")
            .value_counts()
        )
        st.bar_chart(sector_chart)

    with right:
        st.subheader("😊 Sentimen")
        st.bar_chart(filtered["Sentimen"].value_counts())

    mean_score = pd.to_numeric(
        filtered["Skor Sentimen"], errors="coerce"
    ).fillna(0).mean()

    signal = round(50 + (mean_score * 50), 1)

    st.subheader("📈 Business Activity Signal Riau")
    st.metric("Signal sesuai filter", f"{signal}/100")
    st.caption(
        "Indikator berbasis sentimen berita; bukan indikator resmi BPS/PDRB."
    )

    st.subheader("📰 Berita Terbaru")

    display_df = filtered.sort_values(
        "Tanggal_dt",
        ascending=False,
        na_position="last"
    ).drop(columns=["Tanggal_dt"], errors="ignore")

    # Database boleh puluhan ribu baris, tetapi browser tidak perlu
    # merender semuanya sekaligus.
    if len(display_df) > 1000:
        st.info(
            f"Menampilkan 1.000 berita terbaru dari {len(display_df):,} "
            "hasil filter. Database lengkap tetap ada di Google Sheet."
        )
        display_df = display_df.head(1000)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=550
    )

    st.download_button(
        "⬇️ Download CSV hasil filter",
        filtered.drop(columns=["Tanggal_dt"], errors="ignore")
        .to_csv(index=False)
        .encode("utf-8-sig"),
        "berita_riau_hasil_filter.csv",
        "text/csv"
    )

else:
    st.info("Tidak ada berita sesuai filter.")

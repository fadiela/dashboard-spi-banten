"""Dashboard proyeksi SPI Banten 2026-2050 (membaca ekspor sel 14d, 14e, 14f notebook). Grafik interaktif (Plotly): arahkan kursor untuk melihat nilai.
Jalankan:  HASIL_DIR=/jalur/ke/folder streamlit run app_dashboard_spi.py
Sumber Google Drive (opsional): atur DRIVE_FOLDER_ID (env atau Streamlit secrets) = ID folder Drive yang dibagikan 'siapa saja dengan link'.
Berkas wajib: dashboard_tahunan_regional.csv, dashboard_tahunan_per_grid.csv, dashboard_meta.json (14d)
              dashboard_bulanan_regional.csv.gz, dashboard_bulanan_per_grid.csv.gz, dashboard_baseline_bulan_grid.csv.gz, dashboard_grid.csv (14e)
Berkas opsional: dashboard_korelasi.csv, dashboard_korelasi_antar.csv (14g; tab Korelasi & validasi), banten_kabkota.geojson (batas kabupaten/kota; diletakkan di folder hasil atau di sebelah berkas .py ini). Tanpa berkas ini peta tetap jalan, hanya tanpa garis batas dan nama wilayah.
"""
import html, json, os
import numpy as np, pandas as pd, streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Proyeksi kekeringan Banten 2026-2050", page_icon="🌧️", layout="wide")
st.markdown("""<style>
.kpi-grid {display: grid; gap: 12px; margin: 6px 0 12px 0;}
.kpi-grid.k4 {grid-template-columns: repeat(4, 1fr);} .kpi-grid.k3 {grid-template-columns: repeat(3, 1fr);} .kpi-grid.k2 {grid-template-columns: repeat(2, 1fr);}
@media (max-width: 900px) {.kpi-grid.k4 {grid-template-columns: repeat(2, 1fr);}}
@media (max-width: 600px) {.kpi-grid.k4, .kpi-grid.k3, .kpi-grid.k2 {grid-template-columns: 1fr;}}
.kpi {background: rgba(15,139,141,0.10); border: 1.5px solid rgba(15,139,141,0.55); border-radius: 12px; padding: 12px 14px; min-height: 104px; display: flex; flex-direction: column; justify-content: space-between;}
.kpi .l {font-size: 0.86rem; font-weight: 600; opacity: 0.85; line-height: 1.25;}
.kpi .v {font-size: 1.9rem; font-weight: 800; line-height: 1.15; margin: 4px 0;}
.kpi .s {font-size: 0.8rem; opacity: 0.75; line-height: 1.25;}
.badge {display: inline-block; padding: 3px 11px; border-radius: 999px; font-size: 0.8rem; font-weight: 600; margin: 2px 6px 2px 0; border: 1px solid;}
.badge.ok {background: rgba(46,125,50,0.14); border-color: rgba(46,125,50,0.6);} .badge.warn {background: rgba(245,124,0,0.14); border-color: rgba(245,124,0,0.7);} .badge.info {background: rgba(128,128,128,0.14); border-color: rgba(128,128,128,0.55);}
.banner {display: flex; justify-content: space-between; align-items: center; gap: 10px; border-radius: 12px; padding: 12px 16px; margin: 8px 0 12px 0; font-size: 1.02rem; line-height: 1.4; border: 1.5px solid;}
.banner.info {background: rgba(15,139,141,0.10); border-color: rgba(15,139,141,0.55);} .banner.ok {background: rgba(46,125,50,0.10); border-color: rgba(46,125,50,0.55);} .banner.warn {background: rgba(245,124,0,0.10); border-color: rgba(245,124,0,0.6);}
.find-grid {display: grid; gap: 12px; grid-template-columns: repeat(2, 1fr); margin: 4px 0 12px 0;}
@media (max-width: 700px) {.find-grid {grid-template-columns: 1fr;}}
.finding {border-left: 6px solid; border-radius: 10px; padding: 10px 14px; background: rgba(128,128,128,0.09);}
.finding.ok {border-color: #2e7d32;} .finding.warn {border-color: #f57c00;} .finding.info {border-color: #0f8b8d;}
.finding .t {font-weight: 700; margin-bottom: 2px; line-height: 1.25;} .finding .b {font-size: 0.9rem; opacity: 0.88; line-height: 1.35;}
.tip {display: inline-block; position: relative; width: 17px; height: 17px; line-height: 17px; text-align: center; border-radius: 50%; margin-left: 7px; font-size: 0.72rem; font-weight: 700; background: rgba(128,128,128,0.28); cursor: help; flex: none;}
.tip .tt {display: none; position: absolute; left: -8px; bottom: 140%; width: 270px; padding: 9px 11px; border-radius: 9px; background: #263238; color: #fff; font-size: 0.8rem; font-weight: 400; line-height: 1.4; text-align: left; z-index: 99999; box-shadow: 0 4px 14px rgba(0,0,0,0.3); white-space: normal;}
.tip:hover .tt {display: block;} .tip.r .tt {left: auto; right: -8px;}
button[data-baseweb="tab"] p {font-weight: 700; font-size: 1.02rem;}
h5 {margin-top: 0.4rem;}
</style>""", unsafe_allow_html=True)

MON = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
PRESET = {"Sepanjang tahun": list(range(1, 13)), "Des-Feb (kira-kira musim hujan)": [12, 1, 2], "Mar-Mei (peralihan)": [3, 4, 5], "Jun-Agu (kira-kira musim kemarau)": [6, 7, 8], "Sep-Nov (peralihan)": [9, 10, 11], "Pilih bulan sendiri": None}
# Warna: teal = proyeksi, abu = kondisi 1981-2010 menurut model, magenta = data pengamatan CHIRPS, oranye = tren. Biru/merah hanya dipakai di peta selisih (biru = lebih jarang kering, merah = lebih sering kering).
TEAL, TEAL_MUDA, ORANYE = "#0f8b8d", "rgba(15,139,141,0.18)", "#f57c00"
C_BASE, C_TARGET, C_ABU = "#7a7f87", "#d81b60", "#b5bac1"
GAYA = {"Peta dasar terang (disarankan)": "carto-positron", "Peta dasar gelap": "carto-darkmatter", "Peta dasar OpenStreetMap": "open-street-map", "Kotak saja (tanpa peta dasar)": None}
SKALA_INFO = {"SPI-3": ("SPI-3 · jangka pendek (3 bulan)", "Kekeringan dalam 3 bulan terakhir. Paling cepat bereaksi terhadap hujan; relevan untuk tanaman pangan."),
              "SPI-6": ("SPI-6 · menengah (6 bulan)", "Kekeringan dalam 6 bulan terakhir; gambaran satu musim penuh."),
              "SPI-12": ("SPI-12 · jangka panjang (12 bulan)", "Kekeringan dalam 12 bulan terakhir. Lambat berubah; relevan untuk air tanah, sungai, dan waduk.")}
KATEGORI_SPI = pd.DataFrame({"Nilai SPI": ["2,0 atau lebih", "1,5 sampai 1,99", "1,0 sampai 1,49", "-0,99 sampai 0,99", "-1,0 sampai -1,49", "-1,5 sampai -1,99", "-2,0 atau kurang"],
                             "Kategori": ["Sangat basah (ekstrem)", "Sangat basah", "Cukup basah", "Normal", "Kering", "Sangat kering", "Kering ekstrem"],
                             "Dihitung 'kering' di dashboard?": ["Tidak", "Tidak", "Tidak", "Tidak", "Ya", "Ya (juga 'sangat kering')", "Ya (juga 'sangat kering')"]})

# Pita warna kategori SPI untuk grafik deret: (batas bawah, batas atas, warna, nama)
PITA_SPI = [(-9, -2, "#8e0000", "Kering ekstrem"), (-2, -1.5, "#e53935", "Sangat kering"), (-1.5, -1, "#fb8c00", "Kering"), (-1, 1, None, "Normal"),
            (1, 1.5, "#9ccc65", "Cukup basah"), (1.5, 2, "#43a047", "Sangat basah"), (2, 9, "#1b5e20", "Basah ekstrem")]
WARNA_PETA = {"pos": ("YlOrRd", None, "%", "Frekuensi kering"), "pp": ("RdBu_r", 0, " poin", "Selisih vs 1981-2010"), "spi": ("BrBG", 0, "", "SPI median")}

# ---------------- sumber data ----------------
def ambil_drive_id():
    v = os.environ.get("DRIVE_FOLDER_ID")
    if v: return v
    try: return st.secrets["DRIVE_FOLDER_ID"]
    except Exception: return None

@st.cache_data(ttl=600, show_spinner="Mengambil data terbaru dari Google Drive...")
def sinkron_drive(folder_id):
    import gdown, tempfile
    tujuan = os.path.join(tempfile.gettempdir(), "spi_drive_" + folder_id)
    gdown.download_folder(id=folder_id, output=tujuan, quiet=True, use_cookies=False)
    return tujuan

def versi_folder(folder):
    try: return tuple(sorted((n, os.path.getmtime(os.path.join(folder, n))) for n in os.listdir(folder) if n.startswith("dashboard_") or n.endswith(".geojson")))
    except OSError: return ()

def jalur(folder, nama):
    """Jalur berkas; toleran terhadap nama 'xxx_csv.gz' (sebagian layanan unggah mengganti titik dengan garis bawah)."""
    p = os.path.join(folder, nama)
    if os.path.exists(p): return p
    alt = os.path.join(folder, nama.replace(".csv.gz", "_csv.gz"))
    return alt if os.path.exists(alt) else p

folder_awal, sumber = os.environ.get("HASIL_DIR", "."), "folder lokal / repo"
drive_id = ambil_drive_id()
if drive_id:
    try: folder_awal, sumber = sinkron_drive(drive_id), "Google Drive (disegarkan tiap 10 menit)"
    except Exception as e: st.sidebar.warning(f"Gagal mengambil dari Google Drive ({type(e).__name__}); memakai berkas lokal.")

# Sidebar: pilihan utama di atas, pengaturan teknis dilipat di bawah. Wadah dibuat dulu supaya urutannya tetap walau isinya diisi belakangan.
slot_skala = st.sidebar.container()
with st.sidebar.expander("Pengaturan lanjutan"):
    gaya_nama = st.radio("Gaya peta", list(GAYA), index=0, help="Peta dasar memuat ubin dari internet. Pilih 'Kotak saja' bila peta dasar tidak tampil.")
    folder = st.text_input("Folder hasil (berisi dashboard_*.csv)", value=folder_awal)
    st.caption(f"Sumber data: {sumber}")
    if st.button("Muat ulang data sekarang"): st.cache_data.clear(); st.rerun()
gaya = GAYA[gaya_nama]

@st.cache_data
def muat(folder, versi=()):
    reg = pd.read_csv(jalur(folder, "dashboard_tahunan_regional.csv")); grd = pd.read_csv(jalur(folder, "dashboard_tahunan_per_grid.csv"))
    meta = json.load(open(jalur(folder, "dashboard_meta.json"), encoding="utf-8"))
    return reg, grd, meta

@st.cache_data
def muat_bulanan(folder, versi=()):
    nama = ("dashboard_bulanan_regional.csv.gz", "dashboard_bulanan_per_grid.csv.gz", "dashboard_baseline_bulan_grid.csv.gz", "dashboard_grid.csv")
    if not all(os.path.exists(jalur(folder, n)) for n in nama): return None
    return tuple(pd.read_csv(jalur(folder, n)) for n in nama)

@st.cache_data
def muat_korelasi(folder, versi=()):
    pk, pa = os.path.join(folder, "dashboard_korelasi.csv"), os.path.join(folder, "dashboard_korelasi_antar.csv")
    if not os.path.exists(pk): return None, None
    return pd.read_csv(pk), (pd.read_csv(pa) if os.path.exists(pa) else None)

def _dalam_cincin(px, py, ring):
    """Uji titik-dalam-poligon (even-odd) untuk banyak titik sekaligus; ring = array (n, 2) berisi bujur, lintang."""
    x, y = ring[:, 0], ring[:, 1]; x2, y2 = np.roll(x, -1), np.roll(y, -1); dalam = np.zeros(px.shape, bool)
    for xi, yi, xj, yj in zip(x, y, x2, y2):
        if yi == yj: continue
        dalam ^= ((yi > py) != (yj > py)) & (px < (xj - xi) * (py - yi) / (yj - yi) + xi)
    return dalam

def _poligon_fitur(geom):
    return [geom["coordinates"]] if geom["type"] == "Polygon" else list(geom["coordinates"]) if geom["type"] == "MultiPolygon" else []

@st.cache_data
def muat_wilayah(folder, versi, grid_ref):
    """Batas kabupaten/kota (opsional) dan pemetaan grid -> nama wilayah. Mengembalikan (geojson atau None, DataFrame grid_id/wilayah/pusat label)."""
    for d in (folder, os.path.dirname(os.path.abspath(__file__))):
        p = os.path.join(d, "banten_kabkota.geojson")
        if os.path.exists(p):
            gj = json.load(open(p, encoding="utf-8")); px, py = grid_ref["lon"].to_numpy(float), grid_ref["lat"].to_numpy(float); nama = np.full(len(grid_ref), None, dtype=object); label = []
            for f in gj["features"]:
                pr = f.get("properties", {}); nm = next((pr[k] for k in ("nama", "NAME_2", "name", "NAMOBJ", "WADMKK") if k in pr), str(f.get("id", "?"))); f["id"] = nm
                dalam = np.zeros(len(px), bool); besar = None
                for poly in _poligon_fitur(f["geometry"]):
                    ext = np.asarray(poly[0], float); m = _dalam_cincin(px, py, ext)
                    for hole in poly[1:]: m &= ~_dalam_cincin(px, py, np.asarray(hole, float))
                    dalam |= m
                    luas = np.ptp(ext[:, 0]) * np.ptp(ext[:, 1])
                    if besar is None or luas > besar[0]: besar = (luas, ext[:, 0].mean(), ext[:, 1].mean())
                nama[dalam & (nama == None)] = nm       # noqa: E711  (elementwise terhadap array object)
                if besar: label.append((nm, besar[1], besar[2]))
            return gj, pd.DataFrame({"grid_id": grid_ref["grid_id"].to_numpy(), "wilayah": nama}), pd.DataFrame(label, columns=["nama", "lon", "lat"])
    return None, pd.DataFrame({"grid_id": grid_ref["grid_id"].to_numpy(), "wilayah": None}), pd.DataFrame(columns=["nama", "lon", "lat"])

try:
    reg, grd, meta = muat(folder, versi_folder(folder))
except FileNotFoundError as e:
    st.error(f"Berkas ekspor tidak ditemukan di '{folder}'. Jalankan sel 14d notebook dulu. ({e.filename})"); st.stop()
bln = muat_bulanan(folder, versi_folder(folder))
kor, kor_antar = muat_korelasi(folder, versi_folder(folder))
grid_ref = grd[["grid_id", "lat", "lon"]].drop_duplicates().sort_values("grid_id").reset_index(drop=True)
gj, wil_tab, wil_label = muat_wilayah(folder, versi_folder(folder), grid_ref)

# ---------------- pembantu teks dan angka ----------------
def n(x, d=1, plus=False):
    """Format angka gaya Indonesia (koma desimal)."""
    s = f"{x:+.{d}f}" if plus else f"{x:.{d}f}"
    return s.replace(".", ",")

def tafsir(selisih, se):
    """Menafsirkan selisih (poin persentase) terhadap kondisi 1981-2010. 'se' = galat baku kasar dari naik-turun antar-tahun. Aturan praktis: selisih dianggap berarti bila > 2 x galat baku."""
    if not np.isfinite(se): return "sedikit", "Terlalu sedikit tahun untuk disimpulkan: satu atau dua tahun hanyalah satu-dua realisasi model, bukan ramalan dan bukan tren."
    if abs(selisih) < 2 * se: return "sama", "Selisihnya kecil dan masih dalam kisaran naik-turun alami antar-tahun, jadi belum menunjukkan perubahan yang berarti."
    return ("lebih", "Bulan kering diproyeksikan lebih sering daripada kondisi 1981-2010.") if selisih > 0 else ("kurang", "Bulan kering diproyeksikan lebih jarang daripada kondisi 1981-2010.")

KET_KODE = {"sama": "belum berarti", "lebih": "lebih sering kering", "kurang": "lebih jarang kering", "sedikit": "data terlalu sedikit"}

def se_kasar(serie):
    s = pd.Series(serie).dropna(); return float(s.std(ddof=1) / np.sqrt(len(s))) if len(s) >= 3 else float("nan")

def _tip(tip, kanan=False):
    """Ikon '?' kecil; teks muncul saat kursor diarahkan. kanan=True untuk elemen di tepi kanan supaya tooltip tidak terpotong."""
    return f'<span class="tip{" r" if kanan else ""}">?<span class="tt">{html.escape(str(tip))}</span></span>' if tip else ""

def kartu(label, nilai, sub="", tip="", kanan=False):
    e = html.escape
    return f'<div class="kpi"><div class="l">{e(str(label))}{_tip(tip, kanan)}</div><div class="v">{e(str(nilai))}</div><div class="s">{e(str(sub)) if sub else "&nbsp;"}</div></div>'

def kpi_grid(daftar, kolom=4):
    st.markdown(f'<div class="kpi-grid k{kolom}">' + "".join(daftar) + "</div>", unsafe_allow_html=True)

def kartu_temuan(judul_, isi, tip, jenis="info", kanan=False):
    e = html.escape
    return f'<div class="finding {jenis}"><div class="t">{e(judul_)}{_tip(tip, kanan)}</div><div class="b">{e(isi)}</div></div>'

def lencana(teks, jenis="ok", tip=""):
    return f'<span class="badge {jenis}">{html.escape(teks)}{_tip(tip)}</span>'

def banner(teks_html, tip="", jenis="info"):
    st.markdown(f'<div class="banner {jenis}"><span>{teks_html}</span>{_tip(tip, True)}</div>', unsafe_allow_html=True)

def judul(teks, bantuan=None):
    """Judul bagian dengan ikon '?' bawaan Streamlit (teks bantuan muncul saat kursor diarahkan)."""
    st.markdown(f"##### {teks}", help=bantuan)

# ---------------- pembantu grafik ----------------
def tampil(fig, tinggi=420, bawah=10, atas=24):
    fig.update_layout(height=tinggi, margin=dict(l=10, r=10, t=atas, b=bawah), legend=dict(orientation="h", y=-0.2, x=0, font=dict(size=12)), font=dict(size=13), separators=",.", hoverlabel=dict(font_size=13))
    fig.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,0.22)", linecolor="rgba(128,128,128,0.8)", linewidth=1.2, ticks="outside", tickfont=dict(size=12))
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.22)", linecolor="rgba(128,128,128,0.8)", linewidth=1.2, ticks="outside", tickfont=dict(size=12))
    cfg = dict(displaylogo=False, toImageButtonOptions=dict(scale=2))
    try: st.plotly_chart(fig, width="stretch", config=cfg)
    except TypeError: st.plotly_chart(fig, use_container_width=True, config=cfg)

def garis_acuan(fig, x, nilai, nama, warna, dash):
    fig.add_trace(go.Scatter(x=[min(x), max(x)], y=[nilai, nilai], mode="lines", name=nama, line=dict(color=warna, dash=dash, width=2.5), hovertemplate=f"{nama}: {nilai:.1f}%<extra></extra>"))

def batas_skala(v, mode):
    """Batas skala warna mengikuti sebaran data (persentil ke-98) supaya peta tidak jenuh saat hanya sedikit tahun dipilih."""
    v = pd.Series(v).dropna().to_numpy()
    if v.size == 0: return 0, 1
    if mode == "pos": return 0, max(20.0, float(np.ceil(np.percentile(v, 98) / 10) * 10))
    m = float(np.percentile(np.abs(v), 98))
    if mode == "pp": lim = max(5.0, float(np.ceil(m / 5) * 5))
    else: lim = max(0.5, float(np.ceil(m * 4) / 4))
    return -lim, lim

def kotak_geojson(df, h):
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "id": str(int(g)), "properties": {}, "geometry": {"type": "Polygon", "coordinates": [[[lo - h, la - h], [lo + h, la - h], [lo + h, la + h], [lo - h, la + h], [lo - h, la - h]]]}}
                                                      for g, lo, la in zip(df["grid_id"], df["lon"], df["lat"])]}

def garis_batas_xy(gj):
    """Garis batas wilayah sebagai satu deret (x, y) dengan None sebagai pemisah, untuk peta tanpa peta dasar."""
    xs, ys = [], []
    for f in gj["features"]:
        for poly in _poligon_fitur(f["geometry"]):
            for ring in poly: a = np.asarray(ring, float); xs += a[:, 0].tolist() + [None]; ys += a[:, 1].tolist() + [None]
    return xs, ys

def peta(df, kol, judul, warna, zmin, zmax, satuan, label, extra=(), zmid=None, gaya="carto-positron"):
    """Peta grid interaktif. gaya = nama gaya peta dasar atau None untuk kotak saja. extra = [(judul, kolom, satuan), ...] untuk tooltip. Bila df punya kolom 'wilayah' dan batas tersedia, nama wilayah tampil di tooltip."""
    lon, lat = df["lon"].round(4).to_numpy(), df["lat"].round(4).to_numpy(); xs, ys = np.unique(lon), np.unique(lat)
    h = float(np.median(np.diff(xs)) / 2) if len(xs) > 1 else 0.025
    judul_cb = satuan.strip() or None; ada_w = "wilayah" in df.columns
    tip = ("<b>%{text}</b><br>" if ada_w else "") + "Bujur %{customdata[0]:.3f}, Lintang %{customdata[1]:.3f}<br><b>" + label + ": %{z:.1f}" + satuan + "</b>"
    for i, (jd, _, sat) in enumerate(extra): tip += f"<br>{jd}: %{{customdata[{i + 2}]:.1f}}{sat}"
    if gaya and hasattr(go, "Choroplethmap"):
        cd = np.c_[lon, lat, df[[k for _, k, _ in extra]].to_numpy()] if extra else np.c_[lon, lat]
        teks = df["wilayah"].fillna("Di luar batas kab/kota (laut atau provinsi lain)").to_numpy() if ada_w else None
        tr = go.Choroplethmap(geojson=kotak_geojson(df.assign(lon=lon, lat=lat), h), locations=df["grid_id"].astype(int).astype(str), z=df[kol], customdata=cd, text=teks, colorscale=warna, zmin=zmin, zmax=zmax, zmid=zmid,
                              marker=dict(opacity=0.88, line=dict(width=0.4, color="white")), hovertemplate=tip + "<extra></extra>", colorbar=dict(title=judul_cb))
        fig = go.Figure(tr); zoom = float(np.clip(np.log2(500 / 256 * 360 / (max(xs.max() - xs.min(), 0.2) * 1.2)) - 0.1, 5, 11))
        lay = dict(style=gaya, center=dict(lat=float((ys.min() + ys.max()) / 2), lon=float((xs.min() + xs.max()) / 2)), zoom=zoom)
        if gj is not None: lay["layers"] = [dict(sourcetype="geojson", source=gj, type="line", color="#263238", line=dict(width=1.8), below="")]
        fig.update_layout(map=lay)
        if gj is not None and len(wil_label) and hasattr(go, "Scattermap"):
            fig.add_trace(go.Scattermap(lon=wil_label["lon"], lat=wil_label["lat"], mode="text", text=wil_label["nama"], textfont=dict(size=12, color="#263238"), hoverinfo="skip", showlegend=False))
    else:
        tip2 = tip.replace("%{customdata[0]:.3f}", "%{x:.3f}").replace("%{customdata[1]:.3f}", "%{y:.3f}").replace("<b>%{text}</b><br>", "")
        if len(xs) * len(ys) <= 6 * len(df):                                       # grid teratur -> kotak per sel
            ix, iy = np.searchsorted(xs, lon), np.searchsorted(ys, lat)
            def mat(k): m = np.full((len(ys), len(xs)), np.nan); m[iy, ix] = df[k].to_numpy(); return m
            cd = np.dstack([np.zeros_like(mat(kol)), np.zeros_like(mat(kol))] + [mat(k) for _, k, _ in extra])
            tr = go.Heatmap(x=xs, y=ys, z=mat(kol), customdata=cd, colorscale=warna, zmin=zmin, zmax=zmax, zmid=zmid, hoverongaps=False, hovertemplate=tip2 + "<extra></extra>", colorbar=dict(title=judul_cb))
        else:                                                                      # cadangan bila grid tidak teratur
            cd = np.c_[lon, lat, df[[k for _, k, _ in extra]].to_numpy()] if extra else np.c_[lon, lat]
            tr = go.Scatter(x=lon, y=lat, mode="markers", customdata=cd, marker=dict(symbol="square", size=10, color=df[kol], colorscale=warna, cmin=zmin, cmax=zmax, cmid=zmid, colorbar=dict(title=judul_cb)),
                            hovertemplate=tip2.replace("%{z", "%{marker.color") + "<extra></extra>")
        fig = go.Figure(tr); fig.update_layout(xaxis_title="bujur", yaxis_title="lintang"); fig.update_yaxes(scaleanchor="x", scaleratio=1)
        if gj is not None:
            bx, by = garis_batas_xy(gj); fig.add_trace(go.Scatter(x=bx, y=by, mode="lines", line=dict(color="#263238", width=1.5), hoverinfo="skip", showlegend=False))
    fig.update_layout(title=dict(text=judul, font=dict(size=13)) if judul else None)
    return fig

# ---------------- kepala halaman ----------------
h0, h1 = int(meta["horizon"][0]), int(meta["horizon"][1])
TIP_SKALA = ("SPI membandingkan hujan suatu periode dengan hujan biasanya. Kering = SPI <= -1.\n\n**SPI-3** jangka pendek (3 bulan), relevan untuk tanaman. **SPI-6** menengah (satu musim). **SPI-12** jangka panjang, relevan untuk air tanah dan waduk.")
TIP_UTAMA = ("**Cara membaca (30 detik).** Grafik membandingkan seberapa sering bulan kering (SPI <= -1) diproyeksikan dengan kondisi 1981-2010 menurut model yang sama. "
             "Satu tahun bukan ramalan; lihat kecenderungan banyak tahun. Ini proyeksi bersyarat dari satu model iklim dan satu skenario.\n\nArahkan kursor ke ikon ? di tiap bagian untuk penjelasan.")
with slot_skala:
    skala = st.radio("Skala kekeringan (SPI)", meta["spi_skala"], index=0, format_func=lambda s: SKALA_INFO.get(s, (s, ""))[0], help=TIP_SKALA)

SK = {}                                                   # ringkasan per skala SPI: proyeksi, baseline, selisih, galat baku kasar, kode tafsir
for s_ in meta["spi_skala"]:
    d_ = reg[reg["SPI"] == s_].sort_values("tahun"); kol_ = "kering_pct_mean" if "kering_pct_mean" in d_.columns else "kering_pct_median"; p_ = (meta.get("proyeksi_pct") or {}).get(s_)
    p_ = float(p_) if p_ is not None else float(np.average(d_[kol_], weights=d_["n_bulan_valid"])); b_ = float(meta["baseline_model_sendiri_pct"][s_]); se_ = se_kasar(d_[kol_])
    SK[s_] = dict(proy=p_, base=b_, sel=p_ - b_, se=se_, kode=tafsir(p_ - b_, se_)[0])
r = reg[reg["SPI"] == skala].sort_values("tahun"); base = SK[skala]["base"]; acuan = float(meta["acuan_target_pct"][skala]); rata, sel, kode = SK[skala]["proy"], SK[skala]["sel"], SK[skala]["kode"]
KOL_RATA = "kering_pct_mean" if "kering_pct_mean" in r.columns else "kering_pct_median"; kalimat = tafsir(sel, SK[skala]["se"])[1]

st.title(f"Proyeksi kekeringan Banten {h0}-{h1}", help=TIP_UTAMA)
st.caption(f"{meta['gcm']} · {meta['skenario']} · model {meta['model']} · target {meta['target']}")
lolos = str(meta["status_gerbang"]).startswith("lolos")
if not lolos: st.warning(f"Status model: **{meta['status_gerbang']}**. Belum lolos gerbang penuh; baca sebagai proyeksi bersyarat.")
lr_ = meta.get("baris_prediktor_luar_rentang_pct") or {}; luar = lr_.get(f"{h0}-{h1}", next(iter(lr_.values()), None)) if lr_ else None
b_html = lencana("Lolos uji penuh" if lolos else "Belum lolos uji penuh", "ok" if lolos else "warn", "Model lolos tiga syarat uji (a, b, c) yang ditetapkan sebelum hasil dilihat. Rincian ada di tab Panduan." if lolos else "Model belum lolos semua syarat uji; baca sebagai sensitivitas.")
if luar is not None: b_html += lencana(f"Di luar rentang latih: {luar:.0f}%", "ok" if luar < 20 else "warn", "Persentase data masukan GCM yang nilainya di luar rentang yang dilihat model saat dilatih (ERA5). Makin tinggi, makin kurang bisa dipercaya.")
b_html += lencana(f"1 GCM · 1 skenario · {meta['n_anggota_ensemble']} simulasi", "info", "Hasil bersyarat pada satu model iklim dan satu skenario. Simulasi hanya derau acak di sekitar nilai tengah yang sama, bukan ukuran ketidakpastian iklim.")
st.markdown(b_html, unsafe_allow_html=True)

tab1, tab2, tab_k, tab3 = st.tabs(["Ringkasan", "Peta & musim", "Korelasi & validasi", "Panduan"])

# ---------------- tab 1: ringkasan ----------------
with tab1:
    banner(f"<b>{skala}:</b> {n(rata)}% bulan kering diproyeksikan ({h0}-{h1}) vs {n(base)}% pada 1981-2010 · selisih <b>{n(sel, 1, True)} poin</b> ({KET_KODE[kode]})",
           f"{kalimat} Kering = SPI <= -1. Poin = selisih dua persentase (15% ke 17% = 2 poin). Proyeksi bersyarat dari satu model iklim dan satu skenario, bukan ramalan.")
    # ---- temuan utama (otomatis dari data; kartu hanya muncul bila datanya ada) ----
    cards = []
    n_berarti = sum(v["kode"] in ("lebih", "kurang") for v in SK.values()); campur = len({int(np.sign(v["sel"])) for v in SK.values()}) > 1
    rinci = " · ".join(f"{s_} {n(v['sel'], 1, True)}" for s_, v in SK.items()) + " poin"
    j1 = "Belum ada perubahan berarti" if n_berarti == 0 else "Perubahan searah di semua skala" if (n_berarti == len(SK) and not campur) else "Hanya sebagian skala berubah berarti"
    cards.append(kartu_temuan(j1, rinci, "Selisih frekuensi bulan kering terhadap 1981-2010 untuk tiap skala SPI. " + ("Semuanya masih dalam kisaran naik-turun alami antar-tahun" if n_berarti == 0 else f"{n_berarti} dari {len(SK)} skala melewati kisaran naik-turun alami") + (", dan arahnya tidak seragam antar skala." if campur else "."), "info"))
    if kor is not None:
        ng = int(kor["lolos_fdr_gcm_target"].sum()); nmod = int(kor["lolos_fdr_model_t1"].sum()) if "lolos_fdr_model_t1" in kor.columns else None
        cards.append(kartu_temuan("GCM mentah tidak sefase dengan kenyataan" if ng == 0 else "Sebagian korelasi GCM nyata", f"Korelasi nyata: GCM {ng}/{len(kor)}" + (f" · model ERA5 {nmod}/{len(kor)}" if nmod is not None else ""),
                                  f"Dari {len(kor)} uji korelasi (12 bulan, 4 musim, tahunan) dengan {meta['target']}, hanya {ng} untuk hujan GCM yang lolos koreksi uji berganda. GCM berjalan bebas, jadi kejadiannya tidak sefase dengan dunia nyata. Karena itu proyeksi memakai model yang dilatih dengan data ERA5.", "ok" if ng == 0 else "info", True))
    ka = meta.get("konsistensi_arah")
    if ka and ka.get("jendela"):
        lap = next((j for j in ka["jendela"] if j.get("peran") == "dilaporkan"), ka["jendela"][0]); nb_ = sum(bool(j["berlawanan"]) for j in ka["jendela"])
        cards.append(kartu_temuan("Arah berlawanan dengan GCM" if lap["berlawanan"] else "Arah searah dengan GCM", f"Hujan GCM {n(lap['gcm_pr_mentah_pct'], 1, True)}% · model {n(lap['model_pct'], 1, True)}% ({lap['jendela']})",
                                  f"Perubahan hujan rata-rata wilayah: GCM mentah vs model. Berlawanan di {nb_} dari {len(ka['jendela'])} jendela waktu. " + ("Sebabnya belum dibuktikan; baca arah perubahan sebagai bersyarat pada model, bukan temuan iklim." if lap["berlawanan"] else "Arah ini konsisten dengan sinyal GCM."), "warn" if lap["berlawanan"] else "ok"))
    if lr_:
        cards.append(kartu_temuan(f"Keandalan turun setelah {h1}", "Di luar rentang latih: " + " → ".join(f"{v:.0f}%" for v in lr_.values()), "Persentase data masukan GCM di luar rentang latih ERA5 pada jendela " + ", ".join(lr_.keys()) + f". Karena itu hasil hanya dilaporkan sampai {h1}.", "warn" if max(lr_.values()) >= 50 else "info", True))
    judul("Temuan utama", "Ringkasan otomatis dari hasil. Untuk membandingkan skala, wilayah, dan musim sebagai skenario bersyarat dari satu model; bukan untuk meramal tahun tertentu atau menyimpulkan tren iklim Banten.")
    st.markdown('<div class="find-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)
    kpi_grid([kartu(f"Bulan kering {h0}-{h1}", f"{n(rata)}%", "rata-rata simulasi", "Rata-rata semua simulasi dan tahun. Bulan kering = SPI <= -1 pada satu petak peta."),
              kartu("Kondisi 1981-2010", f"{n(base)}%", "menurut model", "Baseline: seberapa sering model yang sama menghasilkan bulan kering pada 1981-2010. Pembanding utama karena model punya bias sendiri; membandingkan model dengan model meniadakan bias itu."),
              kartu("Selisih", f"{n(sel, 1, True)} poin", KET_KODE[kode], "Proyeksi dikurangi kondisi 1981-2010 (model). Dianggap berarti bila lebih dari 2x galat baku kasar naik-turun antar-tahun.", True)], 3)

    judul("Tiga skala SPI", "Selisih frekuensi bulan kering terhadap 1981-2010. Merah = lebih sering kering, biru = lebih jarang. Garis tegak = ±2 galat baku kasar naik-turun antar-tahun; bila menyentuh nol, perubahan belum berarti.")
    sk_n = list(SK); fig = go.Figure(go.Bar(x=[f"{s_}<br>{n(SK[s_]['sel'], 1, True)} poin" for s_ in sk_n], y=[SK[s_]["sel"] for s_ in sk_n], marker_color=["#e57373" if SK[s_]["sel"] > 0 else "#64b5f6" for s_ in sk_n],
                           error_y=dict(type="data", array=[2 * SK[s_]["se"] if np.isfinite(SK[s_]["se"]) else 0 for s_ in sk_n], color="#555", thickness=2, width=9), customdata=[[SK[s_]["proy"], SK[s_]["base"], KET_KODE[SK[s_]["kode"]]] for s_ in sk_n],
                           hovertemplate="proyeksi %{customdata[0]:.1f}% vs 1981-2010 %{customdata[1]:.1f}%<br>%{customdata[2]}<extra></extra>"))
    fig.add_hline(y=0, line_color="#555", line_width=1.5); fig.update_layout(yaxis_title="selisih (poin)", showlegend=False); tampil(fig, 300)

    inc = (r["n_bulan_valid"] < 12).to_numpy(); roll = r.set_index("tahun")["kering_pct_median"].rolling(5, center=True, min_periods=3).mean()
    tip_th = ("Titik teal di atas garis abu-abu = tahun itu lebih sering kering dari 1981-2010. Satu tahun = satu realisasi model, bukan ramalan. Garis oranye = kecenderungan (rata-rata 5 tahun). Pita = sebaran antar simulasi, bukan ketidakpastian iklim. Garis teal = median simulasi; angka ringkasan = rata-rata semua simulasi."
              + (" Penanda berlubang = tahun awal dengan sebagian bulan kosong: " + ", ".join(f"{int(t)} ({int(k)} bulan)" for t, k in r.loc[r["n_bulan_valid"] < 12, ["tahun", "n_bulan_valid"]].to_numpy()) + "." if inc.any() else ""))
    judul("Bulan kering per tahun", tip_th)
    c1, c2 = st.columns(2); pita = c1.toggle("Sebaran simulasi", value=True, help="Pita p10-p90 antar simulasi."); tampil_obs = c2.toggle(f"Bandingkan {meta['target']}", value=False, help=f"Tambahkan garis kondisi 1981-2010 dari data pengamatan {meta['target']}.")
    fig = go.Figure()
    if pita:
        fig.add_trace(go.Scatter(x=r["tahun"], y=r["kering_pct_p10"], mode="lines", line=dict(width=0), name="p10", showlegend=False, hovertemplate="p10: %{y:.1f}%<extra></extra>"))
        fig.add_trace(go.Scatter(x=r["tahun"], y=r["kering_pct_p90"], mode="lines", line=dict(width=0), fill="tonexty", fillcolor=TEAL_MUDA, name="sebaran simulasi", hovertemplate="p90: %{y:.1f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=r["tahun"], y=r["kering_pct_median"], mode="lines+markers", line=dict(color=TEAL, width=3.5), marker=dict(size=9, symbol=np.where(inc, "circle-open", "circle").tolist()), customdata=r["n_bulan_valid"], name="proyeksi", hovertemplate="<b>proyeksi: %{y:.1f}%</b> (%{customdata} bulan valid)<extra></extra>"))
    fig.add_trace(go.Scatter(x=roll.index, y=roll.values, mode="lines", line=dict(color=ORANYE, width=3, dash="dashdot"), name="tren 5 tahun", hovertemplate="rata-rata 5 tahun: %{y:.1f}%<extra></extra>"))
    garis_acuan(fig, r["tahun"], base, "1981-2010 (model)", C_BASE, "dot")
    if tampil_obs: garis_acuan(fig, r["tahun"], acuan, f"1981-2010 ({meta['target']})", C_TARGET, "dash")
    fig.update_layout(hovermode="x unified", xaxis_title="tahun", yaxis_title="% bulan kering"); tampil(fig, 380)

    judul("Dua periode", "Apakah paruh kedua lebih kering dari paruh pertama? Geser tahun pemisah. Berasal dari satu lintasan model iklim, jadi bisa dipengaruhi variasi alami model (mirip ENSO); jangan dibaca sebagai kepastian tren.")
    mid_def = h0 + (h1 - h0 + 1) // 2; pisah = st.slider("Pisah di tahun", h0 + 3, h1 - 3, mid_def, help="Periode awal = sampai tahun sebelum tahun ini; periode akhir = mulai tahun ini.")
    ra, rb = r[r["tahun"] < pisah], r[r["tahun"] >= pisah]
    ma, mb_ = float(np.average(ra[KOL_RATA], weights=ra["n_bulan_valid"])), float(np.average(rb[KOL_RATA], weights=rb["n_bulan_valid"]))
    k2, _ = tafsir(mb_ - ma, float(np.sqrt(se_kasar(ra[KOL_RATA]) ** 2 + se_kasar(rb[KOL_RATA]) ** 2))); la, lb = f"{h0}-{pisah - 1}", f"{pisah}-{h1}"
    fig = go.Figure(go.Bar(x=["1981-2010 (model)", la, lb], y=[base, ma, mb_], marker_color=[C_BASE, "#5bb5b6", TEAL], text=[f"{n(v)}%" for v in (base, ma, mb_)], textposition="outside", cliponaxis=False, hovertemplate="%{x}<br><b>%{y:.1f}%</b> bulan kering<extra></extra>"))
    fig.update_layout(yaxis_title="% bulan kering", yaxis_range=[0, max(base, ma, mb_) * 1.25], showlegend=False); tampil(fig, 300)
    st.markdown(f"**{lb}: {n(mb_)}%** vs **{la}: {n(ma)}%** · selisih **{n(mb_ - ma, 1, True)} poin** ({KET_KODE[k2]})")

    dl = r[[c for c in ["tahun", "n_bulan_valid", "kering_pct_p10", "kering_pct_mean", "kering_pct_median", "kering_pct_p90", "spi_rata2_median"] if c in r.columns]].rename(columns={"n_bulan_valid": "jumlah_bulan_valid", "kering_pct_p10": "bulan_kering_pct_p10", "kering_pct_mean": "bulan_kering_pct_rata2", "kering_pct_median": "bulan_kering_pct_median", "kering_pct_p90": "bulan_kering_pct_p90"})
    st.download_button("Unduh tabel tahunan (CSV)", dl.to_csv(index=False).encode("utf-8-sig"), file_name=f"proyeksi_kering_banten_{skala}.csv", mime="text/csv")
    with st.expander("Detail untuk peneliti: ketiga skala dan pembanding pengamatan"):
        rows = [{"Skala": s, f"Proyeksi {h0}-{h1} (%)": round(v["proy"], 1), "Baseline model 1981-2010 (%)": round(v["base"], 1), f"Acuan {meta['target']} 1981-2010 (%)": round(float(meta["acuan_target_pct"][s]), 1), "Proyeksi - baseline model (poin)": round(v["sel"], 1)} for s, v in SK.items()]
        judul("Perbandingan tiga skala", "Baca perubahan terhadap baseline model sendiri (kolom ke-3), bukan terhadap data pengamatan, karena model punya bias tersendiri.")
        st.dataframe(pd.DataFrame(rows).set_index("Skala"))

# ---------------- tab 2: peta & musim ----------------
KET_PETA = {"Seberapa sering kering (%)": ("Frekuensi kering", "pos"), "Dibanding 1981-2010 (poin)": ("Selisih", "pp"), "SPI rata-rata": ("SPI", "spi")}
TIP_PETA = {"pos": "Makin merah = makin sering bulan kering di grid itu.", "pp": "Merah = lebih sering kering daripada 1981-2010, biru = lebih jarang, putih = sama.", "spi": "Coklat = cenderung kering, hijau = cenderung basah (SPI 0 = normal)."}
with tab2:
    if bln is None:
        st.info("Ekspor bulanan belum ada, jadi hanya peta per tahun yang tersedia.")
        gt_ = sorted(grd["tahun"].unique().tolist()); tahun = st.select_slider("Tahun", gt_, value=gt_[0]); g = grd[(grd["SPI"] == skala) & (grd["tahun"] == tahun)].dropna(subset=["kering_pct"]).merge(wil_tab, on="grid_id", how="left")
        if g.empty: st.warning("Tidak ada nilai untuk pilihan ini.")
        else: tampil(peta(g, "kering_pct", "", "YlOrRd", 0, 100, "%", "% bulan kering", gaya=gaya), 540)
    else:
        regm, grdm, basem, grid = bln
        regm, grdm, basem = (d[d["SPI"] == skala] for d in (regm, grdm, basem)); grid = grid.merge(wil_tab, on="grid_id", how="left")
        daftar_th = sorted(regm["tahun"].unique().tolist())
        kp, kr = st.columns([1, 2], gap="medium")
        with kp:
            with st.container(border=True):
                st.markdown("**Pilihan**")
                th0, th1 = st.select_slider("Rentang tahun", daftar_th, value=(daftar_th[0], daftar_th[-1]), help="Geser kedua ujung ke tahun yang sama untuk melihat satu tahun saja.")
                tahun_pilih = [t for t in daftar_th if th0 <= t <= th1]
                pilih = st.selectbox("Bulan atau musim", list(PRESET), help="Musim di Banten hanya perkiraan kasar. Pilih 'Pilih bulan sendiri' untuk bulan tertentu.")
                bulan = PRESET[pilih] if PRESET[pilih] is not None else [MON.index(m) + 1 for m in st.multiselect("Pilih bulan", MON, default=MON[5:9], key="bulan_multi")]
                ket = st.radio("Tampilkan di peta", list(KET_PETA), help="Frekuensi kering = % bulan kering. Selisih = dibanding 1981-2010 menurut model. SPI rata-rata = nilai SPI median.")
                dalam_saja = st.toggle("Hanya grid dalam batas Banten", value=False, disabled=gj is None, help="Grid berbentuk kotak sehingga sebagian berada di laut atau provinsi tetangga. Bila aktif, angka di tab ini hanya dari grid dalam batas; tab Ringkasan memakai semua grid." if gj is not None else "Perlu berkas banten_kabkota.geojson.")
        gs = grdm[grdm["tahun"].isin(tahun_pilih) & grdm["bulan"].isin(bulan)] if (bulan and tahun_pilih) else grdm.iloc[0:0]
        if gs.empty:
            with kr:
                if not bulan: st.warning("Pilih minimal satu bulan.")
                elif not tahun_pilih: st.warning("Pilih minimal satu tahun.")
                else: st.warning("Tidak ada data untuk pilihan ini (mis. SPI-12 belum terisi pada bulan awal 2026).")
        else:
            etiket_th = f"{tahun_pilih[0]}-{tahun_pilih[-1]}" if len(tahun_pilih) > 1 else str(tahun_pilih[0])
            etiket_bl = pilih if pilih != "Pilih bulan sendiri" else ", ".join(MON[b - 1] for b in bulan); etiket_pendek = etiket_bl.split(" (")[0]
            agg = gs.groupby("grid_id").agg(p_kering=("p_kering", "mean"), p_sangat=("p_sangat_kering", "mean"), spi=("spi_median", "mean")).reset_index(); agg[["p_kering", "p_sangat"]] *= 100
            bs = basem[basem["bulan"].isin(bulan)].groupby("grid_id")[["kering_model_pct", "kering_target_pct"]].mean().reset_index()
            agg = agg.merge(bs, on="grid_id").merge(grid, on="grid_id"); agg["selisih_pp"] = agg["p_kering"] - agg["kering_model_pct"]
            if dalam_saja: agg = agg[agg["wilayah"].notna()]
            if gj is None: agg = agg.drop(columns="wilayah")
            if dalam_saja: gs = gs[gs["grid_id"].isin(agg["grid_id"])]
            fk, fb = agg["p_kering"].mean(), agg["kering_model_pct"].mean(); n_bt = int(gs.groupby("grid_id").size().max()); sel_b = fk - fb
            per_th = gs.groupby("tahun")["p_kering"].mean() * 100; kb, kal_b = tafsir(sel_b, se_kasar(per_th))
            with kr:
                banner(f"<b>{etiket_pendek} · {etiket_th} · {skala}:</b> {n(fk)}% kering vs {n(fb)}% pada 1981-2010 · selisih <b>{n(sel_b, 1, True)} poin</b> ({KET_KODE[kb]})",
                       f"{kal_b} Angka = peluang kering rata-rata dari semua simulasi (definisi sama dengan tab Ringkasan)." + (" Makin sedikit tahun dan bulan dipilih, makin kuat pengaruh variasi acak model." if len(tahun_pilih) * len(bulan) < 36 else ""))
                kpi_grid([kartu("Kering", f"{n(fk)}%", f"dari {n_bt} bulan per grid", "Peluang bulan kering (SPI <= -1), rata-rata semua simulasi."), kartu("Kondisi 1981-2010", f"{n(fb)}%", "menurut model, bulan sama", "Baseline model sendiri untuk bulan yang sama."),
                          kartu("Selisih", f"{n(sel_b, 1, True)} poin", KET_KODE[kb], "Proyeksi dikurangi baseline model."), kartu("Sangat kering", f"{n(agg['p_sangat'].mean())}%", "SPI <= -1,5", "Bulan dengan SPI <= -1,5 (kering parah).", True)], 2)
                if dalam_saja: st.caption(f"Hanya {len(agg)} grid dalam batas Banten.")
            ekstra = [("Kondisi 1981-2010 (model)", "kering_model_pct", "%"), (f"Pengamatan {meta['target']}", "kering_target_pct", "%"), ("Sangat kering", "p_sangat", "%")]
            mode_k = KET_PETA[ket][1]; cA, cB = st.columns(2, gap="medium")
            with cA:
                if mode_k == "pos": z0, z1 = batas_skala(agg["p_kering"], "pos"); fg = peta(agg, "p_kering", "", "YlOrRd", z0, z1, "%", "Frekuensi kering", ekstra, gaya=gaya)
                elif mode_k == "pp": z0, z1 = batas_skala(agg["selisih_pp"], "pp"); fg = peta(agg, "selisih_pp", "", "RdBu_r", z0, z1, " poin", "Selisih vs 1981-2010", ekstra, zmid=0, gaya=gaya)
                else: z0, z1 = batas_skala(agg["spi"], "spi"); fg = peta(agg, "spi", "", "BrBG", z0, z1, "", "SPI median", ekstra, zmid=0, gaya=gaya)
                judul(f"Peta: {ket}", TIP_PETA[mode_k] + f" Arahkan kursor untuk nilai tiap grid. Skala warna menyesuaikan sebaran data ({z0:g} sampai {z1:g})." + (f" Batas wilayah: {gj['catatan']}" if gj is not None and "catatan" in gj else "")); tampil(fg, 460)
            with cB:
                judul("Per tahun", "Batang lebih tinggi dari garis putus-putus = tahun itu lebih sering kering dari 1981-2010 untuk bulan yang dipilih.")
                fig = go.Figure(go.Bar(x=per_th.index, y=per_th.values, marker_color=TEAL, name="proyeksi", hovertemplate="Tahun %{x}<br><b>%{y:.1f}%</b> bulan kering<extra></extra>"))
                garis_acuan(fig, list(per_th.index), fb, "1981-2010 (model)", C_BASE, "dot")
                fig.update_layout(xaxis_title="tahun", yaxis_title="% bulan kering", hovermode="x unified"); tampil(fig, 460)

            def grafik_profil(dengan_pita):
                gt = grdm[grdm["tahun"].isin(tahun_pilih)]; prof = gt.groupby("bulan")["p_kering"].mean() * 100; bb = basem.groupby("bulan")[["kering_model_pct", "kering_target_pct"]].mean(); nm = [MON[b - 1] for b in bb.index]; fig = go.Figure()
                if dengan_pita:
                    pbase = (bb["kering_model_pct"] / 100).clip(0.001, 0.999); se2 = 200 * np.sqrt(pbase * (1 - pbase) / len(tahun_pilih))
                    fig.add_trace(go.Scatter(x=nm, y=(bb["kering_model_pct"] - se2).clip(lower=0), mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
                    fig.add_trace(go.Scatter(x=nm, y=bb["kering_model_pct"] + se2, mode="lines", line=dict(width=0), fill="tonexty", fillcolor="rgba(128,128,128,0.28)", name=f"kisaran acak (±2 SE, {len(tahun_pilih)} tahun)", hoverinfo="skip"))
                fig.add_trace(go.Bar(x=[MON[b - 1] for b in prof.index], y=prof.values, marker_color=[TEAL if b in bulan else C_ABU for b in prof.index], name="proyeksi (teal = bulan terpilih)", hovertemplate="%{x}<br><b>%{y:.1f}%</b> bulan kering<extra></extra>"))
                fig.add_trace(go.Scatter(x=nm, y=bb["kering_model_pct"], mode="lines+markers", line=dict(color=C_BASE, dash="dot", width=3), marker=dict(size=7), name="1981-2010 (model)", hovertemplate="%{x}: %{y:.1f}%<extra>model</extra>"))
                if dengan_pita: fig.add_trace(go.Scatter(x=nm, y=bb["kering_target_pct"], mode="lines+markers", line=dict(color=C_TARGET, dash="dash", width=3), marker=dict(size=7), name=f"1981-2010 ({meta['target']})", hovertemplate="%{x}: %{y:.1f}%<extra>pengamatan</extra>"))
                fig.update_layout(xaxis_title="bulan", yaxis_title="% bulan kering", hovermode="x unified"); return fig

            cC, cD = st.columns(2, gap="medium")
            with cC:
                judul("Pola per bulan", "Bulan mana yang paling sering kering, dan seberapa jauh dari 1981-2010 (garis abu-abu). Batang teal = bulan yang kamu pilih."); tampil(grafik_profil(False), 440)
            with cD:
                judul("Per kabupaten/kota", "Batang yang melewati berlian abu-abu = wilayah itu diproyeksikan lebih sering kering daripada 1981-2010. Rata-rata dari grid yang pusatnya jatuh di dalam wilayah.")
                if gj is not None and agg["wilayah"].notna().any():
                    rk = agg.dropna(subset=["wilayah"]).groupby("wilayah")[["p_kering", "kering_model_pct"]].mean().sort_values("p_kering"); fig = go.Figure()
                    fig.add_trace(go.Bar(y=rk.index, x=rk["p_kering"], orientation="h", marker_color=TEAL, name="proyeksi", hovertemplate="%{y}<br><b>%{x:.1f}%</b> bulan kering<extra></extra>"))
                    fig.add_trace(go.Scatter(y=rk.index, x=rk["kering_model_pct"], mode="markers", marker=dict(symbol="diamond", size=13, color=C_BASE, line=dict(width=1.5, color="white")), name="1981-2010 (model)", hovertemplate="%{y}<br>1981-2010: %{x:.1f}%<extra></extra>"))
                    fig.update_layout(xaxis_title="% bulan kering", yaxis_title=""); tampil(fig, 440)
                else: st.info("Perlu berkas banten_kabkota.geojson.")

            st.download_button("Unduh tabel per grid (CSV)", agg.drop(columns=["p_sangat"], errors="ignore").rename(columns={"p_kering": "bulan_kering_pct", "spi": "spi_median_rata2", "kering_model_pct": "baseline_model_pct", "kering_target_pct": f"baseline_{meta['target']}_pct", "selisih_pp": "selisih_poin"}).round(3).to_csv(index=False).encode("utf-8-sig"),
                               file_name=f"peta_kering_banten_{skala}_{etiket_th}.csv", mime="text/csv")
            with st.expander("Animasi per tahun"):
                if not (gaya and hasattr(go, "Choroplethmap")): st.info("Butuh peta dasar: ubah 'Gaya peta' di Pengaturan lanjutan.")
                elif len(tahun_pilih) < 2: st.info("Pilih rentang minimal dua tahun.")
                elif st.checkbox("Buat animasi sesuai pilihan di atas", key="buat_anim", help="Agak berat; tunggu sebentar. Tekan Putar atau geser slider tahun. Warna memakai skala yang sama untuk semua tahun. Satu tahun = satu realisasi model, jadi perhatikan pola umum."):
                    gy = gs.groupby(["tahun", "grid_id"]).agg(p=("p_kering", "mean"), sp=("spi_median", "mean")).reset_index(); gids = agg["grid_id"].to_numpy(); bgrid = agg.set_index("grid_id")["kering_model_pct"].reindex(gids).to_numpy()
                    def nilai(y):
                        d = gy[gy["tahun"] == y].set_index("grid_id").reindex(gids)
                        return (d["p"] * 100).to_numpy() if mode_k == "pos" else (d["p"] * 100 - bgrid) if mode_k == "pp" else d["sp"].to_numpy()
                    nilai_th = {y: nilai(y) for y in tahun_pilih}; wr, zm, sat, lab = WARNA_PETA[mode_k]; a0, a1 = batas_skala(np.concatenate(list(nilai_th.values())), mode_k)
                    fa = peta(agg.assign(z_anim=nilai_th[tahun_pilih[0]]), "z_anim", "", wr, a0, a1, sat, lab, zmid=zm, gaya=gaya)
                    fa.frames = [go.Frame(name=str(y), traces=[0], data=[go.Choroplethmap(z=nilai_th[y])]) for y in tahun_pilih]
                    fa.update_layout(updatemenus=[dict(type="buttons", direction="left", showactive=False, x=0.0, y=-0.02, xanchor="left", yanchor="top", buttons=[
                                         dict(label="▶ Putar", method="animate", args=[None, dict(frame=dict(duration=800, redraw=True), fromcurrent=True, transition=dict(duration=0))]),
                                         dict(label="⏸ Jeda", method="animate", args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate", transition=dict(duration=0))])])],
                                     sliders=[dict(x=0.18, len=0.8, y=-0.02, yanchor="top", currentvalue=dict(prefix="Tahun: "), steps=[dict(method="animate", label=str(y), args=[[str(y)], dict(mode="immediate", frame=dict(duration=0, redraw=True), transition=dict(duration=0))]) for y in tahun_pilih])])
                    tampil(fa, 600, 90)
            with st.expander("Detail untuk peneliti: deret SPI bulanan dan pola dengan kisaran acak"):
                cE, cF = st.columns(2, gap="medium")
                with cE:
                    judul("Pola per bulan dengan kisaran acak", "Pita abu-abu = kisaran acak kasar dari baseline untuk jumlah tahun terpilih. Batang di luar pita menyimpang lebih dari kisaran acak, tetapi belum tentu sinyal iklim (bisa variabilitas internal GCM atau prediktor)."); tampil(grafik_profil(True), 440)
                with cF:
                    judul("Deret SPI bulanan", "Satu titik = satu bulan dalam satu lintasan GCM, bukan ramalan bulan itu. Garis tegak = p10-p90. Pita warna = kategori SPI; garis merah putus-putus = ambang kering (-1).")
                    rt = regm.sort_values(["tahun", "bulan"]).reset_index(drop=True); thn = rt["tahun"].isin(tahun_pilih).to_numpy(); ok = rt["bulan"].isin(bulan).to_numpy() & thn
                    tgl = pd.to_datetime(dict(year=rt["tahun"], month=rt["bulan"], day=1)); sub = rt[ok]; fig = go.Figure()
                    fig.add_trace(go.Scatter(x=tgl, y=rt["spi_median"].where(thn), mode="lines", line=dict(color=C_ABU, width=1.5), name="semua bulan", hovertemplate="%{x|%b %Y}: %{y:.2f}<extra></extra>"))
                    fig.add_trace(go.Scatter(x=tgl[ok], y=sub["spi_median"], mode="markers", marker=dict(color=TEAL, size=8), name="bulan terpilih",
                                             error_y=dict(type="data", symmetric=False, array=(sub["spi_p90"] - sub["spi_median"]).to_numpy(), arrayminus=(sub["spi_median"] - sub["spi_p10"]).to_numpy(), color="rgba(15,139,141,0.55)", thickness=1.6, width=0),
                                             customdata=np.c_[sub["spi_p10"], sub["spi_p90"]], hovertemplate="%{x|%b %Y}<br><b>median %{y:.2f}</b><br>p10 %{customdata[0]:.2f} | p90 %{customdata[1]:.2f}<extra></extra>"))
                    vv = pd.concat([rt.loc[thn, "spi_p10"], rt.loc[thn, "spi_p90"]]).dropna(); ylo, yhi = min(-2.5, float(vv.min()) - 0.2), max(2.5, float(vv.max()) + 0.2)
                    for b0, b1, wr, nmk in PITA_SPI:
                        y0, y1 = max(b0, ylo), min(b1, yhi)
                        if y0 < y1: fig.add_hrect(y0=y0, y1=y1, fillcolor=wr or "rgba(128,128,128,0.06)", opacity=0.16 if wr else 1, line_width=0, layer="below", annotation_text=nmk, annotation_position="top right", annotation_font_size=11)
                    fig.add_hline(y=-1, line_dash="dash", line_width=2.5, line_color="#e53935"); fig.add_hline(y=0, line_color="#888", line_width=1); fig.update_yaxes(range=[ylo, yhi])
                    fig.update_layout(yaxis_title=f"{skala} rata-rata wilayah", hovermode="closest"); tampil(fig, 440)

# ---------------- tab korelasi & validasi ----------------
with tab_k:
    if kor is None:
        st.info("Berkas korelasi belum ada (sel 14g notebook).")
    else:
        mk = meta.get("korelasi", {}); rk = float(kor["r_kritis_p05"].iloc[0]); nm_model = mk.get("model", "model terpilih"); ada_m = "r_model_t1" in kor.columns
        n_g = int(kor["lolos_fdr_gcm_target"].sum()); n_m = int(kor["lolos_fdr_model_t1"].sum()) if ada_m else None; ir = kor["r_gcm_target"].abs().idxmax(); rmax, umax = float(kor.loc[ir, "r_gcm_target"]), kor.loc[ir, "unit"]
        banner(f"Korelasi nyata dengan {meta['target']}: <b>GCM mentah {n_g}/{len(kor)}</b>" + (f" · <b>model ERA5 {n_m}/{len(kor)}</b>" if n_m is not None else ""),
               f"Dari {len(kor)} uji (12 bulan, 4 musim, 1 tahunan), hanya {n_g} korelasi hujan GCM yang tetap nyata setelah koreksi uji berganda (FDR). Terbesar {n(rmax, 2, True)} ({umax}), di bawah batas kritis {n(rk, 2)}. "
               + ("GCM berjalan bebas, jadi kejadiannya tidak sefase dengan dunia nyata; karena itu proyeksi memakai model yang dilatih dengan data ERA5." if n_g == 0 else "Sebagian korelasi nyata; lihat grafik."), "ok" if n_g == 0 else "info")
        pil = st.radio("Skala waktu", ["Per bulan", "Per musim dan tahunan"], horizontal=True, key="kor_skala"); d = kor[kor["jenis"].isin(["bulan"] if pil == "Per bulan" else ["musim", "tahunan"])]; musim = pil != "Per bulan"
        pk_ = mk.get("periode_gcm_target", ["?", "?"]); pm_ = mk.get("periode_model_t1", ["?", "?"])
        judul(f"Korelasi dengan {meta['target']}", f"Batang di luar garis putus-putus (±{n(rk, 2)}) nyata pada p < 0,05 sebelum koreksi; ★ = tetap nyata setelah koreksi {len(kor)} uji. Abu-abu = hujan GCM mentah. Teal = model yang dilatih dengan data ERA5, diuji pada tahun yang tidak dilihat model. "
                                          "Jingga (hanya musim) = kontrol: bila indeks ERA5 lolos tetapi GCM tidak, ujinya cukup peka dan GCM memang tidak membawa informasi waktu. " + (f"Periode: GCM {pk_[0]}-{pk_[1]}, model {pm_[0]}-{pm_[1]} (out-of-fold), jadi batas kritisnya sedikit berbeda. " if ada_m else "") + "Korelasi tinggi pada rata-rata wilayah belum berarti model bagus per grid.")
        def batang(y, lolos, nama, warna):
            return go.Bar(x=d["unit"], y=d[y], name=nama, marker_color=warna, text=["★" if (pd.notna(v) and bool(v)) else "" for v in d[lolos]] if lolos in d.columns else None, textposition="outside", textfont=dict(size=16), hovertemplate="%{x}<br><b>r = %{y:.2f}</b><extra>" + nama + "</extra>")
        fig = go.Figure(); fig.add_trace(batang("r_gcm_target", "lolos_fdr_gcm_target", "Hujan GCM", C_BASE))
        if ada_m: fig.add_trace(batang("r_model_t1", "lolos_fdr_model_t1", f"Model {nm_model} (ERA5)", TEAL))
        if musim and "r_oof_indeks_era5_musiman" in d.columns: fig.add_trace(batang("r_oof_indeks_era5_musiman", "lolos_fdr_indeks_era5_musiman", "Kontrol: indeks ERA5", ORANYE))
        for yy in (rk, -rk): fig.add_hline(y=yy, line_dash="dot", line_width=1.5, line_color="#555")
        fig.add_hline(y=0, line_color="#888", line_width=1); fig.update_layout(barmode="group", yaxis_title="korelasi (r)", yaxis_range=[-0.65, 1.05], hovermode="x unified"); tampil(fig, 400)
        with st.expander("Angka lengkap"):
            tb = kor.rename(columns={"r_gcm_target": "r GCM-target", "p_gcm_target": "p GCM-target", "lolos_fdr_gcm_target": "lolos FDR (GCM)", "r_model_t1": "r model (T1)", "p_model_t1": "p model (T1)", "lolos_fdr_model_t1": "lolos FDR (model)",
                                     "r_oof_indeks_era5_musiman": "r ERA5 (kontrol)", "r_oof_indeks_gcm_musiman": "r indeks GCM", "r_oof_pr_gcm_musiman": "r pr GCM (musiman)"})
            st.dataframe(tb[[c for c in ["unit", "jenis", "r GCM-target", "p GCM-target", "lolos FDR (GCM)", "r model (T1)", "p model (T1)", "lolos FDR (model)", "r ERA5 (kontrol)", "r indeks GCM", "r pr GCM (musiman)"] if c in tb.columns]].set_index("unit").round(3))
            st.download_button("Unduh tabel korelasi (CSV)", kor.to_csv(index=False).encode("utf-8-sig"), file_name="korelasi_bulan_musim_banten.csv", mime="text/csv")
            for c in mk.get("catatan", []): st.write("- " + c)
        if kor_antar is not None:
            jp = st.radio("Persistensi", ["antar-bulan", "antar-musim"], horizontal=True, key="kor_antar_jenis", format_func=lambda v: {"antar-bulan": "Antar-bulan (12 x 12)", "antar-musim": "Antar-musim (4 x 4)"}[v])
            da = kor_antar[kor_antar["jenis"] == jp]; cols = st.columns(2, gap="medium"); ring = []
            for cc, sumber in zip(cols, da["sumber"].unique()):
                M = da[da["sumber"] == sumber].pivot(index="baris", columns="kolom", values="r"); urut = list(dict.fromkeys(da["baris"])); M = M.loc[urut, urut]
                off = M.to_numpy()[np.triu_indices(len(urut), 1)]; ring.append((sumber, float(np.mean(off)), float(np.max(off))))
                with cc:
                    fg = go.Figure(go.Heatmap(z=M.to_numpy(), x=urut, y=urut, colorscale="RdBu_r", zmin=-0.7, zmax=0.7, zmid=0, colorbar=dict(title="r"), texttemplate="%{z:.2f}" if len(urut) <= 4 else None, hovertemplate="%{y} dan %{x}<br><b>r = %{z:.2f}</b><extra></extra>"))
                    fg.update_layout(title=dict(text=sumber, font=dict(size=14))); fg.update_yaxes(autorange="reversed"); tampil(fg, 380, atas=40)
            judul("Persistensi: apakah bulan basah diikuti bulan basah?", "Merah = dua bulan (atau musim) cenderung sama-sama basah atau sama-sama kering di tahun yang sama; biru = berlawanan; putih = tidak berhubungan. Diagonal selalu 1. " + "; ".join(f"{a}: rata-rata {n(m, 2, True)}, terbesar {n(x, 2, True)}" for a, m, x in ring)
                  + ". Korelasi dari sekitar 34 tahun punya galat baku sekitar 0,17, jadi selisih kecil antar-sel jangan ditafsirkan. Struktur ini menentukan seberapa lebar sebaran SPI-3/6/12.")

# ---------------- tab panduan ----------------
with tab3:
    with st.expander("Cara membaca dashboard (1 menit)", expanded=True):
        st.markdown("1. **Pilih skala SPI** di panel kiri.\n2. **Ringkasan:** baca kalimat biru dan empat kartu *Temuan utama*. Arahkan kursor ke **?** untuk penjelasan.\n3. **Peta & musim:** pilih tahun dan musim, lihat di mana bulan kering lebih sering.\n"
                    "4. **Korelasi & validasi:** bukti bahwa hujan GCM mentah tidak bisa dipakai langsung, dan model ERA5 bisa.\n5. **Ingat:** satu tahun atau satu bulan bukan ramalan; ini proyeksi bersyarat dari satu model dan satu skenario.")
    with st.expander("Apa itu SPI?"):
        st.markdown("**SPI** membandingkan hujan suatu periode dengan hujan biasanya di tempat dan waktu yang sama. 0 = normal, negatif = lebih kering. Angka 3, 6, 12 = lama periode (bulan).")
        st.table(KATEGORI_SPI.set_index("Nilai SPI"))
    with st.expander("Istilah"):
        st.markdown("- **Bulan kering:** SPI <= -1 pada satu petak peta; '% bulan kering' = porsi petak-bulan yang kering.\n- **Poin:** selisih dua persentase (15% ke 17% = 2 poin).\n"
                    "- **Kondisi 1981-2010 (model):** seberapa sering model yang sama menghasilkan bulan kering pada 1981-2010. Pembanding utama karena model punya bias sendiri.\n"
                    f"- **Pengamatan ({meta['target']}):** frekuensi kering dari data hujan pengamatan; pembanding tambahan.\n- **Simulasi:** hasil model diulang dengan derau acak kecil; sebarannya bukan ketidakpastian iklim.\n- **p10, median, p90:** batas bawah, tengah, dan atas yang mencakup 80% simulasi.")
    with st.expander("Catatan wajib"):
        for c in meta["catatan"]: st.write("- " + c)
    with st.expander("Untuk peneliti: model, uji, dan data masukan"):
        st.markdown(f"**Model:** {meta['model']} (set {meta['set_fitur']}) · **GCM:** {meta['gcm']} · **Skenario:** {meta['skenario']} · **Target:** {meta['target']} · **Status:** {meta['status_gerbang']}")
        judul("Gerbang model", "Centang = lolos. (a) skill sefase > 0 (Tingkat 1, data ERA5); (b) sebaran <= 1,10x klimatologi (Tingkat 2, prediktor GCM); (c) selisih frekuensi kering SPI-3 <= 3 poin dari pengamatan.")
        st.dataframe(pd.DataFrame(meta["gerbang"]).T.rename(columns={"a": "(a) skill sefase > 0", "b": "(b) sebaran", "c": "(c) selisih kering"}).replace({True: "✓ lolos", False: "✗ tidak"}))
        ka = meta.get("konsistensi_arah")
        if ka and ka.get("jendela"):
            judul("Konsistensi arah", (ka.get("catatan", "") + " Berlawanan di jendela dengan persen luar-rentang tinggi bisa berupa artefak ekstrapolasi, bukan temuan iklim.").strip())
            st.dataframe(pd.DataFrame([{"Jendela": j["jendela"], "Peran": j["peran"], "Hujan GCM mentah (%)": j["gcm_pr_mentah_pct"], f"Model {ka.get('model', '')} (%)": j["model_pct"], "Berlawanan?": "ya" if j["berlawanan"] else "tidak", "Di luar rentang latih (%)": j["luar_rentang_pct"],
                                       **{f"{nm} (%)": v for nm, v in j.get("semua_model_pct", {}).items() if nm != ka.get("model")}} for j in ka["jendela"]]).set_index("Jendela"))
        judul("Data masukan di luar rentang latih", "Persentase baris prediktor GCM di luar rentang ERA5 (dipotong). Makin tinggi, makin jauh dari kondisi yang dipakai melatih model.")
        st.dataframe(pd.Series(meta["baris_prediktor_luar_rentang_pct"], name="% baris").to_frame().round(1))
        if "bulanan" in meta: st.caption(f"Baseline bulanan memakai periode {meta['bulanan']['baseline_periode'][0]}-{meta['bulanan']['baseline_periode'][1]}.")

"""Dashboard proyeksi SPI Banten 2026-2050 (membaca ekspor sel 14d, 14e, 14f notebook). Grafik interaktif (Plotly): arahkan kursor untuk melihat nilai.
Jalankan:  HASIL_DIR=/jalur/ke/folder streamlit run app_dashboard_spi.py
Sumber Google Drive (opsional): atur DRIVE_FOLDER_ID (env atau Streamlit secrets) = ID folder Drive yang dibagikan 'siapa saja dengan link'.
Berkas wajib: dashboard_tahunan_regional.csv, dashboard_tahunan_per_grid.csv, dashboard_meta.json (14d)
              dashboard_bulanan_regional.csv.gz, dashboard_bulanan_per_grid.csv.gz, dashboard_baseline_bulan_grid.csv.gz, dashboard_grid.csv (14e)
Berkas opsional: banten_kabkota.geojson (batas kabupaten/kota; diletakkan di folder hasil atau di sebelah berkas .py ini). Tanpa berkas ini peta tetap jalan, hanya tanpa garis batas dan nama wilayah.
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
.kpi {background: rgba(15,139,141,0.10); border: 1.5px solid rgba(15,139,141,0.55); border-radius: 10px; padding: 12px 14px; min-height: 112px; display: flex; flex-direction: column; justify-content: space-between;}
.kpi .l {font-size: 0.86rem; font-weight: 600; opacity: 0.85; line-height: 1.25;}
.kpi .v {font-size: 1.95rem; font-weight: 800; line-height: 1.15; margin: 4px 0;}
.kpi .s {font-size: 0.8rem; opacity: 0.75; line-height: 1.25;}
.badge {display: inline-block; padding: 3px 11px; border-radius: 999px; font-size: 0.8rem; font-weight: 600; margin: 2px 6px 2px 0; border: 1px solid;}
.badge.ok {background: rgba(46,125,50,0.14); border-color: rgba(46,125,50,0.6);} .badge.warn {background: rgba(245,124,0,0.14); border-color: rgba(245,124,0,0.7);} .badge.info {background: rgba(128,128,128,0.14); border-color: rgba(128,128,128,0.55);}
button[data-baseweb="tab"] p {font-weight: 700; font-size: 1.02rem;}
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
grid_ref = grd[["grid_id", "lat", "lon"]].drop_duplicates().sort_values("grid_id").reset_index(drop=True)
gj, wil_tab, wil_label = muat_wilayah(folder, versi_folder(folder), grid_ref)

# ---------------- pembantu teks dan angka ----------------
def n(x, d=1, plus=False):
    """Format angka gaya Indonesia (koma desimal)."""
    s = f"{x:+.{d}f}" if plus else f"{x:.{d}f}"
    return s.replace(".", ",")

def tafsir(selisih, se):
    """Menafsirkan selisih (poin persentase) terhadap kondisi 1981-2010. 'se' = galat baku kasar dari naik-turun antar-tahun. Aturan praktis: selisih dianggap berarti bila > 2 x galat baku."""
    if not np.isfinite(se): return "sedikit", "Terlalu sedikit tahun untuk disimpulkan: satu atau dua tahun hanyalah satu-dua realisasi model, **bukan ramalan dan bukan tren**."
    batas = 2 * se
    if abs(selisih) < batas: return "sama", f"Selisihnya kecil dan masih dalam kisaran naik-turun alami antar-tahun, jadi **belum menunjukkan perubahan yang berarti**."
    return ("lebih", "Artinya bulan kering diproyeksikan **lebih sering** daripada kondisi 1981-2010.") if selisih > 0 else ("kurang", "Artinya bulan kering diproyeksikan **lebih jarang** daripada kondisi 1981-2010.")

KET_KODE = {"sama": "belum berarti", "lebih": "lebih sering kering", "kurang": "lebih jarang kering", "sedikit": "data terlalu sedikit"}

def se_kasar(serie):
    s = pd.Series(serie).dropna(); return float(s.std(ddof=1) / np.sqrt(len(s))) if len(s) >= 3 else float("nan")

def kartu(label, nilai, sub=""):
    e = html.escape
    return f'<div class="kpi"><div class="l">{e(str(label))}</div><div class="v">{e(str(nilai))}</div><div class="s">{e(str(sub)) if sub else "&nbsp;"}</div></div>'

def kpi_grid(daftar, kolom=4):
    st.markdown(f'<div class="kpi-grid k{kolom}">' + "".join(daftar) + "</div>", unsafe_allow_html=True)

def lencana(teks, jenis="ok"):
    return f'<span class="badge {jenis}">{html.escape(teks)}</span>'

def catatan_meta(kata, default=""):
    return next((c for c in meta["catatan"] if kata in c), default)

# ---------------- pembantu grafik ----------------
def tampil(fig, tinggi=420):
    fig.update_layout(height=tinggi, margin=dict(l=10, r=10, t=56, b=10), legend=dict(orientation="h", y=-0.2, x=0, font=dict(size=13)), font=dict(size=14), separators=",.",
                      title=dict(font=dict(size=16)), hoverlabel=dict(font_size=14))
    fig.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,0.35)", linecolor="rgba(128,128,128,0.9)", linewidth=1.5, ticks="outside", tickfont=dict(size=13))
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.35)", linecolor="rgba(128,128,128,0.9)", linewidth=1.5, ticks="outside", tickfont=dict(size=13))
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
    fig.update_layout(title=dict(text=judul, font=dict(size=13)))
    return fig

# ---------------- kepala halaman ----------------
h0, h1 = int(meta["horizon"][0]), int(meta["horizon"][1])
with slot_skala:
    skala = st.radio("Skala kekeringan (SPI)", meta["spi_skala"], index=0, format_func=lambda s: SKALA_INFO.get(s, (s, ""))[0],
                     help="SPI membandingkan hujan suatu periode dengan hujan biasanya. Angka belakang = lama periode yang dijumlahkan (bulan). 'Kering' di dashboard ini berarti SPI <= -1.")
    st.caption(SKALA_INFO.get(skala, ("", ""))[1])

r = reg[reg["SPI"] == skala].sort_values("tahun"); base = float(meta["baseline_model_sendiri_pct"][skala]); acuan = float(meta["acuan_target_pct"][skala])
rata = float(np.average(r["kering_pct_median"], weights=r["n_bulan_valid"])); sel = rata - base; kode, kalimat = tafsir(sel, se_kasar(r["kering_pct_median"]))

st.title(f"Proyeksi kekeringan Banten {h0}-{h1}")
st.caption(f"Berdasarkan model iklim global {meta['gcm']} (skenario {meta['skenario']}), diperhalus ke skala lokal Banten dengan model {meta['model']} dan dikalibrasi ke data hujan {meta['target']}.")
if not str(meta["status_gerbang"]).startswith("lolos"):
    st.warning(f"Status model: **{meta['status_gerbang']}**. Model ini belum lolos gerbang penuh; baca sebagai proyeksi bersyarat, bukan hasil terverifikasi.")
luar = meta["baris_prediktor_luar_rentang_pct"].get(f"{h0}-{h1}", meta["baris_prediktor_luar_rentang_pct"].get(next(iter(meta["baris_prediktor_luar_rentang_pct"])))) if meta.get("baris_prediktor_luar_rentang_pct") else None
lencana_html = lencana(f"Uji model: {meta['status_gerbang']}", "ok" if str(meta["status_gerbang"]).startswith("lolos") else "warn")
if luar is not None: lencana_html += lencana(f"Data masukan di luar rentang latih: {luar:.0f}%", "ok" if luar < 20 else "warn")
lencana_html += lencana(f"1 model iklim · 1 skenario · {meta['n_anggota_ensemble']} simulasi", "info")
st.markdown(lencana_html, unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["Ringkasan", "Peta & musim", "Panduan & metode"])

# ---------------- tab 1: ringkasan ----------------
with tab1:
    st.success(f"**Kesimpulan ({skala}):** selama {h0}-{h1}, sekitar **{n(rata)}%** bulan di Banten diproyeksikan kering, dibanding **{n(base)}%** pada 1981-2010 menurut model yang sama (selisih {n(sel, 1, True)} poin). {kalimat}")
    st.caption("'Kering' = SPI <= -1. 'Poin' = poin persentase (selisih dua persentase). Ini proyeksi bersyarat dari satu model iklim dan satu skenario, bukan ramalan.")
    with st.expander("Baru pertama kali? Baca ini dulu (30 detik)"):
        st.markdown("- **Apa yang ditampilkan?** Seberapa sering bulan kering (SPI <= -1) diproyeksikan terjadi di Banten pada tahun-tahun ke depan.\n"
                    "- **Dibandingkan dengan apa?** Garis abu-abu = kondisi 1981-2010 menurut model yang sama. Kalau grafik berada di atas garis itu, bulan kering lebih sering; di bawahnya, lebih jarang.\n"
                    "- **Jangan baca satu tahun sebagai ramalan.** Naik-turun dari tahun ke tahun adalah variasi alami model, bukan prediksi kejadian tahun itu. Lihat kecenderungan jangka panjang (garis oranye) dan rata-rata banyak tahun.\n"
                    "- **Mau lihat per wilayah atau per musim?** Buka tab *Peta & musim*.")
    kpi_grid([kartu(f"Bulan kering rata-rata {h0}-{h1}", f"{n(rata)}%", f"{r['tahun'].nunique()} tahun, median simulasi"), kartu("Kondisi 1981-2010 (menurut model)", f"{n(base)}%", "pembanding utama"),
              kartu("Selisih", f"{n(sel, 1, True)} poin", KET_KODE[kode])], 3)

    st.markdown("##### Frekuensi bulan kering per tahun")
    c1, c2 = st.columns(2); pita = c1.toggle("Tampilkan sebaran antar simulasi", value=True); tampil_obs = c2.toggle(f"Bandingkan dengan data pengamatan ({meta['target']})", value=False)
    inc = (r["n_bulan_valid"] < 12).to_numpy(); roll = r.set_index("tahun")["kering_pct_median"].rolling(5, center=True, min_periods=3).mean()
    fig = go.Figure()
    if pita:
        fig.add_trace(go.Scatter(x=r["tahun"], y=r["kering_pct_p10"], mode="lines", line=dict(width=0), name="p10", showlegend=False, hovertemplate="p10: %{y:.1f}%<extra></extra>"))
        fig.add_trace(go.Scatter(x=r["tahun"], y=r["kering_pct_p90"], mode="lines", line=dict(width=0), fill="tonexty", fillcolor=TEAL_MUDA, name="sebaran antar simulasi (bukan ketidakpastian iklim)", hovertemplate="p90: %{y:.1f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=r["tahun"], y=r["kering_pct_median"], mode="lines+markers", line=dict(color=TEAL, width=3.5), marker=dict(size=9, symbol=np.where(inc, "circle-open", "circle").tolist()), customdata=r["n_bulan_valid"],
                             name="proyeksi (median)", hovertemplate="<b>proyeksi: %{y:.1f}%</b> (%{customdata} bulan valid)<extra></extra>"))
    fig.add_trace(go.Scatter(x=roll.index, y=roll.values, mode="lines", line=dict(color=ORANYE, width=3, dash="dashdot"), name="kecenderungan (rata-rata 5 tahun)", hovertemplate="rata-rata 5 tahun: %{y:.1f}%<extra></extra>"))
    garis_acuan(fig, r["tahun"], base, "kondisi 1981-2010 (menurut model)", C_BASE, "dot")
    if tampil_obs: garis_acuan(fig, r["tahun"], acuan, f"kondisi 1981-2010 (data pengamatan {meta['target']})", C_TARGET, "dash")
    fig.update_layout(title=f"{skala}: % bulan kering di seluruh Banten", hovermode="x unified", xaxis_title="tahun", yaxis_title="% bulan kering"); tampil(fig, 440)
    st.caption("**Cara membaca:** titik teal di atas garis abu-abu putus-putus = tahun itu lebih sering kering dari 1981-2010. Satu tahun hanyalah satu realisasi variasi model, bukan ramalan; garis oranye membantu melihat kecenderungan di balik naik-turunnya.")
    if inc.any(): st.caption("Penanda berlubang = tahun awal dengan sebagian bulan SPI kosong: " + ", ".join(f"{int(t)} ({int(k)} bulan valid)" for t, k in r.loc[r["n_bulan_valid"] < 12, ["tahun", "n_bulan_valid"]].to_numpy()))

    st.markdown("##### Apakah makin kering? Bandingkan dua periode")
    mid_def = h0 + (h1 - h0 + 1) // 2; pisah = st.slider("Bagi periode proyeksi di tahun", h0 + 3, h1 - 3, mid_def, help="Periode awal = sampai tahun sebelum tahun ini; periode akhir = mulai tahun ini.")
    ra, rb = r[r["tahun"] < pisah], r[r["tahun"] >= pisah]
    ma, mb_ = float(np.average(ra["kering_pct_median"], weights=ra["n_bulan_valid"])), float(np.average(rb["kering_pct_median"], weights=rb["n_bulan_valid"]))
    se_ab = float(np.sqrt(se_kasar(ra["kering_pct_median"]) ** 2 + se_kasar(rb["kering_pct_median"]) ** 2)); k2, t2 = tafsir(mb_ - ma, se_ab)
    la, lb = f"{h0}-{pisah - 1}", f"{pisah}-{h1}"
    fig = go.Figure(go.Bar(x=["Kondisi 1981-2010 (model)", la, lb], y=[base, ma, mb_], marker_color=[C_BASE, "#5bb5b6", TEAL], text=[f"{n(v)}%" for v in (base, ma, mb_)], textposition="outside", cliponaxis=False,
                           hovertemplate="%{x}<br><b>%{y:.1f}%</b> bulan kering<extra></extra>"))
    fig.update_layout(title=f"{skala}: rata-rata % bulan kering per periode", yaxis_title="% bulan kering", yaxis_range=[0, max(base, ma, mb_) * 1.25], showlegend=False); tampil(fig, 360)
    st.markdown(f"Periode akhir ({lb}) **{n(mb_)}%** vs periode awal ({la}) **{n(ma)}%**: selisih **{n(mb_ - ma, 1, True)} poin**. " + t2.replace("daripada kondisi 1981-2010", "daripada periode awal"))
    st.caption("Perbandingan ini dari satu lintasan model iklim, jadi bisa dipengaruhi variasi alami model (mirip ENSO) dan sebaiknya tidak dibaca sebagai kepastian tren.")

    dl = r[["tahun", "n_bulan_valid", "kering_pct_p10", "kering_pct_median", "kering_pct_p90", "spi_rata2_median"]].rename(columns={"n_bulan_valid": "jumlah_bulan_valid", "kering_pct_p10": "bulan_kering_pct_p10", "kering_pct_median": "bulan_kering_pct_median", "kering_pct_p90": "bulan_kering_pct_p90", "spi_rata2_median": "spi_rata2_median"})
    st.download_button("Unduh tabel tahunan (CSV)", dl.to_csv(index=False).encode("utf-8-sig"), file_name=f"proyeksi_kering_banten_{skala}.csv", mime="text/csv")

    with st.expander("Detail untuk peneliti: ketiga skala SPI dan pembanding data pengamatan"):
        rows = []
        for s in meta["spi_skala"]:
            d = reg[reg["SPI"] == s]; pr = float(np.average(d["kering_pct_median"], weights=d["n_bulan_valid"])); b_, a_ = float(meta["baseline_model_sendiri_pct"][s]), float(meta["acuan_target_pct"][s])
            rows.append({"Skala": s, f"Proyeksi {h0}-{h1} (%)": round(pr, 1), "Baseline model 1981-2010 (%)": round(b_, 1), f"Acuan {meta['target']} 1981-2010 (%)": round(a_, 1), "Proyeksi - baseline model (poin)": round(pr - b_, 1)})
        st.dataframe(pd.DataFrame(rows).set_index("Skala"))
        st.caption("Baca perubahan terhadap baseline model sendiri (kolom ketiga), bukan terhadap data pengamatan, karena model punya bias tersendiri; perbandingan yang adil adalah model dengan model.")

# ---------------- tab 2: peta & musim ----------------
KET_PETA = {"Seberapa sering kering (%)": ("Frekuensi kering", "pos"), "Dibanding kondisi 1981-2010 (poin)": ("Selisih", "pp"), "SPI rata-rata (basah ke kering)": ("SPI", "spi")}
with tab2:
    if bln is None:
        st.info("Ekspor bulanan belum ada, jadi hanya peta per tahun yang tersedia. Jalankan sel 14e notebook untuk membuka pilihan musim dan rentang tahun.")
        gt_ = sorted(grd["tahun"].unique().tolist()); tahun = st.select_slider("Tahun", gt_, value=gt_[0]); g = grd[(grd["SPI"] == skala) & (grd["tahun"] == tahun)].dropna(subset=["kering_pct"]).merge(wil_tab, on="grid_id", how="left")
        if g.empty: st.warning("Tidak ada nilai untuk pilihan ini.")
        else: tampil(peta(g, "kering_pct", f"{skala}, {tahun}: % bulan kering (median simulasi)", "YlOrRd", 0, 100, "%", "% bulan kering", gaya=gaya), 540)
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
                pilih = st.selectbox("Bulan atau musim", list(PRESET), help="Musim di Banten hanya perkiraan kasar; pilih 'Pilih bulan sendiri' untuk bulan tertentu.")
                bulan = PRESET[pilih] if PRESET[pilih] is not None else [MON.index(m) + 1 for m in st.multiselect("Pilih bulan", MON, default=MON[5:9], key="bulan_multi")]
                ket = st.radio("Yang ditampilkan di peta", list(KET_PETA))
                dalam_saja = st.toggle("Hanya grid di dalam batas Banten", value=False, disabled=gj is None, help="Grid berbentuk kotak sehingga sebagian berada di laut atau provinsi tetangga." if gj is not None else "Perlu berkas banten_kabkota.geojson.")
        gs = grdm[grdm["tahun"].isin(tahun_pilih) & grdm["bulan"].isin(bulan)] if (bulan and tahun_pilih) else grdm.iloc[0:0]
        if gs.empty:
            with kr:
                if not bulan: st.warning("Pilih minimal satu bulan.")
                elif not tahun_pilih: st.warning("Pilih minimal satu tahun.")
                else: st.warning("Tidak ada data untuk pilihan ini (mis. SPI-12 belum terisi pada bulan awal 2026).")
        else:
            etiket_th = f"{tahun_pilih[0]}-{tahun_pilih[-1]}" if len(tahun_pilih) > 1 else str(tahun_pilih[0])
            etiket_bl = pilih if pilih != "Pilih bulan sendiri" else ", ".join(MON[b - 1] for b in bulan)
            agg = gs.groupby("grid_id").agg(p_kering=("p_kering", "mean"), p_sangat=("p_sangat_kering", "mean"), spi=("spi_median", "mean")).reset_index(); agg[["p_kering", "p_sangat"]] *= 100
            bs = basem[basem["bulan"].isin(bulan)].groupby("grid_id")[["kering_model_pct", "kering_target_pct"]].mean().reset_index()
            agg = agg.merge(bs, on="grid_id").merge(grid, on="grid_id"); agg["selisih_pp"] = agg["p_kering"] - agg["kering_model_pct"]
            if dalam_saja: agg = agg[agg["wilayah"].notna()]
            if gj is None: agg = agg.drop(columns="wilayah")
            if dalam_saja: gs = gs[gs["grid_id"].isin(agg["grid_id"])]
            fk, fb, ft = agg["p_kering"].mean(), agg["kering_model_pct"].mean(), agg["kering_target_pct"].mean(); n_bt = int(gs.groupby("grid_id").size().max()); sel_b = fk - fb
            per_th = gs.groupby("tahun")["p_kering"].mean() * 100; kb, kal_b = tafsir(sel_b, se_kasar(per_th))
            with kr:
                st.success(f"**{etiket_bl}, {etiket_th} ({skala}):** sekitar **{n(fk)}%** bulan diproyeksikan kering, dibanding **{n(fb)}%** pada 1981-2010 (selisih {n(sel_b, 1, True)} poin). {kal_b}" + (" Makin sedikit tahun dan bulan yang dipilih, makin kuat pengaruh variasi acak model." if len(tahun_pilih) * len(bulan) < 36 else ""))
                kpi_grid([kartu("Bulan kering diproyeksikan", f"{n(fk)}%", f"dari {n_bt} bulan per grid"), kartu("Kondisi 1981-2010 (model)", f"{n(fb)}%", "bulan yang sama"),
                          kartu("Selisih", f"{n(sel_b, 1, True)} poin", KET_KODE[kb]), kartu("Sangat kering (SPI <= -1,5)", f"{n(agg['p_sangat'].mean())}%", "dari bulan yang dipilih")], 2)
                st.caption("Angka di tab ini = peluang kering rata-rata dari semua simulasi, jadi bisa berbeda sedikit dari tab Ringkasan (median simulasi).")
                if dalam_saja: st.caption(f"Angka di tab ini hanya dari {len(agg)} grid di dalam batas Banten; angka di tab Ringkasan memakai semua grid.")
            ekstra = [("Kondisi 1981-2010 (model)", "kering_model_pct", "%"), (f"Data pengamatan {meta['target']}", "kering_target_pct", "%"), ("Sangat kering", "p_sangat", "%")]
            jd = f"{skala} | {ket} | {etiket_th}, {etiket_bl}"; mode_k = KET_PETA[ket][1]
            cA, cB = st.columns(2, gap="medium")
            with cA:
                if mode_k == "pos": z0, z1 = batas_skala(agg["p_kering"], "pos"); fg = peta(agg, "p_kering", jd, "YlOrRd", z0, z1, "%", "Frekuensi kering", ekstra, gaya=gaya)
                elif mode_k == "pp": z0, z1 = batas_skala(agg["selisih_pp"], "pp"); fg = peta(agg, "selisih_pp", jd, "RdBu_r", z0, z1, " poin", "Selisih vs 1981-2010", ekstra, zmid=0, gaya=gaya)
                else: z0, z1 = batas_skala(agg["spi"], "spi"); fg = peta(agg, "spi", jd, "BrBG", z0, z1, "", "SPI median", ekstra, zmid=0, gaya=gaya)
                tampil(fg, 460)
                st.caption({"pos": "**Cara membaca:** makin merah = makin sering bulan kering di grid itu.", "pp": "**Cara membaca:** merah = lebih sering kering daripada 1981-2010, biru = lebih jarang, putih = sama. Arahkan kursor untuk nilai tiap grid.",
                            "spi": "**Cara membaca:** coklat = cenderung kering, hijau = cenderung basah (SPI 0 = normal)."}[mode_k] + f" Skala warna menyesuaikan sebaran data ({z0:g} sampai {z1:g}).")
                if gj is not None and "catatan" in gj: st.caption("Batas wilayah: " + gj["catatan"])
            with cB:
                fig = go.Figure(go.Bar(x=per_th.index, y=per_th.values, marker_color=TEAL, name="proyeksi", hovertemplate="Tahun %{x}<br><b>%{y:.1f}%</b> bulan kering<extra></extra>"))
                garis_acuan(fig, list(per_th.index), fb, "kondisi 1981-2010 (model)", C_BASE, "dot")
                fig.update_layout(title="Per tahun, untuk bulan yang dipilih", xaxis_title="tahun", yaxis_title="% bulan kering", hovermode="x unified"); tampil(fig, 460)
                st.caption("**Cara membaca:** batang yang lebih tinggi dari garis putus-putus = tahun itu lebih sering kering dari 1981-2010 untuk bulan yang dipilih.")

            def grafik_profil(dengan_pita):
                gt = grdm[grdm["tahun"].isin(tahun_pilih)]; prof = gt.groupby("bulan")["p_kering"].mean() * 100; bb = basem.groupby("bulan")[["kering_model_pct", "kering_target_pct"]].mean(); nm = [MON[b - 1] for b in bb.index]; fig = go.Figure()
                if dengan_pita:
                    pbase = (bb["kering_model_pct"] / 100).clip(0.001, 0.999); se2 = 200 * np.sqrt(pbase * (1 - pbase) / len(tahun_pilih))
                    fig.add_trace(go.Scatter(x=nm, y=(bb["kering_model_pct"] - se2).clip(lower=0), mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
                    fig.add_trace(go.Scatter(x=nm, y=bb["kering_model_pct"] + se2, mode="lines", line=dict(width=0), fill="tonexty", fillcolor="rgba(128,128,128,0.28)", name=f"kisaran acak baseline (±2 SE, {len(tahun_pilih)} tahun; kasar)", hoverinfo="skip"))
                fig.add_trace(go.Bar(x=[MON[b - 1] for b in prof.index], y=prof.values, marker_color=[TEAL if b in bulan else C_ABU for b in prof.index], name="proyeksi (bulan terpilih berwarna teal)", hovertemplate="%{x}<br><b>%{y:.1f}%</b> bulan kering<extra></extra>"))
                fig.add_trace(go.Scatter(x=nm, y=bb["kering_model_pct"], mode="lines+markers", line=dict(color=C_BASE, dash="dot", width=3), marker=dict(size=7), name="kondisi 1981-2010 (model)", hovertemplate="%{x}: %{y:.1f}%<extra>model</extra>"))
                if dengan_pita: fig.add_trace(go.Scatter(x=nm, y=bb["kering_target_pct"], mode="lines+markers", line=dict(color=C_TARGET, dash="dash", width=3), marker=dict(size=7), name=f"kondisi 1981-2010 (pengamatan {meta['target']})", hovertemplate="%{x}: %{y:.1f}%<extra>pengamatan</extra>"))
                fig.update_layout(title="Pola per bulan kalender", xaxis_title="bulan", yaxis_title="% bulan kering", hovermode="x unified"); return fig

            cC, cD = st.columns(2, gap="medium")
            with cC:
                tampil(grafik_profil(False), 460); st.caption("**Cara membaca:** bulan mana yang paling sering kering, dan seberapa jauh dari kondisi 1981-2010 (garis abu-abu). Batang teal = bulan yang kamu pilih.")
            with cD:
                if gj is not None and agg["wilayah"].notna().any():
                    rk = agg.dropna(subset=["wilayah"]).groupby("wilayah")[["p_kering", "kering_model_pct"]].mean().sort_values("p_kering"); fig = go.Figure()
                    fig.add_trace(go.Bar(y=rk.index, x=rk["p_kering"], orientation="h", marker_color=TEAL, name="proyeksi", hovertemplate="%{y}<br><b>%{x:.1f}%</b> bulan kering<extra></extra>"))
                    fig.add_trace(go.Scatter(y=rk.index, x=rk["kering_model_pct"], mode="markers", marker=dict(symbol="diamond", size=13, color=C_BASE, line=dict(width=1.5, color="white")), name="kondisi 1981-2010 (model)", hovertemplate="%{y}<br>1981-2010: %{x:.1f}%<extra></extra>"))
                    fig.update_layout(title="Per kabupaten/kota", xaxis_title="% bulan kering", yaxis_title=""); tampil(fig, 460)
                    st.caption("**Cara membaca:** batang yang melewati berlian abu-abu = wilayah itu diproyeksikan lebih sering kering daripada 1981-2010. Rata-rata dari grid yang pusatnya jatuh di dalam wilayah.")
                else: st.info("Peringkat per kabupaten/kota muncul bila berkas banten_kabkota.geojson ada di folder hasil atau di sebelah berkas aplikasi.")

            st.download_button("Unduh tabel per grid untuk pilihan ini (CSV)", agg.drop(columns=["p_sangat"], errors="ignore").rename(columns={"p_kering": "bulan_kering_pct", "spi": "spi_median_rata2", "kering_model_pct": "baseline_model_pct", "kering_target_pct": f"baseline_{meta['target']}_pct", "selisih_pp": "selisih_poin"}).round(3).to_csv(index=False).encode("utf-8-sig"),
                               file_name=f"peta_kering_banten_{skala}_{etiket_th}.csv", mime="text/csv")
            with st.expander("Detail untuk peneliti: deret SPI bulanan dan pola bulanan dengan kisaran acak"):
                cE, cF = st.columns(2, gap="medium")
                with cE: tampil(grafik_profil(True), 460); st.caption("Pita abu-abu: kisaran acak kasar dari baseline untuk jumlah tahun terpilih. Batang di luar pita menyimpang lebih dari kisaran acak, tetapi itu belum tentu sinyal iklim (bisa variabilitas internal GCM atau prediktor).")
                with cF:
                    rt = regm.sort_values(["tahun", "bulan"]).reset_index(drop=True); thn = rt["tahun"].isin(tahun_pilih).to_numpy(); ok = rt["bulan"].isin(bulan).to_numpy() & thn
                    tgl = pd.to_datetime(dict(year=rt["tahun"], month=rt["bulan"], day=1)); sub = rt[ok]; fig = go.Figure()
                    fig.add_trace(go.Scatter(x=tgl, y=rt["spi_median"].where(thn), mode="lines", line=dict(color=C_ABU, width=1.5), name="semua bulan (tahun terpilih)", hovertemplate="%{x|%b %Y}: %{y:.2f}<extra></extra>"))
                    fig.add_trace(go.Scatter(x=tgl[ok], y=sub["spi_median"], mode="markers", marker=dict(color=TEAL, size=8), name="median (bulan terpilih)",
                                             error_y=dict(type="data", symmetric=False, array=(sub["spi_p90"] - sub["spi_median"]).to_numpy(), arrayminus=(sub["spi_median"] - sub["spi_p10"]).to_numpy(), color="rgba(15,139,141,0.55)", thickness=1.6, width=0),
                                             customdata=np.c_[sub["spi_p10"], sub["spi_p90"]], hovertemplate="%{x|%b %Y}<br><b>median %{y:.2f}</b><br>p10 %{customdata[0]:.2f} | p90 %{customdata[1]:.2f}<extra></extra>"))
                    fig.add_hline(y=-1, line_dash="dash", line_width=2.5, line_color="#e53935", annotation_text="ambang kering (-1)", annotation_position="bottom right"); fig.add_hline(y=0, line_color="#888", line_width=1)
                    fig.update_layout(title=f"Deret SPI bulanan wilayah ({skala}; garis tegak = p10-p90)", yaxis_title=f"{skala} rata-rata wilayah", hovermode="closest"); tampil(fig, 460)
                    st.caption("Satu titik = satu bulan dalam satu lintasan GCM. Tidak untuk dibaca sebagai ramalan bulan itu.")

# ---------------- tab 3: panduan & metode ----------------
with tab3:
    st.subheader("Apa itu SPI?")
    st.markdown("**SPI (Standardized Precipitation Index)** membandingkan curah hujan suatu periode dengan hujan yang biasanya terjadi di tempat dan waktu yang sama. Nilai 0 = normal, negatif = lebih kering, positif = lebih basah. "
                "Angka di belakang (3, 6, 12) adalah lama periode dalam bulan.")
    st.table(KATEGORI_SPI.set_index("Nilai SPI"))
    st.subheader("Istilah yang dipakai")
    st.markdown("- **Bulan kering:** bulan dengan SPI <= -1 pada satu petak (grid) peta. Angka '% bulan kering' = porsi petak-bulan yang kering.\n"
                "- **Poin (poin persentase):** selisih dua persentase. Dari 15% ke 17% = naik 2 poin.\n"
                "- **Kondisi 1981-2010 (menurut model):** seberapa sering model yang sama menghasilkan bulan kering pada 1981-2010. Ini pembanding utama karena model punya bias sendiri.\n"
                f"- **Data pengamatan ({meta['target']}):** frekuensi kering dari data hujan pengamatan pada periode yang sama; pembanding tambahan.\n"
                "- **Simulasi (anggota ensemble):** hasil model diulang beberapa kali dengan derau acak kecil. Sebaran antar simulasi **bukan** ukuran ketidakpastian iklim.\n"
                "- **Median, p10, p90:** nilai tengah simulasi, serta batas bawah dan atas yang mencakup 80% simulasi.")
    st.subheader("Cara membaca dengan benar")
    for c in meta["catatan"]: st.write("- " + c)
    st.subheader("Untuk peneliti: uji model dan data masukan")
    st.markdown(f"**Model:** {meta['model']} (set fitur {meta['set_fitur']}) · **Model iklim global:** {meta['gcm']} · **Skenario:** {meta['skenario']} · **Target kalibrasi:** {meta['target']} · **Status:** {meta['status_gerbang']}")
    st.markdown("**Gerbang model prediktor** (centang = lolos):")
    gb = pd.DataFrame(meta["gerbang"]).T.rename(columns={"a": "(a) skill sefase > 0", "b": "(b) distribusi <= 1,10 x klimatologi", "c": "(c) selisih kering <= 3 poin"}).replace({True: "✓ lolos", False: "✗ tidak"})
    st.dataframe(gb)
    st.markdown("**Baris prediktor GCM di luar rentang ERA5 (dipotong).** Makin tinggi, makin jauh proyeksi dari kondisi yang dipakai melatih model; itu sebabnya hasil dilaporkan hanya sampai " + str(h1) + ".")
    st.dataframe(pd.Series(meta["baris_prediktor_luar_rentang_pct"], name="% baris").to_frame().round(1))
    if "bulanan" in meta: st.caption(f"Baseline bulanan memakai periode {meta['bulanan']['baseline_periode'][0]}-{meta['bulanan']['baseline_periode'][1]}.")

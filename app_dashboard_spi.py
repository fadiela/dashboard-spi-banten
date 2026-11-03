"""Dashboard proyeksi SPI Banten 2026-2050 (membaca ekspor sel 14d, 14e, 14f notebook). Grafik interaktif (Plotly).
Jalankan:  HASIL_DIR=/jalur/ke/folder streamlit run app_dashboard_spi.py
Google Drive (opsional): atur DRIVE_FOLDER_ID (env atau Streamlit secrets) = ID folder Drive 'siapa saja dengan link'.
Wajib   : dashboard_tahunan_regional.csv, dashboard_tahunan_per_grid.csv, dashboard_meta.json (14d)
          dashboard_bulanan_regional.csv.gz, dashboard_bulanan_per_grid.csv.gz, dashboard_baseline_bulan_grid.csv.gz, dashboard_grid.csv (14e)
Opsional: dashboard_korelasi.csv, dashboard_korelasi_antar.csv (14g) | dashboard_model_banding.csv, dashboard_model_gerbang.csv, dashboard_sensitivitas.csv (14i, tab Bandingkan model) | banten_kabkota.geojson (batas wilayah)
"""
import html, json, os
import numpy as np, pandas as pd, streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Proyeksi kekeringan Banten 2026-2050", page_icon="🌧️", layout="wide")
st.markdown("""<style>
.kpi-grid {display: grid; gap: 12px; margin: 6px 0 12px 0;}
.kpi-grid.k3 {grid-template-columns: repeat(3, 1fr);}
@media (max-width: 700px) {.kpi-grid.k3 {grid-template-columns: 1fr;}}
.kpi {background: rgba(15,139,141,0.10); border: 1.5px solid rgba(15,139,141,0.55); border-radius: 12px; padding: 12px 14px; min-height: 100px; display: flex; flex-direction: column; justify-content: space-between;}
.kpi .l {font-size: 0.86rem; font-weight: 600; opacity: 0.85; line-height: 1.25;}
.kpi .v {font-size: 1.8rem; font-weight: 800; line-height: 1.15; margin: 4px 0;}
.kpi .s {font-size: 0.8rem; opacity: 0.75; line-height: 1.25;}
.badge {display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.76rem; font-weight: 600; margin: 2px 4px 2px 0; border: 1px solid;}
.badge.ok {background: rgba(46,125,50,0.14); border-color: rgba(46,125,50,0.6);} .badge.warn {background: rgba(245,124,0,0.14); border-color: rgba(245,124,0,0.7);} .badge.info {background: rgba(128,128,128,0.14); border-color: rgba(128,128,128,0.55);}
.banner {border-radius: 12px; padding: 11px 16px; margin: 8px 0 12px 0; font-size: 1.02rem; line-height: 1.4; border: 1.5px solid; background: rgba(15,139,141,0.10); border-color: rgba(15,139,141,0.55);}
.ins {border-left: 5px solid #0f8b8d; border-radius: 8px; padding: 8px 12px; margin: 2px 0 14px 0; background: rgba(15,139,141,0.07); font-size: 0.9rem; line-height: 1.4;}
.ins b {color: #0f8b8d;}
.tip {display: inline-block; position: relative; width: 17px; height: 17px; line-height: 17px; text-align: center; border-radius: 50%; margin-left: 7px; font-size: 0.72rem; font-weight: 700; background: rgba(128,128,128,0.28); cursor: help; flex: none;}
.tip .tt {display: none; position: absolute; left: -8px; bottom: 140%; width: 240px; padding: 8px 10px; border-radius: 9px; background: #263238; color: #fff; font-size: 0.8rem; font-weight: 400; line-height: 1.4; text-align: left; z-index: 99999; box-shadow: 0 4px 14px rgba(0,0,0,0.3); white-space: normal;}
.tip:hover .tt {display: block;} .tip.r .tt {left: auto; right: -8px;}
button[data-baseweb="tab"] p {font-weight: 700; font-size: 1.02rem;}
h5 {margin-top: 0.4rem;}
/* sidebar */
section[data-testid="stSidebar"] {background: linear-gradient(180deg, rgba(15,139,141,0.13) 0%, rgba(15,139,141,0.03) 55%); border-right: 1px solid rgba(15,139,141,0.28);}
.brand {background: linear-gradient(135deg, #0f8b8d, #0b6466); color: #fff; border-radius: 14px; padding: 14px 16px; margin: 4px 0 6px 0;}
.brand .b1 {font-size: 1.25rem; font-weight: 800; line-height: 1.2;} .brand .b2 {font-size: 0.82rem; opacity: 0.88; margin-top: 2px;}
.sbl {font-size: 0.72rem; letter-spacing: 0.07em; text-transform: uppercase; opacity: 0.65; font-weight: 700; margin: 16px 0 6px 0;}
.sbnote {font-size: 0.82rem; opacity: 0.8; line-height: 1.35; margin-top: 6px;}
.sbcard {border: 1px solid rgba(15,139,141,0.38); border-radius: 12px; padding: 10px 12px; background: rgba(15,139,141,0.07); font-size: 0.84rem; line-height: 1.55;}
.sbcard .k {opacity: 0.65;}
</style>""", unsafe_allow_html=True)

MON = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
PRESET = {"Sepanjang tahun": list(range(1, 13)), "Des-Feb (kira-kira musim hujan)": [12, 1, 2], "Mar-Mei (peralihan)": [3, 4, 5], "Jun-Agu (kira-kira musim kemarau)": [6, 7, 8], "Sep-Nov (peralihan)": [9, 10, 11], "Pilih bulan sendiri": None}
TEAL, TEAL_MUDA, ORANYE = "#0f8b8d", "rgba(15,139,141,0.18)", "#f57c00"
C_BASE, C_TARGET, C_ABU = "#7a7f87", "#d81b60", "#b5bac1"
PALET_MODEL = ["#5c6bc0", "#ab47bc", "#8d6e63", "#26a69a"]
SKALA_INFO = {"SPI-3": "3 bulan · cepat bereaksi, relevan untuk tanaman", "SPI-6": "6 bulan · gambaran satu musim", "SPI-12": "12 bulan · relevan untuk air tanah dan waduk"}
KATEGORI_SPI = pd.DataFrame({"Nilai SPI": ["2,0 atau lebih", "1,5 sampai 1,99", "1,0 sampai 1,49", "-0,99 sampai 0,99", "-1,0 sampai -1,49", "-1,5 sampai -1,99", "-2,0 atau kurang"],
                             "Kategori": ["Sangat basah (ekstrem)", "Sangat basah", "Cukup basah", "Normal", "Kering", "Sangat kering", "Kering ekstrem"],
                             "Dihitung 'kering'?": ["Tidak", "Tidak", "Tidak", "Tidak", "Ya", "Ya", "Ya"]})
PITA_SPI = [(-9, -2, "#8e0000", "Kering ekstrem"), (-2, -1.5, "#e53935", "Sangat kering"), (-1.5, -1, "#fb8c00", "Kering"), (-1, 1, None, "Normal"),
            (1, 1.5, "#9ccc65", "Cukup basah"), (1.5, 2, "#43a047", "Sangat basah"), (2, 9, "#1b5e20", "Basah ekstrem")]

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

# Sidebar: wadah dibuat dulu supaya urutannya tetap walau isinya diisi belakangan.
sb_atas, sb_info = st.sidebar.container(), st.sidebar.container()
with st.sidebar.expander("Pengaturan lanjutan"):
    pakai_dasar = st.toggle("Tampilkan peta dasar", value=True, help="Matikan bila ubin peta dari internet tidak tampil.")
    folder = st.text_input("Folder hasil", value=folder_awal)
    st.caption(f"Sumber data: {sumber}")
    if st.button("Muat ulang data"): st.cache_data.clear(); st.rerun()
gaya = "carto-positron" if pakai_dasar else None

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

@st.cache_data
def muat_banding(folder, versi=()):
    p = os.path.join(folder, "dashboard_model_banding.csv")
    return pd.read_csv(p) if os.path.exists(p) else None

@st.cache_data
def muat_csv(folder, nama, versi=()):
    p = os.path.join(folder, nama)
    return pd.read_csv(p) if os.path.exists(p) else None

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
    """Batas kabupaten/kota (opsional) dan pemetaan grid -> nama wilayah."""
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
                nama[dalam & (nama == None)] = nm       # noqa: E711
                if besar: label.append((nm, besar[1], besar[2]))
            return gj, pd.DataFrame({"grid_id": grid_ref["grid_id"].to_numpy(), "wilayah": nama}), pd.DataFrame(label, columns=["nama", "lon", "lat"])
    return None, pd.DataFrame({"grid_id": grid_ref["grid_id"].to_numpy(), "wilayah": None}), pd.DataFrame(columns=["nama", "lon", "lat"])

try:
    reg, grd, meta = muat(folder, versi_folder(folder))
except FileNotFoundError as e:
    st.error(f"Berkas ekspor tidak ditemukan di '{folder}'. Jalankan sel 14d notebook dulu. ({e.filename})"); st.stop()
VF = versi_folder(folder)
bln = muat_bulanan(folder, VF); kor, kor_antar = muat_korelasi(folder, VF); banding = muat_banding(folder, VF)
gerb, sens = muat_csv(folder, "dashboard_model_gerbang.csv", VF), muat_csv(folder, "dashboard_sensitivitas.csv", VF)
grid_ref = grd[["grid_id", "lat", "lon"]].drop_duplicates().sort_values("grid_id").reset_index(drop=True)
gj, wil_tab, wil_label = muat_wilayah(folder, VF, grid_ref)

# ---------------- pembantu teks dan angka ----------------
def n(x, d=1, plus=False):
    """Format angka gaya Indonesia (koma desimal)."""
    s = f"{x:+.{d}f}" if plus else f"{x:.{d}f}"
    return s.replace(".", ",")

def tafsir(selisih, se):
    """Selisih (poin) dianggap berarti bila > 2 x galat baku kasar naik-turun antar-tahun."""
    if not np.isfinite(se): return "sedikit", "Data terlalu sedikit untuk disimpulkan."
    if abs(selisih) < 2 * se: return "sama", "Masih dalam naik-turun alami antar-tahun, belum berarti."
    return ("lebih", "Bulan kering lebih sering dari 1981-2010.") if selisih > 0 else ("kurang", "Bulan kering lebih jarang dari 1981-2010.")

KET_KODE = {"sama": "belum berarti", "lebih": "lebih sering kering", "kurang": "lebih jarang kering", "sedikit": "data terlalu sedikit"}

def se_kasar(serie):
    s = pd.Series(serie).dropna(); return float(s.std(ddof=1) / np.sqrt(len(s))) if len(s) >= 3 else float("nan")

def tren_dekade(x, y):
    """Kemiringan OLS (poin per dekade) dan galat bakunya."""
    x, y = np.asarray(x, float), np.asarray(y, float); ok = np.isfinite(y); x, y = x[ok], y[ok]
    if len(x) < 6: return float("nan"), float("nan")
    b, a = np.polyfit(x, y, 1); res = y - (a + b * x)
    return float(b * 10), float(np.sqrt(res.var(ddof=2) / ((x - x.mean()) ** 2).sum()) * 10)

def _tip(tip, kanan=False):
    return f'<span class="tip{" r" if kanan else ""}">?<span class="tt">{html.escape(str(tip))}</span></span>' if tip else ""

def kartu(label, nilai, sub="", tip="", kanan=False):
    e = html.escape
    return f'<div class="kpi"><div class="l">{e(str(label))}{_tip(tip, kanan)}</div><div class="v">{e(str(nilai))}</div><div class="s">{e(str(sub)) if sub else "&nbsp;"}</div></div>'

def kpi_grid(daftar):
    st.markdown('<div class="kpi-grid k3">' + "".join(daftar) + "</div>", unsafe_allow_html=True)

def lencana(teks, jenis="ok"):
    return f'<span class="badge {jenis}">{html.escape(teks)}</span>'

def banner(teks_html, tip=""):
    st.markdown(f'<div class="banner"><span>{teks_html}</span>{_tip(tip, True)}</div>', unsafe_allow_html=True)

def ins(teks):
    """Satu kalimat insight di bawah grafik; dihitung dari data yang sedang ditampilkan."""
    st.markdown(f'<div class="ins"><b>Insight</b> · {html.escape(teks)}</div>', unsafe_allow_html=True)

def judul(teks, bantuan=None):
    st.markdown(f"##### {teks}", help=bantuan)

def segmen(label, opsi, key, default=None, format_func=None):
    """Pilihan bergaya tombol segmen (Streamlit baru); kembali ke radio horizontal bila belum tersedia."""
    default = default if default is not None else opsi[0]; ff = format_func or (lambda v: v)
    if hasattr(st, "segmented_control"):
        v = st.segmented_control(label, opsi, default=default, key=key, format_func=ff, label_visibility="collapsed")
        return default if v is None else v
    return st.radio(label, opsi, index=list(opsi).index(default), key=key, format_func=ff, horizontal=True, label_visibility="collapsed")

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
    """Batas skala warna mengikuti sebaran data (persentil ke-98)."""
    v = pd.Series(v).dropna().to_numpy()
    if v.size == 0: return 0, 1
    if mode == "pos": return 0, max(20.0, float(np.ceil(np.percentile(v, 98) / 10) * 10))
    lim = max(5.0, float(np.ceil(float(np.percentile(np.abs(v), 98)) / 5) * 5))
    return -lim, lim

def kotak_geojson(df, h):
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "id": str(int(g)), "properties": {}, "geometry": {"type": "Polygon", "coordinates": [[[lo - h, la - h], [lo + h, la - h], [lo + h, la + h], [lo - h, la + h], [lo - h, la - h]]]}}
                                                      for g, lo, la in zip(df["grid_id"], df["lon"], df["lat"])]}

def garis_batas_xy(gj):
    xs, ys = [], []
    for f in gj["features"]:
        for poly in _poligon_fitur(f["geometry"]):
            for ring in poly: a = np.asarray(ring, float); xs += a[:, 0].tolist() + [None]; ys += a[:, 1].tolist() + [None]
    return xs, ys

def peta(df, kol, warna, zmin, zmax, satuan, label, extra=(), zmid=None, gaya="carto-positron"):
    """Peta grid interaktif. gaya = gaya peta dasar atau None untuk kotak saja. extra = [(judul, kolom, satuan), ...] untuk tooltip."""
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
        if len(xs) * len(ys) <= 6 * len(df):
            ix, iy = np.searchsorted(xs, lon), np.searchsorted(ys, lat)
            def mat(k): m = np.full((len(ys), len(xs)), np.nan); m[iy, ix] = df[k].to_numpy(); return m
            cd = np.dstack([np.zeros_like(mat(kol)), np.zeros_like(mat(kol))] + [mat(k) for _, k, _ in extra])
            tr = go.Heatmap(x=xs, y=ys, z=mat(kol), customdata=cd, colorscale=warna, zmin=zmin, zmax=zmax, zmid=zmid, hoverongaps=False, hovertemplate=tip2 + "<extra></extra>", colorbar=dict(title=judul_cb))
        else:
            cd = np.c_[lon, lat, df[[k for _, k, _ in extra]].to_numpy()] if extra else np.c_[lon, lat]
            tr = go.Scatter(x=lon, y=lat, mode="markers", customdata=cd, marker=dict(symbol="square", size=10, color=df[kol], colorscale=warna, cmin=zmin, cmax=zmax, cmid=zmid, colorbar=dict(title=judul_cb)),
                            hovertemplate=tip2.replace("%{z", "%{marker.color") + "<extra></extra>")
        fig = go.Figure(tr); fig.update_layout(xaxis_title="bujur", yaxis_title="lintang"); fig.update_yaxes(scaleanchor="x", scaleratio=1)
        if gj is not None:
            bx, by = garis_batas_xy(gj); fig.add_trace(go.Scatter(x=bx, y=by, mode="lines", line=dict(color="#263238", width=1.5), hoverinfo="skip", showlegend=False))
    return fig

# ---------------- sidebar dan kepala halaman ----------------
h0, h1 = int(meta["horizon"][0]), int(meta["horizon"][1])
with sb_atas:
    st.markdown(f'<div class="brand"><div class="b1">🌧️ SPI Banten</div><div class="b2">Proyeksi kekeringan {h0}-{h1}</div></div><div class="sbl">Skala kekeringan</div>', unsafe_allow_html=True)
    skala = segmen("Skala SPI", list(meta["spi_skala"]), "skala_spi")
    st.markdown(f'<div class="sbnote">{html.escape(SKALA_INFO.get(skala, ""))}<br>Kering = SPI ≤ -1</div>', unsafe_allow_html=True)

SK = {}                                                   # ringkasan per skala SPI: proyeksi, baseline, selisih, galat baku kasar, kode tafsir
for s_ in meta["spi_skala"]:
    d_ = reg[reg["SPI"] == s_].sort_values("tahun"); kol_ = "kering_pct_mean" if "kering_pct_mean" in d_.columns else "kering_pct_median"; p_ = (meta.get("proyeksi_pct") or {}).get(s_)
    p_ = float(p_) if p_ is not None else float(np.average(d_[kol_], weights=d_["n_bulan_valid"])); b_ = float(meta["baseline_model_sendiri_pct"][s_]); se_ = se_kasar(d_[kol_])
    SK[s_] = dict(proy=p_, base=b_, sel=p_ - b_, se=se_, kode=tafsir(p_ - b_, se_)[0])
r = reg[reg["SPI"] == skala].sort_values("tahun"); base = SK[skala]["base"]; acuan = float(meta["acuan_target_pct"][skala]); rata, sel, kode = SK[skala]["proy"], SK[skala]["sel"], SK[skala]["kode"]
KOL_RATA = "kering_pct_mean" if "kering_pct_mean" in r.columns else "kering_pct_median"

lolos = str(meta["status_gerbang"]).startswith("lolos")
lr_ = meta.get("baris_prediktor_luar_rentang_pct") or {}; luar = lr_.get(f"{h0}-{h1}", next(iter(lr_.values()), None)) if lr_ else None
with sb_info:
    kartu_html = (f'<div class="sbl">Model</div><div class="sbcard"><b>{html.escape(str(meta["model"]).replace(" [mu+V1]", ""))}</b><br>'
                  f'<span class="k">GCM</span> {html.escape(str(meta["gcm"]))}<br><span class="k">Skenario</span> {html.escape(str(meta["skenario"]))}<br><span class="k">Target</span> {html.escape(str(meta["target"]))}<br>')
    ci_nol = bool(meta.get("ci_tingkat2_memuat_nol", False))
    kartu_html += lencana(("Lolos gerbang" + (" · CI memuat 0" if ci_nol else "")) if lolos else "Belum lolos gerbang", "ok" if (lolos and not ci_nol) else "warn")
    if luar is not None: kartu_html += lencana(f"Luar rentang latih {luar:.0f}%", "ok" if luar < 20 else "warn")
    if meta.get("versi_notebook"): kartu_html += f'<br><span class="k">Data</span> {html.escape(str(meta.get("tanggal_run", "")))} · {html.escape(str(meta["versi_notebook"]))}'
    st.markdown(kartu_html + "</div>", unsafe_allow_html=True)

st.title(f"Proyeksi kekeringan Banten {h0}-{h1}", help="Seberapa sering bulan kering (SPI ≤ -1) diproyeksikan dibanding 1981-2010 menurut model yang sama. Proyeksi bersyarat satu model dan satu skenario; satu tahun bukan ramalan.")
st.caption("Proyeksi sensitivitas bersyarat: satu GCM, satu skenario. Bukan prediksi iklim Banten.")
if not lolos: st.warning(f"Status model: **{meta['status_gerbang']}**. Baca sebagai proyeksi bersyarat.")

tab1, tab2, tab_m, tab_k, tab3 = st.tabs(["Ringkasan", "Peta & musim", "Bandingkan model", "Korelasi & validasi", "Panduan"])

# ---------------- tab 1: ringkasan ----------------
with tab1:
    banner(f"<b>{skala}:</b> {n(rata)}% bulan kering ({h0}-{h1}) vs {n(base)}% pada 1981-2010 · selisih <b>{n(sel, 1, True)} poin</b> ({KET_KODE[kode]})",
           tafsir(sel, SK[skala]["se"])[1] + " Poin = selisih dua persentase.")
    kpi_grid([kartu(f"Bulan kering {h0}-{h1}", f"{n(rata)}%", "rata-rata simulasi", "Rata-rata semua simulasi dan tahun."),
              kartu("Kondisi 1981-2010", f"{n(base)}%", "menurut model", "Baseline model yang sama, supaya bias model saling meniadakan."),
              kartu("Selisih", f"{n(sel, 1, True)} poin", KET_KODE[kode], "Berarti bila lebih dari 2x galat baku kasar antar-tahun.", True)])

    judul("Tiga skala SPI", "Selisih terhadap 1981-2010. Garis tegak = ±2 galat baku; bila menyentuh nol, belum berarti. Kotak tebal = skala terpilih.")
    sk_n = list(SK); fig = go.Figure(go.Bar(x=[f"{s_}<br>{n(SK[s_]['sel'], 1, True)} poin" for s_ in sk_n], y=[SK[s_]["sel"] for s_ in sk_n], marker_color=["#e57373" if SK[s_]["sel"] > 0 else "#64b5f6" for s_ in sk_n],
                           marker_line_width=[4 if s_ == skala else 0 for s_ in sk_n], marker_line_color="#263238",
                           error_y=dict(type="data", array=[2 * SK[s_]["se"] if np.isfinite(SK[s_]["se"]) else 0 for s_ in sk_n], color="#555", thickness=2, width=9), customdata=[[SK[s_]["proy"], SK[s_]["base"], KET_KODE[SK[s_]["kode"]]] for s_ in sk_n],
                           hovertemplate="proyeksi %{customdata[0]:.1f}% vs 1981-2010 %{customdata[1]:.1f}%<br>%{customdata[2]}<extra></extra>"))
    fig.add_hline(y=0, line_color="#555", line_width=1.5); fig.update_layout(yaxis_title="selisih (poin)", showlegend=False); tampil(fig, 280)
    berarti = [s_ for s_ in sk_n if SK[s_]["kode"] in ("lebih", "kurang")]
    ins((f"{', '.join(f'{s_} {KET_KODE[SK[s_]['kode']]}' for s_ in berarti)}" + ("; skala lain belum berarti. " if len(berarti) < len(sk_n) else ". ") if berarti else "Ketiga skala masih dalam naik-turun alami, belum ada perubahan berarti. ")
        + f"Terbesar: {max(sk_n, key=lambda s_: abs(SK[s_]['sel']))} ({n(SK[max(sk_n, key=lambda s_: abs(SK[s_]['sel']))]['sel'], 1, True)} poin).")

    inc = (r["n_bulan_valid"] < 12).to_numpy(); roll = r.set_index("tahun")["kering_pct_median"].rolling(5, center=True, min_periods=3).mean()
    judul("Bulan kering per tahun", "Titik di atas garis abu-abu = tahun itu lebih sering kering dari 1981-2010. Satu tahun = satu realisasi model. Penanda berlubang = tahun awal dengan bulan kosong."
          + (" (" + ", ".join(f"{int(t)}: {int(k)} bulan" for t, k in r.loc[r["n_bulan_valid"] < 12, ["tahun", "n_bulan_valid"]].to_numpy()) + ")" if inc.any() else ""))
    c1, c2 = st.columns(2); pita = c1.toggle("Sebaran simulasi", value=False, help="Pita p10-p90 antar simulasi. Hanya derau di sekitar nilai tengah yang sama, bukan ketidakpastian iklim."); tampil_obs = c2.toggle(f"Bandingkan {meta['target']}", value=False, help="Garis kondisi 1981-2010 dari data pengamatan.")
    fig = go.Figure()
    if pita:
        fig.add_trace(go.Scatter(x=r["tahun"], y=r["kering_pct_p10"], mode="lines", line=dict(width=0), name="p10", showlegend=False, hovertemplate="p10: %{y:.1f}%<extra></extra>"))
        fig.add_trace(go.Scatter(x=r["tahun"], y=r["kering_pct_p90"], mode="lines", line=dict(width=0), fill="tonexty", fillcolor=TEAL_MUDA, name="sebaran simulasi", hovertemplate="p90: %{y:.1f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=r["tahun"], y=r["kering_pct_median"], mode="lines+markers", line=dict(color=TEAL, width=3.5), marker=dict(size=9, symbol=np.where(inc, "circle-open", "circle").tolist()), customdata=r["n_bulan_valid"], name="proyeksi", hovertemplate="<b>proyeksi: %{y:.1f}%</b> (%{customdata} bulan valid)<extra></extra>"))
    fig.add_trace(go.Scatter(x=roll.index, y=roll.values, mode="lines", line=dict(color=ORANYE, width=3, dash="dashdot"), name="tren 5 tahun", hovertemplate="rata-rata 5 tahun: %{y:.1f}%<extra></extra>"))
    garis_acuan(fig, r["tahun"], base, "1981-2010 (model)", C_BASE, "dot")
    if tampil_obs: garis_acuan(fig, r["tahun"], acuan, f"1981-2010 ({meta['target']})", C_TARGET, "dash")
    fig.update_layout(hovermode="x unified", xaxis_title="tahun", yaxis_title="% bulan kering"); tampil(fig, 360)
    yy = r["kering_pct_median"]; ta, tb = r.loc[yy.idxmax()], r.loc[yy.idxmin()]; sl, se_sl = tren_dekade(r["tahun"], yy)
    txt_tren = "tanpa tren yang jelas" if not np.isfinite(sl) or abs(sl) < 2 * se_sl else f"cenderung {'naik' if sl > 0 else 'turun'} ({n(sl, 1, True)} poin per dekade)"
    ins(f"{skala}: {int((yy > base).sum())} dari {len(r)} tahun di atas baseline. Tertinggi {int(ta['tahun'])} ({n(ta['kering_pct_median'])}%), terendah {int(tb['tahun'])} ({n(tb['kering_pct_median'])}%). Deret {txt_tren}.")

    judul("Dua periode", "Apakah paruh kedua lebih kering dari paruh pertama? Geser tahun pemisah.")
    mid_def = h0 + (h1 - h0 + 1) // 2; pisah = st.slider("Pisah di tahun", h0 + 3, h1 - 3, mid_def)
    ra, rb = r[r["tahun"] < pisah], r[r["tahun"] >= pisah]
    ma, mb_ = float(np.average(ra[KOL_RATA], weights=ra["n_bulan_valid"])), float(np.average(rb[KOL_RATA], weights=rb["n_bulan_valid"]))
    k2, kal2 = tafsir(mb_ - ma, float(np.sqrt(se_kasar(ra[KOL_RATA]) ** 2 + se_kasar(rb[KOL_RATA]) ** 2))); la, lb = f"{h0}-{pisah - 1}", f"{pisah}-{h1}"
    fig = go.Figure(go.Bar(x=["1981-2010 (model)", la, lb], y=[base, ma, mb_], marker_color=[C_BASE, "#5bb5b6", TEAL], text=[f"{n(v)}%" for v in (base, ma, mb_)], textposition="outside", cliponaxis=False, hovertemplate="%{x}<br><b>%{y:.1f}%</b> bulan kering<extra></extra>"))
    fig.update_layout(yaxis_title="% bulan kering", yaxis_range=[0, max(base, ma, mb_) * 1.25], showlegend=False); tampil(fig, 280)
    ins(f"{skala}: {lb} {n(mb_)}% vs {la} {n(ma)}% (selisih {n(mb_ - ma, 1, True)} poin, {KET_KODE[k2]}). " + ("Perbedaan antar-periode bisa saja variasi alami model." if k2 != "sama" else kal2))

    dl = r[[c for c in ["tahun", "n_bulan_valid", "kering_pct_p10", "kering_pct_mean", "kering_pct_median", "kering_pct_p90", "spi_rata2_median"] if c in r.columns]].rename(columns={"n_bulan_valid": "jumlah_bulan_valid", "kering_pct_p10": "bulan_kering_pct_p10", "kering_pct_mean": "bulan_kering_pct_rata2", "kering_pct_median": "bulan_kering_pct_median", "kering_pct_p90": "bulan_kering_pct_p90"})
    st.download_button("Unduh tabel tahunan (CSV)", dl.to_csv(index=False).encode("utf-8-sig"), file_name=f"proyeksi_kering_banten_{skala}.csv", mime="text/csv")
    with st.expander("Tabel tiga skala"):
        rows = [{"Skala": s, f"Proyeksi {h0}-{h1} (%)": round(v["proy"], 1), "Baseline model 1981-2010 (%)": round(v["base"], 1), f"Acuan {meta['target']} (%)": round(float(meta["acuan_target_pct"][s]), 1), "Selisih (poin)": round(v["sel"], 1)} for s, v in SK.items()]
        st.dataframe(pd.DataFrame(rows).set_index("Skala"))

# ---------------- tab 2: peta & musim ----------------
KET_PETA = {"Seberapa sering kering": "pos", "Dibanding 1981-2010": "pp"}
TIP_PETA = {"pos": "Makin merah = makin sering bulan kering.", "pp": "Merah = lebih sering kering dari 1981-2010, biru = lebih jarang."}

def ringkas_wilayah(agg, kolom, mode):
    """Kalimat insight peta: wilayah (atau grid) tertinggi dan terendah, atau 'seragam' bila sebarannya sempit."""
    sat = " poin" if mode == "pp" else "%"; f = lambda v: n(v, 1, mode == "pp") + sat
    if gj is not None and "wilayah" in agg.columns and agg["wilayah"].notna().any():
        w = agg.dropna(subset=["wilayah"]).groupby("wilayah")[kolom].mean().sort_values(); nm_hi, nm_lo, v_hi, v_lo = w.index[-1], w.index[0], w.iloc[-1], w.iloc[0]
        if len(w) < 2: return ""
    else:
        a = agg.sort_values(kolom); nm_lo, nm_hi, v_lo, v_hi = f"grid {a.iloc[0]['lat']:.2f}°, {a.iloc[0]['lon']:.2f}°", f"grid {a.iloc[-1]['lat']:.2f}°, {a.iloc[-1]['lon']:.2f}°", a.iloc[0][kolom], a.iloc[-1][kolom]
    if v_hi - v_lo < 2: return "Hampir seragam antar wilayah (selisih terbesar kurang dari 2 poin)."
    return f"Tertinggi di {nm_hi} ({f(v_hi)}), terendah di {nm_lo} ({f(v_lo)})."

with tab2:
    if bln is None:
        st.info("Ekspor bulanan belum ada (sel 14e), jadi hanya peta per tahun yang tersedia.")
        gt_ = sorted(grd["tahun"].unique().tolist()); tahun = st.select_slider("Tahun", gt_, value=gt_[0]); g = grd[(grd["SPI"] == skala) & (grd["tahun"] == tahun)].dropna(subset=["kering_pct"]).merge(wil_tab, on="grid_id", how="left")
        if g.empty: st.warning("Tidak ada nilai untuk pilihan ini.")
        else:
            tampil(peta(g, "kering_pct", "YlOrRd", 0, 100, "%", "% bulan kering", gaya=gaya), 500); ins(ringkas_wilayah(g, "kering_pct", "pos") or f"Rata-rata {n(g['kering_pct'].mean())}% bulan kering.")
    else:
        regm, grdm, basem, grid = bln
        regm, grdm, basem = (d[d["SPI"] == skala] for d in (regm, grdm, basem)); grid = grid.merge(wil_tab, on="grid_id", how="left")
        daftar_th = sorted(regm["tahun"].unique().tolist())
        kp, kr = st.columns([1, 2], gap="medium")
        with kp:
            with st.container(border=True):
                st.markdown("**Pilihan**")
                th0, th1 = st.select_slider("Rentang tahun", daftar_th, value=(daftar_th[0], daftar_th[-1]), help="Satukan kedua ujung untuk satu tahun.")
                tahun_pilih = [t for t in daftar_th if th0 <= t <= th1]
                pilih = st.selectbox("Bulan atau musim", list(PRESET), help="Musim di Banten hanya perkiraan kasar.")
                bulan = PRESET[pilih] if PRESET[pilih] is not None else [MON.index(m) + 1 for m in st.multiselect("Pilih bulan", MON, default=MON[5:9], key="bulan_multi")]
                st.markdown("**Tampilan peta**"); ket = segmen("Tampilan peta", list(KET_PETA), "mode_peta")
                dalam_saja = st.toggle("Hanya grid dalam batas Banten", value=False, disabled=gj is None, help="Sebagian grid berada di laut atau provinsi tetangga." if gj is not None else "Perlu berkas banten_kabkota.geojson.")
        gs = grdm[grdm["tahun"].isin(tahun_pilih) & grdm["bulan"].isin(bulan)] if (bulan and tahun_pilih) else grdm.iloc[0:0]
        if gs.empty:
            with kr:
                if not bulan: st.warning("Pilih minimal satu bulan.")
                elif not tahun_pilih: st.warning("Pilih minimal satu tahun.")
                else: st.warning("Tidak ada data untuk pilihan ini (mis. SPI-12 belum terisi pada bulan awal 2026).")
        else:
            etiket_th = f"{tahun_pilih[0]}-{tahun_pilih[-1]}" if len(tahun_pilih) > 1 else str(tahun_pilih[0])
            etiket_bl = pilih.split(" (")[0] if pilih != "Pilih bulan sendiri" else ", ".join(MON[b - 1] for b in bulan)
            agg = gs.groupby("grid_id").agg(p_kering=("p_kering", "mean"), p_sangat=("p_sangat_kering", "mean"), spi=("spi_median", "mean")).reset_index(); agg[["p_kering", "p_sangat"]] *= 100
            bs = basem[basem["bulan"].isin(bulan)].groupby("grid_id")[["kering_model_pct", "kering_target_pct"]].mean().reset_index()
            agg = agg.merge(bs, on="grid_id").merge(grid, on="grid_id"); agg["selisih_pp"] = agg["p_kering"] - agg["kering_model_pct"]
            if dalam_saja: agg = agg[agg["wilayah"].notna()]
            if gj is None: agg = agg.drop(columns="wilayah")
            if dalam_saja: gs = gs[gs["grid_id"].isin(agg["grid_id"])]
            fk, fb = agg["p_kering"].mean(), agg["kering_model_pct"].mean(); sel_b = fk - fb
            per_th = gs.groupby("tahun")["p_kering"].mean() * 100; kb, kal_b = tafsir(sel_b, se_kasar(per_th))
            with kr:
                st.markdown(f"**{etiket_bl} · {etiket_th} · {skala}**")
                kpi_grid([kartu("Kering", f"{n(fk)}%", "proyeksi", "Peluang bulan kering, rata-rata semua simulasi."), kartu("Kondisi 1981-2010", f"{n(fb)}%", "model, bulan sama", "Baseline model untuk bulan yang sama."),
                          kartu("Selisih", f"{n(sel_b, 1, True)} poin", KET_KODE[kb], "Proyeksi dikurangi baseline model.", True)])
            ekstra = [("Kondisi 1981-2010 (model)", "kering_model_pct", "%"), (f"Pengamatan {meta['target']}", "kering_target_pct", "%"), ("Sangat kering", "p_sangat", "%")]
            mode_k = KET_PETA[ket]; cA, cB = st.columns(2, gap="medium")
            with cA:
                if mode_k == "pos": z0, z1 = batas_skala(agg["p_kering"], "pos"); fg = peta(agg, "p_kering", "YlOrRd", z0, z1, "%", "Frekuensi kering", ekstra, gaya=gaya); kol_ins = "p_kering"
                else: z0, z1 = batas_skala(agg["selisih_pp"], "pp"); fg = peta(agg, "selisih_pp", "RdBu_r", z0, z1, " poin", "Selisih vs 1981-2010", ekstra, zmid=0, gaya=gaya); kol_ins = "selisih_pp"
                judul(f"Peta: {ket}", TIP_PETA[mode_k] + " Skala warna menyesuaikan data."); tampil(fg, 440)
                ins(f"{kal_b} " + ringkas_wilayah(agg, kol_ins, mode_k))
            with cB:
                judul("Per tahun", "Batang di atas garis putus-putus = tahun itu lebih sering kering dari 1981-2010.")
                fig = go.Figure(go.Bar(x=per_th.index, y=per_th.values, marker_color=TEAL, name="proyeksi", hovertemplate="Tahun %{x}<br><b>%{y:.1f}%</b> bulan kering<extra></extra>"))
                garis_acuan(fig, list(per_th.index), fb, "1981-2010 (model)", C_BASE, "dot")
                fig.update_layout(xaxis_title="tahun", yaxis_title="% bulan kering", hovermode="x unified"); tampil(fig, 440)
                if len(per_th) > 1: ins(f"{int((per_th > fb).sum())} dari {len(per_th)} tahun di atas baseline. Tertinggi {int(per_th.idxmax())} ({n(per_th.max())}%), terendah {int(per_th.idxmin())} ({n(per_th.min())}%).")
                else: ins(f"Satu tahun ({int(per_th.index[0])}): {n(per_th.iloc[0])}% vs baseline {n(fb)}%. Satu tahun hanya satu realisasi model.")

            cC, cD = st.columns(2, gap="medium")
            with cC:
                judul("Pola per bulan", "Batang teal = bulan terpilih; garis abu-abu = 1981-2010 (model).")
                gt = grdm[grdm["tahun"].isin(tahun_pilih)]; prof = gt.groupby("bulan")["p_kering"].mean() * 100; bb = basem.groupby("bulan")[["kering_model_pct"]].mean()
                fig = go.Figure(go.Bar(x=[MON[b - 1] for b in prof.index], y=prof.values, marker_color=[TEAL if b in bulan else C_ABU for b in prof.index], name="proyeksi", hovertemplate="%{x}<br><b>%{y:.1f}%</b> bulan kering<extra></extra>"))
                fig.add_trace(go.Scatter(x=[MON[b - 1] for b in bb.index], y=bb["kering_model_pct"], mode="lines+markers", line=dict(color=C_BASE, dash="dot", width=3), marker=dict(size=7), name="1981-2010 (model)", hovertemplate="%{x}: %{y:.1f}%<extra>model</extra>"))
                fig.update_layout(xaxis_title="bulan", yaxis_title="% bulan kering", hovermode="x unified"); tampil(fig, 400)
                dif = (prof - bb["kering_model_pct"].reindex(prof.index)).dropna()
                ins(f"Paling sering kering: {MON[int(prof.idxmax()) - 1]} ({n(prof.max())}%); paling jarang: {MON[int(prof.idxmin()) - 1]} ({n(prof.min())}%). Beda terbesar dari baseline: {MON[int(dif.abs().idxmax()) - 1]} ({n(dif[dif.abs().idxmax()], 1, True)} poin).")
            with cD:
                judul("Per kabupaten/kota", "Berlian abu-abu = 1981-2010 (model). Rata-rata grid yang pusatnya di dalam wilayah.")
                if gj is not None and agg["wilayah"].notna().any():
                    rk = agg.dropna(subset=["wilayah"]).groupby("wilayah")[["p_kering", "kering_model_pct"]].mean().sort_values("p_kering"); fig = go.Figure()
                    fig.add_trace(go.Bar(y=rk.index, x=rk["p_kering"], orientation="h", marker_color=TEAL, name="proyeksi", hovertemplate="%{y}<br><b>%{x:.1f}%</b> bulan kering<extra></extra>"))
                    fig.add_trace(go.Scatter(y=rk.index, x=rk["kering_model_pct"], mode="markers", marker=dict(symbol="diamond", size=13, color=C_BASE, line=dict(width=1.5, color="white")), name="1981-2010 (model)", hovertemplate="%{y}<br>1981-2010: %{x:.1f}%<extra></extra>"))
                    fig.update_layout(xaxis_title="% bulan kering", yaxis_title=""); tampil(fig, 400)
                    dk = rk["p_kering"] - rk["kering_model_pct"]
                    ins(f"{int((dk > 0).sum())} dari {len(rk)} wilayah di atas baseline. Paling sering kering: {rk.index[-1]} ({n(rk['p_kering'].iloc[-1])}%); paling jarang: {rk.index[0]} ({n(rk['p_kering'].iloc[0])}%).")
                else: st.info("Perlu berkas banten_kabkota.geojson.")

            st.download_button("Unduh tabel per grid (CSV)", agg.drop(columns=["p_sangat"], errors="ignore").rename(columns={"p_kering": "bulan_kering_pct", "spi": "spi_median_rata2", "kering_model_pct": "baseline_model_pct", "kering_target_pct": f"baseline_{meta['target']}_pct", "selisih_pp": "selisih_poin"}).round(3).to_csv(index=False).encode("utf-8-sig"),
                               file_name=f"peta_kering_banten_{skala}_{etiket_th}.csv", mime="text/csv")
            with st.expander("Deret SPI bulanan"):
                judul("Deret SPI bulanan", "Satu titik = satu bulan dalam satu lintasan model, bukan ramalan. Garis tegak = p10-p90. Garis merah putus-putus = ambang kering (-1).")
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
                fig.update_layout(yaxis_title=f"{skala} rata-rata wilayah", hovermode="closest"); tampil(fig, 400)
                if len(sub): ins(f"{int((sub['spi_median'] <= -1).sum())} dari {len(sub)} bulan terpilih punya SPI median ≤ -1. Terendah {n(sub['spi_median'].min(), 2)} ({tgl[ok][sub['spi_median'].idxmin()]:%b %Y}).")

# ---------------- tab bandingkan model ----------------
with tab_m:
    if banding is None:
        st.info("Berkas dashboard_model_banding.csv belum ada. Jalankan sel 14i-3 notebook, lalu 14f.")
    else:
        bd = banding.copy()
        if "jenis" not in bd.columns: bd["jenis"] = "model P"
        st.caption("Model utama dipilih oleh aturan gerbang yang ditetapkan sebelum hasil dilihat, bukan terbukti terbaik. Model lain hanya pembanding.")

        # --- 1. gerbang ---
        if gerb is not None:
            judul("Gerbang model", "(a) skill sefase > 0 (ERA5). (b) rasio sebaran terhadap klimatologi <= 1,10 (prediktor GCM). (c) selisih frekuensi kering SPI-3 dari pengamatan <= 3 poin. Kolom terakhir: apakah sebaran model sudah terbedakan dari klimatologi (CI bootstrap).")
            ci_ = gerb["ci_qq_memuat_nol"].fillna(True).astype(bool) if "ci_qq_memuat_nol" in gerb.columns else pd.Series(True, index=gerb.index)
            acu = float(gerb["acuan_c"].iloc[0]); sel_c = (gerb["c_kering_pct"] - acu).abs()
            tg = pd.DataFrame({"Model": gerb["model"], "(a) skill sefase (>0)": gerb["a_crpss_t1"].round(3), "(b) rasio sebaran (<=1,10)": gerb["b_qq_rasio"].round(2), "(c) selisih kering (<=3 poin)": sel_c.round(1),
                               "Lolos": gerb["kriteria_lolos"].astype(int).astype(str) + "/3", "Sebaran vs klimatologi": np.where(ci_, "belum terbedakan", "terbedakan")}).set_index("Model")
            st.dataframe(tg)
            mu_ = gerb[gerb["tampil"].astype(bool)].iloc[0]; mc = abs(float(mu_["c_kering_pct"]) - acu)
            ins(f"{int(gerb['lolos'].astype(bool).sum())} dari {len(gerb)} model lolos penuh. Margin kriteria (c) {mu_['model']}: {n(mc)} dari batas 3 poin. "
                + (f"Pada sebaran Tingkat 2, {int(ci_.sum())} dari {len(gerb)} model belum terbedakan dari klimatologi (CI memuat 0)." if ci_.any() else "Semua model terbedakan dari klimatologi pada sebaran Tingkat 2."))

        # --- 2. selisih per model ---
        b = bd[bd["SPI"] == skala]; urut = list(b.sort_values(["jenis", "tampil"], ascending=[False, False])["model"].unique())
        ok_n = {m: b[b["model"] == m]["kriteria_lolos"].iloc[0] for m in urut}; ref_m = {m for m in urut if str(b[b["model"] == m]["jenis"].iloc[0]) == "referensi"}
        lab = lambda m: f"{m} (referensi)" if m in ref_m else f"{m} ({int(ok_n[m])}/3)"
        nama_tampil = next((m for m in urut if bool(b[b["model"] == m]["tampil"].iloc[0])), urut[0])
        judul(f"Selisih terhadap baseline · {skala}", "Hanya model utama yang dipakai di tab lain. Garis tegak = ±2 galat baku kasar antar-tahun. QDM = koreksi bias GCM tanpa ML, dibanding CHIRPS 1981-2010.")
        pilih_m = st.multiselect("Model", urut, default=urut, format_func=lambda m: lab(m) + (" · dipakai di dashboard" if m == nama_tampil else ""))
        rs = []
        for m in pilih_m:
            d = b[b["model"] == m].sort_values("tahun"); bm = float(d["baseline_model_sendiri_pct"].iloc[0]); p = float(np.average(d["kering_pct_mean"], weights=d["n_bulan_valid"])); se_ = se_kasar(d["kering_pct_mean"])
            rs.append(dict(m=m, sel=p - bm, se=se_, kode=tafsir(p - bm, se_)[0], d=d, bm=bm, p=p))
        if not rs: st.warning("Pilih minimal satu model.")
        else:
            warna_m = lambda m: TEAL if m == nama_tampil else ORANYE if m in ref_m else C_ABU
            fig = go.Figure(go.Bar(x=[lab(x["m"]) for x in rs], y=[x["sel"] for x in rs], marker_color=[warna_m(x["m"]) for x in rs],
                                   error_y=dict(type="data", array=[2 * x["se"] if np.isfinite(x["se"]) else 0 for x in rs], color="#555", thickness=2, width=9), customdata=[[x["p"], x["bm"], KET_KODE[x["kode"]]] for x in rs],
                                   text=[n(x["sel"], 1, True) for x in rs], textposition="outside", cliponaxis=False, hovertemplate="proyeksi %{customdata[0]:.1f}% vs baseline %{customdata[1]:.1f}%<br>%{customdata[2]}<extra></extra>"))
            fig.add_hline(y=0, line_color="#555", line_width=1.5); fig.update_layout(yaxis_title="selisih (poin)", showlegend=False); tampil(fig, 320)
            mp_ = [x for x in rs if x["m"] not in ref_m]; sels = [x["sel"] for x in mp_] or [0.0]; n_b = sum(x["kode"] in ("lebih", "kurang") for x in mp_)
            qd = next((x for x in rs if x["m"] in ref_m), None)
            ins(f"Model P: selisih {n(min(sels), 1, True)} sampai {n(max(sels), 1, True)} poin; " + (f"{n_b} dari {len(mp_)} melewati kisaran alami" if n_b else "tak satu pun melewati kisaran alami") + (", arah tidak seragam. " if len({int(np.sign(s)) for s in sels}) > 1 else ", arah searah. ")
                + (f"QDM (GCM mentah) {n(qd['sel'], 1, True)} poin, {KET_KODE[qd['kode']]}." if qd else ""))

            judul("Selisih per tahun", "Rata-rata 5 tahun dari selisih terhadap baseline masing-masing; 0 = sama dengan 1981-2010. Model punya bias berbeda, jadi yang dibandingkan adalah selisihnya.")
            fig = go.Figure()
            for i, x in enumerate(rs):
                y = (x["d"]["kering_pct_mean"] - x["bm"]).rolling(5, center=True, min_periods=3).mean()
                fig.add_trace(go.Scatter(x=x["d"]["tahun"], y=y, mode="lines", name=lab(x["m"]), line=dict(color=warna_m(x["m"]) if x["m"] == nama_tampil or x["m"] in ref_m else PALET_MODEL[i % len(PALET_MODEL)], width=4 if x["m"] == nama_tampil else 2, dash="solid" if x["m"] == nama_tampil else "dash"),
                                         hovertemplate="%{y:+.1f} poin<extra>" + x["m"] + "</extra>"))
            fig.add_hline(y=0, line_color="#555", line_width=1.5); fig.update_layout(hovermode="x unified", xaxis_title="tahun", yaxis_title="selisih (poin)"); tampil(fig, 340)
            akhir = {x["m"]: float((x["d"]["kering_pct_mean"] - x["bm"]).rolling(5, center=True, min_periods=3).mean().iloc[-3]) for x in rs}
            ins(f"Menjelang akhir periode, {max(akhir, key=akhir.get)} paling condong kering ({n(max(akhir.values()), 1, True)} poin) dan {min(akhir, key=akhir.get)} paling jarang ({n(min(akhir.values()), 1, True)} poin).")

        # --- 3. sensitivitas pemotongan ---
        if sens is not None:
            VAR = ["Dipotong (dipakai di dashboard)", "Tanpa pemotongan", "Hanya prediktor stabil"]
            judul("Uji sensitivitas pemotongan prediktor", "Perubahan rata-rata hujan model (%, bukan frekuensi kering) pada jendela dilaporkan vs 1981-2010, dengan tiga perlakuan prediktor GCM. Prediktor dipotong ke rentang ERA5 supaya model tidak mengekstrapolasi.")
            sm = sens[sens["model"] != "Hujan GCM mentah"]; g_ = sens[sens["model"] == "Hujan GCM mentah"]["delta_mu_pct"]; fig = go.Figure()
            for v, wr in zip(VAR, [TEAL, ORANYE, "#5c6bc0"]):
                dv = sm[sm["varian"] == v]
                if not dv.empty: fig.add_trace(go.Bar(x=dv["model"], y=dv["delta_mu_pct"], name=v, marker_color=wr, hovertemplate="%{x}<br><b>%{y:+.1f}%</b><extra>" + v + "</extra>"))
            if len(g_): fig.add_hline(y=float(g_.iloc[0]), line_dash="dash", line_width=2.5, line_color=C_TARGET, annotation_text="hujan GCM mentah", annotation_position="top left")
            fig.add_hline(y=0, line_color="#555", line_width=1.5); fig.update_layout(barmode="group", yaxis_title="perubahan hujan (%)"); tampil(fig, 340)
            pv = sm.pivot(index="model", columns="varian", values="delta_mu_pct"); gv = float(g_.iloc[0]) if len(g_) else float("nan")
            teks = []
            if VAR[0] in pv and VAR[1] in pv:
                beda = [m for m in pv.index if np.sign(pv.loc[m, VAR[0]]) != np.sign(pv.loc[m, VAR[1]])]
                teks.append(f"Tanpa pemotongan, tanda perubahan berbeda di {len(beda)} dari {len(pv)} model" + (f" ({', '.join(beda)})" if beda else "") + f"; selisih rata-rata {n(float((pv[VAR[1]] - pv[VAR[0]]).abs().mean()))} poin persen.")
            if VAR[2] in pv: teks.append(f"Dengan prediktor stabil saja, {int((np.sign(pv[VAR[2]]) == np.sign(pv[VAR[0]])).sum())} dari {len(pv)} model tetap searah dengan versi dipotong.")
            if np.isfinite(gv): teks.append(f"Hujan GCM mentah {n(gv, 1, True)}%; model dipotong searah dengannya di {int((np.sign(pv[VAR[0]]) == np.sign(gv)).sum())} dari {len(pv)} model.")
            tdk = meta.get("prediktor_tidak_stabil")
            if tdk: teks.append("Prediktor tidak stabil: " + ", ".join(tdk) + ".")
            ins(" ".join(teks))

# ---------------- tab korelasi & validasi ----------------
with tab_k:
    if kor is None:
        st.info("Berkas korelasi belum ada (sel 14g notebook).")
    else:
        mk = meta.get("korelasi", {}); rk = float(kor["r_kritis_p05"].iloc[0]); nm_model = mk.get("model", "model terpilih"); ada_m = "r_model_t1" in kor.columns
        n_g = int(kor["lolos_fdr_gcm_target"].sum()); n_m = int(kor["lolos_fdr_model_t1"].sum()) if ada_m else None
        banner(f"Korelasi nyata dengan {meta['target']}: <b>GCM mentah {n_g}/{len(kor)}</b>" + (f" · <b>model ERA5 {n_m}/{len(kor)}</b>" if n_m is not None else ""),
               "Hanya uji yang tetap nyata setelah koreksi uji berganda (FDR) dihitung. GCM berjalan bebas sehingga tidak sefase dengan kejadian nyata; karena itu model dilatih dengan ERA5.")
        pil = segmen("Skala waktu", ["Per bulan", "Per musim dan tahunan"], "kor_skala"); d = kor[kor["jenis"].isin(["bulan"] if pil == "Per bulan" else ["musim", "tahunan"])]; musim = pil != "Per bulan"
        judul(f"Korelasi dengan {meta['target']}", f"Batang di luar garis putus-putus (±{n(rk, 2)}) nyata sebelum koreksi; ★ = tetap nyata setelah koreksi. Abu-abu = hujan GCM, teal = model ERA5 (data uji tak terlihat model)." + (" Jingga = kontrol indeks ERA5." if musim else ""))
        def batang(y, lolos, nama, warna):
            return go.Bar(x=d["unit"], y=d[y], name=nama, marker_color=warna, text=["★" if (pd.notna(v) and bool(v)) else "" for v in d[lolos]] if lolos in d.columns else None, textposition="outside", textfont=dict(size=16), hovertemplate="%{x}<br><b>r = %{y:.2f}</b><extra>" + nama + "</extra>")
        fig = go.Figure(); fig.add_trace(batang("r_gcm_target", "lolos_fdr_gcm_target", "Hujan GCM", C_BASE))
        if ada_m: fig.add_trace(batang("r_model_t1", "lolos_fdr_model_t1", f"Model {nm_model} (ERA5)", TEAL))
        if musim and "r_oof_indeks_era5_musiman" in d.columns: fig.add_trace(batang("r_oof_indeks_era5_musiman", "lolos_fdr_indeks_era5_musiman", "Kontrol: indeks ERA5", ORANYE))
        for yy_ in (rk, -rk): fig.add_hline(y=yy_, line_dash="dot", line_width=1.5, line_color="#555")
        fig.add_hline(y=0, line_color="#888", line_width=1); fig.update_layout(barmode="group", yaxis_title="korelasi (r)", yaxis_range=[-0.65, 1.05], hovermode="x unified"); tampil(fig, 380)
        ig = d["r_gcm_target"].abs().idxmax(); t_g = f"GCM: {int(d['lolos_fdr_gcm_target'].sum())} dari {len(d)} uji nyata, |r| terbesar {n(abs(d.loc[ig, 'r_gcm_target']), 2)} ({d.loc[ig, 'unit']})"
        t_m = f"; model ERA5: {int(d['lolos_fdr_model_t1'].sum())} dari {len(d)} nyata, |r| terbesar {n(d['r_model_t1'].abs().max(), 2)}" if ada_m else ""
        ins(t_g + t_m + f". Batas kritis {n(rk, 2)}.")
        with st.expander("Angka lengkap"):
            tb = kor.rename(columns={"r_gcm_target": "r GCM-target", "p_gcm_target": "p GCM-target", "lolos_fdr_gcm_target": "lolos FDR (GCM)", "r_model_t1": "r model (T1)", "p_model_t1": "p model (T1)", "lolos_fdr_model_t1": "lolos FDR (model)",
                                     "r_oof_indeks_era5_musiman": "r ERA5 (kontrol)", "r_oof_indeks_gcm_musiman": "r indeks GCM", "r_oof_pr_gcm_musiman": "r pr GCM (musiman)"})
            st.dataframe(tb[[c for c in ["unit", "jenis", "r GCM-target", "p GCM-target", "lolos FDR (GCM)", "r model (T1)", "p model (T1)", "lolos FDR (model)", "r ERA5 (kontrol)", "r indeks GCM", "r pr GCM (musiman)"] if c in tb.columns]].set_index("unit").round(3))
            st.download_button("Unduh tabel korelasi (CSV)", kor.to_csv(index=False).encode("utf-8-sig"), file_name="korelasi_bulan_musim_banten.csv", mime="text/csv")
        if kor_antar is not None:
            with st.expander("Persistensi: apakah bulan basah diikuti bulan basah?"):
                jp = segmen("Persistensi", ["antar-bulan", "antar-musim"], "kor_antar_jenis", format_func=lambda v: {"antar-bulan": "Antar-bulan", "antar-musim": "Antar-musim"}[v])
                da = kor_antar[kor_antar["jenis"] == jp]; cols = st.columns(2, gap="medium"); ring = []
                for cc, sumber_ in zip(cols, da["sumber"].unique()):
                    M = da[da["sumber"] == sumber_].pivot(index="baris", columns="kolom", values="r"); urut_ = list(dict.fromkeys(da["baris"])); M = M.loc[urut_, urut_]
                    off = M.to_numpy()[np.triu_indices(len(urut_), 1)]; ring.append((sumber_, float(np.mean(off)), float(np.max(off))))
                    with cc:
                        fg = go.Figure(go.Heatmap(z=M.to_numpy(), x=urut_, y=urut_, colorscale="RdBu_r", zmin=-0.7, zmax=0.7, zmid=0, colorbar=dict(title="r"), texttemplate="%{z:.2f}" if len(urut_) <= 4 else None, hovertemplate="%{y} dan %{x}<br><b>r = %{z:.2f}</b><extra></extra>"))
                        fg.update_layout(title=dict(text=sumber_, font=dict(size=14))); fg.update_yaxes(autorange="reversed"); tampil(fg, 340, atas=40)
                ins("Rata-rata korelasi antar-sel: " + "; ".join(f"{a} {n(m_, 2, True)}" for a, m_, _ in ring) + ". Galat baku tiap korelasi sekitar 0,17, jadi selisih kecil jangan ditafsirkan.")

# ---------------- tab panduan ----------------
with tab3:
    with st.expander("Cara membaca (1 menit)", expanded=True):
        st.markdown("1. Pilih **skala SPI** di panel kiri.\n2. **Ringkasan:** apakah bulan kering lebih sering dari 1981-2010.\n3. **Peta & musim:** pilih tahun dan musim, lihat di mana kering lebih sering.\n"
                    "4. **Bandingkan model:** model lain sebagai pembanding.\n5. Kotak **Insight** di bawah grafik berubah mengikuti pilihanmu. Satu tahun bukan ramalan.")
    with st.expander("Apa itu SPI?"):
        st.markdown("**SPI** membandingkan hujan suatu periode dengan hujan biasanya. 0 = normal, negatif = lebih kering. Angka 3, 6, 12 = lama periode (bulan).")
        st.table(KATEGORI_SPI.set_index("Nilai SPI"))
    with st.expander("Istilah"):
        st.markdown("- **Bulan kering:** SPI ≤ -1; '% bulan kering' = porsi petak-bulan yang kering.\n- **Poin:** selisih dua persentase (15% ke 17% = 2 poin).\n- **Kondisi 1981-2010 (model):** frekuensi kering model yang sama pada 1981-2010; pembanding utama karena model punya bias sendiri.\n"
                    f"- **Pengamatan ({meta['target']}):** pembanding tambahan dari data hujan nyata.\n- **p10, median, p90:** batas bawah, tengah, atas yang mencakup 80% simulasi (bukan ketidakpastian iklim).")
    with st.expander("Catatan wajib"):
        for c in meta["catatan"]: st.write("- " + c)
    with st.expander("Untuk peneliti: model, uji, dan data masukan"):
        st.markdown(f"**Model:** {meta['model']} (set {meta['set_fitur']}) · **GCM:** {meta['gcm']} · **Skenario:** {meta['skenario']} · **Target:** {meta['target']} · **Status:** {meta['status_gerbang']}")
        judul("Gerbang model", "(a) skill sefase > 0 (ERA5); (b) sebaran ≤ 1,10x klimatologi (prediktor GCM); (c) selisih frekuensi kering SPI-3 ≤ 3 poin dari pengamatan.")
        st.dataframe(pd.DataFrame(meta["gerbang"]).T.rename(columns={"a": "(a) skill sefase", "b": "(b) sebaran", "c": "(c) selisih kering"}).replace({True: "✓ lolos", False: "✗ tidak"}))
        ka = meta.get("konsistensi_arah")
        if ka and ka.get("jendela"):
            judul("Konsistensi arah", "Berlawanan di jendela dengan persen luar-rentang tinggi bisa berupa artefak ekstrapolasi.")
            st.dataframe(pd.DataFrame([{"Jendela": j["jendela"], "Peran": j["peran"], "Hujan GCM mentah (%)": j["gcm_pr_mentah_pct"], f"Model {ka.get('model', '')} (%)": j["model_pct"], "Berlawanan?": "ya" if j["berlawanan"] else "tidak", "Di luar rentang latih (%)": j["luar_rentang_pct"]} for j in ka["jendela"]]).set_index("Jendela"))
        judul("Data masukan di luar rentang latih", "Persentase baris prediktor GCM di luar rentang ERA5.")
        st.dataframe(pd.Series(meta["baris_prediktor_luar_rentang_pct"], name="% baris").to_frame().round(1))

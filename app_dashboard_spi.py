"""Dashboard proyeksi bulan kering Banten 2026-2050.
Jalankan mandiri : streamlit run app_dashboard_spi.py
Mode laporan PDF : http://localhost:8501/?laporan=1
Integrasi app.py : Otomatis mengikuti EMBED=True & DATA_DIR saat dipanggil dari cangkang dashBMKG.
Palet Warna      : Disesuaikan dengan standar produk SPI & Iklim BMKG.
"""
import json, math, os
import numpy as np, pandas as pd, streamlit as st
import plotly.graph_objects as go
import streamlit.components.v1 as components

EMBED = bool(globals().get("EMBED", False))

# ------------------------------------------------------------------ pengaturan tampilan
PEMBUAT = "Gemala Aleida Fitri · Statistika dan Sains Data, IPB University"
JUDUL_PROYEK = "Downscaling GCM Hujan untuk Proyeksi Kekeringan (SPI) di Banten"
H_KPI = 96
H_BAN = 64
H_KECIL = 185
UKURAN_TEKS, UKURAN_TEKS_LAPORAN = 15, 15
PETA_STYLE = "carto-positron-nolabels"
PETA_AWAL = "Selisih"

if not EMBED:
    st.set_page_config(page_title="Bulan kering Banten 2026-2050", page_icon="🌧️", layout="wide", initial_sidebar_state="collapsed")

def _param(k): return str(st.query_params.get(k, "")).lower() in ("1", "true", "ya")
LAPORAN = False if EMBED else _param("laporan")


def _angka(k, d, lo, hi):
    try: return int(np.clip(int(str(st.query_params.get(k, d))), lo, hi))
    except Exception: return d


def _ukuran_layar():
    vh, vw = _angka("vh", 0, 0, 6000), _angka("vw", 0, 0, 10000)
    if vh and vw: return vh, vw
    try:
        komp = components.declare_component("ukuran_layar", path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "ukuran_layar"))
        v = komp(key="ukuran_layar", default=None)
        if isinstance(v, dict) and v.get("h") and v.get("w"): return int(v["h"]), int(v["w"])
    except Exception: pass
    return None, None


VH, VW = (None, None) if LAPORAN else _ukuran_layar()
OVERHEAD_EMBED = 248
FSKALA = float(np.clip(VW / 1366, 1.0, 1.45)) if VW else 1.0
OVERHEAD = (OVERHEAD_EMBED if EMBED else 135) + (H_KPI + H_BAN) * FSKALA
if str(st.query_params.get("tinggi", "")).isdigit(): H_KECIL = _angka("tinggi", H_KECIL, 130, 700)
elif VH: H_KECIL = int(np.clip((VH - OVERHEAD - 10) / 2, 150, 700))
H_PETA = 2 * H_KECIL + 12
LEBAR_PETA = int(((VW or 1364) - 30) * 0.30)

CSS_UMUM = """<style>
header[data-testid="stHeader"], footer, #MainMenu, [data-testid="stToolbar"] {display:none !important;}
div[data-testid="stWidgetLabel"] {min-height:0; margin-bottom:0;}
@media print {
  html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stMainBlockContainer"], section.main, .main, .block-container {height:auto !important; min-height:0 !important; max-height:none !important; overflow:visible !important;}
  [data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] {display:none !important;}
  * {-webkit-print-color-adjust:exact !important; print-color-adjust:exact !important;}
  .stPlotlyChart, [data-testid="stIFrame"], [data-testid="stTable"] {break-inside:avoid;}
}
</style>"""
CSS_DASH = """<style>
html {font-size: clamp(14px, 1.1vw, 21px);}
.stApp {background:#f3f5f8;}
@page {size: A4 landscape; margin: 6mm;}
.block-container {padding:.5rem .9rem .4rem; max-width:100%;}
[data-testid="stVerticalBlock"] {gap:.32rem;}
div[data-baseweb="select"] > div {min-height:30px;}
[data-testid="stColumn"] {min-width:0;}
.ttl {font-size:clamp(.98rem, 1.25vw, 1.35rem); font-weight:700; color:#1d2b3a; line-height:1.15; white-space:normal; overflow-wrap:anywhere;}
.sub {font-size:.73rem; color:#5e6c7b; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
div[data-testid="stWidgetLabel"] p {font-size:.65rem !important; font-weight:700; color:#6b7785; text-transform:uppercase; letter-spacing:.04em; margin:0 !important;}
.ttl, .sub, .foot {margin-bottom:0 !important;}
.foot {font-size:.68rem; color:#7d8b99; margin-top:.35rem;}
.insight-strip {display:flex; flex-wrap:wrap; gap:8px; margin:2px 0 4px;}
.insight-pill {background:#ffffff; border:1px solid #dce3ec; border-left:4px solid #1f77b4; border-radius:6px; padding:5px 11px; font-size:.76rem; color:#1d2b3a; flex:1; min-width:230px; line-height:1.32; box-shadow:0 1px 2px rgba(0,0,0,.02);}
.insight-pill b {color:#16324f;}
.insight-pill.warn {border-left-color:#d62728;}
.insight-pill.good {border-left-color:#38a800;}
</style>"""
CSS_LAP = """<style>
html {font-size: __UT__px;}
.stApp {background:#fff;}
@page {size: A4 portrait; margin: 14mm;}
.block-container {max-width:920px; padding:1.2rem 1rem 2rem;}
h2 {color:#1d2b3a; border-bottom:2px solid #1f77b4; padding-bottom:.25rem; margin-top:1.3rem !important;}
h3 {color:#1f77b4;}
.judul {font-size:1.7rem; font-weight:800; color:#1d2b3a; line-height:1.2;}
.sublap {font-size:.85rem; color:#6b7785; margin-bottom:.6rem;}
.cara {font-size:.8rem; color:#55606e; background:#f3f5f8; border-left:4px solid #1f77b4; padding:.35rem .7rem; border-radius:4px; margin:.1rem 0 .6rem;}
.kes {font-size:.88rem; color:#1d2b3a; background:#e8f1f6; border-left:4px solid #38a800; padding:.4rem .7rem; border-radius:4px; margin:.1rem 0 .8rem;}
.jawab {font-size:1.1rem; background:#e8f1f6; border-left:6px solid #1f77b4; border-radius:6px; padding:.7rem 1rem; line-height:1.5;}
</style>"""

if not EMBED:
    st.markdown((CSS_UMUM + (CSS_LAP if LAPORAN else CSS_DASH)).replace("__UT__", str(UKURAN_TEKS_LAPORAN if LAPORAN else UKURAN_TEKS)), unsafe_allow_html=True)
else:
    st.markdown("""<style>
    .insight-strip {display:flex; flex-wrap:wrap; gap:8px; margin:2px 0 4px;}
    .insight-pill {background:#ffffff; border:1px solid #dce3ec; border-left:4px solid #1f77b4; border-radius:6px; padding:5px 11px; font-size:.76rem; color:#1d2b3a; flex:1; min-width:230px; line-height:1.32;}
    .insight-pill b {color:#16324f;}
    .insight-pill.warn {border-left-color:#d62728;}
    .insight-pill.good {border-left-color:#38a800;}
    </style>""", unsafe_allow_html=True)

# ------------------------------------------------------------------ palet warna standar BMKG
PROY, BASE, ABU = "#1f77b4", "#374151", "#9ca3af"          # Biru BMKG (Picture2-15) & netral tegas
TRANSF = "#7c3aed"
MERAH, BIRU, ABU_N = "#d62728", "#1f77b4", "#94a3b8"        # Merah & Biru kontras BMKG
WARNA_CHIP = {"red": "#d62728", "blue": "#1f77b4", "gray": "#64748b", "amber": "#e69800", "green": "#38a800"}

# Skala sekuensial frekuensi kering (Kuning Gading -> Oranye -> Merah -> Merah Tua BMKG)
KERING_BMKG = [
    [0.00, "#ffffbe"],  # Normal / rendah (Kuning Gading SPI BMKG)
    [0.35, "#e69800"],  # Agak Kering (Oranye Amber BMKG)
    [0.70, "#e60000"],  # Kering (Merah BMKG)
    [1.00, "#730000"],  # Sangat Kering (Merah Tua BMKG)
]

# Skala divergen selisih/bias (Biru Basah BMKG -> Hijau -> Kuning Gading -> Oranye -> Merah Tua Kering BMKG)
DIVERGEN_BMKG = [
    [0.00, "#005ce6"],  # Lebih basah / berkurang drastis (Biru BMKG)
    [0.20, "#00a9e6"],  # Sangat Basah (Cyan BMKG)
    [0.38, "#98e600"],  # Agak Basah (Hijau Muda BMKG)
    [0.50, "#ffffbe"],  # Mendekati nol / Normal (Kuning Gading BMKG - tidak pucat!)
    [0.62, "#e69800"],  # Agak Kering (Oranye Amber BMKG)
    [0.80, "#e60000"],  # Kering (Merah BMKG)
    [1.00, "#730000"],  # Sangat Kering / meningkat drastis (Merah Tua BMKG)
]

BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
PRESET = {
    "Sepanjang tahun": list(range(1, 13)),
    "Des-Feb (Basah)": [12, 1, 2],
    "Mar-Mei (Peralihan I)": [3, 4, 5],
    "Jun-Agu (Kemarau)": [6, 7, 8],
    "Sep-Nov (Peralihan II)": [9, 10, 11],
}
NAMA_SKALA = {"SPI-3": "3 bln (Pertanian)", "SPI-6": "6 bln (Musiman)", "SPI-12": "12 bln (Hidrologi)"}
NAMA_SKALA_PANJANG = {"SPI-3": "3 bulan (jangka pendek / pertanian)", "SPI-6": "6 bulan (satu musim)", "SPI-12": "12 bulan (satu tahun / hidrologi)"}
ML = ["GLM Gamma", "Random Forest", "XGBoost", "Neural Net"]
SIM = {"sama": "●", "lebih": "▲", "kurang": "▼", "sedikit": "●"}
KATA = {"sama": "belum beda nyata", "lebih": "lebih sering kering", "kurang": "lebih jarang kering", "sedikit": "data terlalu sedikit"}
WARNA_KODE = {"sama": "gray", "lebih": "red", "kurang": "blue", "sedikit": "gray"}

# ------------------------------------------------------------------ pemuatan data
FOLDER = os.environ.get("HASIL_DIR") or (globals().get("DATA_DIR") if EMBED else None) or os.path.dirname(os.path.abspath(__file__))


def jalur(nama):
    p, alt = os.path.join(FOLDER, nama), os.path.join(FOLDER, nama.replace(".csv.gz", "_csv.gz"))
    return p if os.path.exists(p) or not os.path.exists(alt) else alt


@st.cache_resource
def muat(ver):
    d = {"meta": json.load(open(jalur("dashboard_meta.json"), encoding="utf-8"))}
    for k, nm in [("b_grid", "dashboard_bulanan_per_grid.csv.gz"), ("b_base", "dashboard_baseline_bulan_grid.csv.gz"), ("grid", "dashboard_grid.csv"),
                  ("banding", "dashboard_model_banding.csv"), ("gerb", "dashboard_model_gerbang.csv"), ("reg", "dashboard_bulanan_regional.csv.gz"),
                  ("sens", "dashboard_sensitivitas.csv"), ("kor", "dashboard_korelasi.csv"), ("uji", "dashboard_uji.csv")]:
        d[k] = pd.read_csv(jalur(nm)) if os.path.exists(jalur(nm)) else None
    d["gj"] = json.load(open(jalur("banten_kabkota.geojson"), encoding="utf-8")) if os.path.exists(jalur("banten_kabkota.geojson")) else None
    return d


try:
    D = muat(tuple(sorted((f, os.path.getmtime(os.path.join(FOLDER, f))) for f in os.listdir(FOLDER) if f.startswith("dashboard_") or f.endswith(".geojson"))))
except FileNotFoundError as e:
    st.error(f"Berkas data tidak ditemukan: {e.filename}"); st.stop()

meta, gj = D["meta"], D["gj"]
H0, H1 = int(meta["horizon"][0]), int(meta["horizon"][1])
if D["b_grid"] is None or D["b_base"] is None or D["grid"] is None:
    st.error("Data utama (grid/baseline) belum tersedia."); st.stop()
th_all = sorted(D["b_grid"]["tahun"].unique().tolist())


def n(x, d=1, plus=False):
    if x is None or not np.isfinite(x): return "-"
    s = f"{x:+.{d}f}" if plus else f"{x:.{d}f}"
    return s.replace(".", ",")


def se_kasar(v):
    v = pd.Series(v).dropna()
    return float(v.std(ddof=1) / np.sqrt(len(v))) if len(v) >= 3 else float("nan")


def tafsir(sel, se):
    if not np.isfinite(se): return "sedikit"
    return "sama" if abs(sel) < 2 * se else ("lebih" if sel > 0 else "kurang")


# ------------------------------------------------------------------ peta spasial
def _dalam(px, py, ring):
    x, y = ring[:, 0], ring[:, 1]; d = np.zeros(px.shape, bool)
    for xi, yi, xj, yj in zip(x, y, np.roll(x, -1), np.roll(y, -1)):
        if yi != yj: d ^= ((yi > py) != (yj > py)) & (px < (xj - xi) * (py - yi) / (yj - yi) + xi)
    return d


def nama_pendek(idx):
    inti = [x.replace("Kab. ", "").replace("Kota ", "") for x in idx]
    return [k + (" (Kab)" if x.startswith("Kab.") else " (Kota)") if inti.count(k) > 1 else k for k, x in zip(inti, idx)]


@st.cache_resource
def wilayah_grid(ver):
    gr = D["grid"].sort_values("grid_id").reset_index(drop=True); nama = pd.Series([None] * len(gr), dtype=object); lab = []
    if gj is None: return gr.assign(wilayah=nama), pd.DataFrame(columns=["nama", "lon", "lat"])
    px, py = gr["lon"].to_numpy(float), gr["lat"].to_numpy(float)
    for f in gj["features"]:
        nm = f["properties"].get("nama", "?"); dalam = np.zeros(len(px), bool); besar = None
        polys = [f["geometry"]["coordinates"]] if f["geometry"]["type"] == "Polygon" else list(f["geometry"]["coordinates"])
        for poly in polys:
            ext = np.asarray(poly[0], float); m = _dalam(px, py, ext)
            for h in poly[1:]: m &= ~_dalam(px, py, np.asarray(h, float))
            dalam |= m; luas = np.ptp(ext[:, 0]) * np.ptp(ext[:, 1])
            if besar is None or luas > besar[0]: besar = (luas, ext[:, 0].mean(), ext[:, 1].mean())
        nama[dalam & nama.isna().to_numpy()] = nm
        if besar: lab.append((nm, besar[1], besar[2]))
    lab = pd.DataFrame(lab, columns=["nama", "lon", "lat"]); lab["nama"] = nama_pendek(lab["nama"].tolist())
    return gr.assign(wilayah=nama.to_numpy()), lab


gr_ref, LAB = wilayah_grid(len(D["grid"]))


def fig_peta(df, kol, zmin, zmax, satuan, warna, tinggi, lebar=400, zmid=None, mask=None, catatan=None):
    xs, ys = np.unique(df["lon"].round(4)), np.unique(df["lat"].round(4)); h = float(np.median(np.diff(xs)) / 2) if len(xs) > 1 else 0.025

    def trace(d, op, bar):
        kotak = {"type": "FeatureCollection", "features": [{"type": "Feature", "id": str(int(g)), "properties": {}, "geometry": {"type": "Polygon", "coordinates": [[[lo - h, la - h], [lo + h, la - h], [lo + h, la + h], [lo - h, la + h], [lo - h, la - h]]]}} for g, lo, la in zip(d["grid_id"], d["lon"], d["lat"])]}
        status_txt = np.where(d["nyata"], "Beda nyata (FDR)", "Belum beda nyata (masih dalam variasi alami)") if "nyata" in d.columns else [""] * len(d)
        fmt_z = "%{z:+.1f}" if zmid == 0 else "%{z:.1f}"
        return go.Choroplethmap(
            geojson=kotak, locations=d["grid_id"].astype(int).astype(str), z=d[kol],
            text=d["wilayah"].fillna("Di luar batas kab/kota"), customdata=status_txt,
            colorscale=warna, zmin=zmin, zmax=zmax, zmid=zmid, showscale=bar,
            marker=dict(opacity=op, line=dict(width=0.25, color="rgba(55,65,81,0.22)")),
            colorbar=dict(title=dict(text=satuan, font=dict(size=10), side="top"), thickness=10, len=0.52, tickfont=dict(size=10), x=0.995),
            hovertemplate="<b>%{text}</b><br>Nilai: " + fmt_z + " " + satuan + "<br><i>%{customdata}</i><extra></extra>"
        )

    fig = go.Figure()
    if mask is None:
        fig.add_trace(trace(df, 0.92, True))
    elif not bool(mask.any()):
        # Tetap tampilkan warna peta yang jelas (opacity 0.65) agar tidak terlihat pudar/hilang meski belum lolos FDR
        fig.add_trace(trace(df, 0.65, True))
    else:
        fig.add_trace(trace(df, 0.58, True))
        fig.add_trace(trace(df[mask.to_numpy()], 0.96, False))
    lon_r, lat_r = max(xs.max() - xs.min() + 2 * h, 0.2) * 1.08, max(ys.max() - ys.min() + 2 * h, 0.2) * 1.08 / np.cos(np.radians(float(ys.mean())))
    zoom = float(np.clip(min(np.log2(360 * lebar / (512 * lon_r)), np.log2(360 * tinggi / (512 * lat_r))), 5, 11))
    lay = dict(style=PETA_STYLE, center=dict(lat=float((ys.min() + ys.max()) / 2), lon=float((xs.min() + xs.max()) / 2)), zoom=zoom)
    if gj is not None: lay["layers"] = [dict(sourcetype="geojson", source=gj, type="line", color="#1f2937", line=dict(width=1.4), below="")]
    fig.update_layout(map=lay)
    if len(LAB): fig.add_trace(go.Scattermap(lon=LAB["lon"], lat=LAB["lat"], mode="text", text=LAB["nama"], textfont=dict(size=10, color="#111827"), hoverinfo="skip", showlegend=False))
    if catatan: fig.add_annotation(text=catatan, xref="paper", yref="paper", x=0.01, y=0.99, xanchor="left", yanchor="top", showarrow=False, align="left", font=dict(size=10.5, color="#1f2937"), bgcolor="rgba(255,255,255,.92)", bordercolor="#cbd5e1", borderwidth=1, borderpad=4)
    return fig


def gambar(fig, h, judul=None, legenda=False):
    fig.update_layout(height=h, margin=dict(l=2, r=2, t=2, b=2), font=dict(size=11, color="#33404d"), plot_bgcolor="white", paper_bgcolor="white", separators=",.", showlegend=legenda, uniformtext=dict(minsize=9, mode="hide"), legend=dict(orientation="h", y=1.14, x=0, font_size=10))
    if judul: fig.update_layout(margin=dict(l=2, r=2, t=24, b=2), title=dict(text=judul.upper(), x=0.005, xanchor="left", y=0.99, yanchor="top", font=dict(size=10.5, color="#374151")))
    fig.update_xaxes(showgrid=False, linecolor="#cbd5e1"); fig.update_yaxes(gridcolor="#eef1f4", zeroline=False)
    if FSKALA > 1.01:
        fs = lambda v: round(v * FSKALA, 1); fig.update_layout(font_size=fs(11)); fig.update_xaxes(tickfont_size=fs(10)); fig.update_yaxes(tickfont_size=fs(10))
        for tr in fig.data:
            try: tr.textfont.size = fs(10)
            except Exception: pass
        try: fig.layout.title.font.size = fs(10.5)
        except Exception: pass
        for an in fig.layout.annotations: an.font.size = fs(10.5)
    cfg = dict(displaylogo=False, displayModeBar=False)
    try: st.plotly_chart(fig, width="stretch", config=cfg)
    except TypeError: st.plotly_chart(fig, use_container_width=True, config=cfg)


def pilih(opsi, key, label, default=None, fmt=None):
    default = default or opsi[0]
    if hasattr(st, "segmented_control"):
        v = st.segmented_control(label, opsi, default=default, key=key, format_func=fmt or (lambda x: x))
        return default if v is None else v
    return st.radio(label, opsi, index=opsi.index(default), key=key, format_func=fmt or (lambda x: x), horizontal=True)


def iframe(html, tinggi):
    if hasattr(st, "iframe"): st.iframe(html, height=tinggi)
    else: components.html(html, height=tinggi)


# ------------------------------------------------------------------ analisis statistik (FDR BH + Uji Formal)
def _nyata_bh(sel, se, q=0.05):
    """Beda nyata dengan koreksi uji berganda Benjamini-Hochberg (FDR q=0.05)."""
    sel = pd.Series(sel).astype(float); se = pd.Series(se, index=sel.index).astype(float)
    se_safe = se.replace(0, np.nan)
    z = (sel / se_safe).abs(); ok = z.notna() & np.isfinite(z)
    p = pd.Series(np.nan, index=sel.index); p[ok] = [math.erfc(v / math.sqrt(2)) for v in z[ok]]
    out = pd.Series(False, index=sel.index); pv = p[ok].sort_values(); m = len(pv)
    if m:
        lolos = pv.to_numpy() <= q * np.arange(1, m + 1) / m
        if lolos.any(): out[pv.index[: int(np.max(np.where(lolos)[0])) + 1]] = True
    return out


def ringkas(skala, bulan, t0, t1):
    G = D["b_grid"][D["b_grid"]["SPI"] == skala]; B = D["b_base"][D["b_base"]["SPI"] == skala]
    gs = G[G["bulan"].isin(bulan) & G["tahun"].between(t0, t1)]; bs = B[B["bulan"].isin(bulan)]
    if gs.empty: return None
    R = dict(skala=skala, bulan=bulan, t0=t0, t1=t1)
    R["per_th"] = gs.groupby("tahun")["p_kering"].mean().mul(100)
    R["proy"], R["base"], R["ref"] = float(gs["p_kering"].mean() * 100), float(bs["kering_model_pct"].mean()), float(bs["kering_target_pct"].mean())
    R["sel"] = R["proy"] - R["base"]; R["se"] = se_kasar(R["per_th"]); R["amb"] = 2 * R["se"]; R["kode"] = tafsir(R["sel"], R["se"])

    agg = gs.groupby("grid_id")["p_kering"].mean().mul(100).rename("p_kering").reset_index().merge(
        bs.groupby("grid_id")[["kering_model_pct", "kering_target_pct"]].mean().reset_index(), on="grid_id"
    ).merge(gr_ref, on="grid_id")
    agg["selisih"] = agg["p_kering"] - agg["kering_model_pct"]
    yg = gs.groupby(["grid_id", "tahun"])["p_kering"].mean().mul(100).unstack("tahun")
    se_g = (yg.std(axis=1, ddof=1) / np.sqrt(yg.notna().sum(axis=1))).rename("se_g").reset_index()
    agg = agg.merge(se_g, on="grid_id", how="left")
    agg["nyata"] = _nyata_bh(agg["selisih"], agg["se_g"])
    R["agg"] = agg[agg["wilayah"].notna()] if gj is not None else agg

    rk = R["agg"].dropna(subset=["wilayah"]).groupby("wilayah")[["p_kering", "kering_model_pct", "kering_target_pct"]].mean().sort_values("p_kering") if gj is not None else pd.DataFrame()
    if len(rk): rk.index = nama_pendek(rk.index.tolist())
    R["rk"] = rk

    R["prof"] = G[G["tahun"].between(t0, t1)].groupby("bulan")["p_kering"].mean().mul(100)
    R["pb"] = B.groupby("bulan")["kering_model_pct"].mean().reindex(R["prof"].index)
    R["dbulan"] = R["prof"] - R["pb"]
    ym = G[G["tahun"].between(t0, t1)].groupby(["bulan", "tahun"])["p_kering"].mean().mul(100).unstack("tahun")
    se_m = ym.std(axis=1, ddof=1) / np.sqrt(ym.notna().sum(axis=1))
    R["bulan_nyata"] = _nyata_bh(R["dbulan"], se_m.reindex(R["dbulan"].index))

    R["uji"], R["ci"] = "cepat (FDR BH)", None
    U = D.get("uji"); MUSIM_KODE = {"Des-Feb (Basah)": "DJF", "Mar-Mei (Peralihan I)": "MAM", "Jun-Agu (Kemarau)": "JJA", "Sep-Nov (Peralihan II)": "SON"}
    if U is not None and t0 == H0 and t1 == H1 and {"SPI", "jenis", "unit", "nyata_fdr", "ci_lo", "ci_hi"} <= set(U.columns):
        U = U[U["SPI"] == skala]; ub = U[U["jenis"] == "bulan"].set_index("bulan")
        if len(ub) == 12: R["bulan_nyata"] = ub["nyata_fdr"].astype(bool).reindex(R["dbulan"].index).fillna(False); R["uji"] = "resmi (block bootstrap)"
        semua = sorted(bulan) == list(range(1, 13))
        kunci = next((k for k, v in PRESET.items() if sorted(v) == sorted(bulan) and k in MUSIM_KODE), None)
        ur = U[U["jenis"] == "wilayah"] if semua else U[(U["jenis"] == "musim") & (U["unit"] == MUSIM_KODE.get(kunci, "?"))]
        if len(ur):
            r0 = ur.iloc[0]; R["ci"] = (float(r0["ci_lo"]), float(r0["ci_hi"])); R["amb"] = (R["ci"][1] - R["ci"][0]) / 2
            R["kode"] = ("lebih" if R["sel"] > 0 else "kurang") if bool(r0["nyata_fdr"]) else "sama"; R["uji"] = "resmi (block bootstrap)"
        if semua:
            ug = U[U["jenis"] == "grid"].set_index("grid_id")["nyata_fdr"]
            if len(ug): R["agg"] = R["agg"].assign(nyata=R["agg"]["grid_id"].map(ug).fillna(False).astype(bool))
    return R


def model_selisih(skala, t0=None, t1=None, R=None):
    out = {}
    if D["banding"] is None: return out
    dm = D["banding"][(D["banding"]["SPI"] == skala) & D["banding"]["model"].isin(ML)]
    if t0 is not None: dm = dm[dm["tahun"].between(t0, t1)]
    for nm_, g_ in dm.groupby("model"):
        if g_["baseline_model_sendiri_pct"].notna().any() and g_["n_bulan_valid"].sum() > 0:
            out[nm_] = float(np.average(g_["kering_pct_mean"], weights=g_["n_bulan_valid"]) - g_["baseline_model_sendiri_pct"].dropna().iloc[0])
    if R is not None and UTAMA in out and sorted(R["bulan"]) == list(range(1, 13)): out[UTAMA] = float(R["sel"])
    return out


def arah_model(sm):
    v = list(sm.values()); pos, neg = sum(x > 0 for x in v), sum(x < 0 for x in v); N = len(v)
    return dict(N=N, pos=pos, neg=neg, n_s=max(pos, neg) if N else 0, arah=("kurang" if neg > pos else "lebih" if pos > neg else None))


UTAMA = next((m_ for m_ in ML if m_ in str(meta.get("model", ""))), None)
TRANSFER = (meta.get("model_transfer_terbaik") or {}).get("model")
if TRANSFER is None and D["gerb"] is not None and {"c_kering_pct", "acuan_c"} <= set(D["gerb"].columns):
    _g = D["gerb"].set_index("model"); TRANSFER = (_g["c_kering_pct"] - _g["acuan_c"]).abs().idxmin()


def keyakinan(R, am):
    rl = meta.get("rolling_origin") or {}; ho = meta.get("holdout") or {}
    ka = (meta.get("konsistensi_arah") or {}).get("jendela") or []
    jd = next((j for j in ka if j["jendela"] == f"{H0}-{H1}"), None)
    luar = (meta.get("baris_prediktor_luar_rentang_pct") or {}).get(f"{H0}-{H1}")

    if rl:
        syarat_uji = ("Uji rolling-origin", "Lebih baik daripada klimatologi pada rolling-origin 1996-2020", bool(rl.get("lebih_baik")),
                      f"CRPSS {n(rl['crpss'], 3, True)}, positif {rl['fold_positif']}/{rl['n_fold']} lipatan")
    else:
        syarat_uji = ("Uji hold-out 2021-25", "Lebih baik daripada klimatologi pada hold-out 2021-2025", bool(ho.get("lebih_baik_dari_klimatologi")),
                      f"CRPSS {n(ho['crpss_t1'], 3, True)}, positif {ho['tahun_positif']}/{ho['n_tahun']} tahun" if ho else "belum tersedia")

    cek = [
        ("Model terbaik", "Model dipilih sebagai terbaik di antara empat model (tuning setara)", "terbaik dari 4" in str(meta.get("status_gerbang", "")), str(meta.get("status_gerbang", "-"))),
        syarat_uji,
        ("Arah GCM", "Arah perubahan hujan sejalan dengan hujan mentah GCM", jd is not None and not jd["berlawanan"], f"GCM mentah {n(jd['gcm_pr_mentah_pct'], 1, True)}% vs model {n(jd['model_pct'], 1, True)}%" if jd else "belum tersedia"),
        ("Input di luar rentang", "Data masukan yang di luar rentang latih < 10%", luar is not None and luar < 10, f"{n(luar, 0)}% baris prediktor di luar rentang" if luar is not None else "belum tersedia"),
        ("Bias model", "Baseline model dekat pengamatan (selisih ≤ 3 poin)", abs(R["base"] - R["ref"]) <= 3, f"model {n(R['base'], 0)} vs pengamatan {n(R['ref'], 0)} dari 100 bulan"),
        ("Model searah", "Semua model statistik memberi arah yang sama", am["N"] >= 2 and am["n_s"] == am["N"], f"{am['n_s']} dari {am['N']} model searah")
    ]
    n_ok = sum(c[2] for c in cek); yak, yak_c = (f"{n_ok}/6", "green" if n_ok >= 5 else "amber" if n_ok >= 3 else "red")
    return cek, n_ok, yak, yak_c


KPI_CSS = """<style>
body {margin:0; padding:2px 1px 0; zoom:__Z__; background:__BG__; font-family:"Segoe UI", Arial, sans-serif; color:#1d2b3a; -webkit-print-color-adjust:exact; print-color-adjust:exact;}
.kpi {display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:8px;}
.tile {background:#fff; border:1px solid #e1e5ea; border-top:3px solid var(--c); border-radius:7px; padding:5px 10px 6px; height:88px; box-sizing:border-box; overflow:hidden;}
.k {font-size:10.5px; font-weight:700; color:#6b7785; text-transform:uppercase; letter-spacing:.04em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.v {font-size:22px; font-weight:700; line-height:1.15; white-space:nowrap;}
.v small {font-size:11px; font-weight:500; color:#6b7785;}
.s {font-size:11px; color:#6b7785; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.chip {max-width:100%; overflow:hidden; text-overflow:ellipsis; vertical-align:top; display:inline-block; padding:0 8px; border-radius:9px; font-size:10px; font-weight:700; color:#fff; margin-top:2px; white-space:nowrap;}
.red {background:#d62728;} .blue {background:#1f77b4;} .gray {background:#64748b;} .amber {background:#e69800;} .green {background:#38a800;}
.verd {background:#fff; border:1px solid #e1e5ea; border-left:6px solid var(--c); border-radius:6px; padding:5px 10px; font-size:13.5px; line-height:1.3; margin:0 1px 7px;}
.verd small {display:block; font-size:11px; color:#55606e; margin-top:2px; line-height:1.3;}
.dot {display:inline-block; width:10px; height:10px; border-radius:50%; margin:0 2px 0 0; vertical-align:middle; background:#d9dee4;} .dot.ok {background:#38a800;} .dot.no {background:#e69800;}
</style>"""

PENDEK = {"Model terbaik": "model terbaik", "Uji rolling-origin": "uji rolling-origin", "Uji hold-out 2021-25": "uji hold-out", "Arah GCM": "arah GCM", "Input di luar rentang": "input di luar rentang", "Bias model": "bias model", "Model searah": "model searah"}


def kartu_html(R, sm, bg="#f3f5f8", atas="", zoom=1.0):
    am = arah_model(sm); cek, n_ok, yak, yak_c = keyakinan(R, am); kode = R["kode"]
    def tile(k, v, kecil, s_, chip, cls, warna, tip=""):
        return f'<div class="tile" style="--c:{warna}" title="{tip}"><div class="k">{k}</div><div class="v">{v} <small>{kecil}</small></div><div class="s">{s_}</div><span class="chip {cls}">{chip}</span></div>'
    bias = R["base"] - R["ref"]; gagal = [c[0] for c in cek if not c[2]]
    tip_y = " | ".join(("✓ " if c[2] else "✗ ") + c[1] for c in cek).replace('"', "'")
    titik = "".join('<span class="dot ' + ("ok" if c[2] else "no") + '" title="' + ("✓ " if c[2] else "✗ ") + c[1].replace('"', "'") + '"></span>' for c in cek)

    if bias > 3: b_chip, b_cls = "▲ MODEL TERLALU KERING", "amber"
    elif bias < -3: b_chip, b_cls = "▼ MODEL TERLALU BASAH", "amber"
    else: b_chip, b_cls = "● DEKAT PENGAMATAN", "green"

    if len(sm) >= 2:
        searah = am["N"] >= 2 and am["n_s"] == am["N"]
        m_v = f'{n(min(sm.values()), 1, True)} s/d {n(max(sm.values()), 1, True)}'
        m_s = f'selisih menurut {am["N"]} model' + ("" if len(R["bulan"]) == 12 else " · seluruh bulan")
        m_chip, m_cls = ("● SEMUA MODEL SEARAH", "green") if searah else ("▲ MODEL TIDAK SEPAKAT", "amber")
    else:
        m_v, m_s, m_chip, m_cls = "-", "data perbandingan model belum ada", "● BELUM ADA", "gray"

    T = [
        tile("Selisih bulan kering", n(R["sel"], 1, True), "dari 100 bulan",
             (f'selang 95%: {n(R["ci"][0], 1, True)} s/d {n(R["ci"][1], 1, True)}' if R.get("ci") else f'naik-turun alami ±{n(R["amb"], 1)}') if np.isfinite(R["amb"]) else "proyeksi − masa lalu model",
             f'{SIM[kode]} {KATA[kode].upper()}', WARNA_KODE[kode], WARNA_CHIP[WARNA_KODE[kode]],
             "Selisih frekuensi bulan kering (proyeksi dikurangi masa lalu model)."),
        tile("Rentang antar-model", m_v, "bln/100", m_s, m_chip, m_cls, WARNA_CHIP[m_cls],
             "Selisih yang sama dihitung dengan GLM, Random Forest, XGBoost, dan Neural Net."),
        tile("Masa lalu 1981-2010", f'{n(R["base"], 0)} vs {n(R["ref"], 0)}', "model vs nyata", "bulan kering per 100 bulan", b_chip, b_cls, WARNA_CHIP[b_cls],
             "Perbandingan baseline model vs pengamatan CHIRPS (1981-2010)."),
        tile("Syarat terpenuhi", f'{yak} {titik}', "", ("belum: " + ", ".join(PENDEK.get(g, g) for g in gagal)) if gagal else "semua syarat terpenuhi", f"{n_ok} DARI 6 SYARAT TERPENUHI", yak_c, WARNA_CHIP[yak_c], tip_y)
    ]
    dm = R["dbulan"]; ny = R["bulan_nyata"].reindex(dm.index).fillna(False)
    naik = [BULAN[m - 1] for m, v in dm.items() if v >= 3 and ny[m]]; turun = [BULAN[m - 1] for m, v in dm.items() if v <= -3 and ny[m]]
    html = KPI_CSS.replace("__BG__", bg).replace("__Z__", str(round(zoom, 3))) + atas + '<div class="kpi">' + "".join(T) + "</div>"
    return html, cek, n_ok, yak, yak_c, am, naik, turun


def banner(R, sm, am):
    per, sel, amb, kode = f'{R["t0"]}-{R["t1"]}', R["sel"], R["amb"], R["kode"]
    amb_t = (f"selang 95%: {n(R['ci'][0], 1, True)} s/d {n(R['ci'][1], 1, True)}" if R.get("ci") else f"±{n(amb, 1)}") if np.isfinite(amb) else "-"
    utama = {
        "sama": f'<b>Belum ada perubahan yang bisa dipastikan.</b> Bulan kering {per} hanya {n(abs(sel), 1)} dari 100 bulan {"lebih sering" if sel > 0 else "lebih jarang"} dibanding 1981-2010, masih di dalam naik-turun alami ({amb_t}).',
        "lebih": f'<b>Bulan kering diproyeksikan lebih sering</b> pada {per}: {n(sel, 1, True)} dari 100 bulan dibanding 1981-2010, melampaui naik-turun alami ({amb_t}).',
        "kurang": f'<b>Bulan kering diproyeksikan lebih jarang</b> pada {per}: {n(sel, 1, True)} dari 100 bulan dibanding 1981-2010, melampaui naik-turun alami ({amb_t}).',
        "sedikit": "<b>Data tahun terlalu sedikit untuk disimpulkan.</b> Pilih rentang tahun minimal 3 tahun."
    }[kode]
    kor = D.get("kor")
    if kor is not None and "lolos_fdr_gcm_target" in kor.columns:
        nk, nl = len(kor), int(kor["lolos_fdr_gcm_target"].astype(bool).sum())
        gcm_t = f"GCM tidak sefase dengan hujan nyata ({nl}/{nk} uji korelasi lolos)" if nl == 0 else f"GCM sefase pada {nl}/{nk} uji korelasi"
    else:
        gcm_t = "GCM berjalan bebas (tidak sefase dengan hujan nyata)"
    ny_b, ny_g = int(R["bulan_nyata"].fillna(False).sum()), int(R["agg"]["nyata"].sum())
    cat = (f"Beda nyata (FDR): {ny_b}/{len(R['bulan_nyata'])} bulan & {ny_g}/{len(R['agg'])} grid. {gcm_t}, sehingga hanya selisih relatif yang dibaca."
           + (" " + str(meta.get("klaim_arah_teks", "")) if meta.get("klaim_arah") == "belum_dapat_disimpulkan" else "")
           + (" Model statistik tidak sepakat arahnya." if am["N"] >= 2 and am["n_s"] < am["N"] else ""))
    return f'<div class="verd" style="--c:{WARNA_CHIP[WARNA_KODE[kode]]}">{utama}<small>{cat}</small></div>', WARNA_CHIP[WARNA_KODE[kode]]


def deret_info(sk, t0, t1):
    r = D["reg"]
    if r is None: return None
    s_ = r[(r["SPI"] == sk) & r["tahun"].between(t0, t1)].sort_values(["tahun", "bulan"]).dropna(subset=["spi_median"]).reset_index(drop=True)
    if s_.empty: return None
    kr = (s_["spi_median"] <= -1).to_numpy(); best = run = 0; end = -1
    for i, x in enumerate(kr):
        run = run + 1 if x else 0
        if run > best: best, end = run, i
    lab = lambda i: f"{BULAN[int(s_.loc[i, 'bulan']) - 1]} {int(s_.loc[i, 'tahun'])}"
    mn = int(s_["spi_median"].idxmin())
    return dict(best=best, a=lab(end - best + 1) if best else "-", b=lab(end) if best else "-", mn=lab(mn), mn_v=float(s_.loc[mn, "spi_median"]), n_k=int(kr.sum()), N=len(s_))


def sorotan_insight_html(R, sk, t0, t1):
    """Meringkas 3 insight praktis (Spasial Wilayah, Pergeseran Musim, dan Durasi Kekeringan Terpanjang)."""
    pills = []
    rk = R["rk"]
    if len(rk):
        dk = (rk["p_kering"] - rk["kering_model_pct"]).sort_values()
        top_w, top_v = dk.index[-1], float(dk.iloc[-1])
        abs_w, abs_v = rk["p_kering"].idxmax(), float(rk["p_kering"].max())
        cls_w = "warn" if (np.isfinite(R["amb"]) and top_v > R["amb"]) else ""
        pills.append(f'<div class="insight-pill {cls_w}">📍 <b>Sorotan Wilayah:</b> Kenaikan tertinggi di <b>{top_w}</b> ({n(top_v, 1, True)} bln/100); tingkat kering absolut tertinggi di <b>{abs_w}</b> ({n(abs_v, 0)} bln/100).</div>')

    db = R["dbulan"].dropna()
    ny_b = R["bulan_nyata"].reindex(db.index).fillna(False)
    if len(db):
        b_max = int(db.idxmax()); v_max = float(db.max())
        b_min = int(db.idxmin()); v_min = float(db.min())
        st_max = "beda nyata" if ny_b.loc[b_max] else "masih dalam variasi alami"
        cls_m = "warn" if (ny_b.loc[b_max] and v_max > 0) else ""
        pills.append(f'<div class="insight-pill {cls_m}">📅 <b>Dinamika Musiman:</b> Lonjakan kering tertinggi pada <b>{BULAN[b_max - 1]}</b> ({n(v_max, 1, True)} bln/100, {st_max}); penurunan terbesar pada <b>{BULAN[b_min - 1]}</b> ({n(v_min, 1, True)}).</div>')

    di = deret_info(sk, t0, t1)
    if di:
        pills.append(f'<div class="insight-pill">⏳ <b>Durasi & Ekstrem ({sk}):</b> Rangkaian kering terpanjang <b>{di["best"]} bulan beruntun</b> ({di["a"]}–{di["b"]}); titik terkering mencapai <b>SPI {n(di["mn_v"], 2)}</b> ({di["mn"]}).</div>')

    if not pills: return ""
    return '<div class="insight-strip">' + "".join(pills) + '</div>'


# ------------------------------------------------------------------ pembangun grafik
def tren_tahun(yr):
    x, y = yr.index.to_numpy(float), yr.to_numpy(float)
    if len(y) < 5: return np.nan, np.nan
    xm = x - x.mean(); b = float((xm * (y - y.mean())).sum() / (xm ** 2).sum()); res = y - y.mean() - b * xm
    return 10 * b, 10 * float(np.sqrt((res ** 2).sum() / (len(y) - 2) / (xm ** 2).sum()))


def fig_tahun(R):
    yr = R["per_th"]; x = yr.index.astype(int); mv = yr.rolling(5, center=True, min_periods=3).mean()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=yr.values, marker_color="rgba(31,119,180,.42)", name="Tahunan", hovertemplate="Tahun %{x}<br>%{y:.1f} dari 100 bulan kering<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=mv.values, mode="lines+markers", marker=dict(size=4, color=PROY), line=dict(color=PROY, width=3.0), name="Rata-rata 5 thn", hovertemplate="%{x}: rata-rata 5 tahun %{y:.1f}<extra></extra>"))
    fig.add_hline(y=R["base"], line_dash="dot", line_color=MERAH, line_width=2.2, annotation_text=f"Baseline ({n(R['base'], 0)})", annotation_position="top left", annotation_font_size=9.5)
    fig.update_layout(bargap=0.22, yaxis_range=[0, max(float(yr.max()), R["base"]) * 1.15]); fig.update_xaxes(dtick=5, tickfont=dict(size=10)); return fig


def fig_bulan(R):
    d = R["dbulan"]; ny = R["bulan_nyata"].reindex(d.index).fillna(False).astype(bool); pilih_ = [m in R["bulan"] for m in d.index]
    # Batang yang belum lolos FDR diberi warna tint lembut (bukan abu mati) agar arah anomali bulanan tetap terbaca
    warna = [
        (MERAH if v > 0 else BIRU) if nn else ("rgba(214,39,40,0.34)" if v > 0 else "rgba(31,119,180,0.34)")
        for v, nn in zip(d.values, ny.values)
    ]
    fig = go.Figure(go.Bar(
        x=[BULAN[m - 1] for m in d.index], y=d.values,
        marker=dict(color=warna, opacity=[1 if p else 0.45 for p in pilih_]),
        customdata=np.column_stack([R["prof"].values, R["pb"].values, np.where(ny.values, "Beda nyata (FDR)", "Belum beda nyata (tint lembut)")]),
        hovertemplate="<b>%{x}</b><br>Selisih: %{y:+.1f} bln/100<br>Proyeksi: %{customdata[0]:.1f} vs Lalu: %{customdata[1]:.1f}<br><i>%{customdata[2]}</i><extra></extra>"
    ))
    fig.add_hline(y=0, line_color="#374151", line_width=1); fig.update_xaxes(tickfont=dict(size=10)); return fig


def fig_model(sm, compact=False, amb=None):
    urut = sorted(sm, key=sm.get); v = [sm[m_] for m_ in urut]; a_ = float(amb) if amb is not None and np.isfinite(amb) else 0.0
    if compact:
        lab = [m_ + (" ★" if m_ == UTAMA else "") for m_ in urut]; warna = [PROY if m_ == UTAMA else ABU for m_ in urut]
    else:
        lab = [m_ + ("<br>(dipakai)" if m_ == UTAMA else "<br>(dekat pengamatan)" if m_ == TRANSFER else "") for m_ in urut]
        warna = [PROY if m_ == UTAMA else TRANSF if m_ == TRANSFER else ABU for m_ in urut]
    span = max(max(v) - min(v), a_, 1)
    fig = go.Figure(go.Bar(y=lab, x=v, orientation="h", marker_color=warna, text=[n(x, 1, True) for x in v], textposition="outside", textfont_size=10, cliponaxis=False, hovertemplate="%{y}<br>Selisih: %{x:+.1f} bulan per 100<extra></extra>"))
    if a_ > 0: fig.add_vrect(x0=-a_, x1=a_, fillcolor="#94a3b8", opacity=0.16, line_width=0, layer="below")
    fig.add_vline(x=0, line_color="#374151", line_width=1.2)
    fig.update_xaxes(zeroline=False, range=[min(min(v), -a_, 0) - 0.22 * span, max(max(v), a_, 0) + 0.25 * span]); fig.update_yaxes(type="category", tickfont=dict(size=10), automargin=True); return fig


def fig_kab(R):
    rk = R["rk"]; d = (rk["p_kering"] - rk["kering_model_pct"]).sort_values(); a_ = float(R["amb"]) if np.isfinite(R["amb"]) else 0.0
    rk_s = rk.reindex(d.index)
    # Wilayah di dalam pita alami diberi warna tint merah/biru lembut agar arah pergeseran tiap kab/kota tetap terlihat
    warna = [
        (MERAH if v > 0 else BIRU) if (a_ > 0 and abs(v) >= a_) else ("rgba(214,39,40,0.40)" if v > 0 else "rgba(31,119,180,0.40)")
        for v in d
    ]
    fig = go.Figure(go.Bar(
        y=list(d.index), x=d.values, orientation="h", marker_color=warna,
        text=[n(v, 1, True) for v in d], textposition="outside", textfont_size=10, cliponaxis=False,
        customdata=np.column_stack([rk_s["p_kering"].values, rk_s["kering_model_pct"].values, rk_s["kering_target_pct"].values]),
        hovertemplate="<b>%{y}</b><br>Selisih: %{x:+.1f} bln/100<br>Proyeksi: %{customdata[0]:.1f} | Baseline Model: %{customdata[1]:.1f} | Obs: %{customdata[2]:.1f}<extra></extra>"
    ))
    if a_ > 0: fig.add_vrect(x0=-a_, x1=a_, fillcolor="#94a3b8", opacity=0.16, line_width=0, layer="below")
    fig.add_vline(x=0, line_color="#374151", line_width=1.2); lim = max(a_ * 1.15, float(d.abs().max()) * 1.4, 3.0)
    fig.update_xaxes(range=[-lim, lim]); fig.update_yaxes(type="category", tickmode="array", tickvals=list(d.index), ticktext=list(d.index), automargin=True, tickfont=dict(size=10)); return fig


def peta_dari(R, mode, tinggi, lebar=400):
    a = R["agg"]
    if mode == "Kering":
        return fig_peta(a, "p_kering", 0, max(20.0, float(np.ceil(np.nanpercentile(a["p_kering"], 98) / 10) * 10)), "dari 100", KERING_BMKG, tinggi, lebar)
    if mode == "Bias":
        a = a.assign(bias=a["kering_model_pct"] - a["kering_target_pct"]); lim = max(5.0, float(np.ceil(np.nanpercentile(a["bias"].abs(), 98) / 5) * 5))
        return fig_peta(a, "bias", -lim, lim, "bln/100", DIVERGEN_BMKG, tinggi, lebar, zmid=0, catatan="merah = model terlalu kering<br>biru = model terlalu basah")
    lim = float(max(5.0, round(R["amb"]))) if np.isfinite(R["amb"]) else max(5.0, float(np.ceil(np.nanpercentile(a["selisih"].abs(), 98) / 5) * 5))
    return fig_peta(a, "selisih", -lim, lim, "bln/100", DIVERGEN_BMKG, tinggi, lebar, zmid=0, mask=a["nyata"], catatan=f"{int(a['nyata'].sum())} dari {len(a)} kotak beda nyata<br>(kotak agak pudar = belum pasti)")


def fig_deret(sk, t0=None, t1=None):
    s_ = D["reg"][D["reg"]["SPI"] == sk]; s_ = s_ if t0 is None else s_[s_["tahun"].between(t0, t1)]; s_ = s_.sort_values(["tahun", "bulan"])
    x = pd.to_datetime(dict(year=s_["tahun"], month=s_["bulan"], day=1))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=s_["spi_p90"], line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=x, y=s_["spi_p10"], fill="tonexty", fillcolor="rgba(31,119,180,.18)", line=dict(width=0), name="Sebaran antar-simulasi (p10-p90)", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x, y=s_["spi_median"], line=dict(color=PROY, width=1.8), name="SPI Median Simulasi", hovertemplate="%{x|%b %Y}<br>SPI Median: %{y:.2f}<extra></extra>"))
    kr = s_["spi_median"] <= -1
    fig.add_trace(go.Scatter(x=x[kr], y=s_.loc[kr, "spi_median"], mode="markers", marker=dict(color=MERAH, size=6), name="Bulan kering (SPI ≤ -1)", hoverinfo="skip"))
    fig.add_hline(y=-1, line_dash="dash", line_color=MERAH, line_width=1.4, annotation_text="Batas Kering (-1)", annotation_position="bottom right", annotation_font_size=9.5)
    fig.add_hline(y=0, line_color="#64748b", line_width=1)
    fig.update_yaxes(title_text="Indeks SPI"); return fig


def fig_heat(sk, t0, t1):
    G = D["b_grid"]; G = G[(G["SPI"] == sk) & G["tahun"].between(t0, t1)]
    pv = G.groupby(["bulan", "tahun"])["p_kering"].mean().mul(100).unstack("tahun").reindex(range(1, 13))
    zmax = max(30.0, float(np.ceil(np.nanpercentile(pv.values, 98) / 10) * 10))
    fig = go.Figure(go.Heatmap(
        z=pv.values, x=pv.columns, y=[BULAN[m - 1] for m in pv.index], colorscale=KERING_BMKG, zmin=0, zmax=zmax, xgap=1, ygap=1,
        colorbar=dict(title=dict(text="% kering", font=dict(size=9), side="top"), thickness=8, len=0.9, tickfont=dict(size=9)),
        hovertemplate="%{y} %{x}<br>%{z:.0f}% anggota simulasi kering<extra></extra>"
    ))
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=9.5), gridcolor="white"); fig.update_xaxes(dtick=5, tickfont=dict(size=9.5)); return fig


# ------------------------------------------------------------------ teks laporan & panel
ISTILAH = ("<b>SPI</b> membandingkan hujan suatu periode dengan hujan biasanya (1981-2010): 0 = normal, negatif = lebih kering, dan <b>SPI ≤ −1 disebut bulan kering</b>. "
           "<b>Jangka</b> 3/6/12 bulan = hujan dijumlahkan selama 3/6/12 bulan terakhir. "
           "<b>\"Bulan kering per 100\"</b> = proporsi bulan kering dalam 100 bulan (secara teoretis ~16 dari 100 bulan pada periode acuan).")


def teks_panel(R, sm, am, cek, n_ok, yak, naik, turun, mode):
    amb, sel, kode, bias = R["amb"], R["sel"], R["kode"], R["base"] - R["ref"]
    gagal = [c[1][0].lower() + c[1][1:] for c in cek if not c[2]]
    amb_t = (f"selang 95%: {n(R['ci'][0], 1, True)} s/d {n(R['ci'][1], 1, True)}" if R.get("ci") else f"±{n(amb, 1)}") if np.isfinite(amb) else "(tidak terhitung)"
    KODE_KES = {
        "sama": f"Selisih {n(sel, 1, True)} lebih kecil daripada batas naik-turun alami ({amb_t}), jadi <b>belum bisa disebut perubahan nyata</b>.",
        "lebih": f"Selisih {n(sel, 1, True)} lebih besar daripada batas naik-turun alami ({amb_t}): bulan kering diproyeksikan <b>lebih sering</b>.",
        "kurang": f"Selisih {n(sel, 1, True)} lebih besar daripada batas naik-turun alami ({amb_t}): bulan kering diproyeksikan <b>lebih jarang</b>.",
        "sedikit": "Data terlalu sedikit untuk disimpulkan."
    }
    T = {}
    am_t = (f"Rentang {n(min(sm.values()), 1, True)} s/d {n(max(sm.values()), 1, True)} bulan per 100. " + ("Semua model searah." if am["N"] >= 2 and am["n_s"] == am["N"] else "Model tidak sepakat arahnya, jadi <b>tanda perubahan bergantung pada model yang dipilih</b>.")) if len(sm) >= 2 else "Data perbandingan model belum ada."
    T["k_sel"] = ("Kartu: selisih", "Proyeksi dikurangi masa lalu model (bulan kering per 100 bulan).", KODE_KES[kode])
    T["k_model"] = ("Kartu: rentang model", "Selisih yang sama dihitung dengan empat model statistik (GLM, RF, XGBoost, NN).", am_t)
    T["k_lalu"] = ("Kartu: masa lalu model vs nyata", "Perbandingan frekuensi kering 1981-2010 model vs CHIRPS.",
                   f"Model memberi {n(R['base'], 0)} vs {n(R['ref'], 0)} pengamatan (bias {n(bias, 1, True)} bln/100). Karena itu pembacaan difokuskan pada <b>selisih relatif</b>.")
    T["k_yak"] = ("Kartu: syarat terpenuhi", "Enam syarat ketangguhan model downscaling.",
                  f"Terpenuhi: <b>{n_ok} dari 6 syarat</b>." + (" Belum terpenuhi: " + "; ".join(gagal) + "." if gagal else ""))

    a, rk = R["agg"], R["rk"]
    if mode == "Kering":
        cara_p = f"Tiap kotak = grid ~5 km. Palet SPI BMKG: kuning gading = jarang kering, oranye hingga merah tua = sering kering pada {R['t0']}-{R['t1']}."
        kes_p = (f"Paling sering kering: <b>{rk.index[-1]}</b> ({n(rk['p_kering'].iloc[-1], 0)}/100 bln); terjarang: <b>{rk.index[0]}</b> ({n(rk['p_kering'].iloc[0], 0)}/100 bln)." if len(rk) else "")
    else:
        cara_p = "Merah/oranye = lebih sering kering, biru/hijau = lebih jarang, kuning gading = mendekati nol. Warna penuh = lolos uji beda nyata FDR."
        if len(a) and "wilayah" in a and a["wilayah"].notna().any():
            pos = float((a["selisih"] > 0).mean() * 100); rs = a.groupby("wilayah")["selisih"].mean(); rs.index = nama_pendek(rs.index.tolist())
            kes_p = f"{n(pos, 0)}% grid naik, {n(100 - pos, 0)}% turun. Tertinggi di <b>{rs.idxmax()}</b> ({n(rs.max(), 1, True)}), terendah di <b>{rs.idxmin()}</b> ({n(rs.min(), 1, True)}). Beda nyata FDR: <b>{int(a['nyata'].sum())}/{len(a)} grid</b>."
        else:
            kes_p = "Baca sebagai kecenderungan wilayah."
    T["peta"] = (f"Peta ({mode})", cara_p, kes_p)

    yr = R["per_th"]; b10, se10 = tren_tahun(yr)
    kes_b = f"{int((yr > R['base']).sum())}/{len(yr)} tahun di atas baseline ({n(R['base'], 0)}). Puncak: <b>{int(yr.idxmax())}</b> ({n(yr.max(), 0)}), terendah: <b>{int(yr.min())}</b> ({n(yr.min(), 0)})."
    if np.isfinite(b10): kes_b += f" Tren linear {n(b10, 1, True)} poin/dekade (±{n(2 * se10, 1)})."
    T["blok"] = ("Per tahun", "Batang = % bulan kering tahunan; garis biru = rata-rata bergulir 5 tahun; putus merah = baseline.", kes_b)

    d = R["dbulan"].dropna()
    if len(d) >= 2:
        top = d.nlargest(2); low = d.idxmin()
        n_ny = int(R["bulan_nyata"].reindex(d.index).fillna(False).sum())
        kes_m = f"Kenaikan terbesar pada <b>{BULAN[top.index[0] - 1]}</b> ({n(top.iloc[0], 1, True)}) & <b>{BULAN[top.index[1] - 1]}</b> ({n(top.iloc[1], 1, True)}); terendah {BULAN[low - 1]} ({n(d.min(), 1, True)}). Beda nyata FDR: <b>{n_ny}/{len(d)} bulan</b>."
    else:
        kes_m = "Data bulanan tidak cukup."
    T["bulan"] = ("Selisih per bulan", "Selisih proyeksi vs masa lalu per bulan kalender.", kes_m)

    if len(sm) >= 2:
        v = list(sm.values())
        kes_o = f"{am['n_s']}/{am['N']} model searah (rentang {n(min(v), 1, True)} s/d {n(max(v), 1, True)} bln/100)."
    else:
        kes_o = "Data perbandingan model belum ada."
    T["model"] = ("Perbandingan antar-model", "Sensitivitas hasil terhadap pilihan algoritma downscaling.", kes_o)

    if len(rk):
        dk = rk["p_kering"] - rk["kering_model_pct"]
        kes_k = f"Rentang selisih kab/kota: {n(dk.min(), 1, True)} s/d {n(dk.max(), 1, True)} bln/100."
    else:
        kes_k = "Batas kab/kota belum tersedia."
    T["kab"] = ("Kabupaten/kota", "Rata-rata selisih grid per wilayah administrasi.", kes_k)
    return T


def teks_deret(sk):
    r = D["reg"]
    if r is None: return None
    s_ = r[r["SPI"] == sk].sort_values(["tahun", "bulan"]).dropna(subset=["spi_median"])
    if s_.empty: return None
    kr = (s_["spi_median"] <= -1).to_numpy(); run = best = 0
    for x in kr: run = run + 1 if x else 0; best = max(best, run)
    mn = s_.loc[s_["spi_median"].idxmin()]
    cara_ = f"Garis biru = SPI median ({sk}) dari {meta.get('n_anggota_ensemble', 20)} simulasi; pita = sebaran p10-p90. Titik merah (SPI ≤ -1) = bulan kering."
    kes = f"Median mencapai SPI ≤ −1 pada <b>{int(kr.sum())}/{len(s_)} bulan</b>; titik terendah {BULAN[int(mn['bulan']) - 1]} {int(mn['tahun'])} (SPI {n(mn['spi_median'], 2)}), durasi terpanjang <b>{best} bulan beruntun</b>."
    return cara_, kes


# ================================================================== LAPORAN (?laporan=1)
def halaman_baru(): st.markdown('<div style="break-before:page"></div>', unsafe_allow_html=True)


def halaman_laporan():
    sk = str(st.query_params.get("skala", "SPI-3")); sk = sk if sk in list(meta["spi_skala"]) else "SPI-3"
    R = ringkas(sk, PRESET["Sepanjang tahun"], th_all[0], th_all[-1]); sm = model_selisih(sk, th_all[0], th_all[-1], R=R)
    kh, cek, n_ok, yak, yak_c, am, naik, turun = kartu_html(R, sm, bg="#ffffff")
    kode = R["kode"]; model_nama = str(meta.get("model", "-")).replace(" [mu+V1]", "").replace("P: ", "")
    TP = teks_panel(R, sm, am, cek, n_ok, yak, naik, turun, "Selisih")
    def cara2(k): st.markdown(f'<div class="cara"><b>Cara membaca:</b> {TP[k][1]}</div><div class="kes"><b>Kesimpulan:</b> {TP[k][2]}</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="judul">{JUDUL_PROYEK}</div><div class="sublap">Laporan hasil proyeksi · {PEMBUAT} · analisis versi {meta.get("versi_notebook", "-")} · dijalankan {meta.get("tanggal_run", "-")}</div>', unsafe_allow_html=True)
    st.markdown("## 1. Ringkasan")
    kal = {"sama": f"Selisih ini masih dalam naik-turun alami antar-tahun (±{n(R['amb'], 1)}), sehingga **belum ada perubahan yang bisa dipastikan**.", "lebih": "Bulan kering diproyeksikan **lebih sering** daripada masa lalu.", "kurang": "Bulan kering diproyeksikan **lebih jarang** daripada masa lalu.", "sedikit": "Data terlalu sedikit untuk disimpulkan."}[kode]
    st.markdown(f'<div class="jawab"><b>Jawaban:</b> menurut model terpilih ({model_nama}), sekitar <b>{n(R["proy"], 0)} dari 100 bulan</b> kering pada {H0}-{H1}, dibanding <b>{n(R["base"], 0)}</b> pada 1981-2010 menurut model yang sama (selisih {n(R["sel"], 1, True)}). Pengamatan nyata sekitar {n(R["ref"], 0)} dari 100 bulan. {kal.replace("**", "")}</div>', unsafe_allow_html=True)
    st.write(""); iframe(kh, 98)
    st.markdown(f'<div class="cara">{ISTILAH}</div>', unsafe_allow_html=True)
    for k_ in ("k_sel", "k_model", "k_lalu", "k_yak"):
        st.markdown(f"*{TP[k_][0].replace('Kartu: ', '').capitalize()}*"); cara2(k_)

    halaman_baru(); st.markdown("## 2. Hasil Proyeksi & Dinamika Spasial-Temporal")
    rows = []
    for s_ in meta["spi_skala"]:
        Rk = ringkas(s_, PRESET["Sepanjang tahun"], th_all[0], th_all[-1])
        if Rk: rows.append({"Jangka": NAMA_SKALA_PANJANG.get(s_, s_), "Masa lalu (model)": n(Rk["base"]), "Pengamatan": n(Rk["ref"]), f"Proyeksi {H0}-{H1}": n(Rk["proy"]), "Selisih": n(Rk["sel"], 1, True), "Naik-turun alami (±)": n(Rk["amb"]), "Tafsir": f'{SIM[Rk["kode"]]} {KATA[Rk["kode"]]}'})
    st.table(pd.DataFrame(rows).set_index("Jangka"))
    gambar(peta_dari(R, "Selisih", 380, 800), 380); cara2("peta")
    gambar(fig_tahun(R), 240); cara2("blok")
    gambar(fig_bulan(R), 220); cara2("bulan")
    if len(sm) >= 2: gambar(fig_model(sm, amb=R["amb"]), 220); cara2("model")
    if len(R["rk"]): gambar(fig_kab(R), 220); cara2("kab")

    ts = teks_deret(sk)
    if ts:
        halaman_baru()
        st.markdown(f"## 3. Deret Waktu SPI & Heatmap Musiman ({NAMA_SKALA_PANJANG.get(sk, sk)})")
        gambar(fig_deret(sk), 260, legenda=True)
        st.markdown(f'<div class="cara"><b>Cara membaca:</b> {ts[0]}</div><div class="kes"><b>Kesimpulan:</b> {ts[1]}</div>', unsafe_allow_html=True)
        gambar(fig_heat(sk, th_all[0], th_all[-1]), 260)

    halaman_baru(); st.markdown("## 4. Validasi & Enam Syarat Ketangguhan")
    st.table(pd.DataFrame([{"Syarat": c[1], "Status": "✓ terpenuhi" if c[2] else "✗ belum", "Keterangan": c[3]} for c in cek]).set_index("Syarat"))
    st.caption(f"Sumber: {meta.get('gcm')} ({meta.get('skenario')}); {meta.get('target')}; ERA5. Model: {meta.get('model', '-')}. Status: {meta.get('status_gerbang', '-')}.")


if LAPORAN:
    halaman_laporan(); st.stop()

# ================================================================== DASHBOARD UTAMA & EKSPLORASI
LAYAR_PENUH = """<style>body{margin:0;font-family:"Segoe UI",Arial,sans-serif}button{margin-top:19px;width:100%;height:30px;border:1px solid #c8cfd8;border-radius:6px;background:#fff;color:#1d2b3a;font-size:12px;cursor:pointer}button:hover{background:#eef5f9}</style>
<button id="b" onclick="go()">⛶ Layar penuh</button>
<script>function go(){var b=document.getElementById('b'),f=function(){b.textContent='Tekan F11';};try{var d=window.parent.document; if(d.fullscreenElement){d.exitFullscreen();}else{var p=d.documentElement.requestFullscreen(); if(p&&p.catch){p.catch(f);}}}catch(e){f();}}</script>"""

if EMBED:
    LAYAR_PENUH = LAYAR_PENUH.replace("border:1px solid #c8cfd8;border-radius:6px;background:#fff;color:#1d2b3a", "border:1px solid rgba(255,255,255,.35);border-radius:6px;background:transparent;color:#fff").replace("button:hover{background:#eef5f9}", "button:hover{background:rgba(255,255,255,.12)}")
    with st.container(key="filt2"):
        c_s, c_m, c_y, c_p, c_f = st.columns([2.2, 1.5, 2.0, 2.0, 1.1], gap="small")
else:
    c_t, c_s, c_m, c_y, c_p, c_f = st.columns([2.8, 2.1, 1.3, 1.5, 1.8, 1.0], gap="small")

with c_s: skala = pilih(list(meta["spi_skala"]), "skala", "Skala SPI", fmt=lambda s: NAMA_SKALA.get(s, s))
with c_m: musim = st.selectbox("Musim", list(PRESET), key="spi_musim")
with c_y: t0, t1 = st.select_slider("Periode Tahun", th_all, value=(th_all[0], th_all[-1]), key="spi_tahun")
with c_p: mode = pilih(["Selisih", "Kering", "Bias"], "mode_peta", "Lapisan Peta", default=PETA_AWAL)
with c_f: iframe(LAYAR_PENUH, 52)
if not EMBED:
    c_t.markdown(f'<div class="ttl">{JUDUL_PROYEK}</div><div class="sub">{meta.get("gcm")} · {meta.get("skenario")} · periode {t0}-{t1} · vs 1981-2010 · kering = SPI ≤ −1</div>', unsafe_allow_html=True)

R = ringkas(skala, PRESET[musim], t0, t1)
if R is None:
    st.warning("Tidak ada data untuk kombinasi filter ini."); st.stop()

sm = model_selisih(skala, t0, t1, R=R)
am0 = arah_model(sm)
kh, cek, n_ok, yak, yak_c, am, naik, turun = kartu_html(R, sm, atas=banner(R, sm, am0)[0], zoom=FSKALA)
iframe(kh, int((H_KPI + H_BAN) * FSKALA))

# Strip Sorotan Otomatis (Actionable Insights)
st.markdown(sorotan_insight_html(R, skala, t0, t1), unsafe_allow_html=True)

# Tab Navigasi
tab_utama, tab_deret, tab_validasi = st.tabs([
    "🗺️ Ringkasan Spasial & Proyeksi Wilayah",
    "📈 Deret Waktu SPI & Pola Musiman (Heatmap)",
    "🔬 Validasi Downscaling & Sensitivitas Model"
])

with tab_utama:
    col_peta, col_b, col_c = st.columns([3.6, 4.2, 4.2], gap="small")
    with col_peta:
        judul_peta = {
            "Selisih": "Peta · selisih vs masa lalu · warna penuh = beda nyata (FDR)",
            "Kering": "Peta · frekuensi bulan kering (per 100 bulan · palet BMKG)",
            "Bias": "Peta · bias baseline: model − nyata (bln/100)"
        }[mode]
        gambar(peta_dari(R, mode, H_PETA, LEBAR_PETA), H_PETA, judul=judul_peta)
    with col_b:
        gambar(fig_tahun(R), H_KECIL, judul="Proyeksi per tahun · garis = rata-rata 5 thn · putus = baseline")
        gambar(fig_bulan(R), H_KECIL, judul="Anomali per bulan · warna penuh = beda nyata (FDR)")
    with col_c:
        if len(R["rk"]):
            gambar(fig_kab(R), H_KECIL, judul="Per kab/kota · selisih · pita abu = naik-turun alami")
        else:
            st.caption("Batas kab/kota belum tersedia.")
        if len(sm) >= 2:
            judul_mod = "Perbandingan 4 model · ★ = dipakai · pita abu = alami" if len(R["bulan"]) == 12 else "Perbandingan 4 model · seluruh bulan (tak ikut filter musim)"
            gambar(fig_model(sm, compact=True, amb=R["amb"]), H_KECIL, judul=judul_mod)
        else:
            st.caption("Data perbandingan model belum ada.")

with tab_deret:
    c_d1, c_d2 = st.columns([1.15, 1.0], gap="medium")
    with c_d1:
        if D["reg"] is not None:
            gambar(fig_deret(skala, t0, t1), 320, judul=f"Deret waktu SPI median & sebaran p10-p90 ({skala}, {t0}-{t1})", legenda=True)
            ts = teks_deret(skala)
            if ts: st.caption(ts[0])
        else:
            st.info("Data deret regional (dashboard_bulanan_regional.csv.gz) belum tersedia.")
    with c_d2:
        gambar(fig_heat(skala, t0, t1), 320, judul=f"Heatmap peluang kekeringan per bulan & tahun ({skala})")
        st.caption("Menunjukkan porsi anggota ensemble yang mengalami SPI ≤ -1 pada tiap bulan. Berguna melihat klaster kekeringan multi-tahun.")

with tab_validasi:
    col_v1, col_v2 = st.columns([1.1, 1.0], gap="medium")
    with col_v1:
        st.markdown("**1. Daftar Periksa Enam Syarat Ketangguhan Downscaling**")
        st.dataframe(pd.DataFrame([{"Syarat": c[1], "Status": "✅ Terpenuhi" if c[2] else "⚠️ Belum", "Bukti / Keterangan": c[3]} for c in cek]), use_container_width=True, hide_index=True)

        V_ = meta.get("validasi") or {}
        if V_:
            def _v(k, d=3, plus=True):
                x = V_.get(k); return n(x, d, plus) if isinstance(x, (int, float)) else "-"
            st.markdown("**2. Ringkasan Metrik Validasi & Batasan Teknis**")
            st.markdown(
                f"- **Skill Sefase (ERA5, {V_.get('model', UTAMA or 'model dipakai')}):** CRPSS rolling-origin **{_v('crpss_t1_rolling')}**, CV blok-tahun {_v('crpss_t1_cv')}, hold-out 2021-2025 {_v('crpss_t1_holdout')}.\n"
                f"- **Skill Transfer GCM (Prediktor Iklim):** CRPSS {_v('crpss_t2_oof')} (klimatologi stokastik {_v('crpss_t2_klim_stokastik')}).\n"
                f"- **Bias Klimatologi 1981-2020 ({skala}):** Model {n(R['base'], 1, False)} vs pengamatan {n(R['ref'], 1, False)} bulan kering/100 bulan.\n"
                f"- **Resolusi Spasial:** Grid ~5 km diturunkan dari {V_.get('n_sel_gcm', 4)} sel GCM; baca sebagai tren wilayah, bukan prakiraan titik."
            )

    with col_v2:
        if D["gerb"] is not None and {"a_lolos", "b_lolos", "c_lolos", "a_crpss_t1", "b_qq_rasio", "c_kering_pct", "acuan_c"} <= set(D["gerb"].columns):
            gb = D["gerb"]; ok = lambda v: "✅" if bool(v) else "⚠️"
            st.markdown("**3. Gerbang Seleksi Empat Model Statistik**")
            st.dataframe(pd.DataFrame({
                "Model": gb["model"] + np.where(gb["model"] == UTAMA, " ★", ""),
                "A. Skill CRPSS T1": [f"{ok(l)} {n(v, 3, True)}" for l, v in zip(gb["a_lolos"], gb["a_crpss_t1"])],
                "B. Rasio QQ": [f"{ok(l)} {n(v, 2)}" for l, v in zip(gb["b_lolos"], gb["b_qq_rasio"])],
                "C. Frek. Kering (vs Obs)": [f"{ok(l)} {n(v, 1)} (vs {n(a_, 1)})" for l, v, a_ in zip(gb["c_lolos"], gb["c_kering_pct"], gb["acuan_c"])]
            }), use_container_width=True, hide_index=True)

        if D["sens"] is not None and {"model", "varian", "delta_mu_pct"} <= set(D["sens"].columns):
            sv = D["sens"].pivot_table(index="model", columns="varian", values="delta_mu_pct", aggfunc="first")
            sv = sv.drop(index="Hujan GCM mentah", errors="ignore").round(1).map(lambda v: n(v, 1, True))
            st.markdown("**4. Uji Sensitivitas Prediktor (Δ Rata-Rata Hujan %)**")
            st.dataframe(sv, use_container_width=True)

FA, FB, FC = (' style="grid-template-columns:1fr"', "<div>", "</div>") if EMBED else ("", "", "")
st.markdown(
    f'<div class="foot"{FA}>{FB}{meta.get("gcm")} {meta.get("skenario")} · acuan {meta.get("target")} · run {meta.get("tanggal_run", "-")} · '
    f'uji beda nyata: {R.get("uji", "-")} · gambaran kecenderungan iklim, bukan prakiraan cuaca{" · " + PEMBUAT if PEMBUAT else ""}{FC}</div>',
    unsafe_allow_html=True
)

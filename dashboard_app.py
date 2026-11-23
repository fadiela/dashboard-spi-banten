"""Dashboard satu halaman: downscaling CMCC-ESM2 dan proyeksi SPI Banten."""
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Downscaling CMCC-ESM2 dan SPI Banten",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------
# Konfigurasi dan data
ROOT = Path(os.environ.get("HASIL_DIR", Path(__file__).resolve().parent))
META_PATH = ROOT / "dashboard_meta.json"

st.markdown("""
<style>
  .block-container {max-width: 1440px; padding-top: 1.6rem; padding-bottom: 3rem;}
  .stApp {background: #f7f8fa;}
  h1, h2, h3 {color: #183b32;}
  .intro {color:#52615c; font-size:1rem; line-height:1.65; max-width:1050px;}
  .section-note {background:#eef3f0; border-left:4px solid #52796f; padding:12px 16px;
                 border-radius:5px; color:#33453e; line-height:1.55; margin:8px 0 18px;}
  .warning-note {background:#fff5e8; border-left:4px solid #d18a35; padding:12px 16px;
                 border-radius:5px; color:#5a4630; line-height:1.55; margin:8px 0 18px;}
  .small-muted {color:#68766f; font-size:.88rem;}
  div[data-testid="stMetric"] {background:white; border:1px solid #e4e9e6;
      padding:14px 16px; border-radius:9px;}
  hr {border-color:#e1e7e3;}
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner="Memuat data dashboard...")
def load_data():
    if not META_PATH.exists():
        raise FileNotFoundError(f"Metadata tidak ditemukan: {META_PATH}")
    with META_PATH.open(encoding="utf-8") as f:
        meta = json.load(f)

    names = {
        "grid_spi": "dashboard_bulanan_per_grid.csv.gz",
        "baseline": "dashboard_baseline_bulan_grid.csv.gz",
        "grid": "dashboard_grid.csv",
        "regional": "dashboard_bulanan_regional.csv.gz",
        "correlation": "dashboard_korelasi.csv",
        "tests": "dashboard_uji.csv",
    }
    data = {"meta": meta}
    for key, filename in names.items():
        path = ROOT / filename
        data[key] = pd.read_csv(path) if path.exists() else None
    return data


try:
    D = load_data()
except Exception as exc:
    st.error(f"Data dashboard gagal dimuat: {exc}")
    st.stop()

meta = D["meta"]
if meta.get("gcm") != "CMCC-ESM2":
    st.warning("Metadata GCM pada folder data bukan CMCC-ESM2. Periksa kembali berkas yang digunakan.")

gcm = meta.get("gcm", "CMCC-ESM2")
scenario = meta.get("skenario", "SSP370")
target = meta.get("target", "CHIRPS")
horizon = meta.get("horizon", [2026, 2050])
year_start, year_end = int(horizon[0]), int(horizon[1])
baseline_period = (meta.get("bulanan") or {}).get("baseline_periode", [1981, 2010])
model_name = str(meta.get("model", "Model statistik")).replace("P: ", "").replace(" [mu+V1]", "")
valid = meta.get("validasi") or {}
scales = meta.get("spi_skala", ["SPI-3", "SPI-6", "SPI-12"])
month_names = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
season_months = {
    "Sepanjang tahun": list(range(1, 13)),
    "Des–Feb": [12, 1, 2],
    "Mar–Mei": [3, 4, 5],
    "Jun–Agu": [6, 7, 8],
    "Sep–Nov": [9, 10, 11],
}

G = D.get("grid_spi")
B = D.get("baseline")
if G is None or B is None:
    st.error("Berkas dashboard_bulanan_per_grid.csv.gz atau dashboard_baseline_bulan_grid.csv.gz tidak tersedia.")
    st.stop()

required_g = {"SPI", "tahun", "bulan", "p_kering", "grid_id"}
required_b = {"SPI", "bulan", "grid_id", "kering_model_pct", "kering_target_pct"}
if not required_g.issubset(G.columns) or not required_b.issubset(B.columns):
    st.error("Struktur kolom data SPI tidak sesuai dengan aplikasi. Periksa kembali ekspor notebook.")
    st.stop()

years = sorted(pd.to_numeric(G["tahun"], errors="coerce").dropna().astype(int).unique().tolist())
if not years:
    st.error("Tidak ditemukan informasi tahun pada data SPI.")
    st.stop()


def fmt(value, digits=1, signed=False):
    if pd.isna(value):
        return "—"
    spec = f"{value:+.{digits}f}" if signed else f"{value:.{digits}f}"
    return spec.replace(".", ",")


def filtered_data(scale, y0, y1, months):
    gs = G[(G["SPI"] == scale) & G["tahun"].between(y0, y1) & G["bulan"].isin(months)].copy()
    bs = B[(B["SPI"] == scale) & B["bulan"].isin(months)].copy()
    if gs.empty or bs.empty:
        return None
    projected = float(gs["p_kering"].mean() * 100)
    baseline_model = float(bs["kering_model_pct"].mean())
    observed = float(bs["kering_target_pct"].mean())
    annual = gs.groupby("tahun")["p_kering"].mean().mul(100)
    monthly = gs.groupby("bulan")["p_kering"].mean().mul(100).reindex(range(1, 13))
    spatial = gs.groupby("grid_id")["p_kering"].mean().mul(100).rename("proyeksi_pct").reset_index()
    base_spatial = bs.groupby("grid_id")["kering_model_pct"].mean().rename("baseline_pct").reset_index()
    spatial = spatial.merge(base_spatial, on="grid_id", how="left")
    grid = D.get("grid")
    if grid is not None and {"grid_id", "lon", "lat"}.issubset(grid.columns):
        spatial = spatial.merge(grid[["grid_id", "lon", "lat"]], on="grid_id", how="left")
    spatial["selisih_pp"] = spatial["proyeksi_pct"] - spatial["baseline_pct"]
    return {
        "grid": gs, "baseline": bs, "projected": projected,
        "baseline_model": baseline_model, "observed": observed,
        "delta": projected - baseline_model, "annual": annual,
        "monthly": monthly, "spatial": spatial,
    }


def significance_label(scale, y0, y1, months):
    if y0 != year_start or y1 != year_end or len(months) != 12:
        return "Belum diuji formal untuk rentang filter ini"
    summary = ((meta.get("uji") or {}).get("ringkas") or {}).get(scale)
    if not summary:
        return "Hasil uji formal tidak tersedia"
    if summary.get("nyata") is True:
        return "Berbeda nyata menurut uji formal (FDR)"
    return "Belum berbeda nyata menurut uji formal (FDR)"


# ---------------------------------------------------------------------
# Header
st.title("Downscaling Curah Hujan CMCC-ESM2 dan Proyeksi SPI Banten")
st.markdown(
    f'<p class="intro">Dashboard ini merangkum proses evaluasi downscaling curah hujan dari '
    f'<b>{gcm}</b> dengan data referensi <b>{target}</b>, kemudian menampilkan hasil indeks '
    f'Standardized Precipitation Index (SPI) untuk mengkaji kecenderungan kekeringan di Provinsi Banten. '
    f'Proyeksi menggunakan skenario <b>{scenario}</b> pada periode <b>{year_start}–{year_end}</b>. '
    f'Hasil merupakan proyeksi bersyarat skenario, bukan ramalan cuaca tahunan.</p>',
    unsafe_allow_html=True,
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("GCM", gcm)
m2.metric("Data referensi", target)
m3.metric("Skenario", scenario)
m4.metric("Periode proyeksi", f"{year_start}–{year_end}")
st.caption(
    f"Model statistik yang ditampilkan: {model_name} · "
    f"Baseline SPI: {baseline_period[0]}–{baseline_period[1]} · "
    f"Tanggal pemrosesan: {meta.get('tanggal_run', '—')}"
)

st.divider()

# ---------------------------------------------------------------------
# 1. Downscaling
st.header("1. Evaluasi downscaling")
st.markdown(
    "Bagian ini menjelaskan apakah hubungan data iklim dan proses downscaling cukup mendukung "
    "penggunaan hasil CMCC-ESM2 sebagai masukan proyeksi. Perlu dibedakan antara validasi pada "
    "prediktor ERA5 yang sefase dengan CHIRPS dan penerapan model pada prediktor GCM yang tidak sefase."
)

v1, v2, v3 = st.columns(3)
v1.metric("CRPSS rolling-origin (ERA5)", fmt(valid.get("crpss_t1_rolling"), 3, True))
v2.metric("CRPSS CV blok-tahun (ERA5)", fmt(valid.get("crpss_t1_cv"), 3, True))
v3.metric("CRPSS pada prediktor GCM", fmt(valid.get("crpss_t2_oof"), 3, True))

c1, c2 = st.columns([1.15, 1])
with c1:
    st.subheader("Kinerja validasi")
    vals = [
        ("Rolling-origin ERA5", valid.get("crpss_t1_rolling")),
        ("CV blok-tahun ERA5", valid.get("crpss_t1_cv")),
        ("Prediktor GCM", valid.get("crpss_t2_oof")),
        ("Klimatologi stokastik (pembanding)", valid.get("crpss_t2_klim_stokastik")),
    ]
    vals = [(label, float(value)) for label, value in vals if isinstance(value, (int, float))]
    if vals:
        chart = go.Figure(go.Bar(
            x=[v for _, v in vals], y=[k for k, _ in vals], orientation="h",
            marker_color=["#52796f" if "ERA5" in k else "#d18a35" for k, _ in vals],
            text=[fmt(v, 3, True) for _, v in vals], textposition="outside",
            cliponaxis=False,
        ))
        chart.add_vline(x=0, line_color="#66736d", line_width=1)
        chart.update_layout(height=300, margin=dict(l=10, r=55, t=10, b=20),
                            xaxis_title="CRPSS (nilai positif menunjukkan skill di atas klimatologi)",
                            yaxis_title=None, plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(chart, use_container_width=True)
    else:
        st.info("Metrik validasi belum tersedia pada metadata.")
with c2:
    st.subheader("Apa arti hasil validasi?")
    st.markdown(
        f"- Model statistik: **{valid.get('model', model_name)}**.\n"
        f"- Jalur prediktor: **{valid.get('jalur_prediktor', '—')}**.\n"
        f"- Penyesuaian tren: **{valid.get('detrend', '—')}**.\n"
        f"- Harmonisasi: **{valid.get('harmonisasi', '—')}**.\n"
        f"- Hold-out yang tercatat: **{(meta.get('holdout') or {}).get('periode', ['—', '—'])[0]}–{(meta.get('holdout') or {}).get('periode', ['—', '—'])[1]}**."
    )
    st.markdown(
        '<div class="warning-note"><b>Catatan interpretasi:</b> CRPSS pada prediktor GCM bernilai negatif '
        'pada hasil yang tersimpan. Ini menunjukkan skill validasi pada ERA5 tidak otomatis terbawa '
        'ketika model diterapkan pada prediktor CMCC-ESM2. Karena itu, hasil proyeksi SPI perlu dibaca '
        'secara hati-hati dan relatif terhadap baseline model sendiri.</div>',
        unsafe_allow_html=True,
    )

# Hubungan GCM-target tersedia dalam tabel korelasi, tetapi bukan metrik galat curah hujan.
corr = D.get("correlation")
if corr is not None and {"unit", "jenis", "r_gcm_target"}.issubset(corr.columns):
    monthly_corr = corr[corr["jenis"].astype(str).str.lower().eq("bulan")].copy()
    monthly_corr = monthly_corr[monthly_corr["unit"].isin(month_names)]
    if not monthly_corr.empty:
        st.subheader("Hubungan temporal GCM dan CHIRPS")
        monthly_corr["urutan"] = monthly_corr["unit"].map({m: i for i, m in enumerate(month_names)})
        monthly_corr = monthly_corr.sort_values("urutan")
        monthly_corr["signifikan"] = monthly_corr.get("lolos_fdr_gcm_target", False)
        fig_corr = go.Figure(go.Bar(
            x=monthly_corr["unit"], y=monthly_corr["r_gcm_target"],
            marker_color=["#52796f" if bool(x) else "#c5cec9" for x in monthly_corr["signifikan"]],
            customdata=monthly_corr["signifikan"],
            hovertemplate="%{x}<br>r = %{y:.3f}<br>lolos FDR: %{customdata}<extra></extra>",
        ))
        fig_corr.add_hline(y=0, line_color="#59665f", line_width=1)
        fig_corr.update_layout(height=300, yaxis_title="Korelasi Pearson (r)",
                               xaxis_title="Bulan", plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig_corr, use_container_width=True)
        st.caption(
            "Korelasi dihitung antar-tahun pada rata-rata wilayah selama periode yang tercatat di metadata. "
            "Grafik ini menunjukkan keterkaitan temporal, bukan ukuran bias atau galat curah hujan."
        )
else:
    st.info("Tabel korelasi GCM–CHIRPS tidak tersedia. Grafik hubungan temporal tidak ditampilkan.")

st.markdown(
    '<div class="section-note"><b>Informasi yang belum tersedia di ekspor dashboard:</b> metrik evaluasi '
    'curah hujan seperti MAE, RMSE, bias/MBE, korelasi curah hujan hasil downscaling terhadap CHIRPS, '
    'serta perbandingan distribusi hujan sebelum dan sesudah downscaling. Dashboard tidak mengisi '
    'bagian tersebut dengan angka perkiraan.</div>',
    unsafe_allow_html=True,
)

st.divider()

# ---------------------------------------------------------------------
# 2. SPI
st.header("2. Hasil proyeksi kekeringan (SPI)")
st.markdown(
    "SPI mengukur penyimpangan curah hujan dari kondisi normal pada akumulasi waktu tertentu. "
    "Nilai negatif menunjukkan kondisi lebih kering; **SPI ≤ −1** digunakan sebagai ambang bulan kering."
)

f1, f2, f3 = st.columns([1, 1.4, 1.3])
with f1:
    selected_scale = st.selectbox("Skala SPI", scales, index=0,
                                  format_func=lambda x: {"SPI-3": "SPI-3 (3 bulan)", "SPI-6": "SPI-6 (6 bulan)", "SPI-12": "SPI-12 (12 bulan)"}.get(x, x))
with f2:
    selected_years = st.slider("Rentang tahun proyeksi", min_value=years[0], max_value=years[-1],
                               value=(max(years[0], year_start), min(years[-1], year_end)))
with f3:
    selected_season = st.selectbox("Periode musim", list(season_months.keys()), index=0)

y0, y1 = selected_years
months = season_months[selected_season]
R = filtered_data(selected_scale, y0, y1, months)
if R is None:
    st.warning("Tidak ada data untuk kombinasi skala SPI, tahun, dan musim yang dipilih.")
    st.stop()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Frekuensi kering proyeksi", f"{fmt(R['projected'], 1)} per 100 bulan")
k2.metric("Baseline model", f"{fmt(R['baseline_model'], 1)} per 100 bulan")
k3.metric("Referensi CHIRPS", f"{fmt(R['observed'], 1)} per 100 bulan")
k4.metric("Perubahan terhadap baseline", f"{fmt(R['delta'], 1, True)} poin")

status = significance_label(selected_scale, y0, y1, months)
st.markdown(f'<div class="section-note"><b>Interpretasi uji:</b> {status}. '
            'Perubahan dihitung terhadap baseline historis model yang sama. Nilai referensi CHIRPS ditampilkan '
            'sebagai konteks, bukan sebagai baseline proyeksi.</div>', unsafe_allow_html=True)

left, right = st.columns(2)
with left:
    st.subheader("Frekuensi bulan kering per tahun")
    annual = R["annual"]
    fig_year = go.Figure(go.Bar(
        x=annual.index.astype(int), y=annual.values,
        marker_color="#83a598",
        hovertemplate="%{x}<br>%{y:.1f} dari 100 bulan<extra></extra>",
    ))
    fig_year.add_hline(y=R["baseline_model"], line_dash="dash", line_color="#d18a35",
                       annotation_text="Baseline model")
    fig_year.update_layout(height=340, xaxis_title="Tahun", yaxis_title="Bulan kering per 100 bulan",
                           plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig_year, use_container_width=True)
with right:
    st.subheader("Pola bulanan")
    monthly = R["monthly"].dropna()
    fig_month = go.Figure(go.Bar(
        x=[month_names[int(i)-1] for i in monthly.index], y=monthly.values,
        marker_color="#52796f",
        hovertemplate="%{x}<br>%{y:.1f} dari 100 bulan<extra></extra>",
    ))
    fig_month.add_hline(y=R["baseline_model"], line_dash="dash", line_color="#d18a35",
                        annotation_text="Baseline model")
    fig_month.update_layout(height=340, xaxis_title="Bulan", yaxis_title="Bulan kering per 100 bulan",
                            plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig_month, use_container_width=True)

st.subheader("Sebaran spasial frekuensi bulan kering")
spatial = R["spatial"].dropna(subset=["lon", "lat"]) if {"lon", "lat"}.issubset(R["spatial"].columns) else pd.DataFrame()
if not spatial.empty:
    fig_map = px.scatter_geo(
        spatial, lon="lon", lat="lat", color="proyeksi_pct",
        color_continuous_scale=["#edf2ef", "#83a598", "#245b4b"],
        hover_name="grid_id", hover_data={"proyeksi_pct":":.1f", "selisih_pp":":+.1f", "lon":False, "lat":False},
        projection="mercator",
    )
    fig_map.update_geos(fitbounds="locations", visible=False)
    fig_map.update_layout(height=430, margin=dict(l=0, r=0, t=10, b=0),
                          coloraxis_colorbar_title="Per 100 bulan",
                          paper_bgcolor="white")
    st.plotly_chart(fig_map, use_container_width=True)
    st.caption("Setiap titik mewakili grid data. Peta menunjukkan pola pada grid model, bukan batas administrasi atau detail observasi stasiun.")
else:
    st.info("Koordinat grid tidak tersedia; peta spasial tidak ditampilkan.")

regional = D.get("regional")
if regional is not None and {"SPI", "tahun", "bulan", "spi_median", "spi_p10", "spi_p90"}.issubset(regional.columns):
    series = regional[(regional["SPI"] == selected_scale) & regional["tahun"].between(y0, y1)].sort_values(["tahun", "bulan"])
    if not series.empty:
        st.subheader("Deret waktu SPI")
        dates = pd.to_datetime(dict(year=series["tahun"], month=series["bulan"], day=1))
        fig_spi = go.Figure()
        fig_spi.add_trace(go.Scatter(x=dates, y=series["spi_p90"], line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig_spi.add_trace(go.Scatter(x=dates, y=series["spi_p10"], fill="tonexty",
                                     fillcolor="rgba(82,121,111,0.18)", line=dict(width=0),
                                     name="Rentang persentil 10–90"))
        fig_spi.add_trace(go.Scatter(x=dates, y=series["spi_median"], line=dict(color="#245b4b", width=1.8),
                                     name="Median SPI", hovertemplate="%{x|%b %Y}<br>SPI %{y:.2f}<extra></extra>"))
        dry = series["spi_median"] <= -1
        fig_spi.add_trace(go.Scatter(x=dates[dry], y=series.loc[dry, "spi_median"], mode="markers",
                                     marker=dict(color="#d18a35", size=6), name="SPI ≤ −1"))
        fig_spi.add_hline(y=-1, line_dash="dash", line_color="#d18a35")
        fig_spi.add_hline(y=0, line_color="#87948d")
        fig_spi.update_layout(height=380, xaxis_title="Waktu", yaxis_title="SPI",
                              plot_bgcolor="white", paper_bgcolor="white", legend_orientation="h")
        st.plotly_chart(fig_spi, use_container_width=True)

# ---------------------------------------------------------------------
# 3. Catatan interpretasi dan keterbatasan
st.divider()
st.header("3. Catatan interpretasi dan keterbatasan")
limitations = meta.get("catatan") or []
if limitations:
    for item in limitations:
        st.markdown(f"- {item}")
else:
    st.markdown(
        "- Hasil hanya menggunakan satu GCM dan satu skenario.\n"
        "- Proyeksi bukan ramalan kejadian cuaca pada tahun tertentu.\n"
        "- Ketidakpastian model dan skenario lain belum tercakup."
    )

st.markdown(
    f'<div class="warning-note"><b>Kesimpulan pembacaan:</b> hasil SPI merupakan keluaran lanjutan '
    f'dari downscaling {gcm}. Kinerja pada validasi ERA5 tidak otomatis menjamin transfer yang sama '
    f'pada prediktor GCM. Gunakan hasil sebagai gambaran sensitivitas bersyarat, bukan prediksi pasti '
    f'kekeringan di Banten.</div>',
    unsafe_allow_html=True,
)
st.caption(
    f"Sumber data: {target} (referensi hujan), ERA5 (prediktor untuk validasi), "
    f"{gcm} ({scenario}). Versi notebook: {meta.get('versi_notebook', '—')} · "
    f"tanggal pemrosesan: {meta.get('tanggal_run', '—')}."
)

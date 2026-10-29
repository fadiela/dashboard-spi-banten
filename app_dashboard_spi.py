"""Dashboard proyeksi SPI Banten 2026-2050 (membaca ekspor sel 14d dan 14e notebook). Grafik interaktif (Plotly): arahkan kursor untuk melihat nilai.
Jalankan:  HASIL_DIR=/jalur/ke/folder streamlit run app_dashboard_spi.py
Sumber Google Drive (opsional): atur DRIVE_FOLDER_ID (env atau Streamlit secrets) = ID folder Drive yang dibagikan 'siapa saja dengan link'.
Berkas: dashboard_tahunan_regional.csv, dashboard_tahunan_per_grid.csv, dashboard_meta.json (14d)
        dashboard_bulanan_regional.csv.gz, dashboard_bulanan_per_grid.csv.gz, dashboard_baseline_bulan_grid.csv.gz, dashboard_grid.csv (14e)
"""
import json, os
import numpy as np, pandas as pd, streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Proyeksi SPI Banten 2026-2050", layout="wide")
MON = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
PRESET = {"Semua bulan": list(range(1, 13)), "DJF (Des-Feb)": [12, 1, 2], "MAM (Mar-Mei)": [3, 4, 5], "JJA (Jun-Agu)": [6, 7, 8], "SON (Sep-Nov)": [9, 10, 11], "Pilih sendiri": None}
BIRU, BIRU_MUDA = "#1f77b4", "rgba(31,119,180,0.22)"

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
    try: return tuple(sorted((n, os.path.getmtime(os.path.join(folder, n))) for n in os.listdir(folder) if n.startswith("dashboard_")))
    except OSError: return ()

folder_awal, sumber = os.environ.get("HASIL_DIR", "."), "folder lokal / repo"
drive_id = ambil_drive_id()
if drive_id:
    try: folder_awal, sumber = sinkron_drive(drive_id), "Google Drive (disegarkan tiap 10 menit)"
    except Exception as e: st.sidebar.warning(f"Gagal mengambil dari Google Drive ({type(e).__name__}); memakai berkas lokal.")
folder = st.sidebar.text_input("Folder hasil (berisi dashboard_*.csv)", value=folder_awal)
st.sidebar.caption(f"Sumber data: {sumber}")
if st.sidebar.button("Muat ulang data sekarang"): st.cache_data.clear(); st.rerun()

@st.cache_data
def muat(folder, versi=()):
    reg = pd.read_csv(os.path.join(folder, "dashboard_tahunan_regional.csv"))
    grd = pd.read_csv(os.path.join(folder, "dashboard_tahunan_per_grid.csv"))
    meta = json.load(open(os.path.join(folder, "dashboard_meta.json"), encoding="utf-8"))
    return reg, grd, meta

@st.cache_data
def muat_bulanan(folder, versi=()):
    f = lambda n: os.path.join(folder, n)
    if not all(os.path.exists(f(n)) for n in ("dashboard_bulanan_regional.csv.gz", "dashboard_bulanan_per_grid.csv.gz", "dashboard_baseline_bulan_grid.csv.gz", "dashboard_grid.csv")): return None
    return (pd.read_csv(f("dashboard_bulanan_regional.csv.gz")), pd.read_csv(f("dashboard_bulanan_per_grid.csv.gz")),
            pd.read_csv(f("dashboard_baseline_bulan_grid.csv.gz")), pd.read_csv(f("dashboard_grid.csv")))

try:
    reg, grd, meta = muat(folder, versi_folder(folder))
except FileNotFoundError as e:
    st.error(f"Berkas ekspor tidak ditemukan di '{folder}'. Jalankan sel 14d notebook dulu. ({e.filename})"); st.stop()
bln = muat_bulanan(folder, versi_folder(folder))

# ---------------- pembantu grafik ----------------
def tampil(fig, tinggi=420):
    fig.update_layout(template="plotly_white", height=tinggi, margin=dict(l=10, r=10, t=50, b=10), legend=dict(orientation="h", y=-0.18, x=0))
    try: st.plotly_chart(fig, width="stretch")
    except TypeError: st.plotly_chart(fig, use_container_width=True)

def garis_acuan(fig, x, nilai, nama, warna, dash):
    fig.add_trace(go.Scatter(x=[min(x), max(x)], y=[nilai, nilai], mode="lines", name=nama, line=dict(color=warna, dash=dash, width=1.5), hovertemplate=f"{nama}: {nilai:.1f}%<extra></extra>"))

def peta(df, kol, judul, warna, zmin, zmax, satuan, label, extra=(), zmid=None):
    """Peta grid interaktif. extra = [(judul, kolom, satuan), ...] ditampilkan di tooltip."""
    lon, lat = df["lon"].round(4).to_numpy(), df["lat"].round(4).to_numpy(); xs, ys = np.unique(lon), np.unique(lat)
    tip = "Bujur %{x:.3f}, Lintang %{y:.3f}<br><b>" + label + ": %{z:.1f}" + satuan + "</b>"
    if len(xs) * len(ys) <= 6 * len(df):                                           # grid teratur -> kotak per sel
        ix, iy = np.searchsorted(xs, lon), np.searchsorted(ys, lat)
        def mat(k): m = np.full((len(ys), len(xs)), np.nan); m[iy, ix] = df[k].to_numpy(); return m
        cd = np.dstack([mat(k) for _, k, _ in extra]) if extra else None
        for i, (jd, _, sat) in enumerate(extra): tip += f"<br>{jd}: %{{customdata[{i}]:.1f}}{sat}"
        tr = go.Heatmap(x=xs, y=ys, z=mat(kol), customdata=cd, colorscale=warna, zmin=zmin, zmax=zmax, zmid=zmid, hoverongaps=False, hovertemplate=tip + "<extra></extra>", colorbar=dict(title=satuan.strip() or None))
    else:                                                                          # cadangan bila grid tidak teratur
        cd = df[[k for _, k, _ in extra]].to_numpy() if extra else None
        for i, (jd, _, sat) in enumerate(extra): tip += f"<br>{jd}: %{{customdata[{i}]:.1f}}{sat}"
        tr = go.Scatter(x=lon, y=lat, mode="markers", customdata=cd, marker=dict(symbol="square", size=10, color=df[kol], colorscale=warna, cmin=zmin, cmax=zmax, cmid=zmid, colorbar=dict(title=satuan.strip() or None)),
                        hovertemplate=tip.replace("%{z", "%{marker.color") + "<extra></extra>")
    fig = go.Figure(tr); fig.update_layout(title=dict(text=judul, font=dict(size=13)), xaxis_title="bujur", yaxis_title="lintang"); fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig

# ---------------- kepala halaman ----------------
st.title(f"Proyeksi kekeringan SPI Banten {meta['horizon'][0]}-{meta['horizon'][1]}")
st.caption(f"{meta['gcm']} | {meta['skenario']} | target {meta['target']} | model: {meta['model']} (set {meta['set_fitur']}) | {meta['n_anggota_ensemble']} anggota ensemble")
if not str(meta["status_gerbang"]).startswith("lolos"):
    st.warning(f"Status model: **{meta['status_gerbang']}**. Model ini belum lolos gerbang penuh; baca sebagai proyeksi bersyarat, bukan hasil terverifikasi.")
st.info(meta["catatan"][1])

skala = st.sidebar.radio("Skala SPI", meta["spi_skala"], index=0)
r = reg[reg["SPI"] == skala].sort_values("tahun"); base = float(meta["baseline_model_sendiri_pct"][skala]); acuan = float(meta["acuan_target_pct"][skala])
tab1, tab2, tab_b, tab3 = st.tabs(["Wilayah per tahun", "Peta tahunan", "Bulanan & agregasi", "Cara membaca"])

# ---------------- tab 1: wilayah per tahun ----------------
with tab1:
    st.caption("Ringkasan seluruh Banten per tahun: berapa persen grid-bulan yang kering (SPI <= -1), dengan pita sebaran antar-anggota ensemble.")
    c1, c2, c3 = st.columns(3); rata = float(r["kering_pct_median"].mean())
    c1.metric("Bulan kering rata-rata (median anggota)", f"{rata:.1f}%", f"{rata - base:+.1f} pp vs baseline model sendiri", delta_color="off")
    c2.metric("Baseline model sendiri 1981-2010", f"{base:.1f}%"); c3.metric(f"Acuan {meta['target']} 1981-2010", f"{acuan:.1f}%")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=r["tahun"], y=r["kering_pct_p10"], mode="lines", line=dict(width=0), name="p10", showlegend=False, hovertemplate="p10: %{y:.1f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=r["tahun"], y=r["kering_pct_p90"], mode="lines", line=dict(width=0), fill="tonexty", fillcolor=BIRU_MUDA, name="p10-p90 antar-anggota", hovertemplate="p90: %{y:.1f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=r["tahun"], y=r["kering_pct_median"], mode="lines+markers", line=dict(color=BIRU, width=2.5), marker=dict(size=5), name="median", hovertemplate="<b>median: %{y:.1f}%</b><extra></extra>"))
    garis_acuan(fig, r["tahun"], base, "baseline model sendiri 1981-2010", "gray", "dot"); garis_acuan(fig, r["tahun"], acuan, f"acuan {meta['target']} 1981-2010", "black", "dash")
    fig.update_layout(title=f"{skala}: frekuensi kekeringan per tahun", hovermode="x unified", xaxis_title="tahun", yaxis_title="% grid-bulan SPI <= -1")
    tampil(fig)
    st.caption("Satu tahun = satu realisasi variabilitas GCM, bukan ramalan tahun itu. Pita hanya menggambarkan sebaran dalam satu model.")
    if (r["n_bulan_valid"] < 12).any():
        st.caption("Tahun awal punya bulan SPI kosong: " + ", ".join(f"{int(t)} ({int(n)} bulan valid)" for t, n in r.loc[r['n_bulan_valid'] < 12, ['tahun', 'n_bulan_valid']].to_numpy()))

# ---------------- tab 2: peta tahunan ----------------
ETIKET = {"spi_rata2": "SPI rata-rata tahunan", "kering_pct": "% bulan kering", "spi_des": "SPI Desember"}
with tab2:
    st.caption("Peta per grid untuk satu tahun: lihat sebaran spasial kekeringan di Banten.")
    cA, cB = st.columns([1, 2])
    tahun = cA.selectbox("Tahun", sorted(grd["tahun"].unique().tolist()), key="tahun_peta")
    besaran = cB.radio("Besaran", ["spi_rata2", "kering_pct", "spi_des"], horizontal=True, format_func=lambda v: ETIKET.get(v, v))
    g = grd[(grd["SPI"] == skala) & (grd["tahun"] == tahun)].dropna(subset=[besaran])
    if g.empty: st.warning("Tidak ada nilai untuk pilihan ini (mis. SPI Desember pada skala yang belum terisi).")
    elif besaran == "kering_pct": tampil(peta(g, besaran, f"{skala}, {tahun}: % bulan kering (median anggota)", "YlOrBr", 0, 100, "%", ETIKET[besaran]), 520)
    else: tampil(peta(g, besaran, f"{skala}, {tahun}: {ETIKET[besaran]} (median anggota)", "BrBG", -2, 2, "", ETIKET[besaran], zmid=0), 520)

# ---------------- tab 3: bulanan & agregasi ----------------
with tab_b:
    st.caption("Pilih tahun dan bulan yang ingin digabung, lalu lihat frekuensi kering yang diharapkan di peta, per tahun, per bulan kalender, dan sebagai deret bulanan.")
    if bln is None:
        st.info("Ekspor bulanan belum ada. Jalankan sel 14e notebook (menghasilkan dashboard_bulanan_*.csv.gz, dashboard_baseline_bulan_grid.csv.gz, dashboard_grid.csv).")
    else:
        regm, grdm, basem, grid = bln
        regm, grdm, basem = (d[d["SPI"] == skala] for d in (regm, grdm, basem))
        daftar_th = sorted(regm["tahun"].unique().tolist())
        k1, k2 = st.columns([1, 2])
        mode_th = k1.radio("Pilih tahun", ["Rentang (dari - sampai)", "Tahun tertentu"], horizontal=True, key="mode_th")
        if mode_th.startswith("Rentang"):
            ca, cb = k1.columns(2)
            th0 = ca.selectbox("Dari", daftar_th, index=0, key="th_dari"); th1 = cb.selectbox("Sampai", daftar_th, index=len(daftar_th) - 1, key="th_sampai")
            tahun_pilih = [t for t in daftar_th if th0 <= t <= th1]
        else:
            tahun_pilih = sorted(k1.multiselect("Tahun", daftar_th, default=daftar_th[:5], key="th_multi"))
        pilih = k2.radio("Bulan", list(PRESET), horizontal=True)
        bulan = PRESET[pilih] if PRESET[pilih] is not None else [MON.index(m) + 1 for m in k2.multiselect("Pilih bulan", MON, default=MON[5:9])]
        if not bulan: st.warning("Pilih minimal satu bulan.")
        elif not tahun_pilih: st.warning("Pilih minimal satu tahun (untuk rentang: 'Sampai' tidak boleh lebih awal dari 'Dari').")
        else:
            sel = lambda d: d[d["tahun"].isin(tahun_pilih) & d["bulan"].isin(bulan)]
            gs = sel(grdm)
            etiket_th = f"{tahun_pilih[0]}-{tahun_pilih[-1]}" if tahun_pilih[-1] - tahun_pilih[0] + 1 == len(tahun_pilih) else f"{len(tahun_pilih)} tahun terpilih ({tahun_pilih[0]}...{tahun_pilih[-1]})"
            etiket_bl = pilih if pilih != "Pilih sendiri" else ", ".join(MON[b - 1] for b in bulan)
            if gs.empty:
                st.warning("Tidak ada data untuk pilihan ini (mis. SPI-12 belum terisi pada bulan awal 2026).")
            else:
                agg = gs.groupby("grid_id").agg(p_kering=("p_kering", "mean"), p_sangat=("p_sangat_kering", "mean"), spi=("spi_median", "mean")).reset_index(); agg[["p_kering", "p_sangat"]] *= 100
                bs = basem[basem["bulan"].isin(bulan)].groupby("grid_id")[["kering_model_pct", "kering_target_pct"]].mean().reset_index()
                agg = agg.merge(bs, on="grid_id").merge(grid, on="grid_id"); agg["selisih_pp"] = agg["p_kering"] - agg["kering_model_pct"]
                st.caption(f"{len(bulan)} bulan x {len(tahun_pilih)} tahun = sampai {int(gs.groupby('grid_id').size().max())} bulan per grid yang digabung (hanya bulan dengan SPI terisi).")
                m1, m2, m3, m4 = st.columns(4); fk, fb, ft = agg["p_kering"].mean(), agg["kering_model_pct"].mean(), agg["kering_target_pct"].mean()
                m1.metric("Frekuensi kering yang diharapkan", f"{fk:.1f}%", f"{fk - fb:+.1f} pp vs baseline model sendiri", delta_color="off")
                m2.metric("Baseline model sendiri (bulan sama, 1981-2010)", f"{fb:.1f}%"); m3.metric(f"Baseline {meta['target']} (bulan sama)", f"{ft:.1f}%"); m4.metric("Sangat kering (SPI <= -1,5)", f"{agg['p_sangat'].mean():.1f}%")
                ket = st.radio("Besaran peta", ["Frekuensi kering (%)", "Selisih vs baseline model sendiri (pp)", "SPI median rata-rata"], horizontal=True)
                ekstra = [("Baseline model sendiri", "kering_model_pct", "%"), (f"Baseline {meta['target']}", "kering_target_pct", "%"), ("Sangat kering", "p_sangat", "%")]
                jd = f"{skala} | {ket} | {etiket_th}, {etiket_bl}"
                cA, cB = st.columns(2)
                with cA:
                    if ket.startswith("Frekuensi"): tampil(peta(agg, "p_kering", jd, "YlOrBr", 0, 40, "%", "Frekuensi kering", ekstra), 460)
                    elif ket.startswith("Selisih"): tampil(peta(agg, "selisih_pp", jd, "RdBu_r", -15, 15, " pp", "Selisih vs baseline", ekstra, zmid=0), 460)
                    else: tampil(peta(agg, "spi", jd, "BrBG", -1, 1, "", "SPI median", ekstra, zmid=0), 460)
                with cB:
                    per_th = gs.groupby("tahun")["p_kering"].mean() * 100
                    fig = go.Figure(go.Bar(x=per_th.index, y=per_th.values, marker_color=BIRU, name="frekuensi kering yang diharapkan", hovertemplate="Tahun %{x}<br><b>%{y:.1f}%</b> bulan kering<extra></extra>"))
                    garis_acuan(fig, list(per_th.index), fb, "baseline model sendiri (bulan sama)", "gray", "dot"); garis_acuan(fig, list(per_th.index), ft, f"baseline {meta['target']}", "black", "dash")
                    fig.update_layout(title="Per tahun, bulan terpilih (rata-rata wilayah)", xaxis_title="tahun", yaxis_title="% bulan kering", hovermode="x unified"); tampil(fig, 460)
                # profil bulan kalender (tahun terpilih, semua bulan; bulan terpilih diberi warna)
                gt = grdm[grdm["tahun"].isin(tahun_pilih)]; prof = gt.groupby("bulan")["p_kering"].mean() * 100; bb = basem.groupby("bulan")[["kering_model_pct", "kering_target_pct"]].mean()
                fig = go.Figure(go.Bar(x=[MON[b - 1] for b in prof.index], y=prof.values, marker_color=[BIRU if b in bulan else "lightgray" for b in prof.index], name="proyeksi (tahun terpilih)", hovertemplate="%{x}<br><b>%{y:.1f}%</b> bulan kering<extra></extra>"))
                fig.add_trace(go.Scatter(x=[MON[b - 1] for b in bb.index], y=bb["kering_model_pct"], mode="lines+markers", line=dict(color="gray", dash="dot"), name="baseline model sendiri 1981-2010", hovertemplate="%{x}: %{y:.1f}%<extra>baseline model</extra>"))
                fig.add_trace(go.Scatter(x=[MON[b - 1] for b in bb.index], y=bb["kering_target_pct"], mode="lines+markers", line=dict(color="black", dash="dash"), name=f"baseline {meta['target']} 1981-2010", hovertemplate="%{x}: %{y:.1f}%<extra>baseline target</extra>"))
                fig.update_layout(title="Profil per bulan kalender (bulan terpilih berwarna biru)", xaxis_title="bulan", yaxis_title="% bulan kering", hovermode="x unified"); tampil(fig, 360)
                # deret bulanan wilayah
                rt = regm.sort_values(["tahun", "bulan"]).reset_index(drop=True); thn = rt["tahun"].isin(tahun_pilih).to_numpy(); ok = rt["bulan"].isin(bulan).to_numpy() & thn
                tgl = pd.to_datetime(dict(year=rt["tahun"], month=rt["bulan"], day=1)); sub = rt[ok]
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=tgl, y=rt["spi_median"].where(thn), mode="lines", line=dict(color="lightgray", width=1), name="semua bulan (tahun terpilih)", hovertemplate="%{x|%b %Y}: %{y:.2f}<extra></extra>"))
                fig.add_trace(go.Scatter(x=tgl[ok], y=sub["spi_median"], mode="markers", marker=dict(color=BIRU, size=6), name="median (bulan terpilih)",
                                         error_y=dict(type="data", symmetric=False, array=(sub["spi_p90"] - sub["spi_median"]).to_numpy(), arrayminus=(sub["spi_median"] - sub["spi_p10"]).to_numpy(), color="rgba(31,119,180,0.35)", thickness=1, width=0),
                                         customdata=np.c_[sub["spi_p10"], sub["spi_p90"]], hovertemplate="%{x|%b %Y}<br><b>median %{y:.2f}</b><br>p10 %{customdata[0]:.2f} | p90 %{customdata[1]:.2f}<extra></extra>"))
                fig.add_hline(y=-1, line_dash="dash", line_color="#d62728", annotation_text="ambang kering (-1)", annotation_position="bottom right"); fig.add_hline(y=0, line_color="black", line_width=0.6)
                fig.update_layout(title=f"Deret SPI bulanan wilayah ({skala}, median anggota; garis tegak = p10-p90)", yaxis_title=f"{skala} rata-rata wilayah", hovermode="closest"); tampil(fig, 380)
                st.caption("Makin banyak tahun dan bulan yang digabung, makin bermakna. Satu bulan atau satu tahun hanyalah satu realisasi GCM, bukan ramalan.")

# ---------------- tab 4: cara membaca ----------------
with tab3:
    st.subheader("Fungsi tiap tab")
    st.markdown("- **Wilayah per tahun:** gambaran seluruh Banten per tahun (frekuensi kering dengan pita antar-anggota), dibandingkan dengan baseline model dan acuan CHIRPS.\n"
                "- **Peta tahunan:** sebaran spasial per grid untuk satu tahun (SPI rata-rata, % bulan kering, atau SPI Desember).\n"
                "- **Bulanan & agregasi:** pilih rentang atau tahun tertentu dan bulan tertentu (musim), lalu lihat frekuensi kering yang diharapkan di peta, per tahun, per bulan kalender, dan deret bulanan.\n"
                "- **Cara membaca:** catatan wajib, status gerbang model, dan persen prediktor GCM di luar rentang latih.")
    st.subheader("Catatan wajib")
    for c in meta["catatan"]: st.write("- " + c)
    st.subheader("Gerbang model prediktor")
    st.dataframe(pd.DataFrame(meta["gerbang"]).T.rename(columns={"a": "(a) skill sefase > 0", "b": "(b) distribusi <= 1,10 x klimatologi", "c": "(c) selisih kering <= 3 pp"}))
    st.subheader("Baris prediktor GCM di luar rentang ERA5 (dipotong)")
    st.dataframe(pd.Series(meta["baris_prediktor_luar_rentang_pct"], name="% baris").to_frame())

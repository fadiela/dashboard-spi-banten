"""Dashboard proyeksi SPI Banten 2026-2050 (membaca ekspor sel 14d dan 14e notebook v13).
Jalankan:  HASIL_DIR=/jalur/ke/folder streamlit run app_dashboard_spi.py
Sumber Google Drive (opsional): atur DRIVE_FOLDER_ID (env atau Streamlit secrets) = ID folder Drive yang dibagikan 'siapa saja dengan link'.
Berkas: dashboard_tahunan_regional.csv, dashboard_tahunan_per_grid.csv, dashboard_meta.json (14d)
        dashboard_bulanan_regional.csv.gz, dashboard_bulanan_per_grid.csv.gz, dashboard_baseline_bulan_grid.csv.gz, dashboard_grid.csv (14e)
"""
import json, os
import numpy as np, pandas as pd, streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="Proyeksi SPI Banten 2026-2050", layout="wide")
def ambil_drive_id():
    """ID folder Google Drive dari variabel lingkungan DRIVE_FOLDER_ID atau Streamlit secrets; None bila tidak diatur."""
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
    """Tanda versi data (nama + waktu ubah berkas dashboard_*) supaya cache ikut segar saat berkas berganti."""
    try: return tuple(sorted((n, os.path.getmtime(os.path.join(folder, n))) for n in os.listdir(folder) if n.startswith("dashboard_")))
    except OSError: return ()

folder_awal, sumber = os.environ.get("HASIL_DIR", "."), "folder lokal"
drive_id = ambil_drive_id()
if drive_id:
    try: folder_awal, sumber = sinkron_drive(drive_id), "Google Drive (disegarkan tiap 10 menit)"
    except Exception as e: st.sidebar.warning(f"Gagal mengambil dari Google Drive ({type(e).__name__}); memakai berkas lokal.")
folder = st.sidebar.text_input("Folder hasil (berisi dashboard_*.csv)", value=folder_awal)
st.sidebar.caption(f"Sumber data: {sumber}")
if st.sidebar.button("Muat ulang data sekarang"): st.cache_data.clear(); st.rerun()
MON = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
PRESET = {"Semua bulan": list(range(1, 13)), "DJF (Des-Feb)": [12, 1, 2], "MAM (Mar-Mei)": [3, 4, 5], "JJA (Jun-Agu)": [6, 7, 8], "SON (Sep-Nov)": [9, 10, 11], "Pilih sendiri": None}

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

st.title(f"Proyeksi kekeringan SPI Banten {meta['horizon'][0]}-{meta['horizon'][1]}")
st.caption(f"{meta['gcm']} | {meta['skenario']} | target {meta['target']} | model: {meta['model']} (set {meta['set_fitur']}) | {meta['n_anggota_ensemble']} anggota ensemble")
if not str(meta["status_gerbang"]).startswith("lolos"):
    st.warning(f"Status model: **{meta['status_gerbang']}**. Model ini belum lolos gerbang penuh; baca sebagai proyeksi bersyarat, bukan hasil terverifikasi.")
st.info(meta["catatan"][1])

skala = st.sidebar.radio("Skala SPI", meta["spi_skala"], index=0)
r = reg[reg["SPI"] == skala].sort_values("tahun"); base = float(meta["baseline_model_sendiri_pct"][skala]); acuan = float(meta["acuan_target_pct"][skala])

tab1, tab2, tab_b, tab3 = st.tabs(["Wilayah per tahun", "Peta tahunan", "Bulanan & agregasi", "Cara membaca"])
with tab1:
    c1, c2, c3 = st.columns(3)
    rata = float(r["kering_pct_median"].mean())
    c1.metric("Bulan kering rata-rata (median anggota)", f"{rata:.1f}%", f"{rata - base:+.1f} pp vs baseline model sendiri", delta_color="off")
    c2.metric("Baseline model sendiri 1981-2010", f"{base:.1f}%")
    c3.metric(f"Acuan {meta['target']} 1981-2010", f"{acuan:.1f}%")
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.fill_between(r["tahun"], r["kering_pct_p10"], r["kering_pct_p90"], alpha=0.25, label="p10-p90 antar-anggota ensemble")
    ax.plot(r["tahun"], r["kering_pct_median"], lw=2, label="median")
    ax.axhline(base, color="gray", ls=":", label="baseline model sendiri 1981-2010"); ax.axhline(acuan, color="k", ls="--", lw=1, label=f"acuan {meta['target']} 1981-2010")
    ax.set_xlabel("tahun"); ax.set_ylabel("% grid-bulan SPI <= -1"); ax.set_title(f"{skala}: frekuensi kekeringan per tahun"); ax.legend(fontsize=8); ax.grid(alpha=0.3)
    st.pyplot(fig)
    st.caption("Satu tahun = satu realisasi variabilitas GCM, bukan ramalan tahun itu. Pita hanya menggambarkan sebaran dalam satu model.")
    if (r["n_bulan_valid"] < 12).any():
        st.caption("Tahun awal punya bulan SPI kosong: " + ", ".join(f"{int(t)} ({int(n)} bulan valid)" for t, n in r.loc[r['n_bulan_valid'] < 12, ['tahun', 'n_bulan_valid']].to_numpy()))
ETIKET = {"spi_rata2": "SPI rata-rata tahunan", "kering_pct": "% bulan kering", "spi_des": "SPI Desember"}
with tab2:
    tahun = st.selectbox("Tahun", sorted(grd["tahun"].unique().tolist()), key="tahun_peta")
    besaran = st.radio("Besaran", ["spi_rata2", "kering_pct", "spi_des"], horizontal=True, format_func=lambda v: ETIKET.get(v, v))
    g = grd[(grd["SPI"] == skala) & (grd["tahun"] == tahun)]
    fig, ax = plt.subplots(figsize=(7, 5.2))
    if besaran == "kering_pct": sc = ax.scatter(g["lon"], g["lat"], c=g[besaran], cmap="YlOrBr", marker="s", s=28, vmin=0, vmax=100)
    else: sc = ax.scatter(g["lon"], g["lat"], c=g[besaran], cmap="BrBG", marker="s", s=28, vmin=-2, vmax=2)
    plt.colorbar(sc, ax=ax, shrink=0.85); ax.set_xlabel("bujur"); ax.set_ylabel("lintang"); ax.set_title(f"{skala}, {tahun} (median anggota ensemble)"); ax.set_aspect("equal")
    st.pyplot(fig)

with tab_b:
    if bln is None:
        st.info("Ekspor bulanan belum ada. Jalankan sel 14e notebook v13 (menghasilkan dashboard_bulanan_*.csv.gz, dashboard_baseline_bulan_grid.csv.gz, dashboard_grid.csv).")
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
        bulan = PRESET[pilih] if PRESET[pilih] is not None else [MON.index(m) + 1 for m in st.multiselect("Pilih bulan", MON, default=MON[5:9])]
        if not bulan:
            st.warning("Pilih minimal satu bulan.")
        elif not tahun_pilih:
            st.warning("Pilih minimal satu tahun (untuk rentang: 'Sampai' tidak boleh lebih awal dari 'Dari').")
        else:
            sel = lambda d: d[d["tahun"].isin(tahun_pilih) & d["bulan"].isin(bulan)]
            gs = sel(grdm)
            etiket_th = f"{tahun_pilih[0]}-{tahun_pilih[-1]}" if tahun_pilih[-1] - tahun_pilih[0] + 1 == len(tahun_pilih) else f"{len(tahun_pilih)} tahun terpilih ({tahun_pilih[0]}...{tahun_pilih[-1]})"
            if gs.empty:
                st.warning("Tidak ada data untuk pilihan ini (mis. SPI-12 belum terisi pada bulan awal 2026).")
            else:
                agg = gs.groupby("grid_id").agg(p_kering=("p_kering", "mean"), p_sangat=("p_sangat_kering", "mean"), spi=("spi_median", "mean")).reset_index()
                agg[["p_kering", "p_sangat"]] *= 100
                bs = basem[basem["bulan"].isin(bulan)].groupby("grid_id")[["kering_model_pct", "kering_target_pct"]].mean().reset_index()
                agg = agg.merge(bs, on="grid_id").merge(grid, on="grid_id"); agg["selisih_pp"] = agg["p_kering"] - agg["kering_model_pct"]
                n_bt = gs.groupby("grid_id").size().max()
                st.caption(f"{len(bulan)} bulan x {len(tahun_pilih)} tahun = sampai {int(n_bt)} bulan per grid yang digabung (hanya bulan dengan SPI terisi).")
                m1, m2, m3, m4 = st.columns(4)
                fk, fb, ft = agg["p_kering"].mean(), agg["kering_model_pct"].mean(), agg["kering_target_pct"].mean()
                m1.metric("Frekuensi kering yang diharapkan", f"{fk:.1f}%", f"{fk - fb:+.1f} pp vs baseline model sendiri", delta_color="off")
                m2.metric("Baseline model sendiri (bulan sama, 1981-2010)", f"{fb:.1f}%"); m3.metric(f"Baseline {meta['target']} (bulan sama)", f"{ft:.1f}%")
                m4.metric("Sangat kering (SPI <= -1,5)", f"{agg['p_sangat'].mean():.1f}%")
                ket = st.radio("Besaran peta", ["Frekuensi kering (%)", "Selisih vs baseline model sendiri (pp)", "SPI median rata-rata"], horizontal=True)
                kol, cmap, lim = {"Frekuensi kering (%)": ("p_kering", "YlOrBr", (0, 40)), "Selisih vs baseline model sendiri (pp)": ("selisih_pp", "BrBG_r", (-15, 15)), "SPI median rata-rata": ("spi", "BrBG", (-1, 1))}[ket]
                cA, cB = st.columns(2)
                fig, ax = plt.subplots(figsize=(6, 4.8)); sc = ax.scatter(agg["lon"], agg["lat"], c=agg[kol], cmap=cmap, marker="s", s=26, vmin=lim[0], vmax=lim[1])
                plt.colorbar(sc, ax=ax, shrink=0.85); ax.set_aspect("equal"); ax.set_xlabel("bujur"); ax.set_ylabel("lintang"); ax.set_title(f"{skala} | {ket}\n{etiket_th}, {pilih if pilih != 'Pilih sendiri' else ', '.join(MON[b - 1] for b in bulan)}", fontsize=9)
                cA.pyplot(fig)
                per_th = gs.groupby("tahun")["p_kering"].mean() * 100
                fig, ax = plt.subplots(figsize=(6, 4.8)); ax.bar(per_th.index, per_th.values, color="tab:blue", alpha=0.8)
                ax.axhline(fb, color="gray", ls=":", label="baseline model sendiri (bulan sama)"); ax.axhline(ft, color="k", ls="--", lw=1, label=f"baseline {meta['target']}")
                ax.set_xlabel("tahun"); ax.set_ylabel("frekuensi kering yang diharapkan (%)"); ax.set_title("Per tahun, bulan terpilih (rata-rata wilayah)", fontsize=9); ax.legend(fontsize=7); ax.grid(alpha=0.3)
                cB.pyplot(fig)
                rt = regm.sort_values(["tahun", "bulan"]).reset_index(drop=True); thn = rt["tahun"].isin(tahun_pilih).to_numpy()
                x = rt["tahun"] + (rt["bulan"] - 1) / 12; ok = rt["bulan"].isin(bulan).to_numpy() & thn
                fig, ax = plt.subplots(figsize=(12, 3.6)); ax.plot(x, rt["spi_median"].where(thn), color="lightgray", lw=0.8, label="semua bulan (tahun terpilih)")
                ax.fill_between(x, rt["spi_p10"], rt["spi_p90"], where=ok, alpha=0.3, label="p10-p90 antar-anggota (bulan terpilih)")
                ax.scatter(x[ok], rt.loc[ok, "spi_median"], s=10, color="tab:blue", label="median (bulan terpilih)"); ax.axhline(-1, color="tab:red", ls="--", lw=0.8); ax.axhline(0, color="k", lw=0.5)
                ax.set_ylabel(f"{skala} rata-rata wilayah"); ax.set_title("Deret SPI bulanan wilayah (median anggota); garis merah = ambang kering", fontsize=9); ax.legend(fontsize=7, ncol=3); ax.grid(alpha=0.3)
                st.pyplot(fig)
                st.caption("Makin banyak tahun dan bulan yang digabung, makin bermakna. Satu bulan atau satu tahun hanyalah satu realisasi GCM, bukan ramalan.")
with tab3:
    st.subheader("Catatan wajib")
    for c in meta["catatan"]: st.write("- " + c)
    st.subheader("Gerbang model prediktor")
    st.dataframe(pd.DataFrame(meta["gerbang"]).T.rename(columns={"a": "(a) skill sefase > 0", "b": "(b) distribusi <= 1,10 x klimatologi", "c": "(c) selisih kering <= 3 pp"}))
    st.subheader("Baris prediktor GCM di luar rentang ERA5 (dipotong)")
    st.dataframe(pd.Series(meta["baris_prediktor_luar_rentang_pct"], name="% baris").to_frame())

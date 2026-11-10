"""Dashboard satu layar: proyeksi bulan kering Banten 2026-2050 (gaya Tableau).
Jalankan:  streamlit run app_dashboard_spi.py
Halaman catatan (penjelasan untuk pemahaman sendiri, tidak untuk ditampilkan):  tambahkan ?catatan=1 di alamat.
Berkas data (hasil ekspor notebook 14d-14i) harus ada di folder yang sama, atau tunjuk lewat variabel lingkungan HASIL_DIR.
"""
import json, os
import numpy as np, pandas as pd, streamlit as st
import plotly.graph_objects as go
import streamlit.components.v1 as components

# ------------------------------------------------------------------ pengaturan yang boleh diubah
PEMBUAT = "Gemala Aleida Fitri · Statistika dan Sains Data, IPB University"   # kosongkan bila tak perlu
JUDUL_PROYEK = "Downscaling GCM Hujan untuk Proyeksi Kekeringan (SPI) di Banten 2026-2050"   # ganti dengan judul proyekmu; ukuran huruf mengecil otomatis bila panjang
H_KPI = 124                         # tinggi blok kartu angka + baris insight (px); blok ini iframe berukuran tetap sehingga tidak bisa menimpa elemen lain
H_KECIL = 150                       # tinggi tiap grafik kecil (px), diset untuk layar 1366x768 (layar besar: mis. 205)
H_PETA = 2 * H_KECIL + 45           # tinggi peta, otomatis sejajar dengan dua grafik kecil di kanan
UKURAN_TEKS = 14                    # px dasar seluruh tampilan (Streamlit memakai rem). Teks terlalu kecil/besar: ubah angka ini (13-16)
st.set_page_config(page_title="Bulan kering Banten 2026-2050", page_icon="🌧️", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
html {font-size: __UT__px;}
.stApp {background:#f3f5f8;}
header[data-testid="stHeader"], footer, #MainMenu, [data-testid="stToolbar"] {display:none !important;}
.block-container {padding:.45rem .8rem .2rem; max-width:100%;}
[data-testid="stVerticalBlock"] {gap:.3rem;}
div[data-baseweb="select"] > div {min-height:30px;}
.ttl {font-size:1.3rem; font-weight:700; color:#1d2b3a; line-height:1.15; white-space:nowrap;}
.sub {font-size:.72rem; color:#6b7785; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
[data-testid="stWidgetLabel"] {min-height:0; margin-bottom:0;}
[data-testid="stWidgetLabel"] p {font-size:.65rem !important; font-weight:700; color:#6b7785; text-transform:uppercase; letter-spacing:.04em; margin:0 !important;}
.tile, .insrow, .ttl, .sub, .foot {margin-bottom:0 !important;}
.ph {font-size:.72rem; font-weight:700; color:#55606e; text-transform:uppercase; letter-spacing:.04em; margin:0 0 .15rem !important; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.tile {background:#fff; border:1px solid #e1e5ea; border-top:3px solid var(--c); border-radius:7px; padding:4px 9px 5px; min-height:80px; overflow:hidden;}
.tile .k {font-size:.68rem; font-weight:700; color:#6b7785; text-transform:uppercase; letter-spacing:.04em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.tile .v {font-size:1.7rem; font-weight:700; color:#1d2b3a; line-height:1.15; white-space:nowrap;}
.tile .v small {font-size:.72rem; font-weight:500; color:#6b7785;}
.tile .s {font-size:.72rem; color:#6b7785; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.chip {display:inline-block; padding:0 8px; border-radius:9px; font-size:.68rem; font-weight:700; color:#fff; margin-top:2px; white-space:nowrap;}
.red {background:#d1495b;} .blue {background:#2a6f97;} .gray {background:#8d99a6;} .amber {background:#e0912b;} .green {background:#2a9d8f;}
.dot {display:inline-block; width:10px; height:10px; border-radius:50%; margin:3px 4px 0 0; background:#d9dee4;}
.dot.ok {background:#2a9d8f;} .dot.no {background:#e0912b;}
.kpi {display:grid; grid-template-columns:repeat(5, minmax(0, 1fr)); gap:.5rem;}
.insrow {white-space:nowrap; overflow:hidden; margin-top:.45rem;}
.ins {display:inline-block; font-size:.78rem; color:#33404d; background:#fff; border:1px solid #e1e5ea; border-radius:12px; padding:1px 9px 1px 7px; margin:0 5px 0 0;}
.ins i {display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:5px;}
.foot {font-size:.68rem; color:#8794a3; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
</style>""".replace("__UT__", str(UKURAN_TEKS)), unsafe_allow_html=True)

PROY, BASE, ABU = "#2f6f8f", "#e8833a", "#b9c2cc"
WARNA_CHIP = {"red": "#d1495b", "blue": "#2a6f97", "gray": "#8d99a6", "amber": "#e0912b", "green": "#2a9d8f"}
KERING = [[0, "#fff5e0"], [0.35, "#fdd49e"], [0.7, "#f08a4b"], [1, "#a8281a"]]
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
PRESET = {"Sepanjang tahun": list(range(1, 13)), "Des-Feb": [12, 1, 2], "Mar-Mei": [3, 4, 5], "Jun-Agu": [6, 7, 8], "Sep-Nov": [9, 10, 11]}
NAMA_SKALA = {"SPI-3": "3 bln", "SPI-6": "6 bln", "SPI-12": "12 bln"}
ML = ["GLM Gamma", "Random Forest", "XGBoost", "Neural Net"]

# ------------------------------------------------------------------ data
FOLDER = os.environ.get("HASIL_DIR") or os.path.dirname(os.path.abspath(__file__))


def jalur(nama):
    p, alt = os.path.join(FOLDER, nama), os.path.join(FOLDER, nama.replace(".csv.gz", "_csv.gz"))
    return p if os.path.exists(p) or not os.path.exists(alt) else alt


@st.cache_resource
def muat(ver):
    d = {"meta": json.load(open(jalur("dashboard_meta.json"), encoding="utf-8"))}
    for k, nm in [("b_grid", "dashboard_bulanan_per_grid.csv.gz"), ("b_base", "dashboard_baseline_bulan_grid.csv.gz"), ("grid", "dashboard_grid.csv"),
                  ("banding", "dashboard_model_banding.csv"), ("gerb", "dashboard_model_gerbang.csv")]:
        d[k] = pd.read_csv(jalur(nm)) if os.path.exists(jalur(nm)) else None
    d["gj"] = json.load(open(jalur("banten_kabkota.geojson"), encoding="utf-8")) if os.path.exists(jalur("banten_kabkota.geojson")) else None
    return d


try: D = muat(tuple(sorted((f, os.path.getmtime(os.path.join(FOLDER, f))) for f in os.listdir(FOLDER) if f.startswith("dashboard_") or f.endswith(".geojson"))))
except FileNotFoundError as e: st.error(f"Berkas data tidak ditemukan: {e.filename}"); st.stop()
meta, gj = D["meta"], D["gj"]
H0, H1 = int(meta["horizon"][0]), int(meta["horizon"][1])
if D["b_grid"] is None or D["b_base"] is None or D["grid"] is None: st.error("Berkas ekspor bulanan/per-grid (sel 14e) belum ada."); st.stop()


def n(x, d=1, plus=False):
    s = f"{x:+.{d}f}" if plus else f"{x:.{d}f}"
    return s.replace(".", ",")


def se_kasar(v):
    v = pd.Series(v).dropna()
    return float(v.std(ddof=1) / np.sqrt(len(v))) if len(v) >= 3 else float("nan")


def tafsir(sel, se):
    if not np.isfinite(se): return "sedikit"
    return "sama" if abs(sel) < 2 * se else ("lebih" if sel > 0 else "kurang")


# ------------------------------------------------------------------ peta (pembantu)
def _dalam(px, py, ring):
    x, y = ring[:, 0], ring[:, 1]; d = np.zeros(px.shape, bool)
    for xi, yi, xj, yj in zip(x, y, np.roll(x, -1), np.roll(y, -1)):
        if yi != yj: d ^= ((yi > py) != (yj > py)) & (px < (xj - xi) * (py - yi) / (yj - yi) + xi)
    return d


def nama_pendek(idx):
    """Buang awalan Kab./Kota; bila nama kembar (Tangerang, Serang) beri akhiran (Kab)/(Kota)."""
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


def buat_peta(df, kol, zmin, zmax, satuan, warna, lab, zmid=None):
    xs, ys = np.unique(df["lon"].round(4)), np.unique(df["lat"].round(4)); h = float(np.median(np.diff(xs)) / 2) if len(xs) > 1 else 0.025
    kotak = {"type": "FeatureCollection", "features": [{"type": "Feature", "id": str(int(g)), "properties": {}, "geometry": {"type": "Polygon", "coordinates": [[[lo - h, la - h], [lo + h, la - h], [lo + h, la + h], [lo - h, la + h], [lo - h, la - h]]]}} for g, lo, la in zip(df["grid_id"], df["lon"], df["lat"])]}
    fig = go.Figure(go.Choroplethmap(geojson=kotak, locations=df["grid_id"].astype(int).astype(str), z=df[kol], text=df["wilayah"].fillna("Di luar batas kab/kota"), colorscale=warna, zmin=zmin, zmax=zmax, zmid=zmid,
                                     marker=dict(opacity=0.88, line=dict(width=0)), colorbar=dict(title=dict(text="", font=dict(size=9)), thickness=8, len=0.5, tickfont=dict(size=9), x=0.995),
                                     hovertemplate="<b>%{text}</b><br>%{z:.1f} " + satuan + "<extra></extra>"))
    lon_r, lat_r = max(xs.max() - xs.min() + 2 * h, 0.2) * 1.08, max(ys.max() - ys.min() + 2 * h, 0.2) * 1.08 / np.cos(np.radians(float(ys.mean())))
    zoom = float(np.clip(min(np.log2(360 * 400 / (512 * lon_r)), np.log2(360 * H_PETA / (512 * lat_r))), 5, 11))      # 512 px/tile (MapLibre); lebar kartu diperkirakan 400 px
    lay = dict(style="carto-positron", center=dict(lat=float((ys.min() + ys.max()) / 2), lon=float((xs.min() + xs.max()) / 2)), zoom=zoom)
    if gj is not None: lay["layers"] = [dict(sourcetype="geojson", source=gj, type="line", color="#33474a", line=dict(width=1.3), below="")]
    fig.update_layout(map=lay)
    if len(lab): fig.add_trace(go.Scattermap(lon=lab["lon"], lat=lab["lat"], mode="text", text=lab["nama"], textfont=dict(size=9, color="#1d2b3a"), hoverinfo="skip", showlegend=False))
    return fig


def gambar(fig, h, legenda=False, judul=None):
    fig.update_layout(height=h, margin=dict(l=2, r=2, t=2, b=2), font=dict(size=10, color="#33404d"), plot_bgcolor="white", paper_bgcolor="white", separators=",.", showlegend=legenda, uniformtext=dict(minsize=8, mode="hide"), legend=dict(orientation="h", y=1.14, x=0, font_size=9))
    if judul: fig.update_layout(margin=dict(l=2, r=2, t=24, b=2), title=dict(text=judul.upper(), x=0.005, xanchor="left", y=0.99, yanchor="top", font=dict(size=9.5, color="#55606e")))      # judul panel DI DALAM grafik: tak bisa tertimpa
    fig.update_xaxes(showgrid=False, linecolor="#c8cfd8"); fig.update_yaxes(gridcolor="#eef1f4", zeroline=False)
    cfg = dict(displaylogo=False, displayModeBar=False)
    try: st.plotly_chart(fig, width="stretch", config=cfg)
    except TypeError: st.plotly_chart(fig, use_container_width=True, config=cfg)


def pilih(opsi, key, label, default=None, fmt=None):
    default = default or opsi[0]
    if hasattr(st, "segmented_control"):
        v = st.segmented_control(label, opsi, default=default, key=key, format_func=fmt or (lambda x: x))
        return default if v is None else v
    return st.radio(label, opsi, index=opsi.index(default), key=key, format_func=fmt or (lambda x: x), horizontal=True)


# ================================================================== HALAMAN CATATAN (untuk pemahaman sendiri)
def halaman_catatan():
    ho, tr = meta.get("holdout") or {}, meta.get("model_transfer_terbaik") or {}
    st.markdown("## Catatan untuk pemahaman sendiri (bukan untuk ditampilkan)")
    st.caption("Buka halaman ini dengan menambahkan ?catatan=1 di alamat dashboard. Tutup dengan menghapusnya.")
    st.markdown("### 1. Cara membaca tiap panel")
    st.table(pd.DataFrame([
        ["Kartu angka", "Berapa dari 100 bulan yang kering: masa lalu menurut model, proyeksi 2026-2050, dan selisihnya.", "Bandingkan selisih, bukan angka mutlak. Garis di bawah angka = pengamatan nyata (CHIRPS)."],
        ["Peta", "Frekuensi bulan kering per grid ±5 km, sesuai filter.", "Makin merah makin sering kering. Mode 'Selisih': merah = lebih sering kering dari masa lalu, biru = lebih jarang."],
        ["Per 5 tahun", "Rata-rata proyeksi tiap blok lima tahun; garis oranye = masa lalu model.", "Sengaja per blok agar tidak terbaca sebagai ramalan tahun tertentu."],
        ["Bulan rawan", "Profil per bulan; batang gelap = bulan yang sedang dipilih filter.", "Berlian oranye = masa lalu; batang lebih tinggi dari berlian = lebih sering kering."],
        ["Tergantung model?", "Selisih proyeksi dibanding masa lalu untuk keempat model.", "Batang berbeda arah = hasil bergantung model, jadi tidak ada perubahan yang pasti."],
        ["Per kab/kota", "Rata-rata grid di dalam tiap kab/kota.", "Hanya agregasi; polanya sebagian besar berasal dari klimatologi CHIRPS, bukan sinyal GCM."]],
        columns=["Panel", "Apa itu", "Cara membaca"]).set_index("Panel"))
    st.markdown("### 2. Aturan warna dan kata (semua dihitung otomatis)")
    st.table(pd.DataFrame([
        ["Selisih", "BELUM PASTI (abu) bila |selisih| < 2 × galat baku naik-turun antar-tahun; LEBIH SERING (merah) / LEBIH JARANG (biru) bila lebih besar."],
        ["Searah antar model", "SEPAKAT (hijau) bila 4 dari 4 model searah; CONDONG (kuning) bila 3 dari 4; TERPECAH (merah) bila 2 dari 4 atau kurang."],
        ["Keyakinan", "Enam titik (hijau = terpenuhi): model terbaik dari 4; lebih baik dari klimatologi di uji 2021-2025; arah sejalan GCM mentah; data masukan di luar rentang < 10%; baseline model dekat pengamatan (≤ 3 poin); keempat model searah. Terpenuhi ≥ 5 = TINGGI, 4 = SEDANG, ≤ 3 = RENDAH."],
        ["Satuan", "'dari 100 bulan' = persen bulan kering (SPI ≤ -1); selisih dalam poin persentase."]], columns=["Elemen", "Aturan"]).set_index("Elemen"))
    st.markdown("### 3. Ringkasan metode (5W1H)")
    st.markdown(f"- **Apa:** seberapa sering bulan kering (SPI ≤ -1) di Banten pada {H0}-{H1} dibanding 1981-2010.\n- **Mengapa:** kekeringan memengaruhi pertanian, air bersih, dan waduk; ini gambaran kecenderungan, bukan prakiraan.\n"
                f"- **Siapa:** {PEMBUAT or '-'}.\n- **Di mana:** Banten, grid ±5 km dan kab/kota.\n- **Kapan:** proyeksi {H0}-{H1}; baseline 1981-2010; data dijalankan {meta.get('tanggal_run', '-')} (notebook {meta.get('versi_notebook', '-')}).\n"
                f"- **Bagaimana:** GCM {meta.get('gcm')} ({meta.get('skenario')}) → model statistik dilatih pada ERA5 dan CHIRPS (latih/seleksi 1981-2020, hold-out 2021-2025) → ensemble hujan bulanan → SPI.")
    st.markdown("### 4. Angka penting untuk dijelaskan")
    st.markdown(f"- Model tampil: **{meta.get('model')}**. Status: {meta.get('status_gerbang')}.")
    if ho: st.markdown(f"- Hold-out 2021-2025: CRPSS Tingkat 1 = **{n(ho['crpss_t1'], 3, True)}**, positif di **{ho['tahun_positif']} dari {ho['n_tahun']}** tahun. Hanya 5 tahun, jadi baca sebagai pemeriksaan arah.")
    if tr: st.markdown(f"- Transfer ke prediktor GCM (Tingkat 2, SPI-3): selisih frekuensi kering vs pengamatan per model = {tr.get('selisih_semua')}. Paling dekat pengamatan: **{tr.get('model')}** (sensitivitas, bukan pengganti).")
    if D["gerb"] is not None: st.dataframe(D["gerb"].round(3), hide_index=True)
    st.markdown("### 5. Hal yang harus diingat saat menjelaskan")
    st.markdown("- Ini **bukan ramalan**: GCM berjalan bebas, jadi tahun kering di grafik tidak sama dengan tahun kering sebenarnya.\n- Satu GCM, satu skenario, satu anggota; ketidakpastian model/skenario tidak tercakup.\n"
                "- Skill sefase (Tingkat 1) **tidak otomatis terbawa** ke prediktor GCM (Tingkat 2): model melebihkan frekuensi bulan kering, jadi yang dibaca adalah **selisih**.\n- Hold-out hanya 5 tahun; selisih kecil belum berarti.")
    st.markdown("### 6. Penjelasan 30 detik")
    st.info("Kami memproyeksikan seberapa sering bulan kering terjadi di Banten sampai 2050 memakai satu model iklim global yang diperhalus ke skala Banten. "
            "Hasilnya dibandingkan dengan masa lalu menurut model yang sama. Selisihnya kecil dan masih dalam naik-turun alami, serta keempat model statistik tidak sepakat arahnya, "
            "jadi belum ada perubahan yang bisa dipastikan. Ini gambaran kecenderungan, bukan ramalan.")


if str(st.query_params.get("catatan", "")) in ("1", "true", "ya"): halaman_catatan(); st.stop()

# ================================================================== DASHBOARD SATU LAYAR
gr_ref, LAB = wilayah_grid(len(D["grid"]))
th_all = sorted(D["b_grid"]["tahun"].unique().tolist())

c_t, c_s, c_m, c_y, c_p = st.columns([4.2, 1.35, 1.1, 1.7, 1.25], gap="small")
c_t.markdown(f'<div class="ttl" style="font-size:min(1.3rem, {75 / max(len(JUDUL_PROYEK), 1):.2f}vw)">{JUDUL_PROYEK}</div><div class="sub">{meta.get("gcm")} · {meta.get("skenario")} · dibanding 1981-2010 · bukan ramalan · kering = SPI ≤ -1</div>', unsafe_allow_html=True)
with c_s: skala = pilih(list(meta["spi_skala"]), "skala", "Jangka", fmt=lambda s: NAMA_SKALA.get(s, s))
with c_m: musim = st.selectbox("Musim", list(PRESET))
with c_y: t0, t1 = st.select_slider("Tahun", th_all, value=(th_all[0], th_all[-1]))
with c_p: mode = pilih(["Kering", "Selisih"], "mode_peta", "Peta")
bulan = PRESET[musim]

# ---- agregasi
G = D["b_grid"][(D["b_grid"]["SPI"] == skala)]; B = D["b_base"][(D["b_base"]["SPI"] == skala)]
gs = G[G["bulan"].isin(bulan) & G["tahun"].between(t0, t1)]; bs = B[B["bulan"].isin(bulan)]
if gs.empty: st.warning("Tidak ada data untuk pilihan ini."); st.stop()
per_th = gs.groupby("tahun")["p_kering"].mean().mul(100)
proy, base, ref = float(gs["p_kering"].mean() * 100), float(bs["kering_model_pct"].mean()), float(bs["kering_target_pct"].mean())
sel = proy - base; kode = tafsir(sel, se_kasar(per_th))
# model
selisih_model = {}
if D["banding"] is not None:
    dm = D["banding"][(D["banding"]["SPI"] == skala) & D["banding"]["model"].isin(ML)]
    for nm_, g_ in dm.groupby("model"):
        if g_["baseline_model_sendiri_pct"].notna().any() and g_["n_bulan_valid"].sum() > 0: selisih_model[nm_] = float(np.average(g_["kering_pct_mean"], weights=g_["n_bulan_valid"]) - g_["baseline_model_sendiri_pct"].dropna().iloc[0])
utama = next((m_ for m_ in ML if m_ in str(meta.get("model", ""))), None); tr = (meta.get("model_transfer_terbaik") or {}).get("model")
if tr is None and D["gerb"] is not None and {"c_kering_pct", "acuan_c"} <= set(D["gerb"].columns): gg = D["gerb"].set_index("model"); tr = (gg["c_kering_pct"] - gg["acuan_c"]).abs().idxmin()
tanda = np.sign(list(selisih_model.values())); n_searah = int(max((tanda > 0).sum(), (tanda < 0).sum())) if len(tanda) else 0
# keyakinan
ho = meta.get("holdout") or {}; ka = (meta.get("konsistensi_arah") or {}).get("jendela") or []; jd = next((j for j in ka if j["jendela"] == f"{H0}-{H1}"), None); luar = (meta.get("baris_prediktor_luar_rentang_pct") or {}).get(f"{H0}-{H1}")
cek = [("Model terbaik dari 4 model (tuning setara)", "terbaik dari 4" in str(meta.get("status_gerbang", ""))),
       ("Lebih baik dari klimatologi pada uji 2021-2025", bool(ho.get("lebih_baik_dari_klimatologi"))),
       ("Arah sejalan dengan hujan mentah GCM", jd is not None and not jd["berlawanan"]),
       ("Data masukan di luar rentang < 10%", luar is not None and luar < 10),
       ("Baseline model dekat pengamatan (≤ 3 poin)", abs(base - ref) <= 3),
       ("Keempat model searah", len(tanda) >= 2 and n_searah == len(tanda))]
n_ok = sum(ok for _, ok in cek); yak, yak_c = ("TINGGI", "green") if n_ok >= 5 else ("SEDANG", "amber") if n_ok == 4 else ("RENDAH", "red")

# ---- kartu angka
def tile(k, v, kecil, s, chip, cls, warna):
    return f'<div class="tile" style="--c:{warna}"><div class="k">{k}</div><div class="v">{v} <small>{kecil}</small></div><div class="s">{s}</div><span class="chip {cls}">{chip}</span></div>'
ch_sel = {"sama": ("BELUM PASTI", "gray"), "lebih": ("LEBIH SERING KERING", "red"), "kurang": ("LEBIH JARANG KERING", "blue"), "sedikit": ("DATA SEDIKIT", "gray")}[kode]
ch_mod = ("SEPAKAT", "green") if len(tanda) and n_searah == len(tanda) else ("CONDONG", "amber") if len(tanda) and n_searah == len(tanda) - 1 else ("TERPECAH", "red") if len(tanda) else ("-", "gray")
KPI_CSS = """<style>
body {margin:0; padding:2px 1px 0; background:#f3f5f8; font-family:"Segoe UI", Arial, sans-serif; color:#1d2b3a;}
.kpi {display:grid; grid-template-columns:repeat(5, minmax(0, 1fr)); gap:8px;}
.tile {background:#fff; border:1px solid #e1e5ea; border-top:3px solid var(--c); border-radius:7px; padding:5px 10px 6px; height:86px; box-sizing:border-box; overflow:hidden;}
.k {font-size:9.5px; font-weight:700; color:#6b7785; text-transform:uppercase; letter-spacing:.04em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.v {font-size:24px; font-weight:700; line-height:1.15; white-space:nowrap;}
.v small {font-size:10px; font-weight:500; color:#6b7785;}
.s {font-size:10px; color:#6b7785; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.chip {display:inline-block; padding:0 8px; border-radius:9px; font-size:9.5px; font-weight:700; color:#fff; margin-top:2px; white-space:nowrap;}
.red {background:#d1495b;} .blue {background:#2a6f97;} .gray {background:#8d99a6;} .amber {background:#e0912b;} .green {background:#2a9d8f;}
.dot {display:inline-block; width:10px; height:10px; border-radius:50%; margin:2px 4px 0 0; background:#d9dee4;} .dot.ok {background:#2a9d8f;} .dot.no {background:#e0912b;}
.insrow {margin-top:7px; white-space:nowrap; overflow:hidden;}
.ins {display:inline-block; font-size:11px; color:#33404d; background:#fff; border:1px solid #e1e5ea; border-radius:12px; padding:1px 9px 1px 7px; margin:0 5px 0 0;}
.ins i {display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:5px;}
</style>"""
TILES = []
TILES.append(tile("Masa lalu (model)", n(base, 0), "dari 100 bulan", f"pengamatan nyata: {n(ref, 0)}", "MODEL MELEBIHKAN" if base - ref > 3 else "DEKAT PENGAMATAN", "amber" if base - ref > 3 else "green", "#e8833a"))
TILES.append(tile(f"Proyeksi {t0}-{t1}", n(proy, 0), "dari 100 bulan", f"{musim.lower()} · {NAMA_SKALA.get(skala, skala)}", "ENSEMBLE", "gray", PROY))
TILES.append(tile("Selisih", n(sel, 1, True), "bulan/100", "vs masa lalu model", *ch_sel, WARNA_CHIP[ch_sel[1]]))
TILES.append(tile("Searah antar model", f"{n_searah}/{len(tanda)}" if len(tanda) else "-", "model", f"selisih {n(min(selisih_model.values()), 0, True)} s/d {n(max(selisih_model.values()), 0, True)}" if selisih_model else "data model tidak ada", *ch_mod, WARNA_CHIP[ch_mod[1]]))
titik = "".join(f'<span class="dot {"ok" if ok else "no"}" title="{"✓" if ok else "✗"} {t}"></span>' for t, ok in cek)
TILES.append(f'<div class="tile" style="--c:{WARNA_CHIP[yak_c]}"><div class="k">Keyakinan</div><div class="v">{yak}</div><div class="s">{n_ok}/6 syarat · arahkan kursor</div>{titik}</div>')

# ---- peta & agregasi grid
agg = gs.groupby("grid_id")["p_kering"].mean().mul(100).rename("p_kering").reset_index().merge(bs.groupby("grid_id")["kering_model_pct"].mean().reset_index(), on="grid_id").merge(gr_ref, on="grid_id")
agg["selisih"] = agg["p_kering"] - agg["kering_model_pct"]; agg_in = agg[agg["wilayah"].notna()] if gj is not None else agg
rk = agg_in.dropna(subset=["wilayah"]).groupby("wilayah")[["p_kering", "kering_model_pct"]].mean().sort_values("p_kering") if gj is not None else pd.DataFrame()
if len(rk): rk.index = nama_pendek(rk.index.tolist())
prof = G[G["tahun"].between(t0, t1)].groupby("bulan")["p_kering"].mean().mul(100); pb = B.groupby("bulan")["kering_model_pct"].mean().reindex(prof.index)

# ---- baris insight (kata singkat + warna)
ins = [({"sama": "gray", "lebih": "red", "kurang": "blue", "sedikit": "gray"}[kode], {"sama": f"Selisih {n(sel, 1, True)}: belum pasti", "lebih": f"Lebih sering kering ({n(sel, 1, True)})", "kurang": f"Lebih jarang kering ({n(sel, 1, True)})", "sedikit": "Data terlalu sedikit"}[kode]),
       ("amber" if base - ref > 3 else "green", f"Model melebihkan: {n(base, 0)} vs {n(ref, 0)}" if base - ref > 3 else "Model dekat pengamatan")]
if selisih_model: ins.append((ch_mod[1], "Model sepakat" if ch_mod[0] == "SEPAKAT" else f"Model terpecah: {n(min(selisih_model.values()), 0, True)} s/d {n(max(selisih_model.values()), 0, True)}"))
ins.append(("gray", f"Rawan: {BULAN[int(prof.idxmax()) - 1]}" + (f" · {rk.index[-1]}" if len(rk) else "")))
KPI_HTML = KPI_CSS + '<div class="kpi">' + "".join(TILES) + '</div><div class="insrow">' + "".join(f'<span class="ins"><i style="background:{WARNA_CHIP[c]}"></i>{t}</span>' for c, t in ins) + "</div>"
if hasattr(st, "iframe"): st.iframe(KPI_HTML, height=H_KPI)          # Streamlit baru
else: components.html(KPI_HTML, height=H_KPI)                      # Streamlit lama

# ---- grid panel
col_peta, col_b, col_c = st.columns([4.2, 3.9, 3.9], gap="small")
with col_peta, st.container(border=True):
    JD = f'Peta · {"bulan kering per 100" if mode == "Kering" else "selisih vs masa lalu"}'
    if mode == "Kering": fig = buat_peta(agg_in, "p_kering", 0, max(20.0, float(np.ceil(np.nanpercentile(agg_in["p_kering"], 98) / 10) * 10)), "dari 100", KERING, LAB)
    else: lim = max(5.0, float(np.ceil(np.nanpercentile(agg_in["selisih"].abs(), 98) / 5) * 5)); fig = buat_peta(agg_in, "selisih", -lim, lim, "selisih", "RdBu_r", LAB, zmid=0)
    gambar(fig, H_PETA, judul=JD)
with col_b:
    with st.container(border=True):
        JD = 'Per 5 tahun · garis = masa lalu'
        blok = per_th.groupby((per_th.index - t0) // 5).agg(["mean", lambda s: s.index.min(), lambda s: s.index.max()]); blok.columns = ["v", "a", "b"]
        fig = go.Figure(go.Bar(x=[f"{str(int(a))[2:]}-{str(int(b))[2:]}" for a, b in zip(blok["a"], blok["b"])], y=blok["v"], marker_color=PROY, text=[n(v, 0) for v in blok["v"]], textposition="inside", insidetextanchor="end", textfont=dict(size=10, color="white"), hovertemplate="%{x}<br>%{y:.1f} dari 100<extra></extra>"))
        fig.add_hline(y=base, line_dash="dot", line_color=BASE, line_width=2.5)
        fig.update_layout(yaxis_range=[0, max(blok["v"].max(), base) * 1.12]); gambar(fig, H_KECIL, judul=JD)
    with st.container(border=True):
        JD = 'Tergantung model? ★ dipakai ◆ dekat data'
        if len(selisih_model) >= 2:
            urut = sorted(selisih_model, key=selisih_model.get); nama_ = [m_ + (" ★" if m_ == utama else " ◆" if m_ == tr and m_ != utama else "") for m_ in urut]
            fig = go.Figure(go.Bar(y=nama_, x=[selisih_model[m_] for m_ in urut], orientation="h", marker_color=[PROY if m_ == utama else BASE if m_ == tr else ABU for m_ in urut], text=[n(selisih_model[m_], 1, True) for m_ in urut], textposition="outside", textfont_size=9, cliponaxis=False))
            fig.add_vline(x=0, line_color="#555", line_width=1.2); fig.update_xaxes(zeroline=False); gambar(fig, H_KECIL, judul=JD)
        else: st.caption("Data perbandingan model belum ada.")
with col_c:
    with st.container(border=True):
        JD = 'Bulan rawan · gelap = terpilih'
        fig = go.Figure(go.Bar(x=[BULAN[b - 1] for b in prof.index], y=prof.values, marker_color=[PROY if b in bulan else "#b8cfdd" for b in prof.index], hovertemplate="%{x}<br>%{y:.1f} dari 100<extra>proyeksi</extra>"))
        fig.add_trace(go.Scatter(x=[BULAN[b - 1] for b in pb.index], y=pb.values, mode="markers", marker=dict(symbol="diamond", size=9, color=BASE, line=dict(width=1, color="white")), hovertemplate="%{x}<br>%{y:.1f} dari 100<extra>masa lalu</extra>")); fig.update_xaxes(tickvals=[BULAN[b - 1] for b in prof.index], ticktext=[BULAN[b - 1][0] for b in prof.index]); gambar(fig, H_KECIL, judul=JD)
    with st.container(border=True):
        JD = 'Kab/kota · ◆ = masa lalu'
        if len(rk):
            fig = go.Figure(go.Bar(y=rk.index, x=rk["p_kering"], orientation="h", marker_color=PROY, text=[n(v, 0) for v in rk["p_kering"]], textposition="outside", textfont_size=9, cliponaxis=False, hovertemplate="%{y}<br>%{x:.1f} dari 100<extra></extra>"))
            fig.add_trace(go.Scatter(y=rk.index, x=rk["kering_model_pct"], mode="markers", marker=dict(symbol="diamond", size=9, color=BASE, line=dict(width=1, color="white")), hovertemplate="%{y}<br>masa lalu %{x:.1f}<extra></extra>")); gambar(fig, H_KECIL, judul=JD)
        else: st.caption("Batas kab/kota belum tersedia.")

st.markdown(f'<div class="foot">{meta.get("gcm")} {meta.get("skenario")} · acuan {meta.get("target")} · run {meta.get("tanggal_run", "-")} · gambaran kecenderungan, bukan ramalan cuaca.{" · " + PEMBUAT if PEMBUAT else ""}</div>', unsafe_allow_html=True)

"""Dashboard proyeksi kekeringan Banten 2026-2050 (versi bersih untuk orang awam).
Jalankan:  streamlit run app_dashboard_spi.py
Berkas data (hasil ekspor notebook 14d-14i) harus ada di folder yang sama dengan berkas ini,
atau tunjuk foldernya lewat variabel lingkungan HASIL_DIR.
"""
import json, os
import numpy as np, pandas as pd, streamlit as st
import plotly.graph_objects as go

# ------------------------------------------------------------------ identitas (ubah di sini)
PEMBUAT = "Gemala Aleida Fitri · Statistika dan Sains Data, IPB University"   # tampil kecil di bagian bawah; kosongkan bila tak perlu

st.set_page_config(page_title="Kekeringan Banten 2026-2050", page_icon="🌧️", layout="wide")
st.markdown("""<style>
.block-container {max-width: 1180px; padding-top: 2.2rem;}
.hero {background: #e8f4f3; border-left: 6px solid #0f766e; border-radius: 10px; padding: 16px 20px; font-size: 1.15rem; line-height: 1.55;}
.hero b {color: #0b5a54;}
.kecil {color: #5d6b6c; font-size: 0.88rem;}
button[data-baseweb="tab"] p {font-weight: 600; font-size: 1.02rem;}
</style>""", unsafe_allow_html=True)

# ------------------------------------------------------------------ warna dan teks
TEAL, ORANYE, ABU, ABU_TUA = "#0f766e", "#e07a1f", "#b8c0c4", "#6b777a"
SKALA_WARNA_KERING = [[0, "#fff8ec"], [0.35, "#fdd9a0"], [0.7, "#f08a4b"], [1, "#b23a1a"]]
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
PRESET = {"Sepanjang tahun": list(range(1, 13)), "Des-Feb": [12, 1, 2], "Mar-Mei": [3, 4, 5], "Jun-Agu": [6, 7, 8], "Sep-Nov": [9, 10, 11]}
NAMA_SKALA = {"SPI-3": "Jangka pendek (3 bulan)", "SPI-6": "Satu musim (6 bulan)", "SPI-12": "Satu tahun (12 bulan)"}
PENJELASAN_SKALA = {"SPI-3": "Cepat bereaksi terhadap kurang hujan; relevan untuk tanaman.",
                    "SPI-6": "Gambaran kekeringan satu musim.",
                    "SPI-12": "Kekeringan panjang; relevan untuk air tanah dan waduk."}
KATEGORI = pd.DataFrame({"Nilai SPI": ["2,0 atau lebih", "1,0 sampai 1,99", "-0,99 sampai 0,99", "-1,0 sampai -1,49", "-1,5 sampai -1,99", "-2,0 atau kurang"],
                         "Artinya": ["Sangat basah", "Basah", "Normal", "Kering", "Sangat kering", "Kering ekstrem"],
                         "Dihitung 'bulan kering'?": ["Tidak", "Tidak", "Tidak", "Ya", "Ya", "Ya"]}).set_index("Nilai SPI")


# ------------------------------------------------------------------ pembaca data
FOLDER = os.environ.get("HASIL_DIR") or os.path.dirname(os.path.abspath(__file__))


def jalur(nama):
    p = os.path.join(FOLDER, nama)
    alt = os.path.join(FOLDER, nama.replace(".csv.gz", "_csv.gz"))
    return p if os.path.exists(p) or not os.path.exists(alt) else alt


@st.cache_data
def muat_semua(folder_ver):
    d = {"reg": pd.read_csv(jalur("dashboard_tahunan_regional.csv")),
         "meta": json.load(open(jalur("dashboard_meta.json"), encoding="utf-8"))}
    for kunci, nama in [("b_reg", "dashboard_bulanan_regional.csv.gz"), ("b_grid", "dashboard_bulanan_per_grid.csv.gz"),
                        ("b_base", "dashboard_baseline_bulan_grid.csv.gz"), ("grid", "dashboard_grid.csv"),
                        ("kor", "dashboard_korelasi.csv"), ("gerb", "dashboard_model_gerbang.csv"), ("sens", "dashboard_sensitivitas.csv")]:
        p = jalur(nama)
        d[kunci] = pd.read_csv(p) if os.path.exists(p) else None
    p = jalur("banten_kabkota.geojson")
    d["gj"] = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None
    return d


try:
    D = muat_semua(tuple(sorted(os.listdir(FOLDER))))
except FileNotFoundError as e:
    st.error(f"Berkas data tidak ditemukan: {e.filename}. Letakkan hasil ekspor notebook (14d-14i) di folder yang sama dengan aplikasi ini.")
    st.stop()
reg, meta, gj = D["reg"], D["meta"], D["gj"]
H0, H1 = int(meta["horizon"][0]), int(meta["horizon"][1])


# ------------------------------------------------------------------ pembantu
def n(x, d=1, plus=False):
    s = f"{x:+.{d}f}" if plus else f"{x:.{d}f}"
    return s.replace(".", ",")


def se_kasar(v):
    v = pd.Series(v).dropna()
    return float(v.std(ddof=1) / np.sqrt(len(v))) if len(v) >= 3 else float("nan")


def tafsir(selisih, se):
    """Selisih dianggap berarti bila lebih dari 2x galat baku kasar naik-turun antar-tahun."""
    if not np.isfinite(se): return "sedikit"
    if abs(selisih) < 2 * se: return "sama"
    return "lebih" if selisih > 0 else "kurang"


KALIMAT = {"sama": "Selisihnya masih dalam naik-turun alami antar-tahun, jadi <b>belum ada perubahan yang bisa dipastikan</b>.",
           "lebih": "Bulan kering diproyeksikan <b>lebih sering</b> dari masa lalu.",
           "kurang": "Bulan kering diproyeksikan <b>lebih jarang</b> dari masa lalu.",
           "sedikit": "Data terlalu sedikit untuk disimpulkan."}


def tampil(fig, tinggi=360, legenda=True):
    fig.update_layout(height=tinggi, margin=dict(l=8, r=8, t=10, b=8), font=dict(size=13), separators=",.", plot_bgcolor="white", paper_bgcolor="white",
                      legend=dict(orientation="h", y=-0.22, x=0) if legenda else None, showlegend=legenda)
    fig.update_xaxes(showgrid=False, linecolor="#9aa5a8", ticks="outside")
    fig.update_yaxes(gridcolor="#e6ecec", zeroline=False)
    cfg = dict(displaylogo=False, displayModeBar=False)
    try: st.plotly_chart(fig, width="stretch", config=cfg)
    except TypeError: st.plotly_chart(fig, use_container_width=True, config=cfg)


def pilih(label, opsi, key, default=None, fmt=None):
    default = default or opsi[0]
    if hasattr(st, "segmented_control"):
        v = st.segmented_control(label, opsi, default=default, key=key, format_func=fmt or (lambda x: x), label_visibility="collapsed")
        return default if v is None else v
    return st.radio(label, opsi, index=opsi.index(default), key=key, format_func=fmt or (lambda x: x), horizontal=True, label_visibility="collapsed")


# ------------------------------------------------------------------ peta
def _dalam(px, py, ring):
    x, y = ring[:, 0], ring[:, 1]
    dalam = np.zeros(px.shape, bool)
    for xi, yi, xj, yj in zip(x, y, np.roll(x, -1), np.roll(y, -1)):
        if yi != yj: dalam ^= ((yi > py) != (yj > py)) & (px < (xj - xi) * (py - yi) / (yj - yi) + xi)
    return dalam


def _poligon(geom):
    return [geom["coordinates"]] if geom["type"] == "Polygon" else list(geom["coordinates"]) if geom["type"] == "MultiPolygon" else []


@st.cache_data
def petakan_wilayah(grid_ref, ada_gj):
    """Nama kabupaten/kota untuk tiap grid (titik pusat grid di dalam poligon) dan posisi label peta."""
    nama = pd.Series([None] * len(grid_ref), dtype=object)
    label = []
    if not ada_gj: return nama, pd.DataFrame(columns=["nama", "lon", "lat"])
    px, py = grid_ref["lon"].to_numpy(float), grid_ref["lat"].to_numpy(float)
    for f in gj["features"]:
        nm = f["properties"].get("nama", str(f.get("id", "?")))
        dalam, besar = np.zeros(len(px), bool), None
        for poly in _poligon(f["geometry"]):
            ext = np.asarray(poly[0], float)
            m = _dalam(px, py, ext)
            for hole in poly[1:]: m &= ~_dalam(px, py, np.asarray(hole, float))
            dalam |= m
            luas = np.ptp(ext[:, 0]) * np.ptp(ext[:, 1])
            if besar is None or luas > besar[0]: besar = (luas, ext[:, 0].mean(), ext[:, 1].mean())
        nama[dalam & nama.isna().to_numpy()] = nm
        if besar: label.append((nm.replace("Kab. ", "").replace("Kota ", ""), besar[1], besar[2]))
    return nama, pd.DataFrame(label, columns=["nama", "lon", "lat"])


def buat_peta(df, kol, zmin, zmax, satuan, warna, zmid=None):
    xs, ys = np.unique(df["lon"].round(4)), np.unique(df["lat"].round(4))
    h = float(np.median(np.diff(xs)) / 2) if len(xs) > 1 else 0.025
    kotak = {"type": "FeatureCollection", "features": [{"type": "Feature", "id": str(int(g)), "properties": {}, "geometry": {"type": "Polygon", "coordinates": [[[lo - h, la - h], [lo + h, la - h], [lo + h, la + h], [lo - h, la + h], [lo - h, la - h]]]}}
                                                      for g, lo, la in zip(df["grid_id"], df["lon"], df["lat"])]}
    teks = df["wilayah"].fillna("Di luar batas kab/kota").to_numpy()
    fig = go.Figure(go.Choroplethmap(geojson=kotak, locations=df["grid_id"].astype(int).astype(str), z=df[kol], text=teks, colorscale=warna, zmin=zmin, zmax=zmax, zmid=zmid,
                                     marker=dict(opacity=0.85, line=dict(width=0)), colorbar=dict(title=satuan, thickness=12, len=0.7),
                                     hovertemplate="<b>%{text}</b><br>%{z:.1f} " + satuan + "<extra></extra>"))
    zoom = float(np.clip(np.log2(500 / 256 * 360 / (max(xs.max() - xs.min(), 0.2) * 1.2)) - 0.1, 5, 11))
    lay = dict(style="carto-positron", center=dict(lat=float((ys.min() + ys.max()) / 2), lon=float((xs.min() + xs.max()) / 2)), zoom=zoom)
    if gj is not None: lay["layers"] = [dict(sourcetype="geojson", source=gj, type="line", color="#33474a", line=dict(width=1.5), below="")]
    fig.update_layout(map=lay)
    if len(WIL_LABEL): fig.add_trace(go.Scattermap(lon=WIL_LABEL["lon"], lat=WIL_LABEL["lat"], mode="text", text=WIL_LABEL["nama"], textfont=dict(size=12, color="#1f2d2e"), hoverinfo="skip", showlegend=False))
    return fig


# ------------------------------------------------------------------ kepala halaman
st.title("Seberapa sering Banten mengalami bulan kering?")
st.markdown(f"Proyeksi **{H0}-{H1}** dibanding masa lalu (1981-2010) · satu model iklim, satu skenario · **bukan ramalan cuaca**.")

st.markdown("**Pilih jangka kekeringan:**")
skala = pilih("Skala", list(meta["spi_skala"]), "skala", fmt=lambda s: NAMA_SKALA.get(s, s))
st.caption(PENJELASAN_SKALA.get(skala, "") + "  Bulan dianggap **kering** bila hujannya jauh di bawah normal (SPI ≤ -1).")

r = reg[reg["SPI"] == skala].sort_values("tahun")
rata, base = float(meta["proyeksi_pct"][skala]), float(meta["baseline_model_sendiri_pct"][skala])
sel, se = rata - base, se_kasar(r["kering_pct_mean"])
kode = tafsir(sel, se)

tab_ring, tab_peta, tab_tentang, tab_ilmiah = st.tabs(["Ringkasan", "Peta", "Batasan & istilah", "Untuk peneliti"])

# ------------------------------------------------------------------ tab ringkasan
with tab_ring:
    st.markdown(f'<div class="hero">Pada {H0}-{H1}, sekitar <b>{n(rata, 0)} dari 100 bulan</b> di Banten diproyeksikan kering. '
                f'Pada 1981-2010, model yang sama menghasilkan <b>{n(base, 0)} dari 100 bulan</b>. {KALIMAT[kode]}</div>', unsafe_allow_html=True)
    st.write("")
    c1, c2, c3 = st.columns(3)
    with c1.container(border=True): st.metric("Masa lalu (1981-2010)", f"{n(base)} dari 100 bulan", help="Frekuensi bulan kering menurut model yang sama, supaya bias model saling meniadakan.")
    with c2.container(border=True): st.metric(f"Proyeksi {H0}-{H1}", f"{n(rata)} dari 100 bulan")
    with c3.container(border=True): st.metric("Selisih", f"{n(sel, 1, True)} bulan per 100", delta="belum berarti" if kode == "sama" else ("lebih sering kering" if kode == "lebih" else "lebih jarang kering"), delta_color="off",
                                              help="Dianggap berarti bila lebih dari 2x galat baku kasar naik-turun antar-tahun.")

    st.subheader("Rata-rata per lima tahun")
    st.caption("Per lima tahun supaya tidak terbaca sebagai ramalan tahun tertentu. Garis putus-putus = masa lalu 1981-2010.")
    r = r.assign(blok=(r["tahun"] - H0) // 5)
    blok = r.groupby("blok").apply(lambda g: pd.Series({"a": g["tahun"].min(), "b": g["tahun"].max(), "v": np.average(g["kering_pct_mean"], weights=g["n_bulan_valid"])}), include_groups=False)
    fig = go.Figure(go.Bar(x=[f"{int(a)}-{int(b)}" for a, b in zip(blok["a"], blok["b"])], y=blok["v"], marker_color=TEAL, text=[n(v, 0) for v in blok["v"]], textposition="outside", cliponaxis=False,
                           hovertemplate="%{x}<br><b>%{y:.1f} dari 100 bulan kering</b><extra></extra>"))
    fig.add_hline(y=base, line_dash="dot", line_color=ABU_TUA, line_width=2.5, annotation_text=f"1981-2010: {n(base, 0)}", annotation_position="top left")
    fig.update_layout(yaxis_title="bulan kering dari 100 bulan", yaxis_range=[0, max(blok["v"].max(), base) * 1.3])
    tampil(fig, 320, legenda=False)

    with st.expander("Lihat per tahun (hati-hati: satu tahun bukan ramalan)"):
        st.caption("Model iklim berjalan bebas, jadi tahun kering di grafik ini tidak sama dengan tahun kering sebenarnya. Tahun 2026 hanya memuat sebagian bulan.")
        fig = go.Figure(go.Bar(x=r["tahun"], y=r["kering_pct_mean"], marker_color=ABU, hovertemplate="%{x}<br>%{y:.1f} dari 100 bulan<extra></extra>"))
        fig.add_hline(y=base, line_dash="dot", line_color=ABU_TUA, line_width=2.5)
        fig.update_layout(yaxis_title="bulan kering dari 100 bulan"); tampil(fig, 280, legenda=False)

    st.subheader("Bulan apa yang paling rawan?")
    if D["b_grid"] is not None:
        gm = D["b_grid"][D["b_grid"]["SPI"] == skala]; bb = D["b_base"][D["b_base"]["SPI"] == skala]
        prof = gm.groupby("bulan")["p_kering"].mean() * 100
        pb = bb.groupby("bulan")["kering_model_pct"].mean().reindex(prof.index)
        fig = go.Figure(go.Bar(x=[BULAN[b - 1] for b in prof.index], y=prof.values, marker_color=TEAL, name=f"Proyeksi {H0}-{H1}", hovertemplate="%{x}<br>%{y:.1f} dari 100<extra>proyeksi</extra>"))
        fig.add_trace(go.Scatter(x=[BULAN[b - 1] for b in pb.index], y=pb.values, mode="markers", marker=dict(symbol="diamond", size=11, color=ORANYE, line=dict(width=1.2, color="white")), name="Masa lalu 1981-2010",
                                 hovertemplate="%{x}<br>%{y:.1f} dari 100<extra>1981-2010</extra>"))
        fig.update_layout(yaxis_title="bulan kering dari 100 bulan"); tampil(fig, 320)
        st.caption(f"Paling sering kering: **{BULAN[int(prof.idxmax()) - 1]}** ({n(prof.max(), 0)} dari 100). Paling jarang: **{BULAN[int(prof.idxmin()) - 1]}** ({n(prof.min(), 0)} dari 100).")

    st.subheader("Seberapa bisa dipercaya?")
    ka = (meta.get("konsistensi_arah") or {}).get("jendela") or []
    jd = next((j for j in ka if j["jendela"] == f"{H0}-{H1}"), None)
    luar = (meta.get("baris_prediktor_luar_rentang_pct") or {}).get(f"{H0}-{H1}")
    ho = meta.get("holdout") or {}
    cek = [("terbaik dari 4" in str(meta.get("status_gerbang", "")), "Model dipilih sebagai yang terbaik di antara empat model yang dituning dengan cara yang sama.", "Pemilihan model belum memakai perbandingan empat model yang adil."),
           (bool(ho.get("lebih_baik_dari_klimatologi")) if ho else False, "Pada data uji 2021-2025 yang dikunci, model lebih baik daripada klimatologi biasa.",
            "Pada data uji 2021-2025 yang dikunci, model belum lebih baik daripada klimatologi biasa." if ho else "Data uji 2021-2025 belum tersedia di berkas hasil."),
           (jd is not None and not jd["berlawanan"], "Arah perubahan sejalan dengan hujan mentah model iklim.", "Arah perubahan hujan model <b>berlawanan</b> dengan hujan mentah model iklim; baca sebagai 'belum ada perubahan jelas'."),
           (luar is not None and luar < 20, f"Hanya {n(luar or 0, 0)}% data masukan di luar rentang yang pernah dipelajari model.", f"{n(luar or 0, 0)}% data masukan di luar rentang yang pernah dipelajari model.")]
    for ok, ya, tidak in cek: st.markdown(f"{'✅' if ok else '⚠️'} {ya if ok else tidak}", unsafe_allow_html=True)
    st.caption("Karena itu, pakai dashboard ini sebagai gambaran kemungkinan, bukan angka pasti. Setelah 2050 data masukan makin jauh dari yang dipelajari model, sehingga proyeksi dihentikan di 2050.")

# ------------------------------------------------------------------ tab peta
with tab_peta:
    if D["b_grid"] is None or D["grid"] is None:
        st.info("Berkas ekspor bulanan (sel 14e) belum ada, jadi peta belum bisa ditampilkan.")
    else:
        grid_ref = D["grid"].sort_values("grid_id").reset_index(drop=True)
        wil, WIL_LABEL = petakan_wilayah(grid_ref[["grid_id", "lon", "lat"]], gj is not None)
        grid_ref = grid_ref.assign(wilayah=wil.to_numpy())
        grdm = D["b_grid"][D["b_grid"]["SPI"] == skala]; basem = D["b_base"][D["b_base"]["SPI"] == skala]
        tahun_all = sorted(grdm["tahun"].unique().tolist())

        k1, k2, k3 = st.columns([1.2, 1, 1.2])
        t0, t1 = k1.select_slider("Rentang tahun", tahun_all, value=(tahun_all[0], tahun_all[-1]))
        musim = k2.selectbox("Bulan atau musim", list(PRESET) + ["Pilih bulan sendiri"], help="Pembagian musim di Banten hanya perkiraan kasar.")
        bulan = PRESET[musim] if musim in PRESET else [BULAN.index(m) + 1 for m in st.multiselect("Pilih bulan", BULAN, default=BULAN[5:9])]
        mode = k3.radio("Tampilan", ["Seberapa sering kering", "Dibanding masa lalu"], horizontal=True)
        dalam_saja = st.checkbox("Sembunyikan grid di luar batas Banten (laut atau provinsi tetangga)", value=True, disabled=gj is None)

        tp = [t for t in tahun_all if t0 <= t <= t1]
        gs = grdm[grdm["tahun"].isin(tp) & grdm["bulan"].isin(bulan)]
        if gs.empty or not bulan:
            st.warning("Tidak ada data untuk pilihan ini. Pilih minimal satu bulan dan satu tahun.")
        else:
            agg = gs.groupby("grid_id")["p_kering"].mean().mul(100).rename("p_kering").reset_index()
            bs = basem[basem["bulan"].isin(bulan)].groupby("grid_id")["kering_model_pct"].mean().reset_index()
            agg = agg.merge(bs, on="grid_id").merge(grid_ref, on="grid_id"); agg["selisih"] = agg["p_kering"] - agg["kering_model_pct"]
            if dalam_saja and gj is not None: agg = agg[agg["wilayah"].notna()]
            fk, fb = agg["p_kering"].mean(), agg["kering_model_pct"].mean()
            st.markdown(f"**{musim if musim != 'Pilih bulan sendiri' else ', '.join(BULAN[b - 1] for b in bulan)} · {t0}-{t1}:** sekitar **{n(fk, 0)} dari 100 bulan** kering "
                        f"(masa lalu: {n(fb, 0)}; selisih {n(fk - fb, 1, True)}).")
            ca, cb = st.columns([3, 2], gap="medium")
            with ca:
                if mode == "Seberapa sering kering":
                    hi = max(20.0, float(np.ceil(np.nanpercentile(agg["p_kering"], 98) / 10) * 10)); fig = buat_peta(agg, "p_kering", 0, hi, "dari 100 bulan", SKALA_WARNA_KERING)
                else:
                    lim = max(5.0, float(np.ceil(np.nanpercentile(agg["selisih"].abs(), 98) / 5) * 5)); fig = buat_peta(agg, "selisih", -lim, lim, "selisih", "RdBu_r", zmid=0)
                tampil(fig, 480, legenda=False)
                st.caption("Makin oranye/merah = makin sering kering." if mode.startswith("Seberapa") else "Merah = lebih sering kering dari masa lalu, biru = lebih jarang.")
            with cb:
                if gj is not None and agg["wilayah"].notna().any():
                    rk = agg.dropna(subset=["wilayah"]).groupby("wilayah")[["p_kering", "kering_model_pct"]].mean().sort_values("p_kering")
                    fig = go.Figure(go.Bar(y=rk.index, x=rk["p_kering"], orientation="h", marker_color=TEAL, name="Proyeksi", hovertemplate="%{y}<br>%{x:.1f} dari 100<extra></extra>"))
                    fig.add_trace(go.Scatter(y=rk.index, x=rk["kering_model_pct"], mode="markers", marker=dict(symbol="diamond", size=12, color=ORANYE, line=dict(width=1.2, color="white")), name="Masa lalu"))
                    fig.update_layout(xaxis_title="bulan kering dari 100 bulan"); tampil(fig, 480)
                    st.caption(f"Paling sering kering: **{rk.index[-1]}** ({n(rk['p_kering'].iloc[-1], 0)}). Paling jarang: **{rk.index[0]}** ({n(rk['p_kering'].iloc[0], 0)}).")
            st.download_button("Unduh tabel per grid (CSV)", agg.drop(columns=["selisih"]).round(3).to_csv(index=False).encode("utf-8-sig"), file_name=f"peta_kering_banten_{skala}.csv", mime="text/csv")

# ------------------------------------------------------------------ tab tentang
with tab_tentang:
    st.subheader("Batasan yang perlu diingat")
    st.markdown("- **Bukan ramalan.** Model iklim berjalan bebas, jadi tahun kering di grafik tidak sama dengan tahun kering yang akan terjadi.\n"
                "- **Satu model iklim dan satu skenario.** Hasil model atau skenario lain bisa berbeda; rentang yang ditampilkan tidak mencakup ketidakpastian itu.\n"
                "- **Baca selisih, bukan angka mutlak.** Setiap model punya bias sendiri, maka pembanding utama adalah masa lalu menurut model yang sama.\n"
                "- **Perubahan kecil belum berarti.** Selisih yang masih dalam naik-turun alami antar-tahun tidak boleh ditafsirkan sebagai tren.")
    with st.expander("Apa itu SPI?"):
        st.markdown("**SPI** membandingkan hujan suatu periode dengan hujan biasanya. 0 = normal, negatif = lebih kering. Angka 3, 6, 12 = lama periode dalam bulan.")
        st.table(KATEGORI)
    with st.expander("Catatan teknis lengkap dari analisis"):
        for cat in meta["catatan"]: st.write("- " + cat)

# ------------------------------------------------------------------ tab peneliti
with tab_ilmiah:
    st.caption("Bagian ini untuk pembaca yang ingin memeriksa dasar analisisnya.")
    gerb, sens, kor = D["gerb"], D["sens"], D["kor"]
    if gerb is not None:
        st.subheader("Perbandingan empat model")
        acu = float(gerb["acuan_c"].iloc[0])
        t = pd.DataFrame({"Model": gerb["model"], "Lolos (dari 3)": gerb["kriteria_lolos"].astype(int), "(a) skill vs klimatologi (>0)": gerb["a_crpss_t1"].round(3),
                          "(b) rasio sebaran (≤1,10)": gerb["b_qq_rasio"].round(2), "(c) selisih frekuensi kering (≤3 poin)": (gerb["c_kering_pct"] - acu).abs().round(1),
                          "Dipakai": np.where(gerb["tampil"].astype(bool), "ya", "")}).sort_values(["Lolos (dari 3)", "(a) skill vs klimatologi (>0)"], ascending=False).set_index("Model")
        st.dataframe(t)
        st.caption("Model dipakai = terbaik di antara empat (CRPS Tingkat 1 terkecil, tuning setara). Tiga kolom kriteria hanya diagnostik, bukan penentu. Belum terbukti lebih baik daripada klimatologi bila CRPSS mendekati 0.")
    if sens is not None:
        st.subheader("Perubahan rata-rata hujan menurut model")
        sm = sens[sens["model"] != "Hujan GCM mentah"]; g2 = sens[sens["model"] == "Hujan GCM mentah"]["delta_mu_pct"]
        fig = go.Figure()
        for v, w in zip(["Dipotong (dipakai di dashboard)", "Tanpa pemotongan", "Hanya prediktor stabil"], [TEAL, ORANYE, "#6c7bd0"]):
            dv = sm[sm["varian"] == v]
            if not dv.empty: fig.add_trace(go.Bar(x=dv["model"], y=dv["delta_mu_pct"], name=v, marker_color=w))
        if len(g2): fig.add_hline(y=float(g2.iloc[0]), line_dash="dash", line_color="#c2185b", annotation_text="hujan mentah GCM", annotation_position="top left")
        fig.add_hline(y=0, line_color="#555", line_width=1); fig.update_layout(barmode="group", yaxis_title="perubahan hujan (%)"); tampil(fig, 320)
        st.caption("Empat model memberi arah dan besar perubahan yang berbeda-beda; inilah alasan hasil dibaca sebagai 'belum ada perubahan jelas'.")
    if kor is not None:
        st.subheader("Korelasi dengan data pengamatan per bulan dan musim")
        fig = go.Figure()
        for kol_r, kol_f, nama, w in [("r_gcm_target", "lolos_fdr_gcm_target", "Hujan mentah model iklim", ABU_TUA), ("r_model_t1", "lolos_fdr_model_t1", "Model berinput ERA5", TEAL)]:
            fig.add_trace(go.Bar(x=kor["unit"], y=kor[kol_r], name=nama, marker_color=w, text=["★" if bool(v) else "" for v in kor[kol_f]], textposition="outside"))
        rk = float(kor["r_kritis_p05"].iloc[0])
        for yy in (rk, -rk): fig.add_hline(y=yy, line_dash="dot", line_color="#555")
        fig.update_layout(barmode="group", yaxis_title="korelasi (r)", yaxis_range=[-0.6, 1.05]); tampil(fig, 340)
        st.caption(f"★ = tetap nyata setelah koreksi uji berganda (FDR); garis putus-putus = batas ±{n(rk, 2)}. "
                   "Model berinput ERA5 diuji dengan data nyata yang sefase; angka ini <b>bukan</b> ukuran ketepatan proyeksi, karena proyeksi memakai input model iklim yang tidak sefase dengan kejadian nyata.".replace("<b>", "").replace("</b>", ""))
    ka = meta.get("konsistensi_arah")
    if ka and ka.get("jendela"):
        st.subheader("Konsistensi arah dan data di luar rentang latih")
        st.dataframe(pd.DataFrame([{"Jendela": j["jendela"], "Hujan GCM mentah (%)": j["gcm_pr_mentah_pct"], "Model terpilih (%)": j["model_pct"], "Berlawanan?": "ya" if j["berlawanan"] else "tidak",
                                    "Input di luar rentang latih (%)": j["luar_rentang_pct"]} for j in ka["jendela"]]).set_index("Jendela"))

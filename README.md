# Dashboard Downscaling CMCC-ESM2 dan SPI Banten

Dashboard Streamlit satu halaman untuk menyajikan evaluasi downscaling curah hujan dari **CMCC-ESM2** dengan **CHIRPS** sebagai data referensi, serta hasil proyeksi kekeringan berbasis SPI.

## Isi dashboard

1. **Evaluasi downscaling** — ringkasan validasi pada prediktor ERA5 dan prediktor GCM, serta korelasi temporal GCM–CHIRPS jika tabel tersedia.
2. **Hasil SPI** — frekuensi bulan kering (SPI ≤ −1), pembanding baseline model dan CHIRPS, pola tahunan dan bulanan, peta grid, serta deret waktu SPI.
3. **Keterbatasan** — catatan interpretasi proyeksi, validasi, dan ketidakpastian.

## Menjalankan secara lokal

```bash
pip install -r requirements.txt
streamlit run app_dashboard_spi.py
```

Berkas data hasil ekspor notebook dan `dashboard_meta.json` harus berada di folder yang sama dengan aplikasi, atau diarahkan melalui variabel lingkungan `HASIL_DIR`.

## Data yang dibutuhkan

- `dashboard_meta.json`
- `dashboard_bulanan_per_grid.csv.gz`
- `dashboard_baseline_bulan_grid.csv.gz`
- `dashboard_grid.csv` (opsional untuk peta)
- `dashboard_bulanan_regional.csv.gz` (opsional untuk deret SPI)
- `dashboard_korelasi.csv` (opsional untuk korelasi temporal)
- `dashboard_uji.csv` (metadata ringkasan uji formal disimpan dalam JSON; file ini tidak wajib untuk tampilan ringkasan)

## Catatan interpretasi

- CRPSS positif menunjukkan skill lebih baik daripada klimatologi; CRPSS negatif menunjukkan skill lebih rendah daripada pembanding klimatologi.
- Validasi dengan prediktor ERA5 yang sefase dengan data observasi tidak otomatis menjamin transfer yang sama pada prediktor GCM.
- Uji beda nyata formal hanya ditampilkan ketika pilihan skala, periode, dan musim sesuai dengan cakupan uji yang tersimpan.
- Hasil proyeksi adalah proyeksi bersyarat skenario, bukan ramalan cuaca untuk tahun tertentu.
- Satu GCM dan satu skenario tidak mencakup seluruh ketidakpastian proyeksi iklim.
- Metrik evaluasi hujan seperti MAE, RMSE, dan bias tidak ditampilkan jika belum tersedia dalam berkas ekspor.

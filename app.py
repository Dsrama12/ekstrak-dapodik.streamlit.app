import streamlit as st
import google.generativeai as genai
import pandas as pd
import io

st.set_page_config(page_title="Ekstrak KK Dapodik", page_icon="📄", layout="wide")

# ─── CSS Ringan ────────────────────────────────────────────────
st.markdown("""
<style>
.block-container { padding-top: 1.5rem; }
.stButton>button { background:#1976D2; color:white; border-radius:6px; width:100%; }
.stDownloadButton>button { background:#2e7d32; color:white; border-radius:6px; width:100%; }
</style>
""", unsafe_allow_html=True)

st.title("📄 Ekstraksi Kartu Keluarga → Dapodik")

# ─── API KEY (dari Secrets atau input manual) ──────────────────
api_key = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else ""
if not api_key:
    api_key = st.text_input("Masukkan Google Gemini API Key:", type="password")

if not api_key:
    st.info("💡 Silakan masukkan API Key untuk mengaktifkan aplikasi.")
    st.stop()

genai.configure(api_key=api_key)

# ─── DAFTAR MODEL (terbaru dulu) ──────────────────────────────
MODELS = ['gemini-3.7-flash','gemini-3.6-flash','gemini-3.5-flash',
          'gemini-3.1-pro-preview','gemini-2.5-flash']

PROMPT = """
Kamu adalah sistem ekstraksi data presisi tinggi. Baca gambar Kartu Keluarga ini.
Ambil SEMUA nama anggota keluarga.

KELUARKAN DATA SEBAGAI CSV MURNI TANPA TEKS LAIN. Pemisah: titik koma (;).

Baris pertama header WAJIB persis:
No;Nama;NIK;Jenis Kelamin;Tempat Lahir;Tanggal Lahir;Nama Ayah;Nama Ibu;Alamat Lengkap;No KK;Paket / Kelas

Aturan:
- No: nomor urut mulai 1
- NIK: format ="angka" agar aman di Excel
- No KK: format ="angka" agar aman di Excel  
- Jenis Kelamin: Laki-laki / Perempuan
- Tempat Lahir: nama kota saja
- Tanggal Lahir: DD-MM-YYYY
- Alamat Lengkap: ambil dari kop KK, SAMA untuk semua baris dalam 1 KK
- No KK: ambil dari kop KK, SAMA untuk semua baris
- Paket / Kelas: kosongkan
"""

# ─── TAB UTAMA ────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📤 Ekstrak Foto KK", "📁 Gabung ke Excel Existing"])

# ════════════════════════════════════════════════════════════════
# TAB 1 — Ekstrak foto KK baru
# ════════════════════════════════════════════════════════════════
with tab1:
    uploaded_files = st.file_uploader(
        "Upload Foto KK (JPG/PNG, bisa pilih banyak sekaligus)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="uploader_new"
    )

    if uploaded_files and st.button("🚀 Mulai Ekstrak", key="btn_ekstrak"):
        progress = st.progress(0)
        status  = st.empty()
        all_dfs = []

        for i, f in enumerate(uploaded_files):
            status.info(f"⏳ Membaca file {i+1}/{len(uploaded_files)}: **{f.name}**")
            try:
                img_bytes = f.getvalue()
                img_part  = {"mime_type": f.type, "data": img_bytes}

                resp = None
                err  = None
                for m in MODELS:
                    try:
                        resp = genai.GenerativeModel(m).generate_content([PROMPT, img_part])
                        break
                    except Exception as e:
                        err = e

                if resp is None:
                    st.error(f"❌ Gagal: {f.name} — {err}")
                    continue

                raw = resp.text.strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1]
                    if raw.endswith("```"):
                        raw = raw.rsplit("\n", 1)[0]

                df = pd.read_csv(io.StringIO(raw), sep=";", dtype=str)
                df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
                all_dfs.append(df)

            except Exception as e:
                st.error(f"❌ Error saat memproses {f.name}: {e}")

            progress.progress((i + 1) / len(uploaded_files))

        status.success(f"✅ Selesai! {len(all_dfs)} file berhasil diekstrak.")

        if all_dfs:
            master = pd.concat(all_dfs, ignore_index=True)
            master["No"] = range(1, len(master) + 1)
            st.session_state["master_df"] = master

    # ── Tampilkan hasil & pilih baris ──────────────────────────
    if "master_df" in st.session_state:
        master = st.session_state["master_df"]

        st.markdown("---")
        st.markdown("### ✅ Langkah 1 — Pilih Baris yang Ingin Disimpan")
        st.caption("Klik tanda ✕ pada nama yang TIDAK ingin diambil.")

        label_list = [f"{r.get('No', i+1)}. {r.get('Nama','?')}" for i, (_, r) in enumerate(master.iterrows())]
        selected   = st.multiselect("Pilih nama:", label_list, default=label_list)

        if selected:
            idxs     = [label_list.index(l) for l in selected]
            filtered = master.iloc[idxs].copy()
            filtered["No"] = range(1, len(filtered) + 1)
        else:
            filtered = master.copy()

        st.markdown(f"**{len(filtered)} dari {len(master)} baris dipilih.**")

        st.markdown("### ✅ Langkah 2 — Koreksi Jika Ada Typo (klik 2× pada sel)")
        edited = st.data_editor(filtered, num_rows="dynamic", use_container_width=True)

        st.markdown("---")
        st.markdown("### ✅ Langkah 3 — Download")

        col1, col2 = st.columns(2)
        with col1:
            csv_out = edited.to_csv(index=False, sep=";")
            st.download_button("⬇️ Download CSV (untuk Add-on)", csv_out,
                               "Data_Siswa.csv", "text/csv")
        with col2:
            buf = io.BytesIO()
            edited.to_excel(buf, index=False, engine="openpyxl")
            st.download_button("⬇️ Download Excel (.xlsx)", buf.getvalue(),
                               "Data_Siswa.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ════════════════════════════════════════════════════════════════
# TAB 2 — Gabungkan ke file Excel yang sudah ada (Append)
# ════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 📂 Upload Excel yang Sudah Ada")
    st.caption("Data baru hasil ekstrak akan **ditambahkan di bawah** data lama secara otomatis.")

    existing_file = st.file_uploader("Upload file Excel (.xlsx) yang ingin ditambahi data:",
                                     type=["xlsx"], key="uploader_existing")

    st.markdown("### 📤 Upload Foto KK Baru untuk Ditambahkan")
    new_kk_files = st.file_uploader(
        "Upload Foto KK baru (JPG/PNG):",
        type=["jpg","jpeg","png"],
        accept_multiple_files=True,
        key="uploader_append"
    )

    if existing_file and new_kk_files and st.button("🔗 Gabungkan Data", key="btn_append"):
        # Baca Excel lama
        df_lama = pd.read_excel(existing_file, dtype=str)
        st.write(f"📊 Data lama: **{len(df_lama)} baris**")

        # Ekstrak KK baru
        progress2 = st.progress(0)
        status2   = st.empty()
        new_dfs   = []

        for i, f in enumerate(new_kk_files):
            status2.info(f"⏳ Membaca: {f.name}")
            try:
                img_bytes = f.getvalue()
                img_part  = {"mime_type": f.type, "data": img_bytes}

                resp = None
                err  = None
                for m in MODELS:
                    try:
                        resp = genai.GenerativeModel(m).generate_content([PROMPT, img_part])
                        break
                    except Exception as e:
                        err = e

                if resp is None:
                    st.error(f"❌ {f.name} — {err}")
                    continue

                raw = resp.text.strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1]
                    if raw.endswith("```"):
                        raw = raw.rsplit("\n", 1)[0]

                df = pd.read_csv(io.StringIO(raw), sep=";", dtype=str)
                df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
                new_dfs.append(df)

            except Exception as e:
                st.error(f"❌ Error: {e}")

            progress2.progress((i + 1) / len(new_kk_files))

        status2.success("✅ Ekstraksi selesai! Menggabungkan data...")

        if new_dfs:
            df_baru  = pd.concat(new_dfs, ignore_index=True)

            # Gabungkan lama + baru
            df_gabung = pd.concat([df_lama, df_baru], ignore_index=True)
            df_gabung["No"] = range(1, len(df_gabung) + 1)

            st.success(f"✅ Total data gabungan: **{len(df_gabung)} baris** ({len(df_lama)} lama + {len(df_baru)} baru)")

            st.markdown("### Preview & Pilih Baris")
            label_list2 = [f"{r.get('No',i+1)}. {r.get('Nama','?')}" for i, (_, r) in enumerate(df_gabung.iterrows())]
            selected2   = st.multiselect("Pilih baris:", label_list2, default=label_list2, key="ms2")

            if selected2:
                idxs2     = [label_list2.index(l) for l in selected2]
                filtered2 = df_gabung.iloc[idxs2].copy()
                filtered2["No"] = range(1, len(filtered2) + 1)
            else:
                filtered2 = df_gabung.copy()

            edited2 = st.data_editor(filtered2, num_rows="dynamic", use_container_width=True)

            col3, col4 = st.columns(2)
            with col3:
                csv2 = edited2.to_csv(index=False, sep=";")
                st.download_button("⬇️ Download CSV Gabungan", csv2,
                                   "Data_Siswa_Gabungan.csv", "text/csv", key="dl_csv2")
            with col4:
                buf2 = io.BytesIO()
                edited2.to_excel(buf2, index=False, engine="openpyxl")
                st.download_button("⬇️ Download Excel Gabungan (.xlsx)", buf2.getvalue(),
                                   "Data_Siswa_Gabungan.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   key="dl_xlsx2")

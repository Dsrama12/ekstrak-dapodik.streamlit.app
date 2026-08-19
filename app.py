import streamlit as st
import google.generativeai as genai
import pandas as pd
import io

st.set_page_config(page_title="Ekstrak KK Massal", page_icon="📄", layout="wide")

st.title("📄 Web Ekstraksi Kartu Keluarga (Massal & Lengkap)")
st.write("Versi terbaru ini mendukung **Multiple Upload (bisa upload 100+ Foto sekaligus)**, pemisahan kolom data yang lebih detail, dan fitur **Hapus Baris** untuk membuang nama orang tua yang tidak ingin dimasukkan.")

api_key = ""
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.text_input("Masukkan Google Gemini API Key:", type="password")

if api_key:
    genai.configure(api_key=api_key)
    
    st.markdown("---")
    # Multiple files uploader!
    uploaded_files = st.file_uploader("Upload Foto Kartu Keluarga (Bisa diselect banyak foto sekaligus!)", type=["jpg", "jpeg", "png", "pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        st.info(f"📁 {len(uploaded_files)} file terpilih siap diekstrak.")
        
        if st.button("Mulai Ekstrak Massal 🚀", use_container_width=True):
            
            # Placeholder untuk progres
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            all_data_frames = []
            
            for index, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Sedang membaca file {index+1} dari {len(uploaded_files)}: {uploaded_file.name}")
                
                try:
                    image_bytes = uploaded_file.getvalue()
                    
                    prompt = """
                    Kamu adalah sistem ekstraksi data presisi tinggi. Baca gambar Kartu Keluarga ini.
                    Ambil SEMUA nama anggota keluarga.
                    
                    SAYA MINTA FORMAT DATA WAJIB CSV MURNI DENGAN PEMISAH TITIK KOMA (;).
                    
                    Baris pertama wajib persis seperti ini:
                    No;Nama;NIK;Jenis Kelamin;Tempat Lahir;Tanggal Lahir;Nama Ayah;Nama Ibu;Alamat Lengkap;No KK;Paket / Kelas
                    
                    Instruksi Kolom:
                    - No: Urut 1, 2, dst
                    - Nama: Nama anggota keluarga
                    - NIK: Gunakan format ="1234" agar terbaca text di Excel
                    - Jenis Kelamin: Laki-laki / Perempuan
                    - Tempat Lahir: Nama kotanya saja (Pisahkan dari tanggal)
                    - Tanggal Lahir: Format YYYY-MM-DD atau DD-MM-YYYY
                    - Nama Ayah: Nama ayah
                    - Nama Ibu: Nama ibu kandung
                    - Alamat Lengkap: Ambil alamat rumah dari KOP ATAS Kartu Keluarga (misal Jl. Mawar No 10 RT 1 RW 2, Desa, Kec, dll). ALAMAT INI HARUS SAMA UNTUK SEMUA BARIS dalam 1 KK.
                    - No KK: Ambil Nomor Kartu Keluarga dari Kop atas. (Gunakan format ="1234"). INI HARUS SAMA UNTUK SEMUA BARIS.
                    - Paket / Kelas: Kosongkan
                    
                    Pastikan tabel bersih tanpa teks penjelasan tambahan.
                    """
                    
                    models_to_try = [
                        'gemini-3.7-flash', 
                        'gemini-3.6-flash',
                        'gemini-3.5-flash',
                        'gemini-3.1-pro-preview',
                        'gemini-2.5-flash'
                    ]
                    
                    response = None
                    last_error = None
                    
                    image_parts = [{"mime_type": uploaded_file.type, "data": image_bytes}]
                    
                    for model_name in models_to_try:
                        try:
                            model = genai.GenerativeModel(model_name)
                            response = model.generate_content([prompt, image_parts[0]])
                            break 
                        except Exception as e:
                            last_error = e
                            continue
                            
                    if response is None:
                        raise Exception(f"API Key error: {str(last_error)}")
                    
                    csv_data = response.text.strip()
                    if csv_data.startswith("```"):
                        csv_data = csv_data.split("\n", 1)[1]
                        if csv_data.endswith("```"):
                            csv_data = csv_data.rsplit("\n", 1)[0]
                            
                    # Konversi CSV string ke DataFrame pandas agar bisa dimanipulasi
                    df = pd.read_csv(io.StringIO(csv_data), sep=';', dtype=str)
                    
                    # Bersihkan spasi kosong
                    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
                    all_data_frames.append(df)
                    
                except Exception as e:
                    st.error(f"Gagal memproses {uploaded_file.name}: {str(e)}")
                
                # Update progress
                progress_bar.progress((index + 1) / len(uploaded_files))
            
            status_text.text("Ekstraksi selesai! Memproses tabel...")
            
            # Gabungkan semua data dari berbagai foto KK
            if all_data_frames:
                master_df = pd.concat(all_data_frames, ignore_index=True)
                
                # Update Nomor urut agar berkesinambungan 1..100
                master_df['No'] = range(1, len(master_df) + 1)
                
                # Simpan ke state session agar tidak hilang saat ngedit
                st.session_state['master_df'] = master_df
                st.success(f"✅ Berhasil mengekstrak total {len(master_df)} baris data dari {len(uploaded_files)} file!")
                
    if 'master_df' in st.session_state:
        st.markdown("### ✏️ Editor Tabel Data")
        st.write("Silakan centang kotak di sebelah kiri tabel lalu pencet **'Delete'** (logo tempat sampah di pojok kanan atas tabel) untuk **MENGHAPUS** orang tua atau data yang tidak Anda inginkan. Anda juga bisa klik dua kali pada teks jika ingin membetulkan tulisan (typo).")
        
        # Data Editor interaktif!
        edited_df = st.data_editor(st.session_state['master_df'], num_rows="dynamic", use_container_width=True)
        
        st.markdown("---")
        
        # Konversi kembali dataframe yang sudah diedit ke CSV semicolon
        csv_export = edited_df.to_csv(index=False, sep=';')
        
        st.download_button(
            label="⬇️ Download File CSV Final (Siap Masuk Add-on Dapodik!)",
            data=csv_export,
            file_name="Data_Siswa_Ekstrak_Massal.csv",
            mime="text/csv",
            use_container_width=True
        )

else:
    st.info("💡 Silakan masukkan API Key di setting atau di kotak di atas.")

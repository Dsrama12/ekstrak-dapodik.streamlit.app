import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Ekstrak KK ke CSV", page_icon="📄", layout="centered")

st.title("📄 Web Ekstraksi Kartu Keluarga (AI)")
st.write("Aplikasi web ini menggunakan kecerdasan buatan untuk membaca foto Kartu Keluarga dan secara otomatis menyusunnya menjadi file CSV yang siap dimasukkan ke Add-on Dapodik.")

api_key = st.text_input("Masukkan Google Gemini API Key:", type="password", help="Dapatkan API Key gratis di aistudio.google.com")

if api_key:
    genai.configure(api_key=api_key)
    
    st.markdown("---")
    uploaded_file = st.file_uploader("Upload Foto Kartu Keluarga (JPG/PNG)", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        image_bytes = uploaded_file.getvalue()
        
        st.image(image_bytes, caption="Preview Foto KK", use_container_width=True)
        
        if st.button("Mulai Ekstrak Data 🚀", use_container_width=True):
            with st.spinner('AI sedang membaca baris tabel Kartu Keluarga... Mohon tunggu.'):
                try:
                    prompt = """
                    Kamu adalah asisten ekstraksi data. Saya memberikan gambar Kartu Keluarga (KK).
                    Tugasmu adalah membaca tabel KK tersebut dan mengambil data anggota keluarga.
                    Kembalikan data DALAM FORMAT TEXT CSV SAJA, tanpa teks basa-basi apa pun.
                    Gunakan pemisah titik koma (;).
                    
                    Format Header wajib baris pertamanya persis seperti ini:
                    No;Nama;NIK;TTL;Paket / Kelas;Ayah/Ibu
                    
                    Keterangan pengisian baris selanjutnya:
                    - No: Nomor urut (1, 2, 3)
                    - Nama: Nama Lengkap
                    - NIK: ="NIK" (Tulis NIK dengan format ="1234567890123456" agar tidak rusak di Excel)
                    - TTL: Tempat Lahir, Tanggal Lahir (Misal: JAKARTA, 12-05-2010)
                    - Paket / Kelas: Kosongkan saja (jangan diisi apa-apa)
                    - Ayah/Ibu: Nama Ayah / Nama Ibu (Misal: BUDI / SITI)
                    
                    Pastikan membaca seluruh baris tabel dengan teliti dari atas ke bawah.
                    """
                    
                    image_parts = [
                        {
                            "mime_type": uploaded_file.type,
                            "data": image_bytes
                        }
                    ]
                    
                    # Menggunakan model Gemini generasi terbaru tahun 2026
                    models_to_try = [
                        'gemini-3.7-flash', 
                        'gemini-3.6-flash',
                        'gemini-3.5-flash',
                        'gemini-3.1-pro-preview',
                        'gemini-2.5-flash'
                    ]
                    
                    response = None
                    last_error = None
                    
                    for model_name in models_to_try:
                        try:
                            model = genai.GenerativeModel(model_name)
                            response = model.generate_content([prompt, image_parts[0]])
                            break # Berhasil!
                        except Exception as e:
                            last_error = e
                            continue
                            
                    if response is None:
                        raise Exception(f"Gagal mengakses model AI. Pesan asli: {str(last_error)}")
                    
                    csv_data = response.text.strip()
                    
                    if csv_data.startswith("```"):
                        csv_data = csv_data.split("\n", 1)[1]
                        if csv_data.endswith("```"):
                            csv_data = csv_data.rsplit("\n", 1)[0]
                    
                    st.success("✅ Berhasil diekstrak!")
                    st.text_area("Preview Hasil (Bisa diedit jika ada typo):", csv_data, height=200)
                    
                    st.download_button(
                        label="⬇️ Download File CSV",
                        data=csv_data,
                        file_name="Data_Siswa_Ekstrak.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    
                except Exception as e:
                    st.error(f"Terjadi kesalahan: {str(e)}")
else:
    st.info("💡 Silakan masukkan API Key terlebih dahulu untuk mengaktifkan aplikasi.")

from flask import Flask, render_template, request, redirect, url_for, flash
import cv2
import face_recognition
import mysql.connector
import json
import os
import numpy as np
import sys
import importlib.util
import threading

os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

spoofing_dir = os.path.join(parent_dir, 'Silent-Face-Anti-Spoofing-master')
if spoofing_dir not in sys.path:
    sys.path.insert(0, spoofing_dir)


def _load_spoofing_test():
    test_path = os.path.join(spoofing_dir, 'test.py')
    spec = importlib.util.spec_from_file_location('anti_spoof_test_module', test_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.test

spoofing_test = _load_spoofing_test()

SPOOFING_MODEL_DIR = os.path.join(spoofing_dir, 'resources', 'anti_spoof_models')
SPOOFING_DEVICE_ID = int(os.environ.get('SPOOFING_DEVICE_ID', '0'))
ML_LOCK = threading.Lock()


app = Flask(__name__, template_folder='web')
app.secret_key = "kunci_rahasia"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def run_liveness_check(bgr_image):
    """Jalankan anti-spoofing. Return 1 = wajah asli, selain itu = palsu/invalid."""
    with ML_LOCK:
        original_cwd = os.getcwd()
        try:
            os.chdir(spoofing_dir)
            return spoofing_test(bgr_image, SPOOFING_MODEL_DIR, SPOOFING_DEVICE_ID)
        finally:
            os.chdir(original_cwd)

# mySQL connect
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",         
        password="sip12345",         
        database="data_absen"
    )


# Flask Logic
@app.route('/')
def index():
    return render_template('index.html')

# reg.html
@app.route('/reg', methods=['GET', 'POST'])
def daftar():
    if request.method == 'POST':
        nim = request.form['nim']
        nama = request.form['nama']
        kelas = request.form['kelas']
        foto = request.files['foto']

        if not nim or not nama or not kelas or not foto:
            return "Semua field wajib diisi!"

        path_foto_temp = os.path.join(UPLOAD_FOLDER, f"temp_reg_{nim}.jpg")
        foto.save(path_foto_temp)

        bgr_img = cv2.imread(path_foto_temp)
        rgb_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
        wajah_terdeteksi = face_recognition.face_encodings(rgb_img)

        label = run_liveness_check(rgb_img)
        if label is None:
            os.remove(path_foto_temp)
            return render_template('result.html', title="Absen Gagal", message=f"Mahasiswa dengan NIM {nim} tidak terdaftar di database.", icon="fa-solid fa-user-xmark", icon_color="#ef4444", back_url="/absen", back_text="Coba Lagi")
        if label != 1:
            os.remove(path_foto_temp)
            return render_template('result.html', title="Registrasi Gagal", message="Wajah terdeteksi palsu (spoofing). Gunakan foto wajah asli langsung dari kamera.", icon="fa-solid fa-user-xmark", icon_color="#ef4444", back_url="/reg", back_text="Coba Lagi")


        os.remove(path_foto_temp)

        if len(wajah_terdeteksi) == 0:
            return render_template('result.html', title="Gagal Registrasi", message="Wajah tidak terdeteksi pada foto! Silakan coba foto lain.", icon="fa-solid fa-face-frown", icon_color="#ef4444", back_url="/reg", back_text="Coba Lagi")

        kode_wajah_string = json.dumps(wajah_terdeteksi[0].tolist())

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "INSERT INTO mahasiswa (nim, nama, kelas, kode_wajah) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (nim, nama, kelas, kode_wajah_string))
            conn.commit()
            cursor.close()
            conn.close()
            return render_template('result.html', title="Berhasil", message=f"Mahasiswa bernama {nama} ({nim}) telah terdaftar!", icon="fa-solid fa-circle-check", icon_color="#10b981", back_url="/", back_text="Kembali ke Menu")
        except mysql.connector.Error as err:
            return render_template('result.html', title="Error Database", message=str(err), icon="fa-solid fa-triangle-exclamation", icon_color="#f59e0b", back_url="/reg", back_text="Coba Lagi")

    return render_template('reg.html')


# absen.html
@app.route('/absen', methods=['GET', 'POST'])
def absen():
    if request.method == 'POST':
        nim = request.form['nim']
        foto = request.files['foto']

        if not nim or not foto:
            return "NIM dan Foto wajib diisi!"

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT nama, kode_wajah FROM mahasiswa WHERE nim = %s", (nim,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if not result:
            return f"Absen Gagal: Mahasiswa dengan NIM {nim} tidak terdaftar di database."

        nama_mahasiswa, kode_wajah_db_string = result
        
        master_encoding = np.array(json.loads(kode_wajah_db_string))

        path_foto_absen = os.path.join(UPLOAD_FOLDER, f"temp_abs_{nim}.jpg")
        foto.save(path_foto_absen)

        bgr_absen = cv2.imread(path_foto_absen)
        rgb_absen = cv2.cvtColor(bgr_absen, cv2.COLOR_BGR2RGB)
        wajah_absen_terdeteksi = face_recognition.face_encodings(rgb_absen)

        label = run_liveness_check(rgb_absen)
        if label is None:
            os.remove(path_foto_absen)
            return render_template('result.html', title="Absen Gagal", message=f"Mahasiswa dengan NIM {nim} tidak terdaftar di database.", icon="fa-solid fa-user-xmark", icon_color="#ef4444", back_url="/absen", back_text="Coba Lagi")
        if label != 1:
            os.remove(path_foto_absen)
            return render_template('result.html', title="Absen Gagal", message=f"Wajah terdeteksi palsu (spoofing). Gunakan foto wajah asli langsung dari kamera.", icon="fa-solid fa-user-xmark", icon_color="#ef4444", back_url="/absen", back_text="Coba Lagi")

        os.remove(path_foto_absen)

        if len(wajah_absen_terdeteksi) == 0:
            return render_template('result.html', title="Absen Gagal", message="Wajah tidak terdeteksi pada foto absen yang diunggah.", icon="fa-solid fa-face-frown", icon_color="#ef4444", back_url="/absen", back_text="Coba Lagi")

        absen_encoding = wajah_absen_terdeteksi[0]

        cocok = face_recognition.compare_faces([master_encoding], absen_encoding, tolerance=0.5)

        if cocok[0]:
            return render_template('result.html', title="Absen BERHASIL!", message=f"Selamat Datang, {nama_mahasiswa} ({nim}).", icon="fa-solid fa-circle-check", icon_color="#10b981", back_url="/", back_text="Kembali ke Menu")
        else:
            return render_template('result.html', title="Absen GAGAL", message=f"Wajah tidak cocok dengan pemilik NIM {nim}! Terdeteksi Joki.", icon="fa-solid fa-shield-halved", icon_color="#ef4444", back_url="/absen", back_text="Coba Lagi")

    return render_template('absen.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
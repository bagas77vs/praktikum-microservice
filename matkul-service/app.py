import os, time
import psycopg2
import psycopg2.extras
from flask import Flask, request, jsonify

app = Flask(__name__)

DB = dict(
    host=os.getenv("DB_HOST", "postgres-db"),
    port=os.getenv("DB_PORT", "5432"),
    dbname=os.getenv("DB_NAME", "matkul_db"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", "postgres"),
)

def get_conn():
    return psycopg2.connect(**DB)

def init_db(retries=30):
    for _ in range(retries):
        try:
            conn = get_conn()
            break
        except psycopg2.OperationalError:
            time.sleep(2)
    else:
        raise RuntimeError("Database tidak bisa dihubungi")
    with conn, conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS matkul (
                kode     VARCHAR(10) PRIMARY KEY,
                nama     VARCHAR(100) NOT NULL,
                sks      INT NOT NULL,
                semester INT NOT NULL
            )""")
        # Seeding (idempoten)
        cur.executemany(
            "INSERT INTO matkul (kode, nama, sks, semester) VALUES (%s,%s,%s,%s) "
            "ON CONFLICT (kode) DO NOTHING",
            [("IF301", "Sistem Terdistribusi", 3, 5),
             ("IF302", "Basis Data Lanjut", 3, 5),
             ("IF303", "Jaringan Komputer", 3, 5)])
    conn.close()

def query(sql, params=(), one=False, commit=False):
    conn = get_conn()
    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            if cur.description:
                return cur.fetchone() if one else cur.fetchall()
            return cur.rowcount
    finally:
        conn.close()

@app.get("/matkul")
def list_matkul():
    return jsonify(query("SELECT * FROM matkul ORDER BY kode")), 200

@app.post("/matkul")
def create_matkul():
    d = request.get_json(silent=True) or {}
    if not all(k in d and d[k] not in (None, "") for k in ("kode", "nama", "sks", "semester")):
        return jsonify(error="kode, nama, sks, semester wajib diisi"), 400
    try:
        int(d["sks"]); int(d["semester"])
    except (ValueError, TypeError):
        return jsonify(error="sks dan semester harus angka"), 400
    if query("SELECT 1 FROM matkul WHERE kode=%s", (d["kode"],), one=True):
        return jsonify(error="Kode mata kuliah sudah ada"), 409
    query("INSERT INTO matkul (kode,nama,sks,semester) VALUES (%s,%s,%s,%s)",
          (d["kode"], d["nama"], int(d["sks"]), int(d["semester"])))
    return jsonify(query("SELECT * FROM matkul WHERE kode=%s", (d["kode"],), one=True)), 201

@app.get("/matkul/<kode>")
def get_matkul(kode):
    row = query("SELECT * FROM matkul WHERE kode=%s", (kode,), one=True)
    if not row:
        return jsonify(error="Mata kuliah tidak ditemukan"), 404
    return jsonify(row), 200

@app.put("/matkul/<kode>")
def update_matkul(kode):
    if not query("SELECT 1 FROM matkul WHERE kode=%s", (kode,), one=True):
        return jsonify(error="Mata kuliah tidak ditemukan"), 404
    d = request.get_json(silent=True) or {}
    fields = {k: d[k] for k in ("nama", "sks", "semester") if k in d}
    if not fields:
        return jsonify(error="Tidak ada field yang diperbarui"), 400
    sets = ", ".join(f"{k}=%s" for k in fields)
    query(f"UPDATE matkul SET {sets} WHERE kode=%s", (*fields.values(), kode))
    return jsonify(query("SELECT * FROM matkul WHERE kode=%s", (kode,), one=True)), 200

@app.delete("/matkul/<kode>")
def delete_matkul(kode):
    if query("DELETE FROM matkul WHERE kode=%s", (kode,)) == 0:
        return jsonify(error="Mata kuliah tidak ditemukan"), 404
    return "", 204

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)

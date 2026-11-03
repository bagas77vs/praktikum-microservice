import os
import time
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
db = SQLAlchemy(app)


class MataKuliah(db.Model):
    __tablename__ = 'mata_kuliah'
    kode = db.Column(db.String(10), primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    sks = db.Column(db.Integer, nullable=False)
    semester = db.Column(db.Integer)

    def to_dict(self):
        return {'kode': self.kode, 'nama': self.nama,
                'sks': self.sks, 'semester': self.semester}


def error(pesan, kode):
    return jsonify({'error': pesan}), kode


@app.get('/matkul')
def list_mk():
    data = MataKuliah.query.order_by(MataKuliah.kode).all()
    return jsonify([m.to_dict() for m in data])


@app.post('/matkul')
def create_mk():
    d = request.get_json(silent=True) or {}
    if not d.get('kode') or not d.get('nama') or not d.get('sks'):
        return error('kode, nama, dan sks wajib diisi', 400)
    m = MataKuliah(kode=d['kode'], nama=d['nama'],
                   sks=d['sks'], semester=d.get('semester'))
    db.session.add(m)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error('kode mata kuliah sudah ada', 409)
    return jsonify(m.to_dict()), 201


@app.get('/matkul/<kode>')
def get_mk(kode):
    m = db.session.get(MataKuliah, kode)
    if not m:
        return error('mata kuliah tidak ditemukan', 404)
    return jsonify(m.to_dict())


@app.put('/matkul/<kode>')
def update_mk(kode):
    m = db.session.get(MataKuliah, kode)
    if not m:
        return error('mata kuliah tidak ditemukan', 404)
    d = request.get_json(silent=True) or {}
    m.nama = d.get('nama', m.nama)
    m.sks = d.get('sks', m.sks)
    m.semester = d.get('semester', m.semester)
    db.session.commit()
    return jsonify(m.to_dict())


@app.delete('/matkul/<kode>')
def delete_mk(kode):
    m = db.session.get(MataKuliah, kode)
    if not m:
        return error('mata kuliah tidak ditemukan', 404)
    db.session.delete(m)
    db.session.commit()
    return '', 204


def init_db():
    for _ in range(30):  # tunggu PostgreSQL siap
        try:
            with app.app_context():
                db.create_all()
                if MataKuliah.query.count() == 0:  # data awal
                    db.session.add_all([
                        MataKuliah(kode='IF301', nama='Sistem Terdistribusi', sks=3, semester=5),
                        MataKuliah(kode='IF302', nama='Basis Data Lanjut', sks=3, semester=5),
                        MataKuliah(kode='IF303', nama='Jaringan Komputer', sks=3, semester=4),
                    ])
                    db.session.commit()
            return
        except Exception as e:
            print('menunggu database...', e)
            time.sleep(2)
    raise RuntimeError('database tidak tersedia')


init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

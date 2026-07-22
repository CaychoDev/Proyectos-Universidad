import sqlite3
from datetime import datetime

class DBManager:
    def __init__(self, db_path="monitoreo.db"):
        self.conn = sqlite3.connect(db_path)
        self.crear_tablas()

    def crear_tablas(self):
        c = self.conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS Paciente (
                id_paciente INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                edad INTEGER,
                sexo TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS SesionMedicion (
                id_sesion INTEGER PRIMARY KEY AUTOINCREMENT,
                id_paciente INTEGER,
                fecha_hora TEXT NOT NULL,
                frecuencia_muestreo REAL,
                duracion REAL,
                FOREIGN KEY (id_paciente) REFERENCES Paciente(id_paciente)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS DatosProcesados (
                id_dato INTEGER PRIMARY KEY AUTOINCREMENT,
                id_sesion INTEGER NOT NULL,
                bpm REAL,
                ibi REAL,
                ptt REAL,
                ppg_promedio REAL,
                imu_promedio REAL,
                sys_predicha REAL,
                dia_predicha REAL,
                sys_real REAL,
                dia_real REAL,
                error_sys REAL,
                error_dia REAL,
                FOREIGN KEY (id_sesion) REFERENCES SesionMedicion(id_sesion)
            )
        ''')
        self.conn.commit()

    def insertar_sesion(self, id_paciente=None, fs=100.0, duracion=10.0):
        fecha = datetime.now().isoformat()
        c = self.conn.cursor()
        c.execute('''
            INSERT INTO SesionMedicion (id_paciente, fecha_hora, frecuencia_muestreo, duracion)
            VALUES (?, ?, ?, ?)
        ''', (id_paciente, fecha, fs, duracion))
        self.conn.commit()
        return c.lastrowid

    def insertar_datos(self, id_sesion, bpm, ibi, ptt, ppg_prom, imu_prom,
                       sys_pred, dia_pred, sys_real, dia_real):
        error_sys = abs(sys_real - sys_pred) if sys_real and sys_pred else 0.0
        error_dia = abs(dia_real - dia_pred) if dia_real and dia_pred else 0.0
        c = self.conn.cursor()
        c.execute('''
            INSERT INTO DatosProcesados (id_sesion, bpm, ibi, ptt, ppg_promedio, imu_promedio,
                                         sys_predicha, dia_predicha, sys_real, dia_real, error_sys, error_dia)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (id_sesion, bpm, ibi, ptt, ppg_prom, imu_prom, sys_pred, dia_pred, sys_real, dia_real, error_sys, error_dia))
        self.conn.commit()

    def contar_sesiones(self):
        return self.conn.execute("SELECT COUNT(*) FROM SesionMedicion").fetchone()[0]

    def cerrar(self):
        self.conn.close()
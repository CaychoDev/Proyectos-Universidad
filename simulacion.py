from gestor_db import DBManager

db = DBManager("monitoreo.db")

id_sesion = db.insertar_sesion(
    id_paciente=None,
    fs=100.0,
    duracion=10.0
)

db.insertar_datos(
    id_sesion=id_sesion,
    bpm=72.5,
    ibi=828.0,
    ptt=250,
    ppg_prom=25000.0,
    imu_prom=1.02,
    sys_pred=118,
    dia_pred=76,
    sys_real=120,
    dia_real=80
)

id_sesion2 = db.insertar_sesion(fs=100.0, duracion=10.0)
db.insertar_datos(
    id_sesion=id_sesion2,
    bpm=68.0,
    ibi=882.0,
    ptt=270,
    ppg_prom=24000.0,
    imu_prom=0.98,
    sys_pred=115,
    dia_pred=74,
    sys_real=118,
    dia_real=78
)

print(f"Se insertaron {db.contar_sesiones()} sesiones de prueba.")
db.cerrar()
print("Base de datos 'monitoreo.db' generada con éxito.")
print("Ábrela con DB Browser for SQLite.")
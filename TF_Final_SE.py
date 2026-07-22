import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import heartpy as hp
import numpy as np
import time
import csv
import sys
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt, find_peaks
from max30105 import MAX30105
from mpu6050 import mpu6050
import requests
import threading
import os
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont
from sklearn.ensemble import RandomForestRegressor
from gestor_db import DBManager

sys.stdout.reconfigure(encoding='utf-8', errors='ignore')


# 1. CAPA DE INTERFAZ Y DISPLAY (OLED)

class InterfazOLED:
    def __init__(self):
        try:
            self.i2c_oled = busio.I2C(board.SCL, board.SDA)
            self.oled = adafruit_ssd1306.SSD1306_I2C(128, 64, self.i2c_oled, addr=0x3C)
            self.oled.fill(0)
            self.oled.show()
            self.disponible = True
        except Exception as e:
            print(f"[OLED] No se pudo inicializar la pantalla: {e}")
            self.disponible = False

    def mostrar_datos(self, sbp, dbp, bpm, ptt):
        if not self.disponible:
            return
        self.oled.fill(0)
        image = Image.new("1", (self.oled.width, self.oled.height))
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
            
        draw.text((0, 0), f"SBP: {sbp:.0f} mmHg", font=font, fill=255)
        draw.text((0, 16), f"DBP: {dbp:.0f} mmHg", font=font, fill=255)
        draw.text((0, 32), f"BPM: {bpm:.0f} bpm", font=font, fill=255)
        draw.text((0, 48), f"PTT: {ptt} ms", font=font, fill=255)
        self.oled.image(image)
        self.oled.show()


# 2. CAPA DE INTELIGENCIA ARTIFICIAL Y MACHINE LEARNING

class PredictorPresion:
    def __init__(self, csv_path="dataset_presion.csv"):
        self.csv_path = csv_path
        self.model_sys = None
        self.model_dia = None
        self.X_mean = None
        self.X_std = None
        self.entrenado = False
        self.cargar_o_entrenar()

    def cargar_o_entrenar(self):
        if not os.path.exists(self.csv_path):
            print("[INFO] No se encuentra el archivo CSV. Se creará al guardar.")
            self.entrenado = False
            return

        try:
            datos_validos = []
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                lector = csv.reader(f)
                next(lector, None)
                for num_fila, fila in enumerate(lector, start=1):
                    if not fila or all(c.strip() == '' for c in fila):
                        continue
                    try:
                        valores_limpios = []
                        for valor in fila:
                            valor_limpio = valor.strip().replace('\r', '').replace('\n', '')
                            if valor_limpio == '':
                                raise ValueError("Campo vacío")
                            valores_limpios.append(float(valor_limpio))
                        if len(valores_limpios) == 5:
                            datos_validos.append(valores_limpios)
                    except ValueError:
                        continue

            if len(datos_validos) < 5:
                print(f"[INFO] Solo {len(datos_validos)} muestras válidas. Se necesita al menos 5.")
                self.entrenado = False
                return

            data = np.array(datos_validos)
            X = data[:, :3]
            y_sys = data[:, 3]
            y_dia = data[:, 4]

            self.X_mean = np.mean(X, axis=0)
            self.X_std = np.std(X, axis=0)
            self.X_std[self.X_std == 0] = 1e-6
            X_norm = (X - self.X_mean) / self.X_std

            self.model_sys = RandomForestRegressor(n_estimators=100, random_state=42)
            self.model_dia = RandomForestRegressor(n_estimators=100, random_state=42)
            self.model_sys.fit(X_norm, y_sys)
            self.model_dia.fit(X_norm, y_dia)
            self.entrenado = True
            print(f"[OK] Modelo entrenado con {len(datos_validos)} muestras válidas.")
        except Exception as e:
            print(f"[ERROR] No se pudo entrenar el modelo: {e}")
            self.entrenado = False

    def predecir(self, bpm, ptt, imu):
        if not self.entrenado or self.model_sys is None:
            return 0.0, 0.0
        try:
            X = np.array([[bpm, ptt, imu]])
            X_norm = (X - self.X_mean) / self.X_std
            sys_pred = self.model_sys.predict(X_norm)[0]
            dia_pred = self.model_dia.predict(X_norm)[0]
            return round(sys_pred), round(dia_pred)
        except Exception as e:
            print(f"[ERROR] Predicción fallida: {e}")
            return 0.0, 0.0

    def agregar_y_reentrenar(self, bpm, ptt, imu, sys_val, dia_val):
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([int(bpm), ptt, imu, sys_val, dia_val])
        print(f"[INFO] Nuevo dato guardado: BPM={int(bpm)}, PTT={ptt}, IMU={imu:.4f}, SYS={sys_val}, DIA={dia_val}")
        self.cargar_o_entrenar()


# 3. CAPA DE TELEMETRÍA IOT (ThingSpeak y Telegram)

class ClienteNube:
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://api.thingspeak.com/update"
        
    def enviar_asincrono(self, sbp, dbp, bpm, ptt):
        threading.Thread(target=self._enviar, args=(sbp, dbp, bpm, ptt), daemon=True).start()
        
    def _enviar(self, sbp, dbp, bpm, ptt):
        try:
            requests.post(self.url, data={"api_key": self.api_key, "field1": sbp, "field2": dbp, "field3": bpm, "field4": ptt}, timeout=5)
            print("\n[THINGSPEAK] Datos actualizados en la nube.")
        except Exception: pass

class NotificadorTelegram:
    def __init__(self, token, chat_ids):
        self.url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_ids = chat_ids
        
    def enviar_asincrono(self, mensaje):
        threading.Thread(target=self._enviar, args=(mensaje,), daemon=True).start()
        
    def _enviar(self, msg):
        for cid in self.chat_ids:
            try: requests.post(self.url, data={"chat_id": cid, "text": msg, "parse_mode": "Markdown"}, timeout=5)
            except: pass


# 4. CAPA DE HARDWARE Y PROCESAMIENTO (Sensores y DSP)

class HardwareBiomedico:
    def __init__(self):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        
        self.ads = ADS.ADS1115(self.i2c)
        self.ads.gain = 1
        self.chan = AnalogIn(self.ads, 0)

        self.sensor_ppg = MAX30105()
        self.sensor_ppg.setup()
        self.sensor_ppg.set_led_pulse_amplitude(1, 0x0C)
        self.sensor_ppg.set_led_pulse_amplitude(2, 0x0C)

        self.mpu = mpu6050(0x68)
        self.OFFSET_X = 0.4645
        self.OFFSET_Y = 0.0944
        self.OFFSET_Z = 0.3222

    def verificar_dedo(self):
        print("Verificando sensor PPG...")
        for i in range(10):
            samples = self.sensor_ppg.get_samples()
            if samples and len(samples) > 0:
                valor = samples[0]
                print(f"PPG: {valor}")
                if valor > 10000:
                    return True
            time.sleep(0.2)
        return False

    def capturar_datos(self, fs=100.0, duracion=10):
        num_muestras = int(fs * duracion)
        datos_ecg, datos_ppg, datos_imu = [], [], []

        for i in range(num_muestras):
            inicio = time.time()

            valor_ecg = self.chan.voltage
            datos_ecg.append(valor_ecg)

            samples = self.sensor_ppg.get_samples()
            if samples and len(samples) > 0:
                datos_ppg.append(samples[0])
            else:
                datos_ppg.append(0)

            data = self.mpu.get_accel_data()
            x = data['x'] - self.OFFSET_X
            y = data['y'] - self.OFFSET_Y
            z = data['z'] - self.OFFSET_Z
            imu_mag = np.sqrt(x**2 + y**2 + z**2)
            datos_imu.append(imu_mag)

            time.sleep(max(0, 1.0/fs - (time.time() - inicio)))
            
        return np.array(datos_ecg), np.array(datos_ppg), np.array(datos_imu)


class ProcesadorSenales:
    @staticmethod
    def filter_ecg(data, fs, highcut, lowcut=0.5):
        nyq = 0.5 * fs
        low = lowcut / nyq
        high = highcut / nyq
        b, a = butter(2, [low, high], btype='band')
        return filtfilt(b, a, data)

    def ejecutar_dsp(self, datos_ecg_crudo, datos_ppg, datos_imu, fs=100.0):
        datos_ecg = datos_ecg_crudo * -1
        media = np.mean(datos_ecg)
        datos_ecg = datos_ecg - media
        if np.max(np.abs(datos_ecg)) > 0:
            datos_ecg = datos_ecg / np.max(np.abs(datos_ecg))
        datos_ecg = self.filter_ecg(datos_ecg, fs, highcut=12)

        altura_minima = 0.5
        bpm, ibi, latidos_x2 = 0, 0, 0
        picos_ecg_filtrados = []

        try:
            wd, m = hp.process(datos_ecg, fs)
            picos_ecg = wd['peaklist']
            picos_filtrados = [p for p in picos_ecg if datos_ecg[p] > altura_minima]
            picos_ecg_filtrados = np.array(picos_filtrados)
            latidos = len(picos_ecg_filtrados)

            bpm_crudo = latidos * 6
            bpm = bpm_crudo * 2
            ibi = 60000 / bpm if bpm > 0 else 0
            latidos_x2 = latidos * 2

            print(f"DEBUG: HeartPy picos: {len(wd['peaklist'])}")
            print(f"DEBUG: Picos filtrados (> {altura_minima}): {latidos}")
            print(f"DEBUG: BPM crudo: {bpm_crudo}, BPM final: {bpm}")
        except Exception as e:
            print(f"Error en HeartPy: {e}")

        ppg_promedio = np.mean(datos_ppg) if len(datos_ppg) > 0 else 0
        imu_promedio = np.mean(datos_imu) if len(datos_imu) > 0 else 0
        picos_ppg = []
        ptt_ms = 0

        if len(picos_ecg_filtrados) > 0 and np.max(datos_ppg) > 10000:
            picos_ppg, _ = find_peaks(datos_ppg, height=np.max(datos_ppg)*0.1, distance=30)
            if len(picos_ppg) > 0:
                ptts = []
                for pico_r in picos_ecg_filtrados:
                    idx = np.argmin(np.abs(picos_ppg - pico_r))
                    pico_ppg_cercano = picos_ppg[idx]
                    if 0 < pico_ppg_cercano - pico_r < 50:
                        ptt = (pico_ppg_cercano - pico_r) * (1000 / fs)
                        ptts.append(ptt)
                if ptts:
                    ptt_ms = int(np.mean(ptts))
                    
        return bpm, ibi, latidos_x2, ptt_ms, ppg_promedio, imu_promedio, datos_ecg, picos_ecg_filtrados, picos_ppg


# 5. ORQUESTADOR CENTRAL

class OrquestadorSistema:
    def __init__(self, key_ts, token_tg, red_tg, db_path="monitoreo.db"):
        self.pantalla = InterfazOLED()
        self.predictor = PredictorPresion("dataset_presion.csv")
        self.telemetria = ClienteNube(key_ts)
        self.telegram = NotificadorTelegram(token_tg, red_tg)
        self.hardware = HardwareBiomedico()
        self.dsp = ProcesadorSenales()
        self.db = DBManager(db_path)
        self.fs = 100.0

    def renderizar_graficas(self, datos_ecg, datos_ppg, datos_imu, picos_ecg, picos_ppg, bpm, ptt_ms):
        altura_minima = 0.5
        plt.figure(figsize=(14, 10))

        plt.subplot(4, 1, 1)
        plt.plot(datos_ecg, label='ECG', color='blue')
        if len(picos_ecg) > 0:
            plt.plot(picos_ecg, datos_ecg[picos_ecg], 'rx', markersize=10, label='Picos R')
        plt.axhline(y=altura_minima, color='g', linestyle='--', label=f'Umbral {altura_minima}')
        plt.title(f'ECG - BPM: {bpm:.1f}')
        plt.xlabel('Muestras')
        plt.ylabel('Voltaje normalizado')
        plt.legend()
        plt.grid(True)

        plt.subplot(4, 1, 2)
        plt.plot(datos_ppg, label='PPG', color='red')
        if len(picos_ppg) > 0:
            plt.plot(picos_ppg, datos_ppg[picos_ppg], 'gx', markersize=10, label='Picos PPG')
        plt.title(f'PPG - PTT: {ptt_ms} ms')
        plt.xlabel('Muestras')
        plt.ylabel('Valor ADC')
        plt.legend()
        plt.grid(True)

        plt.subplot(4, 1, 3)
        plt.plot(datos_imu, label='IMU', color='green')
        plt.axhline(y=0.5, color='r', linestyle='--', label='Umbral')
        plt.title('IMU (MPU6050)')
        plt.xlabel('Muestras')
        plt.ylabel('Magnitud (m/s^2)')
        plt.legend()
        plt.grid(True)

        plt.subplot(4, 1, 4)
        plt.plot(datos_ecg * 0.5 + 0.5, label='ECG', color='blue', alpha=0.5)
        if np.max(datos_ppg) > 0:
            plt.plot(datos_ppg / np.max(datos_ppg) * 0.5, label='PPG', color='red', alpha=0.5)
        plt.title('ECG + PPG')
        plt.xlabel('Muestras')
        plt.ylabel('Normalizado')
        plt.legend()
        plt.grid(True)

        plt.tight_layout()
        plt.show()

    def iniciar(self):
        print("=== ECG + PPG + IMU + IA (Random Forest) ===\n")
        print("Presiona ENTER para iniciar...")
        input()

        print("Preparando sensores...")
        if not self.hardware.verificar_dedo():
            print("ERROR: No se detecta el dedo en el sensor PPG")
            print("Coloca el dedo correctamente y vuelve a intentar")
            sys.exit(1)
        else:
            print("Dedo detectado correctamente!")
            print("La captura comenzará en 3 segundos...")
            for i in range(3, 0, -1):
                print(f"{i}...")
                time.sleep(1)

        print("\nCAPTURANDO 10 SEGUNDOS! No te muevas...\n")
        datos_ecg_c, datos_ppg, datos_imu = self.hardware.capturar_datos(self.fs, 10)
        print("Captura completada.\n")

        bpm, ibi, lat_x2, ptt_ms, ppg_prom, imu_prom, ecg_fil, picos_ecg, picos_ppg = self.dsp.ejecutar_dsp(
            datos_ecg_c, datos_ppg, datos_imu, self.fs
        )

        print("=== RESULTADOS ===")
        print(f"BPM: {bpm:.1f}")
        print(f"IBI: {ibi:.0f} ms")
        print(f"Latidos: {lat_x2}")
        print(f"PTT: {ptt_ms} ms")
        print(f"PPG: {ppg_prom:.0f}")
        print(f"IMU: {imu_prom:.4f}")
        print("=================\n")

        if self.predictor.entrenado and bpm > 0 and ptt_ms > 0:
            sys_pred, dia_pred = self.predictor.predecir(bpm, ptt_ms, imu_prom)
            print(f"🔮 Estimación IA: Sistólica = {sys_pred} mmHg, Diastólica = {dia_pred} mmHg")
        else:
            sys_pred, dia_pred = 0, 0
            print("⚠️ Modelo no disponible o datos insuficientes. No se puede estimar.")

        self.pantalla.mostrar_datos(sys_pred, dia_pred, int(bpm), ptt_ms)
        self.renderizar_graficas(ecg_fil, datos_ppg, datos_imu, picos_ecg, picos_ppg, bpm, ptt_ms)

        sis_f, dia_f = 0, 0
        if bpm > 0 and ptt_ms > 0 and sys_pred > 0 and dia_pred > 0:
            print("\n--- Ingrese los valores reales para calcular el margen de error ---")
            sis = input("Presión sistólica real (mmHg): ")
            dia = input("Presión diastólica real (mmHg): ")
            try:
                sis_real = float(str(sis).strip())
                dia_real = float(str(dia).strip())
                
                error_sys = abs(sis_real - sys_pred)
                error_dia = abs(dia_real - dia_pred)
                
                print(f"\n📊 Margen de error (absoluto):")
                print(f"   Sistólica: {error_sys:.1f} mmHg")
                print(f"   Diastólica: {error_dia:.1f} mmHg")
                
                if error_sys > 5:
                    print("⚠️ ADVERTENCIA: Error en sistólica SUPERIOR a 5 mmHg")
                if error_dia > 5:
                    print("⚠️ ADVERTENCIA: Error en diastólica SUPERIOR a 5 mmHg")
                if error_sys <= 5 and error_dia <= 5:
                    print("✅ Ambos errores dentro del margen aceptable (≤ 5 mmHg)")

                self.predictor.agregar_y_reentrenar(bpm, ptt_ms, imu_prom, sis_real, dia_real)
                sis_f, dia_f = sis_real, dia_real
            except ValueError:
                print("❌ Valores inválidos. No se guardarán los datos reales.")
        else:
            print("Datos insuficientes para estimar presión. No se pedirán valores reales.")

        if bpm > 0 and ptt_ms > 0:
            sesion_id = self.db.insertar_sesion(fs=self.fs, duracion=10.0)
            self.db.insertar_datos(sesion_id, bpm, ibi, ptt_ms, ppg_prom, imu_prom,
                                   sys_pred, dia_pred, sis_f, dia_f)
            total = self.db.contar_sesiones()
            print(f"💾 Sesión registrada en la BD (ID: {sesion_id}). Total de sesiones: {total}")
        else:
            print("⚠️ Datos insuficientes. No se almacenó en la base de datos.")

        if sis_f > 0 and dia_f > 0:
            self.telemetria.enviar_asincrono(sis_f, dia_f, int(bpm), ptt_ms)
            if sis_f > 180 or dia_f > 120:
                print("⚠️ [EMERGENCIA] Presión crítica. Notificando a familiares por Telegram...")
                msg = (
                    "🚨 *ALERTA MÉDICA: CRISIS HIPERTENSIVA* 🚨\n\n"
                    f"🩸 *Presión:* {sis_f} / {dia_f} mmHg\n"
                    f"💓 *Frecuencia:* {int(bpm)} BPM\n\n"
                    f"⚠️ *Por favor, revise el panel clínico:*\n"
                    f"🔗 http://raspberrypi.alwaysdata.net/TF.html"
                )
                self.telegram.enviar_asincrono(msg)
            else:
                print(f"INFO: Valores {sis_f}/{dia_f} dentro de rangos normales.")
        else:
            print("No se enviaron datos por valores inválidos.")


if __name__ == "__main__":
    API_KEY_TS = "NHII34EX27A0A92C"
    TOKEN_TG = "8924871663:AAEA2lbWzFL6T0kxE3ilTgXKSKoF8yvzPs4"
    RED_EMERGENCIA = ["1044791294", "6091861349", "5448669518"]

    orquestador = OrquestadorSistema(API_KEY_TS, TOKEN_TG, RED_EMERGENCIA)
    orquestador.iniciar()
    orquestador.db.cerrar()

    print("\nFinalizado. Dando 3 segundos a la red para despachar los datos...")
    time.sleep(3)
    print("\nListo.")
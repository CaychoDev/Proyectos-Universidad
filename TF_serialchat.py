# -*- coding: utf-8 -*-
"""
Created on Thu Jul  2 15:53:03 2026

@author: Sebas Caycho

Comunicación por chat Serial

LEEME

El presente código describe el funcionamiento de una comunicación por chat serial entre dos usuarios ficticios, la interfaz fue a decisión
personal tomando un aspecto similar a la red social "Telegram" y a través de la unión de 2 puertos COM en la computadora se pude conectar
el chat donde se pueden enviar imágenes, emojis y mensajes de texto.

"""
import os
from datetime import datetime
import customtkinter as ctk
import serial
import serial.tools.list_ports
import threading

from tkinter import filedialog
from PIL import Image

class SerialChat(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.configure(fg_color="#17212B")
        
        self.title("SerialGram")
        self.geometry("+50+50")
        self.resizable(0, 0)
        
        ctk.set_appearance_mode("dark")
        # ---------------------- SERIAL PORT --------------------------
        self.serial = None
        self.conectado = False
        # Imágenes en memoria
        self.imagenes_chat = []
        # Nombre usuario
        self.nombre_remoto = "Remitente"
        # Nombre local
        self.nombre_local = "Yo"
        
        # ------------------------ FRAMES -----------------------------
        frm1 = ctk.CTkFrame(self, fg_color="#2AABEE",corner_radius=0)
        frm2 = ctk.CTkFrame(self, fg_color="#0E1621")
        frm3 = ctk.CTkFrame(self, fg_color="#17212B")
        frm1.pack(padx=5, pady=5, anchor='w', fill='x')
        frm2.pack(padx=5, pady=5, fill='both', expand=True)
        frm3.pack(padx=5, pady=5, fill='x')
        # Panel Emojis
        self.frmEmoji = ctk.CTkFrame(self, width=420, height=320, fg_color="#22303C", corner_radius=10)
        self.frmEmoji.place_forget()
        # Lista de Emojis
        emojis = [ "😁","😂","🤣","😊","👋",
                  "😍","😎","🤔","😭","😡",
                  "👍","👎","👏","❤️","🔥", ]
        # Función emojis
        fila = 0
        columna = 0
        for emoji in emojis:
            boton = ctk.CTkButton(self.frmEmoji, text=emoji, width=55, height=50, fg_color="#22303C", hover_color="#2AABEE", 
                                  font=("Segoe UI",26), command=lambda e=emoji: self.insertar_emoji(e))
            boton.grid(row=fila, column=columna, padx=3, pady=3)
            columna += 1
            if columna == 5:
                columna = 0
                fila += 1
        
        # ------------------------ FRAME 1 ----------------------------
        self.lblCOM = ctk.CTkLabel(frm1, text="Puerto COM:", text_color="#0D2363", font=("Segoe UI",14,"bold")) 
        self.cboPort = ctk.CTkOptionMenu(frm1, values=["Cargando puertos..."])
        self.lblSpace = ctk.CTkLabel(frm1, text="")
        self.btnConnect = ctk.CTkButton(frm1, text="Conectar", command=self.conectar_desconectar, fg_color="#1D0E73", hover_color="#1F6AA5")
        self.lblCOM.grid(row=0, column=0, padx=5, pady=5)
        self.cboPort.grid(row=0, column=1, padx=12, pady=5)
        self.lblSpace.grid(row=0,column=2, padx=30, pady=5)
        self.btnConnect.grid(row=0, column=3, padx=12, pady=5)
        
        # ------------------------ FRAME 2 ---------------------------
        #self.txtChat = ctk.CTkTextbox(frm2, width=440, height=420, wrap='word', state='disable', fg_color="#0E1621", border_width=0, text_color="white")
        #self.txtChat.grid(row=0, column=0, columnspan=3, padx=5, pady=5)
        
        # Se cambia por CTkScrollableFrame para burbuja de chat
        self.areaChat = ctk.CTkScrollableFrame(frm2,width=480,height=600,fg_color="#0E1621", corner_radius=0, scrollbar_fg_color="#0E1621",
                                               scrollbar_button_color="#15202E", scrollbar_button_hover_color="#229ED9")
        self.areaChat.grid(row=0,column=0,padx=5,pady=5,sticky="nsew")
        # ------------------------ FRAME 3 --------------------------
        #self.lblText = ctk.CTkLabel(frm3, text="Texto:")
        self.btnEmoji = ctk.CTkButton(frm3, text="😄", width=42,height=40,fg_color="#17212B"
                                      , hover_color="#22303C",font=("Fluent UI",24, "bold"), command=self.mostrar_panel_emojis)
        self.btnEmoji.grid(row=0,column=0,padx=4)
        self.btnImage = ctk.CTkButton(frm3, text="📷", width=42, height=40, fg_color="#17212B", hover_color="#22303C"
                                      , font=("Fluent UI",24), command=self.seleccionar_imagen)
        self.btnImage.grid(row=0, column=1, padx=3)
        self.inText = ctk.CTkEntry(frm3, width=250, state="disabled", fg_color="#22303C", border_width=0)
        self.inText.bind("<Return>", self.enviar_con_enter)
        self.btnSend = ctk.CTkButton(frm3, text="➤", font=("Fluent UI",21, "bold"), state='disable', command=self.enviar_mensaje)
        #self.lblText.grid(row=0, column=0, padx=5, pady=5)
        self.inText.grid(row=0, column=2, padx=5, pady=5)
        self.btnSend.grid(row=0, column=3, padx=3, pady=3)
       
        # Cargar puertos
        self.actualizar_puertos()
        # ------------- Control del boton "X" de la ventana -----------
        self.protocol("WM_DELETE_WINDOW", self.cerrar_puertos)

        # Inicio de chat
        self.agregar_mensaje("Usuario", "No es un contacto\nReside en: 🇵🇪")
        
        
    def actualizar_puertos(self):
        # Obtiene todos los puertos disponibles
        ports = serial.tools.list_ports.comports()
        # Lista el nombre del puerto
        lista_puertos = [port.device for port in ports]
        if not lista_puertos:
            lista_puertos = ["Sin puertos"]
            
        # Actualiza el Menu
        self.cboPort.configure(values=lista_puertos)

        # Selecciona automáticamente el primero
        self.cboPort.set(lista_puertos[0])
        
    def conectar_desconectar(self):
        # CONECTAR
        if not self.conectado:
            puerto = self.cboPort.get()

            try:
                print(f"Conectando a {puerto}...")
                self.serial = serial.Serial(
                    port=puerto,
                    baudrate=9600,
                    bytesize=8,
                    timeout=2,
                    stopbits=serial.STOPBITS_ONE
                )
                print("Conexión establecida")
                # Cambia el estado interno
                self.conectado = True
                self.th1 = threading.Thread(target=self.recibir_mensajes, daemon=True)
                self.th1.start()
                
                # Cambia el botón
                self.btnConnect.configure(text="Desconectar",fg_color="#A10000", hover_color="darkred")
                # Bloquea el selector de puerto
                self.cboPort.configure(state="disabled")
                # Habilita el envío
                self.inText.configure(state="normal")
                self.btnSend.configure(state="normal")
    
            except Exception as e:
                    print("No fue posible conectar.")
                    print(e)
                    
        # DESCONECTAR
        else:
            
            try:
                if self.serial is not None and self.serial.is_open:
                    self.serial.close()
                print("Puerto cerrado")
    
            except Exception as e:
                print(e)
    
            # Estado interno
            self.conectado = False
    
            # Botón vuelve a conectar
            self.btnConnect.configure(
                text="Conectar",
                fg_color=("#1D0E73", "#1D0E73"),
                hover_color=("gray70", "gray30")
            )
            # Vuelve a habilitar el selector
            self.cboPort.configure(state="normal")
            # Bloquea nuevamente el envío
            self.inText.delete(0, "end")
            self.inText.configure(state="disabled")
            self.btnSend.configure(state="disabled")
    
    def agregar_mensaje(self, remitente, mensaje):

       fila = ctk.CTkFrame(self.areaChat, fg_color="transparent")
       fila.pack(fill="x", padx=8, pady=5)
    
       # Alineamos por local y remitente
       if remitente == self.nombre_local:
           anchor = "e"
           colorBurbuja = "#1B2C63"
    
       elif remitente == "Usuario":
           anchor = "center"
           colorBurbuja = "#0F161C"
    
       else:
           anchor = "w"
           colorBurbuja = "#131C24"
    
       # Burbuja
       burbuja = ctk.CTkFrame(fila, fg_color=colorBurbuja,corner_radius=12)
       burbuja.pack(anchor=anchor, padx=8)
       # Remitente 
       lblNombre = ctk.CTkLabel(burbuja, text=remitente, font=("Segoe UI", 16, "bold"), text_color="white")
       lblNombre.pack(anchor="w", padx=10, pady=(6,0))
       # Mensaje
       if len(mensaje.strip()) <= 2:
            fuente = ("Segoe UI Emoji", 26)
       else:
            fuente = ("Segoe UI", 14)
       lblMensaje = ctk.CTkLabel(burbuja, text=mensaje, justify="left", wraplength=260, font=fuente)
       lblMensaje.pack(anchor="w", padx=10, pady=(2,2))
       
       # Hora
       lblHora = ctk.CTkLabel(burbuja, text=f"{datetime.now():%H:%M:%S}", font=("Segoe UI",10), text_color="#D0D0D0")
       lblHora.pack(anchor="e", padx=10, pady=(0,6))
    
       # Scroll automático
       self.after(50, lambda: self.areaChat._parent_canvas.yview_moveto(1.0))
       
    def enviar_mensaje(self):
        # Texto escrito
        mensaje = self.inText.get().strip()
    
        if mensaje == "":
            return
    
        try:
            data = (mensaje + "\n").encode("utf-8")
            # Envía por el puerto serial
            self.serial.write(data)
            # Muestra el mensaje en el chat
            self.agregar_mensaje(self.nombre_local, mensaje)
            self.inText.delete(0, "end")
            self.inText.focus()

        except Exception as e:
            print("Error al enviar:")
            print(e)
            
    def enviar_con_enter(self, event):
        self.enviar_mensaje()
            
    def recibir_mensajes(self):
        while self.conectado:
    
            try:
                if self.serial.in_waiting > 0:   
                    linea = self.serial.readline().decode(
                        "utf-8",
                        errors="ignore"
                    ).strip()
    
                    # Recibir imágenes
                    if linea.startswith("FILE:"):
                        partes = linea.split(":")
                        nombre = partes[1]
                        tamano = int(partes[2])
    
                        print(f"Recibiendo imagen: {nombre} ({tamano} bytes)")
                        
                        datos = b""

                        while len(datos) < tamano:
                            bloque = self.serial.read(min(1024, tamano - len(datos)))
                            datos += bloque
                    
                        # Guardar archivo recibido
                        nombre_guardado = "RECIBIDO_" + nombre
                    
                        with open(nombre_guardado, "wb") as f:
                            f.write(datos)
                        # Mostrar en chat 
                        self.after(0, self.mostrar_imagen_chat, nombre_guardado, self.nombre_remoto)
    
                    # Recibir mensajes
                    else:
                        self.agregar_mensaje(self.nombre_remoto, linea)
    
            except Exception:
                break
            
    def mostrar_panel_emojis(self):

        if self.frmEmoji.winfo_ismapped():
            self.frmEmoji.place_forget()
    
        else:
            self.frmEmoji.place(x=6, y=500)
                
    def insertar_emoji(self, emoji):

        self.inText.insert("end", emoji)
        self.inText.focus()
        self.frmEmoji.place_forget()
        
    def seleccionar_imagen(self):

        ruta = filedialog.askopenfilename(title="Seleccionar imagen", filetypes=[ ("Imágenes", "*.png *.jpg *.jpeg") ])
    
        if ruta == "":
            return
    
        self.mostrar_imagen_chat(ruta, "Yo")
        self.enviar_imagen(ruta)
        
    def mostrar_imagen_chat(self, ruta, remitente="Yo"):

        # Abrir imagen
        imagen = Image.open(ruta)
    
        # Definir proporción
        imagen.thumbnail((220,220))
    
        foto = ctk.CTkImage(light_image=imagen, dark_image=imagen, size=imagen.size)
    
        self.imagenes_chat.append(foto)
    
        # Contenedor
        fila = ctk.CTkFrame(self.areaChat, fg_color="transparent")
        fila.pack(fill="x", padx=8, pady=5)
        
        # Alineamos local remitente
        if remitente == self.nombre_local:
            anchor = "e"
            colorBurbuja = "#1B2C63"
        
        else:
            anchor = "w"
            colorBurbuja = "#131C24"
    
        # Burbuja
        burbuja = ctk.CTkFrame(fila, fg_color=colorBurbuja, corner_radius=10)
        burbuja.pack(anchor=anchor, padx=5)
    
        # Nombre
        lblNombre = ctk.CTkLabel(burbuja, text=remitente, font=("Segoe UI",13,"bold"))
        lblNombre.pack(anchor="w", padx=5, pady=(4,1))
    
        # Imagen
        lblImagen = ctk.CTkLabel(burbuja, text="", image=foto)
        lblImagen.pack(padx=2, pady=2)
    
        # Hora
        lblHora = ctk.CTkLabel(burbuja, text=f"{datetime.now():%H:%M:%S}", 
                               font=("Segoe UI",10), text_color="#D0D0D0")
        lblHora.pack(anchor="e", padx=5, pady=(1,3))
    
        self.after(50, lambda: self.areaChat._parent_canvas.yview_moveto(1.0))
        
    def enviar_imagen(self, ruta):

        try:
            nombre = os.path.basename(ruta)
            tamano = os.path.getsize(ruta)
            # Cabecera
            cabecera = f"FILE:{nombre}:{tamano}\n"
            self.serial.write(cabecera.encode("utf-8"))
            # Envía el archivo en bloques de 1024 bytes
            with open(ruta, "rb") as archivo:
        
                while True:
        
                    bloque = archivo.read(1024)
                    
                    if not bloque:
                        break
        
                    self.serial.write(bloque)
        
            print("Imagen enviada correctamente.")
        
        except Exception as e:
               print("Error al enviar imagen:")
               print(e)
    
    def cerrar_puertos(self):
        # Se cierran los puertos COM y la ventana de tkinter
        try:
            if self.serial is not None and self.serial.is_open:
                self.serial.close()
        except:
            pass

        self.destroy()
    
app = SerialChat()
app.mainloop()

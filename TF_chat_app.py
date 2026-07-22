# -*- coding: utf-8 -*-
"""
Created on Thu Jul  9 15:53:03 2026

@author: Sebas Caycho

Comunicación por chat TCP/IP

LEEME

En el presente código, extensión del trabajo previo con comunicación serial, se realiza una simulación de chat con dos o más usuarios 
a través de TCP/IP, para abrir el servidor acceder a Anaconda Prompt y realizar los siguientes comandos

# > python TF_chat_app.py   (SERVER)
# > python TF_chat_app.py <IP_SERVER> <PORT>   (CLIENTE sin nombre)
# > python TF_chat_app.py <IP_SERVER> <PORT> <username>  (CLIENTE)

"""
import os
import sys
from datetime import datetime
import customtkinter as ctk
import threading
import socket
from tkinter import filedialog
from PIL import Image

HOST = "127.0.0.1"
PORT = 5001
HEADER_SIZE = 10

# Servidor

class Server:
    def __init__(self):
        self.connections = []
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((HOST, PORT))
        self.sock.listen()

    def run(self):
        print(f"Servidor Iniciado en {HOST}:{PORT}\n")
        while True:
            try:
                conn, addr = self.sock.accept()
                self.connections.append(conn)
                threading.Thread(target=self.handler, args=(conn, addr), daemon=True).start()
                print(f"Cliente conectado: {addr[0]}:{addr[1]}")
            except:
                break

    def handler(self, conn, addr):
        while True:
            try:
                header = conn.recv(HEADER_SIZE)
                if not header:
                    break
                
                data_len = int(header.decode('utf-8').strip())
                
                data = b""
                while len(data) < data_len:
                    bloque = conn.recv(data_len - len(data))
                    if not bloque: break
                    data += bloque

                # Broadcast
                for connection in self.connections:
                    if connection != conn:
                        try:
                            connection.send(header + data)
                        except:
                            pass
            except:
                print(f"Cliente desconectado: {addr[0]}:{addr[1]}")
                if conn in self.connections:
                    self.connections.remove(conn)
                conn.close()
                break

# Interfaz 

class TCPChat(ctk.CTk):
    def __init__(self, addr="127.0.0.1", port=5001, username="User1"):
        super().__init__()
        self.username = username
        self.nombre_local = username
        
        self.configure(fg_color="#17212B")
        self.title("TCPGram")
        self.geometry("+50+50")
        self.resizable(0, 0)
        
        ctk.set_appearance_mode("dark")
        # ---------------------- CONEXIÓN --------------------------
        self.sock = None
        self.conectado = False
        
        self.imagenes_chat = []
        self.archivos_entrantes = {} 
        self.nombre_remoto = "Remitente"
        
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
                  "👍","👎","👏","💓","🔥", ]
        
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
        try:
            img_upc = Image.open("logo_upc.png")
            img_upc.thumbnail((35, 35), Image.Resampling.LANCZOS)
            self.logo_photo = ctk.CTkImage(light_image=img_upc, dark_image=img_upc, size=img_upc.size)
        except Exception:
            self.logo_photo = None

        self.lblIP = ctk.CTkLabel(frm1, text="IP:", text_color="#0D2363", font=("Segoe UI",14,"bold"))
        self.inIP = ctk.CTkEntry(frm1, width=100)
        self.inIP.insert(0, addr)
        
        self.lblPuerto = ctk.CTkLabel(frm1, text="Puerto:", text_color="#0D2363", font=("Segoe UI",14,"bold"))
        self.inPuerto = ctk.CTkEntry(frm1, width=60)
        self.inPuerto.insert(0, str(port))

        self.lblUser = ctk.CTkLabel(frm1, text="Usuario:", text_color="#0D2363", font=("Segoe UI",14,"bold"))
        self.inUser = ctk.CTkEntry(frm1, width=80)
        self.inUser.insert(0, self.username)
        
        self.btnConnect = ctk.CTkButton(frm1, text="Conectar", command=self.conectar_desconectar, fg_color="#1D0E73", hover_color="#1F6AA5", width=80)
        
        if self.logo_photo:
            self.lblLogo = ctk.CTkLabel(frm1, text="", image=self.logo_photo)
        else:
            self.lblLogo = ctk.CTkLabel(frm1, text="UPC", text_color="#0D2363", font=("Segoe UI",14,"bold"))

        self.lblIP.grid(row=0,column=0,padx=(5,2),pady=5)
        self.inIP.grid(row=0,column=1,padx=2)
        self.lblPuerto.grid(row=0,column=2,padx=(5,2))
        self.inPuerto.grid(row=0,column=3,padx=2)
        self.lblUser.grid(row=0,column=4,padx=(5,2))
        self.inUser.grid(row=0,column=5,padx=2)
        self.btnConnect.grid(row=0,column=6,padx=(15,5))
        self.lblLogo.grid(row=0, column=7, padx=(15,5))
        
        # ------------------------ FRAME 2 ---------------------------
        self.areaChat = ctk.CTkScrollableFrame(frm2,width=520,height=600,fg_color="#0E1621", corner_radius=0, scrollbar_fg_color="#0E1621",
                                               scrollbar_button_color="#15202E", scrollbar_button_hover_color="#229ED9")
        self.areaChat.grid(row=0,column=0,padx=5,pady=5,sticky="nsew")
        
        # ------------------------ FRAME 3 --------------------------
        self.btnEmoji = ctk.CTkButton(frm3, text="😄", width=42,height=40,fg_color="#17212B"
                                      , hover_color="#22303C",font=("Fluent UI",24, "bold"), command=self.mostrar_panel_emojis)
        self.btnEmoji.grid(row=0,column=0,padx=4)
        
        self.btnImage = ctk.CTkButton(frm3, text="📷", width=42, height=40, fg_color="#17212B", hover_color="#22303C"
                                      , font=("Fluent UI",24), command=self.seleccionar_imagen)
        self.btnImage.grid(row=0, column=1, padx=3)
        
        self.inText = ctk.CTkEntry(frm3, width=300, state="disabled", fg_color="#22303C", border_width=0)
        self.inText.bind("<Return>", self.enviar_con_enter)
        
        self.btnSend = ctk.CTkButton(frm3, text="➤", font=("Fluent UI",21, "bold"), state='disabled', command=self.enviar_mensaje)
        
        self.inText.grid(row=0, column=2, padx=5, pady=5)
        self.btnSend.grid(row=0, column=3, padx=3, pady=3)
       
        # ------------- Control del boton "X" de la ventana -----------
        self.protocol("WM_DELETE_WINDOW", self.cerrar_puertos)

        # Inicio de chat
        self.agregar_mensaje("Sistema", "¡Bienvenido a TCPGram 🤘!")
        
    def conectar_desconectar(self):
        if not self.conectado:
            try:
                ip = self.inIP.get()
                puerto = int(self.inPuerto.get())
                
                usuario = self.inUser.get().strip()
                if usuario == "":
                    usuario = "Anonimo"
                self.username = usuario
                self.nombre_local = usuario

                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((ip, puerto))
                
                self.conectado = True
                self.btnConnect.configure(text="Desconectar", fg_color="#A10000")
                
                self.inIP.configure(state="disabled")
                self.inPuerto.configure(state="disabled")
                self.inUser.configure(state="disabled")
                self.inText.configure(state="normal")
                self.btnSend.configure(state="normal")
                
                self.th1 = threading.Thread(target=self.recibir_mensajes, daemon=True)
                self.th1.start()
            except Exception as e:
                print(e)
        else:
            self.conectado = False
            try:
                self.sock.close()
            except:
                pass
            
            self.btnConnect.configure(text="Conectar", fg_color="#1D0E73")
            self.inIP.configure(state="normal")
            self.inPuerto.configure(state="normal")
            self.inUser.configure(state="normal")
            self.inText.configure(state="disabled")
            self.btnSend.configure(state="disabled")
            
    def recibir_mensajes(self):
        while self.conectado:
            try:
                header = self.sock.recv(HEADER_SIZE)
                if not header:
                    break
                    
                data_len = int(header.decode().strip())
                
                data = b""
                while len(data) < data_len:
                    bloque = self.sock.recv(data_len - len(data))
                    if not bloque: break
                    data += bloque
                
                if data.startswith(b"FILE_START|"):
                    partes = data.decode('utf-8').split('|', 3)
                    llave = f"{partes[1]}_{partes[2]}"
                    self.archivos_entrantes[llave] = b""
                    
                elif data.startswith(b"FILE_CHUNK|"):
                    partes = data.split(b'|', 3)
                    usuario = partes[1].decode('utf-8')
                    archivo = partes[2].decode('utf-8')
                    fragmento = partes[3]
                    llave = f"{usuario}_{archivo}"
                    if llave in self.archivos_entrantes:
                        self.archivos_entrantes[llave] += fragmento
                        
                elif data.startswith(b"FILE_END|"):
                    partes = data.decode('utf-8').split('|', 2)
                    usuario = partes[1]
                    archivo = partes[2]
                    llave = f"{usuario}_{archivo}"
                    
                    data_archivo = self.archivos_entrantes.pop(llave, None)
                    if data_archivo:
                        nombre_guardado = f"RECIBIDO_{archivo}"
                        with open(nombre_guardado, "wb") as f:
                            f.write(data_archivo)
                        self.after(0, self.mostrar_imagen_chat, nombre_guardado, usuario)
                else:
                    mensaje = data.decode("utf-8", errors="ignore")
                    if "> " in mensaje:
                        usuario, texto = mensaje.split("> ", 1)
                        if usuario != self.nombre_local:
                            self.after(0, self.agregar_mensaje, usuario, texto.strip())
            
            except Exception:
                break
        
        self.after(0, self.forzar_desconexion)

    def forzar_desconexion(self):
        if self.conectado:
            self.conectar_desconectar()
                
    def agregar_mensaje(self, remitente, mensaje):
       fila = ctk.CTkFrame(self.areaChat, fg_color="transparent")
       fila.pack(fill="x", padx=8, pady=5)
    
       if remitente == self.nombre_local:
           anchor = "e"
           colorBurbuja = "#1B2C63"
       elif remitente == "Sistema":
           anchor = "center"
           colorBurbuja = "#0F161C"
       else:
           anchor = "w"
           colorBurbuja = "#131C24"
    
       burbuja = ctk.CTkFrame(fila, fg_color=colorBurbuja,corner_radius=12)
       burbuja.pack(anchor=anchor, padx=8)
       
       lblNombre = ctk.CTkLabel(burbuja, text=remitente, font=("Segoe UI", 14, "bold"), text_color="#2AABEE")
       lblNombre.pack(anchor="w", padx=10, pady=(6,0))
       
       if len(mensaje.strip()) <= 2:
            fuente = ("Segoe UI Emoji", 26)
       else:
            fuente = ("Segoe UI", 16)
            
       lblMensaje = ctk.CTkLabel(burbuja, text=mensaje, justify="left", wraplength=260, font=fuente)
       lblMensaje.pack(anchor="w", padx=10, pady=(2,2))
       
       lblHora = ctk.CTkLabel(burbuja, text=f"{datetime.now():%H:%M:%S}", font=("Segoe UI",11), text_color="#D0D0D0")
       lblHora.pack(anchor="e", padx=10, pady=(0,6))
    
       self.after(50, lambda: self.areaChat._parent_canvas.yview_moveto(1.0))
       
    def enviar_mensaje(self):
        mensaje = self.inText.get().strip()
        if mensaje == "":
            return
            
        try:
            data = f"{self.username}> {mensaje}\n".encode("utf-8")
            data_len = len(data)
            header = f"{data_len:<{HEADER_SIZE}}".encode("utf-8")
            
            self.sock.send(header + data)
            self.agregar_mensaje(self.nombre_local, mensaje)
            
            self.inText.delete(0, "end")
            self.inText.focus()
        except Exception as e:
            print(e)
            
    def enviar_con_enter(self, event):
        self.enviar_mensaje()
            
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
        ruta = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[("Imágenes","*.png *.jpg *.jpeg")]
        )
        if ruta == "":
            return
            
        self.mostrar_imagen_chat(ruta, self.nombre_local)
        self.enviar_imagen(ruta)
        
    def mostrar_imagen_chat(self, ruta, remitente="Yo"):
        imagen = Image.open(ruta)
        imagen.thumbnail((220,220))
        foto = ctk.CTkImage(light_image=imagen, dark_image=imagen, size=imagen.size)
        self.imagenes_chat.append(foto)
        
        fila = ctk.CTkFrame(self.areaChat, fg_color="transparent")
        fila.pack(fill="x", padx=8, pady=5)
        
        if remitente == self.nombre_local:
            anchor = "e"
            colorBurbuja = "#1B2C63"
        else:
            anchor = "w"
            colorBurbuja = "#131C24"
    
        burbuja = ctk.CTkFrame(fila, fg_color=colorBurbuja, corner_radius=10)
        burbuja.pack(anchor=anchor, padx=5)
    
        lblNombre = ctk.CTkLabel(burbuja, text=remitente, font=("Segoe UI",13,"bold"), text_color="#2AABEE")
        lblNombre.pack(anchor="w", padx=5, pady=(4,1))
    
        lblImagen = ctk.CTkLabel(burbuja, text="", image=foto)
        lblImagen.pack(padx=2, pady=2)
    
        lblHora = ctk.CTkLabel(burbuja, text=f"{datetime.now():%H:%M:%S}", 
                               font=("Segoe UI",10), text_color="#D0D0D0")
        lblHora.pack(anchor="e", padx=5, pady=(1,3))
    
        self.after(50, lambda: self.areaChat._parent_canvas.yview_moveto(1.0))
        
    def enviar_imagen(self, ruta):
        try:
            nombre = os.path.basename(ruta)
            
            p_start = f"FILE_START|{self.username}|{nombre}|0".encode('utf-8')
            self.sock.send(f"{len(p_start):<{HEADER_SIZE}}".encode('utf-8') + p_start)
            
            with open(ruta, "rb") as archivo:
                while True:
                    bloque = archivo.read(1024)
                    if not bloque: break
                    
                    p_chunk = f"FILE_CHUNK|{self.username}|{nombre}|".encode('utf-8') + bloque
                    self.sock.send(f"{len(p_chunk):<{HEADER_SIZE}}".encode('utf-8') + p_chunk)
                    
            p_end = f"FILE_END|{self.username}|{nombre}".encode('utf-8')
            self.sock.send(f"{len(p_end):<{HEADER_SIZE}}".encode('utf-8') + p_end)
            
        except Exception as e:
            print(e)
    
    def cerrar_puertos(self):
        try:
            if self.sock:
                self.sock.close()
        except:
            pass
        self.destroy()

def main():
    if len(sys.argv) == 1:
        server = Server()
        server.run()
    elif len(sys.argv) == 3:
        app = TCPChat(sys.argv[1], int(sys.argv[2]))
        app.after(200, app.conectar_desconectar)
        app.mainloop()
    elif len(sys.argv) == 4:
        app = TCPChat(sys.argv[1], int(sys.argv[2]), sys.argv[3])
        app.after(200, app.conectar_desconectar)
        app.mainloop()
    else:
        print("Error en la ejecucion del script")

# > python TF_chat_app.py   (SERVER)
# > python TF_chat_app.py <IP_SERVER> <PORT>   (CLIENTE)
# > python TF_chat_app.py <IP_SERVER> <PORT> <username>  (CLIENTE)

if __name__ == "__main__":
    main()
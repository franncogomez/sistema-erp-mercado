import customtkinter as ctk
import rsa
import json
import sys
import subprocess
import os
from tkinter import messagebox
from datetime import datetime

# 🔗 IMPORTAMOS TUS MÓDULOS
from ui_caja import VentanaCaja
from ui_stock import VentanaStock
from ui_arqueo import VentanaArqueo
from ui_libreta import VentanaLibreta 

# ==========================================
# 🔒 BARRERA DE SEGURIDAD CRIPTOGRÁFICA
# ==========================================
def verificar_licencia():
    ruta_base = os.path.dirname(os.path.abspath(__file__))
    ruta_lic = os.path.join(ruta_base, "licencia.key")
    ruta_pub = os.path.join(ruta_base, "llave_publica.pem")

    try:
        comando = ['powershell.exe', '-Command', '(Get-CimInstance -Class Win32_ComputerSystemProduct).UUID']
        CREATE_NO_WINDOW = 0x08000000 
        uuid_pc = subprocess.check_output(comando, text=True, stderr=subprocess.STDOUT, creationflags=CREATE_NO_WINDOW).strip()

        with open(ruta_lic, "r") as arch_lic:
            paquete = json.load(arch_lic)
            
        datos_licencia = paquete["datos"]
        firma_hex = paquete["firma"]
        
        with open(ruta_pub, "rb") as arch_pub:
            llave_publica = rsa.PublicKey.load_pkcs1(arch_pub.read())
            
        mensaje = json.dumps(datos_licencia).encode('utf8')
        firma_bytes = bytes.fromhex(firma_hex)
        
        rsa.verify(mensaje, firma_bytes, llave_publica)
        
        if datos_licencia["uuid_placa"] != uuid_pc:
            raise Exception("Licencia no válida para esta computadora.\nEl hardware no coincide.")
            
        fecha_vencimiento = datetime.strptime(datos_licencia["vencimiento"], "%Y-%m-%d").date()
        fecha_actual = datetime.now().date()
        
        if fecha_actual > fecha_vencimiento:
            raise Exception(f"El servicio expiró el {fecha_vencimiento}.\nPor favor, contacte a Franco para renovar.")
            
    except FileNotFoundError:
        messagebox.showerror("⛔ Sistema Bloqueado", "No se encontró la licencia o la llave pública en la carpeta del sistema.")
        sys.exit()
    except rsa.VerificationError:
        messagebox.showerror("⛔ Sistema Bloqueado", "El archivo de licencia ha sido adulterado o corrompido.")
        sys.exit()
    except Exception as e:
        messagebox.showerror("⛔ Sistema Bloqueado", str(e))
        sys.exit()

# ==========================================
# 🎨 CONFIGURACIÓN VISUAL BÁSICA
# ==========================================
ctk.set_default_color_theme("blue") 
ctk.set_appearance_mode("dark") 

class MenuPrincipal(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sistema Mercado ERP - Panel de Control")
        self.geometry("600x550") # 🔧 Agrandamos 50px para que entre el nuevo botón
        self.resizable(False, False)

        # --- TÍTULO ---
        self.lbl_titulo = ctk.CTkLabel(self, text="🏪 Sistema Mercado", font=("Roboto", 28, "bold"))
        self.lbl_titulo.pack(pady=(30, 10))
        
        self.lbl_subtitulo = ctk.CTkLabel(self, text="Panel de Administración General", font=("Roboto", 14), text_color="gray")
        self.lbl_subtitulo.pack(pady=(0, 30))

        self.frame_botones = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_botones.pack(pady=10)

        # --- BOTONES DEL SISTEMA ---
        self.btn_caja = ctk.CTkButton(self.frame_botones, text="🛒 Abrir Caja Registradora", width=250, height=45, font=("Roboto", 15, "bold"), command=self.abrir_caja)
        self.btn_caja.pack(pady=10)

        self.btn_stock = ctk.CTkButton(self.frame_botones, text="📦 Gestionar Stock", width=250, height=45, font=("Roboto", 15, "bold"), command=self.gestionar_stock)
        self.btn_stock.pack(pady=10)
        
        #  NUEVO BOTÓN PARA LOS FIADOS
        self.btn_libreta = ctk.CTkButton(self.frame_botones, text="📓 Libreta de Fiados", fg_color="#1E88E5", hover_color="#1565C0", width=250, height=45, font=("Roboto", 15, "bold"), command=self.abrir_libreta)
        self.btn_libreta.pack(pady=10)

        self.btn_arqueo = ctk.CTkButton(self.frame_botones, text="🏦 Arqueo y Cierres", width=250, height=45, font=("Roboto", 15, "bold"), command=self.abrir_arqueo)
        self.btn_arqueo.pack(pady=10)

        # --- SWITCH MODO OSCURO / CLARO ---
        self.switch_tema = ctk.CTkSwitch(self, text="🌙 Modo Oscuro", command=self.cambiar_tema, font=("Roboto", 12))
        self.switch_tema.pack(side="bottom", pady=20)
        self.switch_tema.select()

    # ==========================================
    # ⚙️ LÓGICA DE INTERFAZ
    # ==========================================
    def cambiar_tema(self):
        if self.switch_tema.get() == 1:
            ctk.set_appearance_mode("dark")
            self.switch_tema.configure(text="🌙 Modo Oscuro")
        else:
            ctk.set_appearance_mode("light")
            self.switch_tema.configure(text="☀️ Modo Claro")

    # ==========================================
    # 🚀 LANZADORES DE VENTANAS
    # ==========================================
    def abrir_caja(self):
        VentanaCaja(self)

    def gestionar_stock(self):
        VentanaStock(self)
        
    def abrir_libreta(self):
        VentanaLibreta(self)

    def abrir_arqueo(self):
        VentanaArqueo(self)

# ==========================================
# 🏁 ARRANQUE DEL SISTEMA COMPLETO
# ==========================================
if __name__ == "__main__":
    verificar_licencia()
    app = MenuPrincipal()
    app.mainloop()

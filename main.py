import customtkinter as ctk
import rsa
import json
import sys
import subprocess
import os
import sqlite3
import socket
import threading
import uvicorn
import qrcode
import shutil
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from tkinter import messagebox
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

# 🔗 IMPORTAMOS los MÓDULOS DE INTERFAZ
from ui_caja import VentanaCaja
from ui_stock import VentanaStock
from ui_arqueo import VentanaArqueo
from ui_gastos import VentanaGastos
from ui_ajustes import VentanaAjustes
from ui_libreta import VentanaLibreta
from ui_estadisticas import VentanaEstadisticas

# ==========================================
# 🪄 FÓRMULA MÁGICA DE RUTAS
# ==========================================
def obtener_ruta_db():
    if getattr(sys, 'frozen', False):
        directorio_base = os.path.dirname(sys.executable)
    else:
        directorio_base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(directorio_base, "sistema_mercado.db")

# ==========================================
# 🛠️ MIGRACIONES AUTOMÁTICAS Y ROLES
# ==========================================
def inicializar_base_datos():
    ruta_db = obtener_ruta_db()
    conexion = sqlite3.connect(ruta_db)
    cursor = conexion.cursor()
    
    # Tabla de Configuración
    cursor.execute('''CREATE TABLE IF NOT EXISTS config_local (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        razon_social TEXT, nombre_fantasia TEXT, cuit TEXT, direccion TEXT, 
        telefono TEXT, instagram TEXT, condicion_iva TEXT, iibb TEXT, inicio_actividades TEXT
    )''')
    
    try: cursor.execute("ALTER TABLE config_local ADD COLUMN instagram TEXT")
    except: pass 
    try: cursor.execute("ALTER TABLE config_local ADD COLUMN mensaje_ticket TEXT")
    except: pass 
    try: cursor.execute("ALTER TABLE config_local ADD COLUMN mp_alias TEXT")
    except: pass 
    try: cursor.execute("ALTER TABLE config_local ADD COLUMN mp_token TEXT")
    except: pass 

    # 🛠️ ASEGURAMOS LA TABLA DE VENTAS E INYECTAMOS COLUMNAS FISCALES
    cursor.execute('''CREATE TABLE IF NOT EXISTS ventas (
        id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha DATETIME,
        total REAL,
        medio_pago TEXT
    )''')
    
    try: cursor.execute("ALTER TABLE ventas ADD COLUMN tipo_comprobante TEXT DEFAULT 'TICKET NO FISCAL'")
    except: pass
    try: cursor.execute("ALTER TABLE ventas ADD COLUMN nro_comprobante INTEGER DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE ventas ADD COLUMN cae TEXT DEFAULT ''")
    except: pass
    try: cursor.execute("ALTER TABLE ventas ADD COLUMN doc_cliente TEXT DEFAULT ''")
    except: pass

    # 🛠️ NUEVA TABLA: DETALLE DE VENTAS (Para estadísticas avanzadas y reimpresión)
    cursor.execute('''CREATE TABLE IF NOT EXISTS ventas_detalle (
        id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
        id_venta INTEGER,
        codigo_producto TEXT,
        nombre_producto TEXT,
        cantidad REAL,
        precio_unitario REAL,
        subtotal REAL,
        FOREIGN KEY(id_venta) REFERENCES ventas(id_venta)
    )''')

    # 🛡️ Tabla de Usuarios y Roles
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE,
        pin TEXT,
        rol TEXT
    )''')
    
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO usuarios (nombre, pin, rol) VALUES ('ADMIN (Dueño)', '1234', 'MASTER')")
        cursor.execute("INSERT INTO usuarios (nombre, pin, rol) VALUES ('CAJA 1 (Empleado)', '0000', 'CAJERO')")
        
    conexion.commit()
    conexion.close()

# ==========================================
#  MÓDULO DE VALIDACIÓN (Supabase)
# ==========================================
ruta_base = os.path.dirname(obtener_ruta_db())
load_dotenv(os.path.join(ruta_base, ".env"))

URL_NUBE = os.getenv("SUPABASE_URL")
LLAVE_API = os.getenv("SUPABASE_KEY")

def gestionar_licencia_local(nueva_fecha=None):
    ruta_db = obtener_ruta_db()
    conexion = sqlite3.connect(ruta_db)
    cursor = conexion.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS licencia_local (id INTEGER PRIMARY KEY, vencimiento TEXT)''')
    
    if nueva_fecha:
        cursor.execute("DELETE FROM licencia_local")
        cursor.execute("INSERT INTO licencia_local (vencimiento) VALUES (?)", (nueva_fecha,))
        conexion.commit()
        resultado = nueva_fecha
    else:
        cursor.execute("SELECT vencimiento FROM licencia_local LIMIT 1")
        fila = cursor.fetchone()
        resultado = fila[0] if fila else None
        
    conexion.close()
    return resultado

def obtener_id_hardware():
    import winreg
    try:
        registry = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
        key = winreg.OpenKey(registry, r"SOFTWARE\Microsoft\Cryptography")
        machine_guid, _ = winreg.QueryValueEx(key, "MachineGuid")
        winreg.CloseKey(key)
        return machine_guid
    except Exception:
        import subprocess
        return subprocess.check_output('wmic csproduct get uuid').decode().split('\n')[1].strip()

def verificar_licencia_nube():
    id_pc = str(obtener_id_hardware()) 
    fecha_evaluar = None
    origen_dato = "NUBE ☁️"
    
    try:
        print(f"📡 Verificando licencia en internet para: {id_pc}")
        supabase: Client = create_client(URL_NUBE, LLAVE_API)
        respuesta = supabase.table("clientes").select("*").eq("id_hardware", id_pc).execute()
        
        if len(respuesta.data) > 0:
            fecha_evaluar = respuesta.data[0]["fecha_vencimiento"]
            gestionar_licencia_local(fecha_evaluar)
        else:
            try:
                import tkinter as tk
                r = tk.Tk()
                r.withdraw()
                r.clipboard_clear()
                r.clipboard_append(id_pc)
                r.update()
                r.destroy()
            except: pass
            
            mensaje = (
                f"🛑 Este equipo no está autorizado para usar Sistema Mercado.\n\n"
                f"✅ Tu CÓDIGO DE EQUIPO ya fue COPIADO automáticamente a tu portapapeles.\n\n"
                f"Pegalo en un mensaje de WhatsApp a Franco para activar el sistema:\n\n"
                f"👉 ID: {id_pc}"
            )
            messagebox.showerror("Equipo No Registrado", mensaje)
            return False
            
    except Exception as e:
        print("⚠️ Sin internet. Buscando licencia de respaldo en la base de datos local...")
        fecha_evaluar = gestionar_licencia_local()
        origen_dato = "LOCAL (Offline) 💾"
        
    if not fecha_evaluar:
        print("🛑 Error crítico: No hay licencias registradas ni en la nube ni localmente.")
        return False
        
    hoy = datetime.now().date()
    vencimiento_dt = datetime.strptime(fecha_evaluar, "%Y-%m-%d").date()
    dias_restantes = (vencimiento_dt - hoy).days
    fecha_corte_definitivo = vencimiento_dt + timedelta(days=2) 
    
    print(f"✅ Licencia cargada desde {origen_dato} | Vence: {fecha_evaluar}")
    
    if dias_restantes > 5:
        return True
    elif 0 <= dias_restantes <= 5:
        messagebox.showinfo("Aviso de Suscripción", f"¡Hola! 👋 Te recuerdo que tu suscripción vence en {dias_restantes} días ({fecha_evaluar}).")
        return True
    elif hoy > vencimiento_dt and hoy <= fecha_corte_definitivo:
        messagebox.showwarning("Atención - Período de Gracia", f"⚠ Tu suscripción venció el {fecha_evaluar}.\nTenes 48hs de gracia.")
        return True
    elif hoy > fecha_corte_definitivo:
        messagebox.showerror("Sistema Bloqueado", "🛑 El período de gracia finalizó. Sistema bloqueado por falta de pago.")
        return False

# ==========================================
# 🔐 PANTALLA DE LOGIN INICIAL
# ==========================================
class VentanaLogin(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("🔐 Control de Acceso")
        self.geometry("380x420")
        self.resizable(False, False)

        self.protocol("WM_DELETE_WINDOW", self.cancelar_ingreso)
        self.attributes("-topmost", True)

        ctk.CTkLabel(self, text="🏪 Sistema Mercado", font=("Roboto", 24, "bold")).pack(pady=(30, 10))
        ctk.CTkLabel(self, text="Seleccione su usuario:", font=("Roboto", 14)).pack(pady=(10, 5))

        self.usuarios_db = self.obtener_usuarios()
        nombres = [u['nombre'] for u in self.usuarios_db]

        self.combo_usuarios = ctk.CTkComboBox(self, values=nombres, width=250, font=("Roboto", 14), state="readonly")
        self.combo_usuarios.pack(pady=5)
        
        ctk.CTkLabel(self, text="PIN de Seguridad:", font=("Roboto", 14)).pack(pady=(15, 5))
        self.entry_pin = ctk.CTkEntry(self, width=250, font=("Roboto", 18), show="*")
        self.entry_pin.pack(pady=5)
        self.entry_pin.bind("<Return>", lambda event: self.autenticar())
        self.entry_pin.focus()

        self.btn_ingresar = ctk.CTkButton(self, text="Ingresar al Sistema", fg_color="#2FA572", hover_color="#238259", height=45, width=250, font=("Roboto", 16, "bold"), command=self.autenticar)
        self.btn_ingresar.pack(pady=30)

    def cancelar_ingreso(self):
        self.parent.destroy()
        sys.exit()

    def obtener_usuarios(self):
        try:
            conexion = sqlite3.connect(obtener_ruta_db())
            cursor = conexion.cursor()
            cursor.execute("SELECT nombre, pin, rol FROM usuarios ORDER BY rol DESC")
            resultados = [{"nombre": f[0], "pin": f[1], "rol": f[2]} for f in cursor.fetchall()]
            conexion.close()
            return resultados
        except:
            return []

    def autenticar(self):
        usuario_elegido = self.combo_usuarios.get()
        pin_ingresado = self.entry_pin.get().strip()

        for u in self.usuarios_db:
            if u['nombre'] == usuario_elegido:
                if u['pin'] == pin_ingresado:
                    self.parent.usuario_activo = u['nombre']
                    self.parent.rol_activo = u['rol']
                    
                    self.parent.configurar_por_rol()
                    self.parent.deiconify() 
                    self.destroy()          
                    return
                else:
                    messagebox.showerror("❌ Acceso Denegado", "El PIN ingresado es incorrecto.")
                    self.entry_pin.delete(0, 'end')
                    return

# ==========================================
# 🎨 3. INTERFAZ GRÁFICA PRINCIPAL
# ==========================================
ctk.set_default_color_theme("blue") 
ctk.set_appearance_mode("dark") 

class MenuPrincipal(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.withdraw()
        
        self.usuario_activo = None
        self.rol_activo = None

        self.title("Sistema Mercado ERP - Panel de Control")
        self.geometry("750x600") 
        self.resizable(False, False)

        self.lbl_titulo = ctk.CTkLabel(self, text="🏪 Sistema Mercado", font=("Roboto", 28, "bold"))
        self.lbl_titulo.pack(pady=(20, 5))
        
        self.lbl_subtitulo = ctk.CTkLabel(self, text="Cargando...", font=("Roboto", 14), text_color="gray")
        self.lbl_subtitulo.pack(pady=(0, 20))

        self.frame_central = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_central.pack(fill="both", expand=True, padx=40)
        
        self.frame_central.grid_columnconfigure(0, weight=1)
        self.frame_central.grid_columnconfigure(1, weight=1)

        self.btn_caja = ctk.CTkButton(self.frame_central, text="🛒 Abrir Caja Registradora", height=50, font=("Roboto", 15, "bold"), command=self.abrir_caja)
        self.btn_caja.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.btn_stock = ctk.CTkButton(self.frame_central, text="📦 Gestionar Stock", height=50, font=("Roboto", 15, "bold"), command=self.gestionar_stock)
        self.btn_stock.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        self.btn_libreta = ctk.CTkButton(self.frame_central, text="📓 Libreta de Fiados", fg_color="#1E88E5", hover_color="#1565C0", height=50, font=("Roboto", 15, "bold"), command=self.abrir_libreta)
        self.btn_libreta.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.btn_arqueo = ctk.CTkButton(self.frame_central, text="🏦 Arqueo y Cierres", height=50, font=("Roboto", 15, "bold"), command=self.abrir_arqueo)
        self.btn_arqueo.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        self.btn_gastos = ctk.CTkButton(self.frame_central, text="💸 Pagos del Día", height=50, font=("Roboto", 15, "bold"), fg_color="#D32F2F", hover_color="#B71C1C", command=lambda: VentanaGastos(self))
        self.btn_gastos.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.btn_estadisticas = ctk.CTkButton(self.frame_central, text="📊 Historial y Estadísticas", height=50, font=("Roboto", 15, "bold"), fg_color="#F59E0B", hover_color="#D97706", command=lambda: VentanaEstadisticas(self))
        self.btn_estadisticas.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        self.btn_ajustes = ctk.CTkButton(self.frame_central, text="⚙️ Ajustes del Local", fg_color="#546E7A", hover_color="#455A64", height=50, font=("Roboto", 15, "bold"), command=self.abrir_ajustes)
        self.btn_ajustes.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        
        self.btn_backup = ctk.CTkButton(self.frame_central, text="📦 Crear Copia de Seguridad", fg_color="#4CAF50", hover_color="#388E3C", height=50, font=("Roboto", 15, "bold"), command=self.hacer_backup)
        self.btn_backup.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

        self.switch_tema = ctk.CTkSwitch(self, text="🌙 Modo Oscuro", command=self.cambiar_tema, font=("Roboto", 12))
        self.switch_tema.pack(side="bottom", pady=20)
        self.switch_tema.select()
        
        self.after(200, self.mostrar_login)

    def mostrar_login(self):
        login = VentanaLogin(self)
        self.wait_window(login)

    def configurar_por_rol(self):
        self.lbl_subtitulo.configure(text=f"Sesión iniciada por: {self.usuario_activo} | Nivel: {self.rol_activo}")
        self.after(500, self.verificar_backup_diario)

        # 🛡️ RESTRICCIONES PARA CAJEROS
        if self.rol_activo == "CAJERO":
            color_bloqueado = "#333333"
            self.btn_stock.configure(state="disabled", fg_color=color_bloqueado)
            self.btn_estadisticas.configure(state="disabled", fg_color=color_bloqueado)
            self.btn_ajustes.configure(state="disabled", fg_color=color_bloqueado)
            self.btn_backup.configure(state="disabled", fg_color=color_bloqueado)
            
        # 🤖 ASISTENTE AUTOMÁTICO DE FIN DE MES PARA EL DUEÑO (Solo si hay facturas)
        elif self.rol_activo in ["MASTER", "ADMINISTRADOR"]:
            hoy = datetime.now()
            # Si estamos entre el día 1 y 5 del mes...
            if 1 <= hoy.day <= 5:
                # Esperamos 1 segundo para que cargue la interfaz antes de revisar
                self.after(1000, self.verificar_y_recordar_contador)

    def verificar_y_recordar_contador(self):
        hoy = datetime.now()
        primer_dia_mes_actual = hoy.replace(day=1)
        mes_anterior = primer_dia_mes_actual - timedelta(days=1)
        str_mes_anterior = mes_anterior.strftime("%Y-%m")
        
        try:
            conexion = sqlite3.connect(obtener_ruta_db())
            cursor = conexion.cursor()
            
            # Revisamos si emitió FACTURAS AFIP el mes pasado
            cursor.execute("""
                SELECT COUNT(*) FROM ventas 
                WHERE strftime('%Y-%m', fecha) = ? 
                AND tipo_comprobante != 'TICKET NO FISCAL' 
                AND tipo_comprobante IS NOT NULL
            """, (str_mes_anterior,))
            
            cantidad_fiscales = cursor.fetchone()[0]
            conexion.close()
            
            # MAGIA: Solo avisamos si realmente facturó en blanco
            if cantidad_fiscales > 0:
                mensaje = (
                    f"¡Hola {self.usuario_activo}! 👋\n\n"
                    f"Noté que emitiste {cantidad_fiscales} facturas de AFIP en {mes_anterior.strftime('%B')} (el mes pasado).\n"
                    f"¿Querés exportar el Excel ahora para enviárselo al contador?\n\n"
                    f"(Podés hacerlo más tarde desde la sección Estadísticas)"
                )
                if messagebox.askyesno("📊 Cierre de Mes Fiscal", mensaje, parent=self):
                    VentanaEstadisticas(self).abrir_menu_exportar()
        except Exception:
            pass # Si falla por algún motivo (ej. base recién creada), se queda en silencio y no molesta.

    def verificar_backup_diario(self):
        """Crea un backup diario y mantiene solo los últimos 30 días rotativos"""
        try:
            ruta_original = obtener_ruta_db()
            carpeta_backups = os.path.join(os.path.dirname(ruta_original), "backups")
            os.makedirs(carpeta_backups, exist_ok=True)
            
            # 1. Armamos el nombre del backup de HOY
            hoy_str = datetime.now().strftime("%Y%m%d")
            nombre_backup_hoy = f"respaldo_auto_{hoy_str}.db"
            ruta_copia_hoy = os.path.join(carpeta_backups, nombre_backup_hoy)
            
            # 2. Si no existe el backup de hoy, lo creamos
            if not os.path.exists(ruta_copia_hoy):
                import shutil
                shutil.copy2(ruta_original, ruta_copia_hoy)
                print(f"✅ Backup diario automático creado: {nombre_backup_hoy}")
                
            # 3. Mantenimiento Rotativo (Limpieza a 30 días)
            # Buscamos todos los archivos que empiecen con 'respaldo_auto_'
            backups = [f for f in os.listdir(carpeta_backups) if f.startswith('respaldo_auto_') and f.endswith('.db')]
            
            if len(backups) > 30:
                # Ordenamos alfabéticamente al revés (los más nuevos arriba, porque el nombre tiene el año/mes/día)
                backups.sort(reverse=True)
                
                # Agarramos del 31 en adelante y los borramos sin piedad
                backups_a_borrar = backups[30:]
                for backup_viejo in backups_a_borrar:
                    ruta_borrar = os.path.join(carpeta_backups, backup_viejo)
                    os.remove(ruta_borrar)
                    print(f"🗑️ Backup viejo eliminado por rotación: {backup_viejo}")
                    
        except Exception as e:
            print(f"Aviso - Error en rutina de backup diario: {e}")

    def hacer_backup(self):
        """Botón manual que además educa al usuario sobre la nube"""
        ruta_original = obtener_ruta_db()
        directorio_base = os.path.dirname(ruta_original)
        
        if not os.path.exists(ruta_original):
            messagebox.showerror("Error", "No se encontró la base de datos para respaldar.")
            return

        carpeta_backups = os.path.join(directorio_base, "backups")
        os.makedirs(carpeta_backups, exist_ok=True)
        
        fecha_hora = datetime.now().strftime("%Y%m%d_%H%M")
        nombre_copia = f"respaldo_manual_{fecha_hora}.db"
        ruta_copia = os.path.join(carpeta_backups, nombre_copia)
        
        try:
            shutil.copy2(ruta_original, ruta_copia)
            
            # Mensaje educativo con emojis para que sea amigable
            mensaje = (
                f"✅ Copia de seguridad guardada con éxito.\n\n"
                f"📁 Archivo: {nombre_copia}\n"
                f"📍 Ubicación: Carpeta 'backups'\n\n"
                f"☁️ CONSEJO DE SEGURIDAD:\n"
                f"Te sugerimos guardar este archivo en tu Google Drive, "
                f"enviártelo por WhatsApp, o guardarlo en un Pendrive. \n\n"
                f"¡Si a tu computadora le pasa algo, con ese archivo recuperás todo tu negocio!"
            )
            messagebox.showinfo("Respaldo Exitoso", mensaje)
            
            # Opcional: Le abrimos la carpeta de Windows para que vea el archivo y lo pueda arrastrar a Drive
            os.startfile(carpeta_backups)
            
        except Exception as e:
            messagebox.showerror("❌ Error", f"No se pudo crear el backup:\n{e}")

    def cambiar_tema(self):
        if self.switch_tema.get() == 1:
            ctk.set_appearance_mode("dark")
            self.switch_tema.configure(text="🌙 Modo Oscuro")
        else:
            ctk.set_appearance_mode("light")
            self.switch_tema.configure(text="☀️ Modo Claro")

    def abrir_caja(self):
        ruta_db = obtener_ruta_db()
        conexion = sqlite3.connect(ruta_db)
        cursor = conexion.cursor()
        
        try:
            cursor.execute("SELECT tipo_operacion FROM arqueo_caja ORDER BY id_arqueo DESC LIMIT 1")
            registro = cursor.fetchone()
            
            if registro and ("apertura" in registro[0].lower() or "abrir" in registro[0].lower()):
                VentanaCaja(self)
            else:
                messagebox.showwarning("Caja Cerrada", "⛔ No podés ingresar a la registradora.\nPrimero debés realizar la 'Apertura de Caja' desde la sección de Arqueo.")
        except sqlite3.OperationalError:
            messagebox.showwarning("Caja Cerrada", "⛔ El sistema es nuevo y la caja está cerrada.\nPor favor, realizá tu primera 'Apertura de Caja' en la sección de Arqueo.")
        except Exception as e:
            VentanaCaja(self) 
        finally:
            conexion.close()
            
    def gestionar_stock(self): VentanaStock(self)
    def abrir_libreta(self): VentanaLibreta(self)
    def abrir_arqueo(self): VentanaArqueo(self)
    def abrir_ajustes(self): VentanaAjustes(self)
    
if __name__ == "__main__":
    print("🔐 Iniciando control de licencias en la nube...")
    
    inicializar_base_datos()
    estado_licencia = verificar_licencia_nube()
    
    if estado_licencia == True or estado_licencia == "OFFLINE":
        app = MenuPrincipal()
        app.mainloop()
    else:
        print("🛑 ACCESO DENEGADO.")
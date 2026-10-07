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
    
    # 🛡️ Tabla de Usuarios y Roles
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE,
        pin TEXT,
        rol TEXT
    )''')
    
    # Si no hay usuarios (instalación nueva), creamos los 2 por defecto
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO usuarios (nombre, pin, rol) VALUES ('ADMIN (Dueño)', '1234', 'ADMINISTRADOR')")
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
            mensaje = (
                f"🛑 Este equipo no está autorizado para usar Sistema Mercado.\n\n"
                f"Para activar tu licencia, enviale este código de hardware a Franco:\n\n"
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
# 📡 MOTOR DEL SERVIDOR MÓVIL (FASTAPI)
# ==========================================
api = FastAPI()

@api.get("/", response_class=HTMLResponse)
def panel_movil():
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Control de Stock</title>
        <style>
            body { font-family: Arial, sans-serif; background: #1E293B; color: white; padding: 20px; }
            h2 { text-align: center; color: #38BDF8; }
            input { width: 100%; padding: 15px; font-size: 18px; margin-bottom: 20px; box-sizing: border-box; border-radius: 8px; border: none; text-align: center; }
            .producto { background: #334155; padding: 15px; margin-bottom: 10px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
            .producto h3 { margin: 0 0 10px 0; font-size: 20px; }
            .stock { font-size: 18px; margin-bottom: 15px; color: #94A3B8;}
            .stock b { color: #34D399; font-size: 22px;}
            .botones { display: flex; justify-content: space-between; }
            button { padding: 15px 30px; font-size: 20px; font-weight: bold; color: white; border: none; border-radius: 8px; cursor: pointer; width: 45%; }
            .btn-restar { background: #EF4444; }
            .btn-sumar { background: #10B981; }
        </style>
    </head>
    <body>
        <h2>📦 Buscador por Código</h2>
        <input type="number" id="buscador" placeholder="Últimos números del código..." onkeyup="buscar()">
        <div id="resultados"></div>

        <script>
            async function buscar() {
                const query = document.getElementById("buscador").value;
                if (query.length < 3) return; 
                
                const res = await fetch(`/api/buscar/${query}`);
                const data = await res.json();
                
                const div = document.getElementById("resultados");
                div.innerHTML = "";
                
                data.forEach(prod => {
                    div.innerHTML += `
                        <div class="producto">
                            <h3>${prod.nombre}</h3>
                            <div class="stock">Stock actual: <b>${prod.stock}</b></div>
                            <div class="botones">
                                <button class="btn-restar" onclick="actualizar('${prod.codigo}', -1)">- 1</button>
                                <button class="btn-sumar" onclick="actualizar('${prod.codigo}', 1)">+ 1</button>
                            </div>
                        </div>
                    `;
                });
            }

            async function actualizar(codigo, variacion) {
                await fetch('/api/actualizar', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({codigo: codigo, variacion: variacion})
                });
                buscar(); 
            }
        </script>
    </body>
    </html>
    """
    return html_content

@api.get("/api/buscar/{query}")
def buscar_producto(query: str):
    ruta_db = obtener_ruta_db()
    conexion = sqlite3.connect(ruta_db, check_same_thread=False)
    cursor = conexion.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("SELECT codigo_barras, nombre, stock FROM productos WHERE codigo_barras LIKE ? LIMIT 10", (f'%{query}',))
    resultados = [{"codigo": f[0], "nombre": f[1], "stock": f[2]} for f in cursor.fetchall()]
    conexion.close()
    return resultados

@api.post("/api/actualizar")
async def actualizar_stock(request: Request):
    datos = await request.json()
    codigo_limpio = str(datos["codigo"]).strip()
    variacion = int(datos["variacion"])
    
    ruta_db = obtener_ruta_db()
    conexion = sqlite3.connect(ruta_db, check_same_thread=False)
    cursor = conexion.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("UPDATE productos SET stock = CAST(stock AS INTEGER) + ? WHERE codigo_barras = ?", (variacion, codigo_limpio))
    conexion.commit()
    conexion.close()
    return {"status": "ok"}

def arrancar_servidor():
    uvicorn.run(api, host="0.0.0.0", port=8000, log_level="error")

def obtener_ip_local():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception: IP = '127.0.0.1'
    finally: s.close()
    return IP

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
        
        # Obliga al usuario a interactuar con el Login (si lo cierra con la X, se apaga el sistema)
        self.protocol("WM_DELETE_WINDOW", self.cancelar_ingreso)
        self.attributes("-topmost", True)

        # UI
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

    def obtener_usuarios(self):
        try:
            conexion = sqlite3.connect(obtener_ruta_db())
            cursor = conexion.cursor()
            # Mostramos primero a los cajeros y luego al administrador
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
                    # ¡ÉXITO! Guardamos los datos en el menú principal
                    self.parent.usuario_activo = u['nombre']
                    self.parent.rol_activo = u['rol']
                    
                    self.parent.configurar_por_rol()
                    self.parent.deiconify() # Mostramos el menú principal
                    self.destroy()          # Destruimos el Login
                    return
                else:
                    messagebox.showerror("❌ Acceso Denegado", "El PIN ingresado es incorrecto.")
                    self.entry_pin.delete(0, 'end')
                    return
                    
    def cancelar_ingreso(self):
        import sys
        sys.exit() # Si cierran el login con la cruz, apaga el programa entero

# ==========================================
# 🎨 3. INTERFAZ GRÁFICA PRINCIPAL
# ==========================================
ctk.set_default_color_theme("blue") 
ctk.set_appearance_mode("dark") 

class MenuPrincipal(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Ocultamos el Menú apenas arranca para mostrar el Login
        self.withdraw()
        
        self.usuario_activo = None
        self.rol_activo = None

        self.title("Sistema Mercado ERP - Panel de Control")
        self.geometry("750x700")
        self.resizable(False, False)

        # (Diseño del Menú Principal - Igual que antes)
        self.lbl_titulo = ctk.CTkLabel(self, text="🏪 Sistema Mercado", font=("Roboto", 28, "bold"))
        self.lbl_titulo.pack(pady=(20, 5))
        
        # Renglón dinámico para saludar al usuario
        self.lbl_subtitulo = ctk.CTkLabel(self, text="Cargando...", font=("Roboto", 14), text_color="gray")
        self.lbl_subtitulo.pack(pady=(0, 20))

        self.frame_central = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_central.pack(fill="both", expand=True, padx=20)

        # ----- COLUMNA IZQUIERDA: BOTONES -----
        self.col_botones = ctk.CTkFrame(self.frame_central, fg_color="transparent")
        self.col_botones.pack(side="left", fill="y", padx=20)

        self.btn_caja = ctk.CTkButton(self.col_botones, text="🛒 Abrir Caja Registradora", width=250, height=45, font=("Roboto", 15, "bold"), command=self.abrir_caja)
        self.btn_caja.pack(pady=7)

        self.btn_stock = ctk.CTkButton(self.col_botones, text="📦 Gestionar Stock", width=250, height=45, font=("Roboto", 15, "bold"), command=self.gestionar_stock)
        self.btn_stock.pack(pady=7)
        
        self.btn_libreta = ctk.CTkButton(self.col_botones, text="📓 Libreta de Fiados", fg_color="#1E88E5", hover_color="#1565C0", width=250, height=45, font=("Roboto", 15, "bold"), command=self.abrir_libreta)
        self.btn_libreta.pack(pady=7)

        self.btn_arqueo = ctk.CTkButton(self.col_botones, text="🏦 Arqueo y Cierres", width=250, height=45, font=("Roboto", 15, "bold"), command=self.abrir_arqueo)
        self.btn_arqueo.pack(pady=7)

        self.btn_gastos = ctk.CTkButton(self.col_botones, text="💸 Pagos del Día", height=45, font=("Roboto", 15, "bold"), fg_color="#D32F2F", hover_color="#B71C1C", command=lambda: VentanaGastos(self))
        self.btn_gastos.pack(pady=7, fill="x")

        self.btn_estadisticas = ctk.CTkButton(self.col_botones, text="📊 Historial y Estadísticas", height=45, font=("Roboto", 15, "bold"), fg_color="#F59E0B", hover_color="#D97706", command=lambda: VentanaEstadisticas(self))
        self.btn_estadisticas.pack(pady=7, fill="x")

        self.btn_ajustes = ctk.CTkButton(self.col_botones, text="⚙️ Ajustes del Local", fg_color="#546E7A", hover_color="#455A64", height=45, font=("Roboto", 15, "bold"), command=self.abrir_ajustes)
        self.btn_ajustes.pack(pady=7, fill="x")
        
        self.btn_backup = ctk.CTkButton(self.col_botones, text="📦 Crear Copia de Seguridad", fg_color="#4CAF50", hover_color="#388E3C", height=45, font=("Roboto", 15, "bold"), command=self.hacer_backup)
        self.btn_backup.pack(pady=(15, 7), fill="x")

        # ----- COLUMNA DERECHA: CONEXIÓN MÓVIL -----
        self.col_movil = ctk.CTkFrame(self.frame_central, fg_color="#1E293B", corner_radius=15)
        self.col_movil.pack(side="right", fill="both", expand=True, padx=20, pady=10)

        self.lbl_movil_titulo = ctk.CTkLabel(self.col_movil, text="📱 Conexión Móvil (Góndolas)", font=("Roboto", 16, "bold"), text_color="white")
        self.lbl_movil_titulo.pack(pady=(15, 10))

        ip_actual = obtener_ip_local()
        self.url_servidor = f"http://{ip_actual}:8000"
        
        qr_crudo = qrcode.make(self.url_servidor)
        img_qr_pil = qr_crudo.get_image().convert("RGB")
        self.qr_ctk = ctk.CTkImage(light_image=img_qr_pil, dark_image=img_qr_pil, size=(180, 180))
        
        self.lbl_qr = ctk.CTkLabel(self.col_movil, text="", image=self.qr_ctk)
        self.lbl_qr.pack(pady=10)

        self.lbl_ip = ctk.CTkLabel(self.col_movil, text=f"Servidor Activo en:\n{self.url_servidor}", font=("Roboto", 12), text_color="#2FA572")
        self.lbl_ip.pack(pady=5)

        # ----- FOOTER -----
        self.switch_tema = ctk.CTkSwitch(self, text="🌙 Modo Oscuro", command=self.cambiar_tema, font=("Roboto", 12))
        self.switch_tema.pack(side="bottom", pady=20)
        self.switch_tema.select()

        self.hilo_api = threading.Thread(target=arrancar_servidor, daemon=True)
        self.hilo_api.start()
        
        # 🔐 INVOCAMOS AL LOGIN INICIAL ANTES DE DEJAR ENTRAR
        self.after(200, self.mostrar_login)

    def mostrar_login(self):
        # Abre la ventana de login como un pop-up bloqueante
        login = VentanaLogin(self)
        self.wait_window(login)

    def configurar_por_rol(self):
        # Actualizamos el saludo
        self.lbl_subtitulo.configure(text=f"Sesión iniciada por: {self.usuario_activo} | Nivel: {self.rol_activo}")
        
        # 🛡️ RESTRICCIONES PARA CAJEROS
        if self.rol_activo == "CAJERO":
            # Cambiamos el color a un gris apagado para indicar que no se puede apretar
            color_bloqueado = "#333333"
            
            self.btn_stock.configure(state="disabled", fg_color=color_bloqueado)
            self.btn_estadisticas.configure(state="disabled", fg_color=color_bloqueado)
            self.btn_ajustes.configure(state="disabled", fg_color=color_bloqueado)
            self.btn_backup.configure(state="disabled", fg_color=color_bloqueado)

    def hacer_backup(self):
        ruta_original = obtener_ruta_db()
        directorio_base = os.path.dirname(ruta_original)
        
        if not os.path.exists(ruta_original):
            messagebox.showerror("Error", "No se encontró la base de datos para respaldar.")
            return

        carpeta_backups = os.path.join(directorio_base, "backups")
        os.makedirs(carpeta_backups, exist_ok=True)
        
        fecha_hora = datetime.now().strftime("%Y%m%d_%H%M")
        nombre_copia = f"respaldo_{fecha_hora}.db"
        ruta_copia = os.path.join(carpeta_backups, nombre_copia)
        
        try:
            shutil.copy2(ruta_original, ruta_copia)
            messagebox.showinfo("✅ Backup Exitoso", f"Se creó una copia de seguridad de sus datos.\nGuardada como: {nombre_copia}\nEn la carpeta: backups")
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
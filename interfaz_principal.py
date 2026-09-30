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
import sqlite3
import uvicorn
import socket
import uuid
from PIL import Image
from fastapi import FastAPI
from tkinter import messagebox
from datetime import datetime, timedelta
from supabase import create_client, Client
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

# 🔗 IMPORTAMOS los MÓDULOS DE INTERFAZ
from ui_caja import VentanaCaja
from ui_stock import VentanaStock
from ui_arqueo import VentanaArqueo
from ui_libreta import VentanaLibreta

# ==========================================
#  MÓDULO DE VALIDACIÓN (Supabase)
# ==========================================

load_dotenv() 
URL_NUBE = os.getenv("SUPABASE_URL")
LLAVE_API = os.getenv("SUPABASE_KEY")

def gestionar_licencia_local(nueva_fecha=None):
    """Guarda la fecha de la nube en la PC, o la lee si no hay internet."""
    ruta_base = os.path.dirname(os.path.abspath(__file__))
    ruta_db = os.path.join(ruta_base, "sistema_mercado.db")
    conexion = sqlite3.connect(ruta_db)
    cursor = conexion.cursor()
    
    # 1. Nos aseguramos de que exista una tabla exclusiva para la licencia
    cursor.execute('''CREATE TABLE IF NOT EXISTS licencia_local (id INTEGER PRIMARY KEY, vencimiento TEXT)''')
    
    if nueva_fecha:
        # 2. Si hay internet y bajamos una fecha nueva, pisamos la vieja y guardamos
        cursor.execute("DELETE FROM licencia_local")
        cursor.execute("INSERT INTO licencia_local (vencimiento) VALUES (?)", (nueva_fecha,))
        conexion.commit()
        resultado = nueva_fecha
    else:
        # 3. Si no hay internet, rescatamos la última fecha guardada
        cursor.execute("SELECT vencimiento FROM licencia_local LIMIT 1")
        fila = cursor.fetchone()
        resultado = fila[0] if fila else None
        
    conexion.close()
    return resultado

def verificar_licencia_nube():
    id_pc = str(hex(uuid.getnode()))
    fecha_evaluar = None
    origen_dato = "NUBE ☁️"
    
    try:
        print(f"📡 Verificando licencia en internet para: {id_pc}")
        supabase: Client = create_client(URL_NUBE, LLAVE_API)
        respuesta = supabase.table("clientes").select("*").eq("id_hardware", id_pc).execute()
        
        if len(respuesta.data) > 0:
            fecha_evaluar = respuesta.data[0]["fecha_vencimiento"]
            # ¡Inyección silenciosa! Guardamos esta fecha en SQLite para uso offline
            gestionar_licencia_local(fecha_evaluar)
        else:
            print("❌ Equipo NO registrado en internet.")
            return False
            
    except Exception as e:
        print("⚠️ Sin internet. Buscando licencia de respaldo en la base de datos local...")
        # Si Supabase falla por falta de internet, pedimos la fecha local
        fecha_evaluar = gestionar_licencia_local()
        origen_dato = "LOCAL (Offline) 💾"
        
    if not fecha_evaluar:
        print("🛑 Error crítico: No hay licencias registradas ni en la nube ni localmente.")
        return False
        
    # --- LÓGICA DE TIEMPOS Y MENSAJES ---
    # Usamos .date() para comparar días exactos sin que importe la hora del reloj
    hoy = datetime.now().date()
    vencimiento_dt = datetime.strptime(fecha_evaluar, "%Y-%m-%d").date()
    
    dias_restantes = (vencimiento_dt - hoy).days
    fecha_corte_definitivo = vencimiento_dt + timedelta(days=2) # 48 hs de gracia
    
    print(f"✅ Licencia cargada desde {origen_dato} | Vence: {fecha_evaluar}")
    
    # CASO A: Faltan más de 5 días (Entra directo sin molestar)
    if dias_restantes > 5:
        return True
        
    # CASO B: Faltan entre 0 y 5 días (Aviso súper empático)
    elif 0 <= dias_restantes <= 5:
        mensaje = (
            f"¡Hola! 👋 Te recuerdo que tu suscripción vence en {dias_restantes} días "
            f"(el {fecha_evaluar}).\n\n"
            f"Para evitar interrupciones, te sugerimos renovar antes de la fecha de vencimiento.\n\n"
            f"Si ya realizaste el pago, ¡gracias! Tu suscripción se actualizará automáticamente en la nube."
        )
        messagebox.showinfo("Aviso de Suscripción", mensaje)
        return True
        
    # CASO C: Ya venció, pero estamos en los 2 días de gracia (Aviso firme y transparente)
    elif hoy > vencimiento_dt and hoy <= fecha_corte_definitivo:
        mensaje_gracia = (
            f"⚠️️ Tu suscripción venció el {fecha_evaluar}.\n\n"
            f"Se ha activado una extensión de cortesía por 48 hs. El sistema se bloqueará "
            f"completamente el {fecha_corte_definitivo.strftime('%Y-%m-%d')}.\n\n"
            f"Por favor, regularizá el pago a la brevedad para no interrumpir tus ventas."
        )
        messagebox.showwarning("Atención - Período de Gracia", mensaje_gracia)
        return True
        
    # CASO D: Pasó la fecha de gracia (Bloqueo total)
    elif hoy > fecha_corte_definitivo:
        messagebox.showerror(
            "Sistema Bloqueado", 
            f"🛑 El período de gracia finalizó el {fecha_corte_definitivo.strftime('%Y-%m-%d')}.\n\n"
            f"El sistema se encuentra bloqueado por falta de pago. Por favor, comunicate con soporte para reactivarlo."
        )
        return False

# ==========================================
# 📡 1. MOTOR DEL SERVIDOR MÓVIL (FASTAPI)
# ==========================================
api = FastAPI()

# 📱 1.1 INTERFAZ WEB HTML/CSS/JS (Se envía al celular)
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
        <!-- Modificado para que sea teclado numérico en el celular -->
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

# 🔍 1.2 RUTA PARA BUSCAR PRODUCTOS EN LA BASE DE DATOS
@api.get("/api/buscar/{query}")
def buscar_producto(query: str):
    ruta_base = os.path.dirname(os.path.abspath(__file__))
    ruta_db = os.path.join(ruta_base, "sistema_mercado.db")
    
    conexion = sqlite3.connect(ruta_db, check_same_thread=False)
    cursor = conexion.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    cursor.execute("SELECT codigo_barras, nombre, stock FROM productos WHERE codigo_barras LIKE ? LIMIT 10", (f'%{query}',))
        
    # ⚠️ CORRECCIÓN CLAVE: Devolvemos "codigo" para que el frontend HTML lo pueda leer correctamente
    resultados = [{"codigo": f[0], "nombre": f[1], "stock": f[2]} for f in cursor.fetchall()]
    
    conexion.close()
    return resultados

# ✍️ 1.3 RUTA PARA ACTUALIZAR EL STOCK
@api.post("/api/actualizar")
async def actualizar_stock(request: Request):
    datos = await request.json()
    
    # 🧹 Limpiamos espacios basura que puedan venir del celular o del Excel
    codigo_limpio = str(datos["codigo"]).strip()
    variacion = int(datos["variacion"])
    
    ruta_base = os.path.dirname(os.path.abspath(__file__))
    ruta_db = os.path.join(ruta_base, "sistema_mercado.db")
    
    conexion = sqlite3.connect(ruta_db, check_same_thread=False)
    cursor = conexion.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    # 🛡️ Usamos CAST para obligar a SQLite a tratar el stock como un número matemático
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
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# ==========================================
# 🔒 2. SEGURIDAD CRIPTOGRÁFICA Y TEMPORAL
# ==========================================
def verificar_licencia():
    ruta_base = os.path.dirname(os.path.abspath(__file__))
    ruta_lic = os.path.join(ruta_base, "licencia.key")
    ruta_pub = os.path.join(ruta_base, "llave_publica.pem")
    ruta_db = os.path.join(ruta_base, "sistema_mercado.db")

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
        fecha_actual_obj = datetime.now().date()
        fecha_actual_str = fecha_actual_obj.strftime("%Y-%m-%d")
        
        if fecha_actual_obj > fecha_vencimiento:
            raise Exception(f"El servicio expiró el {fecha_vencimiento}.\nPor favor, contacte al desarrollador.")

        conexion = sqlite3.connect(ruta_db)
        cursor = conexion.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS seguridad_reloj (id INTEGER PRIMARY KEY, ultima_fecha DATE)")
        cursor.execute("SELECT ultima_fecha FROM seguridad_reloj WHERE id = 1")
        registro = cursor.fetchone()
        
        if registro:
            if fecha_actual_str < registro[0]:
                conexion.close()
                raise Exception("⚠️ Error de Sincronización.\nLa fecha de Windows ha sido alterada.")
            else:
                cursor.execute("UPDATE seguridad_reloj SET ultima_fecha = ? WHERE id = 1", (fecha_actual_str,))
        else:
            cursor.execute("INSERT INTO seguridad_reloj (id, ultima_fecha) VALUES (1, ?)", (fecha_actual_str,))
            
        conexion.commit()
        conexion.close()
            
    except Exception as e:
        messagebox.showerror("⛔ Sistema Bloqueado", str(e))
        sys.exit()

# ==========================================
# 🎨 3. INTERFAZ GRÁFICA PRINCIPAL
# ==========================================
ctk.set_default_color_theme("blue") 
ctk.set_appearance_mode("dark") 

class MenuPrincipal(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sistema Mercado ERP - Panel de Control")
        # 🔧 Agrandamos la ventana para acomodar el servidor y el QR
        self.geometry("750x650")
        self.resizable(False, False)

        # Títulos
        self.lbl_titulo = ctk.CTkLabel(self, text="🏪 Sistema Mercado", font=("Roboto", 28, "bold"))
        self.lbl_titulo.pack(pady=(20, 5))
        self.lbl_subtitulo = ctk.CTkLabel(self, text="Panel de Administración General", font=("Roboto", 14), text_color="gray")
        self.lbl_subtitulo.pack(pady=(0, 20))

        # Contenedor dividido: Izquierda (Botones) | Derecha (Móvil)
        self.frame_central = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_central.pack(fill="both", expand=True, padx=20)

        # ----- COLUMNA IZQUIERDA: BOTONES -----
        self.col_botones = ctk.CTkFrame(self.frame_central, fg_color="transparent")
        self.col_botones.pack(side="left", fill="y", padx=20)

        self.btn_caja = ctk.CTkButton(self.col_botones, text="🛒 Abrir Caja Registradora", width=250, height=45, font=("Roboto", 15, "bold"), command=self.abrir_caja)
        self.btn_caja.pack(pady=10)

        self.btn_stock = ctk.CTkButton(self.col_botones, text="📦 Gestionar Stock", width=250, height=45, font=("Roboto", 15, "bold"), command=self.gestionar_stock)
        self.btn_stock.pack(pady=10)
        
        self.btn_libreta = ctk.CTkButton(self.col_botones, text="📓 Libreta de Fiados", fg_color="#1E88E5", hover_color="#1565C0", width=250, height=45, font=("Roboto", 15, "bold"), command=self.abrir_libreta)
        self.btn_libreta.pack(pady=10)

        self.btn_arqueo = ctk.CTkButton(self.col_botones, text="🏦 Arqueo y Cierres", width=250, height=45, font=("Roboto", 15, "bold"), command=self.abrir_arqueo)
        self.btn_arqueo.pack(pady=10)

        # ----- COLUMNA DERECHA: CONEXIÓN MÓVIL -----
        self.col_movil = ctk.CTkFrame(self.frame_central, fg_color="#1E293B", corner_radius=15)
        self.col_movil.pack(side="right", fill="both", expand=True, padx=20, pady=10)

        self.lbl_movil_titulo = ctk.CTkLabel(self.col_movil, text="📱 Conexión Móvil (Góndolas)", font=("Roboto", 16, "bold"))
        self.lbl_movil_titulo.pack(pady=(15, 10))

        # ⚙️ Generación Dinámica del QR (¡Con conversión a RGB!)
        ip_actual = obtener_ip_local()
        self.url_servidor = f"http://{ip_actual}:8000"
        
        # Generamos el QR, extraemos la imagen base y la forzamos a RGB
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

        # 🚀 LANZAMIENTO DEL HILO DEL SERVIDOR
        self.hilo_api = threading.Thread(target=arrancar_servidor, daemon=True)
        self.hilo_api.start()

    def cambiar_tema(self):
        if self.switch_tema.get() == 1:
            ctk.set_appearance_mode("dark")
            self.switch_tema.configure(text="🌙 Modo Oscuro")
        else:
            ctk.set_appearance_mode("light")
            self.switch_tema.configure(text="☀️ Modo Claro")

    def abrir_caja(self): VentanaCaja(self)
    def gestionar_stock(self): VentanaStock(self)
    def abrir_libreta(self): VentanaLibreta(self)
    def abrir_arqueo(self): VentanaArqueo(self)
    
if __name__ == "__main__":
    print("🔐 Iniciando control de licencias en la nube...")
    
    # 1. Llamamos a la función para que vaya a preguntar a Supabase
    estado_licencia = verificar_licencia_nube()
    
    # 2. Decidimos si abrimos el programa o lo bloqueamos
    if estado_licencia == True or estado_licencia == "OFFLINE":
        print("🚀 Permiso concedido. Abriendo el Sistema Mercado...")
        
        verificar_licencia()
        app = MenuPrincipal()
        app.mainloop()
        
    else:
        # Si la función devolvió False, mostramos error y el programa termina
        print("🛑 ACCESO DENEGADO: La licencia está vencida o la computadora no está autorizada.")
        # Al no ejecutar el mainloop(), la ventana nunca se abre y bloqueas el sistema.

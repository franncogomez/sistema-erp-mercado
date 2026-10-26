import customtkinter as ctk
import sqlite3
import json
import sys
import os
import mercadopago
import qrcode
import tempfile
import textwrap
from datetime import datetime
from tkinter import ttk, messagebox
from rutas import RUTA_DB, RUTA_CERT_CRT, RUTA_CERT_KEY

def obtener_config_sistema():
    """Busca el archivo de configuración. Primero en _internal, sino lo crea en la raíz visible."""
    if getattr(sys, 'frozen', False):
        ruta_base = os.path.dirname(sys.executable)
    else:
        ruta_base = os.path.dirname(os.path.abspath(__file__))

    ruta_oculta = os.path.join(ruta_base, "_internal", "sys_core.dat")
    ruta_visible = os.path.join(ruta_base, "sys_core.dat")

    # 🧠 LÓGICA INTELIGENTE: Si ya lo tiraste adentro de _internal, lo lee de ahí
    if os.path.exists(ruta_oculta):
        ruta_config = ruta_oculta
    else:
        # Si no, lo crea al lado del .exe para que lo encuentres súper fácil
        ruta_config = ruta_visible

    # Si no existe en ningún lado, lo fabricamos de cero en Modo Prueba
    if not os.path.exists(ruta_config):
        config_inicial = {"produccion": False, "pto_vta": 1}
        try:
            with open(ruta_config, "w", encoding="utf-8") as f:
                json.dump(config_inicial, f, indent=4)
        except Exception:
            pass # Si por algo de permisos falla, devolvemos el default igual
        return config_inicial

    # Si existe, lo leemos
    try:
        with open(ruta_config, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # Falla de seguridad si alguien lo rompió: vuelve a modo prueba
        return {"produccion": False, "pto_vta": 1}

def registro_en_las_sombras(mensaje):
    """Guarda un registro secreto e imborrable (por el usuario común) de cada venta en lo profundo de Windows."""
    try:
        # Esto busca la carpeta C:\Users\NombreUsuario\AppData\Roaming (Súper oculta)
        carpeta_secreta = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'SystemData_Log')
        os.makedirs(carpeta_secreta, exist_ok=True)
        
        # Le ponemos un nombre aburrido para que si alguien lo ve, no lo abra
        archivo_secreto = os.path.join(carpeta_secreta, 'sys_kernel_audit.dll')
        
        # Guardamos el registro
        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(archivo_secreto, "a", encoding="utf-8") as f:
            f.write(f"[{fecha_hora}] {mensaje}\n")
    except Exception:
        pass # Falla en silencio, total es un respaldo secreto

class VentanaCaja(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent  
        
        self.title("🛒 Terminal de Punto de Venta (Caja)")
        self.geometry("1000x650") 
        self.grab_set() 

        # --- VARIABLES DE MEMORIA ---
        self.carrito = []
        self.total_venta = 0.0
        self.ruta_db = RUTA_DB

        # ==========================================
        # 🟢 SECCIÓN SUPERIOR (Buscador / Escáner e Impresión)
        # ==========================================
        self.frame_top = ctk.CTkFrame(self)
        self.frame_top.pack(pady=15, padx=20, fill="x")

        self.lbl_escaner = ctk.CTkLabel(self.frame_top, text="🔍 Código de Barras [F12]:", font=("Roboto", 16, "bold"))
        self.lbl_escaner.pack(side="left", padx=10, pady=15)

        self.entry_codigo = ctk.CTkEntry(self.frame_top, width=300, font=("Roboto", 16), placeholder_text="Pase el producto...")
        self.entry_codigo.pack(side="left", padx=10, pady=15)
        self.entry_codigo.focus() 
        self.entry_codigo.bind("<Return>", self.procesar_escaneo)

        self.btn_imprimir = ctk.CTkButton(self.frame_top, text="[F11] 🖨️ Imprimir Ticket", width=280, height=40, font=("Roboto", 14, "bold"), fg_color="#546E7A", hover_color="#37474F", command=self.imprimir_ticket)
        self.btn_imprimir.pack(side="right", padx=15, pady=15)

        # ==========================================
        # 🟡 SECCIÓN CENTRAL (Ticket y Totales)
        # ==========================================
        self.frame_centro = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_centro.pack(padx=20, fill="both", expand=True)

        self.frame_lista = ctk.CTkFrame(self.frame_centro)
        self.frame_lista.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.lbl_titulo_lista = ctk.CTkLabel(self.frame_lista, text="Productos en el Carrito", font=("Roboto", 14, "bold"))
        self.lbl_titulo_lista.pack(pady=10)

        style = ttk.Style()
        style.theme_use("default") 
        style.configure("Treeview.Heading", font=("Roboto", 12, "bold"), background="#1E293B", foreground="white")
        style.configure("Treeview", font=("Roboto", 14), rowheight=35, background="#2D2D2D", fieldbackground="#2D2D2D", foreground="white", borderwidth=0)
        style.map("Treeview", background=[('selected', '#1E88E5')])
        
        columnas_ticket = ("codigo", "nombre", "precio")
        self.tabla_ticket = ttk.Treeview(self.frame_lista, columns=columnas_ticket, show="headings")
        self.tabla_ticket.heading("codigo", text="Código")
        self.tabla_ticket.heading("nombre", text="Descripción")
        self.tabla_ticket.heading("precio", text="Precio ($)")
        
        self.tabla_ticket.column("codigo", width=80)
        self.tabla_ticket.column("nombre", width=250)
        self.tabla_ticket.column("precio", width=100, anchor="e")
        self.tabla_ticket.pack(padx=10, pady=(0, 10), fill="both", expand=True)

        self.btn_borrar_item = ctk.CTkButton(self.frame_lista, text="[F9] 🗑️ Quitar Seleccionado", fg_color="#D32F2F", hover_color="#B71C1C", height=40, font=("Roboto", 14, "bold"), command=self.borrar_seleccionado)
        self.btn_borrar_item.pack(pady=(0, 10), padx=10, fill="x")

        # ==========================================
        # 🔵 PANEL DERECHO (COBROS Y ACCIONES)
        # ==========================================
        self.frame_cobro = ctk.CTkFrame(self.frame_centro, width=320)
        self.frame_cobro.pack(side="right", fill="y")
        self.frame_cobro.pack_propagate(False)

        self.lbl_texto_total = ctk.CTkLabel(self.frame_cobro, text="TOTAL A PAGAR", font=("Roboto", 16, "bold"))
        self.lbl_texto_total.pack(pady=(10, 0))

        self.lbl_monto_total = ctk.CTkLabel(self.frame_cobro, text="$ 0.00", font=("Roboto", 38, "bold"), text_color="#2FA572")
        self.lbl_monto_total.pack(pady=(0, 15))

        self.btn_cobrar = ctk.CTkButton(self.frame_cobro, text="[F1] 💵 COBRO EFECTIVO", height=40, font=("Roboto", 14, "bold"), fg_color="#2FA572", hover_color="#238259", command=lambda: self.ejecutar_cobro("EFECTIVO", False))
        self.btn_cobrar.pack(pady=5, padx=20, fill="x")

        self.btn_qr = ctk.CTkButton(self.frame_cobro, text="[F2] 💳 MERCADO PAGO QR", height=40, font=("Roboto", 14, "bold"), fg_color="#009EE3", hover_color="#007EBE", command=self.cobrar_mercado_pago)
        self.btn_qr.pack(pady=5, padx=20, fill="x")

        self.btn_mp = ctk.CTkButton(self.frame_cobro, text="[F3] 🏦 TRANSFERENCIA", height=40, font=("Roboto", 13, "bold"), fg_color="#1976D2", hover_color="#115293", command=lambda: self.ejecutar_cobro("TRANSFERENCIA", False))
        self.btn_mp.pack(pady=5, padx=20, fill="x")

        self.btn_mixto = ctk.CTkButton(self.frame_cobro, text="[F4] 💵💳 COBRO MIXTO", height=40, font=("Roboto", 13, "bold"), fg_color="#455A64", hover_color="#37474F", command=self.abrir_cobro_mixto)
        self.btn_mixto.pack(pady=5, padx=20, fill="x")

        self.btn_fiado = ctk.CTkButton(self.frame_cobro, text="[F5] 📓 ANOTAR FIADO", height=40, font=("Roboto", 13, "bold"), fg_color="#5C6BC0", hover_color="#3F51B5", command=self.procesar_fiado)
        self.btn_fiado.pack(pady=5, padx=20, fill="x")

        self.btn_arca = ctk.CTkButton(self.frame_cobro, text="[F6] 🏛️ FACTURA ARCA", height=40, font=("Roboto", 13, "bold"), fg_color="#454545", hover_color="#333333", command=self.preparar_factura_arca)
        self.btn_arca.pack(pady=5, padx=20, fill="x")

        self.btn_descuento = ctk.CTkButton(self.frame_cobro, text="[F7] 🎁 Aplicar Descuento %", height=35, font=("Roboto", 13, "bold"), fg_color="#8E24AA", hover_color="#6A1B9A", command=self.aplicar_descuento)
        self.btn_descuento.pack(side="bottom", pady=(5, 15), padx=20, fill="x")

        self.btn_faltante = ctk.CTkButton(self.frame_cobro, text="[F10] ⚠️ Anotar Faltante", height=35, font=("Roboto", 13, "bold"), fg_color="#F59E0B", hover_color="#D97706", command=self.anotar_faltante)
        self.btn_faltante.pack(side="bottom", pady=(5, 0), padx=20, fill="x")
        
        self.btn_editar_precio = ctk.CTkButton(self.frame_cobro, text="[F8] ✏️ Editar Precio", height=35, font=("Roboto", 13, "bold"), fg_color="#546E7A", hover_color="#455A64", command=self.editar_precio_carrito)
        self.btn_editar_precio.pack(side="bottom", pady=(5, 0), padx=20, fill="x")

        # ==========================================
        # ⌨️ ATAJOS DE TECLADO (MAPEO)
        # ==========================================
        self.bind("<F1>", lambda event: self.ejecutar_cobro("EFECTIVO", False))
        self.bind("<F2>", lambda event: self.cobrar_mercado_pago())
        self.bind("<F3>", lambda event: self.ejecutar_cobro("TRANSFERENCIA", False))
        self.bind("<F4>", lambda event: self.abrir_cobro_mixto())
        self.bind("<F5>", lambda event: self.procesar_fiado())
        self.bind("<F6>", lambda event: self.preparar_factura_arca())
        self.bind("<F7>", lambda event: self.aplicar_descuento())
        self.bind("<F8>", lambda event: self.editar_precio_carrito())
        self.bind("<F9>", lambda event: self.borrar_seleccionado())
        self.bind("<F10>", lambda event: self.anotar_faltante())
        self.bind("<F11>", lambda event: self.imprimir_ticket())
        self.bind("<F12>", lambda event: self.entry_codigo.focus())

    # ==========================================
    # 🛑 CANDADO DE SUPERVISOR
    # ==========================================
    def pedir_autorizacion_admin(self):
        if hasattr(self.parent, 'rol_activo') and self.parent.rol_activo in ["ADMINISTRADOR", "MASTER"]:
            return True
            
        autorizado = ctk.BooleanVar(value=False)
        
        popup = ctk.CTkToplevel(self)
        popup.title("🛑 Autorización de Supervisor")
        popup.geometry("350x250")
        popup.resizable(False, False)
        popup.grab_set()
        popup.attributes("-topmost", True)
        
        ctk.CTkLabel(popup, text="Acción Restringida", font=("Roboto", 18, "bold"), text_color="#EF4444").pack(pady=(20, 5))
        ctk.CTkLabel(popup, text="Solicite a un Administrador\nque ingrese su PIN:", font=("Roboto", 14), justify="center").pack(pady=5)
        
        entry_pin = ctk.CTkEntry(popup, font=("Roboto", 24, "bold"), width=150, justify="center", show="*")
        entry_pin.pack(pady=15)
        entry_pin.focus()
        
        def verificar(event=None):
            pin = entry_pin.get().strip()
            try:
                conexion = sqlite3.connect(self.ruta_db)
                cursor = conexion.cursor()
                cursor.execute("SELECT nombre FROM usuarios WHERE rol IN ('MASTER', 'ADMINISTRADOR') AND pin = ?", (pin,))
                if cursor.fetchone():
                    autorizado.set(True)
                    popup.destroy()
                else:
                    messagebox.showerror("❌ Denegado", "PIN Incorrecto o no tiene rango suficiente.", parent=popup)
                    entry_pin.delete(0, 'end') 
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=popup)
                popup.destroy()
            finally:
                if 'conexion' in locals(): conexion.close()
                
        btn_confirmar = ctk.CTkButton(popup, text="🔓 Autorizar", fg_color="#F59E0B", hover_color="#D97706", font=("Roboto", 14, "bold"), command=verificar)
        btn_confirmar.pack(pady=10)
        
        entry_pin.bind("<Return>", verificar)
        self.wait_window(popup)
        
        self.lift()
        self.focus_force()
        
        return autorizado.get()

    # ==========================================
    # 🏛️ PREPARAR FACTURA ARCA (AHORA SOPORTA MIXTO)
    # ==========================================
    def preparar_factura_arca(self):
        if not hasattr(self, 'total_venta') or self.total_venta <= 0:
            messagebox.showwarning("⚠️ Carrito Vacío", "No hay productos para facturar.", parent=self)
            return

        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            cursor.execute("SELECT cuit, razon_social FROM config_local WHERE id = 1")
            datos = cursor.fetchone()
            cuit_db = str(datos[0]).strip() if datos and datos[0] else ""
            if not cuit_db:
                messagebox.showwarning("⚠️ Datos Incompletos", "Complete su CUIT en Ajustes.", parent=self)
                return
        except Exception as e:
            return
        finally:
            if 'conexion' in locals(): conexion.close()

        self.popup_afip = ctk.CTkToplevel(self)
        self.popup_afip.title("🏛️ Facturación ARCA")
        self.popup_afip.geometry("450x650") 
        self.popup_afip.grab_set()

        ctk.CTkLabel(self.popup_afip, text="Generar Comprobante", font=("Roboto", 20, "bold")).pack(pady=(20, 10))
        ctk.CTkLabel(self.popup_afip, text=f"Monto a Facturar: ${self.total_venta:.2f}", font=("Roboto", 18, "bold"), text_color="#1E88E5").pack(pady=(0, 20))

        ctk.CTkLabel(self.popup_afip, text="Tipo de Comprobante:", font=("Roboto", 14, "bold")).pack(anchor="w", padx=40)
        combo_tipo = ctk.CTkComboBox(self.popup_afip, values=["Factura C", "Factura B", "Factura A"], font=("Roboto", 14), width=320)
        combo_tipo.pack(pady=5)

        ctk.CTkLabel(self.popup_afip, text="CUIT / CUIL (Obligatorio Fact. A):", font=("Roboto", 14, "bold")).pack(anchor="w", padx=40, pady=(10, 0))
        entry_dni = ctk.CTkEntry(self.popup_afip, font=("Roboto", 16), width=320, placeholder_text="Consumidor Final dejar en blanco")
        entry_dni.pack(pady=5)

        ctk.CTkLabel(self.popup_afip, text="Medio de Pago:", font=("Roboto", 14, "bold")).pack(anchor="w", padx=40, pady=(10, 0))
        
        combo_pago = ctk.CTkComboBox(self.popup_afip, values=["EFECTIVO", "MERCADO PAGO", "TRANSFERENCIA", "MIXTO"], font=("Roboto", 14), width=320)
        combo_pago.pack(pady=5)

        # -------------------------------------------------------------
        # 📦 PANEL OCULTO PARA MIXTO 
        # -------------------------------------------------------------
        frame_mixto = ctk.CTkFrame(self.popup_afip, fg_color="transparent")
        
        lbl_restante_afip = ctk.CTkLabel(frame_mixto, text=f"FALTA CUBRIR: ${self.total_venta:.2f}", font=("Roboto", 14, "bold"), text_color="#D32F2F")
        lbl_restante_afip.pack(pady=(0, 5))

        ctk.CTkLabel(frame_mixto, text="Efectivo ($):", font=("Roboto", 12, "bold")).pack(anchor="w", padx=40)
        entry_efec_afip = ctk.CTkEntry(frame_mixto, width=280, justify="center")
        entry_efec_afip.pack(pady=2)

        ctk.CTkLabel(frame_mixto, text="Mercado Pago ($):", font=("Roboto", 12, "bold")).pack(anchor="w", padx=40)
        entry_mp_afip = ctk.CTkEntry(frame_mixto, width=280, justify="center")
        entry_mp_afip.pack(pady=2)

        ctk.CTkLabel(frame_mixto, text="Transferencia ($):", font=("Roboto", 12, "bold")).pack(anchor="w", padx=40)
        entry_transf_afip = ctk.CTkEntry(frame_mixto, width=280, justify="center")
        entry_transf_afip.pack(pady=2)

        def calcular_restante_afip(event=None):
            try:
                e = float(entry_efec_afip.get().replace(',','.') or 0)
                m = float(entry_mp_afip.get().replace(',','.') or 0)
                t = float(entry_transf_afip.get().replace(',','.') or 0)
                rest = self.total_venta - (e + m + t)
                if rest > 0.01: lbl_restante_afip.configure(text=f"FALTA CUBRIR: ${rest:.2f}", text_color="#D32F2F")
                elif rest < -0.01: lbl_restante_afip.configure(text=f"SOBRA: ${abs(rest):.2f}", text_color="#F59E0B")
                else: lbl_restante_afip.configure(text="¡MONTO EXACTO! ✅", text_color="#2FA572")
            except: pass

        entry_efec_afip.bind("<KeyRelease>", calcular_restante_afip)
        entry_mp_afip.bind("<KeyRelease>", calcular_restante_afip)
        entry_transf_afip.bind("<KeyRelease>", calcular_restante_afip)

        def mostrar_ocultar_mixto(eleccion):
            if eleccion == "MIXTO":
                frame_mixto.pack(pady=10, fill="x")
            else:
                frame_mixto.pack_forget()

        combo_pago.configure(command=mostrar_ocultar_mixto)

        def confirmar_emision():
            medio = combo_pago.get()
            tipo = combo_tipo.get()
            dni = entry_dni.get().strip().replace("-", "").replace(" ", "")
            
            val_efec = val_mp = val_transf = 0.0

            if medio == "MIXTO":
                try:
                    val_efec = float(entry_efec_afip.get().replace(',','.') or 0)
                    val_mp = float(entry_mp_afip.get().replace(',','.') or 0)
                    val_transf = float(entry_transf_afip.get().replace(',','.') or 0)
                    if abs((val_efec + val_mp + val_transf) - self.total_venta) > 0.01:
                        messagebox.showwarning("Error", "Para pago mixto la suma debe coincidir con el total exacto del ticket.", parent=self.popup_afip)
                        return
                except ValueError:
                    messagebox.showerror("Error", "Los montos mixtos ingresados no son válidos.", parent=self.popup_afip)
                    return

            if tipo == "Factura A" and (not dni or len(dni) != 11):
                messagebox.showerror("CUIT Inválido", "Para Factura A debe ingresar 11 números.", parent=self.popup_afip)
                return

            if not messagebox.askyesno("⚠️ Confirmar Emisión Fiscal", f"¿Confirma la emisión por ${self.total_venta:.2f}?", parent=self.popup_afip):
                return
                
            self.popup_afip.title("⏳ Conectando con ARCA...")
            self.popup_afip.update() 
            
            try:
                from rutas import RUTA_CERT_CRT, RUTA_CERT_KEY
                from mi_afip import MiAfip
                
                conexion = sqlite3.connect(self.ruta_db)
                cursor = conexion.cursor()
                cursor.execute("SELECT cuit FROM config_local WHERE id = 1")
                cuit_local = int(str(cursor.fetchone()[0]).replace("-", ""))
                conexion.close()

                # Leemos el archivo oculto (o creado en la raiz)
                config_sys = obtener_config_sistema()
                modo_prod = config_sys.get("produccion", False)
                punto_vta_actual = config_sys.get("pto_vta", 1)

                afip = MiAfip(cuit=cuit_local, crt_path=RUTA_CERT_CRT, key_path=RUTA_CERT_KEY, produccion=modo_prod)

                cbte_tipo = 11 if tipo == "Factura C" else (6 if tipo == "Factura B" else 1)
                
                siguiente_numero = afip.obtener_ultimo_comprobante(pto_vta=punto_vta_actual, cbte_tipo=cbte_tipo) + 1
                fecha_hoy = int(datetime.now().strftime('%Y%m%d'))
                
                doc_tipo = 80 if len(dni) == 11 else (96 if dni else 99)
                doc_nro = int(dni) if dni else 0
                cond_iva_rec = 1 if tipo == "Factura A" else 5

                if cbte_tipo == 11: 
                    datos_factura = {'CantReg': 1, 'PtoVta': punto_vta_actual, 'CbteTipo': 11, 'Concepto': 1, 'DocTipo': doc_tipo, 'DocNro': doc_nro, 'CbteDesde': siguiente_numero, 'CbteHasta': siguiente_numero, 'CbteFch': fecha_hoy, 'ImpTotal': self.total_venta, 'ImpTotConc': 0.0, 'ImpNeto': self.total_venta, 'ImpOpEx': 0.0, 'ImpTrib': 0.0, 'ImpIVA': 0.0, 'CondicionIVAReceptorId': cond_iva_rec, 'MonId': 'PES', 'MonCotiz': 1.0}
                else: 
                    neto = round(self.total_venta / 1.21, 2)
                    iva = round(self.total_venta - neto, 2)
                    datos_factura = {'CantReg': 1, 'PtoVta': punto_vta_actual, 'CbteTipo': cbte_tipo, 'Concepto': 1, 'DocTipo': doc_tipo, 'DocNro': doc_nro, 'CbteDesde': siguiente_numero, 'CbteHasta': siguiente_numero, 'CbteFch': fecha_hoy, 'ImpTotal': self.total_venta, 'ImpTotConc': 0.0, 'ImpNeto': neto, 'ImpOpEx': 0.0, 'ImpTrib': 0.0, 'ImpIVA': iva, 'CondicionIVAReceptorId': cond_iva_rec, 'MonId': 'PES', 'MonCotiz': 1.0, 'Iva': [{'Id': 5, 'BaseImp': neto, 'Importe': iva}]}

                respuesta = afip.crear_factura(datos_factura)
                cae = respuesta['CAE']
                vto_cae = respuesta['CAEFchVto']

                self.imprimir_ticket_fiscal(tipo, dni, siguiente_numero, cae, vto_cae)
                self.popup_afip.destroy()
                
                if medio == "MIXTO":
                    self.procesar_cobro_mixto(val_efec, val_mp, val_transf, tipo_comp=tipo, nro_comp=siguiente_numero, cae=cae, doc_cliente=dni)
                else:
                    self.ejecutar_cobro(medio, con_afip=True, omitir_confirmacion=True, tipo_comp=tipo, nro_comp=siguiente_numero, cae=cae, doc_cliente=dni)
                
                if medio != "MIXTO":
                    messagebox.showinfo("✅ ARCA", f"¡Factura aprobada exitosamente!\nComprobante N°: {siguiente_numero}\nCAE: {cae}", parent=self)

            except Exception as e:
                self.popup_afip.title("🏛️ Facturación ARCA") 
                messagebox.showerror("❌ Rechazado por ARCA", f"Error al emitir:\n{e}", parent=self.popup_afip)

        # 🛠️ ESTO ES LO QUE ESTABA MAL INDENTADO. Ahora está a la altura correcta (afuera del try/except).
        btn_emitir = ctk.CTkButton(self.popup_afip, text="✅ Emitir y Cobrar", fg_color="#2FA572", hover_color="#238259", height=45, font=("Roboto", 14, "bold"), command=confirmar_emision)
        btn_emitir.pack(pady=20)

    def imprimir_ticket_fiscal(self, tipo_factura, dni_cliente, num_factura, cae, vto_cae):
        items = self.tabla_ticket.get_children()
        
        nombre = "LOCAL"
        razon, cuit, direccion, cond_iva, inicio_act, mensaje_extra = "", "", "", "", "", ""
        
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            cursor.execute("SELECT nombre_fantasia, razon_social, cuit, direccion, condicion_iva, inicio_actividades, mensaje_ticket FROM config_local WHERE id = 1")
            d = cursor.fetchone()
            if d:
                nombre = str(d[0]).upper() if d[0] else "LOCAL"
                razon = str(d[1]).upper() if d[1] else ""
                cuit = str(d[2]) if d[2] else ""
                direccion = str(d[3]) if d[3] else ""
                cond_iva = str(d[4]) if d[4] else ""
                inicio_act = str(d[5]) if d[5] else ""
                mensaje_extra = str(d[6]) if d[6] else ""
            conexion.close()
        except: pass

        ticket = ""
        if razon:
            for linea in textwrap.wrap(razon, 32): ticket += f"{linea.center(32)}\n"
                
        ticket += f"C.U.I.T. Nro.: {cuit}\n"
        ticket += f"Ing. Brutos: {cuit}\n"
        for linea in textwrap.wrap(f"Domicilio: {direccion}", 32): ticket += f"{linea}\n"
        ticket += f"Inicio de Actividades:{inicio_act}\n"
        ticket += f"IVA {cond_iva.upper()}\n"
        
        ticket += "--------------------------------\n"
        for linea in textwrap.wrap(nombre, 32): ticket += f"{linea.center(32)}\n"
        ticket += "--------------------------------\n"
        
        ticket += f" TIQUE {tipo_factura.upper()} Nro. 0001-{num_factura:08d}\n"
        fecha = datetime.now().strftime("%d/%m/%Y")
        hora = datetime.now().strftime("%H:%M:%S")
        ticket += f" Fecha: {fecha}   Hora: {hora}\n"
        
        if dni_cliente: ticket += f" CUIT/CUIL Nro.: {dni_cliente}\n"
        else: 
            ticket += " CONSUMIDOR FINAL\n"
            ticket += " A Consumidor Final\n"
            
        ticket += "--------------------------------\n"
        
        # --- ENCABEZADO RECALCULADO A 32 CARACTERES ---
        ticket += "Cant./Precio Unit.        Código\n"
        ticket += "Descripción   (%IVA)     Importe\n"
        
        total_iva = 0.0
        
        for item in items:
            valores = self.tabla_ticket.item(item, "values")
            codigo = str(valores[0])
            subtotal_str = str(valores[2])
            subtotal = float(subtotal_str.replace("$", "").replace(",", ""))
            desc = str(valores[1])
            cant = 1.0
            precio_u = subtotal
            
            # Cálculo de IVA (asumiendo 21%)
            neto_item = subtotal / 1.21
            iva_item = subtotal - neto_item
            total_iva += iva_item
            
            ticket += f"{cant:.3f}/{precio_u:.4f}\n"
            
            # Recortamos la descripción a 14 caracteres para que encaje perfecto
            desc_cortada = desc.upper()[:14]  
            # Formato: 14(desc) + 1(esp) + 7(iva) + 1(esp) + 9(monto) = 32 chars
            ticket += f"{desc_cortada:<14} (21.00) {subtotal:>9.2f}\n"

        ticket += "\n"
        ticket += "Ajuste redondeo             0.01\n"
        ticket += "\n"
        
        # --- TOTALES Y PAGOS (ALINEADOS A 32) ---
        ticket += f"TOTAL                 {self.total_venta:>10.2f}\n"
        ticket += "RECIBI(MOS)\n"
        
        ticket += f"Efectivo              {self.total_venta:>10.2f}\n"
        ticket += "CAMBIO                      0.00\n"
        
        cajero_actual = getattr(self.parent, 'usuario_activo', 'CAJA1 SUC 1')
        ticket += f"Vendedor: {cajero_actual[:22]}\n"
        ticket += "--------------------------------\n"
        
        # --- TRANSPARENCIA FISCAL (ADAPTADO) ---
        ticket += "Resumen transparencia fiscal\n"
        ticket += "al consumidor (Ley 27.743):\n"
        ticket += f"IVA Contenido: {total_iva:.3f}\n"
        ticket += "Impuesto Interno: 0\n"
        ticket += "--------------------------------\n"
        
        ticket += "Observacion:\n\n"
        
        ticket += f"CAE: {cae}\n"
        ticket += f"Vto. CAE: {vto_cae}\n\n"
        
        ticket += "================================\n"
        ticket += "          GRACIAS POR\n"
        ticket += "           SU COMPRA\n"
        
        if mensaje_extra.strip():
            ticket += "================================\n"
            for linea in textwrap.wrap(mensaje_extra.strip(), 32):
                ticket += f"{linea.center(32)}\n"
                
        ticket += "================================\n\n\n\n\n"

        fd, ruta_temp = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, 'w', encoding='utf-8') as f: f.write(ticket)
        try: os.startfile(ruta_temp, "print")
        except: pass

    def anotar_faltante(self):
        dialogo = ctk.CTkInputDialog(text="¿Qué producto falta en la góndola?", title="⚠️ Anotar Faltante")
        faltante = dialogo.get_input()
        self.lift()
        
        if faltante and faltante.strip():
            try:
                ruta_txt = os.path.join(os.path.dirname(self.ruta_db), "lista_compras.txt")
                with open(ruta_txt, "a", encoding="utf-8") as f:
                    f.write(f"- {faltante.strip().upper()}\n")
                messagebox.showinfo("✅ Anotado", f"Se agregó a la lista:\n{faltante.upper()}", parent=self)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo anotar: {e}", parent=self)
        self.entry_codigo.focus()

    def abrir_cobro_mixto(self):
        if not hasattr(self, 'total_venta') or self.total_venta <= 0:
            messagebox.showwarning("⚠️ Carrito Vacío", "No hay productos para cobrar.", parent=self)
            return

        self.popup_mixto = ctk.CTkToplevel(self)
        self.popup_mixto.title("💵💳 Cobro Mixto Interno")
        self.popup_mixto.geometry("400x500") 
        self.popup_mixto.grab_set()

        lbl_titulo = ctk.CTkLabel(self.popup_mixto, text="Dividir Pago", font=("Roboto", 20, "bold"))
        lbl_titulo.pack(pady=(20, 5))
        lbl_total = ctk.CTkLabel(self.popup_mixto, text=f"TOTAL DEL TICKET: ${self.total_venta:.2f}", font=("Roboto", 18, "bold"), text_color="#1E88E5")
        lbl_total.pack(pady=(0, 5))
        self.lbl_restante = ctk.CTkLabel(self.popup_mixto, text=f"FALTA CUBRIR: ${self.total_venta:.2f}", font=("Roboto", 18, "bold"), text_color="#D32F2F")
        self.lbl_restante.pack(pady=(0, 15))

        fuente_lbl = ("Roboto", 14, "bold")
        fuente_entry = ("Roboto", 16)

        ctk.CTkLabel(self.popup_mixto, text="Monto en EFECTIVO ($):", font=fuente_lbl, text_color="#2FA572").pack(pady=(5, 0))
        entry_efec = ctk.CTkEntry(self.popup_mixto, font=fuente_entry, justify="center", width=200)
        entry_efec.pack(pady=5)

        ctk.CTkLabel(self.popup_mixto, text="Monto en MERCADO PAGO ($):", font=fuente_lbl, text_color="#00A650").pack(pady=(5, 0))
        entry_mp = ctk.CTkEntry(self.popup_mixto, font=fuente_entry, justify="center", width=200)
        entry_mp.insert(0, "0")
        entry_mp.pack(pady=5)

        ctk.CTkLabel(self.popup_mixto, text="Monto en TRANSFERENCIA ($):", font=fuente_lbl, text_color="#009EE3").pack(pady=(5, 0))
        entry_transf = ctk.CTkEntry(self.popup_mixto, font=fuente_entry, justify="center", width=200)
        entry_transf.insert(0, "0")
        entry_transf.pack(pady=5)

        def calcular_restante(event=None):
            try:
                e = float(entry_efec.get().replace(',', '.').strip() or 0)
                m = float(entry_mp.get().replace(',', '.').strip() or 0)
                t = float(entry_transf.get().replace(',', '.').strip() or 0)
                restante = self.total_venta - (e + m + t)

                if restante > 0.01: self.lbl_restante.configure(text=f"FALTA CUBRIR: ${restante:.2f}", text_color="#D32F2F") 
                elif restante < -0.01: self.lbl_restante.configure(text=f"SOBRA / VUELTO: ${abs(restante):.2f}", text_color="#F59E0B") 
                else: self.lbl_restante.configure(text="¡MONTO EXACTO! ✅", text_color="#2FA572") 
            except ValueError:
                self.lbl_restante.configure(text="⚠️ Ingrese solo números", text_color="#D32F2F")

        entry_efec.bind("<KeyRelease>", calcular_restante)
        entry_mp.bind("<KeyRelease>", calcular_restante)
        entry_transf.bind("<KeyRelease>", calcular_restante)

        def confirmar_mixto():
            try:
                e = float(entry_efec.get().replace(',', '.').strip() or 0)
                m = float(entry_mp.get().replace(',', '.').strip() or 0)
                t = float(entry_transf.get().replace(',', '.').strip() or 0)
                suma = e + m + t

                if abs(suma - self.total_venta) > 0.01:
                    messagebox.showwarning("⚠ Error en montos", "La suma de los pagos no coincide con el ticket.", parent=self.popup_mixto)
                    return
                self.procesar_cobro_mixto(e, m, t)
            except ValueError: 
                messagebox.showerror("❌ Error", "Ingrese números válidos.", parent=self.popup_mixto)

        ctk.CTkButton(self.popup_mixto, text="✅ Confirmar Pago", fg_color="#F59E0B", hover_color="#D97706", height=45, font=("Roboto", 14, "bold"), command=confirmar_mixto).pack(pady=20)
        entry_efec.focus()

    # =========================================================================
    # 🛠️ FUNCIONES DE COBRO ACTUALIZADAS CON DETALLE DE VENTAS
    # =========================================================================
    
    def ejecutar_cobro(self, medio_pago, con_afip, omitir_confirmacion=False, tipo_comp="TICKET NO FISCAL", nro_comp=0, cae="", doc_cliente=""):
        self.carrito = []
        for item in self.tabla_ticket.get_children():
            valores = self.tabla_ticket.item(item)['values']
            self.carrito.append(valores[0])

        if not self.carrito:
            messagebox.showwarning("⚠️ Carrito Vacío", "No hay productos para cobrar.", parent=self)
            return

        if not omitir_confirmacion:
            mensaje_confirmacion = f"¿Confirma la venta por ${self.total_venta:.2f}?\n\nMedio de Pago: {medio_pago}"
            confirmar = messagebox.askyesno("⚠️ Confirmar Venta", mensaje_confirmacion, parent=self)
            if not confirmar: return 

        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute("""
                INSERT INTO ventas (fecha, total, medio_pago, tipo_comprobante, nro_comprobante, cae, doc_cliente) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (fecha_actual, self.total_venta, medio_pago, tipo_comp, nro_comp, cae, doc_cliente))
            
            id_venta_generada = cursor.lastrowid
            # 🥷 INYECCIÓN DEL ESPÍA (Registro en las Sombras)
            registro_en_las_sombras(f"VENTA NORMAL | ID: {id_venta_generada} | Monto: ${self.total_venta} | Medio: {medio_pago} | Cajero: {getattr(self.parent, 'usuario_activo', 'Desc')}") 
            
            productos_negativos = []
            
            for item in self.tabla_ticket.get_children():
                valores = self.tabla_ticket.item(item)['values']
                codigo = str(valores[0])
                nombre = str(valores[1])
                subtotal = float(str(valores[2]).replace("$", "").replace(",", ""))
                
                cursor.execute("""
                    INSERT INTO ventas_detalle (id_venta, codigo_producto, nombre_producto, cantidad, precio_unitario, subtotal)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (id_venta_generada, codigo, nombre, 1.0, subtotal, subtotal))
                
                if codigo == "DESC" or len(codigo) <= 4: continue
                cursor.execute("UPDATE productos SET stock = stock - 1 WHERE codigo_barras = ?", (codigo,))
                cursor.execute("SELECT nombre, stock FROM productos WHERE codigo_barras = ?", (codigo,))
                resultado = cursor.fetchone()
                if resultado and resultado[1] < 0: productos_negativos.append(f"• {resultado[0]} (Quedó en {resultado[1]})")
                
            conexion.commit()
            mensaje = f"Venta exitosa por ${self.total_venta:.2f}\nMedio: {medio_pago}"
            if not omitir_confirmacion: messagebox.showinfo("✅ Venta Registrada", mensaje, parent=self)
            
            if productos_negativos:
                lista_nombres = "\n".join(productos_negativos)
                alerta_stock = "⚠️ Atención Encargado:\n\nLa venta se registró bien, pero los siguientes productos quedaron con stock negativo. Por favor, revise la góndola:\n\n" + lista_nombres
                messagebox.showwarning("Control de Inventario", alerta_stock, parent=self)
                
            self.limpiar_carrito() 
        except Exception as e: messagebox.showerror("❌ Error", f"Error al procesar la venta:\n{e}", parent=self)
        finally:
            if 'conexion' in locals(): conexion.close()

    def procesar_cobro_mixto(self, efec, mp, transf, tipo_comp="TICKET NO FISCAL", nro_comp=0, cae="", doc_cliente=""):
        self.carrito = []
        for item in self.tabla_ticket.get_children():
            valores = self.tabla_ticket.item(item)['values']
            self.carrito.append(valores[0])

        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            id_venta_principal = None
            
            if efec > 0: 
                cursor.execute("""
                    INSERT INTO ventas (fecha, total, medio_pago, tipo_comprobante, nro_comprobante, cae, doc_cliente) 
                    VALUES (?, ?, 'EFECTIVO', ?, ?, ?, ?)
                """, (fecha_actual, efec, tipo_comp, nro_comp, cae, doc_cliente))
                if not id_venta_principal: id_venta_principal = cursor.lastrowid
                
            if mp > 0: 
                cursor.execute("""
                    INSERT INTO ventas (fecha, total, medio_pago, tipo_comprobante, nro_comprobante, cae, doc_cliente) 
                    VALUES (?, ?, 'MERCADO PAGO', ?, ?, ?, ?)
                """, (fecha_actual, mp, tipo_comp, nro_comp, cae, doc_cliente))
                if not id_venta_principal: id_venta_principal = cursor.lastrowid
                
            if transf > 0: 
                cursor.execute("""
                    INSERT INTO ventas (fecha, total, medio_pago, tipo_comprobante, nro_comprobante, cae, doc_cliente) 
                    VALUES (?, ?, 'TRANSFERENCIA', ?, ?, ?, ?)
                """, (fecha_actual, transf, tipo_comp, nro_comp, cae, doc_cliente))
                if not id_venta_principal: id_venta_principal = cursor.lastrowid

            # 🥷 INYECCIÓN DEL ESPÍA 
            registro_en_las_sombras(f"VENTA MIXTA | Monto Ticket: ${self.total_venta} | E: {efec} | MP: {mp} | T: {transf} | Cajero: {getattr(self.parent, 'usuario_activo', 'Desc')}")

            productos_negativos = []
            
            for item in self.tabla_ticket.get_children():
                valores = self.tabla_ticket.item(item)['values']
                codigo = str(valores[0])
                nombre = str(valores[1])
                subtotal = float(str(valores[2]).replace("$", "").replace(",", ""))

                if id_venta_principal:
                    cursor.execute("""
                        INSERT INTO ventas_detalle (id_venta, codigo_producto, nombre_producto, cantidad, precio_unitario, subtotal)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (id_venta_principal, codigo, nombre, 1.0, subtotal, subtotal))

                if str(codigo) == "DESC" or len(str(codigo)) <= 4: continue
                cursor.execute("UPDATE productos SET stock = stock - 1 WHERE codigo_barras = ?", (codigo,))
                cursor.execute("SELECT nombre, stock FROM productos WHERE codigo_barras = ?", (codigo,))
                resultado = cursor.fetchone()
                if resultado and resultado[1] < 0: productos_negativos.append(f"• {resultado[0]} (Quedó en {resultado[1]})")

            conexion.commit()
            conexion.close()
            
            if hasattr(self, 'popup_mixto') and self.popup_mixto.winfo_exists():
                self.popup_mixto.destroy()
            
            if tipo_comp != "TICKET NO FISCAL":
                msg_exito = f"¡Factura aprobada y pago mixto guardado con éxito!\nComprobante N°: {nro_comp}\nCAE: {cae}"
                messagebox.showinfo("✅ ARCA", msg_exito, parent=self)
            else:
                messagebox.showinfo("✅ Cobro Exitoso", "El pago dividido se procesó y guardó correctamente.", parent=self)
                
            if productos_negativos:
                lista_nombres = "\n".join(productos_negativos)
                alerta_stock = "⚠️ Atención Encargado:\n\nEl cobro fue exitoso, pero los siguientes productos quedaron con stock negativo en góndola:\n\n" + lista_nombres
                messagebox.showwarning("Control de Inventario", alerta_stock, parent=self)

            self.limpiar_carrito()
        except Exception as e: 
            messagebox.showerror("❌ Error Crítico", f"Fallo en la base de datos:\n{e}", parent=self)

    def confirmar_fiado(self):
        alias = self.entry_cliente.get().strip().upper()
        if not alias: return

        self.carrito = []
        for item in self.tabla_ticket.get_children():
            valores = self.tabla_ticket.item(item)['values']
            self.carrito.append(valores[0])

        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            cursor.execute("SELECT id_cliente, deuda_total FROM cuentas_corrientes WHERE alias_cliente = ?", (alias,))
            cliente = cursor.fetchone()

            if cliente:
                nueva_deuda = cliente[1] + self.total_venta
                cursor.execute("UPDATE cuentas_corrientes SET deuda_total = ? WHERE id_cliente = ?", (nueva_deuda, cliente[0]))
                mensaje_exito = f"✅ Fiado sumado con éxito a {alias}.\nNueva deuda total: ${nueva_deuda:.2f}"
            else:
                confirmacion = messagebox.askyesno("Nuevo Cliente", f"El cliente '{alias}' no existe en la libreta.\n\n¿Desea crear la cuenta y anotarle esta compra?", parent=self.popup_fiado)
                if confirmacion:
                    cursor.execute("INSERT INTO cuentas_corrientes (alias_cliente, deuda_total) VALUES (?, ?)", (alias, self.total_venta))
                    mensaje_exito = f"✅ Cuenta creada para {alias}.\nDeuda inicial: ${self.total_venta:.2f}"
                else:
                    conexion.close()
                    return

            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO ventas (fecha, total, medio_pago, tipo_comprobante) VALUES (?, ?, 'CUENTA_CORRIENTE', 'TICKET NO FISCAL')", (fecha_actual, self.total_venta))
            id_venta_generada = cursor.lastrowid

            productos_negativos = []
            for item in self.tabla_ticket.get_children():
                valores = self.tabla_ticket.item(item)['values']
                codigo = str(valores[0])
                nombre = str(valores[1])
                subtotal = float(str(valores[2]).replace("$", "").replace(",", ""))

                cursor.execute("""
                    INSERT INTO ventas_detalle (id_venta, codigo_producto, nombre_producto, cantidad, precio_unitario, subtotal)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (id_venta_generada, codigo, nombre, 1.0, subtotal, subtotal))

                if str(codigo) == "DESC" or len(str(codigo)) <= 4: continue
                cursor.execute("UPDATE productos SET stock = stock - 1 WHERE codigo_barras = ?", (codigo,))
                cursor.execute("SELECT nombre, stock FROM productos WHERE codigo_barras = ?", (codigo,))
                resultado = cursor.fetchone()
                if resultado and resultado[1] < 0: productos_negativos.append(f"• {resultado[0]} (Quedó en {resultado[1]})")

            conexion.commit()
            conexion.close()
            
            self.popup_fiado.destroy()
            messagebox.showinfo("📓 Fiado Registrado", mensaje_exito, parent=self)
            
            if productos_negativos:
                lista_nombres = "\n".join(productos_negativos)
                alerta_stock = "⚠️ Atención Encargado:\n\nEl fiado se registró bien, pero los siguientes productos quedaron con stock negativo. Por favor, revise la góndola:\n\n" + lista_nombres
                messagebox.showwarning("Control de Inventario", alerta_stock, parent=self)

            self.limpiar_carrito() 
        except Exception as e: messagebox.showerror("❌ Error Crítico", f"Ocurrió un problema en la base de datos:\n{e}", parent=self.popup_fiado)
    
    def editar_precio_carrito(self):
        seleccion = self.tabla_ticket.selection()
        if not seleccion:
            messagebox.showwarning("⚠️ Atención", "Primero seleccioná un producto de la lista haciendo clic sobre él.", parent=self)
            return

        if not self.pedir_autorizacion_admin():
            return

        item = seleccion[0]
        valores = self.tabla_ticket.item(item)['values']
        codigo_barras = valores[0]
        nombre_prod = valores[1]
        
        dialogo = ctk.CTkInputDialog(text=f"Ingresá el nuevo precio para:\n{nombre_prod}", title="Actualizar Precio")
        nuevo_precio_str = dialogo.get_input()
        self.lift() 

        if nuevo_precio_str is None or nuevo_precio_str.strip() == "": return  

        try:
            nuevo_precio = float(nuevo_precio_str.replace(',', '.'))
            confirmar = messagebox.askyesno("⚠️ Confirmar Precio", f"¿Estás seguro de que el nuevo precio para\n'{nombre_prod}' es ${nuevo_precio:.2f}?", parent=self)
            if not confirmar: return

            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            cursor.execute("UPDATE productos SET precio = ? WHERE codigo_barras = ?", (nuevo_precio, codigo_barras))
            conexion.commit()
            conexion.close()

            for fila in self.tabla_ticket.get_children():
                valores_fila = self.tabla_ticket.item(fila)['values']
                if valores_fila[0] == codigo_barras: 
                    self.tabla_ticket.item(fila, values=(codigo_barras, nombre_prod, f"{nuevo_precio:.2f}"))

            nuevo_total = 0.0
            for fila in self.tabla_ticket.get_children():
                precio_fila = float(self.tabla_ticket.item(fila)['values'][2]) 
                nuevo_total += precio_fila
                
            self.total_venta = nuevo_total
            self.lbl_monto_total.configure(text=f"$ {self.total_venta:.2f}")
            self.entry_codigo.focus()
            messagebox.showinfo("✅ Precio Actualizado", f"El precio de '{nombre_prod}' se actualizó a ${nuevo_precio:.2f} correctamente.", parent=self)

        except ValueError: messagebox.showerror("❌ Error", "Por favor, ingresá un número válido (ejemplo: 1500.50).", parent=self)
        except Exception as e: messagebox.showerror("❌ Error BD", f"Ocurrió un problema al guardar:\n{e}", parent=self)

    def aplicar_descuento(self):
        if not hasattr(self, 'total_venta') or self.total_venta <= 0:
            messagebox.showwarning("⚠️ Carrito Vacío", "No hay productos para aplicar un descuento.", parent=self)
            return

        if not self.pedir_autorizacion_admin():
            return

        dialogo = ctk.CTkInputDialog(text="Ingrese el porcentaje a descontar (Ejemplo: 10 para un 10%):", title="🎁 Aplicar Descuento")
        porcentaje_str = dialogo.get_input()
        self.lift()
        
        if not porcentaje_str: return 

        try:
            porcentaje = float(porcentaje_str.replace(',', '.'))
            if porcentaje <= 0 or porcentaje > 100:
                messagebox.showerror("❌ Error", "El porcentaje debe estar entre 1 y 100.", parent=self)
                return

            monto_descuento = (self.total_venta * porcentaje) / 100
            self.tabla_ticket.insert("", "end", values=("DESC", f"Descuento del {porcentaje:g}%", f"-{monto_descuento:.2f}"))

            nuevo_total = 0.0
            for fila in self.tabla_ticket.get_children():
                precio_fila = float(self.tabla_ticket.item(fila)['values'][2]) 
                nuevo_total += precio_fila
                
            self.total_venta = nuevo_total
            self.lbl_monto_total.configure(text=f"$ {self.total_venta:.2f}")
        except ValueError: messagebox.showerror("❌ Error", "Por favor, ingrese un número válido.", parent=self)

    def cobrar_mercado_pago(self):
        monto_total = getattr(self, "total_venta", 0) 
        if float(monto_total) <= 0:
            messagebox.showwarning("Carrito Vacío", "No hay productos para cobrar.", parent=self)
            return
            
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            cursor.execute("SELECT mp_token FROM config_local WHERE id = 1")
            datos_mp = cursor.fetchone()
            conexion.close()
            
            token = str(datos_mp[0]).strip() if datos_mp and datos_mp[0] else ""
            if not token:
                messagebox.showerror("Configuración Incompleta", "⛔ No tenés configurado Mercado Pago.\n\nEl dueño debe ir a:\nAjustes del Local > Mercado Pago\ny pegar su Access Token.", parent=self)
                return
                
            sdk = mercadopago.SDK(token)
            datos_cobro = {"items": [{"title": "Compra en Sistema Mercado", "quantity": 1, "unit_price": float(monto_total)}]}
            
            respuesta = sdk.preference().create(datos_cobro)
            link_pago = respuesta["response"]["init_point"]
            
            qr_crudo = qrcode.make(link_pago)
            img_qr_pil = qr_crudo.get_image().convert("RGB")
            
            ventana_qr = ctk.CTkToplevel(self)
            ventana_qr.title("Mercado Pago")
            ventana_qr.geometry("400x550")
            ventana_qr.resizable(False, False)
            ventana_qr.attributes("-topmost", True) 
            ventana_qr.grab_set() 
            
            lbl_titulo = ctk.CTkLabel(ventana_qr, text="Escaneá para pagar", font=("Roboto", 24, "bold"), text_color="#009EE3")
            lbl_titulo.pack(pady=(30, 10))
            lbl_monto = ctk.CTkLabel(ventana_qr, text=f"Total: ${monto_total:.2f}", font=("Roboto", 34, "bold"))
            lbl_monto.pack(pady=5)
            
            qr_ctk = ctk.CTkImage(light_image=img_qr_pil, dark_image=img_qr_pil, size=(280, 280))
            lbl_imagen = ctk.CTkLabel(ventana_qr, text="", image=qr_ctk)
            lbl_imagen.pack(pady=15)
            
            def confirmar_pago_manual():
                ventana_qr.destroy()
                self.ejecutar_cobro(medio_pago="MERCADO PAGO", con_afip=False, omitir_confirmacion=True)

            btn_confirmar = ctk.CTkButton(ventana_qr, text="✅ Confirmar Pago", font=("Roboto", 18, "bold"), height=50, fg_color="#10B981", hover_color="#059669", command=confirmar_pago_manual)
            btn_confirmar.pack(pady=10, fill="x", padx=40)
            
        except Exception as e: 
            messagebox.showerror("Error de Red", f"No se pudo contactar a Mercado Pago.\nRevisá que el Token sea válido y tengas internet.\n\nError: {e}", parent=self)

    def procesar_escaneo(self, event=None):
        codigo = self.entry_codigo.get().strip()
        self.entry_codigo.delete(0, 'end')
        if not codigo: return

        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            cursor.execute("SELECT codigo_barras, nombre, precio FROM productos WHERE codigo_barras = ?", (codigo,))
            producto = cursor.fetchone()

            if producto:
                codigo_db, nombre_db, precio_db = producto[0], producto[1], float(producto[2])
                if precio_db == 0.0:
                    if len(codigo) <= 4:
                        dialogo = ctk.CTkInputDialog(text=f"⚖️ Producto Pesable: {nombre_db}\n\nIngrese el monto que dio la balanza ($):", title="Precio Variable")
                        monto_str = dialogo.get_input()
                        self.lift()
                        if monto_str:
                            try:
                                monto = float(monto_str.replace(',', '.'))
                                if monto > 0: self.agregar_al_carrito(codigo_db, nombre_db, monto)
                                else: messagebox.showwarning("⚠️ Atención", "El monto debe ser mayor a cero.", parent=self)
                            except ValueError: messagebox.showerror("❌ Error", "Monto inválido. Use punto o coma para los centavos.", parent=self)
                        self.entry_codigo.focus()
                    else:
                        dialogo_nuevo = ctk.CTkInputDialog(text=f"⚠️ {nombre_db} vino del proveedor sin precio.\n\nIngrese el precio FIJO en góndola ($):", title="Fijar Precio Permanente")
                        nuevo_precio_str = dialogo_nuevo.get_input()
                        self.lift()
                        if nuevo_precio_str:
                            try:
                                nuevo_precio = float(nuevo_precio_str.replace(',', '.'))
                                if nuevo_precio > 0:
                                    mensaje = f"¿Guardar de forma permanente este precio?\n\n🛒 {nombre_db}\n💵 Precio: ${nuevo_precio:.2f}"
                                    if messagebox.askyesno("✅ Confirmar Precio Nuevo", mensaje, parent=self):
                                        if not self.pedir_autorizacion_admin(): return
                                        
                                        cursor.execute("UPDATE productos SET precio = ? WHERE codigo_barras = ?", (nuevo_precio, codigo_db))
                                        conexion.commit()
                                        self.agregar_al_carrito(codigo_db, nombre_db, nuevo_precio)
                                else: messagebox.showwarning("⚠️ Atención", "El precio debe ser mayor a cero.", parent=self)
                            except ValueError: messagebox.showerror("❌ Error", "Precio inválido. Use punto o coma para los centavos.", parent=self)
                        self.entry_codigo.focus()
                else: self.agregar_al_carrito(codigo_db, nombre_db, precio_db)
            else: self.alta_rapida(codigo, conexion, cursor)
        except Exception as e: messagebox.showerror("❌ Error", f"Error en base de datos:\n{e}", parent=self)
        finally:
            if 'conexion' in locals(): conexion.close()

    def agregar_al_carrito(self, codigo, nombre, precio):
        self.tabla_ticket.insert("", "end", values=(codigo, nombre, f"{precio:.2f}"))
        self.total_venta += precio
        self.lbl_monto_total.configure(text=f"$ {self.total_venta:.2f}")
        self.entry_codigo.focus()

    def borrar_seleccionado(self):
        seleccion = self.tabla_ticket.selection()
        if not seleccion:
            messagebox.showwarning("⚠️ Atención", "Haga clic en un producto del ticket para borrarlo.", parent=self)
            return
            
        if not self.pedir_autorizacion_admin():
            return
            
        for item in seleccion:
            valores = self.tabla_ticket.item(item)['values']
            precio_restar = float(valores[2])
            self.total_venta -= precio_restar
            self.tabla_ticket.delete(item)
        self.lbl_monto_total.configure(text=f"$ {self.total_venta:.2f}")
        self.entry_codigo.focus()

    def alta_rapida(self, codigo, conexion, cursor):
        if not self.pedir_autorizacion_admin():
            return

        if not codigo.isdigit():
            messagebox.showerror("❌ Error de Código", "Los códigos de barras o códigos cortos deben ser SOLO NÚMEROS.\n\nSi tipeó letras por accidente, borre y vuelva a intentarlo.", parent=self)
            return
        dialogo_nombre = ctk.CTkInputDialog(text=f"Producto no encontrado.\nIngrese el NOMBRE para el código: {codigo}", title="⚡ Alta Rápida")
        nuevo_nombre = dialogo_nombre.get_input()
        self.lift()
        
        if not nuevo_nombre or not nuevo_nombre.strip(): return 
        nuevo_nombre = nuevo_nombre.strip().upper()

        if len(codigo) <= 4:
            mensaje_pesable = f"¿Crear '{nuevo_nombre}' como producto PESABLE o SUELTO?\n(El sistema le pedirá el importe cada vez que lo cobre)."
            if messagebox.askyesno("⚖️ Confirmar Pesable", mensaje_pesable, parent=self):
                cursor.execute("INSERT INTO productos (codigo_barras, nombre, precio, stock, marca, cat1) VALUES (?, ?, 0, 0, 'Suelto', 'Pesable')", (codigo, nuevo_nombre))
                conexion.commit()
                messagebox.showinfo("✅ Listo", f"{nuevo_nombre} guardado exitosamente.\n\nVuelva a tipear el código {codigo} para cobrarlo.", parent=self)
        else:
            mensaje_nombre = f"¿Está seguro que el nombre es correcto?\n\n➡️ {nuevo_nombre}"
            if not messagebox.askyesno("⚠️ Confirmar Nombre", mensaje_nombre, parent=self): return 

            dialogo_precio = ctk.CTkInputDialog(text=f"Ingrese el PRECIO de venta ($)\npara: {nuevo_nombre}", title="⚡ Alta Rápida")
            precio_str = dialogo_precio.get_input()
            self.lift()
            if not precio_str: return

            try:
                nuevo_precio = float(precio_str.replace(',', '.'))
                mensaje_precio = f"¿Está seguro que el precio es correcto?\n\n➡️ ${nuevo_precio:.2f}"
                if messagebox.askyesno("⚠️ Confirmar Precio", mensaje_precio, parent=self):
                    cursor.execute("INSERT INTO productos (codigo_barras, nombre, precio, stock) VALUES (?, ?, ?, 0)", (codigo, nuevo_nombre, nuevo_precio))
                    conexion.commit()
                    self.agregar_al_carrito(codigo, nuevo_nombre, nuevo_precio)
            except ValueError: messagebox.showerror("❌ Error", "El precio ingresado no es válido. Use solo números.", parent=self)

    def procesar_fiado(self):
        if not hasattr(self, 'total_venta') or self.total_venta <= 0:
            messagebox.showwarning("⚠️ Carrito Vacío", "No hay productos en el ticket para anotar.", parent=self)
            return
        self.popup_fiado = ctk.CTkToplevel(self)
        self.popup_fiado.title("📓 Buscar Cliente")
        self.popup_fiado.geometry("400x250")
        self.popup_fiado.grab_set() 

        lbl = ctk.CTkLabel(self.popup_fiado, text="Ingrese Nombre o Alias del cliente:", font=("Roboto", 14, "bold"))
        lbl.pack(pady=(20, 10))
        self.entry_cliente = ctk.CTkEntry(self.popup_fiado, font=("Roboto", 16), width=300)
        self.entry_cliente.pack(pady=10)
        self.entry_cliente.focus() 

        btn_confirmar = ctk.CTkButton(self.popup_fiado, text="✅ Confirmar Fiado", fg_color="#2FA572", hover_color="#237a54", height=40, font=("Roboto", 14, "bold"), command=self.confirmar_fiado)
        btn_confirmar.pack(pady=20)

    def limpiar_carrito(self):
        for item in self.tabla_ticket.get_children(): self.tabla_ticket.delete(item)
        self.total_venta = 0.0
        self.lbl_monto_total.configure(text="$ 0.00")
        self.lift()
        self.focus_force()
        self.entry_codigo.focus()

    def imprimir_ticket(self):
        items = self.tabla_ticket.get_children()
        if not items:
            messagebox.showwarning("⚠️ Vacío", "No hay productos en el ticket para imprimir.", parent=self)
            return

        nombre_local = "M I N I M E R C A D O"
        direccion, telefono, instagram, mensaje_extra = "", "", "", ""
        
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            cursor.execute("SELECT nombre_fantasia, direccion, telefono, instagram, mensaje_ticket FROM config_local WHERE id = 1")
            datos_db = cursor.fetchone()
            if datos_db:
                if datos_db[0]: nombre_local = str(datos_db[0]).upper()
                if datos_db[1]: direccion = str(datos_db[1])
                if datos_db[2]: telefono = str(datos_db[2])
                if datos_db[3]: instagram = str(datos_db[3])
                if datos_db[4]: mensaje_extra = str(datos_db[4])
        except: pass
        finally:
            if 'conexion' in locals(): conexion.close()

        ticket = ""
        
        ticket += "================================\n"
        for linea in textwrap.wrap(nombre_local, 32):
            ticket += f"{linea.center(32)}\n"
        ticket += "================================\n"
        
        if direccion:
            for linea in textwrap.wrap(f"Dir: {direccion}", 32): ticket += f"{linea.center(32)}\n"
        if telefono:
            for linea in textwrap.wrap(f"Tel: {telefono}", 32): ticket += f"{linea.center(32)}\n"
        if instagram:
            for linea in textwrap.wrap(f"IG: {instagram}", 32): ticket += f"{linea.center(32)}\n"
            
        ticket += "--------------------------------\n"
        ticket += "      DOCUMENTO NO FISCAL       \n"
        ticket += "        CONTROL INTERNO         \n"
        ticket += "--------------------------------\n"
        
        fecha = datetime.now().strftime("%d/%m/%Y")
        hora = datetime.now().strftime("%H:%M:%S")
        ticket += f" Fecha {fecha}    Hora {hora}\n"
        ticket += "--------------------------------\n"
        
        for item in items:
            valores = self.tabla_ticket.item(item)['values']
            
            subtotal_str = str(valores[2])
            subtotal = float(subtotal_str.replace("$", "").replace(",", ""))
            desc = str(valores[1])
            
            cant = 1.0
            precio_u = subtotal
            
            ticket += f"{cant:.2f} x ${precio_u:.2f}\n"
            lineas_desc = textwrap.wrap(desc.upper(), width=22)
            for i, linea in enumerate(lineas_desc):
                if i == 0: ticket += f"{linea:<23}${subtotal:>8.2f}\n"
                else: ticket += f"{linea}\n"
                    
        ticket += "--------------------------------\n"
        ticket += f"TOTAL                  ${self.total_venta:>8.2f}\n"
        ticket += "================================\n"
        ticket += "          GRACIAS POR\n"
        ticket += "           SU COMPRA\n"
        
        if mensaje_extra.strip():
            ticket += "================================\n"
            for linea in textwrap.wrap(mensaje_extra.strip(), 32):
                ticket += f"{linea.center(32)}\n"
                
        ticket += "================================\n\n\n\n\n"

        try:
            ruta_archivo = os.path.join(tempfile.gettempdir(), "ticket_actual.txt")
            with open(ruta_archivo, "w", encoding="utf-8") as f:
                f.write(ticket)
            os.startfile(ruta_archivo, "print") 
        except Exception as e:
            messagebox.showerror("❌ Error de Impresora", f"Fallo al imprimir.\n\nDetalle: {e}", parent=self)

if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("100x100") 
    app.withdraw() 
    ventana = VentanaCaja(app) 
    app.mainloop()
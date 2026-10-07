import customtkinter as ctk
import sqlite3
import os
import mercadopago
import qrcode
import tempfile
import textwrap
from datetime import datetime
from tkinter import ttk, messagebox
from dotenv import load_dotenv
from afip import Afip  
from rutas import RUTA_DB, RUTA_CERT_CRT, RUTA_CERT_KEY

class VentanaCaja(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent  # 🛡️ Guardamos la referencia para saber el rol activo
        
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

        self.btn_imprimir = ctk.CTkButton(self.frame_top, text="[F11] 🖨️ Imprimir Ticket", height=40, font=("Roboto", 14, "bold"), fg_color="#546E7A", hover_color="#37474F", command=self.imprimir_ticket)
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
        # Atajo salvavidas: si pierden el foco, F12 lo devuelve al escáner al instante
        self.bind("<F12>", lambda event: self.entry_codigo.focus())

    # ==========================================
    # 🛑 CANDADO DE SUPERVISOR
    # ==========================================
    def pedir_autorizacion_admin(self):
        """Bloquea la acción si es cajero y exige el PIN del Dueño o Encargado."""
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
                    messagebox.showerror("❌ Denegado", "PIN Incorrecto o no tiene rango suficiente.")
                    entry_pin.delete(0, 'end') 
            except Exception as e:
                messagebox.showerror("Error", str(e))
                popup.destroy()
            finally:
                if 'conexion' in locals(): conexion.close()
                
        btn_confirmar = ctk.CTkButton(popup, text="🔓 Autorizar", fg_color="#F59E0B", hover_color="#D97706", font=("Roboto", 14, "bold"), command=verificar)
        btn_confirmar.pack(pady=10)
        
        entry_pin.bind("<Return>", verificar)
        self.wait_window(popup)
        return autorizado.get()

    # ==========================================
    # ⚙️ LÓGICA DE BASE DE DATOS Y ESCANEO
    # ==========================================

    def preparar_factura_arca(self):
        if not hasattr(self, 'total_venta') or self.total_venta <= 0:
            messagebox.showwarning("⚠️ Carrito Vacío", "No hay productos para facturar.")
            return

        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            cursor.execute("SELECT cuit, razon_social FROM config_local WHERE id = 1")
            datos = cursor.fetchone()
            
            cuit_db = str(datos[0]).strip() if datos and datos[0] else ""
            razon_db = str(datos[1]).strip() if datos and datos[1] else ""
            
            if not cuit_db or not razon_db:
                messagebox.showwarning("⚠️ Datos Incompletos", "Para facturar con ARCA, primero debe completar su CUIT y Razón Social en la ventana de Ajustes.")
                return
        except Exception as e:
            messagebox.showerror("Error", f"Error leyendo configuración: {e}")
            return
        finally:
            if 'conexion' in locals():
                conexion.close()

        self.popup_afip = ctk.CTkToplevel(self)
        self.popup_afip.title("🏛️ Facturación ARCA (Fase 2)")
        self.popup_afip.geometry("400x520") 
        self.popup_afip.grab_set()

        lbl_titulo = ctk.CTkLabel(self.popup_afip, text="Generar Comprobante", font=("Roboto", 20, "bold"))
        lbl_titulo.pack(pady=(20, 10))

        lbl_monto = ctk.CTkLabel(self.popup_afip, text=f"Monto a Facturar: ${self.total_venta:.2f}", font=("Roboto", 18, "bold"), text_color="#1E88E5")
        lbl_monto.pack(pady=(0, 20))

        ctk.CTkLabel(self.popup_afip, text="Tipo de Comprobante:", font=("Roboto", 14, "bold")).pack(anchor="w", padx=40, pady=(5, 0))
        combo_tipo = ctk.CTkComboBox(self.popup_afip, values=["Factura C", "Factura B", "Factura A"], font=("Roboto", 14), width=320)
        combo_tipo.pack(pady=5)

        ctk.CTkLabel(self.popup_afip, text="CUIT / CUIL del Cliente (Obligatorio Fact. A):", font=("Roboto", 14, "bold")).pack(anchor="w", padx=40, pady=(15, 0))
        entry_dni = ctk.CTkEntry(self.popup_afip, font=("Roboto", 16), width=320, placeholder_text="Consumidor Final dejar en blanco")
        entry_dni.pack(pady=5)
        entry_dni.focus()

        ctk.CTkLabel(self.popup_afip, text="Medio de Pago:", font=("Roboto", 14, "bold")).pack(anchor="w", padx=40, pady=(15, 0))
        combo_pago = ctk.CTkComboBox(self.popup_afip, values=["EFECTIVO", "MERCADO PAGO", "TRANSFERENCIA"], font=("Roboto", 14), width=320)
        combo_pago.pack(pady=5)

        def confirmar_emision():
            medio = combo_pago.get()
            tipo = combo_tipo.get()
            dni = entry_dni.get().strip()

            dni_limpio = dni.replace("-", "").replace(" ", "")

            if tipo == "Factura A":
                if not dni_limpio:
                    messagebox.showerror("Falta CUIT", "Para emitir Factura A es obligatorio ingresar el CUIT del cliente.")
                    return
                if len(dni_limpio) != 11 or not dni_limpio.isdigit():
                    messagebox.showerror("CUIT Inválido", "El CUIT del cliente para Factura A debe tener exactamente 11 números (sin guiones).")
                    return

            if not messagebox.askyesno("⚠️ Confirmar Emisión Fiscal", f"¿Confirma la emisión de la {tipo} por ${self.total_venta:.2f}?"):
                return
                
            self.popup_afip.title("⏳ Conectando con ARCA...")
            self.popup_afip.update() 
            
            try:
                conexion = sqlite3.connect(self.ruta_db)
                cursor = conexion.cursor()
                cursor.execute("SELECT cuit, condicion_iva FROM config_local WHERE id = 1")
                datos = cursor.fetchone()
                conexion.close()
                
                cuit_local_str = str(datos[0]).replace("-", "").replace(" ", "")
                if not cuit_local_str or cuit_local_str == "00000000000":
                    messagebox.showerror("Faltan Ajustes", "Debe ir a 'Ajustes del Local' y colocar su CUIT real.")
                    self.popup_afip.title("🏛 Facturación ARCA")
                    return
                    
                cuit_local = int(cuit_local_str)
                
                txt_cert = ""
                txt_key = ""
                if os.path.exists(RUTA_CERT_CRT) and os.path.exists(RUTA_CERT_KEY):
                    with open(RUTA_CERT_CRT, "r") as f: txt_cert = f.read()
                    with open(RUTA_CERT_KEY, "r") as f: txt_key = f.read()
                else:
                    messagebox.showerror("Faltan Certificados", "No se encontraron los archivos de certificado en la carpeta 'certificados'.")
                    self.popup_afip.destroy()
                    return

                afip = Afip({
                    "CUIT": cuit_local, 
                    "cert": txt_cert, 
                    "key": txt_key, 
                    "access_token": "3SVIUYG0Z4WE7Po750G4MJrMaJAYtWzrwViHtZPOOAHJetMHjNc2khldta7epTFW",
                    "production": False
                })

                cbte_tipo = 11 if tipo == "Factura C" else (6 if tipo == "Factura B" else 1)
                
                siguiente_numero = afip.ElectronicBilling.getLastVoucher(1, cbte_tipo) + 1
                fecha_hoy = int(datetime.now().strftime('%Y%m%d'))
                total_venta = float(self.total_venta)

                if cbte_tipo == 11: 
                    datos_factura = {
                        'CantReg': 1, 'PtoVta': 1, 'CbteTipo': 11, 'Concepto': 1,
                        'DocTipo': 99 if not dni_limpio else 80, 
                        'DocNro': 0 if not dni_limpio else int(dni_limpio),
                        'CbteDesde': siguiente_numero, 'CbteHasta': siguiente_numero, 'CbteFch': fecha_hoy,
                        'ImpTotal': total_venta, 'ImpTotConc': 0.0, 'ImpNeto': total_venta, 
                        'ImpOpEx': 0.0, 'ImpTrib': 0.0, 'ImpIVA': 0.0,
                        'CondicionIVAReceptorId': 5, 'MonId': 'PES', 'MonCotiz': 1.0
                    }
                else: 
                    neto = round(total_venta / 1.21, 2)
                    iva = round(total_venta - neto, 2)
                    datos_factura = {
                        'CantReg': 1, 'PtoVta': 1, 'CbteTipo': cbte_tipo, 'Concepto': 1,
                        'DocTipo': 80 if tipo == "Factura A" else (99 if not dni_limpio else 96),
                        'DocNro': int(dni_limpio) if dni_limpio else 0,
                        'CbteDesde': siguiente_numero, 'CbteHasta': siguiente_numero, 'CbteFch': fecha_hoy,
                        'ImpTotal': total_venta, 'ImpTotConc': 0.0, 'ImpNeto': neto, 
                        'ImpOpEx': 0.0, 'ImpTrib': 0.0, 'ImpIVA': iva,
                        'CondicionIVAReceptorId': 1 if tipo == "Factura A" else 5, 
                        'MonId': 'PES', 'MonCotiz': 1.0,
                        'Iva': [{'Id': 5, 'BaseImp': neto, 'Importe': iva}]
                    }

                respuesta = afip.ElectronicBilling.createVoucher(datos_factura)
                cae = respuesta['CAE']
                vto_cae = respuesta['CAEFchVto']

                self.imprimir_ticket_fiscal(tipo, dni, siguiente_numero, cae, vto_cae)

                self.popup_afip.destroy()
                self.ejecutar_cobro(medio_pago=medio, con_afip=True, omitir_confirmacion=True)
                
                messagebox.showinfo("✅ ARCA", f"¡Factura aprobada exitosamente!\nComprobante N°: {siguiente_numero}\nCAE: {cae}")

            except Exception as e:
                self.popup_afip.title("🏛️ Facturación ARCA") 
                messagebox.showerror("❌ Rechazado por ARCA", f"Error al emitir:\n{e}")
        
        btn_emitir = ctk.CTkButton(self.popup_afip, text="✅ Emitir y Cobrar", fg_color="#2FA572", hover_color="#238259", height=45, font=("Roboto", 14, "bold"), command=confirmar_emision)
        btn_emitir.pack(pady=25)

    def imprimir_ticket_fiscal(self, tipo_factura, dni_cliente, num_factura, cae, vto_cae):
        items = self.tabla_ticket.get_children()
        
        nombre = "LOCAL"
        razon, cuit, direccion, cond_iva, inicio_act = "", "", "", "", ""
        
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            cursor.execute("SELECT nombre_fantasia, razon_social, cuit, direccion, condicion_iva, inicio_actividades FROM config_local WHERE id = 1")
            d = cursor.fetchone()
            if d:
                nombre = str(d[0]).upper() if d[0] else "LOCAL"
                razon = str(d[1]).upper() if d[1] else ""
                cuit = str(d[2]) if d[2] else ""
                direccion = str(d[3]) if d[3] else ""
                cond_iva = str(d[4]) if d[4] else ""
                inicio_act = str(d[5]) if d[5] else ""
            conexion.close()
        except: pass

        ticket = ""
        if razon:
            for linea in textwrap.wrap(razon, 32): ticket += f"{linea.center(32)}\n"
                
        ticket += f"C.U.I.T. Nro.: {cuit}\n"
        ticket += f"Ing. Brutos: {cuit}\n"
        for linea in textwrap.wrap(f"Domicilio: {direccion}", 32): ticket += f"{linea}\n"
        ticket += f"Inicio de Actividades: {inicio_act}\n"
        ticket += f"IVA {cond_iva.upper()}\n"
        
        ticket += "--------------------------------\n"
        for linea in textwrap.wrap(nombre, 32): ticket += f"{linea.center(32)}\n"
        ticket += "--------------------------------\n"
        
        ticket += f" TIQUE {tipo_factura.upper()} Nro. 0001-{num_factura:08d}\n"
        fecha = datetime.now().strftime("%d/%m/%Y")
        hora = datetime.now().strftime("%H:%M:%S")
        ticket += f" Fecha {fecha}    Hora {hora}\n"
        
        if dni_cliente: ticket += f" CUIT/CUIL Nro.: {dni_cliente}\n"
        else: ticket += " A CONSUMIDOR FINAL\n"
        ticket += "--------------------------------\n"
        
        for item in items:
            valores = self.tabla_ticket.item(item, "values")
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
        ticket += "--------------------------------\n"
        ticket += f"CAE: {cae}\n"
        ticket += f"Vto. CAE: {vto_cae}\n\n"
        ticket += "          GRACIAS POR\n"
        ticket += "           SU COMPRA\n\n\n\n\n"

        fd, ruta_temp = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, 'w', encoding='utf-8') as f: f.write(ticket)
        try: os.startfile(ruta_temp, "print")
        except: pass

    def anotar_faltante(self):
        dialogo = ctk.CTkInputDialog(text="¿Qué producto falta en la góndola?", title="⚠️ Anotar Faltante")
        faltante = dialogo.get_input()
        
        if faltante and faltante.strip():
            try:
                ruta_txt = os.path.join(os.path.dirname(self.ruta_db), "lista_compras.txt")
                with open(ruta_txt, "a", encoding="utf-8") as f:
                    f.write(f"- {faltante.strip().upper()}\n")
                messagebox.showinfo("✅ Anotado", f"Se agregó a la lista:\n{faltante.upper()}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo anotar: {e}")
        self.entry_codigo.focus()

    def abrir_cobro_mixto(self):
        if not hasattr(self, 'total_venta') or self.total_venta <= 0:
            messagebox.showwarning("⚠️ Carrito Vacío", "No hay productos para cobrar.")
            return

        self.popup_mixto = ctk.CTkToplevel(self)
        self.popup_mixto.title("💵💳 Cobro Mixto")
        self.popup_mixto.geometry("400x520") 
        self.popup_mixto.grab_set()

        lbl_titulo = ctk.CTkLabel(self.popup_mixto, text="Dividir Pago", font=("Roboto", 20, "bold"))
        lbl_titulo.pack(pady=(20, 5))
        lbl_total = ctk.CTkLabel(self.popup_mixto, text=f"TOTAL DEL TICKET: ${self.total_venta:.2f}", font=("Roboto", 18, "bold"), text_color="#1E88E5")
        lbl_total.pack(pady=(0, 5))
        self.lbl_restante = ctk.CTkLabel(self.popup_mixto, text=f"FALTA CUBRIR: ${self.total_venta:.2f}", font=("Roboto", 18, "bold"), text_color="#D32F2F")
        self.lbl_restante.pack(pady=(0, 20))

        fuente_lbl = ("Roboto", 14, "bold")
        fuente_entry = ("Roboto", 16)

        ctk.CTkLabel(self.popup_mixto, text="Monto en EFECTIVO ($):", font=fuente_lbl, text_color="#2FA572").pack(pady=(5, 0))
        entry_efec = ctk.CTkEntry(self.popup_mixto, font=fuente_entry, justify="center", width=200)
        entry_efec.pack(pady=5)

        ctk.CTkLabel(self.popup_mixto, text="Monto en MERCADO PAGO ($):", font=fuente_lbl, text_color="#00A650").pack(pady=(10, 0))
        entry_mp = ctk.CTkEntry(self.popup_mixto, font=fuente_entry, justify="center", width=200)
        entry_mp.insert(0, "0")
        entry_mp.pack(pady=5)

        ctk.CTkLabel(self.popup_mixto, text="Monto en TRANSFERENCIA ($):", font=fuente_lbl, text_color="#009EE3").pack(pady=(10, 0))
        entry_transf = ctk.CTkEntry(self.popup_mixto, font=fuente_entry, justify="center", width=200)
        entry_transf.insert(0, "0")
        entry_transf.pack(pady=5)

        def calcular_restante(event=None):
            try:
                txt_efec = entry_efec.get().replace(',', '.').strip()
                txt_mp = entry_mp.get().replace(',', '.').strip()
                txt_transf = entry_transf.get().replace(',', '.').strip()

                val_efec = float(txt_efec) if txt_efec else 0.0
                val_mp = float(txt_mp) if txt_mp else 0.0
                val_transf = float(txt_transf) if txt_transf else 0.0

                suma = val_efec + val_mp + val_transf
                restante = self.total_venta - suma

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
                txt_efec = entry_efec.get().replace(',', '.').strip()
                txt_mp = entry_mp.get().replace(',', '.').strip()
                txt_transf = entry_transf.get().replace(',', '.').strip()

                val_efec = float(txt_efec) if txt_efec else 0.0
                val_mp = float(txt_mp) if txt_mp else 0.0
                val_transf = float(txt_transf) if txt_transf else 0.0

                suma_ingresada = val_efec + val_mp + val_transf

                if abs(suma_ingresada - self.total_venta) > 0.01:
                    diferencia = self.total_venta - suma_ingresada
                    if diferencia > 0: messagebox.showwarning("⚠ Faltan fondos", f"La suma no alcanza.\nFaltan cubrir: ${diferencia:.2f}")
                    else: messagebox.showwarning("⚠️ Sobran fondos", f"La suma supera el ticket por: ${abs(diferencia):.2f}\nPara cobro mixto, ingrese los montos exactos.")
                    return
                
                self.procesar_cobro_mixto(val_efec, val_mp, val_transf)
            except ValueError: messagebox.showerror("❌ Error", "Por favor, ingrese números válidos (Ej: 1500.50).")

        btn_confirmar = ctk.CTkButton(self.popup_mixto, text="✅ Confirmar Pago Mixto", fg_color="#F59E0B", hover_color="#D97706", height=45, font=("Roboto", 14, "bold"), command=confirmar_mixto)
        btn_confirmar.pack(pady=25)
        entry_efec.focus()

    def procesar_cobro_mixto(self, efec, mp, transf):
        self.carrito = []
        for item in self.tabla_ticket.get_children():
            valores = self.tabla_ticket.item(item)['values']
            self.carrito.append(valores[0])

        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if efec > 0: cursor.execute("INSERT INTO ventas (fecha, total, medio_pago) VALUES (?, ?, 'EFECTIVO')", (fecha_actual, efec))
            if mp > 0: cursor.execute("INSERT INTO ventas (fecha, total, medio_pago) VALUES (?, ?, 'MERCADO PAGO')", (fecha_actual, mp))
            if transf > 0: cursor.execute("INSERT INTO ventas (fecha, total, medio_pago) VALUES (?, ?, 'TRANSFERENCIA')", (fecha_actual, transf))

            productos_negativos = []
            for codigo in self.carrito:
                if str(codigo) == "DESC": continue 
                if len(str(codigo)) > 4: cursor.execute("UPDATE productos SET stock = stock - 1 WHERE codigo_barras = ?", (codigo,))
                
                cursor.execute("SELECT nombre, stock FROM productos WHERE codigo_barras = ?", (codigo,))
                resultado = cursor.fetchone()
                if resultado and resultado[1] < 0: productos_negativos.append(f"• {resultado[0]} (Quedó en {resultado[1]})")

            conexion.commit()
            conexion.close()
            self.popup_mixto.destroy()
            
            messagebox.showinfo("✅ Cobro Exitoso", "El pago dividido se procesó y guardó correctamente.")
            if productos_negativos:
                lista_nombres = "\n".join(productos_negativos)
                alerta_stock = "⚠️ Atención Encargado:\n\nEl cobro fue exitoso, pero los siguientes productos quedaron con stock negativo en góndola:\n\n" + lista_nombres
                messagebox.showwarning("Control de Inventario", alerta_stock)

            self.limpiar_carrito()
        except Exception as e: messagebox.showerror("❌ Error Crítico", f"Fallo en la base de datos:\n{e}")

    def editar_precio_carrito(self):
        seleccion = self.tabla_ticket.selection()
        if not seleccion:
            messagebox.showwarning("⚠️ Atención", "Primero seleccioná un producto de la lista haciendo clic sobre él.")
            return

        if not self.pedir_autorizacion_admin():
            return

        item = seleccion[0]
        valores = self.tabla_ticket.item(item)['values']
        codigo_barras = valores[0]
        nombre_prod = valores[1]
        
        dialogo = ctk.CTkInputDialog(text=f"Ingresá el nuevo precio para:\n{nombre_prod}", title="Actualizar Precio")
        nuevo_precio_str = dialogo.get_input()

        if nuevo_precio_str is None or nuevo_precio_str.strip() == "": return  

        try:
            nuevo_precio = float(nuevo_precio_str.replace(',', '.'))
            confirmar = messagebox.askyesno("⚠️ Confirmar Precio", f"¿Estás seguro de que el nuevo precio para\n'{nombre_prod}' es ${nuevo_precio:.2f}?")
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
            messagebox.showinfo("✅ Precio Actualizado", f"El precio de '{nombre_prod}' se actualizó a ${nuevo_precio:.2f} correctamente.")

        except ValueError: messagebox.showerror("❌ Error", "Por favor, ingresá un número válido (ejemplo: 1500.50).")
        except Exception as e: messagebox.showerror("❌ Error BD", f"Ocurrió un problema al guardar:\n{e}")

    def aplicar_descuento(self):
        if not hasattr(self, 'total_venta') or self.total_venta <= 0:
            messagebox.showwarning("⚠️ Carrito Vacío", "No hay productos para aplicar un descuento.")
            return

        if not self.pedir_autorizacion_admin():
            return

        dialogo = ctk.CTkInputDialog(text="Ingrese el porcentaje a descontar (Ejemplo: 10 para un 10%):", title="🎁 Aplicar Descuento")
        porcentaje_str = dialogo.get_input()
        if not porcentaje_str: return 

        try:
            porcentaje = float(porcentaje_str.replace(',', '.'))
            if porcentaje <= 0 or porcentaje > 100:
                messagebox.showerror("❌ Error", "El porcentaje debe estar entre 1 y 100.")
                return

            monto_descuento = (self.total_venta * porcentaje) / 100
            self.tabla_ticket.insert("", "end", values=("DESC", f"Descuento del {porcentaje:g}%", f"-{monto_descuento:.2f}"))

            nuevo_total = 0.0
            for fila in self.tabla_ticket.get_children():
                precio_fila = float(self.tabla_ticket.item(fila)['values'][2]) 
                nuevo_total += precio_fila
                
            self.total_venta = nuevo_total
            self.lbl_monto_total.configure(text=f"$ {self.total_venta:.2f}")
        except ValueError: messagebox.showerror("❌ Error", "Por favor, ingrese un número válido.")

    def cobrar_mercado_pago(self):
        monto_total = getattr(self, "total_venta", 0) 
        if float(monto_total) <= 0:
            messagebox.showwarning("Carrito Vacío", "No hay productos para cobrar.")
            return
        
        load_dotenv()
        token = os.getenv("MP_ACCESS_TOKEN")
        if not token:
            messagebox.showerror("Error de Seguridad", "Falta el token de Mercado Pago en el archivo .env")
            return
            
        sdk = mercadopago.SDK(token)
        datos_cobro = {"items": [{"title": "Compra en Sistema Mercado", "quantity": 1, "unit_price": float(monto_total)}]}

        try:
            respuesta = sdk.preference().create(datos_cobro)
            link_pago = respuesta["response"]["init_point"]
            
            qr_crudo = qrcode.make(link_pago)
            img_qr_pil = qr_crudo.get_image().convert("RGB")
            
            ventana_qr = ctk.CTkToplevel(self)
            ventana_qr.title("Mercado Pago")
            ventana_qr.geometry("400x550")
            ventana_qr.resizable(False, False)
            ventana_qr.attributes("-topmost", True) 
            
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
        except Exception as e: messagebox.showerror("Error de Red", f"No se pudo contactar a Mercado Pago:\n{e}")

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
                        if monto_str:
                            try:
                                monto = float(monto_str.replace(',', '.'))
                                if monto > 0: self.agregar_al_carrito(codigo_db, nombre_db, monto)
                                else: messagebox.showwarning("⚠️ Atención", "El monto debe ser mayor a cero.")
                            except ValueError: messagebox.showerror("❌ Error", "Monto inválido. Use punto o coma para los centavos.")
                        self.entry_codigo.focus()
                    else:
                        dialogo_nuevo = ctk.CTkInputDialog(text=f"⚠️ {nombre_db} vino del proveedor sin precio.\n\nIngrese el precio FIJO en góndola ($):", title="Fijar Precio Permanente")
                        nuevo_precio_str = dialogo_nuevo.get_input()
                        if nuevo_precio_str:
                            try:
                                nuevo_precio = float(nuevo_precio_str.replace(',', '.'))
                                if nuevo_precio > 0:
                                    mensaje = f"¿Guardar de forma permanente este precio?\n\n🛒 {nombre_db}\n💵 Precio: ${nuevo_precio:.2f}"
                                    if messagebox.askyesno("✅ Confirmar Precio Nuevo", mensaje):
                                        if not self.pedir_autorizacion_admin(): return
                                        
                                        cursor.execute("UPDATE productos SET precio = ? WHERE codigo_barras = ?", (nuevo_precio, codigo_db))
                                        conexion.commit()
                                        self.agregar_al_carrito(codigo_db, nombre_db, nuevo_precio)
                                else: messagebox.showwarning("⚠️ Atención", "El precio debe ser mayor a cero.")
                            except ValueError: messagebox.showerror("❌ Error", "Precio inválido. Use punto o coma para los centavos.")
                        self.entry_codigo.focus()
                else: self.agregar_al_carrito(codigo_db, nombre_db, precio_db)
            else: self.alta_rapida(codigo, conexion, cursor)
        except Exception as e: messagebox.showerror("❌ Error", f"Error en base de datos:\n{e}")
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
            messagebox.showwarning("⚠️ Atención", "Haga clic en un producto del ticket para borrarlo.")
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
            messagebox.showerror("❌ Error de Código", "Los códigos de barras o códigos cortos deben ser SOLO NÚMEROS.\n\nSi tipeó letras por accidente, borre y vuelva a intentarlo.")
            return
        dialogo_nombre = ctk.CTkInputDialog(text=f"Producto no encontrado.\nIngrese el NOMBRE para el código: {codigo}", title="⚡ Alta Rápida")
        nuevo_nombre = dialogo_nombre.get_input()
        
        if not nuevo_nombre or not nuevo_nombre.strip(): return 
        nuevo_nombre = nuevo_nombre.strip().upper()

        if len(codigo) <= 4:
            mensaje_pesable = f"¿Crear '{nuevo_nombre}' como producto PESABLE o SUELTO?\n(El sistema le pedirá el importe cada vez que lo cobre)."
            if messagebox.askyesno("⚖️ Confirmar Pesable", mensaje_pesable):
                cursor.execute("INSERT INTO productos (codigo_barras, nombre, precio, stock, marca, cat1) VALUES (?, ?, 0, 0, 'Suelto', 'Pesable')", (codigo, nuevo_nombre))
                conexion.commit()
                messagebox.showinfo("✅ Listo", f"{nuevo_nombre} guardado exitosamente.\n\nVuelva a tipear el código {codigo} para cobrarlo.")
        else:
            mensaje_nombre = f"¿Está seguro que el nombre es correcto?\n\n➡️ {nuevo_nombre}"
            if not messagebox.askyesno("⚠️ Confirmar Nombre", mensaje_nombre): return 

            dialogo_precio = ctk.CTkInputDialog(text=f"Ingrese el PRECIO de venta ($)\npara: {nuevo_nombre}", title="⚡ Alta Rápida")
            precio_str = dialogo_precio.get_input()
            if not precio_str: return

            try:
                nuevo_precio = float(precio_str.replace(',', '.'))
                mensaje_precio = f"¿Está seguro que el precio es correcto?\n\n➡️ ${nuevo_precio:.2f}"
                if messagebox.askyesno("⚠️ Confirmar Precio", mensaje_precio):
                    cursor.execute("INSERT INTO productos (codigo_barras, nombre, precio, stock) VALUES (?, ?, ?, 0)", (codigo, nuevo_nombre, nuevo_precio))
                    conexion.commit()
                    self.agregar_al_carrito(codigo, nuevo_nombre, nuevo_precio)
            except ValueError: messagebox.showerror("❌ Error", "El precio ingresado no es válido. Use solo números.")

    def procesar_fiado(self):
        if not hasattr(self, 'total_venta') or self.total_venta <= 0:
            messagebox.showwarning("⚠️ Carrito Vacío", "No hay productos en el ticket para anotar.")
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
                confirmacion = messagebox.askyesno("Nuevo Cliente", f"El cliente '{alias}' no existe en la libreta.\n\n¿Desea crear la cuenta y anotarle esta compra?")
                if confirmacion:
                    cursor.execute("INSERT INTO cuentas_corrientes (alias_cliente, deuda_total) VALUES (?, ?)", (alias, self.total_venta))
                    mensaje_exito = f"✅ Cuenta creada para {alias}.\nDeuda inicial: ${self.total_venta:.2f}"
                else:
                    conexion.close()
                    return

            productos_negativos = []
            for codigo in self.carrito:
                if str(codigo) == "DESC" or len(str(codigo)) <= 4: continue
                cursor.execute("UPDATE productos SET stock = stock - 1 WHERE codigo_barras = ?", (codigo,))
                cursor.execute("SELECT nombre, stock FROM productos WHERE codigo_barras = ?", (codigo,))
                resultado = cursor.fetchone()
                if resultado and resultado[1] < 0: productos_negativos.append(f"• {resultado[0]} (Quedó en {resultado[1]})")

            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO ventas (fecha, total, medio_pago) VALUES (?, ?, 'CUENTA_CORRIENTE')", (fecha_actual, self.total_venta))

            conexion.commit()
            conexion.close()
            messagebox.showinfo("📓 Fiado Registrado", mensaje_exito)
            
            if productos_negativos:
                lista_nombres = "\n".join(productos_negativos)
                alerta_stock = "⚠️ Atención Encargado:\n\nEl fiado se registró bien, pero los siguientes productos quedaron con stock negativo. Por favor, revise la góndola:\n\n" + lista_nombres
                messagebox.showwarning("Control de Inventario", alerta_stock)

            self.popup_fiado.destroy()
            self.limpiar_carrito() 
        except Exception as e: messagebox.showerror("❌ Error Crítico", f"Ocurrió un problema en la base de datos:\n{e}")

    def ejecutar_cobro(self, medio_pago, con_afip, omitir_confirmacion=False):
        self.carrito = []
        for item in self.tabla_ticket.get_children():
            valores = self.tabla_ticket.item(item)['values']
            self.carrito.append(valores[0])

        if not self.carrito:
            messagebox.showwarning("⚠️ Carrito Vacío", "No hay productos para cobrar.")
            return

        if not omitir_confirmacion:
            mensaje_confirmacion = f"¿Confirma la venta por ${self.total_venta:.2f}?\n\nMedio de Pago: {medio_pago}"
            confirmar = messagebox.askyesno("⚠️ Confirmar Venta", mensaje_confirmacion)
            if not confirmar: return 

        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO ventas (fecha, total, medio_pago) VALUES (?, ?, ?)", (fecha_actual, self.total_venta, medio_pago))
            
            productos_negativos = []
            for codigo in self.carrito:
                if str(codigo) == "DESC" or len(str(codigo)) <= 4: continue
                cursor.execute("UPDATE productos SET stock = stock - 1 WHERE codigo_barras = ?", (codigo,))
                cursor.execute("SELECT nombre, stock FROM productos WHERE codigo_barras = ?", (codigo,))
                resultado = cursor.fetchone()
                if resultado and resultado[1] < 0: productos_negativos.append(f"• {resultado[0]} (Quedó en {resultado[1]})")
                
            conexion.commit()
            mensaje = f"Venta exitosa por ${self.total_venta:.2f}\nMedio: {medio_pago}"
            messagebox.showinfo("✅ Venta Registrada", mensaje)
            
            if productos_negativos:
                lista_nombres = "\n".join(productos_negativos)
                alerta_stock = "⚠️ Atención Encargado:\n\nLa venta se registró bien, pero los siguientes productos quedaron con stock negativo. Por favor, revise la góndola:\n\n" + lista_nombres
                messagebox.showwarning("Control de Inventario", alerta_stock)
                
            self.limpiar_carrito() 
        except Exception as e: messagebox.showerror("❌ Error", f"Error al procesar la venta:\n{e}")
        finally:
            if 'conexion' in locals(): conexion.close()

    def limpiar_carrito(self):
        for item in self.tabla_ticket.get_children(): self.tabla_ticket.delete(item)
        self.total_venta = 0.0
        self.lbl_monto_total.configure(text="$ 0.00")
        self.entry_codigo.focus()

    def imprimir_ticket(self):
        items = self.tabla_ticket.get_children()
        if not items:
            messagebox.showwarning("⚠️ Vacío", "No hay productos en el ticket para imprimir.")
            return

        nombre_local = "M I N I M E R C A D O"
        direccion, telefono, instagram = "", "", ""
        
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            cursor.execute("SELECT nombre_fantasia, direccion, telefono, instagram FROM config_local WHERE id = 1")
            datos_db = cursor.fetchone()
            if datos_db:
                if datos_db[0]: nombre_local = str(datos_db[0]).upper()
                if datos_db[1]: direccion = str(datos_db[1])
                if datos_db[2]: telefono = str(datos_db[2])
                if datos_db[3]: instagram = str(datos_db[3])
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
        ticket += "           SU COMPRA\n\n\n\n\n"

        try:
            ruta_archivo = os.path.join(tempfile.gettempdir(), "ticket_actual.txt")
            with open(ruta_archivo, "w", encoding="utf-8") as f:
                f.write(ticket)
            os.startfile(ruta_archivo, "print") 
        except Exception as e:
            messagebox.showerror("❌ Error de Impresora", f"Fallo al imprimir.\n\nDetalle: {e}")

if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("100x100") 
    app.withdraw() 
    ventana = VentanaCaja(app) 
    app.mainloop()
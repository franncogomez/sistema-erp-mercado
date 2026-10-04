import customtkinter as ctk
import sqlite3
import os
import tkinter.messagebox as messagebox
import mercadopago
import qrcode
import customtkinter as ctk
from datetime import datetime
from tkinter import ttk
from tkinter import messagebox
from PIL import Image
from dotenv import load_dotenv

class VentanaCaja(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("🛒 Terminal de Punto de Venta (Caja)")
        self.geometry("1000x650") # Un poco más amplia para que todo respire mejor
        self.grab_set() 

        # --- VARIABLES DE MEMORIA ---
        self.carrito = []
        self.total_venta = 0.0
        self.ruta_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sistema_mercado.db")

        # ==========================================
        # 🟢 SECCIÓN SUPERIOR (Buscador / Escáner e Impresión)
        # ==========================================
        self.frame_top = ctk.CTkFrame(self)
        self.frame_top.pack(pady=15, padx=20, fill="x")

        self.lbl_escaner = ctk.CTkLabel(self.frame_top, text="🔍 Código de Barras:", font=("Roboto", 16, "bold"))
        self.lbl_escaner.pack(side="left", padx=10, pady=15)

        self.entry_codigo = ctk.CTkEntry(self.frame_top, width=300, font=("Roboto", 16), placeholder_text="Pase el producto...")
        self.entry_codigo.pack(side="left", padx=10, pady=15)
        self.entry_codigo.focus() 
        self.entry_codigo.bind("<Return>", self.procesar_escaneo)

        # 🖨️ Movimos el botón de Imprimir Ticket acá arriba (Aprovechamos el espacio muerto)
        self.btn_imprimir = ctk.CTkButton(self.frame_top, text="🖨️ Imprimir Ticket No Fiscal", height=40, font=("Roboto", 14, "bold"), fg_color="#546E7A", hover_color="#37474F", command=self.imprimir_ticket)
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

        self.btn_borrar_item = ctk.CTkButton(self.frame_lista, text="🗑️ Quitar Seleccionado", fg_color="#D32F2F", hover_color="#B71C1C", height=40, font=("Roboto", 14, "bold"), command=self.borrar_seleccionado)
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

        # 💵 MÉTODOS DE PAGO (Botones Uniformes)
        self.btn_cobrar = ctk.CTkButton(self.frame_cobro, text="💵 COBRO EFECTIVO", height=40, font=("Roboto", 14, "bold"), fg_color="#2FA572", hover_color="#238259", command=lambda: self.ejecutar_cobro("EFECTIVO", False))
        self.btn_cobrar.pack(pady=5, padx=20, fill="x")

        self.btn_qr = ctk.CTkButton(self.frame_cobro, text="💳 MERCADO PAGO QR", height=40, font=("Roboto", 14, "bold"), fg_color="#009EE3", hover_color="#007EBE", command=self.cobrar_mercado_pago)
        self.btn_qr.pack(pady=5, padx=20, fill="x")

        self.btn_mp = ctk.CTkButton(self.frame_cobro, text="🏦 TRANSFERENCIA BANCARIA", height=40, font=("Roboto", 13, "bold"), fg_color="#1976D2", hover_color="#115293", command=lambda: self.ejecutar_cobro("TRANSFERENCIA", False))
        self.btn_mp.pack(pady=5, padx=20, fill="x")

        self.btn_mixto = ctk.CTkButton(self.frame_cobro, text="💵💳 COBRO MIXTO", height=40, font=("Roboto", 13, "bold"), fg_color="#455A64", hover_color="#37474F", command=self.abrir_cobro_mixto)
        self.btn_mixto.pack(pady=5, padx=20, fill="x")

        self.btn_fiado = ctk.CTkButton(self.frame_cobro, text="📓 ANOTAR FIADO", height=40, font=("Roboto", 13, "bold"), fg_color="#5C6BC0", hover_color="#3F51B5", command=self.procesar_fiado)
        self.btn_fiado.pack(pady=5, padx=20, fill="x")

        self.btn_arca = ctk.CTkButton(self.frame_cobro, text="🏛️ FACTURACIÓN ARCA", height=40, font=("Roboto", 13, "bold"), fg_color="#454545", hover_color="#333333", command=self.preparar_factura_arca)
        self.btn_arca.pack(pady=5, padx=20, fill="x")

        # 🛠️ ACCIONES ESPECIALES (Ancladas abajo)
        self.btn_descuento = ctk.CTkButton(self.frame_cobro, text="🎁 Aplicar Descuento %", height=35, font=("Roboto", 13, "bold"), fg_color="#8E24AA", hover_color="#6A1B9A", command=self.aplicar_descuento)
        self.btn_descuento.pack(side="bottom", pady=(5, 15), padx=20, fill="x")

        self.btn_faltante = ctk.CTkButton(self.frame_cobro, text="⚠️ Anotar Faltante", height=35, font=("Roboto", 13, "bold"), fg_color="#F59E0B", hover_color="#D97706", command=self.anotar_faltante)
        self.btn_faltante.pack(side="bottom", pady=(5, 0), padx=20, fill="x")
        
        self.btn_editar_precio = ctk.CTkButton(self.frame_cobro, text="✏️ Editar Precio Renglón", height=35, font=("Roboto", 13, "bold"), fg_color="#546E7A", hover_color="#455A64", command=self.editar_precio_carrito)
        self.btn_editar_precio.pack(side="bottom", pady=(5, 0), padx=20, fill="x")

    # ==========================================
    # ⚙️ LÓGICA DE BASE DE DATOS Y ESCANEO
    # ==========================================

    def preparar_factura_arca(self):
        import customtkinter as ctk
        from tkinter import messagebox
        import sqlite3

        if not hasattr(self, 'total_venta') or self.total_venta <= 0:
            messagebox.showwarning("⚠️ Carrito Vacío", "No hay productos para facturar.")
            return

        # --- 🛡️ BARRERA DE SEGURIDAD FISCAL ---
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            cursor.execute("SELECT cuit, razon_social FROM config_local WHERE id = 1")
            datos = cursor.fetchone()
            
            # 🛠️ CORRECCIÓN: Manejo seguro de valores nulos (None)
            cuit_db = str(datos[0]).strip() if datos and datos[0] else ""
            razon_db = str(datos[1]).strip() if datos and datos[1] else ""
            
            # Verificamos que existan y no estén en blanco
            if not cuit_db or not razon_db:
                messagebox.showwarning("⚠️ Datos Incompletos", "Para facturar con ARCA, primero debe completar su CUIT y Razón Social en la ventana de Ajustes.")
                return
        except Exception as e:
            messagebox.showerror("Error", f"Error leyendo configuración: {e}")
            return
        finally:
            if 'conexion' in locals():
                conexion.close()

        # --- 🧾 VENTANA DE FACTURACIÓN (Si pasó la barrera) ---
        self.popup_afip = ctk.CTkToplevel(self)
        self.popup_afip.title("🏛️ Facturación ARCA (Fase 2)")
        self.popup_afip.geometry("400x520") # Más alta para que entre el Tipo de Factura
        self.popup_afip.grab_set()

        lbl_titulo = ctk.CTkLabel(self.popup_afip, text="Generar Comprobante", font=("Roboto", 20, "bold"))
        lbl_titulo.pack(pady=(20, 10))

        lbl_monto = ctk.CTkLabel(self.popup_afip, text=f"Monto a Facturar: ${self.total_venta:.2f}", font=("Roboto", 18, "bold"), text_color="#1E88E5")
        lbl_monto.pack(pady=(0, 20))

        # NUEVO: Tipo de Factura
        ctk.CTkLabel(self.popup_afip, text="Tipo de Comprobante:", font=("Roboto", 14, "bold")).pack(anchor="w", padx=40, pady=(5, 0))
        combo_tipo = ctk.CTkComboBox(self.popup_afip, values=["Factura C", "Factura B", "Factura A"], font=("Roboto", 14), width=320)
        combo_tipo.pack(pady=5)

        ctk.CTkLabel(self.popup_afip, text="CUIT / DNI del Cliente (Obligatorio para Fact. A):", font=("Roboto", 14, "bold")).pack(anchor="w", padx=40, pady=(15, 0))
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

            if tipo == "Factura A" and not dni:
                messagebox.showerror("Falta CUIT", "Para emitir Factura A es obligatorio ingresar el CUIT del cliente.")
                return

            mensaje = f"¿Confirma la emisión de la {tipo} por ${self.total_venta:.2f} abonada con {medio}?"
            
            if messagebox.askyesno("⚠️ Confirmar Emisión Fiscal", mensaje):
                self.popup_afip.destroy()
                self.ejecutar_cobro(medio_pago=medio, con_afip=True, omitir_confirmacion=True)
                messagebox.showinfo("☁️ ARCA", f"Simulación ARCA: El sistema enviaría los datos de la {tipo} a los servidores de la ex AFIP.")

        btn_emitir = ctk.CTkButton(self.popup_afip, text="✅ Emitir y Cobrar", fg_color="#2FA572", hover_color="#238259", height=45, font=("Roboto", 14, "bold"), command=confirmar_emision)
        btn_emitir.pack(pady=25)

    def anotar_faltante(self):
        import customtkinter as ctk
        import os
        from tkinter import messagebox
        
        dialogo = ctk.CTkInputDialog(text="¿Qué producto falta en la góndola?", title="⚠️ Anotar Faltante")
        faltante = dialogo.get_input()
        
        if faltante and faltante.strip():
            try:
                ruta_txt = os.path.join(os.path.dirname(self.ruta_db), "lista_compras.txt")
                # El modo "a" (append) agrega al final sin borrar lo anterior
                with open(ruta_txt, "a", encoding="utf-8") as f:
                    f.write(f"- {faltante.strip().upper()}\n")
                    
                messagebox.showinfo("✅ Anotado", f"Se agregó a la lista:\n{faltante.upper()}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo anotar: {e}")
                
        self.entry_codigo.focus()

    def abrir_cobro_mixto(self):
        import customtkinter as ctk
        from tkinter import messagebox

        if not hasattr(self, 'total_venta') or self.total_venta <= 0:
            messagebox.showwarning("⚠️ Carrito Vacío", "No hay productos para cobrar.")
            return

        self.popup_mixto = ctk.CTkToplevel(self)
        self.popup_mixto.title("💵💳 Cobro Mixto")
        self.popup_mixto.geometry("400x520") # Lo hicimos un poquito más alto para que entre el cartel nuevo
        self.popup_mixto.grab_set()

        lbl_titulo = ctk.CTkLabel(self.popup_mixto, text="Dividir Pago", font=("Roboto", 20, "bold"))
        lbl_titulo.pack(pady=(20, 5))

        lbl_total = ctk.CTkLabel(self.popup_mixto, text=f"TOTAL DEL TICKET: ${self.total_venta:.2f}", font=("Roboto", 18, "bold"), text_color="#1E88E5")
        lbl_total.pack(pady=(0, 5))

        # 👇 NUEVO: Etiqueta dinámica que muestra en tiempo real cuánto falta
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

        # 👇 NUEVO: Motor de cálculo automático
        def calcular_restante(event=None):
            try:
                # Leemos los 3 casilleros. Si están vacíos, los tratamos como 0.
                txt_efec = entry_efec.get().replace(',', '.').strip()
                txt_mp = entry_mp.get().replace(',', '.').strip()
                txt_transf = entry_transf.get().replace(',', '.').strip()

                val_efec = float(txt_efec) if txt_efec else 0.0
                val_mp = float(txt_mp) if txt_mp else 0.0
                val_transf = float(txt_transf) if txt_transf else 0.0

                suma = val_efec + val_mp + val_transf
                restante = self.total_venta - suma

                # Actualizamos los colores y el texto al instante
                if restante > 0.01:
                    self.lbl_restante.configure(text=f"FALTA CUBRIR: ${restante:.2f}", text_color="#D32F2F") # Rojo
                elif restante < -0.01:
                    self.lbl_restante.configure(text=f"SOBRA / VUELTO: ${abs(restante):.2f}", text_color="#F59E0B") # Naranja
                else:
                    self.lbl_restante.configure(text="¡MONTO EXACTO! ✅", text_color="#2FA572") # Verde
            except ValueError:
                self.lbl_restante.configure(text="⚠️ Ingrese solo números", text_color="#D32F2F")

        # Conectamos la función para que se dispare cada vez que el cajero toca el teclado
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
                    if diferencia > 0:
                        messagebox.showwarning("⚠️️ Faltan fondos", f"La suma no alcanza.\nFaltan cubrir: ${diferencia:.2f}")
                    else:
                        messagebox.showwarning("⚠️ Sobran fondos", f"La suma supera el ticket por: ${abs(diferencia):.2f}\nPara cobro mixto, ingrese los montos exactos.")
                    return
                
                self.procesar_cobro_mixto(val_efec, val_mp, val_transf)

            except ValueError:
                messagebox.showerror("❌ Error", "Por favor, ingrese números válidos (Ej: 1500.50).")

        btn_confirmar = ctk.CTkButton(self.popup_mixto, text="✅ Confirmar Pago Mixto", fg_color="#F59E0B", hover_color="#D97706", height=45, font=("Roboto", 14, "bold"), command=confirmar_mixto)
        btn_confirmar.pack(pady=25)

        # Truco UX: Mandamos el cursor directo al primer cuadro para que el cajero empiece a tipear al instante
        entry_efec.focus()


    def procesar_cobro_mixto(self, efec, mp, transf):
        import sqlite3
        from datetime import datetime
        from tkinter import messagebox

        self.carrito = []
        for item in self.tabla_ticket.get_children():
            valores = self.tabla_ticket.item(item)['values']
            self.carrito.append(valores[0])

        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if efec > 0:
                cursor.execute("INSERT INTO ventas (fecha, total, medio_pago) VALUES (?, ?, 'EFECTIVO')", (fecha_actual, efec))
            if mp > 0:
                cursor.execute("INSERT INTO ventas (fecha, total, medio_pago) VALUES (?, ?, 'MERCADO PAGO')", (fecha_actual, mp))
            if transf > 0:
                cursor.execute("INSERT INTO ventas (fecha, total, medio_pago) VALUES (?, ?, 'TRANSFERENCIA')", (fecha_actual, transf))

            productos_negativos = []
            for codigo in self.carrito:
                if str(codigo) == "DESC":
                    continue 

                if len(str(codigo)) > 4:
                    cursor.execute("UPDATE productos SET stock = stock - 1 WHERE codigo_barras = ?", (codigo,))
                
                cursor.execute("SELECT nombre, stock FROM productos WHERE codigo_barras = ?", (codigo,))
                resultado = cursor.fetchone()
                if resultado and resultado[1] < 0:
                    productos_negativos.append(f"• {resultado[0]} (Quedó en {resultado[1]})")

            conexion.commit()
            conexion.close()

            self.popup_mixto.destroy()
            
            messagebox.showinfo("✅ Cobro Exitoso", "El pago dividido se procesó y guardó correctamente.")
            
            if productos_negativos:
                lista_nombres = "\n".join(productos_negativos)
                alerta_stock = (
                    "⚠️ Atención Encargado:\n\n"
                    "El cobro fue exitoso, pero los siguientes productos "
                    "quedaron con stock negativo en góndola:\n\n"
                    f"{lista_nombres}"
                )
                messagebox.showwarning("Control de Inventario", alerta_stock)

            self.limpiar_carrito()

        except Exception as e:
            messagebox.showerror("❌ Error Crítico", f"Fallo en la base de datos:\n{e}")

    def editar_precio_carrito(self):
        seleccion = self.tabla_ticket.selection()
        if not seleccion:
            from tkinter import messagebox
            messagebox.showwarning("⚠️ Atención", "Primero seleccioná un producto de la lista haciendo clic sobre él.")
            return

        item = seleccion[0]
        valores = self.tabla_ticket.item(item)['values']
        
        codigo_barras = valores[0]
        nombre_prod = valores[1]
        
        import customtkinter as ctk
        dialogo = ctk.CTkInputDialog(text=f"Ingresá el nuevo precio para:\n{nombre_prod}", title="Actualizar Precio")
        nuevo_precio_str = dialogo.get_input()

        if nuevo_precio_str is None or nuevo_precio_str.strip() == "":
            return  

        try:
            nuevo_precio = float(nuevo_precio_str.replace(',', '.'))
            
            from tkinter import messagebox
            confirmar = messagebox.askyesno("⚠️ Confirmar Precio", f"¿Estás seguro de que el nuevo precio para\n'{nombre_prod}' es ${nuevo_precio:.2f}?")
            
            if not confirmar: return

            import sqlite3
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

            from tkinter import messagebox
            messagebox.showinfo("✅ Precio Actualizado", f"El precio de '{nombre_prod}' se actualizó a ${nuevo_precio:.2f} correctamente.")

        except ValueError:
            from tkinter import messagebox
            messagebox.showerror("❌ Error", "Por favor, ingresá un número válido (ejemplo: 1500.50).")
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("❌ Error BD", f"Ocurrió un problema al guardar:\n{e}")

    def aplicar_descuento(self):
        if not hasattr(self, 'total_venta') or self.total_venta <= 0:
            from tkinter import messagebox
            messagebox.showwarning("⚠️ Carrito Vacío", "No hay productos para aplicar un descuento.")
            return

        import customtkinter as ctk
        dialogo = ctk.CTkInputDialog(text="Ingrese el porcentaje a descontar (Ejemplo: 10 para un 10%):", title="🎁 Aplicar Descuento")
        porcentaje_str = dialogo.get_input()

        if not porcentaje_str: return 

        try:
            porcentaje = float(porcentaje_str.replace(',', '.'))
            
            if porcentaje <= 0 or porcentaje > 100:
                from tkinter import messagebox
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

        except ValueError:
            from tkinter import messagebox
            messagebox.showerror("❌ Error", "Por favor, ingrese un número válido.")

    def cobrar_mercado_pago(self):
        monto_total = getattr(self, "total_venta", 0) 
        
        if float(monto_total) <= 0:
            messagebox.showwarning("Carrito Vacío", "No hay productos para cobrar.")
            return

        print(f"🔌 Generando QR de Mercado Pago por ${monto_total}...")
        
        load_dotenv()
        token = os.getenv("MP_ACCESS_TOKEN")
        if not token:
            messagebox.showerror("Error de Seguridad", "Falta el token de Mercado Pago en el archivo .env")
            return
            
        sdk = mercadopago.SDK(token)
        
        datos_cobro = {
            "items": [
                {
                    "title": "Compra en Sistema Mercado",
                    "quantity": 1,
                    "unit_price": float(monto_total)
                }
            ]
        }

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
                print("✅ Pago confirmado en mostrador.")

            btn_confirmar = ctk.CTkButton(ventana_qr, text="✅ Confirmar Pago", font=("Roboto", 18, "bold"), height=50, fg_color="#10B981", hover_color="#059669", command=confirmar_pago_manual)
            btn_confirmar.pack(pady=10, fill="x", padx=40)

        except Exception as e:
            messagebox.showerror("Error de Red", f"No se pudo contactar a Mercado Pago:\n{e}")

    def procesar_escaneo(self, event=None):
        import sqlite3
        import customtkinter as ctk
        from tkinter import messagebox

        codigo = self.entry_codigo.get().strip()
        self.entry_codigo.delete(0, 'end')
        if not codigo: return

        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            
            cursor.execute("SELECT codigo_barras, nombre, precio FROM productos WHERE codigo_barras = ?", (codigo,))
            producto = cursor.fetchone()

            if producto:
                codigo_db = producto[0]
                nombre_db = producto[1]
                precio_db = float(producto[2])

                if precio_db == 0.0:
                    if len(codigo) <= 4:
                        dialogo = ctk.CTkInputDialog(text=f"⚖️ Producto Pesable: {nombre_db}\n\nIngrese el monto que dio la balanza ($):", title="Precio Variable")
                        monto_str = dialogo.get_input()
                        
                        if monto_str:
                            try:
                                monto = float(monto_str.replace(',', '.'))
                                if monto > 0:
                                    self.agregar_al_carrito(codigo_db, nombre_db, monto)
                                else:
                                    messagebox.showwarning("⚠️ Atención", "El monto debe ser mayor a cero.")
                            except ValueError:
                                messagebox.showerror("❌ Error", "Monto inválido. Use punto o coma para los centavos.")
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
                                        cursor.execute("UPDATE productos SET precio = ? WHERE codigo_barras = ?", (nuevo_precio, codigo_db))
                                        conexion.commit()
                                        self.agregar_al_carrito(codigo_db, nombre_db, nuevo_precio)
                                else:
                                    messagebox.showwarning("⚠️ Atención", "El precio debe ser mayor a cero.")
                            except ValueError:
                                messagebox.showerror("❌ Error", "Precio inválido. Use punto o coma para los centavos.")
                        self.entry_codigo.focus()
                        
                else:
                    self.agregar_al_carrito(codigo_db, nombre_db, precio_db)
                    
            else:
                self.alta_rapida(codigo, conexion, cursor)

        except Exception as e:
            messagebox.showerror("❌ Error", f"Error en base de datos:\n{e}")
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
        
        for item in seleccion:
            valores = self.tabla_ticket.item(item)['values']
            precio_restar = float(valores[2])
            
            self.total_venta -= precio_restar
            self.tabla_ticket.delete(item)
            
        self.lbl_monto_total.configure(text=f"$ {self.total_venta:.2f}")
        self.entry_codigo.focus()

    def alta_rapida(self, codigo, conexion, cursor):
        import customtkinter as ctk
        from tkinter import messagebox

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
            except ValueError:
                messagebox.showerror("❌ Error", "El precio ingresado no es válido. Use solo números.")

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
        from datetime import datetime
        from tkinter import messagebox
        import sqlite3
        
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
                if resultado and resultado[1] < 0:
                    productos_negativos.append(f"• {resultado[0]} (Quedó en {resultado[1]})")

            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO ventas (fecha, total, medio_pago) VALUES (?, ?, 'CUENTA_CORRIENTE')", (fecha_actual, self.total_venta))

            conexion.commit()
            conexion.close()

            messagebox.showinfo("📓 Fiado Registrado", mensaje_exito)
            
            if productos_negativos:
                lista_nombres = "\n".join(productos_negativos)
                alerta_stock = (
                    "⚠️ Atención Encargado:\n\n"
                    "El fiado se registró bien, pero los siguientes productos "
                    "quedaron con stock negativo. Por favor, revise la góndola:\n\n"
                    f"{lista_nombres}"
                )
                messagebox.showwarning("Control de Inventario", alerta_stock)

            self.popup_fiado.destroy()
            self.limpiar_carrito() 

        except Exception as e:
            messagebox.showerror("❌ Error Crítico", f"Ocurrió un problema en la base de datos:\n{e}")

    # ==========================================
    # 💰 FUNCIÓN DE COBRO REAL (¡REPARADA!)
    # ==========================================

    def ejecutar_cobro(self, medio_pago, con_afip, omitir_confirmacion=False):
        # 1. Armamos la lista de códigos SIN tocar la base de datos todavía
        self.carrito = []
        for item in self.tabla_ticket.get_children():
            valores = self.tabla_ticket.item(item)['values']
            self.carrito.append(valores[0])

        if not self.carrito:
            messagebox.showwarning("⚠️ Carrito Vacío", "No hay productos para cobrar.")
            return

        # 2. Confirmación al cajero (salvo que venga del QR de Mercado Pago)
        if not omitir_confirmacion:
            mensaje_confirmacion = f"¿Confirma la venta por ${self.total_venta:.2f}?\n\nMedio de Pago: {medio_pago}"
            confirmar = messagebox.askyesno("⚠️ Confirmar Venta", mensaje_confirmacion)
            if not confirmar: return 

        # 3. Guardado en Base de Datos
        try:
            import sqlite3
            from datetime import datetime
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            
            # ¡Se inyecta la fecha correcta que antes faltaba!
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO ventas (fecha, total, medio_pago) VALUES (?, ?, ?)", (fecha_actual, self.total_venta, medio_pago))
            
            # --- 🕵️‍♂️ MAGIA DEL STOCK NEGATIVO ---
            productos_negativos = []
            
            for codigo in self.carrito:
                # Si es un descuento o un producto pesable (<= 4 dígitos), lo saltamos
                if str(codigo) == "DESC" or len(str(codigo)) <= 4:
                    continue

                cursor.execute("UPDATE productos SET stock = stock - 1 WHERE codigo_barras = ?", (codigo,))
                cursor.execute("SELECT nombre, stock FROM productos WHERE codigo_barras = ?", (codigo,))
                resultado = cursor.fetchone()
                
                if resultado and resultado[1] < 0:
                    productos_negativos.append(f"• {resultado[0]} (Quedó en {resultado[1]})")
                
            conexion.commit()
            
            mensaje = f"Venta exitosa por ${self.total_venta:.2f}\nMedio: {medio_pago}"
            messagebox.showinfo("✅ Venta Registrada", mensaje)
            
            if productos_negativos:
                lista_nombres = "\n".join(productos_negativos)
                alerta_stock = (
                    "⚠️ Atención Encargado:\n\n"
                    "La venta se registró bien, pero los siguientes productos "
                    "quedaron con stock negativo. Por favor, revise la góndola:\n\n"
                    f"{lista_nombres}"
                )
                messagebox.showwarning("Control de Inventario", alerta_stock)
                
            self.limpiar_carrito() 

        except Exception as e:
            messagebox.showerror("❌ Error", f"Error al procesar la venta:\n{e}")
        finally:
            if 'conexion' in locals(): conexion.close()

    def limpiar_carrito(self):
        for item in self.tabla_ticket.get_children():
            self.tabla_ticket.delete(item)
        self.total_venta = 0.0
        self.lbl_monto_total.configure(text="$ 0.00")
        self.entry_codigo.focus()

    def imprimir_ticket(self):
        from tkinter import messagebox
        import tempfile
        import os
        import textwrap 
        import sqlite3

        items = self.tabla_ticket.get_children()
        if not items:
            messagebox.showwarning("⚠️ Vacío", "No hay productos en el ticket para imprimir.")
            return

        # Buscamos los datos dinámicos en la base de datos
        nombre_local = "M I N I M E R C A D O"
        direccion = ""
        telefono = ""
        instagram = ""
        
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
        except Exception:
            pass # Si hay error, usa los valores por defecto
        finally:
            if 'conexion' in locals(): conexion.close()

        # Armado del encabezado
        ticket = "================================\n"
        
        lineas_nombre = textwrap.wrap(nombre_local, width=32)
        for linea in lineas_nombre:
            ticket += f"{linea.center(32)}\n"
            
        ticket += "================================\n"
        
        if direccion:
            lineas_dir = textwrap.wrap(direccion, width=30)
            for linea in lineas_dir: ticket += f"  {linea}\n"
            
        if telefono:
            lineas_tel = textwrap.wrap(telefono, width=30)
            for linea in lineas_tel: ticket += f"  {linea}\n"
            
        if instagram:
            lineas_ig = textwrap.wrap(instagram, width=30)
            for linea in lineas_ig: ticket += f"  {linea}\n"
            
        ticket += "--------------------------------\n"
        #ticket += "DESCRIPCION               PRECIO\n"
        #ticket += "--------------------------------\n"
        
        for item in items:
            valores = self.tabla_ticket.item(item)['values']
            descripcion = str(valores[1])
            precio = float(valores[2])

            precio_formato = f"${precio:.2f}".rjust(11) 
            lineas_desc = textwrap.wrap(descripcion, width=20)
            if not lineas_desc:
                lineas_desc = [" "]

            for i, linea in enumerate(lineas_desc):
                if i == len(lineas_desc) - 1:
                    ticket += f"{linea.ljust(21)}{precio_formato}\n"
                else:
                    ticket += f"{linea}\n"

        ticket += "--------------------------------\n"
        ticket += f"TOTAL:".ljust(15) + f"${self.total_venta:.2f}".rjust(17) + "\n"
        ticket += "================================\n"
        ticket += "\n    GRACIAS POR SU COMPRA!      \n"
        ticket += "================================\n\n\n"

        try:
            ruta_archivo = os.path.join(tempfile.gettempdir(), "ticket_actual.txt")
            with open(ruta_archivo, "w", encoding="utf-8") as f:
                f.write(ticket)

            os.startfile(ruta_archivo, "print") 
            
        except Exception as e:
            messagebox.showerror("❌ Error de Impresora", f"Fallo al imprimir.\n\nDetalle: {e}")

# ==========================================
if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("100x100") 
    app.withdraw() 
    ventana = VentanaCaja(app) 
    app.mainloop()
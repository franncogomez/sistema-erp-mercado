import customtkinter as ctk
import sqlite3
import os
import tkinter.messagebox as messagebox
from datetime import datetime
from tkinter import ttk

class VentanaCaja(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("🛒 Terminal de Punto de Venta (Caja)")
        self.geometry("900x600")
        self.grab_set() 

        # --- VARIABLES DE MEMORIA ---
        self.carrito = []
        self.total_venta = 0.0
        self.ruta_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sistema_mercado.db")

        # ==========================================
        # 🟢 SECCIÓN SUPERIOR (Buscador / Escáner)
        # ==========================================
        self.frame_top = ctk.CTkFrame(self)
        self.frame_top.pack(pady=15, padx=20, fill="x")

        self.lbl_escaner = ctk.CTkLabel(self.frame_top, text="🔍 Código de Barras:", font=("Roboto", 16, "bold"))
        self.lbl_escaner.pack(side="left", padx=10, pady=15)

        self.entry_codigo = ctk.CTkEntry(self.frame_top, width=300, font=("Roboto", 16), placeholder_text="Pase el producto...")
        self.entry_codigo.pack(side="left", padx=10, pady=15)
        self.entry_codigo.focus() 
        
        self.entry_codigo.bind("<Return>", self.procesar_escaneo)

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
        style.configure("Treeview", 
                        font=("Roboto", 14), 
                        rowheight=35,
                        background="#2D2D2D",      
                        fieldbackground="#2D2D2D", 
                        foreground="white",        
                        borderwidth=0)
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

        self.frame_cobro = ctk.CTkFrame(self.frame_centro, width=300)
        self.frame_cobro.pack(side="right", fill="y")
        self.frame_cobro.pack_propagate(False)

        self.lbl_texto_total = ctk.CTkLabel(self.frame_cobro, text="TOTAL A PAGAR", font=("Roboto", 18, "bold"))
        self.lbl_texto_total.pack(pady=(20, 0))

        self.lbl_monto_total = ctk.CTkLabel(self.frame_cobro, text="$ 0.00", font=("Roboto", 40, "bold"), text_color="#2FA572")
        self.lbl_monto_total.pack(pady=(0, 30))

        self.btn_cobrar = ctk.CTkButton(self.frame_cobro, text="💵 COBRAR (Efectivo)", height=50, font=("Roboto", 14, "bold"), command=lambda: self.ejecutar_cobro("EFECTIVO", False))
        self.btn_cobrar.pack(pady=10, padx=20, fill="x")

        self.btn_mp = ctk.CTkButton(self.frame_cobro, text="📱 COBRAR (Transferencia)", height=50, font=("Roboto", 14, "bold"), fg_color="#009EE3", hover_color="#007EBE", command=lambda: self.ejecutar_cobro("TRANSFERENCIA", False))
        self.btn_mp.pack(pady=10, padx=20, fill="x")

        self.btn_afip = ctk.CTkButton(self.frame_cobro, text="🏛️ TICKET AFIP (Factura B)", height=50, font=("Roboto", 14, "bold"), fg_color="#454545", hover_color="#333333", command=lambda: self.ejecutar_cobro("EFECTIVO", True))
        self.btn_afip.pack(pady=30, padx=20, fill="x")

        self.btn_fiado = ctk.CTkButton(self.frame_cobro, text="📓 Anotar Fiado", fg_color="#1E88E5", hover_color="#1565C0", height=45, font=("Roboto", 16, "bold"), command=self.procesar_fiado)
        self.btn_fiado.pack(pady=10, fill="x", padx=20)

    # ==========================================
    # ⚙️ LÓGICA DE BASE DE DATOS Y ESCANEO
    # ==========================================

    def procesar_escaneo(self, event=None):
        codigo = self.entry_codigo.get().strip().lower()
        self.entry_codigo.delete(0, 'end')

        if not codigo: return

        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            
            cursor.execute("SELECT codigo_barras, nombre, precio FROM productos WHERE LOWER(codigo_barras) = ?", (codigo,))
            producto = cursor.fetchone()

            if producto:
                codigo_db = producto[0]
                nombre_db = producto[1]
                precio_db = float(producto[2])

                if precio_db == 0.0:
                    if len(codigo) < 8:
                        dialogo = ctk.CTkInputDialog(text=f"Ingrese el monto a cobrar para:\n⚖️ {nombre_db}", title="Precio Variable")
                        monto_str = dialogo.get_input()
                        
                        if monto_str:
                            monto_str = monto_str.replace(',', '.') 
                            try:
                                monto = float(monto_str)
                                if monto > 0:
                                    self.agregar_al_carrito(codigo_db, nombre_db, monto)
                                else:
                                    messagebox.showwarning("⚠️ Atención", "El monto debe ser mayor a cero.")
                            except ValueError:
                                messagebox.showerror("❌ Error", "Monto inválido. Use punto para los centavos.")
                        self.entry_codigo.focus()
                    
                    else:
                        dialogo_nuevo = ctk.CTkInputDialog(text=f"⚠️ {nombre_db} no tiene precio.\n\nIngrese el precio de VENTA FINAL ($):", title="Fijar Precio Permanente")
                        nuevo_precio_str = dialogo_nuevo.get_input()
                        
                        if nuevo_precio_str:
                            nuevo_precio_str = nuevo_precio_str.replace(',', '.')
                            try:
                                nuevo_precio = float(nuevo_precio_str)
                                if nuevo_precio > 0:
                                    mensaje = f"¿Guardar de forma permanente este precio?\n\n🛒 {nombre_db}\n💵 Precio: ${nuevo_precio:.2f}"
                                    if messagebox.askyesno("✅ Confirmar Precio Nuevo", mensaje):
                                        cursor.execute("UPDATE productos SET precio = ? WHERE codigo_barras = ?", (nuevo_precio, codigo_db))
                                        conexion.commit()
                                        self.agregar_al_carrito(codigo_db, nombre_db, nuevo_precio)
                                else:
                                    messagebox.showwarning("⚠️ Atención", "El precio debe ser mayor a cero.")
                            except ValueError:
                                messagebox.showerror("❌ Error", "Precio inválido. Use punto para los centavos.")
                        self.entry_codigo.focus()
                else:
                    self.agregar_al_carrito(codigo_db, nombre_db, precio_db)
                    
            else:
                self.alta_rapida(codigo, conexion, cursor)

        except Exception as e:
            messagebox.showerror("❌ Error", f"Error en base de datos: {e}")
        finally:
            if 'conexion' in locals(): 
                conexion.close()

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
        dialogo_nombre = ctk.CTkInputDialog(text=f"Producto no encontrado.\nIngrese el NOMBRE para:\n{codigo}", title="⚡ Alta Rápida")
        nuevo_nombre = dialogo_nombre.get_input()
        
        if not nuevo_nombre: 
            return 

        mensaje_nombre = f"¿Está seguro que el nombre es correcto?\n\n➡️ {nuevo_nombre}"
        confirma_nombre = messagebox.askyesno("⚠️ Confirmar Nombre", mensaje_nombre)
        
        if not confirma_nombre:
            return 

        dialogo_precio = ctk.CTkInputDialog(text=f"Ingrese el PRECIO de venta ($)\npara: {nuevo_nombre}", title="⚡ Alta Rápida")
        precio_str = dialogo_precio.get_input()
        
        if not precio_str: 
            return

        try:
            nuevo_precio = float(precio_str)
            
            mensaje_precio = f"¿Está seguro que el precio es correcto?\n\n➡️ ${nuevo_precio:.2f}"
            confirma_precio = messagebox.askyesno("⚠️ Confirmar Precio", mensaje_precio)
            
            if not confirma_precio:
                return 

            cursor.execute("INSERT INTO productos (codigo_barras, nombre, precio, stock) VALUES (?, ?, ?, 0)", (codigo, nuevo_nombre, nuevo_precio))
            conexion.commit()
            self.agregar_al_carrito(codigo, nuevo_nombre, nuevo_precio)
                
        except ValueError:
            messagebox.showerror("❌ Error", "El precio ingresado no es válido.")

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

        # 🛡️ PARCHE: Reconstruimos el carrito para descontar stock antes de abrir conexión
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

            # 🛡️ PARCHE: Descontamos el stock de los productos fiados
            for codigo in self.carrito:
                cursor.execute("UPDATE productos SET stock = stock - 1 WHERE codigo_barras = ?", (codigo,))

            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO ventas (fecha, total, medio_pago) VALUES (?, ?, 'CUENTA_CORRIENTE')", (fecha_actual, self.total_venta))

            conexion.commit()
            conexion.close()

            messagebox.showinfo("📓 Fiado Registrado", mensaje_exito)
            self.popup_fiado.destroy()
            self.limpiar_carrito() 

        except Exception as e:
            messagebox.showerror("❌ Error Crítico", f"Ocurrió un problema en la base de datos:\n{e}")

    # ==========================================
    # 💰 NUEVA FUNCIÓN: EL COBRO REAL
    # ==========================================
    def ejecutar_cobro(self, medio_pago, con_afip):
        self.carrito = []
        for item in self.tabla_ticket.get_children():
            valores = self.tabla_ticket.item(item)['values']
            self.carrito.append(valores[0]) # Solo necesitamos el código para el stock

        if not self.carrito:
            messagebox.showwarning("⚠️ Carrito Vacío", "No hay productos para cobrar.")
            return

        mensaje_confirmacion = f"¿Confirma la venta por ${self.total_venta:.2f}?\n\nMedio de Pago: {medio_pago}"
        confirmar = messagebox.askyesno("⚠️ Confirmar Venta", mensaje_confirmacion)
        
        if not confirmar:
            return 

        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            
            consulta = "INSERT INTO ventas (total, factura_afip, medio_pago) VALUES (?, ?, ?)"
            cursor.execute(consulta, (self.total_venta, con_afip, medio_pago))
            
            for codigo in self.carrito:
                cursor.execute("UPDATE productos SET stock = stock - 1 WHERE codigo_barras = ?", (codigo,))
                
            conexion.commit()
            
            mensaje = f"Venta exitosa por ${self.total_venta:.2f}\nMedio: {medio_pago}"
            messagebox.showinfo("✅ Venta Registrada", mensaje)
            self.limpiar_carrito() 

        except Exception as e:
            messagebox.showerror("❌ Error", f"Error al procesar la venta:\n{e}")
        finally:
            if 'conexion' in locals():
                conexion.close()

    def limpiar_carrito(self):
        for item in self.tabla_ticket.get_children():
            self.tabla_ticket.delete(item)
        self.total_venta = 0.0
        self.lbl_monto_total.configure(text="$ 0.00")
        self.entry_codigo.focus()

# ==========================================
if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("100x100") 
    app.withdraw() 
    ventana = VentanaCaja(app) 
    app.mainloop()
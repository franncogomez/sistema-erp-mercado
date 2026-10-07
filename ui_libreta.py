import customtkinter as ctk
import tkinter.messagebox as messagebox
from tkinter import ttk
import sqlite3
import os
from datetime import datetime
from rutas import RUTA_DB

class VentanaLibreta(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("📓 Libreta de Fiados (Cuentas Corrientes)")
        self.geometry("900x600") 
        self.grab_set()

        self.ruta_db = RUTA_DB

        # 🛡️ MIGRACIÓN Y CREACIÓN DE TABLA
        self.verificar_tabla_libreta()

        # ==========================================
        # 🟢 ENCABEZADO Y MÉTRICAS
        # ==========================================
        self.lbl_titulo = ctk.CTkLabel(self, text="📓 Gestión de Fiados y Cuentas", font=("Roboto", 24, "bold"))
        self.lbl_titulo.pack(pady=(15, 5))

        self.frame_metricas = ctk.CTkFrame(self, fg_color="#1E293B")
        self.frame_metricas.pack(pady=10, padx=20, fill="x")

        self.lbl_total_clientes = ctk.CTkLabel(self.frame_metricas, text="Clientes Activos: 0", font=("Roboto", 16, "bold"))
        self.lbl_total_clientes.pack(side="left", padx=20, pady=10)

        self.lbl_plata_calle = ctk.CTkLabel(self.frame_metricas, text="Plata en la calle: $ 0.00", font=("Roboto", 16, "bold"), text_color="#2FA572")
        self.lbl_plata_calle.pack(side="right", padx=20, pady=10)

        # ==========================================
        # 🟡 TABLA DE DEUDORES
        # ==========================================
        style = ttk.Style()
        style.theme_use("default") 
        
        style.configure("Treeview.Heading", font=("Roboto", 12, "bold"), background="#1E293B", foreground="white")
        style.configure("Treeview", font=("Roboto", 12), rowheight=30, background="#2D2D2D", fieldbackground="#2D2D2D", foreground="white", borderwidth=0)
        style.map("Treeview", background=[('selected', '#1E88E5')])

        self.frame_tabla = ctk.CTkFrame(self)
        self.frame_tabla.pack(pady=10, padx=20, fill="both", expand=True)

        columnas = ("alias", "telefono", "correo", "deuda")
        self.tabla = ttk.Treeview(self.frame_tabla, columns=columnas, show="headings")
        
        self.tabla.heading("alias", text="👤 Nombre / Alias")
        self.tabla.heading("telefono", text="📱 Teléfono")
        self.tabla.heading("correo", text="✉️ Correo")
        self.tabla.heading("deuda", text="💰 Deuda Pendiente")
        
        self.tabla.column("alias", width=250, anchor="w")
        self.tabla.column("telefono", width=120, anchor="center")
        self.tabla.column("correo", width=200, anchor="w")
        self.tabla.column("deuda", width=150, anchor="e")

        self.tabla.pack(fill="both", expand=True)

        # ==========================================
        # 🛠️ PANEL DE GESTIÓN DE CLIENTES
        # ==========================================
        self.frame_acciones_clientes = ctk.CTkFrame(self, fg_color="transparent") 
        self.frame_acciones_clientes.pack(pady=15)

        self.btn_nuevo_cliente = ctk.CTkButton(self.frame_acciones_clientes, text="➕ Nuevo Cliente", fg_color="#2FA572", hover_color="#238259", height=40, font=("Roboto", 14, "bold"), width=180, command=self.agregar_cliente)
        self.btn_nuevo_cliente.pack(side="left", padx=10)

        self.btn_editar_cliente = ctk.CTkButton(self.frame_acciones_clientes, text="✏️ Editar Cliente", fg_color="#F59E0B", hover_color="#D97706", height=40, font=("Roboto", 14, "bold"), width=180, command=self.editar_cliente)
        self.btn_editar_cliente.pack(side="left", padx=10)

        self.btn_eliminar_cliente = ctk.CTkButton(self.frame_acciones_clientes, text="🗑️ Eliminar", fg_color="#D32F2F", hover_color="#B71C1C", height=40, font=("Roboto", 14, "bold"), width=180, command=self.eliminar_cliente)
        self.btn_eliminar_cliente.pack(side="left", padx=10)

        # ==========================================
        # 🔵 BOTONES (Solo Cobro)
        # ==========================================
        self.frame_acciones = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_acciones.pack(pady=15)

        self.btn_cobrar = ctk.CTkButton(self.frame_acciones, text="💵 Registrar Pago (Saldar Deuda)", fg_color="#D97706", hover_color="#b36205", height=40, font=("Roboto", 14, "bold"), command=self.registrar_pago)
        self.btn_cobrar.pack(side="left", padx=10)

        self.cargar_cuentas()

    # ==========================================
    # ⚙️ LÓGICA DE DATOS
    # ==========================================
    def verificar_tabla_libreta(self):
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cuentas_corrientes (
                    id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
                    alias_cliente TEXT UNIQUE,
                    deuda_total REAL
                )
            """)
            try: cursor.execute("ALTER TABLE cuentas_corrientes ADD COLUMN telefono TEXT")
            except: pass
            try: cursor.execute("ALTER TABLE cuentas_corrientes ADD COLUMN correo TEXT")
            except: pass
            
            conexion.commit()
        except Exception as e:
            print("Aviso interno:", e)
        finally:
            if 'conexion' in locals(): conexion.close()

    def cargar_cuentas(self):
        for item in self.tabla.get_children():
            self.tabla.delete(item)
            
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            
            cursor.execute("SELECT alias_cliente, telefono, correo, deuda_total FROM cuentas_corrientes ORDER BY alias_cliente ASC")
            cuentas = cursor.fetchall()
            
            total_clientes = 0
            plata_calle = 0.0

            for cuenta in cuentas:
                alias = cuenta[0]
                tel = str(cuenta[1]) if cuenta[1] else "-"
                correo = str(cuenta[2]) if cuenta[2] else "-"
                deuda = float(cuenta[3]) if cuenta[3] else 0.0
                
                self.tabla.insert("", "end", values=(alias, tel, correo, f"${deuda:.2f}"))
                total_clientes += 1
                plata_calle += deuda
                
            self.lbl_total_clientes.configure(text=f"Clientes Activos: {total_clientes}")
            self.lbl_plata_calle.configure(text=f"Plata en la calle: $ {plata_calle:.2f}")
                
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error al cargar libretas:\n{e}")
        finally:
            if 'conexion' in locals(): conexion.close()

    def agregar_cliente(self):
        ventana_nuevo = ctk.CTkToplevel(self)
        ventana_nuevo.title("➕ Nuevo Cliente")
        ventana_nuevo.geometry("350x300")
        ventana_nuevo.grab_set()

        ctk.CTkLabel(ventana_nuevo, text="👤 Nombre o Alias:", font=("Roboto", 14, "bold")).pack(pady=(15, 5))
        entry_alias = ctk.CTkEntry(ventana_nuevo, font=("Roboto", 14), width=250)
        entry_alias.pack(pady=5)
        entry_alias.focus()

        ctk.CTkLabel(ventana_nuevo, text="📱 Teléfono (Opcional):", font=("Roboto", 14, "bold")).pack(pady=(15, 5))
        entry_tel = ctk.CTkEntry(ventana_nuevo, font=("Roboto", 14), width=250, placeholder_text="Solo números...")
        entry_tel.pack(pady=5)

        def confirmar_nuevo():
            alias = entry_alias.get().strip().upper()
            tel = entry_tel.get().strip()
            
            if not alias:
                messagebox.showwarning("⚠️ Faltan datos", "El nombre del cliente es obligatorio.")
                return
                
            if tel:
                if not tel.isdigit():
                    messagebox.showerror("❌ Teléfono Inválido", "El teléfono solo puede contener números.\nSin guiones ni espacios.")
                    return
                if len(tel) < 8 or len(tel) > 15:
                    messagebox.showerror("❌ Teléfono Inválido", "El teléfono debe tener entre 8 y 15 números.")
                    return

            try:
                conexion = sqlite3.connect(self.ruta_db)
                cursor = conexion.cursor()
                
                cursor.execute("SELECT id_cliente FROM cuentas_corrientes WHERE alias_cliente = ?", (alias,))
                if cursor.fetchone():
                    messagebox.showwarning("⚠️ Atención", f"El cliente '{alias}' ya existe en la libreta.")
                else:
                    cursor.execute("INSERT INTO cuentas_corrientes (alias_cliente, telefono, correo, deuda_total) VALUES (?, ?, '', 0)", (alias, tel))
                    conexion.commit()
                    messagebox.showinfo("✅ Éxito", f"Cliente '{alias}' agregado correctamente.")
                    self.cargar_cuentas()
                    ventana_nuevo.destroy()
            except Exception as e:
                messagebox.showerror("❌ Error", f"Ocurrió un problema:\n{e}")
            finally:
                if 'conexion' in locals(): conexion.close()

        ctk.CTkButton(ventana_nuevo, text="💾 Guardar", fg_color="#2FA572", hover_color="#238259", height=40, font=("Roboto", 14, "bold"), command=confirmar_nuevo).pack(pady=20)

    def editar_cliente(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showwarning("⚠️ Atención", "Primero seleccione un cliente de la tabla.")
            return

        valores = self.tabla.item(seleccion[0])['values']
        alias_actual = valores[0]
        tel_actual = valores[1] if valores[1] != "-" else ""
        correo_actual = valores[2] if valores[2] != "-" else ""

        ventana_editar = ctk.CTkToplevel(self)
        ventana_editar.title("✏️ Editar Cliente")
        ventana_editar.geometry("400x420") 
        ventana_editar.grab_set()

        ctk.CTkLabel(ventana_editar, text="👤 Nombre o Alias:", font=("Roboto", 14, "bold")).pack(pady=(15, 5))
        entry_alias = ctk.CTkEntry(ventana_editar, font=("Roboto", 14), width=300)
        entry_alias.insert(0, alias_actual)
        entry_alias.pack(pady=5)

        ctk.CTkLabel(ventana_editar, text="📱 Teléfono:", font=("Roboto", 14, "bold")).pack(pady=(15, 5))
        entry_tel = ctk.CTkEntry(ventana_editar, font=("Roboto", 14), width=300)
        entry_tel.insert(0, tel_actual)
        entry_tel.pack(pady=5)

        ctk.CTkLabel(ventana_editar, text="✉️ Correo Electrónico:", font=("Roboto", 14, "bold")).pack(pady=(15, 5))
        entry_correo = ctk.CTkEntry(ventana_editar, font=("Roboto", 14), width=300)
        entry_correo.insert(0, correo_actual)
        entry_correo.pack(pady=5)

        def confirmar_edicion():
            nuevo_alias = entry_alias.get().strip().upper()
            nuevo_tel = entry_tel.get().replace("-", "").replace(" ", "").strip()
            nuevo_correo = entry_correo.get().strip().lower()

            if not nuevo_alias:
                messagebox.showwarning("⚠️ Faltan datos", "El nombre es obligatorio.")
                return

            if nuevo_tel:
                if not nuevo_tel.isdigit():
                    messagebox.showerror("❌ Teléfono Inválido", "El teléfono solo puede contener números.")
                    return
                if len(nuevo_tel) < 8 or len(nuevo_tel) > 15:
                    messagebox.showerror("❌ Teléfono Inválido", "El teléfono debe tener entre 8 y 15 números.")
                    return

            if nuevo_correo:
                if len(nuevo_correo) > 50:
                    messagebox.showerror("❌ Correo Inválido", "El correo es demasiado largo.")
                    return
                if "@" not in nuevo_correo or "." not in nuevo_correo:
                    messagebox.showerror("❌ Correo Inválido", "Por favor, ingrese un formato de correo válido (ej: cliente@gmail.com).")
                    return

            try:
                conexion = sqlite3.connect(self.ruta_db)
                cursor = conexion.cursor()
                cursor.execute("""
                    UPDATE cuentas_corrientes 
                    SET alias_cliente = ?, telefono = ?, correo = ? 
                    WHERE alias_cliente = ?
                """, (nuevo_alias, nuevo_tel, nuevo_correo, alias_actual))
                conexion.commit()
                
                messagebox.showinfo("✅ Éxito", "Datos del cliente actualizados.")
                self.cargar_cuentas()
                ventana_editar.destroy()
                
            except sqlite3.IntegrityError:
                messagebox.showerror("❌ Error", f"Ya existe otro cliente con el nombre '{nuevo_alias}'.")
            except Exception as e:
                messagebox.showerror("❌ Error", f"Ocurrió un problema:\n{e}")
            finally:
                if 'conexion' in locals(): conexion.close()

        ctk.CTkButton(ventana_editar, text="💾 Guardar Cambios", fg_color="#1E88E5", hover_color="#1565C0", height=40, font=("Roboto", 14, "bold"), command=confirmar_edicion).pack(pady=25)

    def eliminar_cliente(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showwarning("⚠️ Atención", "Primero seleccione un cliente para eliminar.")
            return

        valores = self.tabla.item(seleccion[0])['values']
        alias = valores[0]
        deuda_str = str(valores[3]).replace("$", "").replace(",", "")
        deuda = float(deuda_str)

        if deuda > 0:
            advertencia = f"¡CUIDADO! El cliente '{alias}' tiene una deuda de ${deuda:.2f}.\n\n¿Está COMPLETAMENTE SEGURO de querer eliminarlo y perder este registro?"
        else:
            advertencia = f"¿Seguro que desea eliminar a '{alias}' de la libreta?"

        confirmar = messagebox.askyesno("🗑️ Confirmar Eliminación", advertencia)
        if not confirmar: return

        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            cursor.execute("DELETE FROM cuentas_corrientes WHERE alias_cliente = ?", (alias,))
            conexion.commit()
            
            messagebox.showinfo("✅ Éxito", f"Cliente '{alias}' eliminado correctamente.")
            self.cargar_cuentas() 
            
        except Exception as e:
            messagebox.showerror("❌ Error", f"Ocurrió un problema al eliminar:\n{e}")
        finally:
            if 'conexion' in locals(): conexion.close()

    def registrar_pago(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showwarning("⚠️ Atención", "Primero seleccione un cliente de la lista.")
            return
            
        valores = self.tabla.item(seleccion[0])['values']
        alias = valores[0]
        deuda_str = str(valores[3]).replace("$", "").replace(",", "")
        deuda_actual = float(deuda_str)
        
        ventana_pago = ctk.CTkToplevel(self)
        ventana_pago.title("💰 Registrar Pago")
        ventana_pago.geometry("350x380")
        ventana_pago.grab_set() 
        
        lbl_info = ctk.CTkLabel(ventana_pago, text=f"Cliente: {alias}\nDeuda Total: ${deuda_actual:.2f}", font=("Roboto", 16, "bold"))
        lbl_info.pack(pady=15)
        
        lbl_monto = ctk.CTkLabel(ventana_pago, text="Monto a pagar:", font=("Roboto", 14))
        lbl_monto.pack(pady=(10, 0))
        
        entry_monto = ctk.CTkEntry(ventana_pago, font=("Roboto", 16), justify="center", width=150)
        entry_monto.pack(pady=5)
        entry_monto.focus()
        
        lbl_metodo = ctk.CTkLabel(ventana_pago, text="¿Cómo pagó el cliente?:", font=("Roboto", 14))
        lbl_metodo.pack(pady=(15, 0))
        
        combo_metodo = ctk.CTkComboBox(
            ventana_pago, 
            values=["EFECTIVO", "MERCADO PAGO", "TRANSFERENCIA"], 
            font=("Roboto", 14), 
            state="readonly",
            width=200
        )
        combo_metodo.set("EFECTIVO") 
        combo_metodo.pack(pady=5)
        
        def confirmar_pago_deuda():
            monto_str = entry_monto.get().replace(',', '.')
            metodo_elegido = combo_metodo.get()
            
            try:
                monto_pago = float(monto_str)
                if monto_pago <= 0:
                    messagebox.showerror("❌ Error", "El monto debe ser mayor a cero.")
                    return
                if monto_pago > deuda_actual:
                    messagebox.showerror("❌ Error", "El monto ingresado es mayor a la deuda actual.")
                    return
                    
                confirmacion = messagebox.askyesno("⚠️ Confirmar Pago", f"¿Registrar pago de ${monto_pago:.2f}\ncon {metodo_elegido}\npara la cuenta de {alias}?")
                if not confirmacion: return
                
                fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conexion = sqlite3.connect(self.ruta_db)
                cursor = conexion.cursor()
                
                cursor.execute("UPDATE cuentas_corrientes SET deuda_total = ROUND(deuda_total - ?, 2) WHERE alias_cliente = ?", (monto_pago, alias))
                cursor.execute("INSERT INTO ventas (fecha, total, medio_pago) VALUES (?, ?, ?)", (fecha_actual, monto_pago, metodo_elegido))
                
                conexion.commit()
                conexion.close()
                
                messagebox.showinfo("✅ Pago Registrado", f"Se descontaron ${monto_pago:.2f} abonados con {metodo_elegido}.\n\nEse dinero ya impactó en la Caja.")
                self.cargar_cuentas()
                ventana_pago.destroy()
                
            except ValueError: messagebox.showerror("❌ Error", "Ingrese un número válido (ej: 1500 o 1500.50).")
            except Exception as e: messagebox.showerror("❌ Error Crítico", f"Fallo al registrar el pago:\n{e}")

        btn_confirmar = ctk.CTkButton(ventana_pago, text="✅ Confirmar Pago", fg_color="#2FA572", hover_color="#238259", height=40, font=("Roboto", 14, "bold"), command=confirmar_pago_deuda)
        btn_confirmar.pack(pady=25)
        
if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("100x100")
    app.withdraw() 
    v = VentanaLibreta(app)
    app.mainloop()
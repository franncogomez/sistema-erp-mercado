import customtkinter as ctk
import tkinter.messagebox as messagebox
from tkinter import ttk
import sqlite3
import os

class VentanaLibreta(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("📓 Libreta de Fiados (Cuentas Corrientes)")
        self.geometry("700x600")
        self.grab_set()

        self.ruta_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sistema_mercado.db")

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
        style.theme_use("default") # Obliga a Windows a soltar el control del color
        
        # Color del encabezado
        style.configure("Treeview.Heading", font=("Roboto", 12, "bold"), background="#1E293B", foreground="white")
        
        # 🛡️ FONDO GRIS OSCURO PARA CUIDAR LA VISTA
        style.configure("Treeview", 
                        font=("Roboto", 12), 
                        rowheight=30, 
                        background="#2D2D2D",      # Gris oscuro mate
                        fieldbackground="#2D2D2D", # Fondo de las celdas vacías
                        foreground="white",        # Letra blanca
                        borderwidth=0)
        
        # Color azul al hacer clic en un cliente
        style.map("Treeview", background=[('selected', '#1E88E5')])

        self.frame_tabla = ctk.CTkFrame(self)
        self.frame_tabla.pack(pady=10, padx=20, fill="both", expand=True)

        columnas = ("alias", "deuda")
        self.tabla = ttk.Treeview(self.frame_tabla, columns=columnas, show="headings")
        
        self.tabla.heading("alias", text="👤 Nombre / Alias del Cliente")
        self.tabla.heading("deuda", text="💰 Deuda Pendiente ($)")
        
        self.tabla.column("alias", width=400, anchor="w")
        self.tabla.column("deuda", width=200, anchor="e")

        self.tabla.pack(fill="both", expand=True)

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
    def cargar_cuentas(self):
        # Limpiamos la tabla
        for item in self.tabla.get_children():
            self.tabla.delete(item)
            
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            
            cursor.execute("SELECT alias_cliente, deuda_total FROM cuentas_corrientes WHERE deuda_total > 0 ORDER BY alias_cliente ASC")
            cuentas = cursor.fetchall()
            
            total_clientes = 0
            plata_calle = 0.0

            for cuenta in cuentas:
                alias = cuenta[0]
                deuda = float(cuenta[1])
                self.tabla.insert("", "end", values=(alias, f"{deuda:.2f}"))
                total_clientes += 1
                plata_calle += deuda
                
            # Actualizamos los carteles de arriba
            self.lbl_total_clientes.configure(text=f"Clientes Activos: {total_clientes}")
            self.lbl_plata_calle.configure(text=f"Plata en la calle: $ {plata_calle:.2f}")
                
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error al cargar libretas:\n{e}")
        finally:
            if 'conexion' in locals():
                conexion.close()

    def registrar_pago(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showwarning("⚠️ Atención", "Primero seleccione un cliente de la lista.")
            return
            
        valores = self.tabla.item(seleccion[0])['values']
        alias = valores[0]
        deuda_actual = float(valores[1])
        
        dialogo = ctk.CTkInputDialog(text=f"Cliente: {alias}\nDeuda Total: ${deuda_actual:.2f}\n\nIngrese el monto a entregar:", title="💰 Registrar Pago")
        monto_str = dialogo.get_input()
        
        if not monto_str: 
            return

        monto_str = monto_str.replace(',', '.')
        
        try:
            monto_pago = float(monto_str)
            if monto_pago <= 0:
                messagebox.showerror("❌ Error", "El monto debe ser mayor a cero.")
                return
            if monto_pago > deuda_actual:
                messagebox.showerror("❌ Error", "El monto ingresado es mayor a la deuda actual.")
                return
                
            import datetime
            fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            
            # 1. Restamos la plata de la libreta del cliente
            cursor.execute("UPDATE cuentas_corrientes SET deuda_total = deuda_total - ? WHERE alias_cliente = ?", (monto_pago, alias))
            
            # 2. Ingresamos la plata a la caja general del día
            cursor.execute("INSERT INTO ventas (fecha, total, medio_pago) VALUES (?, ?, 'EFECTIVO')", (fecha_actual, monto_pago))
            
            conexion.commit()
            conexion.close()
            
            messagebox.showinfo("✅ Pago Registrado", f"Se descontaron ${monto_pago:.2f} de la cuenta de {alias}.\n\nEse dinero ya impactó en la Caja.")
            
            # Recargamos la tabla visual
            self.cargar_cuentas()
            
        except ValueError:
            messagebox.showerror("❌ Error", "Ingrese un número válido (ej: 1500 o 1500.50).")
        except Exception as e:
            messagebox.showerror("❌ Error Crítico", f"Fallo al registrar el pago:\n{e}")
        
# ==========================================
# CÓDIGO DE PRUEBA INDIVIDUAL
# ==========================================
if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("100x100")
    app.withdraw() # Oculta la ventanita fea de fondo
    v = VentanaLibreta(app)
    app.mainloop()
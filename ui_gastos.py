import customtkinter as ctk
from tkinter import messagebox
import sqlite3
import os
from datetime import datetime
from rutas import RUTA_DB

class VentanaGastos(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("💸 Pagos a Proveedores y Gastos")
        self.geometry("450x620") # 🛠️ Un poco más alta para que entren los 3 cuadros del mixto
        self.grab_set()

        self.ruta_db = RUTA_DB
        self.crear_tabla_gastos()

        # ==========================================
        # 🎨 DISEÑO DE LA VENTANA
        # ==========================================
        lbl_titulo = ctk.CTkLabel(self, text="Registro de Salida de Dinero", font=("Roboto", 20, "bold"))
        lbl_titulo.pack(pady=(25, 10))

        # 1. Motivo
        lbl_motivo = ctk.CTkLabel(self, text="Motivo del pago (Ej: Proveedor, Luz, etc.):", font=("Roboto", 14))
        lbl_motivo.pack(pady=(10, 0))
        
        self.entry_motivo = ctk.CTkEntry(self, width=320, font=("Roboto", 14))
        self.entry_motivo.pack(pady=5)
        self.entry_motivo.focus()

        # 2. Selector de Método
        lbl_metodo = ctk.CTkLabel(self, text="¿Cómo se pagó este gasto?:", font=("Roboto", 14, "bold"))
        lbl_metodo.pack(pady=(20, 5))

        self.combo_metodo = ctk.CTkComboBox(
            self, 
            values=["Efectivo", "Mercado Pago", "Transferencia", "Mixto (Dividir Pago)"],
            width=250,
            font=("Roboto", 14),
            state="readonly",
            command=self.actualizar_campos_monto
        )
        self.combo_metodo.set("Efectivo")
        self.combo_metodo.pack(pady=5)

        # 3. Contenedor Dinámico para los Montos
        self.frame_montos = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_montos.pack(pady=20, fill="x")

        self.entry_unico = None
        self.entry_mix_efec = None
        self.entry_mix_mp = None
        self.entry_mix_transf = None

        self.actualizar_campos_monto("Efectivo")

        # 4. Botón Guardar
        btn_guardar = ctk.CTkButton(self, text="💾 Registrar Salida", font=("Roboto", 15, "bold"), fg_color="#D32F2F", hover_color="#B71C1C", height=45, command=self.guardar_gasto)
        btn_guardar.pack(side="bottom", pady=30)

    # ==========================================
    # ⚙️ LÓGICA DE INTERFAZ Y BASE DE DATOS
    # ==========================================
    def actualizar_campos_monto(self, eleccion):
        for widget in self.frame_montos.winfo_children():
            widget.destroy()

        if eleccion == "Mixto (Dividir Pago)":
            lbl_mix_efec = ctk.CTkLabel(self.frame_montos, text="Monto pagado en EFECTIVO ($):", font=("Roboto", 13, "bold"), text_color="#2FA572")
            lbl_mix_efec.pack(pady=(0, 2))
            self.entry_mix_efec = ctk.CTkEntry(self.frame_montos, width=180, font=("Roboto", 16), justify="center")
            self.entry_mix_efec.pack(pady=(0, 10))

            lbl_mix_mp = ctk.CTkLabel(self.frame_montos, text="Monto pagado en MERCADO PAGO ($):", font=("Roboto", 13, "bold"), text_color="#00A650")
            lbl_mix_mp.pack(pady=(0, 2))
            self.entry_mix_mp = ctk.CTkEntry(self.frame_montos, width=180, font=("Roboto", 16), justify="center")
            self.entry_mix_mp.pack(pady=(0, 10))

            lbl_mix_transf = ctk.CTkLabel(self.frame_montos, text="Monto pagado por TRANSFERENCIA ($):", font=("Roboto", 13, "bold"), text_color="#009EE3")
            lbl_mix_transf.pack(pady=(0, 2))
            self.entry_mix_transf = ctk.CTkEntry(self.frame_montos, width=180, font=("Roboto", 16), justify="center")
            self.entry_mix_transf.pack(pady=(0, 5))
            
            self.entry_unico = None 
            
        else:
            if eleccion == "Efectivo": color_lbl = "#2FA572"
            elif eleccion == "Mercado Pago": color_lbl = "#00A650"
            else: color_lbl = "#009EE3"
            
            lbl_unico = ctk.CTkLabel(self.frame_montos, text=f"Monto total en {eleccion.upper()} ($):", font=("Roboto", 14, "bold"), text_color=color_lbl)
            lbl_unico.pack(pady=(10, 5))
            
            self.entry_unico = ctk.CTkEntry(self.frame_montos, width=200, font=("Roboto", 18), justify="center")
            self.entry_unico.pack(pady=5)
            
            self.entry_mix_efec = None
            self.entry_mix_mp = None
            self.entry_mix_transf = None

    def crear_tabla_gastos(self):
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            # Creamos la tabla con la nueva columna monto_mp por si el sistema es nuevo
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gastos (
                    id_gasto INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha DATETIME,
                    motivo TEXT,
                    monto_efectivo REAL,
                    monto_mp REAL,
                    monto_transf REAL
                )
            """)
            # 🛠️ Parche silencioso: Le inyectamos la columna a bases de datos que ya existan
            try:
                cursor.execute("ALTER TABLE gastos ADD COLUMN monto_mp REAL")
            except sqlite3.OperationalError:
                pass # Si da error es porque ya existe, no hacemos nada
                
            conexion.commit()
        except Exception as e:
            messagebox.showerror("Error", f"Error al inicializar la base de datos de gastos:\n{e}")
        finally:
            if 'conexion' in locals(): conexion.close()

    def guardar_gasto(self):
        motivo = self.entry_motivo.get().strip()
        metodo = self.combo_metodo.get()
        
        if not motivo:
            messagebox.showwarning("⚠️ Faltan datos", "Por favor, ingrese a quién se le pagó o el motivo del gasto.")
            return

        efectivo = 0.0
        mp = 0.0
        transf = 0.0

        try:
            if metodo == "Mixto (Dividir Pago)":
                str_efec = self.entry_mix_efec.get().replace(',', '.')
                str_mp = self.entry_mix_mp.get().replace(',', '.')
                str_transf = self.entry_mix_transf.get().replace(',', '.')
                
                if str_efec: efectivo = float(str_efec)
                if str_mp: mp = float(str_mp)
                if str_transf: transf = float(str_transf)
            else:
                str_unico = self.entry_unico.get().replace(',', '.')
                if not str_unico: raise ValueError
                
                if metodo == "Efectivo": efectivo = float(str_unico)
                elif metodo == "Mercado Pago": mp = float(str_unico)
                else: transf = float(str_unico)

            total = efectivo + mp + transf
            if total <= 0:
                messagebox.showwarning("⚠️ Monto inválido", "El total del pago debe ser mayor a cero.")
                return

            mensaje = f"¿Confirmar salida de dinero por:\n'{motivo}'?\n\n"
            if efectivo > 0: mensaje += f"💵 Efectivo: ${efectivo:.2f}\n"
            if mp > 0: mensaje += f"💳 Mercado Pago: ${mp:.2f}\n"
            if transf > 0: mensaje += f"📱 Transferencia: ${transf:.2f}\n"
            mensaje += f"\nTOTAL PAGADO: ${total:.2f}"

            if not messagebox.askyesno("⚠️ Confirmar Gasto", mensaje):
                return

            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            
            # Guardamos los 3 montos en la base de datos
            cursor.execute("INSERT INTO gastos (fecha, motivo, monto_efectivo, monto_mp, monto_transf) VALUES (?, ?, ?, ?, ?)", (fecha_actual, motivo, efectivo, mp, transf))
            conexion.commit()
            conexion.close()

            messagebox.showinfo("✅ Éxito", "Gasto registrado.\n\nEl sistema ya lo descontó automáticamente del Arqueo de Caja correspondiente.")
            self.destroy()

        except ValueError:
            messagebox.showerror("❌ Error", "Por favor, ingrese montos numéricos válidos (Ej: 1500.50). No deje los campos vacíos si eligió método Mixto.")
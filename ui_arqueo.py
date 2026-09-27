import customtkinter as ctk
import tkinter.messagebox as messagebox
import sqlite3
import os
from datetime import datetime

class VentanaArqueo(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("🏦 Módulo Financiero - Arqueo de Caja")
        self.geometry("600x600")
        self.grab_set()

        self.ruta_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sistema_mercado.db")
        
        # 🛡️ PARCHE 1: Prevenir crasheos en instalaciones nuevas
        self.verificar_tabla_arqueo()

        # ==========================================
        # 🟢 ENCABEZADO Y ESTADO
        # ==========================================
        self.lbl_titulo = ctk.CTkLabel(self, text="📊 Control de Caja y Arqueos", font=("Roboto", 24, "bold"))
        self.lbl_titulo.pack(pady=(20, 5))

        self.lbl_estado = ctk.CTkLabel(self, text="ESTADO: DESCONOCIDO", font=("Roboto", 16, "bold"))
        self.lbl_estado.pack(pady=(0, 20))

        # ==========================================
        # 🟡 PANEL DE RESUMEN DEL TURNO
        # ==========================================
        self.frame_resumen = ctk.CTkFrame(self)
        self.frame_resumen.pack(padx=30, fill="both", expand=True)

        self.lbl_subtitulo = ctk.CTkLabel(self.frame_resumen, text="Resumen del Turno Actual", font=("Roboto", 18, "bold"))
        self.lbl_subtitulo.pack(pady=15)

        fuente_datos = ("Roboto", 14)
        self.lbl_fondo_fijo = ctk.CTkLabel(self.frame_resumen, text="Fondo Fijo Inicial: $ 0.00", font=fuente_datos)
        self.lbl_fondo_fijo.pack(pady=5, anchor="w", padx=40)

        self.lbl_efectivo = ctk.CTkLabel(self.frame_resumen, text="Ventas en Efectivo: $ 0.00", font=fuente_datos)
        self.lbl_efectivo.pack(pady=5, anchor="w", padx=40)

        self.lbl_transf = ctk.CTkLabel(self.frame_resumen, text="Ventas por Transferencia: $ 0.00", font=fuente_datos)
        self.lbl_transf.pack(pady=5, anchor="w", padx=40)

        self.lbl_cta_cte = ctk.CTkLabel(self.frame_resumen, text="Ventas en Cta. Corriente: $ 0.00", font=fuente_datos)
        self.lbl_cta_cte.pack(pady=5, anchor="w", padx=40)

        self.lbl_total_esperado = ctk.CTkLabel(self.frame_resumen, text="EFECTIVO ESPERADO EN CAJA: $ 0.00", font=("Roboto", 16, "bold"), text_color="#D97706")
        self.lbl_total_esperado.pack(pady=(20, 15))

        # ==========================================
        # 🔵 BOTONES DE ACCIÓN
        # ==========================================
        self.frame_botones = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_botones.pack(pady=20)

        self.btn_abrir = ctk.CTkButton(self.frame_botones, text="🔓 ABRIR CAJA", fg_color="#2FA572", hover_color="#237a54", height=45, font=("Roboto", 14, "bold"), command=self.abrir_caja)
        self.btn_abrir.pack(side="left", padx=10)

        self.btn_cerrar = ctk.CTkButton(self.frame_botones, text="🔒 CERRAR TURNO (Arqueo Z)", fg_color="#C62828", hover_color="#8e1d1d", height=45, font=("Roboto", 14, "bold"), command=self.cerrar_caja)
        self.btn_cerrar.pack(side="left", padx=10)

        self.id_apertura_actual = None
        self.fecha_apertura = None
        self.fondo_fijo = 0.0
        self.efectivo_esperado = 0.0

        self.actualizar_estado()

    # ==========================================
    # ⚙️ LÓGICA DEL MÓDULO FINANCIERO
    # ==========================================
    def verificar_tabla_arqueo(self):
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS arqueo_caja (
                    id_arqueo INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha_operacion DATETIME,
                    tipo_operacion TEXT,
                    monto_declarado REAL,
                    observaciones TEXT
                )
            """)
            conexion.commit()
        except Exception as e:
            print("Aviso interno:", e)
        finally:
            if 'conexion' in locals():
                conexion.close()

    def actualizar_estado(self):
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            
            cursor.execute("SELECT id_arqueo, tipo_operacion, monto_declarado, fecha_operacion FROM arqueo_caja ORDER BY id_arqueo DESC LIMIT 1")
            ultima_op = cursor.fetchone()

            if not ultima_op or ultima_op[1] == 'CIERRE':
                self.lbl_estado.configure(text="ESTADO: 🔴 CAJA CERRADA", text_color="#C62828")
                self.btn_abrir.configure(state="normal")
                self.btn_cerrar.configure(state="disabled")
                self.limpiar_resumen()
            else:
                self.id_apertura_actual, tipo, self.fondo_fijo, self.fecha_apertura = ultima_op
                self.lbl_estado.configure(text=f"ESTADO: 🟢 CAJA ABIERTA (Desde: {self.fecha_apertura})", text_color="#2FA572")
                self.btn_abrir.configure(state="disabled")
                self.btn_cerrar.configure(state="normal")
                self.calcular_resumen(cursor)

        except Exception as e:
            messagebox.showerror("❌ Error", f"Error de base de datos:\n{e}")
        finally:
            if 'conexion' in locals():
                conexion.close()

    def limpiar_resumen(self):
        self.lbl_fondo_fijo.configure(text="Fondo Fijo Inicial: $ 0.00")
        self.lbl_efectivo.configure(text="Ventas en Efectivo: $ 0.00")
        self.lbl_transf.configure(text="Ventas por Transferencia: $ 0.00")
        self.lbl_cta_cte.configure(text="Ventas en Cta. Corriente: $ 0.00")
        self.lbl_total_esperado.configure(text="EFECTIVO ESPERADO EN CAJA: $ 0.00")

    def calcular_resumen(self, cursor):
        cursor.execute("SELECT medio_pago, SUM(total) FROM ventas WHERE fecha >= ? GROUP BY medio_pago", (self.fecha_apertura,))
        ventas = cursor.fetchall()

        t_efectivo = 0.0
        t_transf = 0.0
        t_cta_cte = 0.0

        for medio, total in ventas:
            if medio == 'EFECTIVO': t_efectivo = total
            elif medio == 'TRANSFERENCIA': t_transf = total
            elif medio == 'CUENTA_CORRIENTE': t_cta_cte = total

        self.efectivo_esperado = self.fondo_fijo + t_efectivo

        self.lbl_fondo_fijo.configure(text=f"Fondo Fijo Inicial: $ {self.fondo_fijo:.2f}")
        self.lbl_efectivo.configure(text=f"Ventas en Efectivo: $ {t_efectivo:.2f}")
        self.lbl_transf.configure(text=f"Ventas por Transferencia: $ {t_transf:.2f}")
        self.lbl_cta_cte.configure(text=f"Ventas en Cta. Corriente: $ {t_cta_cte:.2f}")
        self.lbl_total_esperado.configure(text=f"EFECTIVO ESPERADO EN CAJA: $ {self.efectivo_esperado:.2f}")

    def abrir_caja(self):
        dialogo = ctk.CTkInputDialog(text="Ingrese el Fondo Fijo Inicial (Cambio en caja):", title="🔓 Apertura de Caja")
        monto_str = dialogo.get_input()
        
        if not monto_str: return

        try:
            monto_str = monto_str.replace(',', '.')
            monto = float(monto_str)
            if monto < 0: raise ValueError
            
            confirmacion = messagebox.askyesno("⚠️ Confirmar Apertura", f"¿Está seguro de abrir la caja con un fondo fijo de:\n\n💰 ${monto:.2f}?")
            if not confirmacion:
                return
            
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute("INSERT INTO arqueo_caja (fecha_operacion, tipo_operacion, monto_declarado) VALUES (?, 'APERTURA', ?)", (fecha_actual, monto))
            conexion.commit()
            conexion.close()
            
            messagebox.showinfo("✅ Apertura Exitosa", f"Turno abierto correctamente con ${monto:.2f}.")
            self.actualizar_estado()
            
        except ValueError:
            messagebox.showerror("❌ Error", "El monto ingresado no es válido. Debe ser un número.")

    def cerrar_caja(self):
        mensaje_rapido = f"Efectivo esperado en caja: 💰 ${self.efectivo_esperado:.2f}\n\n¿El dinero físico coincide EXACTAMENTE con este monto?"
        es_perfecto = messagebox.askyesno("🔒 Cierre Rápido", mensaje_rapido)
        
        if es_perfecto:
            monto_real = self.efectivo_esperado
        else:
            dialogo = ctk.CTkInputDialog(text="Cuente los billetes reales e ingrese el total físico:", title="🔒 Declaración Manual")
            monto_str = dialogo.get_input()
            
            if not monto_str: return 
            
            try:
                monto_str = monto_str.replace(',', '.')
                monto_real = float(monto_str)
            except ValueError:
                messagebox.showerror("❌ Error", "El monto ingresado no es válido.")
                return

        # 🛡️ PARCHE 2: Redondeo matemático estricto para evitar bugs de flotantes
        diferencia = round(monto_real - self.efectivo_esperado, 2)
        
        resumen = f"Declarado: ${monto_real:.2f}\nEsperado: ${self.efectivo_esperado:.2f}\n"
        if diferencia == 0:
            resumen += "\n✅ Arqueo Perfecto (Sin diferencias)."
        else:
            resumen += f"\n⚠️ Diferencia de: ${diferencia:.2f} (Faltante/Sobrante)"
            
        if messagebox.askyesno("⚠️ Confirmar Cierre", f"¿Está seguro de cerrar el turno con los siguientes datos?\n\n{resumen}"):
            
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            obs = f"Diferencia: {diferencia:.2f}"
            cursor.execute("INSERT INTO arqueo_caja (fecha_operacion, tipo_operacion, monto_declarado, observaciones) VALUES (?, 'CIERRE', ?, ?)", (fecha_actual, monto_real, obs))
            conexion.commit()
            conexion.close()
            
            messagebox.showinfo("✅ Turno Cerrado", "El cierre de caja se procesó exitosamente.")
            self.actualizar_estado()

if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("100x100")
    app.withdraw()
    v = VentanaArqueo(app)
    app.mainloop()
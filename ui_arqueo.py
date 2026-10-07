import customtkinter as ctk
import tkinter.messagebox as messagebox
import sqlite3
import os
import shutil
from datetime import datetime
from rutas import RUTA_DB

class VentanaArqueo(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("🏦 Módulo Financiero - Arqueo de Caja")
        self.geometry("650x740") # Ventana más amplia para acomodar fuentes más grandes
        self.grab_set()

        self.ruta_db = RUTA_DB
        self.verificar_tabla_arqueo()

        # ==========================================
        # 🟢 ENCABEZADO Y ESTADO
        # ==========================================
        self.lbl_titulo = ctk.CTkLabel(self, text="📊 Control de Caja y Arqueos", font=("Roboto", 26, "bold"))
        self.lbl_titulo.pack(pady=(20, 5))

        self.frame_estado = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_estado.pack(pady=(0, 15))

        self.lbl_estado = ctk.CTkLabel(self.frame_estado, text="ESTADO: DESCONOCIDO", font=("Roboto", 18, "bold"))
        self.lbl_estado.pack()

        # ==========================================
        # 🟡 PANEL DE RESUMEN (Estilo Contable con Grid)
        # ==========================================
        self.frame_resumen = ctk.CTkFrame(self, corner_radius=15)
        self.frame_resumen.pack(padx=30, fill="both", expand=True)

        # Configuramos 2 columnas: 0 para textos (izquierda) y 1 para montos (derecha)
        self.frame_resumen.columnconfigure(0, weight=1)
        self.frame_resumen.columnconfigure(1, weight=1)

        self.lbl_subtitulo = ctk.CTkLabel(self.frame_resumen, text="Resumen del Turno Actual", font=("Roboto", 18, "bold"), text_color="gray")
        self.lbl_subtitulo.grid(row=0, column=0, columnspan=2, pady=(15, 10))

        # 🛠️ Función auxiliar para crear renglones alineados
        def crear_renglon(fila, texto, color_txt="white", color_val="white", negrita=False, tamaño=16):
            fuente_lbl = ("Roboto", tamaño)
            fuente_val = ("Roboto", tamaño, "bold") if negrita else ("Roboto", tamaño)
            
            lbl = ctk.CTkLabel(self.frame_resumen, text=texto, font=fuente_lbl, text_color=color_txt)
            lbl.grid(row=fila, column=0, sticky="w", padx=30, pady=6)
            
            val = ctk.CTkLabel(self.frame_resumen, text="$ 0.00", font=fuente_val, text_color=color_val)
            val.grid(row=fila, column=1, sticky="e", padx=30, pady=6)
            return val

        # --- INGRESOS ---
        self.val_fondo_fijo = crear_renglon(1, "💵 Fondo Fijo Inicial:")
        self.val_efectivo = crear_renglon(2, "🟩 Ventas en Efectivo:")
        self.val_mp = crear_renglon(3, "🟦 Ventas Mercado Pago:")
        self.val_transf = crear_renglon(4, "🏦 Ventas Transferencia:")
        self.val_cta_cte = crear_renglon(5, "📓 Ventas Fiadas (Cta. Cte.):")

        # --- EGRESOS ---
        self.val_gastos_efec = crear_renglon(6, "🔻 Salidas por Pagos (Efectivo):", color_txt="#EF4444", color_val="#EF4444")
        self.val_gastos_transf = crear_renglon(7, "🔻 Salidas por Pagos (Virtual):", color_txt="#EF4444", color_val="#EF4444")

        # --- LÍNEA DIVISORIA VISUAL ---
        separador = ctk.CTkFrame(self.frame_resumen, height=2, fg_color="#475569")
        separador.grid(row=8, column=0, columnspan=2, sticky="ew", padx=20, pady=10)

        # --- TOTALES FINALES ---
        self.val_ingreso_total = crear_renglon(9, "📈 INGRESO NETO DEL TURNO:", color_val="#3B82F6", negrita=True, tamaño=18)
        
        # Este es el número más importante para el cajero
        self.val_efectivo_caja = crear_renglon(10, "💰 EFECTIVO FÍSICO A RENDIR:", color_val="#10B981", color_txt="#10B981", negrita=True, tamaño=20)

        # ==========================================
        # 🔵 BOTONES DE ACCIÓN
        # ==========================================
        self.frame_botones = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_botones.pack(pady=20)

        self.btn_abrir = ctk.CTkButton(self.frame_botones, text="🔓 ABRIR CAJA", fg_color="#2FA572", hover_color="#237a54", height=50, width=180, font=("Roboto", 15, "bold"), command=self.abrir_caja)
        self.btn_abrir.pack(side="left", padx=10)

        self.btn_cerrar = ctk.CTkButton(self.frame_botones, text="🔒 CERRAR TURNO", fg_color="#C62828", hover_color="#8e1d1d", height=50, width=180, font=("Roboto", 15, "bold"), command=self.cerrar_caja)
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gastos (
                    id_gasto INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha DATETIME,
                    motivo TEXT,
                    monto_efectivo REAL,
                    monto_transf REAL
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
                self.lbl_estado.configure(text="🔴 CAJA CERRADA", text_color="#EF4444")
                self.btn_abrir.configure(state="normal")
                self.btn_cerrar.configure(state="disabled")
                self.limpiar_resumen()
            else:
                self.id_apertura_actual, tipo, self.fondo_fijo, self.fecha_apertura = ultima_op
                self.lbl_estado.configure(text=f"🟢 CAJA ABIERTA (Desde: {self.fecha_apertura})", text_color="#10B981")
                self.btn_abrir.configure(state="disabled")
                self.btn_cerrar.configure(state="normal")
                self.calcular_resumen(cursor)

        except Exception as e:
            messagebox.showerror("❌ Error", f"Error de base de datos:\n{e}")
        finally:
            if 'conexion' in locals():
                conexion.close()

    def limpiar_resumen(self):
        self.val_fondo_fijo.configure(text="$ 0.00")
        self.val_efectivo.configure(text="$ 0.00")
        self.val_mp.configure(text="$ 0.00")
        self.val_transf.configure(text="$ 0.00")
        self.val_cta_cte.configure(text="$ 0.00")
        self.val_gastos_efec.configure(text="-$ 0.00")
        self.val_gastos_transf.configure(text="-$ 0.00")
        self.val_ingreso_total.configure(text="$ 0.00")
        self.val_efectivo_caja.configure(text="$ 0.00")

    def calcular_resumen(self, cursor):
        cursor.execute("SELECT medio_pago, SUM(total) FROM ventas WHERE fecha >= ? GROUP BY medio_pago", (self.fecha_apertura,))
        ventas = cursor.fetchall()

        t_efectivo = 0.0
        t_mp = 0.0
        t_transf = 0.0
        t_cta_cte = 0.0

        for medio, total in ventas:
            if medio == 'EFECTIVO': t_efectivo = total
            elif medio == 'MERCADO PAGO': t_mp = total
            elif medio == 'TRANSFERENCIA': t_transf = total
            elif medio == 'CUENTA_CORRIENTE': t_cta_cte = total

        cursor.execute("SELECT SUM(monto_efectivo), SUM(monto_transf) FROM gastos WHERE fecha >= ?", (self.fecha_apertura,))
        resultado_gastos = cursor.fetchone()
        
        salidas_efectivo = resultado_gastos[0] if resultado_gastos[0] else 0.0
        salidas_transf = resultado_gastos[1] if resultado_gastos[1] else 0.0

        self.efectivo_esperado = (self.fondo_fijo + t_efectivo) - salidas_efectivo
        
        ingreso_bruto = t_efectivo + t_mp + t_transf
        ingreso_neto = ingreso_bruto - (salidas_efectivo + salidas_transf)

        # Actualización visual de etiquetas
        self.val_fondo_fijo.configure(text=f"$ {self.fondo_fijo:,.2f}")
        self.val_efectivo.configure(text=f"$ {t_efectivo:,.2f}")
        self.val_mp.configure(text=f"$ {t_mp:,.2f}")
        self.val_transf.configure(text=f"$ {t_transf:,.2f}")
        self.val_cta_cte.configure(text=f"$ {t_cta_cte:,.2f}")
        
        self.val_gastos_efec.configure(text=f"-$ {salidas_efectivo:,.2f}")
        self.val_gastos_transf.configure(text=f"-$ {salidas_transf:,.2f}")
        
        self.val_ingreso_total.configure(text=f"$ {ingreso_neto:,.2f}")
        self.val_efectivo_caja.configure(text=f"$ {self.efectivo_esperado:,.2f}")

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
        mensaje_rapido = f"Efectivo esperado en caja (Billetes físicos): 💰 ${self.efectivo_esperado:.2f}\n\n¿El dinero contado coincide EXACTAMENTE con este monto?"
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
            self.generar_backup_automatico()
            conexion.close()
            
            messagebox.showinfo("✅ Turno Cerrado", "El cierre de caja se procesó exitosamente.")
            self.actualizar_estado()

    def generar_backup_automatico(self):
        """Genera una copia de seguridad silenciosa al cerrar la caja."""
        directorio_base = os.path.dirname(self.ruta_db)
        carpeta_backups = os.path.join(directorio_base, "backups_cierres")
        
        # Creamos la carpeta si no existe
        os.makedirs(carpeta_backups, exist_ok=True)
        
        fecha_hora = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_copia = f"backup_cierre_{fecha_hora}.db"
        ruta_copia = os.path.join(carpeta_backups, nombre_copia)
        
        try:
            shutil.copy2(self.ruta_db, ruta_copia)
            print(f"✅ Backup automático creado: {nombre_copia}")
        except Exception as e:
            print(f"⚠️ Aviso: Fallo el backup automático: {e}")

if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("100x100")
    app.withdraw()
    v = VentanaArqueo(app)
    app.mainloop()
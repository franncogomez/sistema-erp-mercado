import customtkinter as ctk
from tkinter import ttk, messagebox
import sqlite3
import os
from datetime import datetime, timedelta
from rutas import RUTA_DB

class VentanaEstadisticas(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("📊 Flujo de Caja y Estadísticas (ERP)")
        self.geometry("850x600") 
        self.grab_set()

        self.ruta_db = RUTA_DB
        self.mapa_filas = {} 

        # ==========================================
        # 🎨 ENCABEZADO
        # ==========================================
        self.lbl_titulo = ctk.CTkLabel(self, text="Flujo de Caja (Ingresos vs Egresos)", font=("Roboto", 22, "bold"))
        self.lbl_titulo.pack(pady=(15, 5))
        
        self.lbl_sub = ctk.CTkLabel(self, text="Balance general del negocio agrupado por semanas", font=("Roboto", 13), text_color="gray")
        self.lbl_sub.pack(pady=(0, 10))

        self.aplicar_estilo_tabla()

        # ==========================================
        # 🛠️ PANEL DE ACCIONES (Fijo en la base)
        # ==========================================
        frame_acciones = ctk.CTkFrame(self, fg_color="transparent")
        frame_acciones.pack(side="bottom", pady=(5, 20), padx=20, fill="x")

        self.btn_detalle = ctk.CTkButton(frame_acciones, text="🔍 Ver Detalle de la Semana", fg_color="#1E88E5", hover_color="#1565C0", height=45, font=("Roboto", 14, "bold"), command=self.ver_detalle_semana)
        self.btn_detalle.pack(side="left", padx=10, expand=True, fill="x")

        self.btn_grafico = ctk.CTkButton(frame_acciones, text="📊 Generar Gráfico de Gastos", fg_color="#8E24AA", hover_color="#6A1B9A", height=45, font=("Roboto", 14, "bold"), command=self.abrir_menu_graficos)
        self.btn_grafico.pack(side="right", padx=10, expand=True, fill="x")

        # ==========================================
        # 📊 TABLA MAESTRA DE CASH FLOW
        # ==========================================
        frame_tabla = ctk.CTkFrame(self)
        frame_tabla.pack(side="top", pady=10, padx=20, fill="both", expand=True)

        columnas = ("mes", "semana", "ingresos", "gastos", "neta")
        self.tabla = ttk.Treeview(frame_tabla, columns=columnas, show="headings", height=12)
        
        self.tabla.heading("mes", text="📅 Mes")
        self.tabla.heading("semana", text="📆 Semana")
        self.tabla.heading("ingresos", text="📈 Ingresos Totales")
        self.tabla.heading("gastos", text="📉 Gastos Totales")
        self.tabla.heading("neta", text="💰 Ganancia Neta")

        self.tabla.column("mes", width=140, anchor="center")
        self.tabla.column("semana", width=100, anchor="center")
        self.tabla.column("ingresos", width=140, anchor="e")
        self.tabla.column("gastos", width=140, anchor="e")
        self.tabla.column("neta", width=140, anchor="e")

        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=scrollbar.set)
        
        self.tabla.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.cargar_datos()

    def aplicar_estilo_tabla(self):
        style = ttk.Style(self)
        style.theme_use("default")
        
        modo = ctk.get_appearance_mode()
        if modo == "Dark":
            bg_color, fg_color, field_bg, head_bg, seleccion = "#2b2b2b", "white", "#2b2b2b", "#1f538d", "#14375e"
        else:
            bg_color, fg_color, field_bg, head_bg, seleccion = "#f2f2f2", "black", "#f2f2f2", "#3a7ebf", "#9ec5eb"

        style.configure("Treeview", background=bg_color, foreground=fg_color, rowheight=35, fieldbackground=field_bg, font=("Roboto", 12))
        style.configure("Treeview.Heading", background=head_bg, foreground="white", font=("Roboto", 13, "bold"), padding=5)
        style.map('Treeview', background=[('selected', seleccion)])

    # ==========================================
    # ⚙️ MOTOR DE AGRUPACIÓN DE DATOS
    # ==========================================
    def cargar_datos(self):
        for item in self.tabla.get_children(): self.tabla.delete(item)
        self.mapa_filas.clear()

        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()

            cursor.execute("""
                SELECT strftime('%Y', fecha), strftime('%m', fecha), strftime('%W', fecha), total 
                FROM ventas
            """)
            ventas = cursor.fetchall()

            gastos = []
            try:
                cursor.execute("""
                    SELECT strftime('%Y', fecha), strftime('%m', fecha), strftime('%W', fecha), (monto_efectivo + monto_transf) 
                    FROM gastos
                """)
                gastos = cursor.fetchall()
            except sqlite3.OperationalError:
                pass 

            historial = {} 

            for anio, mes, sem, total in ventas:
                if not anio or not mes or not sem: continue
                clave = (anio, mes, sem)
                if clave not in historial: historial[clave] = {'ingresos': 0.0, 'gastos': 0.0}
                historial[clave]['ingresos'] += float(total)

            for anio, mes, sem, total_gasto in gastos:
                if not anio or not mes or not sem: continue
                clave = (anio, mes, sem)
                if clave not in historial: historial[clave] = {'ingresos': 0.0, 'gastos': 0.0}
                historial[clave]['gastos'] += float(total_gasto)

            meses_nombres = {
                "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril", 
                "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto", 
                "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"
            }

            claves_ordenadas = sorted(historial.keys(), key=lambda x: (x[0], x[1], x[2]), reverse=True)

            for anio, mes, sem in claves_ordenadas:
                data = historial[(anio, mes, sem)]
                ingresos = data['ingresos']
                gastos = data['gastos']
                neta = ingresos - gastos

                nombre_mes = f"{meses_nombres.get(mes, mes)} {anio}"
                semana_del_mes = (int(sem) % 4) + 1 
                texto_semana = f"Semana {semana_del_mes}"

                item_id = self.tabla.insert("", "end", values=(
                    nombre_mes, 
                    texto_semana, 
                    f"$ {ingresos:.2f}", 
                    f"$ {gastos:.2f}", 
                    f"$ {neta:.2f}"
                ))
                
                self.mapa_filas[item_id] = (anio, mes, sem)

        except Exception as e:
            messagebox.showerror("Error", f"Fallo al cargar estadísticas:\n{e}")
        finally:
            if 'conexion' in locals(): conexion.close()

    # ==========================================
    # 🔍 VER DETALLE DE SEMANA
    # ==========================================
    def ver_detalle_semana(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Primero seleccioná una semana de la tabla haciendo clic sobre ella.")
            return

        item_id = seleccion[0]
        anio, mes, sem = self.mapa_filas[item_id]

        ventana_det = ctk.CTkToplevel(self)
        ventana_det.title(f"🔍 Detalle de Movimientos (Semana del {mes}/{anio})")
        ventana_det.geometry("700x500")
        ventana_det.grab_set()

        lbl_tit = ctk.CTkLabel(ventana_det, text="Auditoría de Gastos y Ventas", font=("Roboto", 18, "bold"))
        lbl_tit.pack(pady=10)

        frame_det = ctk.CTkFrame(ventana_det)
        frame_det.pack(padx=20, pady=10, fill="both", expand=True)

        tabla_det = ttk.Treeview(frame_det, columns=("fecha", "tipo", "motivo", "monto"), show="headings")
        tabla_det.heading("fecha", text="📅 Fecha y Hora")
        tabla_det.heading("tipo", text="🔄 Tipo")
        tabla_det.heading("motivo", text="📝 Motivo / Medio")
        tabla_det.heading("monto", text="💵 Monto")

        tabla_det.column("fecha", width=150, anchor="center")
        tabla_det.column("tipo", width=100, anchor="center")
        tabla_det.column("motivo", width=250, anchor="w")
        tabla_det.column("monto", width=100, anchor="e")
        
        tabla_det.tag_configure("ingreso", foreground="#2FA572") 
        tabla_det.tag_configure("egreso", foreground="#D32F2F")  

        scrollbar = ttk.Scrollbar(frame_det, orient="vertical", command=tabla_det.yview)
        tabla_det.configure(yscrollcommand=scrollbar.set)
        tabla_det.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            
            cursor.execute("SELECT fecha, medio_pago, total FROM ventas WHERE strftime('%Y', fecha) = ? AND strftime('%W', fecha) = ?", (anio, sem))
            for f, medio, tot in cursor.fetchall():
                tabla_det.insert("", "end", values=(f, "Ingreso", f"Venta en {medio}", f"+ ${tot:.2f}"), tags=("ingreso",))

            try:
                cursor.execute("SELECT fecha, motivo, (monto_efectivo + monto_transf) FROM gastos WHERE strftime('%Y', fecha) = ? AND strftime('%W', fecha) = ?", (anio, sem))
                for f, motivo, tot in cursor.fetchall():
                    tabla_det.insert("", "end", values=(f, "Gasto", motivo, f"- ${tot:.2f}"), tags=("egreso",))
            except sqlite3.OperationalError:
                pass

        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            if 'conexion' in locals(): conexion.close()

    # ==========================================
    # 📊 GRÁFICO DE TORTA
    # ==========================================
    def abrir_menu_graficos(self):
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            messagebox.showerror("⚠️ Componente Faltante", "Para generar gráficos profesionales necesitas instalar una librería.\n\nAbrí tu terminal o consola y escribí:\npip install matplotlib")
            return

        ventana_graf = ctk.CTkToplevel(self)
        ventana_graf.title("📊 Selector de Gráficos")
        ventana_graf.geometry("350x250")
        ventana_graf.grab_set()

        ctk.CTkLabel(ventana_graf, text="¿Qué período querés analizar?", font=("Roboto", 16, "bold")).pack(pady=(20, 10))

        combo_periodo = ctk.CTkComboBox(ventana_graf, values=["Mes Actual", "Últimos 3 meses", "Año Actual", "Todo el Historial"], font=("Roboto", 14), width=250, state="readonly")
        combo_periodo.set("Mes Actual")
        combo_periodo.pack(pady=15)

        def generar_torta():
            periodo = combo_periodo.get()
            anio_actual = datetime.now().strftime("%Y")
            mes_actual = datetime.now().strftime("%m")

            query = "SELECT motivo, SUM(monto_efectivo + monto_transf) FROM gastos"
            parametros = []

            if periodo == "Mes Actual":
                query += " WHERE strftime('%Y', fecha) = ? AND strftime('%m', fecha) = ?"
                parametros = [anio_actual, mes_actual]
                
            elif periodo == "Últimos 3 meses":
                fecha_limite = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
                query += " WHERE fecha >= ?"
                parametros = [fecha_limite]
                
            elif periodo == "Año Actual":
                query += " WHERE strftime('%Y', fecha) = ?"
                parametros = [anio_actual]

            query += " GROUP BY motivo ORDER BY SUM(monto_efectivo + monto_transf) DESC"

            try:
                conexion = sqlite3.connect(self.ruta_db)
                cursor = conexion.cursor()
                cursor.execute(query, parametros)
                resultados = cursor.fetchall()
                conexion.close()

                if not resultados:
                    messagebox.showwarning("Aviso", f"No hay gastos registrados en el período: {periodo}")
                    return

                motivos = [fila[0] for fila in resultados]
                montos = [float(fila[1]) for fila in resultados]

                plt.figure(figsize=(8, 6))
                plt.pie(montos, labels=motivos, autopct='%1.1f%%', startangle=140, shadow=True, colors=plt.cm.Paired.colors)
                plt.title(f"Distribución de Gastos - {periodo}", fontsize=16, fontweight='bold')
                plt.axis('equal') 
                
                ventana_graf.destroy()
                plt.show() 

            except Exception as e:
                messagebox.showerror("Error SQL", str(e))

        ctk.CTkButton(ventana_graf, text="✅ Mostrar Gráfico", fg_color="#2FA572", hover_color="#238259", height=40, font=("Roboto", 14, "bold"), command=generar_torta).pack(pady=20)

if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("100x100")
    app.withdraw()
    v = VentanaEstadisticas(app)
    app.mainloop()
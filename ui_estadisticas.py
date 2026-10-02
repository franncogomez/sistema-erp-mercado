import customtkinter as ctk
from tkinter import ttk
import sqlite3
import os

class VentanaEstadisticas(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("📊 Estadísticas de Ventas")
        self.geometry("600x500")
        self.grab_set()

        self.ruta_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sistema_mercado.db")

        # ==========================================
        # 🎨 DISEÑO DE LA VENTANA
        # ==========================================
        lbl_titulo = ctk.CTkLabel(self, text="Historial de Ingresos", font=("Roboto", 20, "bold"))
        lbl_titulo.pack(pady=(20, 15))

        # 🛡️ Aplicamos el estilo adaptativo (Oscuro/Claro) para proteger la vista
        self.aplicar_estilo_tabla()

        # ==========================================
        # 📊 TABLA DE RESULTADOS
        # ==========================================
        frame_tabla = ctk.CTkFrame(self)
        frame_tabla.pack(pady=10, padx=20, fill="both", expand=True)

        columnas = ("mes", "semana", "total")
        self.tabla = ttk.Treeview(frame_tabla, columns=columnas, show="headings", height=12)
        
        self.tabla.heading("mes", text="📅 Mes")
        self.tabla.heading("semana", text="📆 Semana del Mes")
        self.tabla.heading("total", text="💰 Ingreso Bruto ($)")

        self.tabla.column("mes", width=180, anchor="center")
        self.tabla.column("semana", width=150, anchor="center")
        self.tabla.column("total", width=150, anchor="center")

        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=scrollbar.set)
        
        self.tabla.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.cargar_datos()

    def aplicar_estilo_tabla(self):
        style = ttk.Style(self)
        style.theme_use("default")
        
        # Detectamos el tema de CustomTkinter para pintar la tabla acorde
        modo = ctk.get_appearance_mode()
        if modo == "Dark":
            bg_color = "#2b2b2b"
            fg_color = "white"
            field_bg = "#2b2b2b"
            head_bg = "#1f538d"
            seleccion = "#14375e"
        else:
            bg_color = "#f2f2f2"
            fg_color = "black"
            field_bg = "#f2f2f2"
            head_bg = "#3a7ebf"
            seleccion = "#9ec5eb"

        style.configure("Treeview", 
                        background=bg_color, 
                        foreground=fg_color, 
                        rowheight=35, 
                        fieldbackground=field_bg,
                        font=("Roboto", 12))
        
        style.configure("Treeview.Heading", 
                        background=head_bg, 
                        foreground="white", 
                        font=("Roboto", 13, "bold"),
                        padding=5)
        
        style.map('Treeview', background=[('selected', seleccion)])

    # ==========================================
    # ⚙️ LÓGICA DE AGRUPACIÓN (Mes y Semanas)
    # ==========================================
    def cargar_datos(self):
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()

            # Agrupamos por año, mes y semana calendario de SQLite. 
            # El orden ascendente (ASC) nos permite calcular qué número de semana es dentro del mes.
            cursor.execute("""
                SELECT 
                    strftime('%Y', fecha) as anio,
                    strftime('%m', fecha) as mes,
                    strftime('%W', fecha) as semana_anio,
                    SUM(total) as total_ventas
                FROM ventas 
                GROUP BY anio, mes, semana_anio
                ORDER BY anio ASC, mes ASC, semana_anio ASC
            """)
            resultados = cursor.fetchall()

            meses_nombres = {
                "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril", 
                "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto", 
                "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"
            }

            # Organizamos los datos en un diccionario: { ('2026', '09'): [ total_sem1, total_sem2, ... ] }
            historial = {}

            for anio, mes, sem, total in resultados:
                clave = (anio, mes)
                if clave not in historial:
                    historial[clave] = []
                historial[clave].append(total)

            # Insertamos en la tabla en reversa (para ver lo más actual arriba de todo)
            for clave in reversed(list(historial.keys())):
                anio, mes = clave
                nombre_mes = f"{meses_nombres.get(mes, mes)} {anio}"
                semanas_del_mes = historial[clave]
                
                # Invertimos también las semanas para ver "Semana 4" antes que "Semana 1"
                for indice_semana in reversed(range(len(semanas_del_mes))):
                    total_semana = semanas_del_mes[indice_semana]
                    texto_semana = f"Semana {indice_semana + 1}"
                    texto_total = f"${total_semana:.2f}" if total_semana else "$0.00"
                    
                    self.tabla.insert("", "end", values=(nombre_mes, texto_semana, texto_total))

        except Exception as e:
            print(f"Error al cargar estadísticas: {e}")
        finally:
            if 'conexion' in locals():
                conexion.close()
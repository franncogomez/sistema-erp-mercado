import customtkinter as ctk
import sqlite3
import shutil
import csv
import os
from rutas import RUTA_DB
from datetime import datetime, timedelta
from tkinter import ttk, messagebox, filedialog

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

        self.btn_detalle = ctk.CTkButton(frame_acciones, text="🔍 Ver Detalle", fg_color="#1E88E5", hover_color="#1565C0", height=45, font=("Roboto", 14, "bold"), command=self.ver_detalle_semana)
        self.btn_detalle.pack(side="left", padx=5, expand=True, fill="x")

        self.btn_exportar = ctk.CTkButton(frame_acciones, text="📥 Exportar (Contador)", fg_color="#2FA572", hover_color="#237a54", height=45, font=("Roboto", 14, "bold"), command=self.abrir_menu_exportar)
        self.btn_exportar.pack(side="left", padx=5, expand=True, fill="x")
        
        # 🏆 NUEVO BOTÓN: TOP VENTAS
        self.btn_ranking = ctk.CTkButton(frame_acciones, text="🏆 Top 10 Ventas", fg_color="#F59E0B", hover_color="#D97706", height=45, font=("Roboto", 14, "bold"), command=self.abrir_ranking_ventas)
        self.btn_ranking.pack(side="left", padx=5, expand=True, fill="x")

        self.btn_grafico = ctk.CTkButton(frame_acciones, text="📊 Gráficos", fg_color="#8E24AA", hover_color="#6A1B9A", height=45, font=("Roboto", 14, "bold"), command=self.abrir_menu_graficos)
        self.btn_grafico.pack(side="left", padx=5, expand=True, fill="x")

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
                cursor.execute("PRAGMA table_info(gastos)")
                cols = [c[1] for c in cursor.fetchall()]
                if 'monto_mp' in cols:
                    q_g = "SELECT strftime('%Y', fecha), strftime('%m', fecha), strftime('%W', fecha), (COALESCE(monto_efectivo,0) + COALESCE(monto_transf,0) + COALESCE(monto_mp,0)) FROM gastos"
                else:
                    q_g = "SELECT strftime('%Y', fecha), strftime('%m', fecha), strftime('%W', fecha), (COALESCE(monto_efectivo,0) + COALESCE(monto_transf,0)) FROM gastos"
                
                cursor.execute(q_g)
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
    # ↕️ LÓGICA DE ORDENAMIENTO (DETALLES)
    # ==========================================
    def ordenar_detalle_columna(self, tabla, col):
        if not hasattr(tabla, 'orden_desc'):
            tabla.orden_desc = {"tipo": True, "monto": True}

        reverso = tabla.orden_desc[col]
        items = [(tabla.set(k, col), k) for k in tabla.get_children('')]

        if col == "monto":
            def a_numero(x):
                s = x[0].replace('$', '').replace(' ', '')
                try: return float(s)
                except ValueError: return 0.0
            
            items.sort(key=a_numero, reverse=reverso)
        else:
            items.sort(key=lambda x: x[0], reverse=reverso)

        for index, (val, k) in enumerate(items):
            tabla.move(k, '', index)

        tabla.orden_desc[col] = not reverso
        flecha = " 🔽" if reverso else " 🔼"
        tabla.heading("tipo", text="🔄 Tipo ↕️")
        tabla.heading("monto", text="💵 Monto ↕️")
        
        texto_base = "🔄 Tipo" if col == "tipo" else "💵 Monto"
        tabla.heading(col, text=texto_base + flecha)

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
        ventana_det.geometry("820x500") 
        ventana_det.grab_set()

        lbl_tit = ctk.CTkLabel(ventana_det, text="Auditoría de Gastos y Ventas", font=("Roboto", 18, "bold"))
        lbl_tit.pack(pady=10)

        frame_det = ctk.CTkFrame(ventana_det)
        frame_det.pack(padx=20, pady=10, fill="both", expand=True)

        tabla_det = ttk.Treeview(frame_det, columns=("dia", "fecha", "tipo", "motivo", "monto"), show="headings")
        tabla_det.heading("dia", text="📆 Día")
        tabla_det.heading("fecha", text="🕒 Fecha y Hora")
        
        tabla_det.heading("tipo", text="🔄 Tipo ↕️", command=lambda: self.ordenar_detalle_columna(tabla_det, "tipo"))
        tabla_det.heading("motivo", text="📝 Motivo / Medio")
        tabla_det.heading("monto", text="💵 Monto ↕️", command=lambda: self.ordenar_detalle_columna(tabla_det, "monto"))

        tabla_det.column("dia", width=90, anchor="center")
        tabla_det.column("fecha", width=140, anchor="center")
        tabla_det.column("tipo", width=80, anchor="center")
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
            
            movimientos = [] 

            cursor.execute("SELECT fecha, medio_pago, total FROM ventas WHERE strftime('%Y', fecha) = ? AND strftime('%W', fecha) = ?", (anio, sem))
            for f, medio, tot in cursor.fetchall():
                movimientos.append((f, "Ingreso", f"Venta en {medio}", tot, "ingreso"))

            try:
                cursor.execute("PRAGMA table_info(gastos)")
                cols = [c[1] for c in cursor.fetchall()]
                if 'monto_mp' in cols:
                    q_g = "SELECT fecha, motivo, COALESCE(monto_efectivo,0), COALESCE(monto_mp,0), COALESCE(monto_transf,0) FROM gastos WHERE strftime('%Y', fecha) = ? AND strftime('%W', fecha) = ?"
                    cursor.execute(q_g, (anio, sem))
                    for f, motivo, efec, mp, transf in cursor.fetchall():
                        tot = efec + mp + transf
                        detalles = []
                        if efec > 0: detalles.append(f"Ef. ${efec:.2f}")
                        if mp > 0: detalles.append(f"MP ${mp:.2f}")
                        if transf > 0: detalles.append(f"Trcia ${transf:.2f}")
                        
                        txt_pago = " - ".join(detalles)
                        motivo_final = f"{motivo} ({txt_pago})" if txt_pago else motivo
                        
                        movimientos.append((f, "Gasto", motivo_final, tot, "egreso"))
                else:
                    q_g = "SELECT fecha, motivo, COALESCE(monto_efectivo,0), 0, COALESCE(monto_transf,0) FROM gastos WHERE strftime('%Y', fecha) = ? AND strftime('%W', fecha) = ?"
                    cursor.execute(q_g, (anio, sem))
                    for f, motivo, efec, mp, transf in cursor.fetchall():
                        tot = efec + transf
                        detalles = []
                        if efec > 0: detalles.append(f"Ef. ${efec:.2f}")
                        if transf > 0: detalles.append(f"Trcia ${transf:.2f}")
                        
                        txt_pago = " - ".join(detalles)
                        motivo_final = f"{motivo} ({txt_pago})" if txt_pago else motivo
                        
                        movimientos.append((f, "Gasto", motivo_final, tot, "egreso"))
            except sqlite3.OperationalError:
                pass

            movimientos.sort(key=lambda x: x[0])

            dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

            for f, tipo, motivo, tot, tag in movimientos:
                try:
                    dt = datetime.strptime(f, "%Y-%m-%d %H:%M:%S")
                    nombre_dia = dias_semana[dt.weekday()]
                    fecha_str = dt.strftime("%d/%m/%Y %H:%M")
                except:
                    nombre_dia = "-"
                    fecha_str = f
                    
                monto_str = f"+ ${tot:.2f}" if tag == "ingreso" else f"- ${tot:.2f}"
                tabla_det.insert("", "end", values=(nombre_dia, fecha_str, tipo, motivo, monto_str), tags=(tag,))

        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            if 'conexion' in locals(): conexion.close()

    # ==========================================
    # 📥 EXPORTAR EXCEL (CONTADOR / AFIP)
    # ==========================================
    def abrir_menu_exportar(self):
        ventana_exp = ctk.CTkToplevel(self)
        ventana_exp.title("📥 Exportar Datos")
        ventana_exp.geometry("400x380")
        ventana_exp.grab_set()

        ctk.CTkLabel(ventana_exp, text="Descargar Excel para el Contador", font=("Roboto", 18, "bold")).pack(pady=(20, 10))

        ctk.CTkLabel(ventana_exp, text="¿Qué período querés exportar?:", font=("Roboto", 14)).pack(pady=(10, 0))
        combo_periodo = ctk.CTkComboBox(ventana_exp, values=["Mes Actual", "Mes Anterior", "Todo el Historial"], font=("Roboto", 14), width=280, state="readonly")
        combo_periodo.set("Mes Actual")
        combo_periodo.pack(pady=5)

        ctk.CTkLabel(ventana_exp, text="Filtro de Datos:", font=("Roboto", 14)).pack(pady=(10, 0))
        combo_tipo = ctk.CTkComboBox(ventana_exp, values=["Solo Facturas Fiscales (AFIP)", "Todo (Fiscal + Ticket Interno)"], font=("Roboto", 14), width=280, state="readonly")
        combo_tipo.set("Solo Facturas Fiscales (AFIP)")
        combo_tipo.pack(pady=5)

        def procesar_exportacion():
            periodo = combo_periodo.get()
            tipo_export = combo_tipo.get()

            hoy = datetime.now()
            filtro_fecha = ""
            parametros = []

            if periodo == "Mes Actual":
                filtro_fecha = "WHERE strftime('%Y-%m', fecha) = ?"
                parametros = [hoy.strftime("%Y-%m")]
            elif periodo == "Mes Anterior":
                primer_dia_mes_actual = hoy.replace(day=1)
                mes_anterior = primer_dia_mes_actual - timedelta(days=1)
                filtro_fecha = "WHERE strftime('%Y-%m', fecha) = ?"
                parametros = [mes_anterior.strftime("%Y-%m")]

            filtro_tipo = ""
            if tipo_export == "Solo Facturas Fiscales (AFIP)":
                if filtro_fecha:
                    filtro_tipo = " AND tipo_comprobante != 'TICKET NO FISCAL' AND tipo_comprobante IS NOT NULL"
                else:
                    filtro_tipo = "WHERE tipo_comprobante != 'TICKET NO FISCAL' AND tipo_comprobante IS NOT NULL"

            query = f"SELECT id_venta, fecha, total, medio_pago, tipo_comprobante, nro_comprobante, cae, doc_cliente FROM ventas {filtro_fecha} {filtro_tipo} ORDER BY fecha DESC"

            try:
                conexion = sqlite3.connect(self.ruta_db)
                cursor = conexion.cursor()
                
                cursor.execute("PRAGMA table_info(ventas)")
                columnas_db = [c[1] for c in cursor.fetchall()]
                
                if 'tipo_comprobante' not in columnas_db:
                    messagebox.showwarning("Base desactualizada", "No tenés facturas AFIP registradas todavía.", parent=ventana_exp)
                    conexion.close()
                    return

                cursor.execute(query, parametros)
                resultados = cursor.fetchall()
                conexion.close()

                if not resultados:
                    messagebox.showinfo("Sin Datos", "No se encontraron ventas para exportar con esos filtros.", parent=ventana_exp)
                    return

                nombre_defecto = f"Reporte_Contador_{hoy.strftime('%Y_%m')}.csv"
                ruta_guardado = filedialog.asksaveasfilename(
                    parent=ventana_exp,
                    title="Guardar Excel como...",
                    defaultextension=".csv",
                    initialfile=nombre_defecto,
                    filetypes=[("Archivo Excel CSV", "*.csv")]
                )

                if not ruta_guardado:
                    return

                with open(ruta_guardado, mode='w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f, delimiter=';') 
                    # 🛠️ ORDEN PERFECTO PARA EL CONTADOR (Incluye NETO E IVA)
                    writer.writerow(["ID", "FECHA / HORA", "COMPROBANTE", "NRO COMPROBANTE", "DOC CLIENTE", "MEDIO DE PAGO", "NETO GRAVADO", "IVA", "TOTAL", "CAE"])
                    
                    for fila in resultados:
                        id_v, fecha, tot, mp, tipo, nro, cae, doc = fila
                        
                        tipo_limpio = str(tipo) if tipo else "TICKET NO FISCAL"
                        nro_limpio = str(nro) if (nro and nro != 0) else "-"
                        cae_limpio = str(cae) if cae else "-"
                        doc_limpio = str(doc) if doc else "Consumidor Final"
                        
                        # 🛠️ MAGIA PARA QUE EL CAE NO SE ACHIQUE EN EXCEL[cite: 8]
                        if cae_limpio != "-":
                            cae_excel = f'="{cae_limpio}"'
                        else:
                            cae_excel = "-"
                            
                        # 🛠️ MATEMÁTICA FISCAL: Calcular NETO e IVA
                        tot_float = float(tot)
                        if tipo_limpio in ["Factura A", "Factura B"]:
                            neto = round(tot_float / 1.21, 2)
                            iva = round(tot_float - neto, 2)
                        else:
                            # Factura C y Tickets No Fiscales no discriminan IVA
                            neto = tot_float
                            iva = 0.0
                            
                        # Convertir punto por coma para Excel Argentina
                        neto_fmt = f"{neto:.2f}".replace('.', ',')
                        iva_fmt = f"{iva:.2f}".replace('.', ',')
                        total_fmt = f"{tot_float:.2f}".replace('.', ',')
                        
                        writer.writerow([id_v, fecha, tipo_limpio, nro_limpio, doc_limpio, mp, neto_fmt, iva_fmt, total_fmt, cae_excel])
                try:
                    directorio_base = os.path.dirname(self.ruta_db)
                    carpeta_exportaciones = os.path.join(directorio_base, "exportaciones_contador")
                    os.makedirs(carpeta_exportaciones, exist_ok=True)
                    
                    # Armamos una ruta con nombre de archivo seguro
                    nombre_archivo_seguro = os.path.basename(ruta_guardado)
                    ruta_respaldo = os.path.join(carpeta_exportaciones, f"Copia_{nombre_archivo_seguro}")
                    
                    shutil.copy2(ruta_guardado, ruta_respaldo)
                except Exception as e:
                    print(f"No se pudo crear la copia de seguridad: {e}") # Falla en silencio para el usuario

                messagebox.showinfo("✅ Éxito", f"El archivo se guardó correctamente.\n\nYa está listo para enviarle al contador.", parent=ventana_exp)
                ventana_exp.destroy()

            except Exception as e:
                messagebox.showerror("Error de Exportación", str(e), parent=ventana_exp)

        ctk.CTkButton(ventana_exp, text="✅ Generar y Guardar", fg_color="#2FA572", hover_color="#238259", height=45, font=("Roboto", 14, "bold"), command=procesar_exportacion).pack(pady=25)

    # ==========================================
    # 📊 GRÁFICO PROFESIONAL: BARRAS COMPARATIVAS
    # ==========================================
    def abrir_menu_graficos(self):
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            messagebox.showerror("⚠️ Componente Faltante", "Para generar gráficos profesionales necesitas instalar matplotlib.\n\nAbrí tu terminal y escribí:\npip install matplotlib")
            return

        ventana_graf = ctk.CTkToplevel(self)
        ventana_graf.title("📊 Selector de Gráficos")
        ventana_graf.geometry("350x250")
        ventana_graf.grab_set()

        ctk.CTkLabel(ventana_graf, text="¿Qué período querés analizar?", font=("Roboto", 16, "bold")).pack(pady=(20, 10))

        combo_periodo = ctk.CTkComboBox(ventana_graf, values=["Mes Actual", "Últimos 3 meses", "Año Actual", "Todo el Historial"], font=("Roboto", 14), width=250, state="readonly")
        combo_periodo.set("Últimos 3 meses")
        combo_periodo.pack(pady=15)

        def generar_barras():
            periodo = combo_periodo.get()
            
            try:
                conexion = sqlite3.connect(self.ruta_db)
                cursor = conexion.cursor()

                cursor.execute("PRAGMA table_info(gastos)")
                cols = [c[1] for c in cursor.fetchall()]
                if 'monto_mp' in cols:
                    sum_g = "SUM(COALESCE(monto_efectivo,0) + COALESCE(monto_transf,0) + COALESCE(monto_mp,0))"
                else:
                    sum_g = "SUM(COALESCE(monto_efectivo,0) + COALESCE(monto_transf,0))"

                hoy = datetime.now()
                filtro_fecha = ""
                parametros = []
                
                if periodo == "Mes Actual":
                    formato_sql = "'%Y-%m-%d'" 
                    filtro_fecha = "WHERE strftime('%Y-%m', fecha) = ?"
                    parametros = [hoy.strftime("%Y-%m")]
                elif periodo == "Últimos 3 meses":
                    formato_sql = "'%Y-%m'" 
                    hace_3_meses = (hoy - timedelta(days=90)).strftime("%Y-%m-%d")
                    filtro_fecha = "WHERE fecha >= ?"
                    parametros = [hace_3_meses]
                elif periodo == "Año Actual":
                    formato_sql = "'%Y-%m'"
                    filtro_fecha = "WHERE strftime('%Y', fecha) = ?"
                    parametros = [hoy.strftime("%Y")]
                else:
                    formato_sql = "'%Y-%m'"

                q_ventas = f"SELECT strftime({formato_sql}, fecha) AS p, SUM(total) FROM ventas {filtro_fecha} GROUP BY p"
                q_gastos = f"SELECT strftime({formato_sql}, fecha) AS p, {sum_g} FROM gastos {filtro_fecha} GROUP BY p"

                cursor.execute(q_ventas, parametros)
                res_v = cursor.fetchall()
                
                cursor.execute(q_gastos, parametros)
                res_g = cursor.fetchall()
                conexion.close()

                data_plot = {}
                for p, tot in res_v:
                    if p not in data_plot: data_plot[p] = {'v': 0.0, 'g': 0.0}
                    if p: data_plot[p]['v'] += float(tot or 0)
                    
                for p, tot in res_g:
                    if p not in data_plot: data_plot[p] = {'v': 0.0, 'g': 0.0}
                    if p: data_plot[p]['g'] += float(tot or 0)

                if not data_plot:
                    messagebox.showwarning("Aviso", f"No hay movimientos registrados en: {periodo}")
                    return

                labels = sorted([k for k in data_plot.keys() if k is not None])
                ventas_vals = [data_plot[L]['v'] for L in labels]
                gastos_vals = [data_plot[L]['g'] for L in labels]

                x = range(len(labels))
                width = 0.35
                
                x_ventas = [i - width/2 for i in x]
                x_gastos = [i + width/2 for i in x]

                nice_labels = []
                for l in labels:
                    if len(l) == 10: nice_labels.append(f"{l[8:10]}/{l[5:7]}")
                    elif len(l) == 7: nice_labels.append(f"{l[5:7]}/{l[0:4]}")
                    else: nice_labels.append(l)

                modo_actual = ctk.get_appearance_mode()
                
                if modo_actual == "Dark":
                    plt.style.use('dark_background')
                    color_fondo = '#2b2b2b' 
                    plt.rcParams['figure.facecolor'] = color_fondo
                    plt.rcParams['axes.facecolor'] = color_fondo
                    plt.rcParams['savefig.facecolor'] = color_fondo
                    color_ingresos = '#2FA572' 
                    color_gastos = '#EF4444'   
                else:
                    plt.style.use('ggplot')
                    color_ingresos = '#2FA572'
                    color_gastos = '#D32F2F'

                fig, ax = plt.subplots(figsize=(10, 6))
                
                rects1 = ax.bar(x_ventas, ventas_vals, width, label='Ingresos 📈', color=color_ingresos)
                rects2 = ax.bar(x_gastos, gastos_vals, width, label='Gastos 📉', color=color_gastos)

                ax.set_ylabel('Monto en Pesos ($)', fontweight='bold')
                ax.set_title(f'Balance Comercial: Ingresos vs Gastos ({periodo})', fontsize=15, fontweight='bold', pad=20)
                ax.set_xticks(list(x))
                ax.set_xticklabels(nice_labels, rotation=45 if len(nice_labels)>6 else 0)
                ax.legend(fontsize=12)

                ax.bar_label(rects1, fmt='$%.0f', padding=3, fontsize=9)
                ax.bar_label(rects2, fmt='$%.0f', padding=3, fontsize=9)

                fig.tight_layout()
                
                if modo_actual == "Dark":
                    manager = plt.get_current_fig_manager()
                    try:
                        manager.window.configure(bg='#2b2b2b')
                        for widget in manager.window.winfo_children():
                            try: widget.configure(bg='#2b2b2b')
                            except: pass
                            
                        import ctypes
                        manager.window.update()
                        hwnd = ctypes.windll.user32.GetParent(manager.window.winfo_id())
                        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(2)), 4) 
                        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(ctypes.c_int(2)), 4) 
                    except Exception:
                        pass
                
                ventana_graf.destroy()  
                self.withdraw()         
                
                plt.show()              
                
                self.deiconify()        
                self.grab_set()         
                self.lift()             

            except Exception as e:
                messagebox.showerror("Error Analítico", f"Error al generar gráfico:\n{e}")

        ctk.CTkButton(ventana_graf, text="✅ Mostrar Gráfico", fg_color="#1E88E5", hover_color="#1565C0", height=40, font=("Roboto", 14, "bold"), command=generar_barras).pack(pady=20)
    
    # ==========================================
    # 🏆 RANKING DE PRODUCTOS MÁS VENDIDOS 
    # ==========================================
    def abrir_ranking_ventas(self):
        ventana_top = ctk.CTkToplevel(self)
        ventana_top.title("🏆 Ranking Dinámico de Productos")
        ventana_top.geometry("850x620")
        ventana_top.grab_set()

        # --- ENCABEZADO ---
        ctk.CTkLabel(ventana_top, text="Ranking de Ventas", font=("Roboto", 22, "bold"), text_color="#F59E0B").pack(pady=(15, 0))
        ctk.CTkLabel(ventana_top, text="Analizá cuáles son los productos que más rinden en tu negocio.", font=("Roboto", 13), text_color="gray").pack(pady=(0, 15))

        # --- PANEL DE FILTROS ---
        frame_filtros = ctk.CTkFrame(ventana_top, fg_color="transparent")
        frame_filtros.pack(fill="x", padx=20, pady=5)
        
        # Filtro de Período
        ctk.CTkLabel(frame_filtros, text="📅 Período:", font=("Roboto", 13, "bold")).pack(side="left", padx=(0, 5))
        combo_periodo = ctk.CTkComboBox(frame_filtros, values=["Mes Actual", "Mes Anterior", "Últimos 30 Días", "Año Actual", "Todo el Historial"], width=140, state="readonly")
        combo_periodo.set("Mes Actual")
        combo_periodo.pack(side="left", padx=5)

        # Filtro de Orden (Cantidad vs Recaudación)
        ctk.CTkLabel(frame_filtros, text="🎯 Ordenar por:", font=("Roboto", 13, "bold")).pack(side="left", padx=(15, 5))
        combo_orden = ctk.CTkComboBox(frame_filtros, values=["Unidades Vendidas", "Dinero Recaudado"], width=160, state="readonly")
        combo_orden.set("Unidades Vendidas")
        combo_orden.pack(side="left", padx=5)

        # Filtro de Límite
        ctk.CTkLabel(frame_filtros, text="📊 Mostrar:", font=("Roboto", 13, "bold")).pack(side="left", padx=(15, 5))
        combo_limite = ctk.CTkComboBox(frame_filtros, values=["Top 10", "Top 20", "Top 50", "Todos"], width=100, state="readonly")
        combo_limite.set("Top 20")
        combo_limite.pack(side="left", padx=5)

        # --- TABLA DE RESULTADOS ---
        frame_tabla = ctk.CTkFrame(ventana_top)
        frame_tabla.pack(padx=20, pady=10, fill="both", expand=True)

        columnas = ("pos", "codigo", "nombre", "cantidad", "recaudado")
        tabla_top = ttk.Treeview(frame_tabla, columns=columnas, show="headings", height=12)
        
        tabla_top.heading("pos", text="🏆 #")
        tabla_top.heading("codigo", text="Código")
        tabla_top.heading("nombre", text="📦 Producto")
        tabla_top.heading("cantidad", text="📈 Unidades")
        tabla_top.heading("recaudado", text="💰 Recaudado")

        tabla_top.column("pos", width=60, anchor="center")
        tabla_top.column("codigo", width=120, anchor="center")
        tabla_top.column("nombre", width=280, anchor="w")
        tabla_top.column("cantidad", width=120, anchor="center")
        tabla_top.column("recaudado", width=140, anchor="e")

        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=tabla_top.yview)
        tabla_top.configure(yscrollcommand=scrollbar.set)
        tabla_top.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- MOTOR DE BÚSQUEDA DINÁMICA ---
        def refrescar_ranking(*args):
            # Limpiamos la tabla antes de cargar nuevos datos
            for item in tabla_top.get_children():
                tabla_top.delete(item)

            periodo = combo_periodo.get()
            orden = combo_orden.get()
            limite_txt = combo_limite.get()

            # 1. Configurar Límite
            limite_sql = ""
            if limite_txt != "Todos":
                lim = int(limite_txt.replace("Top ", ""))
                limite_sql = f"LIMIT {lim}"

            # 2. Configurar Orden (Cantidad o Plata)
            orden_sql = "ORDER BY total_unidades DESC"
            if orden == "Dinero Recaudado":
                orden_sql = "ORDER BY dinero_generado DESC"

            # 3. Configurar Fechas
            hoy = datetime.now()
            filtro_fecha = ""
            parametros = []

            if periodo == "Mes Actual":
                filtro_fecha = "AND strftime('%Y-%m', v.fecha) = ?"
                parametros = [hoy.strftime("%Y-%m")]
            elif periodo == "Mes Anterior":
                primer_dia_mes_actual = hoy.replace(day=1)
                mes_anterior = primer_dia_mes_actual - timedelta(days=1)
                filtro_fecha = "AND strftime('%Y-%m', v.fecha) = ?"
                parametros = [mes_anterior.strftime("%Y-%m")]
            elif periodo == "Últimos 30 Días":
                hace_30 = (hoy - timedelta(days=30)).strftime("%Y-%m-%d")
                filtro_fecha = "AND v.fecha >= ?"
                parametros = [hace_30]
            elif periodo == "Año Actual":
                filtro_fecha = "AND strftime('%Y', v.fecha) = ?"
                parametros = [hoy.strftime("%Y")]

            # 4. Consulta SQL con JOIN (Unimos ventas_detalle con ventas para saber la fecha)
            query = f'''
                SELECT vd.codigo_producto, vd.nombre_producto, SUM(vd.cantidad) as total_unidades, SUM(vd.subtotal) as dinero_generado
                FROM ventas_detalle vd
                JOIN ventas v ON vd.id_venta = v.id_venta
                WHERE vd.codigo_producto != 'DESC' {filtro_fecha}
                GROUP BY vd.codigo_producto
                {orden_sql}
                {limite_sql}
            '''

            try:
                conexion = sqlite3.connect(self.ruta_db)
                cursor = conexion.cursor()
                cursor.execute(query, parametros)
                resultados = cursor.fetchall()
                conexion.close()

                if not resultados:
                    tabla_top.insert("", "end", values=("-", "-", "No hay ventas en este período o no coinciden con los filtros.", "-", "-"))
                else:
                    medalla = ["🥇", "🥈", "🥉"]
                    for i, fila in enumerate(resultados):
                        codigo, nombre, cantidad, recaudado = fila
                        
                        posicion = medalla[i] if i < 3 else f"{i+1}º"
                        # Quitamos decimales si se vendieron unidades enteras
                        cant_mostrar = int(cantidad) if float(cantidad).is_integer() else round(float(cantidad), 2)
                        
                        tabla_top.insert("", "end", values=(posicion, codigo, nombre, f"{cant_mostrar} un.", f"$ {recaudado:.2f}"))
            except Exception as e:
                messagebox.showerror("Error", f"Fallo al cargar datos de ranking:\n{e}", parent=ventana_top)

        # Conectar el cambio de los menúes desplegables para que gatillen el refresco automático
        combo_periodo.configure(command=refrescar_ranking)
        combo_orden.configure(command=refrescar_ranking)
        combo_limite.configure(command=refrescar_ranking)

        # Cargar los datos la primera vez que se abre la ventana
        refrescar_ranking()

        # Botón cerrar
        btn_cerrar = ctk.CTkButton(ventana_top, text="Cerrar Panel", fg_color="#546E7A", hover_color="#455A64", font=("Roboto", 14), command=ventana_top.destroy)
        btn_cerrar.pack(pady=10)

if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("100x100")
    app.withdraw()
    v = VentanaEstadisticas(app)
    app.mainloop()
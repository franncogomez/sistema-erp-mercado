import customtkinter as ctk
import tkinter.messagebox as messagebox
from tkinter import ttk
import sqlite3
import os
from tkinter import filedialog
import pandas as pd
from rutas import RUTA_DB

class VentanaStock(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("📦 Gestión de Inventario")
        self.geometry("1050x650") 
        self.grab_set()
        self.ruta_db = RUTA_DB

        # ==========================================
        # 🟢 TÍTULO
        # ==========================================
        self.lbl_titulo = ctk.CTkLabel(self, text="📦 Panel de Control de Stock", font=("Roboto", 24, "bold"))
        self.lbl_titulo.pack(pady=(15, 5))

        # ==========================================
        # 🔵 BARRA SUPERIOR (Filtro Dinámico, Buscador y Excel)
        # ==========================================
        self.frame_top = ctk.CTkFrame(self, fg_color="transparent", height=45)
        self.frame_top.pack(pady=5, padx=20, fill="x")
        self.frame_top.pack_propagate(False) 

        # 1. Filtro de Stock Crítico Personalizable (Switch + Entry)
        self.frame_critico = ctk.CTkFrame(self.frame_top, fg_color="transparent")
        self.frame_critico.place(relx=0.0, rely=0.5, anchor="w")

        self.filtro_reponer_var = ctk.BooleanVar(value=False)
        self.switch_reponer = ctk.CTkSwitch(
            self.frame_critico, 
            text="⚠️ Stock Crítico ≤", 
            font=("Roboto", 13, "bold"), 
            text_color="#EF4444", 
            variable=self.filtro_reponer_var, 
            command=self.aplicar_filtro
        )
        self.switch_reponer.pack(side="left")

        self.entry_umbral = ctk.CTkEntry(self.frame_critico, width=45, font=("Roboto", 13, "bold"), justify="center", text_color="#EF4444")
        self.entry_umbral.insert(0, "5")
        self.entry_umbral.pack(side="left", padx=(5, 0))
        self.entry_umbral.bind("<Return>", lambda e: self.aplicar_filtro())

        # 2. Buscador (Centrado absoluto)
        self.frame_buscador = ctk.CTkFrame(self.frame_top, fg_color="transparent")
        self.frame_buscador.place(relx=0.5, rely=0.5, anchor="center")

        self.lbl_buscar = ctk.CTkLabel(self.frame_buscador, text="🔍 Buscar:", font=("Roboto", 14, "bold"))
        self.lbl_buscar.pack(side="left", padx=5)

        self.combo_filtro_busqueda = ctk.CTkOptionMenu(
            self.frame_buscador, 
            values=["Búsqueda Global", "Solo Nombre", "Solo Marca", "Solo Código"],
            width=140,
            font=("Roboto", 13)
        )
        self.combo_filtro_busqueda.pack(side="left", padx=(0, 5))

        self.entry_buscador = ctk.CTkEntry(self.frame_buscador, width=220, placeholder_text="Escriba aquí...")
        self.entry_buscador.pack(side="left", padx=5)
        self.entry_buscador.focus() 
        self.entry_buscador.bind("<Return>", self.buscar_producto)
        
        self.btn_limpiar = ctk.CTkButton(self.frame_buscador, text="❌ Limpiar", width=70, height=35, fg_color="#C62828", hover_color="#8e1d1d", command=self.limpiar_busqueda)
        self.btn_limpiar.pack(side="left", padx=5)

        # 3. Inyectar Excel (Anclado a la derecha)
        self.btn_importar = ctk.CTkButton(self.frame_top, text="📥 Inyectar Excel", fg_color="#4A148C", hover_color="#311B92", height=35, font=("Roboto", 14, "bold"), command=self.importar_excel)
        self.btn_importar.place(relx=1.0, rely=0.5, anchor="e")

        # ==========================================
        # 🟣 BARRA DE HERRAMIENTAS
        # ==========================================
        self.frame_acciones = ctk.CTkScrollableFrame(self, orientation="horizontal", height=60, fg_color="transparent")
        self.frame_acciones.pack(pady=10, padx=20, fill="x")

        self.btn_corregir = ctk.CTkButton(self.frame_acciones, text="✏️ Corregir Stock", fg_color="#D97706", hover_color="#b36205", height=40, font=("Roboto", 13, "bold"), command=self.corregir_stock)
        self.btn_corregir.pack(side="left", padx=8)
        
        self.btn_editar_nombre = ctk.CTkButton(self.frame_acciones, text="📝 Editar Nombre", fg_color="#1E88E5", hover_color="#1565C0", height=40, font=("Roboto", 13, "bold"), command=self.editar_nombre)
        self.btn_editar_nombre.pack(side="left", padx=8)

        self.btn_editar_precio = ctk.CTkButton(self.frame_acciones, text="💲 Editar Precio", fg_color="#43A047", hover_color="#2E7D32", height=40, font=("Roboto", 13, "bold"), command=self.editar_precio)
        self.btn_editar_precio.pack(side="left", padx=8)

        self.btn_nuevo_suelto = ctk.CTkButton(self.frame_acciones, text="➕ Nuevo Pesable", fg_color="#2FA572", hover_color="#237a54", height=40, font=("Roboto", 13, "bold"), command=self.crear_producto_suelto)
        self.btn_nuevo_suelto.pack(side="left", padx=8)

        self.btn_add_lista = ctk.CTkButton(self.frame_acciones, text="🛒 A la Lista", fg_color="#F59E0B", hover_color="#D97706", height=40, font=("Roboto", 13, "bold"), command=self.añadir_a_lista)
        self.btn_add_lista.pack(side="left", padx=8) 

        self.btn_ver_lista = ctk.CTkButton(self.frame_acciones, text="📝 Abrir Anotador", fg_color="#8E24AA", hover_color="#6A1B9A", height=40, font=("Roboto", 13, "bold"), command=self.abrir_anotador)
        self.btn_ver_lista.pack(side="left", padx=8)

        # 🛠️ NUEVO BOTÓN: Imprimir Etiquetas
        self.btn_imprimir_etiquetas = ctk.CTkButton(self.frame_acciones, text="🖨️ Imprimir Etiquetas", fg_color="#00ACC1", hover_color="#00838F", height=40, font=("Roboto", 13, "bold"), command=self.imprimir_etiquetas)
        self.btn_imprimir_etiquetas.pack(side="left", padx=8)

        self.btn_eliminar = ctk.CTkButton(self.frame_acciones, text="🗑️ Eliminar", width=100, fg_color="#C62828", hover_color="#8e1d1d", height=40, font=("Roboto", 13, "bold"), command=self.eliminar_producto)
        self.btn_eliminar.pack(side="left", padx=8)

        # ==========================================
        # 🟡 LA TABLA DE INVENTARIO CON SCROLLBAR
        # ==========================================
        self.frame_tabla = ctk.CTkFrame(self)
        self.frame_tabla.pack(side="top", padx=20, pady=(5, 15), fill="both", expand=True)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", rowheight=30, font=("Roboto", 12), background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b")
        style.configure("Treeview.Heading", font=("Roboto", 12, "bold"), background="#333333", foreground="white")
        style.map("Treeview", background=[('selected', '#1f538d')])

        columnas = ("codigo", "nombre", "marca", "rubro", "precio", "stock")
        self.tabla = ttk.Treeview(self.frame_tabla, columns=columnas, show="headings")

        self.tabla.heading("codigo", text="Código de Barras")
        self.tabla.heading("nombre", text="Producto")
        self.tabla.heading("marca", text="Marca")
        self.tabla.heading("rubro", text="Rubro")
        self.tabla.heading("precio", text="Precio Venta")
        self.tabla.heading("stock", text="Stock Actual")

        self.tabla.column("codigo", width=130, anchor="center")
        self.tabla.column("nombre", width=300, anchor="w")
        self.tabla.column("marca", width=120, anchor="w")
        self.tabla.column("rubro", width=120, anchor="w")
        self.tabla.column("precio", width=90, anchor="center")
        self.tabla.column("stock", width=90, anchor="center")

        self.tabla.tag_configure("sin_stock", foreground="#EF4444")
        
        self.scrollbar = ttk.Scrollbar(self.frame_tabla, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=self.scrollbar.set)
        
        self.tabla.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=5)
        self.scrollbar.pack(side="right", fill="y", padx=(0, 5), pady=5)

        self.cargar_datos()

    # ==========================================
    # ⚙️ FUNCIONES DE LA BASE DE DATOS Y FILTROS
    # ==========================================
    def obtener_umbral(self):
        try:
            val = int(self.entry_umbral.get().strip())
            return val if val >= 0 else 5
        except ValueError:
            return 5

    def limpiar_busqueda(self):
        self.entry_buscador.delete(0, 'end')
        self.cargar_datos()

    def aplicar_filtro(self):
        if self.entry_buscador.get().strip():
            self.buscar_producto()
        else:
            self.cargar_datos()

    def procesar_fila_tabla(self, codigo, nombre, marca, rubro, precio, stock):
        umbral = self.obtener_umbral()
        try:
            stock_num = int(float(stock)) if stock else 0
        except:
            stock_num = 0
            
        if len(str(codigo)) <= 4:
            stock_mostrar = "Pesable"
            etiqueta = () 
        else:
            stock_mostrar = f"{stock_num} ⚠️" if stock_num <= umbral else str(stock_num)
            etiqueta = ("sin_stock",) if stock_num <= umbral else ()
            
        self.tabla.insert("", "end", values=(codigo, nombre, marca, rubro, f"${precio:.2f}", stock_mostrar), tags=etiqueta)

    def cargar_datos(self):
        for item in self.tabla.get_children(): self.tabla.delete(item)
        
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            
            query = "SELECT codigo_barras, nombre, marca, cat1, precio, stock FROM productos"
            
            if self.filtro_reponer_var.get():
                umbral = self.obtener_umbral()
                query += f" WHERE CAST(stock AS INTEGER) <= {umbral} AND LENGTH(codigo_barras) > 4"
                
            query += " ORDER BY (precio = 0 AND LENGTH(codigo_barras) <= 4) DESC, nombre ASC LIMIT 150"
            
            cursor.execute(query)
            productos = cursor.fetchall()

            for p in productos:
                self.procesar_fila_tabla(*p)

        except Exception as e:
            messagebox.showerror("❌ Error", f"Error al cargar la base de datos:\n{e}")
        finally:
            if 'conexion' in locals(): conexion.close()

    def buscar_producto(self, event=None):
        codigo_buscado = self.entry_buscador.get().strip()
        if not codigo_buscado:
            self.cargar_datos()
            return

        for item in self.tabla.get_children(): self.tabla.delete(item)
            
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            
            palabras = codigo_buscado.split()
            query = "SELECT codigo_barras, nombre, marca, cat1, precio, stock FROM productos WHERE 1=1"
            parametros = []
            
            tipo_busqueda = self.combo_filtro_busqueda.get()

            if self.filtro_reponer_var.get():
                umbral = self.obtener_umbral()
                query += f" AND CAST(stock AS INTEGER) <= {umbral} AND LENGTH(codigo_barras) > 4"

            for palabra in palabras:
                param = f"%{palabra}%"
                if tipo_busqueda == "Búsqueda Global":
                    query += " AND (codigo_barras LIKE ? OR nombre LIKE ? OR marca LIKE ? OR cat1 LIKE ?)"
                    parametros.extend([param, param, param, param])
                elif tipo_busqueda == "Solo Nombre":
                    query += " AND nombre LIKE ?"
                    parametros.append(param)
                elif tipo_busqueda == "Solo Marca":
                    query += " AND marca LIKE ?"
                    parametros.append(param)
                elif tipo_busqueda == "Solo Código":
                    query += " AND codigo_barras LIKE ?"
                    parametros.append(param)
                
            query += " ORDER BY (precio = 0 AND LENGTH(codigo_barras) <= 4) DESC, nombre ASC LIMIT 100"
            
            cursor.execute(query, parametros)
            productos = cursor.fetchall()

            if productos:
                for p in productos:
                    self.procesar_fila_tabla(*p)
                self.tabla.selection_set(self.tabla.get_children()[0])
            else:
                messagebox.showinfo("🔍 Búsqueda", f"No se encontraron productos coincidentes.")
                self.cargar_datos()

        except Exception as e:
            messagebox.showerror("❌ Error", f"Error en la búsqueda:\n{e}")
        finally:
            if 'conexion' in locals(): conexion.close()
            self.entry_buscador.focus()

    # ==========================================
    # 🖨️ IMPRESIÓN DE ETIQUETAS DE GÓNDOLA (Térmica)
    # ==========================================
    # ==========================================
    # 🖨️ IMPRESIÓN DE ETIQUETAS MULTIFORMATO
    # ==========================================
    def imprimir_etiquetas(self):
        seleccion = self.tabla.selection()
        items_a_procesar = seleccion if seleccion else self.tabla.get_children()
        
        if not items_a_procesar:
            messagebox.showwarning("⚠ Vacío", "No hay productos en la tabla para imprimir.")
            return
            
        if seleccion:
            mensaje = f"Se imprimirán {len(seleccion)} productos seleccionados."
        else:
            mensaje = f"Se imprimirán TODOS los {len(items_a_procesar)} productos filtrados."
            
        popup = ctk.CTkToplevel(self)
        popup.title("🖨️ Formato de Impresión")
        popup.geometry("450x380")
        popup.resizable(False, False)
        popup.grab_set()
        popup.attributes("-topmost", True)

        ctk.CTkLabel(popup, text="Configuración de Etiquetas", font=("Roboto", 20, "bold")).pack(pady=(20, 5))
        ctk.CTkLabel(popup, text=mensaje, font=("Roboto", 14), text_color="#1E88E5").pack(pady=(0, 20))

        formato_var = ctk.StringVar(value="termica")

        ctk.CTkRadioButton(popup, text="🧾 Impresora Térmica (Tickeadora 58mm/80mm)", variable=formato_var, value="termica", font=("Roboto", 14)).pack(anchor="w", padx=40, pady=10)
        ctk.CTkRadioButton(popup, text="🏷️ Impresora Zebra / Rollo Etiquetador", variable=formato_var, value="zebra", font=("Roboto", 14)).pack(anchor="w", padx=40, pady=10)
        ctk.CTkRadioButton(popup, text="📄 Hojas A4 (Impresora Láser o Tinta)", variable=formato_var, value="a4", font=("Roboto", 14)).pack(anchor="w", padx=40, pady=10)

        def procesar():
            formato = formato_var.get()
            popup.destroy()
            self.generar_archivo_etiquetas(items_a_procesar, formato)

        ctk.CTkButton(popup, text="✅ Generar Etiquetas", command=procesar, fg_color="#2FA572", hover_color="#238259", height=45, font=("Roboto", 15, "bold")).pack(pady=25)

    def generar_archivo_etiquetas(self, items, formato):
        import tempfile
        import textwrap
        import webbrowser

        # Plantilla CSS para hoja A4 (Cuadrícula de 4 columnas)
        html_a4 = """<html><head><meta charset="utf-8"><style>
            @page { size: A4; margin: 10mm; }
            body { font-family: Arial, sans-serif; background: #fff; color: #000; }
            .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
            .label { border: 1px dashed #aaa; padding: 10px; text-align: center; height: 110px; display: flex; flex-direction: column; justify-content: center; }
            .nombre { font-size: 12px; font-weight: bold; max-height: 35px; overflow: hidden; }
            .precio { font-size: 26px; font-weight: bold; margin: 5px 0; }
            .codigo { font-size: 10px; color: #444; }
        </style></head><body><div class="grid">"""

        # Plantilla CSS para Zebra (Etiqueta individual estándar de 60x40mm)
        html_zebra = """<html><head><meta charset="utf-8"><style>
            @page { size: 60mm 40mm; margin: 2mm; }
            body { font-family: Arial, sans-serif; margin: 0; padding: 0; background: #fff; color: #000; }
            .label { width: 100%; height: 100%; text-align: center; display: flex; flex-direction: column; justify-content: center; align-items: center; page-break-after: always; }
            .nombre { font-size: 14px; font-weight: bold; max-height: 40px; overflow: hidden; width: 95%; line-height: 1.1; }
            .precio { font-size: 34px; font-weight: bold; margin: 3px 0; }
            .codigo { font-size: 12px; }
        </style></head><body>"""

        ticket_termico = "\n"

        for item in items:
            valores = self.tabla.item(item)['values']
            codigo = str(valores[0])
            nombre = str(valores[1]).upper()
            precio = str(valores[4]).replace("$", "").strip()

            if formato == "a4":
                html_a4 += f"<div class='label'><div class='nombre'>{nombre}</div><div class='precio'>${precio}</div><div class='codigo'>Cod: {codigo}</div></div>"
            elif formato == "zebra":
                html_zebra += f"<div class='label'><div class='nombre'>{nombre}</div><div class='precio'>${precio}</div><div class='codigo'>Cod: {codigo}</div></div>"
            else:
                ticket_termico += "-" * 32 + "\n\n"
                for linea in textwrap.wrap(nombre, 32): ticket_termico += f"{linea.center(32)}\n"
                ticket_termico += "\n" + f"$ {precio}".center(32) + "\n\n"
                ticket_termico += f"Cod: {codigo}".center(32) + "\n\n" + "-" * 32 + "\n\n\n\n"

        html_a4 += "</div><script>window.onload = function() { window.print(); }</script></body></html>"
        html_zebra += "<script>window.onload = function() { window.print(); }</script></body></html>"

        try:
            if formato == "termica":
                fd, ruta = tempfile.mkstemp(suffix=".txt")
                with os.fdopen(fd, 'w', encoding='utf-8') as f: f.write(ticket_termico)
                os.startfile(ruta, "print")
            else:
                contenido = html_a4 if formato == "a4" else html_zebra
                fd, ruta = tempfile.mkstemp(suffix=".html")
                with os.fdopen(fd, 'w', encoding='utf-8') as f: f.write(contenido)
                import webbrowser
                webbrowser.open(f"file://{ruta}")
        except Exception as e:
            messagebox.showerror("❌ Error", f"Fallo al generar archivo:\n{e}")

    # ==========================================
    # 🛒 AÑADIR A LISTA INTELIGENTE
    # ==========================================
    def añadir_a_lista(self):
        seleccion = self.tabla.selection()
        items_a_procesar = seleccion if seleccion else self.tabla.get_children()
        
        if not items_a_procesar:
            messagebox.showwarning("⚠ Vacío", "No hay productos en la tabla para agregar.")
            return
            
        if seleccion:
            mensaje = f"¿Desea agregar los {len(seleccion)} productos seleccionados a la lista de compras?"
        else:
            mensaje = f"No ha seleccionado productos específicos.\n\n¿Desea agregar TODOS los {len(items_a_procesar)} productos que se muestran en la tabla a la lista de compras?"
            
        if not messagebox.askyesno("🛒 Confirmar Acción", mensaje):
            return
        
        ruta_txt = os.path.join(os.path.dirname(self.ruta_db), "lista_compras.txt")
        agregados = 0
        
        try:
            with open(ruta_txt, "a", encoding="utf-8") as f:
                for item in items_a_procesar:
                    valores = self.tabla.item(item)['values']
                    nombre = valores[1]
                    f.write(f"- {nombre}\n")
                    agregados += 1
                    
            messagebox.showinfo("✅ Listo", f"Se agregaron {agregados} productos al anotador.")
            self.entry_buscador.focus()
            
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al guardar: {e}")

    def abrir_anotador(self):
        ventana_notas = ctk.CTkToplevel(self)
        ventana_notas.title("📝 Anotador de Faltantes")
        ventana_notas.geometry("450x550")
        ventana_notas.grab_set()

        lbl = ctk.CTkLabel(ventana_notas, text="Lista de Compras / Pendientes", font=("Roboto", 18, "bold"))
        lbl.pack(pady=15)

        caja_texto = ctk.CTkTextbox(ventana_notas, width=400, height=400, font=("Roboto", 16))
        caja_texto.pack(pady=5)

        ruta_txt = os.path.join(os.path.dirname(self.ruta_db), "lista_compras.txt")
        
        if os.path.exists(ruta_txt):
            with open(ruta_txt, "r", encoding="utf-8") as f:
                caja_texto.insert("1.0", f.read())

        def guardar_notas():
            with open(ruta_txt, "w", encoding="utf-8") as f:
                f.write(caja_texto.get("1.0", "end-1c"))
                
            messagebox.showinfo("✅ Guardado", "El anotador se guardó con éxito.")
            ventana_notas.destroy()
            self.entry_buscador.focus()

        btn_guardar = ctk.CTkButton(ventana_notas, text="💾 Guardar Cambios", command=guardar_notas, fg_color="#2FA572", hover_color="#237a54", height=45, font=("Roboto", 14, "bold"))
        btn_guardar.pack(pady=15)

    def crear_producto_suelto(self):
        dialogo_cod = ctk.CTkInputDialog(text="Ingrese un CÓDIGO CORTO (Ej: 1 para Pan, 2 para Tomate):", title="➕ Nuevo Pesable")
        codigo = dialogo_cod.get_input()
        if not codigo or not codigo.strip(): return

        if not codigo.strip().isdigit() or len(codigo.strip()) > 4:
            messagebox.showerror("❌ Error", "El código debe ser de SÓLO NÚMEROS y de máximo 4 dígitos para que sea variable.")
            return

        dialogo_nom = ctk.CTkInputDialog(text="Ingrese el NOMBRE del producto:", title="➕ Nuevo Pesable")
        nombre = dialogo_nom.get_input()
        if not nombre or not nombre.strip(): return

        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            
            cursor.execute("SELECT nombre FROM productos WHERE codigo_barras = ?", (codigo.strip(),))
            if cursor.fetchone():
                messagebox.showerror("❌ Error", "Ese código ya está en uso.")
                return
                
            cursor.execute("INSERT INTO productos (codigo_barras, nombre, precio, stock, marca, cat1, cat2, cat3) VALUES (?, ?, 0, 0, 'Suelto', 'Pesable', '', '')", (codigo.strip(), nombre.strip().upper()))
            conexion.commit()
            
            messagebox.showinfo("✅ Éxito", f"Producto '{nombre.strip().upper()}' creado con éxito.")
            
            if self.entry_buscador.get().strip():
                self.buscar_producto()
            else:
                self.cargar_datos()
                
        except Exception as e:
            messagebox.showerror("❌ Error", f"Ocurrió un error: {e}")
        finally:
            if 'conexion' in locals(): conexion.close()

    def importar_excel(self):
        archivo = filedialog.askopenfilename(
            title="Seleccionar lista del proveedor",
            filetypes=(("Archivos Excel", "*.xlsx *.xls"), ("Archivos CSV", "*.csv"))
        )
        
        if not archivo: return

        try:
            if archivo.endswith('.csv'):
                df = pd.read_csv(archivo, header=None, encoding='latin-1')
            else:
                df = pd.read_excel(archivo, header=None)
                
            header_row_idx = None
            for i, row in df.iterrows():
                row_str = ' '.join(str(val).lower() for val in row.values)
                if ('codigo' in row_str or 'ean' in row_str or 'cod' in row_str) and ('nombre' in row_str or 'descrip' in row_str or 'articulo' in row_str):
                    header_row_idx = i
                    break
            
            if header_row_idx is None:
                messagebox.showerror("Error de Formato", "No se encontraron columnas identificables como Código y Nombre en la misma fila.")
                return
                
            df.columns = df.iloc[header_row_idx]
            df = df[header_row_idx + 1:]
            df.columns = [str(col).strip().lower() for col in df.columns]

            renombres = {
                'ean': 'codigo', 'código': 'codigo', 'cod': 'codigo', 'cod.': 'codigo',
                'artículo': 'nombre', 'articulo': 'nombre', 'descripción': 'nombre', 'descripcion': 'nombre', 'producto': 'nombre',
                'rubro': 'cat1', 'categoría': 'cat1', 'categoria': 'cat1', 'familia': 'cat1', 'sección': 'cat1', 'seccion': 'cat1',
                'fabricante': 'marca', 'laboratorio': 'marca',
                'importe': 'precio', 'precio final': 'precio', 'precio de venta': 'precio'
            }
            df.rename(columns=renombres, inplace=True)

            if 'codigo' not in df.columns or 'nombre' not in df.columns:
                messagebox.showerror("❌ Error de Columnas", "Falta la columna 'codigo' o la columna 'nombre' en su Excel.")
                return

            if 'precio' not in df.columns:
                messagebox.showinfo("⚠️ Aviso sobre Precios", "Su Excel no tiene la columna 'precio'. Se cargarán con precio $0.")

            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            
            nuevos = 0; actualizados = 0; sin_cambios = 0; errores = 0 

            for index, fila in df.iterrows():
                try:
                    val_codigo = fila['codigo']
                    val_nombre = fila['nombre']
                    
                    if 'precio' in df.columns and not pd.isna(fila['precio']):
                        try:
                            val_precio = float(fila['precio'])
                        except ValueError:
                            val_precio = 0.0
                    else:
                        val_precio = 0.0

                    if pd.isna(val_codigo) or pd.isna(val_nombre):
                        errores += 1; continue

                    codigo = str(val_codigo).strip()
                    if codigo.endswith('.0'): codigo = codigo[:-2]
                    if not codigo.isalnum() or len(codigo) < 2:
                        errores += 1; continue
                        
                    nombre = str(val_nombre).strip()
                    if len(nombre) < 2:
                        errores += 1; continue
                    if val_precio < 0: 
                        errores += 1; continue

                    marca = str(fila['marca']).strip() if 'marca' in df.columns and not pd.isna(fila['marca']) else ""
                    cat1 = str(fila['cat1']).strip() if 'cat1' in df.columns and not pd.isna(fila['cat1']) else ""
                    cat2 = str(fila['cat2']).strip() if 'cat2' in df.columns and not pd.isna(fila['cat2']) else ""
                    cat3 = str(fila['cat3']).strip() if 'cat3' in df.columns and not pd.isna(fila['cat3']) else ""

                    cursor.execute("SELECT nombre, precio, marca, cat1, cat2, cat3 FROM productos WHERE codigo_barras = ?", (codigo,))
                    producto_db = cursor.fetchone()

                    if producto_db:
                        precio_db = float(producto_db[1])
                        marca_db = str(producto_db[2]) if producto_db[2] else ""
                        cat1_db = str(producto_db[3]) if producto_db[3] else ""
                        cat2_db = str(producto_db[4]) if producto_db[4] else ""
                        cat3_db = str(producto_db[5]) if producto_db[5] else ""
                        
                        precio_final = val_precio if val_precio > 0 else precio_db
                        marca_final = marca if marca != "" else marca_db
                        cat1_final = cat1 if cat1 != "" else cat1_db
                        cat2_final = cat2 if cat2 != "" else cat2_db
                        cat3_final = cat3 if cat3 != "" else cat3_db
                        
                        if (precio_db != precio_final) or (producto_db[0] != nombre) or (marca_db != marca_final) or (cat1_db != cat1_final):
                            cursor.execute("UPDATE productos SET nombre = ?, precio = ?, marca = ?, cat1 = ?, cat2 = ?, cat3 = ? WHERE codigo_barras = ?", (nombre, precio_final, marca_final, cat1_final, cat2_final, cat3_final, codigo))
                            actualizados += 1
                        else:
                            sin_cambios += 1 
                    else:
                        cursor.execute("INSERT INTO productos (codigo_barras, nombre, precio, stock, marca, cat1, cat2, cat3) VALUES (?, ?, ?, 0, ?, ?, ?, ?)", (codigo, nombre, val_precio, marca, cat1, cat2, cat3))
                        nuevos += 1
                except Exception:
                    errores += 1 

            conexion.commit()
            conexion.close()

            if nuevos == 0 and actualizados == 0 and sin_cambios == 0:
                messagebox.showwarning("Inyección Fallida", f"Se rechazaron todas las filas.\nErrores detectados: {errores}")
            else:
                mensaje = f"Productos Nuevos: {nuevos}\nPrecios/Datos Actualizados: {actualizados}\nOmitidos (Sin cambios): {sin_cambios}\n"
                if errores > 0: mensaje += f"\nSe descartaron {errores} filas por errores."
                messagebox.showinfo("Resumen de Inyección", mensaje)
            
            self.cargar_datos() 

        except Exception as e:
            messagebox.showerror("Error Crítico", f"Fallo al procesar:\n{e}")

    def eliminar_producto(self):
        producto = self.obtener_seleccionado()
        if not producto: return
        
        codigo, nombre = str(producto[0]), producto[1]
        confirmacion = messagebox.askyesno("🗑️ Eliminar Producto", f"¿Está COMPLETAMENTE SEGURO de que desea eliminar?\n\n🛒 {nombre}\n🔢 Código: {codigo}")
        
        if confirmacion:
            try:
                conexion = sqlite3.connect(self.ruta_db)
                cursor = conexion.cursor()
                cursor.execute("DELETE FROM productos WHERE codigo_barras = ?", (codigo,))
                conexion.commit()
                messagebox.showinfo("✅ Éxito", f"El producto '{nombre}' fue eliminado del sistema.")
                if self.entry_buscador.get().strip(): self.buscar_producto()
                else: self.cargar_datos() 
            except Exception as e:
                messagebox.showerror("❌ Error", f"No se pudo eliminar:\n{e}")
            finally:
                if 'conexion' in locals(): conexion.close()
    
    def editar_nombre(self):
        producto = self.obtener_seleccionado()
        if not producto: return
        codigo, nombre = str(producto[0]), producto[1]
        
        dialogo = ctk.CTkInputDialog(text=f"Editando producto:\n{codigo}\n\nNombre actual: {nombre}\nIngrese el NUEVO NOMBRE:", title="📝 Editar Nombre")
        nuevo_nombre = dialogo.get_input()
        if not nuevo_nombre or nuevo_nombre.strip() == "" or nuevo_nombre.strip() == nombre: return

        if messagebox.askyesno("⚠️ Confirmar", f"¿Guardar cambios?\n\nAnterior: {nombre}\nNuevo: {nuevo_nombre.strip()}"):
            try:
                conexion = sqlite3.connect(self.ruta_db)
                cursor = conexion.cursor()
                cursor.execute("UPDATE productos SET nombre = ? WHERE codigo_barras = ?", (nuevo_nombre.strip(), codigo))
                conexion.commit()
                messagebox.showinfo("✅ Éxito", "Nombre actualizado.")
                if self.entry_buscador.get().strip(): self.buscar_producto()
                else: self.cargar_datos() 
            except Exception as e:
                messagebox.showerror("❌ Error", f"Fallo al actualizar:\n{e}")
            finally:
                if 'conexion' in locals(): conexion.close()

    def editar_precio(self):
        producto = self.obtener_seleccionado()
        if not producto: return
        codigo, nombre, precio_actual = str(producto[0]), producto[1], str(producto[4]).replace('$', '').strip()

        dialogo = ctk.CTkInputDialog(text=f"Producto: {nombre}\nPrecio actual: ${precio_actual}\nIngrese el NUEVO PRECIO ($):", title="💲 Editar Precio")
        nuevo_precio_str = dialogo.get_input()
        if not nuevo_precio_str or nuevo_precio_str.strip() == "": return

        try:
            nuevo_precio = float(nuevo_precio_str.replace(',', '.'))
            if nuevo_precio < 0: raise ValueError
            
            if messagebox.askyesno("⚠️ Confirmar", f"¿Guardar precio para {nombre}?\n\nNuevo Precio: ${nuevo_precio:.2f}"):
                conexion = sqlite3.connect(self.ruta_db)
                cursor = conexion.cursor()
                cursor.execute("UPDATE productos SET precio = ? WHERE codigo_barras = ?", (nuevo_precio, codigo))
                conexion.commit()
                messagebox.showinfo("✅ Éxito", "Precio actualizado.")
                if self.entry_buscador.get().strip(): self.buscar_producto()
                else: self.cargar_datos() 
        except ValueError:
            messagebox.showerror("❌ Error", "El precio ingresado no es válido.")
        finally:
            if 'conexion' in locals(): conexion.close()

    def obtener_seleccionado(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showwarning("⚠️ Atención", "Primero hacé clic en un producto de la tabla para seleccionarlo.")
            return None
        return self.tabla.item(seleccion[0])['values'] 

    def corregir_stock(self):
        producto = self.obtener_seleccionado()
        if not producto: return
        codigo, nombre = str(producto[0]), producto[1]

        dialogo = ctk.CTkInputDialog(text=f"Conteo físico. ¿Cuántas unidades hay REALMENTE de:\n{nombre}?", title="✏️ Corregir Stock")
        cantidad_str = dialogo.get_input()
        if not cantidad_str: return

        try:
            nuevo_stock = int(cantidad_str)
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            cursor.execute("UPDATE productos SET stock = ? WHERE codigo_barras = ?", (nuevo_stock, codigo))
            conexion.commit()
            messagebox.showinfo("✅ Éxito", f"El stock de {nombre} se corrigió a {nuevo_stock}.")
            if self.entry_buscador.get().strip(): self.buscar_producto()
            else: self.cargar_datos()
            self.entry_buscador.focus()
        except ValueError:
            messagebox.showerror("❌ Error", "Por favor ingresá un número entero.")
            self.entry_buscador.focus()
        finally:
            if 'conexion' in locals(): conexion.close()

if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("100x100")
    app.withdraw()
    v = VentanaStock(app)
    app.mainloop()
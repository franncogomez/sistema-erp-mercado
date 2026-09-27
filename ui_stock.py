import customtkinter as ctk
import tkinter.messagebox as messagebox
from tkinter import ttk
import sqlite3
import os
from tkinter import filedialog
import pandas as pd

class VentanaStock(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("📦 Gestión de Inventario")
        self.geometry("950x600") # Lo ensanché un poquito para que entren bien las marcas
        self.grab_set()
        self.ruta_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sistema_mercado.db")
        
        # ==========================================
        # 🟢 TÍTULO Y BUSCADOR (Escáner)
        # ==========================================
        self.lbl_titulo = ctk.CTkLabel(self, text="📦 Panel de Control de Stock", font=("Roboto", 24, "bold"))
        self.lbl_titulo.pack(pady=15)

        self.frame_buscador = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_buscador.pack(pady=(0, 10))

        self.lbl_buscar = ctk.CTkLabel(self.frame_buscador, text="🔍 Buscar / Escanear Código:", font=("Roboto", 14, "bold"))
        self.lbl_buscar.pack(side="left", padx=10)

        self.entry_buscador = ctk.CTkEntry(self.frame_buscador, width=250, placeholder_text="Pase el producto aquí...")
        self.entry_buscador.pack(side="left", padx=10)
        self.entry_buscador.focus() 
        
        self.entry_buscador.bind("<Return>", self.buscar_producto)
        
        self.btn_limpiar = ctk.CTkButton(self.frame_buscador, text="❌ Limpiar", width=80, fg_color="#C62828", hover_color="#8e1d1d", command=self.cargar_datos)
        self.btn_limpiar.pack(side="left", padx=10)

        # ==========================================
        # 🔵 MARCO DE ACCIONES
        # ==========================================
        self.frame_acciones = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_acciones.pack(pady=10)

        self.btn_ingreso = ctk.CTkButton(self.frame_acciones, text="➕ Llegó Mercadería", fg_color="#2FA572", hover_color="#237a54", height=40, font=("Roboto", 14, "bold"), command=self.sumar_stock)
        self.btn_ingreso.pack(side="left", padx=10)

        self.btn_corregir = ctk.CTkButton(self.frame_acciones, text="✏️ Corregir Stock", fg_color="#D97706", hover_color="#b36205", height=40, font=("Roboto", 14, "bold"), command=self.corregir_stock)
        self.btn_corregir.pack(side="left", padx=10)
        
        self.btn_editar = ctk.CTkButton(self.frame_acciones, text="⚙️ Editar Datos", fg_color="#1E88E5", hover_color="#1565C0", height=40, font=("Roboto", 14, "bold"), command=self.editar_producto)
        self.btn_editar.pack(side="left", padx=10)

        self.btn_actualizar = ctk.CTkButton(self.frame_acciones, text="🔄 Actualizar Tabla", height=40, font=("Roboto", 14), command=self.cargar_datos)
        self.btn_actualizar.pack(side="left", padx=10)

        self.btn_eliminar = ctk.CTkButton(self.frame_acciones, text="🗑️ Eliminar", fg_color="#C62828", hover_color="#8e1d1d", height=40, font=("Roboto", 14, "bold"), command=self.eliminar_producto)
        self.btn_eliminar.pack(side="left", padx=10)

        self.btn_importar = ctk.CTkButton(self.frame_acciones, text="📥 Inyectar Excel", fg_color="#4A148C", hover_color="#311B92", height=40, font=("Roboto", 14, "bold"), command=self.importar_excel)
        self.btn_importar.pack(side="left", padx=5)

        self.btn_aumento = ctk.CTkButton(self.frame_acciones, text="📈 Aumento %", fg_color="#D81B60", hover_color="#ad144d", height=40, font=("Roboto", 14, "bold"), command=self.aumento_masivo)
        self.btn_aumento.pack(side="left", padx=5)
        
        # ==========================================
        # 🟡 LA TABLA DE INVENTARIO (Treeview)
        # ==========================================
        self.frame_tabla = ctk.CTkFrame(self)
        self.frame_tabla.pack(padx=20, pady=10, fill="both", expand=True)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", rowheight=30, font=("Roboto", 12), background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b")
        style.configure("Treeview.Heading", font=("Roboto", 12, "bold"), background="#333333", foreground="white")
        style.map("Treeview", background=[('selected', '#1f538d')])

        # 🔧 Actualizado para mostrar Marca y Rubro
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

        self.tabla.pack(fill="both", expand=True, padx=5, pady=5)

        self.cargar_datos()

    # ==========================================
    # ⚙️ FUNCIONES DE LA BASE DE DATOS
    # ==========================================

    def aumento_masivo(self):
        dialogo = ctk.CTkInputDialog(text="Ingrese el porcentaje de aumento.\nEjemplo: para un 15%, escriba 15", title="📈 Aumento Masivo")
        porcentaje_str = dialogo.get_input()
        
        if not porcentaje_str: return

        try:
            porcentaje = float(porcentaje_str)
            if porcentaje <= 0:
                messagebox.showerror("❌ Error", "El porcentaje debe ser mayor a cero.")
                return

            mensaje = f"⚠️ ATENCIÓN: Va a aumentar el precio de TODOS los productos de la base de datos un {porcentaje}%.\n\nEsta acción no se puede deshacer de forma automática.\n¿Está completamente seguro?"
            confirmacion = messagebox.askyesno("🚨 Confirmar Remarcación", mensaje)
            
            if confirmacion:
                conexion = sqlite3.connect(self.ruta_db)
                cursor = conexion.cursor()
                multiplicador = 1 + (porcentaje / 100.0)
                cursor.execute("UPDATE productos SET precio = ROUND(precio * ?, 2)", (multiplicador,))
                conexion.commit()
                conexion.close()
                
                messagebox.showinfo("✅ Éxito", f"Se actualizaron los precios de toda la base de datos con un {porcentaje}% de aumento.")
                self.cargar_datos() 
                
        except ValueError:
            messagebox.showerror("❌ Error", "Por favor, ingrese solo números (ej: 10 o 15.5).")

    def importar_excel(self):
        archivo = filedialog.askopenfilename(
            title="Seleccionar lista del proveedor",
            filetypes=(("Archivos Excel", "*.xlsx *.xls"), ("Archivos CSV", "*.csv"))
        )
        
        if not archivo:
            return

        try:
            if archivo.endswith('.csv'):
                # 🔧 El encoding clave para no romper los nombres
                df = pd.read_csv(archivo, header=None, encoding='latin-1')
            else:
                df = pd.read_excel(archivo, header=None)
                
            header_row_idx = None
            for i, row in df.iterrows():
                row_str = ' '.join(str(val).lower() for val in row.values)
                if ('codigo' in row_str or 'ean' in row_str) and 'nombre' in row_str:
                    header_row_idx = i
                    break
            
            if header_row_idx is None:
                messagebox.showerror("Error de Formato", "No se encontraron las palabras 'Codigo' (o 'EAN') y 'Nombre' en la misma fila.")
                return
                
            df.columns = df.iloc[header_row_idx]
            df = df[header_row_idx + 1:]
            df.columns = [str(col).strip().lower() for col in df.columns]

            if 'ean' in df.columns and 'codigo' not in df.columns:
                df.rename(columns={'ean': 'codigo'}, inplace=True)

            # 1. Validación estricta de columnas obligatorias (Rojo)
            if 'codigo' not in df.columns or 'nombre' not in df.columns:
                messagebox.showerror(
                    "❌ Error de Columnas", 
                    "No se puede continuar.\n\nFalta la columna 'codigo' o la columna 'nombre' en su Excel. Por favor, revíselo y vuelva a intentar."
                )
                return

            # 2. Aviso amigable si falta el precio (Amarillo - No detiene la carga)
            if 'precio' not in df.columns:
                messagebox.showinfo(
                    "⚠️ Aviso sobre Precios", 
                    "Su Excel no tiene la columna 'precio'.\n\nEl sistema cargará los productos igual, pero les asignará un valor de $0 para que usted defina el precio de venta en la caja registradora."
                )

            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            
            nuevos = 0
            actualizados = 0
            sin_cambios = 0
            errores = 0 

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
                        errores += 1
                        continue

                    codigo = str(val_codigo).strip()
                    if codigo.endswith('.0'): 
                        codigo = codigo[:-2]
                        
                    if not codigo.isalnum() or len(codigo) < 2:
                        errores += 1
                        continue
                        
                    nombre = str(val_nombre).strip()
                    if len(nombre) < 2:
                        errores += 1
                        continue
                        
                    if val_precio < 0: 
                        errores += 1
                        continue

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
                            cursor.execute("""
                                UPDATE productos 
                                SET nombre = ?, precio = ?, marca = ?, cat1 = ?, cat2 = ?, cat3 = ? 
                                WHERE codigo_barras = ?
                            """, (nombre, precio_final, marca_final, cat1_final, cat2_final, cat3_final, codigo))
                            actualizados += 1
                        else:
                            sin_cambios += 1 
                    else:
                        cursor.execute("""
                            INSERT INTO productos (codigo_barras, nombre, precio, stock, marca, cat1, cat2, cat3) 
                            VALUES (?, ?, ?, 0, ?, ?, ?, ?)
                        """, (codigo, nombre, val_precio, marca, cat1, cat2, cat3))
                        nuevos += 1
                        
                except Exception as e:
                    errores += 1 

            conexion.commit()
            conexion.close()

            if nuevos == 0 and actualizados == 0 and sin_cambios == 0:
                messagebox.showwarning("Inyección Fallida", f"Se rechazaron todas las filas.\nErrores detectados: {errores}\n\nMotivos comunes:\n- Códigos con símbolos.\n- Precios con letras o negativos.\n- Filas incompletas.")
            else:
                mensaje = (
                    f"Procesamiento finalizado.\n\n"
                    f"Productos Nuevos: {nuevos}\n"
                    f"Precios/Datos Actualizados: {actualizados}\n"
                    f"Omitidos (Sin cambios): {sin_cambios}\n"
                )
                if errores > 0:
                    mensaje += f"\nSe descartaron {errores} filas por tener datos inválidos o basura."
                    
                messagebox.showinfo("Resumen de Inyección", mensaje)
            
            self.cargar_datos() 

        except Exception as e:
            messagebox.showerror("Error Crítico", f"Fallo al procesar el archivo:\n\nDetalle: {e}")

    def eliminar_producto(self):
        producto = self.obtener_seleccionado()
        if not producto: return
        
        codigo, nombre = str(producto[0]), producto[1]

        mensaje = f"⚠️ ATENCIÓN: Esta acción es irreversible.\n\n¿Está COMPLETAMENTE SEGURO de que desea eliminar el producto de la base de datos?\n\n🛒 {nombre}\n🔢 Código: {codigo}"
        
        confirmacion = messagebox.askyesno("🗑️ Eliminar Producto", mensaje)
        
        if confirmacion:
            try:
                conexion = sqlite3.connect(self.ruta_db)
                cursor = conexion.cursor()
                cursor.execute("DELETE FROM productos WHERE codigo_barras = ?", (codigo,))
                conexion.commit()
                messagebox.showinfo("✅ Éxito", f"El producto '{nombre}' fue eliminado del sistema.")
                self.cargar_datos() 
                
            except Exception as e:
                messagebox.showerror("❌ Error", f"No se pudo eliminar el producto:\n{e}")
            finally:
                if 'conexion' in locals():
                    conexion.close()
    
    def buscar_producto(self, event=None):
        codigo_buscado = self.entry_buscador.get().strip()
        
        if not codigo_buscado:
            self.cargar_datos()
            return

        for item in self.tabla.get_children():
            self.tabla.delete(item)
            
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            
            param = f"%{codigo_buscado}%"
            cursor.execute("""
                SELECT codigo_barras, nombre, marca, cat1, precio, stock 
                FROM productos 
                WHERE codigo_barras LIKE ? 
                OR nombre LIKE ?
                OR marca LIKE ?
                OR cat1 LIKE ?
                LIMIT 100
            """, (param, param, param, param))
            productos = cursor.fetchall()

            if productos:
                for p in productos:
                    # 🔧 Desempaquetado actualizado a las 6 columnas
                    codigo, nombre, marca, rubro, precio, stock = p
                    stock_mostrar = f"{stock} ⚠️" if stock <= 0 else str(stock)
                    precio_mostrar = f"${precio:.2f}"
                    
                    self.tabla.insert("", "end", values=(codigo, nombre, marca, rubro, precio_mostrar, stock_mostrar))
                    
                self.tabla.selection_set(self.tabla.get_children()[0])
            else:
                messagebox.showinfo("🔍 Búsqueda", f"No se encontraron productos con: {codigo_buscado}")
                self.cargar_datos()

        except Exception as e:
            messagebox.showerror("❌ Error", f"Error en la búsqueda:\n{e}")
        finally:
            if 'conexion' in locals():
                conexion.close()
            self.entry_buscador.delete(0, 'end')

    def cargar_datos(self):
        for item in self.tabla.get_children():
            self.tabla.delete(item)

        self.entry_buscador.delete(0, 'end')    
        
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            
            # 🛡️ PARCHE DE ESCALABILIDAD: LIMIT 100
            # Evita que la interfaz colapse al intentar renderizar 200.000 filas juntas.
            cursor.execute("SELECT codigo_barras, nombre, marca, cat1, precio, stock FROM productos ORDER BY nombre LIMIT 100")
            productos = cursor.fetchall()

            for p in productos:
                codigo, nombre, marca, rubro, precio, stock = p
                
                stock_mostrar = f"{stock} ⚠️" if stock <= 0 else str(stock)
                precio_mostrar = f"${precio:.2f}"
                
                self.tabla.insert("", "end", values=(codigo, nombre, marca, rubro, precio_mostrar, stock_mostrar))

        except Exception as e:
            messagebox.showerror("❌ Error", f"Error al cargar la base de datos:\n{e}")
        finally:
            if 'conexion' in locals():
                conexion.close()

    def editar_producto(self):
        producto = self.obtener_seleccionado()
        if not producto: return
        
        # 🔧 ATENCIÓN ACÁ: el precio ahora está en la posición [4] porque metimos marca y rubro
        codigo, nombre = str(producto[0]), producto[1]
        precio_actual_str = str(producto[4]).replace('$', '').strip()

        dialogo_nombre = ctk.CTkInputDialog(text=f"Editando producto:\n{codigo}\n\nNombre actual: {nombre}\nIngrese el NUEVO NOMBRE (o deje igual):", title="⚙️ Editar Nombre")
        nuevo_nombre = dialogo_nombre.get_input()
        
        if nuevo_nombre is None or nuevo_nombre.strip() == "":
            nuevo_nombre = nombre 

        dialogo_precio = ctk.CTkInputDialog(text=f"Precio actual: ${precio_actual_str}\nIngrese el NUEVO PRECIO ($):", title="⚙️ Editar Precio")
        nuevo_precio_str = dialogo_precio.get_input()
        
        if nuevo_precio_str is None or nuevo_precio_str.strip() == "":
            nuevo_precio_str = precio_actual_str

        try:
            nuevo_precio = float(nuevo_precio_str)
            
            mensaje_confirmacion = f"¿Guardar cambios?\n\nNombre: {nuevo_nombre}\nPrecio: ${nuevo_precio:.2f}"
            if messagebox.askyesno("⚠️ Confirmar Edición", mensaje_confirmacion):
                
                conexion = sqlite3.connect(self.ruta_db)
                cursor = conexion.cursor()
                cursor.execute("UPDATE productos SET nombre = ?, precio = ? WHERE codigo_barras = ?", (nuevo_nombre, nuevo_precio, codigo))
                conexion.commit()
                conexion.close()
                
                messagebox.showinfo("✅ Éxito", "Producto actualizado correctamente.")
                self.cargar_datos() 
                
        except ValueError:
            messagebox.showerror("❌ Error", "El precio ingresado no es válido. Debe ser un número.")

    def obtener_seleccionado(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showwarning("⚠️ Atención", "Primero hacé clic en un producto de la tabla para seleccionarlo.")
            return None
        item = self.tabla.item(seleccion[0])
        return item['values'] 

    def sumar_stock(self):
        producto = self.obtener_seleccionado()
        if not producto: return
        
        codigo, nombre = str(producto[0]), producto[1]

        dialogo = ctk.CTkInputDialog(text=f"¿Cuántas unidades nuevas llegaron de:\n{nombre}?", title="➕ Ingreso de Mercadería")
        cantidad_str = dialogo.get_input()

        if not cantidad_str: return

        try:
            cantidad = int(cantidad_str)
            if cantidad <= 0:
                messagebox.showerror("❌ Error", "La cantidad a sumar debe ser mayor a cero.")
                return

            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            cursor.execute("UPDATE productos SET stock = stock + ? WHERE codigo_barras = ?", (cantidad, codigo))
            conexion.commit()
            conexion.close()

            messagebox.showinfo("✅ Éxito", f"Se sumaron {cantidad} unidades a {nombre}.")
            self.cargar_datos()

        except ValueError:
            messagebox.showerror("❌ Error", "Por favor ingresá un número entero.")

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
            conexion.close()

            messagebox.showinfo("✅ Éxito", f"El stock de {nombre} se corrigió a {nuevo_stock}.")
            self.cargar_datos()

        except ValueError:
            messagebox.showerror("❌ Error", "Por favor ingresá un número entero.")

# ==========================================
# CÓDIGO DE PRUEBA INDIVIDUAL
# ==========================================
if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("100x100")
    app.withdraw()
    v = VentanaStock(app)
    app.mainloop()
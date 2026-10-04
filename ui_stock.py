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
        self.geometry("1050x600") # Lo ensanché a 1050 para que entren cómodos todos los botones
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
        # 🔵 MARCO DE ACCIONES (AHORA CON SCROLL HORIZONTAL)
        # ==========================================
        # 🪄 Acá está la magia: CTkScrollableFrame con orientation="horizontal"
        self.frame_acciones = ctk.CTkScrollableFrame(self, orientation="horizontal", height=65, fg_color="transparent")
        self.frame_acciones.pack(pady=10, padx=20, fill="x")

        # Todos tus botones adentro del scroll (sin cambiar sus funciones)
        self.btn_corregir = ctk.CTkButton(self.frame_acciones, text="✏️ Corregir Stock", fg_color="#D97706", hover_color="#b36205", height=40, font=("Roboto", 14, "bold"), command=self.corregir_stock)
        self.btn_corregir.pack(side="left", padx=5)
        
        self.btn_editar_nombre = ctk.CTkButton(self.frame_acciones, text="📝 Editar Nombre", fg_color="#1E88E5", hover_color="#1565C0", height=40, font=("Roboto", 14, "bold"), command=self.editar_nombre)
        self.btn_editar_nombre.pack(side="left", padx=5)

        self.btn_editar_precio = ctk.CTkButton(self.frame_acciones, text="💲 Editar Precio", fg_color="#43A047", hover_color="#2E7D32", height=40, font=("Roboto", 14, "bold"), command=self.editar_precio)
        self.btn_editar_precio.pack(side="left", padx=5)

        self.btn_nuevo_suelto = ctk.CTkButton(self.frame_acciones, text="➕ Nuevo Suelto", fg_color="#2FA572", hover_color="#237a54", height=40, font=("Roboto", 14, "bold"), command=self.crear_producto_suelto)
        self.btn_nuevo_suelto.pack(side="left", padx=5)

        self.btn_actualizar = ctk.CTkButton(self.frame_acciones, text="🔄 Actualizar", height=40, font=("Roboto", 14), command=self.cargar_datos)
        self.btn_actualizar.pack(side="left", padx=5)

        self.btn_eliminar = ctk.CTkButton(self.frame_acciones, text="🗑️ Eliminar", fg_color="#C62828", hover_color="#8e1d1d", height=40, font=("Roboto", 14, "bold"), command=self.eliminar_producto)
        self.btn_eliminar.pack(side="left", padx=5)

        self.btn_importar = ctk.CTkButton(self.frame_acciones, text="📥 Inyectar Excel", fg_color="#4A148C", hover_color="#311B92", height=40, font=("Roboto", 14, "bold"), command=self.importar_excel)
        self.btn_importar.pack(side="left", padx=5)

        # Tus botones nuevos del anotador ya integrados al scroll
        self.btn_add_lista = ctk.CTkButton(self.frame_acciones, text="🛒 A la Lista", fg_color="#F59E0B", hover_color="#D97706", height=40, font=("Roboto", 14, "bold"), command=self.añadir_a_lista)
        self.btn_add_lista.pack(side="left", padx=5)

        self.btn_ver_lista = ctk.CTkButton(self.frame_acciones, text="📝 Abrir Anotador", fg_color="#8E24AA", hover_color="#6A1B9A", height=40, font=("Roboto", 14, "bold"), command=self.abrir_anotador)
        self.btn_ver_lista.pack(side="left", padx=5)

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

        self.tabla.tag_configure("sin_stock", foreground="#ff5252")

        self.tabla.pack(fill="both", expand=True, padx=5, pady=5)

        self.cargar_datos()

    # ==========================================
    # ⚙️ FUNCIONES DE LA BASE DE DATOS
    # ==========================================

    def añadir_a_lista(self):
        import os
        from tkinter import messagebox
        
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showwarning("⚠️️ Atención", "Seleccioná uno o varios productos de la tabla (usá Ctrl + Clic para elegir varios).")
            return
        
        ruta_txt = os.path.join(os.path.dirname(self.ruta_db), "lista_compras.txt")
        agregados = 0
        
        try:
            with open(ruta_txt, "a", encoding="utf-8") as f:
                for item in seleccion:
                    valores = self.tabla.item(item)['values']
                    nombre = valores[1]
                    f.write(f"- {nombre}\n")
                    agregados += 1
                    
            messagebox.showinfo("✅ Listo", f"Se agregaron {agregados} productos al anotador.")
            self.entry_buscador.focus()
            
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al guardar: {e}")

    def abrir_anotador(self):
        import customtkinter as ctk
        import os
        from tkinter import messagebox
        
        ventana_notas = ctk.CTkToplevel(self)
        ventana_notas.title("📝 Anotador de Faltantes")
        ventana_notas.geometry("450x550")
        ventana_notas.grab_set()

        lbl = ctk.CTkLabel(ventana_notas, text="Lista de Compras / Pendientes", font=("Roboto", 18, "bold"))
        lbl.pack(pady=15)

        # La caja de texto editable
        caja_texto = ctk.CTkTextbox(ventana_notas, width=400, height=400, font=("Roboto", 16))
        caja_texto.pack(pady=5)

        ruta_txt = os.path.join(os.path.dirname(self.ruta_db), "lista_compras.txt")
        
        # Cargamos lo que ya estaba anotado
        if os.path.exists(ruta_txt):
            with open(ruta_txt, "r", encoding="utf-8") as f:
                caja_texto.insert("1.0", f.read())

        def guardar_notas():
            # Guardamos lo que el usuario editó o borró
            with open(ruta_txt, "w", encoding="utf-8") as f:
                f.write(caja_texto.get("1.0", "end-1c"))
                
            messagebox.showinfo("✅ Guardado", "El anotador se guardó con éxito.")
            ventana_notas.destroy()
            self.entry_buscador.focus()

        btn_guardar = ctk.CTkButton(ventana_notas, text="💾 Guardar Cambios", command=guardar_notas, fg_color="#2FA572", hover_color="#237a54", height=45, font=("Roboto", 14, "bold"))
        btn_guardar.pack(pady=15)

    def crear_producto_suelto(self):
        # 🚀 Función exclusiva para crear fiambre, verdura y panadería rapidísimo
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
            if 'conexion' in locals():
                conexion.close()

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

            for palabra in palabras:
                query += " AND (codigo_barras LIKE ? OR nombre LIKE ? OR marca LIKE ? OR cat1 LIKE ?)"
                param = f"%{palabra}%"
                parametros.extend([param, param, param, param])
                
            query += " ORDER BY (precio = 0 AND LENGTH(codigo_barras) <= 4) DESC, nombre ASC LIMIT 100"
            
            cursor.execute(query, parametros)
            productos = cursor.fetchall()

            if productos:
                for p in productos:
                    codigo, nombre, marca, rubro, precio, stock = p
                    stock_mostrar = f"{stock} ⚠" if stock <= 0 else str(stock)
                    etiqueta = ("sin_stock",) if stock <= 0 else ()
                    self.tabla.insert("", "end", values=(codigo, nombre, marca, rubro, f"${precio:.2f}", stock_mostrar), tags=etiqueta)
                    
                self.tabla.selection_set(self.tabla.get_children()[0])
            else:
                messagebox.showinfo("🔍 Búsqueda", f"No se encontraron productos con: {codigo_buscado}")
                self.cargar_datos()

        except Exception as e:
            messagebox.showerror("❌ Error", f"Error en la búsqueda:\n{e}")
        finally:
            if 'conexion' in locals(): conexion.close()
            self.entry_buscador.focus()

    def cargar_datos(self):
        for item in self.tabla.get_children(): self.tabla.delete(item)
        self.entry_buscador.delete(0, 'end')    
        
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            
            cursor.execute("SELECT codigo_barras, nombre, marca, cat1, precio, stock FROM productos ORDER BY (precio = 0 AND LENGTH(codigo_barras) <= 4) DESC, nombre ASC LIMIT 100")
            productos = cursor.fetchall()

            for p in productos:
                codigo, nombre, marca, rubro, precio, stock = p
                if len(str(codigo)) <= 4:
                    stock_mostrar = "Pesable"
                    etiqueta = () 
                else:
                    stock_mostrar = f"{stock} ⚠️" if stock <= 0 else str(stock)
                    etiqueta = ("sin_stock",) if stock <= 0 else ()
                self.tabla.insert("", "end", values=(codigo, nombre, marca, rubro, f"${precio:.2f}", stock_mostrar), tags=etiqueta)

        except Exception as e:
            messagebox.showerror("❌ Error", f"Error al cargar la base de datos:\n{e}")
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
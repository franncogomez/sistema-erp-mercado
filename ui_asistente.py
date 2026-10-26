import customtkinter as ctk
from tkinter import ttk, messagebox
import sqlite3
import os
import sys
import threading
from google import genai
from google.genai import types

class VentanaAsistente(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("🧠 IA Analítica de Stock")
        self.geometry("900x600")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        self.chat_session = None
        
        # Fórmula de ruta dinámica (igual a main.py)
        if getattr(sys, 'frozen', False):
            directorio_base = os.path.dirname(sys.executable)
        else:
            directorio_base = os.path.dirname(os.path.abspath(__file__))
        self.ruta_db = os.path.join(directorio_base, "sistema_mercado.db")

        # ==========================================
        # 🎨 INTERFAZ GRÁFICA
        # ==========================================
        self.lbl_titulo = ctk.CTkLabel(self, text="Buscador Inteligente de Inventario", font=("Roboto", 20, "bold"), text_color="#1E88E5")
        self.lbl_titulo.pack(pady=(15, 5))

        self.lbl_sub = ctk.CTkLabel(self, text="Ejemplo: 'Mostrame los últimos 20 productos que actualicé' o '¿Qué agregué hoy?'", font=("Roboto", 13))
        self.lbl_sub.pack(pady=(0, 10))

        # Buscador y Botón
        self.frame_input = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_input.pack(fill="x", padx=20, pady=5)

        self.entry_pregunta = ctk.CTkEntry(self.frame_input, height=45, font=("Roboto", 15), placeholder_text="Escribí tu consulta en lenguaje natural...")
        self.entry_pregunta.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_pregunta.bind("<Return>", lambda event: self.consultar_ia())

        self.btn_buscar = ctk.CTkButton(self.frame_input, text="✨ Analizar", width=120, height=45, font=("Roboto", 16, "bold"), fg_color="#2FA572", hover_color="#238259", command=self.consultar_ia)
        self.btn_buscar.pack(side="right")

        self.lbl_estado = ctk.CTkLabel(self, text="", font=("Roboto", 12, "italic"), text_color="gray")
        self.lbl_estado.pack(pady=5)

        # ==========================================
        # 📊 TABLA DE RESULTADOS DE LA IA
        # ==========================================
        self.frame_tabla = ctk.CTkFrame(self)
        self.frame_tabla.pack(padx=20, pady=10, fill="both", expand=True)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", rowheight=30, font=("Roboto", 12), background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b")
        style.configure("Treeview.Heading", font=("Roboto", 12, "bold"), background="#333333", foreground="white")

        columnas = ("codigo", "nombre", "precio", "stock", "marca", "fecha")
        self.tabla = ttk.Treeview(self.frame_tabla, columns=columnas, show="headings")

        self.tabla.heading("codigo", text="Código")
        self.tabla.heading("nombre", text="Producto")
        self.tabla.heading("precio", text="Precio ($)")
        self.tabla.heading("stock", text="Stock")
        self.tabla.heading("marca", text="Marca")
        self.tabla.heading("fecha", text="Últ. Modificación")

        self.tabla.column("codigo", width=100, anchor="center")
        self.tabla.column("nombre", width=250, anchor="w")
        self.tabla.column("precio", width=80, anchor="center")
        self.tabla.column("stock", width=60, anchor="center")
        self.tabla.column("marca", width=100, anchor="w")
        self.tabla.column("fecha", width=140, anchor="center")

        self.scrollbar = ttk.Scrollbar(self.frame_tabla, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=self.scrollbar.set)
        
        self.tabla.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=5)
        self.scrollbar.pack(side="right", fill="y", padx=(0, 5), pady=5)

        self.configurar_ia()

    # ==========================================
    # ⚙️ CONFIGURACIÓN DEL TRADUCTOR SQL (GEMINI)
    # ==========================================
    def configurar_ia(self):
        # 🔑 ACÁ PEGÁS TU CLAVE COPIADA
        api_key = "AQ.Ab8RN6I0fGCvgC_8DoCJitsQRK5_uSxJe9CIJJQonS20hGXklA"

        if not api_key or api_key == "TU_CLAVE_GEMINI_AQUI":
            self.lbl_estado.configure(text="⚠️ Error: Falta la API Key en el código.", text_color="#EF4444")
            return

        instrucciones_sql = """
        Sos un traductor experto y robótico que convierte preguntas en lenguaje natural a consultas SQL para SQLite.
        Esquema de la tabla 'productos':
        - codigo_barras (TEXT)
        - nombre (TEXT)
        - precio (REAL)
        - stock (INTEGER)
        - marca (TEXT)
        - fecha_creacion (TEXT) - Formato 'YYYY-MM-DD HH:MM:SS'
        - fecha_modificacion (TEXT) - Formato 'YYYY-MM-DD HH:MM:SS'

        REGLAS ABSOLUTAS E INQUEBRANTABLES:
        1. Respondé ÚNICAMENTE con la consulta SQL cruda. NADA de texto, NADA de explicaciones.
        2. NO uses formato markdown (prohibido usar ```sql al principio o al final).
        3. SOLO sentencias SELECT. Prohibido usar DROP, DELETE, UPDATE, INSERT.
        4. Si te piden "últimos actualizados", usa ORDER BY fecha_modificacion DESC.
        5. Si te piden "nuevos agregados", usa ORDER BY fecha_creacion DESC.
        6. Seleccioná siempre estas 6 columnas EXACTAS en este orden: codigo_barras, nombre, precio, stock, marca, fecha_modificacion.
        7. Agregá siempre LIMIT 100 al final para no saturar el sistema.
        """

        try:
            self.client = genai.Client(api_key=api_key)
            
            # 🛑 Eliminamos el buscador problemático y clavamos el modelo que a vos te funcionó.
            modelo_elegido = "gemini-3.5-flash" 
            
            config = types.GenerateContentConfig(
                system_instruction=instrucciones_sql,
                temperature=0.0 # Temperatura cero: Nada de creatividad, solo lógica estricta
            )
            
            self.chat_session = self.client.chats.create(model=modelo_elegido, config=config)
        except Exception as err:
            # Guardamos el error en texto puro para evitar el fallo de la variable
            mensaje_error = str(err)
            self.lbl_estado.configure(text=f"⚠️ Falla al inicializar IA: {mensaje_error}", text_color="#EF4444")

    # ==========================================
    # 🧠 PROCESAMIENTO DE LA PREGUNTA
    # ==========================================
    def consultar_ia(self):
        pregunta = self.entry_pregunta.get().strip()
        if not pregunta: return

        if not self.chat_session:
            messagebox.showwarning("Atención", "La IA no se pudo conectar.")
            return

        self.btn_buscar.configure(text="Pensando...", state="disabled")
        self.entry_pregunta.configure(state="disabled")
        self.lbl_estado.configure(text="🤖 La IA está traduciendo tu consulta...", text_color="#F59E0B")

        threading.Thread(target=self.obtener_sql_ia, args=(pregunta,), daemon=True).start()

    def obtener_sql_ia(self, pregunta):
        try:
            respuesta = self.chat_session.send_message(pregunta)
            sql_crudo = respuesta.text.strip()
            sql_limpio = sql_crudo.replace("```sql", "").replace("```", "").strip()
            
            self.after(0, lambda: self.ejecutar_y_mostrar(sql_limpio))
        except Exception as err:
            # 🛠️ BUG 
            mensaje_error = str(err)
            self.after(0, lambda e_msg=mensaje_error: self.restaurar_ui(f"❌ Error de IA: {e_msg}", "#EF4444"))

    # ==========================================
    # 💾 EJECUCIÓN DEL SQL Y TABLA
    # ==========================================
    def ejecutar_y_mostrar(self, query_sql):
        # 🛡️ CORTAFUEGOS DE SEGURIDAD (Por si la IA intenta borrar algo)
        if not query_sql.upper().startswith("SELECT"):
            self.restaurar_ui("❌ Alerta de Seguridad: La IA intentó generar una consulta no permitida.", "#EF4444")
            return

        # Limpiamos la tabla
        for item in self.tabla.get_children():
            self.tabla.delete(item)
            
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            cursor.execute(query_sql)
            resultados = cursor.fetchall()

            for fila in resultados:
                # Formateamos el precio para que quede lindo
                precio_f = f"${fila[2]:.2f}" if fila[2] is not None else "$0.00"
                
                # Insertamos (código, nombre, precio, stock, marca, fecha)
                self.tabla.insert("", "end", values=(fila[0], fila[1], precio_f, fila[3], fila[4], fila[5]))
                
            self.restaurar_ui(f"✅ ¡Listo! Se encontraron {len(resultados)} resultados. (Consulta ejecutada internamente)", "#2FA572")

        except sqlite3.Error as e:
            self.restaurar_ui(f"⚠️ La IA generó un código que la base de datos no entendió: {e}", "#EF4444")
        finally:
            if 'conexion' in locals(): conexion.close()

    def restaurar_ui(self, mensaje_estado, color):
        self.lbl_estado.configure(text=mensaje_estado, text_color=color)
        self.btn_buscar.configure(text="✨ Analizar", state="normal")
        self.entry_pregunta.configure(state="normal")
        self.entry_pregunta.focus()
        self.entry_pregunta.select_range(0, 'end')

if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("100x100")
    app.withdraw()
    v = VentanaAsistente(app)
    app.mainloop()
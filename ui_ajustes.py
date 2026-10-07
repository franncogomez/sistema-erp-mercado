import customtkinter as ctk
import sqlite3
import os
import datetime
import threading
import winreg
import subprocess
from tkinter import ttk, messagebox
from supabase import create_client
from dotenv import load_dotenv
from rutas import RUTA_DB

class VentanaAjustes(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("⚙️ Configuración del Local y Usuarios")
        self.geometry("550x650") 
        self.resizable(False, False)
        self.grab_set()
        
        self.ruta_db = RUTA_DB

        lbl_titulo = ctk.CTkLabel(self, text="Ajustes del Negocio", font=("Roboto", 20, "bold"))
        lbl_titulo.pack(pady=(15, 5))

        self.tabview = ctk.CTkTabview(self, width=500, height=530)
        self.tabview.pack(padx=20, pady=5, fill="both", expand=True)

        tab_interno = "🧾 Ticket Interno"
        tab_fiscal = "🏛️ ARCA (Fiscal)"
        tab_usuarios = "👥 Usuarios"

        self.tabview.add(tab_interno)
        self.tabview.add(tab_fiscal)
        self.tabview.add(tab_usuarios)

        fuente_lbl = ("Roboto", 13, "bold")
        fuente_entry = ("Roboto", 14)

        # ==========================================
        # PESTAÑA 1: TICKET INTERNO
        # ==========================================
        ctk.CTkLabel(self.tabview.tab(tab_interno), text="Nombre del Local / Fantasía:", font=fuente_lbl).pack(anchor="w", padx=20, pady=(10,0))
        self.entry_fantasia = ctk.CTkEntry(self.tabview.tab(tab_interno), font=fuente_entry, width=420)
        self.entry_fantasia.pack(pady=5)

        ctk.CTkLabel(self.tabview.tab(tab_interno), text="Dirección Comercial:", font=fuente_lbl).pack(anchor="w", padx=20)
        self.entry_direccion = ctk.CTkEntry(self.tabview.tab(tab_interno), font=fuente_entry, width=420)
        self.entry_direccion.pack(pady=5)

        ctk.CTkLabel(self.tabview.tab(tab_interno), text="Teléfono / WhatsApp:", font=fuente_lbl).pack(anchor="w", padx=20)
        self.entry_telefono = ctk.CTkEntry(self.tabview.tab(tab_interno), font=fuente_entry, width=420)
        self.entry_telefono.pack(pady=5)

        ctk.CTkLabel(self.tabview.tab(tab_interno), text="Instagram (Ej: @milocal):", font=fuente_lbl).pack(anchor="w", padx=20)
        self.entry_instagram = ctk.CTkEntry(self.tabview.tab(tab_interno), font=fuente_entry, width=420)
        self.entry_instagram.pack(pady=5)

        self.btn_guardar_local = ctk.CTkButton(self.tabview.tab(tab_interno), text="💾 Guardar Ticket", fg_color="#2FA572", hover_color="#238259", height=45, font=("Roboto", 14, "bold"), command=self.guardar_datos_local)
        self.btn_guardar_local.pack(pady=20)

        # ==========================================
        # PESTAÑA 2: ARCA FISCAL
        # ==========================================
        ctk.CTkLabel(self.tabview.tab(tab_fiscal), text="Razón Social (Nombre legal):", font=fuente_lbl).pack(anchor="w", padx=20, pady=(10,0))
        self.entry_razon = ctk.CTkEntry(self.tabview.tab(tab_fiscal), font=fuente_entry, width=420)
        self.entry_razon.pack(pady=5)

        ctk.CTkLabel(self.tabview.tab(tab_fiscal), text="CUIT (11 números, sin guiones):", font=fuente_lbl).pack(anchor="w", padx=20)
        self.entry_cuit = ctk.CTkEntry(self.tabview.tab(tab_fiscal), font=fuente_entry, width=420)
        self.entry_cuit.pack(pady=5)

        ctk.CTkLabel(self.tabview.tab(tab_fiscal), text="Condición frente al IVA:", font=fuente_lbl).pack(anchor="w", padx=20)
        self.combo_iva = ctk.CTkComboBox(self.tabview.tab(tab_fiscal), values=["Monotributista", "Responsable Inscripto", "Exento"], font=fuente_entry, width=420)
        self.combo_iva.pack(pady=5)

        ctk.CTkLabel(self.tabview.tab(tab_fiscal), text="N° Ingresos Brutos (o 'Exento'):", font=fuente_lbl).pack(anchor="w", padx=20)
        self.entry_iibb = ctk.CTkEntry(self.tabview.tab(tab_fiscal), font=fuente_entry, width=420)
        self.entry_iibb.pack(pady=5)

        ctk.CTkLabel(self.tabview.tab(tab_fiscal), text="Inicio de Actividades (DD/MM/AAAA):", font=fuente_lbl).pack(anchor="w", padx=20)
        self.entry_inicio = ctk.CTkEntry(self.tabview.tab(tab_fiscal), font=fuente_entry, width=420, placeholder_text="Ej: 01/05/2020")
        self.entry_inicio.pack(pady=5)

        self.btn_guardar_arca = ctk.CTkButton(self.tabview.tab(tab_fiscal), text="💾 Guardar Fiscal", fg_color="#1E88E5", hover_color="#1565C0", height=45, font=("Roboto", 14, "bold"), command=self.guardar_datos_local)
        self.btn_guardar_arca.pack(pady=20)

        # ==========================================
        # PESTAÑA 3: GESTIÓN DE USUARIOS 👥
        # ==========================================
        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Roboto", 11, "bold"))
        style.configure("Treeview", font=("Roboto", 12), rowheight=28)
        
        self.tabla_usuarios = ttk.Treeview(self.tabview.tab(tab_usuarios), columns=("id", "nombre", "rol", "pin"), show="headings", height=5)
        self.tabla_usuarios.heading("id", text="ID")
        self.tabla_usuarios.heading("nombre", text="Nombre / Alias")
        self.tabla_usuarios.heading("rol", text="Nivel de Acceso")
        self.tabla_usuarios.heading("pin", text="PIN")
        
        self.tabla_usuarios.column("id", width=30, anchor="center")
        self.tabla_usuarios.column("nombre", width=180, anchor="w")
        self.tabla_usuarios.column("rol", width=130, anchor="center")
        self.tabla_usuarios.column("pin", width=60, anchor="center")
        self.tabla_usuarios.pack(pady=10, fill="x", padx=10)
        self.tabla_usuarios.bind("<ButtonRelease-1>", self.seleccionar_usuario)

        frame_form = ctk.CTkFrame(self.tabview.tab(tab_usuarios), fg_color="transparent")
        frame_form.pack(pady=5, fill="x", padx=10)

        ctk.CTkLabel(frame_form, text="Nombre:", font=fuente_lbl).grid(row=0, column=0, sticky="w", pady=5)
        self.entry_usu_nombre = ctk.CTkEntry(frame_form, width=180)
        self.entry_usu_nombre.grid(row=0, column=1, padx=10)

        ctk.CTkLabel(frame_form, text="PIN (4 núm):", font=fuente_lbl).grid(row=1, column=0, sticky="w", pady=5)
        self.entry_usu_pin = ctk.CTkEntry(frame_form, width=180)
        self.entry_usu_pin.grid(row=1, column=1, padx=10)

        ctk.CTkLabel(frame_form, text="Rol:", font=fuente_lbl).grid(row=2, column=0, sticky="w", pady=5)
        self.combo_usu_rol = ctk.CTkComboBox(frame_form, values=["CAJERO", "ADMINISTRADOR"], width=180, state="readonly")
        self.combo_usu_rol.grid(row=2, column=1, padx=10)

        frame_btns = ctk.CTkFrame(self.tabview.tab(tab_usuarios), fg_color="transparent")
        frame_btns.pack(pady=15)

        ctk.CTkButton(frame_btns, text="💾 Guardar / Nuevo", fg_color="#2FA572", hover_color="#238259", width=140, command=self.guardar_usuario).pack(side="left", padx=5)
        ctk.CTkButton(frame_btns, text="🗑️ Eliminar", fg_color="#D32F2F", hover_color="#B71C1C", width=100, command=self.eliminar_usuario).pack(side="left", padx=5)
        ctk.CTkButton(frame_btns, text="🧹 Limpiar", fg_color="#546E7A", hover_color="#37474F", width=100, command=self.limpiar_form_usuarios).pack(side="left", padx=5)

        self.id_usuario_editando = None

        self.parche_migracion_master()
        self.cargar_datos_local()
        self.cargar_usuarios()

    # ==========================================
    # ⚙️ LÓGICA DE USUARIOS Y SINCRONIZACIÓN
    # ==========================================
    def parche_migracion_master(self):
        """Si existe un ADMINISTRADOR pero ningún MASTER, convierte al primero en MASTER automáticamente."""
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            cursor.execute("SELECT COUNT(*) FROM usuarios WHERE rol = 'MASTER'")
            if cursor.fetchone()[0] == 0:
                cursor.execute("UPDATE usuarios SET rol = 'MASTER' WHERE id_usuario = (SELECT MIN(id_usuario) FROM usuarios WHERE rol = 'ADMINISTRADOR')")
                conexion.commit()
        except Exception: pass
        finally:
            if 'conexion' in locals(): conexion.close()

    def cargar_usuarios(self):
        for item in self.tabla_usuarios.get_children(): self.tabla_usuarios.delete(item)
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            # Ordenar para que el MASTER siempre quede arriba
            cursor.execute("SELECT id_usuario, nombre, rol, pin FROM usuarios ORDER BY CASE WHEN rol='MASTER' THEN 1 WHEN rol='ADMINISTRADOR' THEN 2 ELSE 3 END")
            for u in cursor.fetchall():
                self.tabla_usuarios.insert("", "end", values=u)
            conexion.close()
        except: pass

    def seleccionar_usuario(self, event):
        seleccion = self.tabla_usuarios.selection()
        if not seleccion: return
        valores = self.tabla_usuarios.item(seleccion[0])['values']
        
        self.id_usuario_editando = valores[0]
        self.entry_usu_nombre.delete(0, 'end')
        self.entry_usu_nombre.insert(0, valores[1])
        
        rol_seleccionado = valores[2]
        
        # 🛠️ VULNERABILIDAD CORREGIDA: Destrabamos el componente ANTES de darle órdenes
        self.combo_usu_rol.configure(state="normal")
        
        if rol_seleccionado == 'MASTER':
            self.combo_usu_rol.configure(values=["MASTER"])
            self.combo_usu_rol.set("MASTER")
            self.combo_usu_rol.configure(state="disabled") # Lo volvemos a bloquear fuerte
        else:
            self.combo_usu_rol.configure(values=["CAJERO", "ADMINISTRADOR"])
            self.combo_usu_rol.set(rol_seleccionado)
            self.combo_usu_rol.configure(state="readonly") # Lo dejamos en solo lectura
        
        self.entry_usu_pin.delete(0, 'end')
        
        pin_texto = str(valores[3])
        if len(pin_texto) < 4 and pin_texto.isdigit():
            pin_texto = pin_texto.zfill(4)
            
        self.entry_usu_pin.insert(0, pin_texto)

    def limpiar_form_usuarios(self):
        self.id_usuario_editando = None
        self.entry_usu_nombre.delete(0, 'end')
        self.entry_usu_pin.delete(0, 'end')
        
        # 🛠️ VULNERABILIDAD CORREGIDA: También lo destrabamos al apretar el botón "Limpiar"
        self.combo_usu_rol.configure(state="normal")
        self.combo_usu_rol.configure(values=["CAJERO", "ADMINISTRADOR"])
        self.combo_usu_rol.set("CAJERO")
        self.combo_usu_rol.configure(state="readonly")

    def sincronizar_pin_nube(self, nuevo_pin):
        """Envía el PIN del MASTER a Supabase en segundo plano."""
        def tarea():
            try:
                try:
                    registry = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
                    key = winreg.OpenKey(registry, r"SOFTWARE\Microsoft\Cryptography")
                    id_pc, _ = winreg.QueryValueEx(key, "MachineGuid")
                    winreg.CloseKey(key)
                except:
                    id_pc = subprocess.check_output('wmic csproduct get uuid').decode().split('\n')[1].strip()

                ruta_base = os.path.dirname(self.ruta_db)
                load_dotenv(os.path.join(ruta_base, ".env"))
                url = os.getenv("SUPABASE_URL")
                llave = os.getenv("SUPABASE_KEY")

                if url and llave:
                    cliente = create_client(url, llave)
                    # Guarda el PIN del Master en la columna de la base de datos de Franco
                    cliente.table("clientes").update({"pin_admin": nuevo_pin}).eq("id_hardware", id_pc).execute()
                    print("✅ PIN MASTER resguardado en la nube exitosamente.")
            except Exception as e:
                print(f"⚠️ Aviso: No se pudo respaldar el PIN en la nube: {e}")

        threading.Thread(target=tarea, daemon=True).start()

    def guardar_usuario(self):
        nombre = self.entry_usu_nombre.get().strip().upper()
        pin = self.entry_usu_pin.get().strip()
        rol = self.combo_usu_rol.get()

        if not nombre or not pin:
            messagebox.showwarning("Atención", "El nombre y el PIN son obligatorios.")
            return
        if not pin.isdigit() or len(pin) != 4:
            messagebox.showerror("Error", "El PIN debe tener exactamente 4 números.")
            return

        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()

            if self.id_usuario_editando:
                cursor.execute("UPDATE usuarios SET nombre=?, pin=?, rol=? WHERE id_usuario=?", (nombre, pin, rol, self.id_usuario_editando))
                mensaje = "Usuario actualizado."
            else:
                cursor.execute("SELECT id_usuario FROM usuarios WHERE nombre=?", (nombre,))
                if cursor.fetchone():
                    messagebox.showerror("Error", "El nombre de usuario ya existe.")
                    conexion.close()
                    return
                cursor.execute("INSERT INTO usuarios (nombre, pin, rol) VALUES (?, ?, ?)", (nombre, pin, rol))
                mensaje = "Usuario creado."

            conexion.commit()
            conexion.close()
            
            # ☁️ MAGIA: Si el rol es MASTER, enviamos la clave a tu panel de Supabase
            if rol == "MASTER":
                self.sincronizar_pin_nube(pin)

            messagebox.showinfo("Éxito", mensaje)
            self.limpiar_form_usuarios()
            self.cargar_usuarios()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def eliminar_usuario(self):
        if not self.id_usuario_editando:
            messagebox.showwarning("Atención", "Seleccione un usuario de la tabla para eliminar.")
            return
            
        nombre = self.entry_usu_nombre.get()
        if messagebox.askyesno("Confirmar", f"¿Eliminar definitivamente el usuario '{nombre}'?"):
            try:
                conexion = sqlite3.connect(self.ruta_db)
                cursor = conexion.cursor()
                
                # 🛡️ Blindaje anti-bloqueo total
                cursor.execute("SELECT rol FROM usuarios WHERE id_usuario=?", (self.id_usuario_editando,))
                rol_a_borrar = cursor.fetchone()[0]
                
                if rol_a_borrar == "MASTER":
                    messagebox.showerror("Prohibido", "No puede eliminar al usuario MASTER. Es la cuenta principal del dueño del sistema.")
                    conexion.close()
                    return

                cursor.execute("DELETE FROM usuarios WHERE id_usuario=?", (self.id_usuario_editando,))
                conexion.commit()
                conexion.close()
                messagebox.showinfo("Éxito", "Usuario eliminado.")
                self.limpiar_form_usuarios()
                self.cargar_usuarios()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    # ==========================================
    # ⚙️ LÓGICA DEL LOCAL
    # ==========================================
    def cargar_datos_local(self):
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            cursor.execute("SELECT razon_social, nombre_fantasia, cuit, direccion, telefono, instagram, condicion_iva, iibb, inicio_actividades FROM config_local WHERE id = 1")
            datos = cursor.fetchone()
            
            if datos:
                self.entry_razon.insert(0, str(datos[0]) if datos[0] else "")
                self.entry_fantasia.insert(0, str(datos[1]) if datos[1] else "")
                self.entry_cuit.insert(0, str(datos[2]) if datos[2] else "")
                self.entry_direccion.insert(0, str(datos[3]) if datos[3] else "")
                self.entry_telefono.insert(0, str(datos[4]) if datos[4] else "")
                self.entry_instagram.insert(0, str(datos[5]) if datos[5] else "")
                self.combo_iva.set(str(datos[6]) if datos[6] else "Monotributista")
                self.entry_iibb.insert(0, str(datos[7]) if datos[7] else "")
                self.entry_inicio.insert(0, str(datos[8]) if datos[8] else "")
        except Exception as e:
            pass
        finally:
            if 'conexion' in locals(): conexion.close()

    def guardar_datos_local(self):
        fantasia = self.entry_fantasia.get().strip()
        razon = self.entry_razon.get().strip()
        cuit = self.entry_cuit.get().strip().replace("-", "").replace(" ", "")
        direccion = self.entry_direccion.get().strip()
        telefono = self.entry_telefono.get().strip()
        instagram = self.entry_instagram.get().strip()
        iva = self.combo_iva.get()
        iibb = self.entry_iibb.get().strip().replace("-", "").replace(" ", "").upper()
        inicio_act = self.entry_inicio.get().strip()

        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE config_local 
                SET razon_social = ?, nombre_fantasia = ?, cuit = ?, direccion = ?, 
                    telefono = ?, instagram = ?, condicion_iva = ?, iibb = ?, inicio_actividades = ?
                WHERE id = 1
            """, (razon, fantasia, cuit, direccion, telefono, instagram, iva, iibb, inicio_act))
            
            conexion.commit()
            messagebox.showinfo("✅ Guardado", "Ajustes del local actualizados correctamente.")
        except Exception as e:
            messagebox.showerror("❌ Error", str(e))
        finally:
            if 'conexion' in locals(): conexion.close()

if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("100x100")
    app.withdraw()
    v = VentanaAjustes(app)
    app.mainloop()
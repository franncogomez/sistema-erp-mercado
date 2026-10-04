import customtkinter as ctk
import sqlite3
import os
from tkinter import messagebox

class VentanaAjustes(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("⚙️ Configuración del Local")
        self.geometry("500x550")
        self.resizable(False, False)
        self.grab_set()
        
        self.ruta_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sistema_mercado.db")

        lbl_titulo = ctk.CTkLabel(self, text="Ajustes del Negocio", font=("Roboto", 20, "bold"))
        lbl_titulo.pack(pady=(15, 5))

        self.tabview = ctk.CTkTabview(self, width=450, height=380)
        self.tabview.pack(padx=20, pady=5, fill="both", expand=True)

        # Definimos los nombres de las pestañas en variables para evitar errores con los emojis
        tab_interno = "🧾 Ticket Interno"
        tab_fiscal = "🏛️ ARCA (Fiscal)"

        self.tabview.add(tab_interno)
        self.tabview.add(tab_fiscal)

        fuente_lbl = ("Roboto", 13, "bold")
        fuente_entry = ("Roboto", 14)

        # ==========================================
        # PESTAÑA 1: TICKET INTERNO (Básico)
        # ==========================================
        ctk.CTkLabel(self.tabview.tab(tab_interno), text="Datos para el ticket de control diario", text_color="#2FA572", font=("Roboto", 12, "italic")).pack(pady=(5, 10))

        ctk.CTkLabel(self.tabview.tab(tab_interno), text="Nombre del Local / Fantasía:", font=fuente_lbl).pack(anchor="w", padx=20)
        self.entry_fantasia = ctk.CTkEntry(self.tabview.tab(tab_interno), font=fuente_entry, width=380)
        self.entry_fantasia.pack(pady=(0, 10))

        ctk.CTkLabel(self.tabview.tab(tab_interno), text="Dirección Comercial:", font=fuente_lbl).pack(anchor="w", padx=20)
        self.entry_direccion = ctk.CTkEntry(self.tabview.tab(tab_interno), font=fuente_entry, width=380)
        self.entry_direccion.pack(pady=(0, 10))

        ctk.CTkLabel(self.tabview.tab(tab_interno), text="Teléfono / WhatsApp:", font=fuente_lbl).pack(anchor="w", padx=20)
        self.entry_telefono = ctk.CTkEntry(self.tabview.tab(tab_interno), font=fuente_entry, width=380)
        self.entry_telefono.pack(pady=(0, 10))

        ctk.CTkLabel(self.tabview.tab(tab_interno), text="Instagram (Ej: @milocal):", font=fuente_lbl).pack(anchor="w", padx=20)
        self.entry_instagram = ctk.CTkEntry(self.tabview.tab(tab_interno), font=fuente_entry, width=380)
        self.entry_instagram.pack(pady=(0, 10))

        # ==========================================
        # PESTAÑA 2: ARCA FISCAL (Avanzado)
        # ==========================================
        ctk.CTkLabel(self.tabview.tab(tab_fiscal), text="Completar solo si va a emitir Facturas Electrónicas", text_color="#1E88E5", font=("Roboto", 12, "italic")).pack(pady=(5, 10))

        # Acá estaba el error, ahora usa la variable tab_fiscal
        ctk.CTkLabel(self.tabview.tab(tab_fiscal), text="Razón Social (Nombre legal):", font=fuente_lbl).pack(anchor="w", padx=20)
        self.entry_razon = ctk.CTkEntry(self.tabview.tab(tab_fiscal), font=fuente_entry, width=380)
        self.entry_razon.pack(pady=(0, 5))

        ctk.CTkLabel(self.tabview.tab(tab_fiscal), text="CUIT (11 números, sin guiones):", font=fuente_lbl).pack(anchor="w", padx=20)
        self.entry_cuit = ctk.CTkEntry(self.tabview.tab(tab_fiscal), font=fuente_entry, width=380)
        self.entry_cuit.pack(pady=(0, 5))

        ctk.CTkLabel(self.tabview.tab(tab_fiscal), text="Condición frente al IVA:", font=fuente_lbl).pack(anchor="w", padx=20)
        self.combo_iva = ctk.CTkComboBox(self.tabview.tab(tab_fiscal), values=["Monotributista", "Responsable Inscripto", "Exento"], font=fuente_entry, width=380)
        self.combo_iva.pack(pady=(0, 5))

        ctk.CTkLabel(self.tabview.tab(tab_fiscal), text="N° Ingresos Brutos (o 'Exento'):", font=fuente_lbl).pack(anchor="w", padx=20)
        self.entry_iibb = ctk.CTkEntry(self.tabview.tab(tab_fiscal), font=fuente_entry, width=380)
        self.entry_iibb.pack(pady=(0, 5))

        ctk.CTkLabel(self.tabview.tab(tab_fiscal), text="Inicio de Actividades (DD/MM/AAAA):", font=fuente_lbl).pack(anchor="w", padx=20)
        self.entry_inicio = ctk.CTkEntry(self.tabview.tab(tab_fiscal), font=fuente_entry, width=380, placeholder_text="Ej: 01/05/2020")
        self.entry_inicio.pack(pady=(0, 5))

        # Botón Guardar global (Guarda ambas pestañas a la vez y está SIEMPRE visible)
        self.btn_guardar = ctk.CTkButton(self, text="💾 Guardar Configuración", fg_color="#2FA572", hover_color="#238259", height=45, font=("Roboto", 14, "bold"), command=self.guardar_datos)
        self.btn_guardar.pack(pady=(10, 20))

        # Cargamos los datos al iniciar para que el usuario vea lo que ya está guardado
        self.cargar_datos()

    def cargar_datos(self):
        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config_local (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    razon_social TEXT, nombre_fantasia TEXT, cuit TEXT, direccion TEXT, 
                    telefono TEXT, instagram TEXT, condicion_iva TEXT, iibb TEXT, inicio_actividades TEXT
                )
            """)
            
            try:
                cursor.execute("ALTER TABLE config_local ADD COLUMN instagram TEXT")
            except:
                pass 
                
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
            else:
                cursor.execute("INSERT INTO config_local (id, nombre_fantasia, condicion_iva) VALUES (1, 'MI LOCAL', 'Monotributista')")
                conexion.commit()

        except Exception as e:
            messagebox.showerror("❌ Error", f"No se pudieron cargar los ajustes:\n{e}")
        finally:
            if 'conexion' in locals(): conexion.close()

    def guardar_datos(self):
        fantasia = self.entry_fantasia.get().strip()
        razon = self.entry_razon.get().strip()
        cuit = self.entry_cuit.get().strip()
        direccion = self.entry_direccion.get().strip()
        telefono = self.entry_telefono.get().strip()
        instagram = self.entry_instagram.get().strip()
        iva = self.combo_iva.get()
        iibb = self.entry_iibb.get().strip()
        inicio = self.entry_inicio.get().strip()

        if cuit != "" and (not cuit.isdigit() or len(cuit) != 11):
            messagebox.showwarning("⚠️ CUIT Inválido", "Si completa el CUIT, debe tener exactamente 11 números, sin guiones.")
            return

        try:
            conexion = sqlite3.connect(self.ruta_db)
            cursor = conexion.cursor()
            
            cursor.execute("""
                UPDATE config_local 
                SET razon_social = ?, nombre_fantasia = ?, cuit = ?, direccion = ?, 
                    telefono = ?, instagram = ?, condicion_iva = ?, iibb = ?, inicio_actividades = ?
                WHERE id = 1
            """, (razon, fantasia, cuit, direccion, telefono, instagram, iva, iibb, inicio))
            
            conexion.commit()
            messagebox.showinfo("✅ Guardado", "Ajustes actualizados correctamente.")
            self.destroy()

        except Exception as e:
            messagebox.showerror("❌ Error", f"No se pudieron guardar los ajustes:\n{e}")
        finally:
            if 'conexion' in locals(): conexion.close()

if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("100x100")
    app.withdraw()
    v = VentanaAjustes(app)
    app.mainloop()
# 🏪 Sistema ERP y POS para Minimercados

Sistema integral de Punto de Venta (POS), facturación, control de inventario y gestión financiera diseñado específicamente para pequeños y medianos comercios. Desarrollado con enfoque en rendimiento, experiencia de usuario y seguridad criptográfica.

## 🚀 Características Principales

* **Caja Registradora Inteligente:** Soporte para lectores de códigos de barras, detección automática de productos de peso (precio variable) y fijación de precios en tiempo real para productos nuevos.
* **Motor de Inventario Escalable:** Gestión fluida de bases de datos masivas (+200k artículos) mediante consultas SQL optimizadas con indexación y paginación en memoria.
* **Inyección Masiva de Datos:** Módulo de importación de listas de precios de proveedores que procesa archivos Excel y CSV, tolerando desorden de columnas y detectando datos faltantes sin interrumpir la carga.
* **Módulo Financiero y Arqueos:** Control de aperturas de caja con fondo fijo, cierres Z declarativos y cálculo automático de diferencias financieras.
* **Gestión de Cuentas Corrientes:** Libreta de "fiados" digital con registro de deudas por cliente, recepción de pagos parciales y sincronización automática con el arqueo del día.

## 🛡️ Arquitectura y Seguridad

* **Licenciamiento Criptográfico:** El sistema implementa una barrera de seguridad de clave asimétrica (RSA). Las licencias se firman digitalmente y se encriptan validando la fecha de vencimiento.
* **Hardware Locking:** El software captura el UUID (Hardware ID) de la placa madre a través de PowerShell, atando la ejecución del sistema a una computadora física específica para evitar la piratería.
* **Bases de Datos Locales:** Uso de SQLite para garantizar operaciones rápidas y offline, previniendo cuellos de botella y manteniendo la privacidad transaccional del comercio.

## 🛠️ Tecnologías Utilizadas

* **Lenguaje:** Python 3.12
* **Interfaz Gráfica (GUI):** CustomTkinter (Diseño moderno y adaptativo)
* **Base de Datos:** SQLite3
* **Procesamiento de Datos:** Pandas
* **Seguridad:** RSA, Subprocess (Interacción con SO)

## 📌 Estado del Proyecto
Versión 1.0 - Lista para producción y empaquetado en formato `.exe` mediante PyInstaller.

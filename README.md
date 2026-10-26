# 🏪 SistemaMercado — ERP y POS Híbrido para Minimercados

Sistema integral de Punto de Venta (POS), facturación, control de inventario y gestión financiera diseñado específicamente para pequeños y medianos comercios minoristas. Desarrollado con un enfoque nativo en rendimiento, seguridad y adaptabilidad operativa (tanto en escritorio como en entornos móviles de nube).

---

## 🚀 Características Principales

* **Caja Registradora Inteligente:** Soporte para lectores de códigos de barras (USB y Bluetooth), detección automática de productos pesables (precio variable) y fijación de precios en tiempo real.
* **Motor de Inventario Escalable:** Gestión fluida de bases de datos masivas (compatible con catálogos amplios de almacén, ferretería y farmacia) mediante consultas SQL optimizadas.
* **Inyección Masiva de Datos:** Módulo de importación inteligente de listas de precios de proveedores que procesa archivos Excel (`.xlsx`) y CSV, realizando autolimpieza de columnas y deduplicación automática.
* **Módulo Financiero y Arqueos:** Control de aperturas de caja con fondo fijo, cierres Z declarativos, pagos mixtos (efectivo, transferencia, Mercado Pago) y cálculo automático de diferencias financieras.
* **Gestión de Cuentas Corrientes:** Libreta digital de "fiados" con registro de deudas por cliente y recepción de pagos parciales.
* **Cumplimiento Normativo (Argentina):** Adaptado a las exigencias de Facturación Electrónica vía ARCA/AFIP (BFE) y lineamientos de Transparencia Fiscal al Consumidor (**Ley 27.743**, desglose de IVA y tickets optimizados para impresoras térmicas de 58mm).

---

## 🛡️ Arquitectura y Seguridad

* **Licenciamiento Criptográfico (RSA):** El sistema implementa una barrera de seguridad de clave asimétrica. Las licencias se firman digitalmente y se encriptan validando fechas de vencimiento.
* **Hardware Locking:** Captura del UUID (Hardware ID) de la placa madre mediante el sistema operativo, atando la ejecución del software a terminales autorizadas.
* **Estrategia Híbrida (Escritorio & Cloud):** 
  * Versión Local (Legacy/Escritorio): Diseñada en Python con SQLite para operaciones rápidas, offline y seguras.
  * Evolución Cloud (v2.0): Arquitectura preparada para migración multi-inquilino (*tenant_id*) con **Supabase (PostgreSQL)** y **FastAPI**, permitiendo acceso móvil mediante PWA (Progressive Web App) y escaneo por cámara para comercios sin computadora de escritorio.

---

## 🛠️ Tecnologías Utilizadas

* **Lenguaje:** Python 3.12
* **Interfaz Gráfica (Escritorio):** CustomTkinter
* **Backend & Cloud (En desarrollo):** FastAPI, Supabase, PostgreSQL
* **Procesamiento de Datos:** Pandas
* **Seguridad:** RSA, Subprocess (Hardware ID), Certificados X.509 (AFIP)
* **Empaquetado:** PyInstaller (`.exe` autónomo)

---

## 📌 Estado del Proyecto
* **v1.0 (Escritorio):** Completa y lista para producción en entornos con terminal PC.
* **v2.0 (Cloud/Mobile PWA):** En fase de diseño arquitectónico y migración de esquemas de base de datos.

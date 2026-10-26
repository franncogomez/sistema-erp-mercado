import zeep
import base64
import json
import sys
import os
from datetime import datetime, timedelta
from lxml import etree
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography import x509

class MiAfip:
    def __init__(self, cuit, crt_path, key_path, produccion=False):
        self.cuit = cuit
        self.crt_path = crt_path
        self.key_path = key_path
        self.produccion = produccion
        
        # 🔗 URLs de los servidores (Homologación/Pruebas o Producción/Real)
        if produccion:
            self.wsaa_url = "https://wsaa.afip.gov.ar/ws/services/LoginCms?wsdl"
            self.wsfe_url = "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL"
        else:
            self.wsaa_url = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl"
            self.wsfe_url = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"

        self.token = None
        self.sign = None

    def _generar_tra(self):
        """Genera el Ticket de Requerimiento de Acceso (TRA) en XML"""
        generacion = (datetime.utcnow() - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S-00:00")
        expiracion = (datetime.utcnow() + timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%S-00:00")
        unique_id = str(int(datetime.utcnow().timestamp()))
        
        tra = f"""<?xml version="1.0" encoding="UTF-8"?>
        <loginTicketRequest version="1.0">
            <header>
                <uniqueId>{unique_id}</uniqueId>
                <generationTime>{generacion}</generationTime>
                <expirationTime>{expiracion}</expirationTime>
            </header>
            <service>wsfe</service>
        </loginTicketRequest>"""
        return tra

    def _firmar_tra(self, tra_xml):
        """Firma el XML usando tu certificado (.crt) y tu clave privada (.key)"""
        with open(self.crt_path, "rb") as f:
            cert = x509.load_pem_x509_certificate(f.read())
        with open(self.key_path, "rb") as f:
            key = serialization.load_pem_private_key(f.read(), password=None)
        
        builder = pkcs7.PKCS7SignatureBuilder().set_data(tra_xml.encode('utf-8'))
        builder = builder.add_signer(cert, key, hashes.SHA256())
        
        signed_der = builder.sign(serialization.Encoding.DER, [])
        return base64.b64encode(signed_der).decode('utf-8')

    def autenticar(self):
        """Se conecta a AFIP para conseguir la autorización de 12 horas"""
        
        # 🛠️ LÓGICA DE RUTA ABSOLUTA (Para VS Code y para el .exe)
        if getattr(sys, 'frozen', False):
            # Si estamos en el .exe, buscamos en _internal/certificados
            ruta_base = os.path.dirname(sys.executable)
            ruta_certificados = os.path.join(ruta_base, "_internal", "certificados")
        else:
            # Si estamos en VS Code, buscamos en la carpeta certificados de desarrollo
            ruta_base = os.path.dirname(os.path.abspath(__file__))
            ruta_certificados = os.path.join(ruta_base, "certificados")
            
        # Nos aseguramos de que la carpeta exista por si las dudas
        os.makedirs(ruta_certificados, exist_ok=True)
        
        # Ahora sí, armamos la ruta completa y blindada del token
        archivo_token = os.path.join(ruta_certificados, f"token_afip_{self.cuit}.json")
        
        # 🛡️ Sistema de Caché: Si el token existe y no venció, lo reutiliza (más rápido)
        if os.path.exists(archivo_token):
            with open(archivo_token, "r") as f:
                datos = json.load(f)
                exp = datetime.strptime(datos["expiracion"], "%Y-%m-%d %H:%M:%S")
                if datetime.now() < exp:
                    self.token = datos["token"]
                    self.sign = datos["sign"]
                    return
        
        # Generar firma y comunicarse por SOAP (Zeep)
        tra = self._generar_tra()
        cms_firmado = self._firmar_tra(tra)
        
        cliente = zeep.Client(self.wsaa_url)
        resultado = cliente.service.loginCms(in0=cms_firmado)
        
        # Leer la respuesta XML del gobierno
        xml_res = etree.fromstring(resultado.encode('utf-8'))
        self.token = xml_res.find(".//token").text
        self.sign = xml_res.find(".//sign").text
        
        # Guardar localmente para reutilizar (en la nueva ruta segura)
        with open(archivo_token, "w") as f:
            exp = (datetime.now() + timedelta(hours=10)).strftime("%Y-%m-%d %H:%M:%S")
            json.dump({"token": self.token, "sign": self.sign, "expiracion": exp}, f)

    def _auth_wsfe(self):
        if not self.token or not self.sign:
            self.autenticar()
        return {"Token": self.token, "Sign": self.sign, "Cuit": self.cuit}

    def obtener_ultimo_comprobante(self, pto_vta, cbte_tipo):
        """Le pregunta a AFIP qué número de factura toca ahora"""
        cliente = zeep.Client(self.wsfe_url)
        res = cliente.service.FECompUltimoAutorizado(Auth=self._auth_wsfe(), PtoVta=pto_vta, CbteTipo=cbte_tipo)
        if res.Errors:
            raise Exception(res.Errors.Err[0].Msg)
        return res.CbteNro

    def crear_factura(self, datos):
        """Manda los datos de la venta y recibe el CAE aprobado"""
        cliente = zeep.Client(self.wsfe_url)
        
        # Armamos el paquete que requiere AFIP basado en el WSDL oficial
        req = {
            "FeCAEReq": {
                "FeCabReq": {
                    "CantReg": datos["CantReg"],
                    "PtoVta": datos["PtoVta"],
                    "CbteTipo": datos["CbteTipo"]
                },
                "FeDetReq": {
                    "FECAEDetRequest": [{
                        "Concepto": datos["Concepto"],
                        "DocTipo": datos["DocTipo"],
                        "DocNro": datos["DocNro"],
                        "CbteDesde": datos["CbteDesde"],
                        "CbteHasta": datos["CbteHasta"],
                        "CbteFch": str(datos["CbteFch"]),
                        "ImpTotal": datos["ImpTotal"],
                        "ImpTotConc": datos["ImpTotConc"],
                        "ImpNeto": datos["ImpNeto"],
                        "ImpOpEx": datos["ImpOpEx"],
                        "ImpTrib": datos["ImpTrib"],
                        "ImpIVA": datos["ImpIVA"],
                        "MonId": datos["MonId"],
                        "MonCotiz": datos["MonCotiz"],
                        # 🛠️ ACÁ ESTABA EL ERROR: Faltaba enviarle esto a AFIP
                        "CondicionIVAReceptorId": datos.get("CondicionIVAReceptorId", 5) 
                    }]
                }
            }
        }
        
        # Desglose de IVA si existe en los datos
        if "Iva" in datos:
            iva_list = []
            for iva in datos["Iva"]:
                iva_list.append({"Id": iva["Id"], "BaseImp": iva["BaseImp"], "Importe": iva["Importe"]})
            req["FeCAEReq"]["FeDetReq"]["FECAEDetRequest"][0]["Iva"] = {"AlicIva": iva_list}
        
        # Solicitamos la autorización (CAE)
        res = cliente.service.FECAESolicitar(Auth=self._auth_wsfe(), **req)
        
        if res.Errors:
            raise Exception(res.Errors.Err[0].Msg)
            
        detalle_res = res.FeDetResp.FECAEDetResponse[0]
        
        if detalle_res.Resultado == "R":
            motivo = detalle_res.Observaciones.Obs[0].Msg if detalle_res.Observaciones else "Rechazado por inconsistencias en los montos."
            raise Exception(f"AFIP rechazó la factura:\n{motivo}")
            
        return {
            "CAE": detalle_res.CAE,
            "CAEFchVto": detalle_res.CAEFchVto
        }
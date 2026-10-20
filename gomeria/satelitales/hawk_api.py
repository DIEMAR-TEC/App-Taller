"""Hawk por su API: Api.asmx/getUnits, con usuario y contraseña.

Reemplaza al login con Chrome de hawk.py: un solo pedido HTTP trae toda la
flota, sin navegador ni cookies. Por eso esto ya no depende de GitHub
Actions y podría correr en cualquier lado.

Es un servicio .asmx de .NET, que puede contestar de tres maneras según
cómo esté configurado: XML con los campos, XML con un JSON adentro, o JSON
directo. Se aceptan las tres. Los nombres de los parámetros se leen del WSDL
del propio servicio, así que si Hawk los llama `user` o `usuario` da igual;
y los campos de cada unidad se buscan por nombre (Patente, Kilometraje,
Odometro…). Si ninguno se reconoce, el error dice cuáles llegaron, que es
lo que hace falta para ajustar la lista.

Opciones de la cuenta (cuentas.json → "opciones"), todas opcionales:

    "url":       otra dirección del Api.asmx
    "metodo":    otro método en vez de getUnits
    "parametros": {"usuario": "nombreDelParametro", "clave": "...", "otro": "valor"}
    "campos":    {"patente": "...", "km": "...", "reporte": "...", "id": "..."}
"""
import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from xml.etree import ElementTree

import satelitales as sat

FUENTE = "hawk"
URL = "http://www.hawkgps.com.ar/HawkEyeWeb/Api/Api.asmx"
METODO = "getUnits"

# Los nombres posibles de cada dato, en orden de preferencia. Lo que no
# coincide exacto se busca por pedazo (la segunda tupla).
PATENTE = (("VehiclePlate", "Patente", "Dominio", "Plate", "LicensePlate", "Descripcion",
            "Description", "Alias", "UnitName", "Nombre", "Name"), ("patente", "dominio"))
KM = (("Kilometraje", "Odometro", "Odometer", "OdometroKm", "Km", "Kms",
       "Mileage", "TotalKm"), ("odom", "kilomet", "mileage"))
# getUnits manda GPSDate sin zona y en hora argentina (12:25 de la lectura
# del 20/10 a las 12:30 ART), así que se guarda tal cual.
REPORTE = (("GPSDate", "FechaServer", "UltimoReporte", "FechaUltimoReporte", "LastReport",
            "FechaGPS", "GpsDate", "Fecha", "Date", "DateTime", "Timestamp"),
           ("fecha", "date", "report"))
ID = (("idGPS", "IdGps", "IdMovil", "IdUnidad", "UnitId", "Id", "IMEI"), ())
EMPRESA = (("NombreEmpresa", "Empresa", "Company", "Cliente"), ())

PARAM_USUARIO = re.compile(r"user|usuario|login", re.I)
PARAM_CLAVE = re.compile(r"pass|clave|contra|pwd", re.I)

WSDL = "{http://schemas.xmlsoap.org/wsdl/}"
XS = "{http://www.w3.org/2001/XMLSchema}"


def _sin_ns(tag):
    return tag.rsplit("}", 1)[-1]


# ------------------------------------------------------------------ pedido

def _basica(credenciales):
    """Usuario y contraseña como autenticación HTTP básica.

    Es lo que pide getUnits: al abrirlo en el navegador aparece la ventana
    de usuario y contraseña, y la dirección no lleva parámetros.
    """
    par = f"{credenciales.get('usuario', '')}:{credenciales.get('clave', '')}"
    return {"Authorization": "Basic " + base64.b64encode(par.encode("utf-8")).decode()}


def _pedir(url, datos=None, cabeceras=None):
    pedido = urllib.request.Request(url, data=datos, headers=cabeceras or {})
    try:
        with urllib.request.urlopen(pedido, timeout=60) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        cuerpo = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {e.code}: {_texto_plano(cuerpo)[:300]}") from None


def _texto_plano(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _wsdl(url, metodo, cabeceras=None):
    """Los parámetros que pide el método y el namespace del servicio.

    None si no se pudo leer el WSDL; [] si el método no lleva parámetros.
    """
    try:
        raiz = ElementTree.fromstring(_pedir(url + "?WSDL", cabeceras=cabeceras))
    except Exception:
        return None, None
    namespace = raiz.get("targetNamespace")
    for el in raiz.iter(XS + "element"):
        if el.get("name") == metodo:
            return [e.get("name") for e in el.iter(XS + "element") if e is not el], namespace
    return None, namespace


def _parametros(nombres, credenciales, opciones):
    """Los parámetros del pedido, con la credencial que va en cada uno."""
    fijos = dict((opciones or {}).get("parametros") or {})
    p_usuario = fijos.pop("usuario", None)
    p_clave = fijos.pop("clave", None)
    if nombres is None:
        # Sin WSDL: solo los que diga la configuración. Por defecto ninguno,
        # porque el usuario y la contraseña van en la autenticación básica.
        nombres = [n for n in (p_usuario, p_clave) if n] + list(fijos)
    salida = {}
    for n in nombres:
        if n == p_usuario or (not p_usuario and PARAM_USUARIO.search(n)):
            salida[n] = credenciales.get("usuario", "")
        elif n == p_clave or (not p_clave and PARAM_CLAVE.search(n)):
            salida[n] = credenciales.get("clave", "")
        else:
            salida[n] = str(fijos.get(n, credenciales.get(n, "")))
    return salida


def _directo(url, metodo, parametros, cabeceras):
    """GET si no hay parámetros (como el navegador), si no POST de formulario."""
    if not parametros:
        return _pedir(f"{url}/{metodo}", cabeceras=cabeceras)
    return _pedir(f"{url}/{metodo}", urllib.parse.urlencode(parametros).encode(),
                  {**cabeceras, "Content-Type": "application/x-www-form-urlencoded"})


def _soap(url, metodo, parametros, namespace, cabeceras):
    """El mismo pedido en SOAP 1.1, que es lo único que .asmx deja prendido siempre."""
    namespace = namespace or "http://tempuri.org/"
    campos = "".join(f"<{k}>{_escapar(v)}</{k}>" for k, v in parametros.items())
    sobre = ('<?xml version="1.0" encoding="utf-8"?>'
             '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
             f'<soap:Body><{metodo} xmlns="{namespace}">{campos}</{metodo}></soap:Body>'
             '</soap:Envelope>')
    accion = namespace.rstrip("/") + "/" + metodo
    return _pedir(url, sobre.encode("utf-8"),
                  {**cabeceras, "Content-Type": "text/xml; charset=utf-8",
                   "SOAPAction": f'"{accion}"'})


def _escapar(v):
    return (str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# --------------------------------------------------------------- respuesta

def registros(texto):
    """Las unidades de la respuesta, como lista de diccionarios planos."""
    texto = (texto or "").strip()
    if texto[:1] in "[{":
        return _de_json(json.loads(texto))
    raiz = ElementTree.fromstring(texto)
    # <string>…JSON o XML…</string>, o el Result de SOAP con texto adentro:
    # un sobre de pocos elementos con un único texto que es otro documento.
    if sum(1 for _ in raiz.iter()) <= 6:
        for el in raiz.iter():
            if len(el) == 0 and (el.text or "").strip()[:1] in "[{<":
                return registros(el.text)
    return _de_xml(raiz)


def _de_json(datos):
    if isinstance(datos, dict):
        if "d" in datos:
            return _de_json(datos["d"])
        listas = [v for v in datos.values() if isinstance(v, list)]
        if listas:
            return _de_json(max(listas, key=len))
        return [datos]
    if isinstance(datos, str):
        return registros(datos)
    return [_plano(d) for d in datos or [] if isinstance(d, dict)]


def _plano(d):
    """{"Posicion": {"Odometro": 5}} → {"Odometro": 5}: los anidados suben."""
    salida = {}
    for k, v in d.items():
        if isinstance(v, dict):
            for k2, v2 in _plano(v).items():
                salida.setdefault(k2, v2)
        elif not isinstance(v, list):
            salida[k] = v
    return salida


def _de_xml(raiz):
    """El grupo más grande de elementos hermanos con hijos es la lista de unidades."""
    mejor = []
    for padre in raiz.iter():
        hijos = [h for h in padre if len(h)]
        if len(hijos) > len(mejor):
            mejor = hijos
    salida = []
    for unidad in mejor:
        fila = dict(unidad.attrib)
        for el in unidad.iter():
            if el is not unidad and len(el) == 0:
                fila.setdefault(_sin_ns(el.tag), (el.text or "").strip())
        salida.append(fila)
    return salida


def _lectura(r, campos, hoy):
    import hawk

    def tomar(cual, nombres):
        propio = campos.get(cual)
        return r.get(propio) if propio else sat.campo(r, *nombres)

    km = sat.numero(tomar("km", KM))
    return {
        "Patente": hawk._patente(tomar("patente", PATENTE)),
        "Kilometraje": km,
        "Ultimo_reporte": sat.momento(tomar("reporte", REPORTE)),
        "idGPS": str(tomar("id", ID) or "").strip() or None,
        "Fecha_lectura": hoy,
        "Empresa": str(tomar("empresa", EMPRESA) or "").strip() or None,
    }


# ------------------------------------------------------------------ lectura

def leer(credenciales, opciones=None):
    """La respuesta cruda de getUnits: primero directo, si no por SOAP."""
    opciones = opciones or {}
    url = (opciones.get("url") or URL).rstrip("/")
    metodo = opciones.get("metodo") or METODO
    cabeceras = _basica(credenciales)
    nombres, namespace = _wsdl(url, metodo, cabeceras)
    parametros = _parametros(nombres, credenciales, opciones)
    try:
        return _directo(url, metodo, parametros, cabeceras)
    except Exception as e:
        print(f"Hawk API: el pedido directo no anduvo ({e}); se prueba por SOAP")
        return _soap(url, metodo, parametros, namespace, cabeceras)


def lecturas(credenciales, opciones=None):
    opciones = opciones or {}
    filas = registros(leer(credenciales, opciones))
    if not filas:
        raise SystemExit("Hawk API: getUnits no devolvió ninguna unidad.")
    print(f"flota: {len(filas)} móviles")

    hoy = sat.ahora()
    campos = opciones.get("campos") or {}
    salida = [_lectura(r, campos, hoy) for r in filas]

    if not any(isinstance(f["Kilometraje"], float) for f in salida):
        raise SystemExit("Hawk API: ninguna unidad trae un campo reconocible de "
                         f"kilometraje. Campos recibidos: {', '.join(sorted(filas[0]))}")

    sin = [f["Patente"] or str(f["idGPS"]) for f in salida
           if not isinstance(f["Kilometraje"], float)]
    print(f"leídos {len(salida) - len(sin)}/{len(salida)} con kilometraje")
    if sin:
        print(f"sin lectura ({len(sin)}): " + ", ".join(sin[:10]) +
              (" …" if len(sin) > 10 else ""))
    return salida

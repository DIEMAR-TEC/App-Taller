"""Los kilómetros de cada empresa, vengan del satelital que vengan.

Cada empresa cliente usa su propio proveedor de GPS y cada proveedor tiene
su API: Hawk contesta XML de un servicio .asmx, otro va a contestar JSON con
token, otro un CSV. Lo que no cambia es lo que la app necesita de ellos: la
patente, el odómetro y cuándo reportó. Este paquete es ese contrato.

Un proveedor es un módulo de esta carpeta con dos cosas:

    FUENTE = "hawk"                       # lo que queda en odometros.fuente
    def lecturas(credenciales, opciones): # la lista de lecturas estándar

`credenciales` trae los valores ya resueltos de los secrets
({"usuario": ..., "clave": ...}) y `opciones` lo que la cuenta tenga de
particular (otra URL, un filtro, nombres de campos).

Y una lectura estándar es el diccionario que ya espera subir_odometros:

    {"Patente": "AE527FA",                     # sin espacios ni guiones
     "Kilometraje": 120000.5,                  # km, número; None si no vino
     "Ultimo_reporte": "2026-09-11 09:00:00",  # hora argentina, o None
     "idGPS": "29627",                         # id del equipo en el proveedor
     "Fecha_lectura": "2026-09-11 05:00:00",   # cuándo se leyó (hora argentina)
     "Empresa": "Diemar"}                      # opcional, para filtrar

Las cuentas —qué empresa, con qué proveedor y con qué credenciales— están
en `cuentas.json`. Agregar un cliente con un satelital que ya existe es una
línea ahí y dos secrets; uno con un satelital nuevo es además un módulo acá
y una línea en PROVEEDORES. Ver ODOMETROS.md.
"""
import datetime
import importlib
import json
import os
import re
from pathlib import Path

# id del proveedor (el de cuentas.json) → módulo de esta carpeta.
PROVEEDORES = {
    "hawk_api": "satelitales.hawk_api",   # Api.asmx/getUnits, sin navegador
    "hawk_web": "satelitales.hawk_web",   # el login con Chrome, de respaldo
}

# Las fuentes de `odometros` que son lecturas de un satelital, a diferencia
# de las que carga la app (enganche, correccion:…, mantenimiento:…). La
# portada y Parámetros cuentan solo estas. Hawk API y Hawk web son el mismo
# odómetro, así que comparten fuente y la segunda lectura del día pisa a la
# primera en vez de duplicarla.
FUENTES = ("hawk",)

CUENTAS = Path(__file__).with_name("cuentas.json")

ARG = datetime.timezone(datetime.timedelta(hours=-3))


def en_sql():
    """FUENTES escritas como lista de SQL: ('hawk', 'otro')."""
    return "(" + ", ".join("'" + f.replace("'", "''") + "'" for f in FUENTES) + ")"


def ahora():
    return datetime.datetime.now(ARG).strftime("%Y-%m-%d %H:%M:%S")


def proveedor(nombre):
    """El módulo del proveedor. Explota con la lista si el nombre no existe."""
    if nombre not in PROVEEDORES:
        raise SystemExit(f"proveedor desconocido: {nombre!r} "
                         f"(hay: {', '.join(sorted(PROVEEDORES))})")
    return importlib.import_module(PROVEEDORES[nombre])


def cuentas(ruta=None, solo_activas=True):
    """Las cuentas de cuentas.json; por defecto sin las que están apagadas."""
    datos = json.loads(Path(ruta or CUENTAS).read_text(encoding="utf-8"))
    return [c for c in datos if not solo_activas or c.get("activa", True)]


def secreto(nombre):
    """El valor de un secret por su nombre.

    Primero la variable de entorno, que es como los pasa el workflow: uno
    por uno, con su nombre. Si no está, el JSON de SECRETOS, {"NOMBRE":
    "valor"}, que sirve para correr esto a mano sin exportar cuatro
    variables.

    El workflow pasó un tiempo volcando todos los secrets del repo acá con
    toJSON(secrets). GitHub lo lee como una fuga y bloquea el workflow, así
    que cada secret va nombrado.
    """
    valor = os.environ.get(nombre)
    if valor is None:
        try:
            valor = json.loads(os.environ.get("SECRETOS") or "{}").get(nombre)
        except ValueError:
            valor = None
    return (valor or "").strip()


def credenciales(cuenta):
    """{"usuario": "HAWK_USER"} → {"usuario": "<el valor del secret>"}."""
    salida, faltan = {}, []
    for campo, nombre in (cuenta.get("credenciales") or {}).items():
        valor = secreto(nombre)
        if not valor:
            faltan.append(nombre)
        salida[campo] = valor
    if faltan:
        raise SystemExit(f"{cuenta.get('empresa')}: faltan los secrets {', '.join(faltan)}")
    return salida


# ------------------------------------------------- ayudas para los módulos

def numero(valor):
    """120000.5, "120000,5", "120.000,5" y "120,000.5" son el mismo número."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = re.sub(r"[^\d.,-]", "", str(valor or ""))
    if not texto:
        return None
    if "," in texto and "." in texto:
        # El último separador es el decimal.
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".") if len(texto.split(",")[-1]) != 3 \
            else texto.replace(",", "")
    try:
        return float(texto)
    except ValueError:
        return None


def momento(valor):
    """Una fecha en cualquiera de los formatos que mandan los satelitales.

    Devuelve 'YYYY-MM-DD HH:MM:SS' en hora argentina, o None.
    """
    texto = str(valor or "").strip()
    if not texto:
        return None
    m = re.search(r"/Date\((-?\d+)", texto)                    # .NET
    if m:
        dt = datetime.datetime.fromtimestamp(int(m.group(1)) / 1000, ARG)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    if re.fullmatch(r"\d{10}(\d{3})?", texto):                 # epoch
        seg = int(texto) / (1000 if len(texto) == 13 else 1)
        return datetime.datetime.fromtimestamp(seg, ARG).strftime("%Y-%m-%d %H:%M:%S")
    try:                                                       # ISO 8601
        dt = datetime.datetime.fromisoformat(texto.replace("Z", "+00:00"))
        if dt.tzinfo:
            dt = dt.astimezone(ARG)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass
    for formato in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y",
                    "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M"):
        try:
            return datetime.datetime.strptime(texto, formato).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return None


def _clave(texto):
    return re.sub(r"[^a-z0-9]", "", str(texto).lower())


def campo(registro, candidatos, contiene=()):
    """El primer campo del registro que coincida, sin mirar mayúsculas ni guiones.

    `candidatos` son nombres exactos en orden de preferencia; `contiene`,
    pedazos que se aceptan si no hubo ninguno exacto.
    """
    planos = {_clave(k): v for k, v in registro.items()}
    for c in candidatos:
        v = planos.get(_clave(c))
        if v not in (None, ""):
            return v
    for k, v in planos.items():
        if v not in (None, "") and any(p in k for p in contiene):
            return v
    return None

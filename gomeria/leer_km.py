"""Los odómetros de todas las empresas, cada una desde su satelital.

Recorre las cuentas de satelitales/cuentas.json, le pide a cada proveedor
sus lecturas en el formato estándar y las deja en `odometros`. Una cuenta
que falla no frena a las demás, pero el job termina en error para que
llegue el mail.

Si el proveedor principal de una cuenta falla y tiene "respaldo", se prueba
con ese: hoy Hawk se lee por su API y, si la API no contesta, por la página
con Chrome como antes.

    python gomeria/leer_km.py

Variables opcionales:
    SOLO_CUENTAS   leer solo estas cuentas (pedazo del nombre, separadas por coma)
    SOLO_EMPRESAS  dentro de la cuenta, solo las unidades de estas empresas
    PROBAR=1       leer y mostrar, sin guardar nada en la base
"""
import os
import sys

import satelitales as sat
import subir_odometros


def _lista(variable):
    return [s.strip().upper() for s in os.environ.get(variable, "").split(",") if s.strip()]


def _con_km(filas):
    return [f for f in filas
            if isinstance(f.get("Kilometraje"), (int, float)) and f["Kilometraje"] > 0]


def leer_cuenta(cuenta):
    """(fuente, lecturas) del primer proveedor de la cuenta que traiga km."""
    credenciales = sat.credenciales(cuenta)
    respaldo = cuenta.get("respaldo") or []
    intentos = [cuenta["proveedor"]] + ([respaldo] if isinstance(respaldo, str) else list(respaldo))
    errores = []
    for nombre in intentos:
        modulo = sat.proveedor(nombre)
        print(f"\n== {cuenta['empresa']} · {nombre}")
        try:
            filas = modulo.lecturas(credenciales, cuenta.get("opciones") or {})
            # Que el satelital conteste sin un solo kilometraje no es un día
            # sin viajes: es la sesión caída o la API cambiada.
            if not _con_km(filas):
                raise SystemExit(f"{nombre} contestó pero ningún móvil trajo kilometraje.")
            return modulo.FUENTE, filas
        except (Exception, SystemExit) as e:
            print(f"{nombre}: {e}")
            errores.append(f"{nombre}: {e}")
    raise SystemExit("; ".join(errores))


def _filtrar(filas, empresas):
    if not empresas:
        return filas
    return [f for f in filas
            if not f.get("Empresa") or any(e in str(f["Empresa"]).upper() for e in empresas)]


def main():
    solo = _lista("SOLO_CUENTAS")
    empresas = _lista("SOLO_EMPRESAS")
    probar = os.environ.get("PROBAR", "").strip().lower() in ("1", "si", "sí", "true")

    cuentas = [c for c in sat.cuentas()
               if not solo or any(s in c["empresa"].upper() for s in solo)]
    if not cuentas:
        raise SystemExit("No hay cuentas para leer en satelitales/cuentas.json")

    fallidas = []
    for cuenta in cuentas:
        try:
            fuente, filas = leer_cuenta(cuenta)
        except SystemExit as e:
            fallidas.append(f"{cuenta['empresa']}: {e}")
            continue
        filas = _filtrar(filas, empresas)
        if probar:
            print(f"[prueba] {len(_con_km(filas))} lecturas, no se guardan. Primeras:")
            for f in _con_km(filas)[:5]:
                print(f"  {f['Patente']}  {f['Kilometraje']:.1f} km  {f['Ultimo_reporte']}")
            continue
        nuevas = subir_odometros.subir(filas, fuente=fuente)
        print(f"nuevas: {nuevas}")

    if fallidas:
        raise SystemExit("Sin lecturas: " + " | ".join(fallidas))


if __name__ == "__main__":
    sys.exit(main())

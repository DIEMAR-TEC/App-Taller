"""Hawk por la página web: el lector con Chrome de gomeria/hawk.py.

Queda como respaldo de hawk_api. Necesita Chrome y Selenium, así que solo
anda en el job de GitHub Actions.
"""
FUENTE = "hawk"


def lecturas(credenciales, opciones):
    import hawk
    return hawk.lecturas(credenciales["usuario"], credenciales["clave"])

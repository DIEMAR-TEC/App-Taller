"""Cuántas cubiertas tiene que haber en el depósito, como mínimo.

Una regla es una medida y, si hace falta, una marca, un tipo (dirección,
tracción, mixta) y una condición (nueva o recapada), con el mínimo:

    295 · BF Goodrich                   menos de 10 avisa
    295 · dirección · nueva             menos de 5 avisa

Lo que no se especifica vale cualquiera. Se cuenta lo que está en el
depósito: estado 'stock' y sin montaje abierto. Lo que está en el
recapador o en reparación no se puede poner hoy y no suma.

Las reglas se editan desde Parámetros → Gomería y avisan en Alertas.
"""
import re

import permisos

TIPOS = {"direccion": "dirección", "traccion": "tracción", "mixta": "mixta"}
CONDICIONES = {"nueva": "nueva", "recapada": "recapada"}


def _exigir_gestor(usuario):
    if not permisos.gestiona(usuario):
        raise PermissionError("Solo un encargado o administrador puede tocar el stock mínimo.")


def _texto(valor, limite=120):
    texto = " ".join(str(valor or "").split())
    return texto[:limite] or None


def _slug(nombre):
    return re.sub(r"[^a-z0-9]", "", str(nombre or "").lower())


def medida_corta(medida):
    """«295/80R22.5» → «295». «1000×20» → «1000». Sin número, None."""
    encontrado = re.search(r"\d+", str(medida or ""))
    return encontrado.group(0) if encontrado else None


def instalado(cx):
    fila = cx.execute("select to_regclass('public.cubiertas_stock_minimo') as t").fetchone()
    return bool(fila and fila["t"])


def nombre_regla(r):
    """«295 · BF GOODRICH · dirección · nueva»."""
    partes = [r["medida"], r.get("marca"), TIPOS.get(r.get("tipo") or ""),
              CONDICIONES.get(r.get("condicion") or "")]
    return " · ".join(p for p in partes if p)


def _en_deposito(cx):
    return [dict(f) for f in cx.execute("""
        select c.medida, c.marca, c.tipo, c.recapados
        from cubiertas c
        where c.estado = 'stock'
          and not exists (select 1 from montajes m
                          where m.cubierta_id = c.id and m.hasta is null)
    """).fetchall()]


def _cumple(cubierta, regla):
    if medida_corta(cubierta["medida"]) != medida_corta(regla["medida"]):
        return False
    if regla.get("marca") and _slug(cubierta["marca"]) != _slug(regla["marca"]):
        return False
    if regla.get("tipo") and cubierta.get("tipo") != regla["tipo"]:
        return False
    recapada = (cubierta.get("recapados") or 0) > 0
    if regla.get("condicion") == "nueva" and recapada:
        return False
    if regla.get("condicion") == "recapada" and not recapada:
        return False
    return True


def reglas(cx):
    """Las reglas, cada una con cuántas hay hoy y si está por debajo."""
    filas = [dict(r) for r in cx.execute("""
        select id, medida, marca, tipo, condicion, minimo, activa, nota
        from cubiertas_stock_minimo
        order by activa desc, medida, marca nulls first, tipo nulls first,
                 condicion nulls first""").fetchall()]
    deposito = _en_deposito(cx) if filas else []
    for r in filas:
        r["hay"] = sum(1 for c in deposito if _cumple(c, r))
        r["nombre"] = nombre_regla(r)
        r["falta"] = r["activa"] and r["hay"] < r["minimo"]
    return filas


def guardar(cx, datos, usuario=None):
    """Da de alta una regla o la corrige."""
    _exigir_gestor(usuario)
    if not instalado(cx):
        raise ValueError("Falta correr gomeria/51_stock_minimo_cubiertas.sql en Supabase.")
    medida = medida_corta(datos.get("medida"))
    if not medida:
        raise ValueError("Falta la medida.")
    marca = _texto(datos.get("marca"))
    tipo = _texto(datos.get("tipo")) or None
    if tipo and tipo not in TIPOS:
        raise ValueError("El tipo es dirección, tracción o mixta.")
    condicion = _texto(datos.get("condicion")) or None
    if condicion and condicion not in CONDICIONES:
        raise ValueError("La condición es nueva o recapada.")
    try:
        minimo = int(datos.get("minimo"))
    except (TypeError, ValueError):
        raise ValueError("El mínimo tiene que ser un número entero.") from None
    if minimo < 1:
        raise ValueError("El mínimo tiene que ser 1 o más.")
    activa = bool(datos.get("activa", True))
    nota = _texto(datos.get("nota"), 300)

    regla_id = datos.get("id")
    repetida = cx.execute("""
        select id from cubiertas_stock_minimo
        where medida = %s and coalesce(lower(marca), '') = coalesce(lower(%s), '')
          and coalesce(tipo, '') = coalesce(%s, '')
          and coalesce(condicion, '') = coalesce(%s, '')
          and id <> coalesce(%s, 0)""",
        (medida, marca, tipo, condicion, int(regla_id) if regla_id else None)).fetchone()
    if repetida:
        raise ValueError("Ya hay una regla para esa combinación.")

    valores = (medida, marca, tipo, condicion, minimo, activa, nota)
    if regla_id:
        fila = cx.execute("""
            update cubiertas_stock_minimo
            set medida=%s, marca=%s, tipo=%s, condicion=%s, minimo=%s, activa=%s, nota=%s
            where id=%s returning id""", (*valores, int(regla_id))).fetchone()
        if not fila:
            raise ValueError("Esa regla no existe.")
        return {"ok": True, "id": fila["id"]}
    fila = cx.execute("""
        insert into cubiertas_stock_minimo
          (medida, marca, tipo, condicion, minimo, activa, nota)
        values (%s,%s,%s,%s,%s,%s,%s) returning id""", valores).fetchone()
    return {"ok": True, "id": fila["id"]}


def borrar(cx, datos, usuario=None):
    _exigir_gestor(usuario)
    try:
        regla_id = int(datos.get("id"))
    except (TypeError, ValueError):
        raise ValueError("Falta la regla.") from None
    cx.execute("delete from cubiertas_stock_minimo where id = %s", (regla_id,))
    return {"ok": True}


def alertas(cx):
    """Las reglas que están por debajo, con la forma de la lista de Alertas.

    Sin ninguna en el depósito es grave: la próxima que se rompa no tiene
    con qué cambiarse. Por debajo del mínimo pero con alguna, es para
    esta semana.
    """
    salida = []
    for r in reglas(cx):
        if not r["falta"]:
            continue
        salida.append({
            "fuente": "stock",
            "clave": str(r["id"]),
            "severidad": "grave" if r["hay"] == 0 else "media",
            "titulo": (f"Sin cubiertas {r['nombre']}" if r["hay"] == 0
                       else f"Quedan {r['hay']} cubiertas {r['nombre']}"),
            "detalle": f"El mínimo es {r['minimo']}. Faltan {r['minimo'] - r['hay']}.",
            "patente": None,
            "interno": None,
            "sucursal": None,
            "de_quien": None,
            "fecha": None,
            "orden": r["hay"] / r["minimo"],
            "extra": r.get("nota"),
        })
    return salida

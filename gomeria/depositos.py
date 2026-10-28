"""Los depósitos: dónde se guardan las cubiertas y los repuestos.

Uno por lugar físico (Buenos Aires, otra provincia). Cada uno dice para
qué se usa: cubiertas, repuestos o los dos. Se editan desde
`/parametros`. Ver 53_estados_y_depositos.sql.
"""
import permisos

USOS = ("cubiertas", "repuestos", "ambos")


def _exigir_gestor(usuario):
    if not permisos.gestiona(usuario):
        raise PermissionError("Solo un encargado o administrador puede tocar los depósitos.")


def _texto(valor, limite=120):
    texto = " ".join(str(valor or "").split())
    return texto[:limite] or None


def instalado(cx):
    fila = cx.execute("select to_regclass('public.depositos') as t").fetchone()
    return bool(fila and fila["t"])


def listar(cx, incluir_inactivos=False):
    """Los depósitos, con cuántas cubiertas hay en cada uno sin montar."""
    return [dict(d) for d in cx.execute(f"""
        select d.id, d.nombre, d.uso, d.direccion, d.activo, d.orden,
               (select count(*) from cubiertas c
                where c.deposito_id = d.id and c.estado = 'stock')::int as cubiertas
        from depositos d
        {'' if incluir_inactivos else 'where d.activo'}
        order by d.activo desc, d.orden, d.nombre
    """).fetchall()]


def guardar(cx, datos, usuario=None):
    """Da de alta un depósito o lo corrige."""
    _exigir_gestor(usuario)
    if not instalado(cx):
        raise ValueError("Falta correr gomeria/53_estados_y_depositos.sql en Supabase.")
    nombre = _texto(datos.get("nombre"))
    if not nombre:
        raise ValueError("Falta el nombre del depósito.")
    uso = str(datos.get("uso") or "ambos").strip().lower()
    if uso not in USOS:
        raise ValueError("El uso es cubiertas, repuestos o ambos.")
    try:
        orden = int(datos.get("orden") or 50)
    except (TypeError, ValueError):
        raise ValueError("El orden tiene que ser un número.") from None
    valores = (nombre, uso, _texto(datos.get("direccion"), 300),
               bool(datos.get("activo", True)), orden)

    otro = cx.execute("select id from depositos where lower(nombre) = lower(%s)",
                      (nombre,)).fetchone()
    deposito_id = int(datos.get("id") or 0) or None
    if otro and otro["id"] != deposito_id:
        raise ValueError(f"Ya hay un depósito {nombre}.")

    if deposito_id:
        if not valores[3]:
            _sin_cubiertas(cx, deposito_id, "darlo de baja")
        fila = cx.execute("""update depositos
                             set nombre=%s, uso=%s, direccion=%s, activo=%s, orden=%s
                             where id=%s returning id""",
                          (*valores, deposito_id)).fetchone()
        if not fila:
            raise ValueError("Ese depósito no existe.")
        return {"ok": True, "id": deposito_id}

    fila = cx.execute("""
        insert into depositos (nombre, uso, direccion, activo, orden)
        values (%s,%s,%s,%s,%s) returning id""", valores).fetchone()
    return {"ok": True, "id": fila["id"]}


def _sin_cubiertas(cx, deposito_id, que):
    n = cx.execute("""select count(*) as n from cubiertas
                      where deposito_id = %s and estado = 'stock'""",
                   (deposito_id,)).fetchone()["n"]
    if n:
        raise ValueError(f"Hay {n} cubierta(s) en ese depósito. Pasarlas a otro "
                         f"antes de {que}.")


def borrar(cx, datos, usuario=None):
    _exigir_gestor(usuario)
    deposito_id = int(datos.get("id") or 0)
    _sin_cubiertas(cx, deposito_id, "borrarlo")
    usadas = cx.execute("select count(*) as n from cubiertas where deposito_id = %s",
                        (deposito_id,)).fetchone()["n"]
    if usadas:
        raise ValueError("Ese depósito figura en cubiertas montadas o de baja. "
                         "Darlo de baja en lugar de borrarlo.")
    cx.execute("delete from depositos where id = %s", (deposito_id,))
    return {"ok": True}

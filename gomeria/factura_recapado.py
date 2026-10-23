"""De la factura del recapador a las gomas que volvieron.

El recapador factura por goma, con el número de fuego grabado en cada
renglón. Eso es lo que hace que esto se pueda verificar: no hay que
creerle al modelo, porque lo que leyó se cruza contra lo que el sistema
sabe que mandó.

    · fuego que está en la factura y en un envío abierto → volvió
    · fuego en la factura que no salió nunca            → algo está mal
    · fuego que salió y no está en la factura           → ésa no volvió

El último es el que importa y el que no existía. Si se mandaron doce y la
factura trae diez, las dos que faltan quedan señaladas.

Se le pasa la lista de números de fuego que están afuera, igual que a la
factura de servicios se le pasan las patentes. Sin eso, un 4521 grabado a
fuego y después fotografiado sale 4S21 una de cada tres veces; con la
lista, el modelo elige entre los que existen.
"""
import lector

HERRAMIENTA = {
    "name": "cargar_recapados",
    "description": "Los renglones de una factura de recapado: qué cubierta se "
                   "recapó y cuánto salió cada una.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "factura": {
                "type": ["string", "null"],
                "description": "Número de comprobante completo, como figura: "
                               "'0001-00012345'."
            },
            "fecha": {
                "type": ["string", "null"],
                "description": "Fecha de la factura en AAAA-MM-DD."
            },
            "renglones": {
                "type": "array",
                "description": "Un elemento por cubierta facturada. Si un "
                               "renglón dice cantidad 2 con un solo número de "
                               "fuego, es un renglón.",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "codigo_fuego": {
                            "type": ["string", "null"],
                            "description": "El número de fuego de la empresa: "
                                           "el número que va pegado a la marca "
                                           "('MICHELIN 457' → '457', 'OTRAS 020' "
                                           "→ '020'). No es el número propio del "
                                           "recapador que abre el renglón. Si el "
                                           "renglón no lo trae, null."
                        },
                        "numero_recapador": {
                            "type": ["string", "null"],
                            "description": "El número interno del recapador, el "
                                           "que abre el renglón ('34581'), si lo hay."
                        },
                        "marca": {
                            "type": ["string", "null"],
                            "description": "La marca de la carcasa: 'MICHELIN', "
                                           "'FATE', 'OTRAS'."
                        },
                        "trabajo": {
                            "type": "string",
                            "enum": ["recapado", "reparacion", "otro"],
                            "description": "recapado: banda nueva (PREC., "
                                           "recapado, banda). reparacion: "
                                           "vulcanizado, hombro, parche sobre una "
                                           "cubierta identificada. otro: un "
                                           "insumo o cargo sin cubierta."
                        },
                        "detalle": {
                            "type": ["string", "null"],
                            "description": "La descripción del renglón, tal cual."
                        },
                        "costo": {
                            "type": ["number", "null"],
                            "description": "Lo que salió recapar esa cubierta, "
                                           "sin IVA. Si la factura trae un total "
                                           "por renglón y una cantidad, el costo "
                                           "es el unitario."
                        },
                        "banda": {
                            "type": ["string", "null"],
                            "description": "La banda o dibujo que le pusieron, si "
                                           "el renglón lo dice: 'BDR-HT', 'R250'."
                        },
                    },
                    "required": ["codigo_fuego", "numero_recapador", "marca",
                                 "trabajo", "detalle", "costo", "banda"],
                },
            },
            "dudas": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Lo que no se pudo leer con seguridad. Una frase "
                               "por cosa, en castellano."
            },
        },
        "required": ["factura", "fecha", "renglones", "dudas"],
    },
}


def _instrucciones(codigos):
    lista = ", ".join(codigos[:400]) if codigos else "(no hay ninguna afuera)"
    return (
        "Leés facturas de recapado de una empresa de transporte argentina.\n\n"
        "El recapador factura por cubierta: cada renglón es una goma con lo "
        "que salió el trabajo. Un renglón típico es:\n"
        "  34581 MICHELIN 457 PREC.RAD. B440 BANDAG 295.80X22.5\n"
        "· 34581 es el número interno del recapador: NO es el fuego.\n"
        "· MICHELIN es la marca de la carcasa.\n"
        "· 457, el número pegado a la marca, es el número de fuego de la "
        "empresa: ése va en codigo_fuego, tal cual (con sus ceros: '020').\n"
        "· El resto es el trabajo: PREC./BANDAG/banda es un recapado; "
        "HOMBRO, VULCANIZADO o PARCHE sobre una cubierta es una reparación. "
        "Un renglón sin marca ni número (un parche suelto) va con "
        "codigo_fuego null y trabajo 'otro'.\n\n"
        "Estos son los números de fuego de las cubiertas que la empresa "
        "mandó a recapar y todavía no volvieron:\n"
        f"{lista}\n\n"
        "Si el número leído es casi igual a uno de la lista (un 5 por una "
        "S, un 0 por una O), usá el de la lista. Si no se parece a ninguno, "
        "escribí el número tal cual figura en la factura: no lo cambies "
        "por uno de la lista. El sistema lo cruza después.\n\n"
        "El costo es sin IVA y por cubierta. Si el renglón trae cantidad y "
        "total, dividí. Si la factura trae un único total para todo, dejá "
        "los costos en null y anotalo en dudas: no inventes un prorrateo.\n\n"
        "Lo que no se lee con seguridad va en dudas, en frases cortas. No "
        "anotes en dudas lo que ya está claro en los campos (que un renglón "
        "es una reparación, o que la suma cierra): solo lo dudoso."
    )


def leer(archivos, codigos_afuera=None, cliente=None):
    """Lo que dice la factura. No toca la base ni decide nada."""
    contenido = lector.preparar(archivos)
    leido = lector.preguntar(
        contenido, HERRAMIENTA, _instrucciones(list(codigos_afuera or [])),
        "Leé esta factura de recapado y cargá sus renglones.",
        cliente=cliente, max_tokens=8000)

    renglones = []
    for r in (leido.get("renglones") or []):
        codigo = " ".join(str(r.get("codigo_fuego") or "").split()).upper()
        limpio = lambda k: " ".join(str(r.get(k) or "").split()) or None
        trabajo = r.get("trabajo") if r.get("trabajo") in (
            "recapado", "reparacion", "otro") else "recapado"
        renglones.append({"codigo_fuego": codigo or None,
                          "numero_recapador": limpio("numero_recapador"),
                          "marca": (limpio("marca") or "").upper() or None,
                          "trabajo": trabajo,
                          "detalle": limpio("detalle"),
                          "costo": lector.numero(r.get("costo")),
                          "banda": (r.get("banda") or "").strip().upper() or None})
    leido["renglones"] = renglones
    leido["dudas"] = [str(d) for d in (leido.get("dudas") or []) if d]
    return leido

"""El contrato entre órdenes, reparaciones externas y el último service."""
import sys
import unittest
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "gomeria"))
import alertas
import ordenes


class Resultado:
    def __init__(self, una=None, muchas=None):
        self.una = una
        self.muchas = muchas or []

    def fetchone(self):
        return self.una

    def fetchall(self):
        return self.muchas


class BaseFalsa:
    def __init__(self, orden=None):
        self.orden = orden
        self.consultas = []

    def rollback(self):
        pass

    def execute(self, consulta, valores=()):
        sql = " ".join(consulta.split())
        self.consultas.append((sql, valores))
        if sql.startswith("select pg_advisory_xact_lock"):
            return Resultado()
        # Sin el módulo de solicitudes instalado no se le exige solicitud a nadie:
        # estas pruebas miran el enganche con el service, no el circuito.
        if sql.startswith("select to_regclass('public.solicitudes_ajustes')"):
            return Resultado({"t": "solicitudes_ajustes"})
        if sql.startswith("select exigir_solicitud from solicitudes_ajustes"):
            return Resultado({"exigir_solicitud": False})
        if sql.startswith("select * from ordenes_trabajo where id"):
            return Resultado(self.orden)
        if "select 1 from ordenes_tareas" in sql:
            return Resultado({"hay": 1})
        if sql.startswith("select * from unidades where id"):
            return Resultado({"id": 7, "patente": "AD247MQ", "chofer": "Ana",
                              "km_actual": 120000})
        if sql.startswith("select numero from ordenes_trabajo"):
            return Resultado(None)
        if sql.startswith("insert into ordenes_trabajo"):
            return Resultado({"id": 41, "numero": 82})
        if sql.startswith(("update", "delete")):
            return Resultado()
        raise AssertionError(f"Consulta inesperada: {sql}")


class BaseService:
    def __init__(self, con_plan=True):
        self.consultas = []
        self.con_plan = con_plan

    def execute(self, consulta, valores=()):
        sql = " ".join(consulta.split())
        self.consultas.append((sql, valores))
        if sql.startswith("select id, patente, km_actual from unidades"):
            return Resultado({"id": 7, "patente": "AD247MQ", "km_actual": 123000})
        if sql.startswith("select p.cada_km from unidades"):
            return Resultado({"cada_km": 20000} if self.con_plan else None)
        if sql.startswith("select fecha, km from odometros"):
            # Lo que marcaba el satelital ese día. Acá, menos que el km del
            # service: la carga es buena y tiene que entrar.
            return Resultado({"fecha": date(2026, 9, 1), "km": 120000})
        if sql.startswith("select id from services where orden_id"):
            return Resultado(None)
        if sql.startswith("insert into services"):
            return Resultado({"id": 19})
        if sql.startswith("delete from alertas_silenciadas"):
            return Resultado()
        raise AssertionError(f"Consulta inesperada: {sql}")


GESTOR = {"id": 2, "nombre": "Nicolás", "rol": "admin"}


class CamposObligatorios(unittest.TestCase):
    def test_clase_fecha_y_km_son_obligatorios(self):
        validos = {"unidad_id": 7, "mantenimiento": "preventivo",
                   "fecha": "2026-09-09", "km": 123000}
        for campo in ("mantenimiento", "fecha", "km"):
            datos = dict(validos)
            datos[campo] = ""
            with self.subTest(campo=campo), self.assertRaises(ValueError):
                ordenes.abrir(BaseFalsa(), datos, GESTOR)


class OrdenInterna(unittest.TestCase):
    def test_al_abrir_guarda_la_clasificacion(self):
        cx = BaseFalsa()
        salida = ordenes.abrir(cx, {
            "unidad_id": 7, "mantenimiento": "preventivo",
            "fecha": "2026-09-09", "km": 123000,
            "solicitado": "Cambio de aceite y filtros",
        }, GESTOR)
        self.assertEqual(salida["id"], 41)
        insercion = next(x for x in cx.consultas if x[0].startswith("insert into"))
        self.assertEqual(insercion[1][0], "preventivo")

    def test_al_cerrar_un_preventivo_no_registra_service(self):
        """Los services se cargan solo desde el módulo de services."""
        orden = {"id": 41, "numero": 82, "tipo": "interna", "estado": "abierta",
                 "mantenimiento": "preventivo", "unidad_id": 7,
                 "patente": "AD247MQ", "fecha": date(2026, 9, 9), "km": 123000,
                 "solicitado": "Cambio de aceite", "diagnostico": None, "taller": None}
        cx = BaseFalsa(orden)
        salida = ordenes.cerrar(cx, {"id": 41}, GESTOR)
        self.assertNotIn("service_id", salida)
        self.assertFalse(any("services" in sql for sql, _ in cx.consultas))


class BaseExterna(BaseFalsa):
    """La carga de la externa más el registro de su service."""

    def execute(self, consulta, valores=()):
        sql = " ".join(consulta.split())
        if sql.startswith("select id, patente, km_actual from unidades"):
            self.consultas.append((sql, valores))
            return Resultado({"id": 7, "patente": "AD247MQ", "km_actual": 123000})
        if sql.startswith("select p.cada_km from unidades"):
            self.consultas.append((sql, valores))
            return Resultado({"cada_km": 20000})
        if sql.startswith("select fecha, km from odometros"):
            self.consultas.append((sql, valores))
            return Resultado({"fecha": date(2026, 9, 1), "km": 120000})
        if sql.startswith("select id from services where orden_id"):
            self.consultas.append((sql, valores))
            return Resultado(None)
        if sql.startswith("insert into services"):
            self.consultas.append((sql, valores))
            return Resultado({"id": 19})
        if sql.startswith("delete from alertas_silenciadas"):
            self.consultas.append((sql, valores))
            return Resultado()
        return super().execute(consulta, valores)


EXTERNA = {"unidad_id": 7, "gestion": "mantenimiento",
           "fecha": "2026-09-08", "km": 122500,
           "factura": "A-123", "monto": 250000,
           "taller": "Iveco", "solicitado": "Service M6"}


class ServicioExterno(unittest.TestCase):
    def test_un_preventivo_registra_el_service_atado_a_la_orden(self):
        cx = BaseExterna()
        salida = ordenes.externa(cx, {**EXTERNA, "mantenimiento": "preventivo"}, GESTOR)
        self.assertEqual(salida["id"], 41)
        self.assertEqual(salida["service_id"], 19)
        insercion = next(x for x in cx.consultas if x[0].startswith("insert into ordenes_trabajo"))
        self.assertIn("'cerrada'", insercion[0])
        service = next(x for x in cx.consultas if x[0].startswith("insert into services"))
        self.assertEqual(service[1][1], "2026-09-08")
        self.assertEqual(service[1][2], 122500)
        self.assertEqual(service[1][-1], 41)

    def test_un_correctivo_no_toca_los_services(self):
        cx = BaseExterna()
        salida = ordenes.externa(cx, {**EXTERNA, "mantenimiento": "correctivo"}, GESTOR)
        self.assertNotIn("service_id", salida)
        self.assertFalse(any("services" in sql for sql, _ in cx.consultas))

    def test_anular_la_externa_borra_su_service(self):
        orden = {"id": 41, "numero": 82, "tipo": "externa", "estado": "cerrada",
                 "mantenimiento": "preventivo", "unidad_id": 7}
        cx = BaseFalsa(orden)
        original = cx.execute

        def execute(consulta, valores=()):
            sql = " ".join(consulta.split())
            if sql.startswith("select movimiento_id from ordenes_repuestos"):
                cx.consultas.append((sql, valores))
                return Resultado(muchas=[])
            return original(consulta, valores)
        cx.execute = execute
        ordenes.anular(cx, {"id": 41}, GESTOR)
        self.assertIn(("delete from services where orden_id = %s", (41,)), cx.consultas)


class ServiceCreaOrden(unittest.TestCase):
    """Registrar un service desde su módulo deja una orden preventiva cerrada."""

    def _base(self):
        cx = BaseService()
        original = cx.execute

        def execute(consulta, valores=()):
            sql = " ".join(consulta.split())
            if sql.startswith("insert into ordenes_trabajo"):
                cx.consultas.append((sql, valores))
                return Resultado({"id": 55})
            if sql.startswith("update services set orden_id"):
                cx.consultas.append((sql, valores))
                return Resultado()
            return original(consulta, valores)
        cx.execute = execute
        return cx

    def test_el_service_crea_su_orden_y_queda_vinculado(self):
        cx = self._base()
        service_id = alertas.guardar_service(cx, {
            "unidad_id": 7, "fecha": "2026-09-09", "km": 123000, "tipo": "M6",
        }, usuario="Nicolás", crear_orden=True)
        self.assertEqual(service_id, 19)
        orden = next(x for x in cx.consultas if x[0].startswith("insert into ordenes_trabajo"))
        self.assertIn("'preventivo'", orden[0])
        self.assertIn("'cerrada'", orden[0])
        self.assertEqual(orden[1][1], "AD247MQ")
        self.assertIn(("update services set orden_id = %s where id = %s", (55, 19)), cx.consultas)

    def test_sin_el_pedido_no_crea_orden(self):
        """La solicitud preventiva cerrada registra service pero no orden:
        su orden es la externa con la que se rinde la factura."""
        cx = self._base()
        alertas.guardar_service(cx, {"unidad_id": 7, "fecha": "2026-09-09", "km": 123000})
        self.assertFalse(any(sql.startswith("insert into ordenes_trabajo") for sql, _ in cx.consultas))

    def test_sin_plan_no_hay_ni_service_ni_orden(self):
        cx = BaseService(con_plan=False)
        with self.assertRaisesRegex(ValueError, "no tiene un plan"):
            alertas.guardar_service(cx, {"unidad_id": 7, "km": 123000}, crear_orden=True)
        self.assertFalse(any(sql.startswith("insert") for sql, _ in cx.consultas))


if __name__ == "__main__":
    unittest.main()

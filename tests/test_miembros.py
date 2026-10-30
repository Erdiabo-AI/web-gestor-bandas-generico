"""Miembros: devolución al bajar coste, nota de muerte, eliminar, duplicar, Excel y PDF."""
import sys
from io import BytesIO

from openpyxl import load_workbook

from _comun import app, cur, ok, one, txt, cliente, limpiar, resultado
from app.helpers import ahora_es

try:
    c = cliente("Nov", adm=True)
    c.post("/admin/reglamentos/guardar", data={"descripcion": "Mordheim NOV", "anyo": "1999", "version": "1",
           "stats": '{"m": 4, "ha": 4, "hp": 3}'})
    c.post("/gestion-campanas/crear", data={"nombre": "Campaña NOV E2E", "tesoreria_inicial": "500",
           "regla_id": str(one("SELECT regla_id FROM reglas WHERE regla_descripcion='Mordheim NOV'"))})
    cid = str(one("SELECT campana_id FROM campanas WHERE campana_nombre='Campaña NOV E2E'"))
    c.post("/banda/nueva", data={"nombre": "Banda NOV", "tipo": "Reikland", "campana_id": cid})
    bid = str(one("SELECT banda_id FROM bandas WHERE campana_id=%s", cid))
    tes = lambda: one("SELECT banda_tesoreria FROM bandas WHERE banda_id=%s", bid)
    valor = lambda: one("SELECT banda_valor_banda FROM bandas WHERE banda_id=%s", bid)
    hist = lambda: one("SELECT banda_audit FROM bandas WHERE banda_id=%s", bid)
    base = {"orden": "1", "nombre": "Manolo", "subtipo": "Capitán", "categoria": "Héroe", "cantidad": "1",
            "precio": "60", "stat_0": "4", "stat_1": "4", "stat_2": "3", "notas": "Líder valiente"}
    c.post(f"/banda/{bid}/contratar", data={**base, "arm_nombre": ["Maza", "Rodela", "Daga"], "arm_precio": ["3", "10", "0"]})
    lid = str(one("SELECT banda_lin_id FROM bandas_lin WHERE banda_id=%s", bid))
    ok(tes() == 427 and valor() == 73, "Contratar 73 → tesorería 427")

    c.post(f"/banda/{bid}/miembro/{lid}/editar", data={**base, "estado": "0", "arm_nombre": ["Maza", "Daga"], "arm_precio": ["3", "0"]})
    ok(tes() == 437 and valor() == 63 and "devolución 10 · tesorería 427 → 437" in hist(), "Quitar Rodela → devuelve 10")
    c.post(f"/banda/{bid}/miembro/{lid}/editar", data={**base, "estado": "0", "arm_nombre": ["Maza", "Daga", "Espada"], "arm_precio": ["3", "0", "10"]})
    ok(tes() == 427, "Comprar Espada → cobra 10")
    c.post(f"/banda/{bid}/miembro/{lid}/editar", data={**base, "estado": "1", "arm_nombre": ["Maza", "Daga", "Espada"], "arm_precio": ["3", "0", "10"]})
    ok(tes() == 427 and valor() == 73, "Lesionado: sin dinero, sigue contando")
    c.post(f"/banda/{bid}/miembro/{lid}/editar", data={**base, "estado": "3", "arm_nombre": ["Maza", "Daga", "Espada"], "arm_precio": ["3", "0", "10"]})
    fecha = f"{ahora_es():%d/%m/%y}"
    ok(one("SELECT banda_lin_notas FROM bandas_lin WHERE banda_lin_id=%s", lid) == f"Muerto: {fecha}"
       and "(notas anteriores: «Líder valiente»)" in hist(), f"Muerto → «Muerto: {fecha}», notas antiguas al historial")
    ok(tes() == 427 and valor() == 0, "Muerto: sin devolución y fuera del coste")

    pag = txt(c.get(f"/banda/{bid}"))
    ok("Duplicar" in pag and "Exportar Excel" in pag and "Eliminar miembro" in pag and "Despedir" not in pag,
       "Ficha: Duplicar, Excel, Eliminar; sin Despedir")
    c.post(f"/banda/{bid}/contratar", data={**base, "nombre": "Manolo (copia)", "orden": "2", "notas": "",
           "arm_nombre": ["Maza", "Daga"], "arm_precio": ["3", "0"]})
    ok(tes() == 364, "Duplicado contratado: cobra 63")
    lc = str(one("SELECT banda_lin_id FROM bandas_lin WHERE banda_lin_nombre='Manolo (copia)' AND banda_id=%s", bid))
    c.post(f"/banda/{bid}/miembro/{lc}/eliminar")
    ok(one("SELECT count(*) FROM bandas_lin WHERE banda_lin_id=%s", lc) == 0 and tes() == 364 and valor() == 0,
       "Eliminar: sin devolución, coste recalculado")
    ok(cliente("Otro").post(f"/banda/{bid}/miembro/{lid}/eliminar").status_code == 403, "Otro usuario no elimina")

    r = c.get(f"/banda/{bid}/excel")
    ws = load_workbook(BytesIO(r.data)).active
    celdas = [str(x.value) for fila in ws.iter_rows() for x in fila if x.value is not None]
    ok(r.status_code == 200 and ws["A1"].value == "Banda NOV" and "Categoría" in celdas
       and not any("Crea la banda" in v for v in celdas), "Excel con datos y sin historial")
    r = c.get(f"/banda/{bid}/pdf")
    ok(r.status_code == 200 and r.data[:5] == b"%PDF-", "PDF generado")
finally:
    limpiar("NOV E2E", "Mordheim NOV")
sys.exit(resultado())

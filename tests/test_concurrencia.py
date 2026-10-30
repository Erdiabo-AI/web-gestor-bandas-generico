"""Doble clic y peticiones simultáneas: un solo cargo, tesorería exacta, categoría."""
import sys
import threading

from _comun import app, cur, ok, one, txt, cliente, limpiar, resultado, DOM, CLAVE


def a_la_vez(n, fn):
    """Lanza n peticiones en paralelo, soltándolas todas en el mismo instante."""
    barrera, res = threading.Barrier(n), []

    def tarea(i):
        c = app.test_client()
        c.post("/login", data={"email": "conc" + DOM, "password": CLAVE})
        barrera.wait()
        res.append(fn(c, i).status_code)
    hilos = [threading.Thread(target=tarea, args=(i,)) for i in range(n)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    return res


try:
    c = cliente("Conc", adm=True)
    c.post("/admin/reglamentos/guardar", data={"descripcion": "Mordheim CONC", "anyo": "1999", "version": "1",
           "stats": '{"m": 4, "ha": 4}'})
    c.post("/gestion-campanas/crear", data={"nombre": "Campaña CONC E2E", "tesoreria_inicial": "500",
           "regla_id": str(one("SELECT regla_id FROM reglas WHERE regla_descripcion='Mordheim CONC'"))})
    cid = str(one("SELECT campana_id FROM campanas WHERE campana_nombre='Campaña CONC E2E'"))
    c.post("/banda/nueva", data={"nombre": "Banda CONC", "tipo": "X", "campana_id": cid})
    bid = str(one("SELECT banda_id FROM bandas WHERE campana_id=%s", cid))
    tes = lambda: one("SELECT banda_tesoreria FROM bandas WHERE banda_id=%s", bid)
    hist = lambda: one("SELECT banda_audit FROM bandas WHERE banda_id=%s", bid)

    c.post(f"/banda/{bid}/contratar", data={"orden": "1", "nombre": "Klaus", "subtipo": "Capitán", "categoria": "Héroe",
           "cantidad": "1", "precio": "60", "stat_0": "4", "stat_1": "4"})
    lid = str(one("SELECT banda_lin_id FROM bandas_lin WHERE banda_id=%s", bid))
    ok(one("SELECT banda_lin_categoria FROM bandas_lin WHERE banda_lin_id=%s", lid) == "Héroe" and tes() == 440,
       "Categoría guardada; contratar 60 → 440")
    pag = txt(c.get(f"/banda/{bid}"))
    ok(">Categoría<" in pag and "<td>Héroe</td>" in pag and 'value="Secuaz"' in pag, "Ficha: columna y sugerencias de categoría")
    base = {"orden": "1", "nombre": "Klaus", "subtipo": "Capitán", "cantidad": "1", "precio": "60",
            "stat_0": "4", "stat_1": "4", "estado": "0"}
    c.post(f"/banda/{bid}/miembro/{lid}/editar", data={**base, "categoria": "Líder"})
    ok("categoría Héroe → Líder" in hist(), "Cambio de categoría en el historial")

    datos = {**base, "categoria": "Líder", "arm_nombre": ["Espada"], "arm_precio": ["10"]}
    a_la_vez(2, lambda cl, i: cl.post(f"/banda/{bid}/miembro/{lid}/editar", data=datos))
    ok(tes() == 430 and hist().count("cargo 10") == 1, "Doble clic comprando Espada (10) → un solo cargo (430)")

    estados = a_la_vez(5, lambda cl, i: cl.post(f"/banda/{bid}/contratar", data={
        "orden": str(10 + i), "nombre": f"Secuaz {i}", "subtipo": "Secuaz", "cantidad": "1", "precio": "20"}))
    ok(estados == [302] * 5 and tes() == 330, "Cinco contrataciones simultáneas → tesorería exacta (330)")
    ok(one("SELECT banda_valor_banda FROM bandas WHERE banda_id=%s", bid) == 170, "Valor exacto (170)")
    tramos = sorted(l.split("tesorería ")[1] for l in hist().splitlines() if "Contrata «Secuaz" in l)
    ok(tramos == ["350 → 330", "370 → 350", "390 → 370", "410 → 390", "430 → 410"], "Historial encadenado sin saltos")

    lid2 = str(one("SELECT banda_lin_id FROM bandas_lin WHERE banda_lin_nombre='Secuaz 0' AND banda_id=%s", bid))
    a_la_vez(2, lambda cl, i: cl.post(f"/banda/{bid}/miembro/{lid2}/eliminar"))
    ok(hist().count("Elimina «Secuaz 0»") == 1, "Doble clic eliminando → una sola línea en el historial")
finally:
    limpiar("CONC E2E", "Mordheim CONC")
sys.exit(resultado())

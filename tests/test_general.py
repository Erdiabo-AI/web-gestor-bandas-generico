"""Prueba de punta a punta: reglamentos, campañas, bandas, miembros, comisario,
batallas, estadísticas, mensajes, suplente y administración."""
import json
import re
import sys

from _comun import app, cur, ok, one, txt, cliente, limpiar, resultado, DOM

try:
    A = cliente("Admin", adm=True)
    G, P1, P2 = cliente("Gestor"), cliente("Jugador1"), cliente("Jugador2")
    uid = lambda n: str(one("SELECT usuario_id FROM usuarios WHERE usuario_email=%s", n.lower() + DOM))

    # --- Reglamentos
    r = A.post("/admin/reglamentos/guardar", data={"descripcion": "Mordheim E2E", "anyo": "1999", "version": "1.0",
               "stats": "{mal json"}, follow_redirects=True)
    ok("no es válido" in txt(r) and one("SELECT count(*) FROM reglas WHERE regla_descripcion='Mordheim E2E'") == 0,
       "JSON de stats inválido rechazado")
    A.post("/admin/reglamentos/guardar", data={"descripcion": "Mordheim E2E", "anyo": "1999", "version": "1.0",
           "stats": '{"m": 4, "ha": 4, "hp": 3, "f": 3, "r": 3, "h": 1, "i": 4, "a": 1, "l": 7}'})
    A.post("/admin/reglamentos/guardar", data={"descripcion": "Battlefleet E2E", "anyo": "1999", "version": "2",
           "stats": '{"velocidad": 20, "giros": "45°", "blindaje": 5}'})
    rid = str(one("SELECT regla_id FROM reglas WHERE regla_descripcion='Mordheim E2E'"))
    rid_bf = str(one("SELECT regla_id FROM reglas WHERE regla_descripcion='Battlefleet E2E'"))
    ok(P1.get("/admin/reglamentos").status_code == 403, "Reglamentos solo ADM")

    # --- Campañas
    G.post("/gestion-campanas/crear", data={"nombre": "Campaña E2E", "tesoreria_inicial": "500", "temporada": "2026", "regla_id": rid})
    cid = str(one("SELECT campana_id FROM campanas WHERE campana_nombre='Campaña E2E'"))
    ok(one("SELECT campana_estado||'/'||campana_formato||'/'||campana_tesoreria_inicial FROM campanas WHERE campana_id=%s", cid)
       == "INSCRIPCION/LIBRE/500", "Campaña creada: Inscripción, LIBRE, tesorería 500")
    G.post("/gestion-campanas/crear", data={"nombre": "Flota E2E", "tesoreria_inicial": "1000", "regla_id": rid_bf})
    cid_bf = str(one("SELECT campana_id FROM campanas WHERE campana_nombre='Flota E2E'"))

    # --- Banda
    ok("Campaña E2E" in txt(P1.get("/banda/nueva")), "Nueva banda ofrece campaña en Inscripción")
    P1.post("/banda/nueva", data={"nombre": "Lobos E2E", "tipo": "Reikland", "campana_id": cid})
    bid = str(one("SELECT banda_id FROM bandas WHERE banda_nombre='Lobos E2E'"))
    tes = lambda b=None: one("SELECT banda_tesoreria FROM bandas WHERE banda_id=%s", b or bid)
    ok(tes() == 500, "Banda creada con tesorería inicial 500")
    P1.post("/banda/nueva", data={"nombre": "Otra E2E", "tipo": "X", "campana_id": cid})
    ok(one("SELECT count(*) FROM bandas WHERE banda_nombre='Otra E2E'") == 0, "No se crea segunda banda activa")

    # --- Miembros
    stats = {f"stat_{i}": v for i, v in enumerate(["4", "4", "4", "3", "3", "1", "4", "1", "8"])}
    P1.post(f"/banda/{bid}/contratar", data={"orden": "1", "nombre": "Klaus", "subtipo": "Capitán", "cantidad": "1",
            "precio": "35", **stats, "arm_nombre": ["Espada", "Daga", "Daga"], "arm_precio": ["10", "2", "2"], "experiencia": "20"})
    ok(one("SELECT banda_lin_coste FROM bandas_lin WHERE banda_lin_nombre='Klaus'") == 49 and tes() == 451,
       "Contratar 35 + armamento 14 = 49 → tesorería 451")
    P1.post(f"/banda/{bid}/contratar", data={"orden": "2", "nombre": "Espadachines", "subtipo": "Secuaz", "cantidad": "3",
            "precio": "25", "arm_nombre": ["Daga"], "arm_precio": ["2"]})
    ok(one("SELECT banda_tesoreria||'/'||banda_valor_banda FROM bandas WHERE banda_id=%s", bid) == "370/130",
       "Grupo ×3 de 27 → tesorería 370, valor 130")
    lid = str(one("SELECT banda_lin_id FROM bandas_lin WHERE banda_lin_nombre='Klaus'"))
    P1.post(f"/banda/{bid}/miembro/{lid}/editar", data={"orden": "1", "nombre": "Klaus", "subtipo": "Capitán", "cantidad": "1",
            "precio": "35", **stats, "arm_nombre": ["Espada", "Daga", "Daga", "Escudo"], "arm_precio": ["10", "2", "2", "5"],
            "experiencia": "25", "estado": "1"})
    hist = one("SELECT banda_audit FROM bandas WHERE banda_id=%s", bid)
    ok(tes() == 365 and "compra Escudo" in hist and "cargo 5" in hist, "Comprar Escudo (5) → 365, en el historial")
    P1.post(f"/banda/{bid}/editar", data={"nombre": "Lobos E2E", "tipo": "Reikland", "tesoreria": "400", "estado": "1"})
    ok(tes() == 400 and "(edición manual)" in one("SELECT banda_audit FROM bandas WHERE banda_id=%s", bid),
       "Tesorería editable y anotada")
    ok(P2.post(f"/banda/{bid}/editar", data={"tesoreria": "9999"}).status_code == 403, "Otro jugador no edita la banda")
    ok(G.post(f"/banda/{bid}/editar", data={"tesoreria": "9999"}).status_code == 403, "Gestor sin modo comisario no edita")
    lid2 = str(one("SELECT banda_lin_id FROM bandas_lin WHERE banda_lin_nombre='Espadachines'"))
    P1.post(f"/banda/{bid}/miembro/{lid2}/editar", data={"orden": "2", "nombre": "Espadachines", "subtipo": "Secuaz",
            "cantidad": "3", "precio": "25", "arm_nombre": ["Daga"], "arm_precio": ["2"], "estado": "2"})
    ok(one("SELECT banda_valor_banda FROM bandas WHERE banda_id=%s", bid) == 54 and tes() == 400,
       "Pasar a Despedido desde editar → valor 54, sin mover dinero")
    pag = txt(P1.get(f"/banda/{bid}"))
    cols = re.findall(r'<th class="col-stat">([^<]+)</th>', pag)[:9]
    ok("Bajas (1)" in pag and cols == ["M", "HA", "HP", "F", "R", "H", "I", "A", "L"], f"Ficha: bajas y stats en orden {cols}")

    # --- Comisario
    G.post(f"/gestion-campanas/{cid}/estado", data={"estado": "ABIERTA"})
    ok(one("SELECT campana_estado FROM campanas WHERE campana_id=%s", cid) == "ABIERTA", "Gestor cambia estado a Abierta")
    ok(P1.post(f"/gestion-campanas/{cid}/estado", data={"estado": "CERRADA"}).status_code == 403, "Jugador no cambia estado")
    G.post(f"/gestion-campanas/{cid}/comisario", data={"activar": "1"})
    r = G.post(f"/banda/{bid}/editar", data={"nombre": "Lobos E2E", "tipo": "Reikland", "tesoreria": "410", "estado": "1"})
    ok("Modo comisario" in txt(G.get("/perfil")) and tes() == 410, "Gestor en modo comisario edita")
    ok(P1.post(f"/gestion-campanas/{cid}/comisario", data={"activar": "1"}).status_code == 403, "Jugador no activa comisario")

    # --- Batallas
    P2.post("/banda/nueva", data={"nombre": "Skaven E2E", "tipo": "Clan Eshin", "campana_id": cid})
    bid2 = str(one("SELECT banda_id FROM bandas WHERE banda_nombre='Skaven E2E'"))
    r = P1.post(f"/campana/{cid}/batallas/crear")
    btid = str(one("SELECT batalla_id FROM batallas WHERE campana_id=%s", cid))
    ok("/acta" in r.location and one("SELECT count(*) FROM batallas_bandas WHERE batalla_id=%s", btid) == 1,
       "Crear batalla vincula la banda propia")
    P1.post(f"/batalla/{btid}/acta", data={"accion": "anadir", "banda_id": bid2, "fecha": "2026-10-18", "escenario": "Escaramuza"})
    cur.execute("SELECT banda_id::text, batalla_banda_id::text FROM batallas_bandas WHERE batalla_id=%s", (btid,))
    bbs = dict(cur.fetchall())
    k1, k2 = bbs[bid], bbs[bid2]
    conf = {"fecha": "2026-10-18", "escenario": "Escaramuza", f"ganancias_{k1}": "60", f"ganador_{k1}": "1",
            f"bajas_{k1}": "Hans (lisiado)", f"ganancias_{k2}": "20"}
    P1.post(f"/batalla/{btid}/acta", data={"accion": "guardar", **conf})
    ok(one("SELECT batalla_ganador FROM batallas WHERE batalla_id=%s", btid) == "Lobos E2E" and tes() == 410,
       "Acta guardada (ganador) y no toca la tesorería")
    P1.post(f"/batalla/{btid}/acta", data={"accion": f"quitar:{k1}", **conf})
    ok(one("SELECT count(*) FROM batallas_bandas WHERE batalla_id=%s", btid) == 2, "Jugador no quita su propia banda")
    P1.post(f"/batalla/{btid}/acta", data={"accion": "confirmar", **conf})
    ok(P1.post(f"/batalla/{btid}/acta", data={"accion": "guardar"}).status_code == 403, "Confirmada: el jugador ya no edita")
    G.post(f"/batalla/{btid}/acta", data={"accion": "reabrir"})
    ok(one("SELECT batalla_estado FROM batallas WHERE batalla_id=%s", btid) == 0, "Comisario reabre")
    G.post(f"/batalla/{btid}/acta", data={"accion": "confirmar", **conf})

    an = app.test_client()
    pag = txt(an.get(f"/campana/{cid}"))
    ok(pag.index("Lobos E2E") < pag.index("Skaven E2E"), "Clasificación por coste")
    ok("Lobos E2E, Skaven E2E" in txt(an.get(f"/campana/{cid}/batallas")), "Batallas con oponentes")
    fila = re.search(r"Lobos E2E</a>.*?</tr>", txt(an.get(f"/campana/{cid}/estadisticas")), re.S).group(0)
    ok(re.findall(r"<td>(\d+)</td>", fila) == ["1", "1", "60", "0"], "Estadísticas: 1 jugada, 1 victoria, 60, 0 bajas")

    # --- Banda destruida → nueva banda
    P1.post(f"/banda/{bid}/editar", data={"nombre": "Lobos E2E", "tipo": "Reikland", "tesoreria": "410", "estado": "2"})
    P1.post("/banda/nueva", data={"nombre": "Lobos II E2E", "tipo": "Reikland", "campana_id": cid})
    ok(one("SELECT count(*) FROM bandas WHERE banda_nombre='Lobos II E2E'") == 1, "Con la banda Destruida crea otra")

    # --- Stats de texto (Battlefleet)
    P1.post("/banda/nueva", data={"nombre": "Flota E2E1", "tipo": "Imperial", "campana_id": cid_bf})
    fb = str(one("SELECT banda_id FROM bandas WHERE banda_nombre='Flota E2E1'"))
    P1.post(f"/banda/{fb}/contratar", data={"orden": "1", "nombre": "Crucero", "subtipo": "Lunar", "cantidad": "1",
            "precio": "180", "stat_0": "20", "stat_1": "90°", "stat_2": "6"})
    ok(one("SELECT banda_lin_stats FROM bandas_lin WHERE banda_lin_nombre='Crucero'") == {"velocidad": 20, "giros": "90°", "blindaje": 6},
       "Stats número/texto según el reglamento")

    # --- Mensajes, suplente, administración
    an.post(f"/campana/{cid}/contactar", data={"nombre": "Visitante", "email": "v" + DOM, "mensaje": "¿Puedo unirme?"})
    ok("¿Puedo unirme?" in txt(G.get(f"/gestion-campanas?campana={cid}")) and "¿Puedo unirme?" not in txt(A.get("/admin/notificaciones")),
       "Mensaje al comisario: lo ve el gestor, no el ADM")
    G.post(f"/gestion-campanas/{cid}/suplente", data={"usuario_id": uid("Jugador2")})
    ok("Acceder como comisario" in txt(P2.get(f"/gestion-campanas?campana={cid}")) and
       P2.post(f"/gestion-campanas/{cid}/suplente", data={"usuario_id": ""}).status_code == 403,
       "Suplente activa comisario pero no cambia el suplente")
    ok("Todos los usuarios" in txt(A.get("/gestion-campanas")) and "Todos los usuarios" not in txt(P1.get("/gestion-campanas")),
       "Bloque 3 solo para ADM")
    A.post(f"/admin/reglamentos/{rid}/borrar")
    ok(one("SELECT count(*) FROM reglas WHERE regla_id=%s", rid) == 1, "No se borra un reglamento en uso")
    ok("batallas_bandas" in txt(A.get("/admin/backup.sql")), "Copia de seguridad completa")
    ok(app.test_client().post("/registro", data={"nombre": "Nuevo", "email": "nuevo" + DOM, "password": "clave-e2e-123"}).location == "/",
       "Registro redirige a Main")
    ok(app.test_client().get("/salud").get_json() == {"estado": "ok"}, "/salud ok")
finally:
    limpiar(" E2E", "% E2E")
    cur.execute("DELETE FROM campanas WHERE campana_nombre IN ('Campaña E2E', 'Flota E2E')")
sys.exit(resultado())

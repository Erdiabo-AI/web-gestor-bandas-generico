"""Disposición de stats en una o dos líneas (ficha y PDF), automática o forzada."""
import json
import sys

from _comun import app, cur, ok, one, cliente, limpiar, resultado

REGLAS = {
    "Aeronautica DL": {"Estructura": 3, "Transporte": 0, "Fuel": 0, "Throtle": 2, "Maniobras": "1-6",
                       "Handling": "3+", "Min.Spd": 2, "Max.Spd": 6, "Max. Alt": 5},
    "Battlefleet DL": {"velocidad": 20, "giros": "45°", "blindaje": 5, "escudos": 2, "torretas": 1,
                       "impactos_totales": 6, "impactos_actuales": 6},
    "Mordheim DL": {"m": 4, "ha": 4, "hp": 3, "f": 3, "r": 3, "h": 1, "i": 4, "a": 1, "l": 7},
}

try:
    c = cliente("DosLineas", adm=True)
    bandas = {}
    for nombre, stats in REGLAS.items():
        c.post("/admin/reglamentos/guardar", data={"descripcion": nombre, "anyo": "2000", "version": "1",
               "stats": json.dumps(stats, ensure_ascii=False), "disposicion": "auto"})
        rid = str(one("select regla_id from reglas where regla_descripcion=%s", nombre))
        c.post("/gestion-campanas/crear", data={"nombre": f"{nombre} E2E", "tesoreria_inicial": "5000", "regla_id": rid})
        cid = str(one("select campana_id from campanas where campana_nombre=%s", f"{nombre} E2E"))
        c.post("/banda/nueva", data={"nombre": f"Banda {nombre}", "tipo": "Prueba", "campana_id": cid})
        bid = str(one("select banda_id from bandas where campana_id=%s", cid))
        bandas[nombre] = (bid, rid)
        n = 16 if nombre == "Aeronautica DL" else 3
        for i in range(n):
            d = {"orden": str(i + 1), "nombre": f"Miembro {i + 1}", "subtipo": "Caza Thunderbolt" if "Aero" in nombre else "Tipo",
                 "categoria": "Escuadrón A" if i % 2 else "Héroe", "cantidad": "1", "precio": "10",
                 "arm_nombre": ["Autocañón pesado", "Misiles Skystrike"], "arm_precio": ["5", "8"],
                 "notas": "Notas de prueba algo largas para ver el ajuste de texto" if i == 0 else ""}
            d.update({f"stat_{k}": str(v) for k, v in enumerate(stats.values())})
            c.post(f"/banda/{bid}/contratar", data=d)

    def ficha(nombre):
        return c.get(f"/banda/{bandas[nombre][0]}").get_data(as_text=True)

    ok("fila-perfil" in ficha("Aeronautica DL") and 'class="perfil-lbl">ESTRUCTURA' in ficha("Aeronautica DL"),
       "Aeronautica (auto) → dos líneas en la ficha, con perfil ESTRUCTURA…")
    ok("fila-perfil" in ficha("Battlefleet DL") and "IMPACTOS TOTALES" in ficha("Battlefleet DL"),
       "Battlefleet (auto) → dos líneas, «IMPACTOS TOTALES» con espacio")
    ok("fila-perfil" not in ficha("Mordheim DL") and '<th class="col-stat">HA</th>' in ficha("Mordheim DL"),
       "Mordheim (auto) → una línea, una columna por stat")
    for nombre in REGLAS:
        r = c.get(f"/banda/{bandas[nombre][0]}/pdf")
        ok(r.status_code == 200 and r.data[:5] == b"%PDF-", f"PDF {nombre} generado")

    # Forzar modos desde Reglamentos
    bid, rid = bandas["Aeronautica DL"]
    c.post("/admin/reglamentos/guardar", data={"regla_id": rid, "descripcion": "Aeronautica DL", "anyo": "2000",
           "version": "1", "stats": json.dumps(REGLAS["Aeronautica DL"], ensure_ascii=False), "disposicion": "una"})
    ok(one("select regla_info->>'disposicion_stats' from reglas where regla_id=%s", rid) == "una"
       and one("select regla_info->'orden_stats'->>0 from reglas where regla_id=%s", rid) == "Estructura",
       "Disposición «una» guardada sin perder el orden de stats")
    ok("fila-perfil" not in ficha("Aeronautica DL"), "Aeronautica forzado a una línea → columnas")
    ok(c.get(f"/banda/{bid}/pdf").status_code == 200, "PDF forzado a una línea se genera")
    bid_m, rid_m = bandas["Mordheim DL"]
    c.post("/admin/reglamentos/guardar", data={"regla_id": rid_m, "descripcion": "Mordheim DL", "anyo": "2000",
           "version": "1", "stats": json.dumps(REGLAS["Mordheim DL"]), "disposicion": "dos"})
    ok("fila-perfil" in ficha("Mordheim DL"), "Mordheim forzado a dos líneas → perfil debajo")
    ok(c.get(f"/banda/{bid_m}/pdf").status_code == 200, "PDF de Mordheim en dos líneas")
    c.post("/admin/reglamentos/guardar", data={"regla_id": rid_m, "descripcion": "Mordheim DL", "anyo": "2000",
           "version": "1", "stats": json.dumps(REGLAS["Mordheim DL"]), "disposicion": "inventado"})
    ok(one("select regla_info->>'disposicion_stats' from reglas where regla_id=%s", rid_m) == "auto", "Valor no válido → «auto»")
    ok('id="r-disposicion"' in c.get("/admin/reglamentos").get_data(as_text=True), "Reglamentos: desplegable de disposición")
    ok(c.get(f"/banda/{bid}/excel").status_code == 200, "Excel sigue generándose (siempre una línea)")
finally:
    limpiar("DL E2E", "% DL")
sys.exit(resultado())

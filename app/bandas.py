"""Bandas: alta, ficha, edición in situ y miembros (bandas_lin).

Reglas de negocio (docs/PENDIENTES.md):
  - Una banda ACTIVA por usuario y campaña; si queda Destruida puede crear otra.
  - Solo en campañas en INSCRIPCION o ABIERTA.
  - Contratar o comprar equipo descuenta de la tesorería; la tesorería sigue
    siendo editable a mano. Toda acción queda en el historial (banda_audit).
  - Coste del miembro = precio base + Σ precios del armamento (por unidad).
"""
from datetime import date

import psycopg2
from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash, abort)
from psycopg2.extras import Json

from . import db
from .helpers import (login_required, puede_editar_banda, columnas_stats, definicion_stats, a_entero,
                      ESTADOS_BANDA, ESTADOS_MIEMBRO, MIEMBRO_EN_PLANTILLA)
from .servicios import anotar_historial, recalcular_valor, historial

bp = Blueprint("bandas", __name__)

CAMPANA_ADMITE_BANDAS = ("INSCRIPCION", "ABIERTA")


def _banda(banda_id):
    b = db.query(
        """
        SELECT b.*, c.campana_nombre, c.campana_estado, c.usuarios_gestor_id,
               c.usuarios_gestor_suplente_id, r.regla_descripcion, r.regla_stats_especificos, r.regla_info,
               u.usuario_id, u.usuario_nombre
        FROM bandas b
        JOIN campanas c ON c.campana_id = b.campana_id
        LEFT JOIN reglas r ON r.regla_id = c.regla_id
        LEFT JOIN campanas_usuarios cu ON cu.campana_usuario_id = b.campana_usuario_id
        LEFT JOIN usuarios u ON u.usuario_id = cu.usuario_id
        WHERE b.banda_id = %s
        """,
        (str(banda_id),), one=True,
    )
    if not b:
        abort(404)
    return b


def _banda_editable(banda_id):
    """Banda que el usuario puede modificar, BLOQUEADA hasta el final de la petición.

    SELECT … FOR UPDATE: si llegan dos peticiones a la vez (doble clic, o jugador y
    comisario), la segunda espera a que la primera confirme y lee los datos ya
    actualizados. Así no se cobra dos veces ni se pisa la tesorería."""
    if db.query("SELECT 1 AS ok FROM bandas WHERE banda_id = %s FOR UPDATE",
                (str(banda_id),), one=True) is None:
        abort(404)
    b = _banda(banda_id)
    if not puede_editar_banda(b, session.get("user")):
        abort(403)
    return b


def _suma_armamento(armamento):
    if not isinstance(armamento, list):
        return 0
    return sum(a_entero(a.get("precio"), 0) for a in armamento if isinstance(a, dict))


def _nombres_armamento(armamento):
    if not isinstance(armamento, list):
        return []
    return [str(a.get("nombre")) for a in armamento if isinstance(a, dict) and a.get("nombre")]


# ---------------------------------------------------------------------------
#  Alta
# ---------------------------------------------------------------------------
def _campanas_disponibles(uid):
    """Campañas en Inscripción/Abierta donde el usuario no tiene banda activa."""
    return db.query(
        """SELECT c.campana_id, c.campana_nombre, c.campana_temporada, c.campana_estado,
                  c.campana_tesoreria_inicial, r.regla_descripcion
           FROM campanas c
           LEFT JOIN reglas r ON r.regla_id = c.regla_id
           WHERE c.campana_estado = ANY(%s)
             AND NOT EXISTS (
                 SELECT 1 FROM bandas b
                 JOIN campanas_usuarios cu ON cu.campana_usuario_id = b.campana_usuario_id
                 WHERE b.campana_id = c.campana_id AND cu.usuario_id = %s AND b.banda_estado = 1)
           ORDER BY c.campana_temporada DESC, c.campana_nombre""",
        (list(CAMPANA_ADMITE_BANDAS), uid))


@bp.route("/banda/nueva", methods=["GET", "POST"])
@login_required
def nueva():
    uid = session["user"]["id"]
    campanas = _campanas_disponibles(uid)
    if request.method == "POST":
        nombre = (request.form.get("nombre") or "").strip()[:150]
        tipo = (request.form.get("tipo") or "").strip()[:150]
        cid = request.form.get("campana_id") or ""
        c = next((x for x in campanas if str(x["campana_id"]) == cid), None)
        if not (nombre and tipo and c):
            flash("Indica el nombre, el tipo de banda y una campaña disponible.", "warning")
            return render_template("banda_nueva.html", campanas=campanas, form=request.form)
        try:
            # Inscripción en la campaña (si aún no lo estaba)
            db.execute(
                """INSERT INTO campanas_usuarios (campana_id, usuario_id, fecha_inscripcion)
                   VALUES (%s, %s, %s) ON CONFLICT (campana_id, usuario_id) DO NOTHING""",
                (cid, uid, date.today()), commit=False)
            cu = db.query(
                "SELECT campana_usuario_id FROM campanas_usuarios WHERE campana_id = %s AND usuario_id = %s",
                (cid, uid), one=True)
            row = db.execute(
                """INSERT INTO bandas (campana_id, campana_usuario_id, banda_nombre, banda_tipo,
                       banda_tesoreria, banda_estado)
                   VALUES (%s, %s, %s, %s, %s, 1) RETURNING banda_id""",
                (cid, str(cu["campana_usuario_id"]), nombre, tipo, c["campana_tesoreria_inicial"]),
                returning=True, commit=False)
            anotar_historial(row["banda_id"],
                             f"Crea la banda con tesorería inicial {c['campana_tesoreria_inicial']}")
        except psycopg2.IntegrityError:
            db.get_db().rollback()
            flash("Ya existe una banda con ese nombre en la campaña.", "danger")
            return render_template("banda_nueva.html", campanas=campanas, form=request.form)
        flash(f"Banda «{nombre}» creada.", "success")
        return redirect(url_for("bandas.ver", banda_id=row["banda_id"]))
    return render_template("banda_nueva.html", campanas=campanas, form={})


# ---------------------------------------------------------------------------
#  Ficha
# ---------------------------------------------------------------------------
def _ficha(banda_id):
    """Datos comunes de la ficha (pantalla y PDF): banda, miembros, stats y bajas."""
    b = _banda(banda_id)
    lineas = db.query(
        "SELECT * FROM bandas_lin WHERE banda_id = %s ORDER BY banda_lin_orden, banda_lin_nombre",
        (str(banda_id),))
    defs = definicion_stats(b["regla_stats_especificos"], b["regla_info"])
    stats = columnas_stats(defs, lineas)
    plantilla = [ln for ln in lineas if ln["banda_lin_estado"] in MIEMBRO_EN_PLANTILLA]
    bajas = [ln for ln in lineas if ln["banda_lin_estado"] not in MIEMBRO_EN_PLANTILLA]
    return b, lineas, defs, stats, plantilla, bajas


@bp.route("/banda/<uuid:banda_id>/pdf")
def pdf(banda_id):
    """Ficha de banda en PDF (mismo acceso que la ficha: público)."""
    import re
    import unicodedata
    from flask import current_app, send_file
    from io import BytesIO
    from .pdf import build_banda_pdf
    b, _lineas, _defs, stats, plantilla, bajas = _ficha(banda_id)
    contenido = build_banda_pdf(b, plantilla, bajas, stats, historial(b["banda_audit"]),
                                ESTADOS_BANDA, ESTADOS_MIEMBRO, current_app.config["APP_NAME"])
    # Nombre de archivo sin acentos ni símbolos: «Lobos «azules» & Cía» → banda_Lobos_azules_Cia.pdf
    sin_tildes = unicodedata.normalize("NFKD", b["banda_nombre"]).encode("ascii", "ignore").decode()
    nombre = re.sub(r"[^A-Za-z0-9_-]+", "_", sin_tildes).strip("_") or "banda"
    return send_file(BytesIO(contenido), mimetype="application/pdf", as_attachment=False,
                     download_name=f"banda_{nombre}.pdf")


@bp.route("/banda/<uuid:banda_id>")
def ver(banda_id):
    b, lineas, defs, stats, plantilla, bajas = _ficha(banda_id)
    # Datos para el popup de edición (se serializan con |tojson en la plantilla)
    miembros = {str(ln["banda_lin_id"]): {
        "orden": ln["banda_lin_orden"], "nombre": ln["banda_lin_nombre"],
        "subtipo": ln["banda_lin_subtipo"], "categoria": ln["banda_lin_categoria"] or "",
        "cantidad": ln["banda_lin_cantidad"],
        "precio": ln["banda_lin_coste"] - _suma_armamento(ln["banda_lin_armamento"]),
        "stats": ln["banda_lin_stats"] if isinstance(ln["banda_lin_stats"], dict) else {},
        "armamento": ln["banda_lin_armamento"] if isinstance(ln["banda_lin_armamento"], list) else [],
        "experiencia": ln["banda_lin_experiencia"] or 0, "estado": ln["banda_lin_estado"] or 0,
        "notas": ln["banda_lin_notas"] or "", "observaciones": ln["banda_lin_observaciones"] or "",
    } for ln in lineas}
    siguiente_orden = max([ln["banda_lin_orden"] for ln in lineas] or [0]) + 1
    return render_template(
        "banda.html", b=b, plantilla=plantilla, bajas=bajas, stats=stats,
        defectos=defs if isinstance(defs, dict) else {}, miembros=miembros,
        siguiente_orden=siguiente_orden, historial=historial(b["banda_audit"]),
        puede_editar=puede_editar_banda(b, session.get("user")),
        estados_banda=ESTADOS_BANDA, estados_miembro=ESTADOS_MIEMBRO,
    )


@bp.route("/banda/<uuid:banda_id>/editar", methods=["POST"])
@login_required
def editar(banda_id):
    """Edición in situ de los datos de la banda (la tesorería siempre es editable)."""
    b = _banda_editable(banda_id)
    f = request.form
    nombre = (f.get("nombre") or "").strip()[:150] or b["banda_nombre"]
    tipo = (f.get("tipo") or "").strip()[:150] or b["banda_tipo"]
    tesoreria = a_entero(f.get("tesoreria"), b["banda_tesoreria"] or 0)
    estado = a_entero(f.get("estado"), b["banda_estado"])
    if estado not in ESTADOS_BANDA:
        estado = b["banda_estado"]
    observaciones = (f.get("observaciones") or "").strip() or None

    cambios = []
    if nombre != b["banda_nombre"]:
        cambios.append(f"nombre «{b['banda_nombre']}» → «{nombre}»")
    if tipo != b["banda_tipo"]:
        cambios.append(f"tipo «{b['banda_tipo']}» → «{tipo}»")
    if tesoreria != (b["banda_tesoreria"] or 0):
        cambios.append(f"tesorería {b['banda_tesoreria'] or 0} → {tesoreria} (edición manual)")
    if estado != b["banda_estado"]:
        cambios.append(f"estado {ESTADOS_BANDA.get(b['banda_estado'])} → {ESTADOS_BANDA[estado]}")
    if observaciones != b["banda_observaciones"]:
        cambios.append("observaciones")
    if not cambios:
        flash("No hay cambios que guardar.", "info")
        return redirect(url_for("bandas.ver", banda_id=banda_id))
    try:
        db.execute(
            """UPDATE bandas SET banda_nombre=%s, banda_tipo=%s, banda_tesoreria=%s,
                   banda_estado=%s, banda_observaciones=%s WHERE banda_id=%s""",
            (nombre, tipo, tesoreria, estado, observaciones, str(banda_id)), commit=False)
        anotar_historial(banda_id, "Edita la banda: " + "; ".join(cambios))
    except psycopg2.IntegrityError:
        db.get_db().rollback()
        flash("No se pudo guardar: ya hay una banda con ese nombre en la campaña, "
              "o el usuario ya tiene otra banda activa en ella.", "danger")
        return redirect(url_for("bandas.ver", banda_id=banda_id))
    flash("Datos de la banda guardados.", "success")
    return redirect(url_for("bandas.ver", banda_id=banda_id))


# ---------------------------------------------------------------------------
#  Miembros
# ---------------------------------------------------------------------------
def _convertir_stat(texto, defecto):
    """Respeta el tipo del valor por defecto del reglamento (número o texto)."""
    texto = (texto or "").strip()
    if texto == "":
        return defecto if defecto is not None else ""
    if isinstance(defecto, bool):
        return texto.lower() in ("1", "true", "si", "sí")
    if isinstance(defecto, int) or defecto is None:
        try:
            return int(texto)
        except ValueError:
            pass
    if isinstance(defecto, (int, float)):
        try:
            return float(texto.replace(",", "."))
        except ValueError:
            pass
    return texto[:50]


def _leer_miembro(form, stats_claves, defectos):
    nombre = (form.get("nombre") or "").strip()[:150]
    subtipo = (form.get("subtipo") or "").strip()[:150]
    if not (nombre and subtipo):
        return None
    armamento = []
    for n, p in zip(form.getlist("arm_nombre"), form.getlist("arm_precio")):
        n = (n or "").strip()[:100]
        if n:
            armamento.append({"nombre": n, "precio": max(0, a_entero(p, 0))})
    precio = max(0, a_entero(form.get("precio"), 0))
    estado = a_entero(form.get("estado"), 0)
    return {
        "orden": a_entero(form.get("orden"), 1),
        "nombre": nombre,
        "subtipo": subtipo,
        "categoria": (form.get("categoria") or "").strip()[:50] or None,
        "cantidad": max(1, a_entero(form.get("cantidad"), 1)),
        "coste": precio + _suma_armamento(armamento),
        "stats": {clave: _convertir_stat(form.get(f"stat_{i}"), defectos.get(clave))
                  for i, clave in enumerate(stats_claves)},
        "armamento": armamento,
        "experiencia": max(0, a_entero(form.get("experiencia"), 0)),
        "estado": estado if estado in ESTADOS_MIEMBRO else 0,
        "notas": (form.get("notas") or "").strip() or None,
        "observaciones": (form.get("observaciones") or "").strip() or None,
    }


def _claves_stats(b):
    defs = definicion_stats(b["regla_stats_especificos"], b["regla_info"])
    lineas = db.query("SELECT banda_lin_stats FROM bandas_lin WHERE banda_id = %s", (str(b["banda_id"]),))
    return columnas_stats(defs, lineas), (defs if isinstance(defs, dict) else {})


def _cobrar(b, importe, motivo, commit=False):
    """Descuenta `importe` de la tesorería y lo anota en el historial.

    La resta la hace PostgreSQL en una sola sentencia (tesorería = tesorería − importe)
    sobre el valor vigente, no sobre uno leído antes: dos cobros simultáneos nunca
    se pisan."""
    row = db.execute(
        """UPDATE bandas SET banda_tesoreria = COALESCE(banda_tesoreria, 0) - %s
           WHERE banda_id = %s RETURNING banda_tesoreria""",
        (importe, str(b["banda_id"])), returning=True, commit=False)
    despues = row["banda_tesoreria"]
    antes = despues + importe
    anotar_historial(b["banda_id"], f"{motivo} · tesorería {antes} → {despues}", commit=commit)
    b["banda_tesoreria"] = despues
    if despues < 0:
        flash(f"Atención: la tesorería queda en negativo ({despues}).", "warning")


@bp.route("/banda/<uuid:banda_id>/contratar", methods=["POST"])
@login_required
def contratar(banda_id):
    b = _banda_editable(banda_id)
    claves, defectos = _claves_stats(b)
    m = _leer_miembro(request.form, claves, defectos)
    if not m:
        flash("El nombre y el tipo del miembro son obligatorios.", "warning")
        return redirect(url_for("bandas.ver", banda_id=banda_id))
    db.execute(
        """INSERT INTO bandas_lin (banda_id, banda_lin_orden, banda_lin_nombre, banda_lin_subtipo,
               banda_lin_categoria, banda_lin_cantidad, banda_lin_coste, banda_lin_experiencia,
               banda_lin_estado, banda_lin_stats, banda_lin_armamento, banda_lin_notas,
               banda_lin_observaciones)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s)""",
        (str(banda_id), m["orden"], m["nombre"], m["subtipo"], m["categoria"], m["cantidad"], m["coste"],
         m["experiencia"], Json(m["stats"]), Json(m["armamento"]), m["notas"], m["observaciones"]),
        commit=False)
    total = m["coste"] * m["cantidad"]
    equipo = ", ".join(_nombres_armamento(m["armamento"]))
    _cobrar(b, total, f"Contrata «{m['nombre']}» ({m['subtipo']}) ×{m['cantidad']} por {total}"
                      + (f" [equipo: {equipo}]" if equipo else ""))
    recalcular_valor(banda_id)
    flash(f"«{m['nombre']}» contratado por {total}.", "success")
    return redirect(url_for("bandas.ver", banda_id=banda_id))


def _linea(banda_id, lin_id):
    ln = db.query("SELECT * FROM bandas_lin WHERE banda_lin_id = %s AND banda_id = %s",
                  (str(lin_id), str(banda_id)), one=True)
    if not ln:
        abort(404)
    return ln


@bp.route("/banda/<uuid:banda_id>/miembro/<uuid:lin_id>/editar", methods=["POST"])
@login_required
def editar_miembro(banda_id, lin_id):
    b = _banda_editable(banda_id)
    ln = _linea(banda_id, lin_id)
    claves, defectos = _claves_stats(b)
    m = _leer_miembro(request.form, claves, defectos)
    if not m:
        flash("El nombre y el tipo del miembro son obligatorios.", "warning")
        return redirect(url_for("bandas.ver", banda_id=banda_id))

    cambios = []
    for etiqueta, antes, despues in (
            ("nombre", ln["banda_lin_nombre"], m["nombre"]),
            ("tipo", ln["banda_lin_subtipo"], m["subtipo"]),
            ("categoría", ln["banda_lin_categoria"] or "—", m["categoria"] or "—"),
            ("cantidad", ln["banda_lin_cantidad"], m["cantidad"]),
            ("coste", ln["banda_lin_coste"], m["coste"]),
            ("experiencia", ln["banda_lin_experiencia"] or 0, m["experiencia"])):
        if antes != despues:
            cambios.append(f"{etiqueta} {antes} → {despues}")
    if (ln["banda_lin_estado"] or 0) != m["estado"]:
        cambios.append(f"estado {ESTADOS_MIEMBRO.get(ln['banda_lin_estado'] or 0)} → "
                       f"{ESTADOS_MIEMBRO[m['estado']]}")
    if (ln["banda_lin_stats"] or {}) != m["stats"]:
        cambios.append("stats")
    # Equipo comprado / retirado (comparación por nombre, admite repetidos)
    antes_eq = _nombres_armamento(ln["banda_lin_armamento"])
    nuevos, quitados = list(_nombres_armamento(m["armamento"])), []
    for n in antes_eq:
        if n in nuevos:
            nuevos.remove(n)
        else:
            quitados.append(n)
    if nuevos:
        cambios.append("compra " + ", ".join(nuevos))
    if quitados:
        cambios.append("retira " + ", ".join(quitados))
    if (ln["banda_lin_notas"] or None) != m["notas"] or \
            (ln["banda_lin_observaciones"] or None) != m["observaciones"]:
        cambios.append("notas")

    db.execute(
        """UPDATE bandas_lin SET banda_lin_orden=%s, banda_lin_nombre=%s, banda_lin_subtipo=%s,
               banda_lin_categoria=%s, banda_lin_cantidad=%s, banda_lin_coste=%s, banda_lin_experiencia=%s,
               banda_lin_estado=%s, banda_lin_stats=%s, banda_lin_armamento=%s,
               banda_lin_notas=%s, banda_lin_observaciones=%s
           WHERE banda_lin_id=%s""",
        (m["orden"], m["nombre"], m["subtipo"], m["categoria"], m["cantidad"], m["coste"],
         m["experiencia"], m["estado"], Json(m["stats"]), Json(m["armamento"]), m["notas"], m["observaciones"],
         str(lin_id)), commit=False)

    # Cobro: lo que sube el coste de la línea (equipo nuevo o más unidades).
    # Las bajadas no se reembolsan solas: la tesorería se corrige a mano.
    incremento = m["coste"] * m["cantidad"] - ln["banda_lin_coste"] * ln["banda_lin_cantidad"]
    texto = f"Edita «{m['nombre']}»: " + ("; ".join(cambios) if cambios else "sin cambios")
    if incremento > 0 and m["estado"] in MIEMBRO_EN_PLANTILLA:
        _cobrar(b, incremento, f"{texto} · cargo {incremento}")
    else:
        anotar_historial(banda_id, texto, commit=False)
    recalcular_valor(banda_id)
    flash(f"«{m['nombre']}» actualizado.", "success")
    return redirect(url_for("bandas.ver", banda_id=banda_id))


@bp.route("/banda/<uuid:banda_id>/miembro/<uuid:lin_id>/despedir", methods=["POST"])
@login_required
def despedir(banda_id, lin_id):
    _banda_editable(banda_id)
    ln = _linea(banda_id, lin_id)
    if ln["banda_lin_estado"] == 2:   # doble clic: ya estaba despedido, no se repite
        flash(f"«{ln['banda_lin_nombre']}» ya estaba despedido.", "info")
        return redirect(url_for("bandas.ver", banda_id=banda_id))
    db.execute("UPDATE bandas_lin SET banda_lin_estado = 2 WHERE banda_lin_id = %s",
               (str(lin_id),), commit=False)
    anotar_historial(banda_id, f"Despide a «{ln['banda_lin_nombre']}» ({ln['banda_lin_subtipo']})",
                     commit=False)
    recalcular_valor(banda_id)
    flash(f"«{ln['banda_lin_nombre']}» despedido.", "info")
    return redirect(url_for("bandas.ver", banda_id=banda_id))

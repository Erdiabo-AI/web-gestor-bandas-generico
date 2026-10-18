from functools import wraps
from flask import session, redirect, url_for, flash, abort


def current_user():
    return session.get("user")


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            flash("Debes iniciar sesión para acceder a esta página.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = session.get("user")
        if not user:
            return redirect(url_for("auth.login"))
        if user.get("rol") != "ADM":
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def es_gestor_campana(fila, user):
    """¿El usuario gestiona la campaña de esta fila? Vale el gestor titular,
    el suplente (si está nombrado) o un ADM. `fila` debe traer
    usuarios_gestor_id (y usuarios_gestor_suplente_id si existe)."""
    if not user or not fila:
        return False
    if user.get("rol") == "ADM":
        return True
    if str(fila["usuarios_gestor_id"]) == user["id"]:
        return True
    supl = fila.get("usuarios_gestor_suplente_id")
    return supl is not None and str(supl) == user["id"]


def definicion_stats(stats, info):
    """regla_stats_especificos en el orden en que lo escribió el administrador.

    jsonb no conserva el orden de las claves (las reordena por longitud), así
    que el orden se guarda aparte en regla_info["orden_stats"] (los arrays sí
    lo conservan)."""
    if not isinstance(stats, dict):
        return stats
    orden = info.get("orden_stats") if isinstance(info, dict) else None
    if not orden:
        return stats
    res = {k: stats[k] for k in orden if k in stats}
    res.update({k: v for k, v in stats.items() if k not in res})
    return res


def columnas_stats(definicion, lineas):
    """Columnas de stats a mostrar en la ficha de banda.

    `definicion` es reglas.regla_stats_especificos (formato aún por cerrar,
    ver docs/PENDIENTES.md). Se aceptan:
      - lista de claves: ["M", "HA", "HP"]
      - lista de objetos: [{"clave": "M", "nombre": "Movimiento"}, ...]
      - objeto: {"M": ..., "HA": ...} (se usan sus claves, en orden)
    Sin definición, se usan las claves que aparezcan en banda_lin_stats."""
    claves = []
    if isinstance(definicion, list):
        for d in definicion:
            if isinstance(d, dict):
                c = d.get("clave") or d.get("nombre")
                if c:
                    claves.append(str(c))
            elif d is not None:
                claves.append(str(d))
    elif isinstance(definicion, dict):
        claves = [str(k) for k in definicion]
    if claves:
        return claves
    for ln in lineas:
        stats = ln.get("banda_lin_stats")
        if isinstance(stats, dict):
            for k in stats:
                if k not in claves:
                    claves.append(k)
    return claves


def formato_info(valor):
    """Filtro Jinja `info`: texto legible de un campo JSONB (dict/lista/escalar)."""
    if valor is None or valor == "" or valor == {} or valor == []:
        return ""
    if isinstance(valor, dict):
        return " · ".join(f"{k}: {formato_info(v)}" for k, v in valor.items())
    if isinstance(valor, list):
        return ", ".join(formato_info(v) for v in valor)
    return str(valor)


# ---------------------------------------------------------------------------
#  Códigos de estado (ver cabecera de db/schema.sql)
# ---------------------------------------------------------------------------
ESTADOS_CAMPANA = ["INSCRIPCION", "ABIERTA", "CERRADA"]
ESTADOS_BANDA = {1: "Activa", 2: "Destruida"}
ESTADOS_MIEMBRO = {0: "Activo", 1: "Lesionado", 2: "Despedido", 3: "Muerto"}
ESTADOS_BATALLA = {0: "Borrador", 1: "Confirmada"}
MIEMBRO_EN_PLANTILLA = (0, 1)   # cuentan para el valor de la banda


# ---------------------------------------------------------------------------
#  Modo comisario (COM): no es un rol guardado, sino un permiso de sesión que
#  el gestor (o suplente) activa por campaña con «Acceder como comisario».
# ---------------------------------------------------------------------------
def campanas_com():
    return session.get("com", [])


def activar_com(campana_id, activo):
    com = [c for c in campanas_com() if c != str(campana_id)]
    if activo:
        com.append(str(campana_id))
    session["com"] = com


def es_comisario(campana_id, user):
    """¿Puede gestionar bandas y actas de todos en esta campaña? ADM siempre;
    gestor/suplente solo con el modo comisario activado."""
    if not user:
        return False
    if user.get("rol") == "ADM":
        return True
    return str(campana_id) in campanas_com()


def puede_editar_banda(banda, user):
    """Propietario de la banda o comisario de su campaña. `banda` trae
    usuario_id (propietario) y campana_id."""
    if not user or not banda:
        return False
    if banda.get("usuario_id") and str(banda["usuario_id"]) == user["id"]:
        return True
    return es_comisario(banda["campana_id"], user)


def a_entero(valor, defecto=0):
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return defecto

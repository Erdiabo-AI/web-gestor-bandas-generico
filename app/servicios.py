"""Operaciones de datos compartidas: historial y valor de las bandas."""
from flask import session

from . import db
from .helpers import MIEMBRO_EN_PLANTILLA


def anotar_historial(banda_id, texto, commit=True):
    """Añade una línea al historial de la banda (bandas.banda_audit):
    «dd/mm/aaaa hh:mm · Usuario · texto». La hora es la de España."""
    autor = (session.get("user") or {}).get("nombre", "sistema")
    db.execute(
        """UPDATE bandas SET banda_audit = COALESCE(banda_audit, '')
               || to_char(now() AT TIME ZONE 'Europe/Madrid', 'DD/MM/YYYY HH24:MI')
               || ' · ' || %s || ' · ' || %s || E'\n'
           WHERE banda_id = %s""",
        (autor, texto, str(banda_id)), commit=commit,
    )


def recalcular_valor(banda_id, commit=True):
    """Valor de banda = Σ coste × cantidad de los miembros en plantilla
    (activos y lesionados). Es la base de la clasificación de la campaña."""
    db.execute(
        """UPDATE bandas SET banda_valor_banda = COALESCE((
               SELECT SUM(banda_lin_coste * banda_lin_cantidad) FROM bandas_lin
               WHERE banda_id = %s AND banda_lin_estado = ANY(%s)), 0)
           WHERE banda_id = %s""",
        (str(banda_id), list(MIEMBRO_EN_PLANTILLA), str(banda_id)), commit=commit,
    )


def historial(texto_audit):
    """Líneas del historial, la más reciente primero."""
    return [ln for ln in (texto_audit or "").splitlines() if ln.strip()][::-1]

"""Generación de PDF con reportlab: ficha de banda (A4 apaisado)."""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                Paragraph, Spacer)

from .helpers import ahora_es

PADDING = 3                                # margen interior de celda (puntos)
GRIS_OSCURO = colors.HexColor("#3f3f46")   # cabecera de la web
GRIS_LINEA = colors.HexColor("#999999")
FONDO_ALTERNO = colors.HexColor("#f4f4f5")
BEIGE = colors.HexColor("#e8e4bc")


def _esc(s):
    """Texto seguro para Paragraph. Helvetica no tiene la flecha «→»: se sustituye."""
    return (str(s if s is not None else "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace("→", "->"))


def _armamento(lista):
    if not isinstance(lista, list):
        return ""
    return ", ".join(f"{_esc(a.get('nombre'))} ({_esc(a.get('precio'))})"
                     for a in lista if isinstance(a, dict) and a.get("nombre"))


# ---------------------------------------------------------------------------
#  Disposición de los stats: una línea (una columna por stat) o dos líneas
#  (datos del miembro arriba y su perfil de stats debajo, a todo el ancho).
# ---------------------------------------------------------------------------
FUENTE_CAB = 6                       # cuerpo de letra de las cabeceras de stats
UMBRAL_DOS_LINEAS = 90 * mm          # en «auto», más ancho que esto → dos líneas
DISPOSICIONES = ("auto", "una", "dos")


def etiqueta_stat(clave):
    """«impactos_totales» → «IMPACTOS TOTALES»: así parte por palabras y no a mitad."""
    return clave.replace("_", " ").upper()


def ancho_stat(clave):
    """Ancho real de la palabra más larga de la etiqueta (Helvetica-Bold) + márgenes."""
    palabras = etiqueta_stat(clave).split() or [""]
    return max(9 * mm, max(stringWidth(w, "Helvetica-Bold", FUENTE_CAB) for w in palabras) + 2 * PADDING + 2)


def usar_dos_lineas(stats, regla_info):
    """Decide la disposición según regla_info["disposicion_stats"] (auto / una / dos).
    En «auto» se pasa a dos líneas cuando las columnas de stats ocuparían más de
    UMBRAL_DOS_LINEAS (≈ un tercio de la página): Mordheim (9 stats cortos) cabe en
    una línea; Battlefleet o Aeronautica (nombres largos) van a dos."""
    if not stats:
        return False
    disposicion = (regla_info or {}).get("disposicion_stats", "auto") if isinstance(regla_info, dict) else "auto"
    if disposicion == "una":
        return False
    if disposicion == "dos":
        return True
    return sum(ancho_stat(s) for s in stats) > UMBRAL_DOS_LINEAS


def _celdas_comunes(ln, estados, st):
    """Celdas de la fila principal (sin stats), ya formateadas."""
    p = lambda txt: Paragraph(txt, st["celda"])
    coste = f"{ln['banda_lin_coste']}"
    if ln["banda_lin_cantidad"] > 1:
        coste += f"<br/><font size=6>x{ln['banda_lin_cantidad']} = {ln['banda_lin_coste'] * ln['banda_lin_cantidad']}</font>"
    notas = _esc(ln["banda_lin_notas"] or "")
    if ln["banda_lin_observaciones"]:
        notas += f"<br/><font size=6 color='#555555'>{_esc(ln['banda_lin_observaciones'])}</font>"
    return {
        "orden": str(ln["banda_lin_orden"]), "nombre": p(_esc(ln["banda_lin_nombre"])),
        "tipo": p(_esc(ln["banda_lin_subtipo"])), "categoria": p(_esc(ln["banda_lin_categoria"] or "")),
        "cant": str(ln["banda_lin_cantidad"]), "armamento": p(_armamento(ln["banda_lin_armamento"])),
        "exp": str(ln["banda_lin_experiencia"] or 0), "coste": p(coste),
        "estado": _esc(estados.get(ln["banda_lin_estado"] or 0, "")), "notas": p(notas),
    }


def _tabla_miembros(lineas, stats, estados, st, dos_lineas=False):
    if dos_lineas:
        return _tabla_miembros_dos_lineas(lineas, stats, estados, st)
    return _tabla_miembros_una_linea(lineas, stats, estados, st)


def _tabla_miembros_una_linea(lineas, stats, estados, st):
    """Tabla de miembros con una columna por stat del reglamento."""
    etiquetas_stats = [etiqueta_stat(s) for s in stats]
    cab = ["Nº", "Nombre", "Tipo", "Categoría", "Cant."] + etiquetas_stats + \
          ["Armamento", "Exp.", "Coste", "Estado", "Notas"]
    data = [[Paragraph(f"<b>{_esc(c)}</b>", st["cab"]) for c in cab]]
    for ln in lineas:
        c = _celdas_comunes(ln, estados, st)
        valores = ln["banda_lin_stats"] if isinstance(ln["banda_lin_stats"], dict) else {}
        data.append([c["orden"], c["nombre"], c["tipo"], c["categoria"], c["cant"]]
                    + [_esc(valores.get(s, "")) for s in stats]
                    + [c["armamento"], c["exp"], c["coste"], c["estado"], c["notas"]])

    # Anchos: columnas fijas + una por stat; el resto se reparte entre Armamento y
    # Notas, que nunca bajan de MIN_TEXTO entre las dos.
    ancho_total = landscape(A4)[0] - 20 * mm
    fijas = {"orden": 9, "nombre": 28, "tipo": 20, "categoria": 16, "cant": 10, "exp": 10, "coste": 15, "estado": 16}
    libre = ancho_total - sum(fijas.values()) * mm
    MIN_TEXTO = 45 * mm
    anchos_stats = [ancho_stat(s) for s in stats]
    if anchos_stats and sum(anchos_stats) > libre - MIN_TEXTO:
        factor = (libre - MIN_TEXTO) / sum(anchos_stats)
        anchos_stats = [a * factor for a in anchos_stats]
    resto = libre - sum(anchos_stats)
    anchos = ([fijas["orden"] * mm, fijas["nombre"] * mm, fijas["tipo"] * mm, fijas["categoria"] * mm,
               fijas["cant"] * mm]
              + anchos_stats
              + [resto * 0.55, fijas["exp"] * mm, fijas["coste"] * mm, fijas["estado"] * mm, resto * 0.45])

    n = len(stats)
    t = Table(data, colWidths=anchos, repeatRows=1)
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.4, GRIS_LINEA),
        ("BACKGROUND", (0, 0), (-1, 0), GRIS_OSCURO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (4, 1), (4 + n, -1), "CENTER"),        # cantidad y stats
        ("ALIGN", (6 + n, 1), (6 + n, -1), "CENTER"),    # experiencia
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FONDO_ALTERNO]),
        ("LEFTPADDING", (0, 0), (-1, -1), PADDING),
        ("RIGHTPADDING", (0, 0), (-1, -1), PADDING),
    ]))
    return t


def _perfil(valores, stats, st, ancho_max):
    """Mini tabla del perfil: etiquetas encima, valores debajo (como la hoja de Mordheim)."""
    anchos = [max(ancho_stat(s), 12 * mm) for s in stats]
    if sum(anchos) > ancho_max:
        anchos = [a * ancho_max / sum(anchos) for a in anchos]
    t = Table([[Paragraph(f"<b>{_esc(etiqueta_stat(s))}</b>", st["cab_perfil"]) for s in stats],
               [_esc(valores.get(s, "")) for s in stats]],
              colWidths=anchos, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 8.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
        ("BOX", (0, 0), (-1, -1), 0.4, GRIS_LINEA),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c4c4c8")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def _tabla_miembros_dos_lineas(lineas, stats, estados, st):
    """Dos filas por miembro: datos arriba y, debajo, su perfil de stats a todo el ancho.
    Las dos filas de un miembro nunca se separan entre páginas (NOSPLIT)."""
    cab = ["Nº", "Nombre", "Tipo", "Categoría", "Cant.", "Armamento", "Exp.", "Coste", "Estado", "Notas"]
    ancho_total = landscape(A4)[0] - 20 * mm
    fijas = [9, 34, 26, 20, 10, None, 10, 15, 16, None]          # mm; None = se reparte
    resto = ancho_total - sum(f for f in fijas if f) * mm
    anchos = [f * mm if f else (resto * (0.55 if i == 5 else 0.45)) for i, f in enumerate(fijas)]

    data = [[Paragraph(f"<b>{_esc(c)}</b>", st["cab"]) for c in cab]]
    estilo = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("BACKGROUND", (0, 0), (-1, 0), GRIS_OSCURO),
        ("GRID", (0, 0), (-1, 0), 0.4, GRIS_LINEA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), PADDING),
        ("RIGHTPADDING", (0, 0), (-1, -1), PADDING),
    ]
    for i, ln in enumerate(lineas):
        c = _celdas_comunes(ln, estados, st)
        valores = ln["banda_lin_stats"] if isinstance(ln["banda_lin_stats"], dict) else {}
        a = len(data)                       # fila de datos; a + 1 = fila del perfil
        data.append([c["orden"], c["nombre"], c["tipo"], c["categoria"], c["cant"],
                     c["armamento"], c["exp"], c["coste"], c["estado"], c["notas"]])
        data.append(["", _perfil(valores, stats, st, ancho_total - anchos[0] - 2 * PADDING)]
                    + [""] * (len(cab) - 2))
        estilo += [
            ("SPAN", (0, a), (0, a + 1)),                     # Nº ocupa las dos filas
            ("SPAN", (1, a + 1), (-1, a + 1)),                # perfil a todo el ancho
            ("BOX", (0, a), (-1, a + 1), 0.6, GRIS_LINEA),    # recuadro del miembro
            ("INNERGRID", (0, a), (-1, a), 0.3, GRIS_LINEA),  # separadores de la fila de datos
            ("LINEAFTER", (0, a), (0, a + 1), 0.3, GRIS_LINEA),
            ("ALIGN", (0, a), (0, a), "CENTER"),
            ("ALIGN", (4, a), (4, a), "CENTER"),
            ("ALIGN", (6, a), (6, a), "CENTER"),
            ("TOPPADDING", (1, a + 1), (-1, a + 1), 1),
            ("BOTTOMPADDING", (1, a + 1), (-1, a + 1), 4),
            ("NOSPLIT", (0, a), (-1, a + 1)),
        ]
        if i % 2:
            estilo.append(("BACKGROUND", (0, a), (-1, a + 1), FONDO_ALTERNO))
    t = Table(data, colWidths=anchos, repeatRows=1)
    t.setStyle(TableStyle(estilo))
    return t


def build_banda_pdf(b, plantilla, bajas, stats, estados_banda, estados_miembro, app_name, dos_lineas=False):
    """PDF de la ficha de banda: datos, miembros en plantilla y bajas (sin historial)."""
    buf = BytesIO()
    generado = ahora_es().strftime("%d/%m/%Y %H:%M")

    def pie(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawString(10 * mm, 6 * mm, f"{app_name} · {b['banda_nombre']} · generado el {generado}")
        canvas.drawRightString(landscape(A4)[0] - 10 * mm, 6 * mm, f"Página {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4), title=f"Banda {b['banda_nombre']}", author=app_name,
        leftMargin=10 * mm, rightMargin=10 * mm, topMargin=10 * mm, bottomMargin=12 * mm)

    base = getSampleStyleSheet()
    st = {
        "titulo": ParagraphStyle("titulo", parent=base["Title"], fontSize=18, spaceAfter=1, alignment=0),
        "sub": ParagraphStyle("sub", parent=base["Normal"], fontSize=9, textColor=colors.HexColor("#555555")),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontSize=12, spaceBefore=6, spaceAfter=3),
        "normal": ParagraphStyle("normal", parent=base["Normal"], fontSize=9, leading=11),
        "celda": ParagraphStyle("celda", parent=base["Normal"], fontSize=7.5, leading=9),
        "cab": ParagraphStyle("cab", parent=base["Normal"], fontSize=FUENTE_CAB, leading=7, textColor=colors.white),
        "cab_perfil": ParagraphStyle("cab_perfil", parent=base["Normal"], fontSize=FUENTE_CAB, leading=7,
                                     alignment=1, textColor=colors.HexColor("#3f3f46")),
    }

    estado_banda = estados_banda.get(b["banda_estado"], b["banda_estado"])
    story = [
        Paragraph(_esc(b["banda_nombre"]), st["titulo"]),
        Paragraph(f"{_esc(b['banda_tipo'])} · Campaña {_esc(b['campana_nombre'])}"
                  + (f" · {_esc(b['regla_descripcion'])}" if b.get("regla_descripcion") else ""), st["sub"]),
        Spacer(1, 4 * mm),
    ]

    # Datos de la banda
    etiquetas = ["Usuario", "Banda", "Campaña", "Reglamento", "Tesorería", "Coste", "Estado"]
    valores = [b["usuario_nombre"] or "—", b["banda_tipo"], b["campana_nombre"],
               b.get("regla_descripcion") or "—", b["banda_tesoreria"] or 0,
               b["banda_valor_banda"] or 0, estado_banda]
    datos = Table(
        [[Paragraph(f"<b>{e}</b>", st["celda"]) for e in etiquetas],
         [Paragraph(_esc(v), st["normal"]) for v in valores]],
        colWidths=[(landscape(A4)[0] - 20 * mm) / len(etiquetas)] * len(etiquetas))
    datos.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BEIGE),
        ("BOX", (0, 0), (-1, -1), 0.6, GRIS_LINEA),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, GRIS_LINEA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(datos)

    if b["banda_observaciones"]:
        story += [Spacer(1, 2 * mm),
                  Paragraph(f"<b>Observaciones:</b> {_esc(b['banda_observaciones'])}", st["normal"])]

    story.append(Paragraph(f"Miembros de la banda ({len(plantilla)})", st["h2"]))
    if plantilla:
        story.append(_tabla_miembros(plantilla, stats, estados_miembro, st, dos_lineas))
    else:
        story.append(Paragraph("La banda aún no tiene miembros.", st["normal"]))

    if bajas:
        story.append(Paragraph(f"Bajas: despedidos y muertos ({len(bajas)})", st["h2"]))
        story.append(_tabla_miembros(bajas, stats, estados_miembro, st, dos_lineas))

    doc.build(story, onFirstPage=pie, onLaterPages=pie)
    return buf.getvalue()

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


def _tabla_miembros(lineas, stats, estados, st):
    """Tabla de miembros con una columna por stat del reglamento."""
    p = lambda txt: Paragraph(txt, st["celda"])
    # «impactos_totales» → «IMPACTOS TOTALES»: así parte por palabras y no a mitad
    etiquetas_stats = [s.replace("_", " ").upper() for s in stats]
    cab = ["Nº", "Nombre", "Tipo", "Categoría", "Cant."] + etiquetas_stats + \
          ["Armamento", "Exp.", "Coste", "Estado", "Notas"]
    data = [[Paragraph(f"<b>{_esc(c)}</b>", st["cab"]) for c in cab]]
    for ln in lineas:
        valores = ln["banda_lin_stats"] if isinstance(ln["banda_lin_stats"], dict) else {}
        coste = f"{ln['banda_lin_coste']}"
        if ln["banda_lin_cantidad"] > 1:
            coste += f"<br/><font size=6>x{ln['banda_lin_cantidad']} = {ln['banda_lin_coste'] * ln['banda_lin_cantidad']}</font>"
        notas = _esc(ln["banda_lin_notas"] or "")
        if ln["banda_lin_observaciones"]:
            notas += f"<br/><font size=6 color='#555555'>{_esc(ln['banda_lin_observaciones'])}</font>"
        data.append(
            [str(ln["banda_lin_orden"]), p(_esc(ln["banda_lin_nombre"])), p(_esc(ln["banda_lin_subtipo"])),
             p(_esc(ln["banda_lin_categoria"] or "")), str(ln["banda_lin_cantidad"])]
            + [_esc(valores.get(s, "")) for s in stats]
            + [p(_armamento(ln["banda_lin_armamento"])), str(ln["banda_lin_experiencia"] or 0), p(coste),
               _esc(estados.get(ln["banda_lin_estado"] or 0, "")), p(notas)])

    # Anchos: columnas fijas + una por stat (según su palabra más larga); el resto
    # se reparte entre Armamento y Notas, que nunca bajan de MIN_TEXTO entre las dos.
    ancho_total = landscape(A4)[0] - 20 * mm
    fijas = {"orden": 9, "nombre": 28, "tipo": 20, "categoria": 16, "cant": 10, "exp": 10, "coste": 15, "estado": 16}
    libre = ancho_total - sum(fijas.values()) * mm
    MIN_TEXTO = 45 * mm
    # Ancho real de la palabra más larga (Helvetica-Bold, cuerpo de la cabecera) + márgenes
    anchos_stats = [max(9 * mm, max(stringWidth(w, "Helvetica-Bold", st["cab"].fontSize)
                                    for w in e.split()) + 2 * PADDING + 2)
                    for e in etiquetas_stats]
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


def build_banda_pdf(b, plantilla, bajas, stats, estados_banda, estados_miembro, app_name):
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
        "cab": ParagraphStyle("cab", parent=base["Normal"], fontSize=6, leading=7, textColor=colors.white),
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
        story.append(_tabla_miembros(plantilla, stats, estados_miembro, st))
    else:
        story.append(Paragraph("La banda aún no tiene miembros.", st["normal"]))

    if bajas:
        story.append(Paragraph(f"Bajas: despedidos y muertos ({len(bajas)})", st["h2"]))
        story.append(_tabla_miembros(bajas, stats, estados_miembro, st))

    doc.build(story, onFirstPage=pie, onLaterPages=pie)
    return buf.getvalue()

# 09 · Ficha de banda

| | |
|---|---|
| **Ruta** | `GET /banda/<uuid:banda_id>` + acciones POST |
| **Acceso** | Lectura pública. Edición: propietario o comisario de la campaña (ADM siempre) |
| **Vista** | `app/bandas.py` (`ver`, `pdf`, `excel`, `editar`, `contratar`, `editar_miembro`, `eliminar_miembro`) |
| **Plantilla** | `app/templates/banda.html` |
| **Mockup** | `docs/material_base/03_banda_gestor_generico.png` |

## Propósito
Hoja de control de la banda: datos, miembros, bajas e historial, con su gestión.

## 1. Datos de la banda (edición in situ)
Vista: Usuario · Banda (tipo) · Campaña · **Tesorería** (en rojo si es negativa) · Coste · Estado · Observaciones.

Botón **Editar datos** (si puede editar) → el bloque se convierte en formulario (clase CSS `.editando`):

| Campo | Destino | Historial |
|---|---|---|
| Nombre | `banda_nombre` (único en campaña) | «nombre «A» → «B»» |
| Banda (tipo) | `banda_tipo` | «tipo …» |
| Tesorería | `banda_tesoreria` (**siempre editable**) | «tesorería 365 → 400 (edición manual)» |
| Estado (Activa / Destruida) | `banda_estado` | «estado Activa → Destruida» |
| Observaciones | `banda_observaciones` | «observaciones» |

`POST /banda/<id>/editar`. Sin cambios → «No hay cambios que guardar.» Reactivar una banda destruida
teniendo otra activa en la misma campaña lo impide la BBDD → mensaje de error.

## 2. Miembros de la banda
Tabla de miembros **en plantilla** (Activo o Lesionado):

Orden · Nombre (+ distintivo «Lesionado») · Tipo · Categoría · Cant. · **una columna por stat del reglamento**
(en mayúsculas y en el orden escrito) · Armamento (`nombre (precio)`) · Exp. · Coste (y `×n = total` si cantidad > 1) ·
Notas (+ observaciones) · acciones **Editar** y **Duplicar**. (No hay botón «Despedir»: el estado se cambia en el popup.)

Las columnas de stats salen de `reglas.regla_stats_especificos`, ordenadas con `regla_info.orden_stats`
(`helpers.definicion_stats` + `helpers.columnas_stats`).

## 3. Popup de miembro (contratar / editar)
Botón **+ Contratar miembro** o **Editar** abren el mismo popup `#modal-miembro`:

| Campo | Notas |
|---|---|
| Orden | Por defecto, el siguiente libre |
| Nombre, Tipo | Obligatorios |
| Categoría | Opcional, máx. 50 (`banda_lin_categoria`). Sugerencias: «Héroe», «Secuaz» y las ya usadas en la banda (`<datalist>`) |
| Cantidad | ≥ 1 (grupos de secuaces) |
| Precio | Precio base ≥ 0. Al editar se deduce: `coste − Σ armamento` |
| Stats | Un campo por stat (`stat_0…stat_n`), relleno con el valor por defecto del reglamento; numérico si el valor por defecto es número, texto si es texto (p. ej. `45°`) |
| Armamento | Filas dinámicas Nombre + Precio (`arm_nombre[]`, `arm_precio[]`), botón «+ Añadir arma o equipo» y ✕ para quitar |
| Coste del miembro | Calculado en vivo: precio + Σ armamento; `× cantidad = total`; aviso «se descontarán N de la tesorería» |
| Experiencia | ≥ 0 |
| Estado | Solo al editar: Activo / Lesionado / Despedido / Muerto |
| Notas, Observaciones | Texto libre |

### Contratar — `POST /banda/<id>/contratar`
Inserta en `bandas_lin` (estado 0), descuenta `coste × cantidad` de la tesorería, anota
«Contrata «X» (Tipo) ×n por T [equipo: …] · tesorería A → B» y recalcula el valor. Todo en una transacción.

### Duplicar
Abre el mismo popup en modo «Duplicar miembro» con los datos del miembro (tipo, categoría, cantidad, precio,
stats, armamento, experiencia), nombre «… (copia)», orden siguiente y **sin notas**. El botón «Contratar copia»
envía a `contratar`, así que cobra como una contratación normal (el aviso lo indica).

### Editar — `POST /banda/<id>/miembro/<lid>/editar`
Actualiza la línea. Detecta y anota cambios (nombre, tipo, categoría, cantidad, coste, experiencia, estado, stats,
**compra** / **retira** de equipo por nombre, notas).

- **Dinero**: si el miembro está en plantilla antes y después, **se cobra la subida** y **se devuelve la bajada**
  del coste de la línea (`coste × cantidad`). El popup lo avisa en vivo («se descontarán N» / «se devolverán N»).
  Cambiar de estado no mueve dinero.
- **Muerto**: al pasar a Muerto, las notas se sustituyen por `Muerto: dd/mm/aa`; las anteriores se guardan en el
  historial («notas anteriores: «…»»).

### Eliminar — `POST /banda/<id>/miembro/<lid>/eliminar`
Botón rojo «Eliminar miembro» dentro del popup de edición (solo en modo editar), con confirmación del navegador.
Borra la línea **sin devolver** su coste, anota «Elimina «X» (Tipo) ×n, estado E, coste C · sin devolución» y
recalcula el valor. Si ya no existe (doble clic), avisa «Ese miembro ya no existe.»

### Protección contra doble clic
Todas las acciones de esta pantalla bloquean la banda (`SELECT … FOR UPDATE`) mientras se procesan, y los cobros se restan en una sola sentencia SQL. Un doble clic o dos usuarios a la vez nunca cobran dos veces ni pisan la tesorería. En el navegador, cada formulario solo se envía una vez.

## 4. Bajas (plegable)
Miembros Despedidos o Muertos, con la misma tabla. Se pueden editar (p. ej. corregir un estado).

## 5. Historial (plegable)
Líneas de `banda_audit`, la más reciente primero: `dd/mm/aaaa hh:mm · Usuario · acción`.
Abierto por defecto si tiene 5 líneas o menos.

## 6. Botones «📄 Generar PDF» y «📊 Exportar Excel»

**Excel** — `GET /banda/<id>/excel` (`bandas.excel`), descarga `banda_<nombre>.xlsx` generado con openpyxl en
`app/excel.py` (`build_banda_xlsx`). Una hoja «Ficha» con el mismo contenido que el PDF: título, datos de la banda
(tesorería y coste como números), observaciones, tabla de miembros y de bajas (Nº, Nombre, Tipo, Categoría, Cant.,
una columna por stat, Armamento, Exp., Coste unit., Coste total, Estado, Notas, Observaciones) y pie con la fecha.
**Sin historial.** Anchos de columna ajustados al contenido e impresión apaisada a una página de ancho.

**PDF**
Junto a «Volver a campaña». Abre en una pestaña nueva `GET /banda/<id>/pdf` (`bandas.pdf`), con el mismo
acceso que la ficha (público). Usa la misma carga de datos que la pantalla (`_ficha`), así que el PDF muestra
exactamente lo mismo. Generado con reportlab en `app/pdf.py` (`build_banda_pdf`), **A4 apaisado**:

- Título (nombre de la banda) y subtítulo: tipo · campaña · reglamento.
- Tabla de datos: Usuario, Banda, Campaña, Reglamento, Tesorería, Coste, Estado (cabecera beige).
- Observaciones.
- «Miembros de la banda (n)»: Nº, Nombre, Tipo, Categoría, Cant., **una columna por stat**, Armamento, Exp., Coste
  (`xN = total`), Estado, Notas (+ observaciones). Cabecera gris oscura, filas alternas.
- «Bajas: despedidos y muertos (n)» con la misma tabla, si hay.
- Pie en cada página: título del gestor · banda · fecha de generación y «Página N».

Detalles técnicos:
- Las columnas de stats se dimensionan **midiendo el ancho real** de su palabra más larga
  (`stringWidth`, Helvetica-Bold); `impactos_totales` se muestra «IMPACTOS TOTALES» para partir por palabras.
  Si no caben, se reducen proporcionalmente reservando al menos 45 mm para Armamento + Notas.
- La fuente Helvetica no tiene «→»: en el PDF se sustituye por «->». El texto del usuario se escapa.
- Nombre del archivo sin acentos ni símbolos: «Lobos «azules» & Cía» → `banda_Lobos_azules_Cia.pdf`
  (se muestra en el navegador; se puede guardar o imprimir).

## Mensajes
««X» contratado por N.», ««X» actualizado.», ««X» despedido.», «Datos de la banda guardados.»,
«Atención: la tesorería queda en negativo (N).», «El nombre y el tipo del miembro son obligatorios.»
Sin permiso → 403.

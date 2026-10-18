# Documento técnico — Gestor de bandas genérico

**Versión:** 1.0 (beta) · **Fecha:** octubre de 2026
**Producción:** https://web-gestor-bandas-generico.vercel.app
**Repositorio:** https://github.com/Erdiabo-AI/web-gestor-bandas-generico (rama `main`)

---

## 1. Objetivo

Aplicación web para llevar las **fichas de control de campañas** de juegos de miniaturas por bandas
(Mordheim, Battlefleet Gothic, etc.). Es **genérica**: cada juego se define como un *reglamento*
cuyo JSON indica qué stats tiene un miembro de banda, de modo que la misma aplicación sirve para
juegos con perfiles completamente distintos.

Se compone de dos partes:

- **Parte 1 · Web pública** (sin login): campañas, clasificación, batallas, estadísticas, actas en
  modo lectura y contacto con el comisario de cada campaña.
- **Parte 2 · Gestor** (con login): crear campañas, gestionar las bandas propias (miembros,
  armamento, tesorería, historial), introducir actas de batalla y, para el gestor de la campaña,
  administrarla en modo comisario. El administrador global mantiene los reglamentos.

Es una variante simplificada del proyecto *web-gestor-bellvibowl* (Blood Bowl), del que reutiliza
la arquitectura, la autenticación, el contacto y la copia de seguridad. **Son proyectos totalmente
independientes**: repositorio, proyecto de Vercel y base de datos distintos.

---

## 2. Stack tecnológico

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3.12 |
| Framework | Flask 3.0.3 (blueprints, Jinja2, sesión en cookie firmada) |
| Base de datos | PostgreSQL en **Neon** (región eu-central-1), acceso con psycopg2-binary 2.9.9 |
| Configuración | python-dotenv 1.0.1 (solo en local; en Vercel, variables del panel) |
| Frontend | HTML5 + CSS3 propio (sin framework) + JavaScript básico (popups, cálculo en vivo) |
| Despliegue | Vercel, runtime `@vercel/python`, despliegue automático en cada `git push` a `main` |
| Contraseñas | `werkzeug.security` (hash PBKDF2), tokens de recuperación con SHA-256 |
| PDF | reportlab 5.0.0 (ficha de banda en A4 apaisado) |

No hay ORM: las consultas son SQL escrito a mano con parámetros (`%s`), lo que evita inyección SQL.

---

## 3. Estructura del proyecto

```
JaumeP_gestorgenerico/
├── api/index.py            Entrada serverless de Vercel (con corrección de ruta, ver §10)
├── wsgi.py                 Entrada local: python wsgi.py → http://127.0.0.1:5001
├── vercel.json             Todas las rutas → api/index.py
├── requirements.txt        Flask, psycopg2-binary, python-dotenv, reportlab
├── .env.example            Plantilla de variables (SECRET_KEY, DATABASE_URL, APP_NAME)
├── .gitignore / .vercelignore
├── app/
│   ├── __init__.py         create_app(): config, blueprints, filtro |info, variables globales
│   ├── config.py           SECRET_KEY, DATABASE_URL, APP_NAME
│   ├── db.py               get_db / query / execute / close_db
│   ├── helpers.py          Decoradores de acceso, permisos, estados, stats dinámicos
│   ├── servicios.py        Historial de banda y recálculo del valor
│   ├── auth.py             Blueprint auth: login, registro, logout, recuperación
│   ├── public.py           Blueprint public: main, campaña, batallas, estadísticas, legal, contacto, salud
│   ├── dashboard.py        Blueprint dashboard: perfil
│   ├── campanas.py         Blueprint campanas: gestión, modo comisario, suplente, mensajes
│   ├── bandas.py           Blueprint bandas: alta, ficha, edición, miembros
│   ├── batallas.py         Blueprint batallas: crear batalla, acta
│   ├── admin.py            Blueprint admin (/admin): reglamentos, notificaciones, reset, backup
│   ├── pdf.py              Generación del PDF de la ficha de banda (reportlab)
│   ├── templates/          Plantillas Jinja2 (base.html + una por pantalla; auth/ y admin/)
│   └── static/css/style.css
├── db/
│   ├── schema.sql          Esquema completo (instalación desde cero)
│   └── migracion_2026-10-18_base.sql   Migración aplicada sobre la BBDD original
└── docs/
    ├── PENDIENTES.md       Decisiones funcionales e interpretaciones
    ├── documentacion_tecnica/   (esta carpeta)
    └── material_base/      Mockups y especificación original (solo local)
```

---

## 4. Configuración

| Variable | Obligatoria | Uso |
|---|---|---|
| `SECRET_KEY` | Sí (en producción) | Firma de la cookie de sesión. Sin ella se genera una aleatoria por proceso y las sesiones se pierden en cada arranque en frío |
| `DATABASE_URL` | Sí | Cadena de conexión PostgreSQL. En Neon usar el host **`-pooler`** con `?sslmode=require` |
| `APP_NAME` | No | Título de la cabecera. Por defecto: "Gestor de Fichas de control para campañas genérico" |

- **Local:** fichero `.env` (excluido de git y de Vercel).
- **Vercel:** *Settings → Environment Variables*, con el nombre exacto, entornos Production y Preview.
  Tras añadir o cambiar una variable hay que hacer **Redeploy**.
- **Comprobación:** `GET /salud` devuelve `{"estado":"ok"}` si la BBDD está configurada y tiene el esquema.

---

## 5. Arquitectura de la aplicación

### 5.1 Ciclo de una petición

1. Vercel recibe la petición y la entrega a `api/index.py` (todas las rutas).
2. `api/index.py` restaura la ruta original si el proxy la ha reescrito a `/api/index` (§10).
3. Flask enruta al blueprint correspondiente.
4. La vista abre **una conexión por petición** (`db.get_db()`, guardada en `flask.g`), ejecuta el SQL
   y renderiza la plantilla.
5. Al terminar la petición, `close_db` cierra la conexión. Lo que no se haya confirmado se descarta.

### 5.2 Capa de datos (`app/db.py`)

| Función | Comportamiento |
|---|---|
| `get_db()` | Conexión psycopg2 por petición; `None` si no hay `DATABASE_URL` |
| `query(sql, params, one=False)` | SELECT → lista de dicts (`RealDictCursor`) o un dict. Ante error de SQL hace rollback y devuelve vacío |
| `execute(sql, params, returning=False, commit=True)` | INSERT/UPDATE/DELETE. Con `returning=True` devuelve la primera fila. **Con `commit=False` la sentencia queda en la transacción abierta**: así varias operaciones (p. ej. insertar miembro + cobrar + historial + recalcular valor) se confirman juntas en la última llamada con `commit=True` |
| `close_db()` | Cierra la conexión al final de la petición |

Los campos JSONB se escriben siempre con `psycopg2.extras.Json(...)`.

### 5.3 Blueprints y rutas

| Blueprint | Archivo | Rutas |
|---|---|---|
| `public` | public.py | `/`, `/campana/<id>`, `/campana/<id>/batallas`, `/campana/<id>/estadisticas`, `/salud`, `/aviso-legal`, `/privacidad`, `POST /contactar` |
| `auth` | auth.py | `/login`, `/registro`, `/logout`, `/recuperar`, `/restablecer/<token>` |
| `dashboard` | dashboard.py | `/perfil`, `POST /perfil/editar` |
| `campanas` | campanas.py | `/gestion-campanas`, `POST /gestion-campanas/crear`, `POST /gestion-campanas/<id>/estado`, `POST …/<id>/suplente`, `POST …/<id>/comisario`, `POST /gestion-campanas/mensaje/<nid>`, `POST /campana/<id>/contactar` |
| `bandas` | bandas.py | `/banda/nueva` (GET/POST), `/banda/<id>`, `/banda/<id>/pdf`, `POST /banda/<id>/editar`, `POST /banda/<id>/contratar`, `POST /banda/<id>/miembro/<lid>/editar`, `POST /banda/<id>/miembro/<lid>/despedir` |
| `batallas` | batallas.py | `POST /campana/<id>/batallas/crear`, `/batalla/<id>/acta` (GET/POST) |
| `admin` | admin.py | `/admin/reglamentos`, `POST /admin/reglamentos/guardar`, `POST /admin/reglamentos/<id>/borrar`, `/admin/notificaciones` (+ leída, borrar, todas leídas), `POST /admin/usuarios/<id>/reset`, `/admin/backup.sql` |

Todas las rutas con identificador usan el conversor `<uuid:…>`: un identificador mal formado da 404 sin llegar a la BBDD.

### 5.4 Plantillas y frontend

- `base.html`: cabecera (título, aviso **Modo comisario**, usuario, Mi perfil, Salir / Login),
  mensajes flash, pie (Contacto, Aviso legal, Política de privacidad), popup de contacto y el
  **sistema de popups**: `data-abrir="id"` abre, `data-cerrar` o clic en el fondo cierra;
  funciones globales `abrirModal(id)` y `cerrarModal(id)`. Bloque `{% block scripts %}` para JS de cada página.
- Filtro Jinja `|info`: convierte un JSONB (dict/lista) en texto legible (`clave: valor · …`).
- Los datos que necesita el JavaScript se pasan con `<script type="application/json">{{ datos|tojson }}</script>`,
  que es seguro frente a inyección de HTML.
- Estilos: `static/css/style.css` con variables CSS (`--bg` beige `#e8e4bc` de los mockups, `--bar`
  gris oscuro de la cabecera, `--accent` violeta de los botones). Diseño adaptable a móvil (`@media max-width: 760px`).

---

## 6. Modelo de datos

Esquema completo en `db/schema.sql`. Todas las claves primarias son `uuid` con `gen_random_uuid()`.

```
reglas 1───n campanas 1───n campanas_usuarios n───1 usuarios
                │                 │
                │                 1
                │                 │
                ├──────n bandas n─┘ 1───n bandas_lin
                │          │
                1          n
                │          │
                └──n batallas 1───n batallas_bandas
notificaciones n───1 usuarios (remitente, opcional)
notificaciones n───1 campanas (mensaje al comisario, opcional)
```

| Tabla | Contenido | Campos clave |
|---|---|---|
| `reglas` | Reglamentos (juegos) | `regla_descripcion` (nombre del juego), `regla_anyo`, `regla_version`, `regla_stats_especificos` (JSON de stats), `regla_info` (`orden_stats`) |
| `usuarios` | Cuentas | `usuario_email` (único), `usuario_password_hash`, `usuario_rol` (STD/ADM), `reset_*` |
| `campanas` | Campañas | `regla_id`, `campana_estado`, `campana_tesoreria_inicial`, `usuarios_gestor_id`, `usuarios_gestor_suplente_id` |
| `campanas_usuarios` | Inscripción usuario ↔ campaña | único (`campana_id`, `usuario_id`) |
| `bandas` | Bandas | `campana_usuario_id` (propietario), `banda_tesoreria`, `banda_valor_banda`, `banda_estado`, `banda_audit` (historial) |
| `bandas_lin` | Miembros de banda | `banda_lin_categoria` (texto libre, p. ej. Héroe/Secuaz), `banda_lin_coste` (unitario), `banda_lin_cantidad`, `banda_lin_stats`, `banda_lin_armamento`, `banda_lin_estado` |
| `batallas` | Batallas / actas | `batalla_orden` (único por campaña), `batalla_fecha`, `batalla_escenario`, `batalla_estado`, `batalla_ganador` (texto derivado) |
| `batallas_bandas` | Bandas implicadas en una batalla | `batalla_banda_ganancias`, `batalla_banda_ganador`, `batalla_banda_info` (`{"bajas": …}`) |
| `notificaciones` | Contacto y avisos | `notificacion_tipo` (CONTACTO, RECUPERACION, COMISARIO), `campana_id` (si va al comisario) |

### 6.1 Códigos de estado

| Campo | Valores |
|---|---|
| `campanas.campana_estado` | `INSCRIPCION` · `ABIERTA` · `CERRADA` |
| `bandas.banda_estado` | `1` Activa · `2` Destruida |
| `bandas_lin.banda_lin_estado` | `0` Activo · `1` Lesionado · `2` Despedido · `3` Muerto |
| `batallas.batalla_estado` | `0` Borrador · `1` Confirmada |
| `usuarios.usuario_rol` | `STD` · `ADM` (COM no se guarda: es un modo de sesión) |

Están centralizados en `app/helpers.py` (`ESTADOS_CAMPANA`, `ESTADOS_BANDA`, `ESTADOS_MIEMBRO`,
`ESTADOS_BATALLA`, `MIEMBRO_EN_PLANTILLA = (0, 1)`).

### 6.2 Formatos JSON

| Campo | Formato | Ejemplo |
|---|---|---|
| `reglas.regla_stats_especificos` | Objeto: claves = columnas de stats; valores = valor por defecto (su tipo número/texto define el tipo del campo) | `{"m": 4, "ha": 4, "hp": 3, "f": 3, "r": 3, "h": 1, "i": 4, "a": 1, "l": 7}` · `{"velocidad": 20, "giros": "45°", "blindaje": 5}` |
| `reglas.regla_info` | `{"orden_stats": [claves en el orden escrito]}` | `{"orden_stats": ["m","ha","hp","f","r","h","i","a","l"]}` |
| `bandas_lin.banda_lin_stats` | Objeto con las mismas claves del reglamento | `{"m": 4, "ha": 4, …}` |
| `bandas_lin.banda_lin_armamento` | Lista de objetos (admite repetidos y campos extra) | `[{"nombre":"Espada","precio":10},{"nombre":"Daga","precio":2},{"nombre":"Daga","precio":2}]` |
| `batallas_bandas.batalla_banda_info` | `{"bajas": "texto libre"}` | `{"bajas": "Hans (lisiado)"}` |

> **Importante:** PostgreSQL `jsonb` **no conserva el orden de las claves** (las reordena por longitud).
> Por eso el orden de las columnas de stats se guarda aparte en `regla_info.orden_stats`, y
> `helpers.definicion_stats()` lo reconstruye al leer.

### 6.3 Restricciones relevantes

- 13 claves foráneas con `ON DELETE CASCADE` (borrar una campaña borra sus bandas, miembros, batallas y mensajes).
- `bandas_una_activa_por_usuario`: índice único parcial `(campana_usuario_id) WHERE banda_estado = 1`
  → **una sola banda activa por usuario y campaña**; con la banda Destruida puede crear otra.
- `bandas (campana_id, banda_nombre)` único · `batallas (campana_id, batalla_orden)` único ·
  `batallas_bandas (batalla_id, banda_id)` único · `usuarios.usuario_email` único.

---

## 7. Roles y permisos

| Rol | Cómo se obtiene | Puede |
|---|---|---|
| Anónimo | — | Ver campañas, clasificación, batallas, actas (lectura), estadísticas; contactar |
| **STD** | Registro | Crear campañas (queda como gestor), crear su banda, gestionar **solo su banda**, crear batallas y editar actas **en borrador donde participa su banda** |
| **Gestor / suplente** | Crear la campaña / ser nombrado suplente | Cambiar estado de la campaña, leer mensajes al comisario, activar el **modo comisario**. Solo el creador nombra al suplente |
| **COM** (modo comisario) | Botón «Acceder como comisario» (gestor, suplente o ADM) | Mientras dure la sesión: editar **todas** las bandas y actas de esa campaña, reabrir actas confirmadas, eliminar batallas en borrador |
| **ADM** | `UPDATE usuarios SET usuario_rol='ADM'` en la BBDD | Todo lo anterior en todas las campañas (siempre actúa como comisario) + reglamentos, notificaciones, usuarios, copia de seguridad |

Funciones en `app/helpers.py`:

| Función | Devuelve verdadero si… |
|---|---|
| `login_required` / `admin_required` | Decoradores: hay sesión / el rol es ADM (si no: login o 403) |
| `es_gestor_campana(fila, user)` | Es ADM, gestor titular o suplente de la campaña |
| `es_comisario(campana_id, user)` | Es ADM o tiene el modo comisario activo en esa campaña (`session["com"]`) |
| `puede_editar_banda(banda, user)` | Es el propietario de la banda o comisario de su campaña |

El modo comisario se guarda en `session["com"]` (lista de ids de campaña) y se borra al iniciar o cerrar sesión.

---

## 8. Reglas de negocio

### 8.1 Campañas
- Al crearla: estado `INSCRIPCION`, formato `LIBRE`, temporada = año actual (editable), gestor = creador.
- La **tesorería inicial** se copia a cada banda en el momento de crearla.

### 8.2 Bandas
- Solo se pueden crear en campañas en `INSCRIPCION` o `ABIERTA`.
- Crear la banda inscribe al usuario en la campaña (`campanas_usuarios`) si no lo estaba.
- Una banda activa por usuario y campaña (índice único parcial). Con la banda **Destruida** puede crear otra.
- **Valor (coste) de la banda** = Σ `banda_lin_coste × banda_lin_cantidad` de los miembros **Activos y Lesionados**.
  Se recalcula (`servicios.recalcular_valor`) tras cada cambio de miembros. Es el criterio de la clasificación.

### 8.3 Miembros y tesorería
- **Coste unitario del miembro** = precio base + Σ precios del armamento. El precio base no se guarda:
  se deduce como `coste − Σ armamento` al editar.
- **Contratar** descuenta `coste × cantidad` de la tesorería.
- **Editar** cobra solo lo que **sube** el coste de la línea (`coste × cantidad` nuevo − anterior), es decir,
  equipo comprado o más unidades. Retirar equipo **no reembolsa** automáticamente.
- **Despedir** pone el estado `2` (Despedido); el miembro pasa a la lista de bajas y deja de contar en el valor.
- La **tesorería es siempre editable** a mano desde la ficha. Si queda negativa se avisa, pero se permite.
- **Categoría** del miembro (`banda_lin_categoria`): texto libre opcional (máx. 50) con sugerencias «Héroe», «Secuaz» y las ya usadas en la banda. Sus cambios quedan en el historial.

### 8.3.1 Doble clic y operaciones simultáneas
- **Navegador** (`base.html`): cada formulario POST se envía una sola vez; los botones se desactivan justo después de enviar (con `setTimeout`, para no perder el valor del botón pulsado, p. ej. `accion=confirmar`). Al volver atrás con el navegador se reactivan (`pageshow`).
- **Servidor**: toda operación que modifica una banda la bloquea con `SELECT … FOR UPDATE` (`bandas._banda_editable`) hasta confirmar. Una segunda petición simultánea espera y lee los datos ya actualizados, así que no vuelve a cobrar.
- **Cobros atómicos**: `UPDATE bandas SET banda_tesoreria = banda_tesoreria − importe … RETURNING`; el historial calcula «antes → después» a partir del valor real devuelto.
- **Despedir** es idempotente: si el miembro ya estaba despedido no se repite ni se anota.
- Probado con peticiones en paralelo: doble compra → un solo cargo; cinco contrataciones a la vez → tesorería exacta.
- **Historial**: toda acción (crear banda, contratar, editar, comprar, despedir, cambios de datos y de tesorería)
  añade una línea a `bandas.banda_audit` con el formato `dd/mm/aaaa hh:mm · Usuario · texto` (hora de
  España calculada en PostgreSQL con `AT TIME ZONE 'Europe/Madrid'`).

### 8.4 Batallas y actas
- Las actas son **informativas**: no modifican tesorería, miembros ni valor de las bandas.
- Crear una batalla: participante con banda activa (se vincula su banda) o comisario. Orden = máximo + 1,
  fecha = hoy, escenario «Por definir». No se permite en campaña `CERRADA` salvo comisario.
- En **borrador** la editan el comisario o cualquier participante con banda vinculada: fecha, escenario,
  bandas implicadas (vincular / quitar), ganancias, bajas, ganador(es) y comentarios.
- Un jugador no puede quitar su propia banda del acta.
- **Confirmar** bloquea el acta. Solo el comisario puede **reabrirla** o **eliminar** una batalla en borrador.
- `batallas.batalla_ganador` guarda los nombres de las bandas ganadoras separados por comas (para listados).

### 8.5 Estadísticas
Por banda, contando **solo actas confirmadas**: batallas jugadas, victorias, ganancias totales;
bajas = miembros en estado Muerto.

### 8.6 Notificaciones
- `CONTACTO`: formulario del pie → administrador.
- `RECUPERACION`: solicitud de contraseña → administrador.
- `COMISARIO`: botón de la página de campaña → gestor de esa campaña (`campana_id` con valor).
  El ADM no los ve en su bandeja; el gestor los ve en Gestión de campañas.

### 8.7 Recuperación de contraseña (sin correo electrónico)
1. El usuario la pide en `/recuperar` (se anota `reset_solicitado` y se crea una notificación; no se revela si el email existe).
2. El ADM genera un enlace en Gestión de campañas · Bloque 3: token aleatorio de 32 bytes, se guarda su hash SHA-256 y caduca a las 24 h.
3. El ADM hace llegar el enlace; el usuario abre `/restablecer/<token>` y fija la contraseña nueva (mínimo 8 caracteres).

---

## 9. Seguridad

| Aspecto | Medida |
|---|---|
| Contraseñas | Hash de werkzeug; mínimo 8 caracteres; nunca se guardan ni se muestran en claro |
| Sesión | Cookie firmada con `SECRET_KEY`; solo guarda id, nombre, rol y modo comisario |
| Inyección SQL | Siempre consultas parametrizadas |
| XSS | Autoescape de Jinja; datos a JavaScript con `tojson`; los `confirm()` no interpolan datos de usuario |
| Permisos | Comprobados en el servidor en cada POST (403 si no corresponde), no solo ocultando botones |
| Concurrencia | Bloqueo de fila por banda, cobros atómicos y protección de doble envío (§8.3.1) |
| Redirecciones | Tras contactar solo se vuelve al `referrer` si es del mismo host |
| Tokens de recuperación | Solo se guarda el hash; un uso; caducidad 24 h |
| Secretos | `.env` y `.env.*` fuera de git y de Vercel; `/salud` no muestra la cadena de conexión |
| Datos personales | Mockups con email excluidos del repositorio público |
| Cookies | Una única cookie técnica de sesión (sin banner de consentimiento) |

---

## 10. Despliegue en Vercel

- `vercel.json` usa el formato `builds` + `routes`: todo va a `api/index.py`.
- **Corrección de ruta en `api/index.py`:** desde 2026 el proxy de Vercel puede entregar la petición con
  `PATH_INFO=/api/index` en lugar de la ruta original. Un WSGI intermedio recupera la ruta real de las
  cabeceras (`x-vercel-original-path`, `x-original-path`, `x-forwarded-uri`, `x-rewrite-url` o
  `x-now-route-matches`) antes de pasarla a Flask. Si no la encuentra, `/api/index` muestra una página
  de «Mantenimiento» (503) en lugar de un 404.
- `.vercelignore` excluye `docs/`, `db/`, `.env*`, `.venv`, `.claude`, `wsgi.py`, `*.md` y PDF.
- Flujo: `git push origin main` → Vercel despliega solo en ~1 minuto.
- Tras cambiar variables de entorno: *Deployments → ⋯ → Redeploy*.

### 10.1 Base de datos nueva desde cero
```
psql "$DATABASE_URL" -f db/schema.sql
```
Después, registrar el primer usuario en la web y darle rol ADM:
```sql
UPDATE usuarios SET usuario_rol = 'ADM' WHERE usuario_email = 'correo@ejemplo.com';
```

---

## 11. Desarrollo local

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env        (rellenar SECRET_KEY y DATABASE_URL)
.venv\Scripts\python wsgi.py  → http://127.0.0.1:5001
```
El puerto 5001 evita el choque con BellviBowl (5000).

---

## 12. Pruebas realizadas

- **Prueba de punta a punta** con el cliente de pruebas de Flask y cuatro usuarios (ADM, gestor, dos jugadores):
  64 comprobaciones de reglas de negocio y permisos (cobros, historial, una banda activa, modo comisario,
  actas, estadísticas, mensajes, suplente, reglamentos, copia de seguridad). Los datos se crean con dominio
  `@e2e.test` y se borran al terminar.
- **Navegador:** popups de miembro (coste en vivo, filas de armamento, aviso de cobro), edición in situ,
  popup de reglamentos; sin errores de JavaScript.
- **Producción:** `/salud`, todas las rutas públicas, redirecciones a login y 404.

---

## 13. Mantenimiento

| Tarea | Cómo |
|---|---|
| Cambio de esquema | Crear `db/migracion_AAAA-MM-DD_descripcion.sql` (en transacción), aplicarlo, y actualizar `db/schema.sql` |
| Nueva pantalla | Ruta en el blueprint que corresponda + plantilla que extienda `base.html` + documento en `pantallas/` |
| Nuevo juego | Desde la web: Reglamentos → Nuevo, con su JSON de stats (no requiere código) |
| Nuevo estado | Añadirlo en `helpers.py` y documentarlo en la cabecera de `db/schema.sql` |
| Copia de seguridad | Perfil → Opciones de administrador → Copia de seguridad BBDD |
| Cambiar contraseña de Neon | Neon → Roles → Reset password; actualizar `DATABASE_URL` en Vercel (+ Redeploy) y en `.env` |

---

## 14. Limitaciones conocidas y campos sin uso

- Sin envío de correo: la recuperación de contraseña depende del administrador.
- Sin subida de archivos (Vercel no conserva ficheros): `campana_logo_path` y `banda_logo_path` sin uso.
- Sin uso en esta versión: `campana_ia_clave`, `campana_ia_activa`, `campana_adicional`, `batallas.batalla_info`,
  `bandas_lin.banda_lin_nivel`, `bandas_lin.banda_lin_audit`.
- El historial es texto acumulado en `banda_audit`; para auditorías complejas convendría una tabla propia.

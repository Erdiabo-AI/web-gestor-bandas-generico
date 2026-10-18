# 13 · Legal y contacto

| Elemento | Ruta | Vista | Plantilla |
|---|---|---|---|
| Aviso legal | `GET /aviso-legal` | `public.aviso_legal` | `legal.html` (`pagina='aviso'`) |
| Política de privacidad | `GET /privacidad` | `public.privacidad` | `legal.html` |
| Popup de contacto | `POST /contactar` | `public.contactar` | en `base.html` (`#modal-contacto`) |

Acceso público. Enlaces en el pie de todas las páginas.

## Aviso legal
Objeto y titularidad (aplicación sin ánimo de lucro de aficionados), condiciones de uso, servicio en beta
sin garantías, y propiedad intelectual: Mordheim y demás juegos pertenecen a sus titulares (Games Workshop);
la web no es oficial y no reproduce reglamentos.

## Política de privacidad (RGPD)
Responsable, datos recogidos (cuenta, datos de juego, mensajes de contacto), finalidad única, base jurídica
(art. 6.1.a y 6.1.b), alojamiento en Vercel y Neon (UE), conservación, derechos ARSOPL vía Contacto y AEPD,
y cookies: **una única cookie técnica de sesión**, sin banner.

## Popup de contacto
Se abre desde «Contacto» del pie.

| Campo | Reglas |
|---|---|
| Tu nombre | Opcional, máx. 100 (relleno si hay sesión) |
| Tu email | Obligatorio, máx. 150 |
| Mensaje | Obligatorio, máx. 2000 |

Crea una notificación `CONTACTO` (sin campaña) para el ADM → [11 · Notificaciones](11_notificaciones.md).
Vuelve a la página de origen solo si el `referrer` es del mismo dominio; si no, a Main.
Mensajes: «Mensaje enviado al administrador. ¡Gracias!» / «Escribe tu email y el mensaje para contactar.»

> Para escribir al comisario de una campaña concreta se usa el botón de la [página de campaña](02_campana.md).

## Pie de página
Mismo fondo beige que el cuerpo (`--bg`), línea superior suave y texto gris oscuro `#4b5563` para buen contraste.

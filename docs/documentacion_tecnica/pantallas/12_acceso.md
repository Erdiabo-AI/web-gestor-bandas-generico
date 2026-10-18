# 12 · Acceso: login, registro y recuperación de contraseña

| Pantalla | Ruta | Plantilla | Mockup |
|---|---|---|---|
| Iniciar sesión | `GET/POST /login` | `auth/login.html` | `06_acceso_login_gestor_generico.png` |
| Crear cuenta | `GET/POST /registro` | `auth/register.html` | `07_registro_usuario_gestor_generico.png` |
| Recuperar contraseña | `GET/POST /recuperar` | `auth/recuperar.html` | `07_registro_recuperar_pass_gestor_generico.png` |
| Nueva contraseña | `GET/POST /restablecer/<token>` | `auth/restablecer.html` | — |
| Cerrar sesión | `GET /logout` | — | — |

Vistas en `app/auth.py`. Acceso público. Se usan páginas (no popups) por decisión C2.

## Login
| Campo | Reglas |
|---|---|
| Email | Obligatorio; se compara en minúsculas |
| Contraseña | Se verifica con `check_password_hash` |

Éxito: guarda en sesión `{id, nombre, rol}`, borra el modo comisario y va al [perfil](06_perfil.md).
Error: «Email o contraseña incorrectos.» (mismo mensaje exista o no el email).
Enlaces a **Regístrate** y **Recupérala**.

## Registro
| Campo | Reglas |
|---|---|
| Nombre | Obligatorio, máx. 100 |
| Email | Obligatorio, máx. 150, único |
| Contraseña | Mínimo **8** caracteres (validado en navegador y servidor; aviso visible) |

Crea el usuario con rol `STD`, abre sesión y redirige a la **página Main** (decisión C3).

| Situación | Mensaje |
|---|---|
| Faltan campos | «Nombre, email y contraseña son obligatorios.» |
| Contraseña corta | «La contraseña debe tener al menos 8 caracteres.» |
| Email repetido (`IntegrityError`) | «Ese email ya está registrado. Inicia sesión o recupera la contraseña.» |
| Fallo de BBDD (sin `DATABASE_URL`, sin conexión) | «No se pudo registrar por un problema con la base de datos. Avisa al administrador.» + error en los logs de Vercel |

## Recuperación de contraseña (sin correo)
1. **`/recuperar`**: el usuario escribe su email. Se anota `usuarios.reset_solicitado = now()` y se crea una
   notificación `RECUPERACION` para el ADM. El mensaje es el mismo exista o no el email (no se revela).
2. **ADM**: en [Gestión de campañas · Bloque 3](07_gestion_campanas.md) pulsa **Enlace de contraseña**
   (`POST /admin/usuarios/<id>/reset`): token `secrets.token_urlsafe(32)`, se guarda **solo su hash SHA-256**
   en `reset_token_hash`, caducidad `reset_expira = now() + 24 h`. El enlace se muestra al ADM en un aviso.
3. **`/restablecer/<token>`**: si el hash coincide y no ha caducado, pide contraseña y confirmación (mín. 8,
   iguales). Al guardar limpia `reset_token_hash`, `reset_expira` y `reset_solicitado`.
   Enlace inválido o caducado → «El enlace de recuperación no es válido o ha caducado…».

## Logout
Borra `user` y `com` de la sesión → Main con «Sesión cerrada.»

## Alta del primer administrador
No hay pantalla: tras registrarse, en la BBDD
`UPDATE usuarios SET usuario_rol = 'ADM' WHERE usuario_email = '…';`

"""Autenticación: login, registro, logout y recuperación de contraseña."""
import hashlib

import psycopg2
from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash, current_app)
from werkzeug.security import generate_password_hash, check_password_hash

from . import db

bp = Blueprint("auth", __name__)

MIN_PASSWORD = 8


def _password_valida(pwd):
    return bool(pwd) and len(pwd) >= MIN_PASSWORD


def _abrir_sesion(row):
    session.pop("com", None)
    session["user"] = {
        "id": str(row["usuario_id"]),
        "nombre": row["usuario_nombre"],
        "rol": row["usuario_rol"],
    }


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db.query(
            """
            SELECT usuario_id, usuario_nombre, usuario_rol, usuario_password_hash
            FROM usuarios WHERE lower(usuario_email) = %s
            """,
            (email,), one=True,
        )
        if user and check_password_hash(user["usuario_password_hash"], password):
            _abrir_sesion(user)
            flash("Sesión iniciada.", "success")
            return redirect(url_for("dashboard.perfil"))
        flash("Email o contraseña incorrectos.", "danger")
    return render_template("auth/login.html")


@bp.route("/registro", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not (nombre and email and password):
            flash("Nombre, email y contraseña son obligatorios.", "warning")
            return render_template("auth/register.html")
        if not _password_valida(password):
            flash(f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres.", "warning")
            return render_template("auth/register.html")

        try:
            row = db.execute(
                """
                INSERT INTO usuarios
                    (usuario_nombre, usuario_email, usuario_password_hash, usuario_rol)
                VALUES (%s, %s, %s, 'STD')
                RETURNING usuario_id, usuario_nombre, usuario_rol
                """,
                (nombre, email, generate_password_hash(password)),
                returning=True,
            )
        except psycopg2.IntegrityError:
            db.get_db().rollback()
            flash("Ese email ya está registrado. Inicia sesión o recupera la contraseña.", "danger")
            return render_template("auth/register.html")
        except Exception:
            # Sin DATABASE_URL o sin conexión: se registra en los logs (Vercel → Logs)
            current_app.logger.exception("Registro: error de base de datos")
            flash("No se pudo registrar por un problema con la base de datos. "
                  "Avisa al administrador.", "danger")
            return render_template("auth/register.html")

        if row:
            _abrir_sesion(row)
            flash("Registro completado.", "success")
        return redirect(url_for("public.index"))

    return render_template("auth/register.html")


@bp.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("com", None)
    flash("Sesión cerrada.", "info")
    return redirect(url_for("public.index"))


# ---------------------------------------------------------------------------
#  Recuperación de contraseña (sin SMTP):
#  1) El usuario la solicita en /recuperar (queda registrada la solicitud y
#     se crea una notificación al administrador).
#  2) El ADM genera un enlace de un solo uso desde Gestión de campañas · Bloque 3
#     y se lo hace llegar al usuario.
#  3) El usuario abre /restablecer/<token> y fija su nueva contraseña.
# ---------------------------------------------------------------------------
def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


@bp.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        if email:
            # Registrar la solicitud (sin revelar si el email existe)
            db_ok = True
            try:
                db.execute(
                    "UPDATE usuarios SET reset_solicitado = now() WHERE lower(usuario_email) = %s",
                    (email,),
                )
                db.execute(
                    """INSERT INTO notificaciones
                           (notificacion_tipo, remitente_email, mensaje)
                       VALUES ('RECUPERACION', %s, %s)""",
                    (email[:150],
                     f"Solicitud de recuperación de contraseña para {email}. "
                     "Genera el enlace desde Gestión de campañas · Bloque 3."),
                )
            except Exception:
                db_ok = False
            if db_ok:
                flash("Solicitud registrada. El administrador te hará llegar un enlace "
                      "para restablecer la contraseña.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/recuperar.html")


@bp.route("/restablecer/<token>", methods=["GET", "POST"])
def restablecer(token):
    user = db.query(
        """SELECT usuario_id, usuario_nombre FROM usuarios
           WHERE reset_token_hash = %s AND reset_expira > now()""",
        (hash_token(token),), one=True,
    )
    if not user:
        flash("El enlace de recuperación no es válido o ha caducado. "
              "Pide uno nuevo al administrador.", "warning")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        password = request.form.get("password") or ""
        confirmar = request.form.get("confirmar") or ""
        if not _password_valida(password):
            flash(f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres.", "warning")
        elif password != confirmar:
            flash("Las contraseñas no coinciden.", "warning")
        else:
            db.execute(
                """UPDATE usuarios SET usuario_password_hash = %s,
                       reset_token_hash = NULL, reset_expira = NULL, reset_solicitado = NULL
                   WHERE usuario_id = %s""",
                (generate_password_hash(password), str(user["usuario_id"])),
            )
            flash("Contraseña restablecida. Ya puedes iniciar sesión.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/restablecer.html", nombre=user["usuario_nombre"])

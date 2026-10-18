from flask import Flask

from .config import Config
from . import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.teardown_appcontext(db.close_db)

    # Blueprints
    from .public import bp as public_bp
    from .auth import bp as auth_bp
    from .dashboard import bp as dashboard_bp
    from .admin import bp as admin_bp
    from .campanas import bp as campanas_bp
    from .bandas import bp as bandas_bp
    from .batallas import bp as batallas_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(campanas_bp)
    app.register_blueprint(bandas_bp)
    app.register_blueprint(batallas_bp)

    from .helpers import formato_info
    app.add_template_filter(formato_info, "info")

    # Variables disponibles en todas las plantillas
    @app.context_processor
    def inject_globals():
        from flask import session
        return {
            "current_user": session.get("user"),
            "app_name": app.config["APP_NAME"],
            "modo_comisario": bool(session.get("com")),
        }

    return app

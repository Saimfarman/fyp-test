from quart import Quart, jsonify
from quart_cors import cors

from .auth import bp as auth_bp
from .config import Settings
from .db import create_session_factory
from .health import bp as health_bp
from .workspaces import bp as workspaces_bp
from .discovery import bp as discovery_bp
from .audits import bp as audits_bp
from .pitches import bp as pitches_bp
from .prototypes import bp as prototypes_bp
from .platform import bp as platform_bp
from .security import bp as security_bp


def create_app() -> Quart:
    settings = Settings.from_env()
    app = Quart(__name__)
    app.config.from_mapping(SECRET_KEY=settings.secret_key, SESSION_COOKIE_SECURE=settings.session_cookie_secure)
    app.session_factory = create_session_factory(settings)
    app = cors(app, allow_origin=settings.frontend_origin, allow_credentials=True)
    app.register_blueprint(security_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(workspaces_bp)
    app.register_blueprint(discovery_bp)
    app.register_blueprint(audits_bp)
    app.register_blueprint(pitches_bp)
    app.register_blueprint(prototypes_bp)
    app.register_blueprint(platform_bp)

    @app.get("/openapi.json")
    async def root_openapi():
        return jsonify({
            "openapi": "3.0.3",
            "info": {"title": "LeadPitch API", "version": "1.0.0"},
            "paths": {
                "/api/v1/leads": {"get": {"security": [{"ApiKey": []}], "responses": {"200": {"description": "Workspace leads"}}}},
                "/api/v1/audits": {"get": {"security": [{"ApiKey": []}], "responses": {"200": {"description": "Workspace audits"}}}},
            },
            "components": {"securitySchemes": {"ApiKey": {"type": "http", "scheme": "bearer"}}},
        })
    return app

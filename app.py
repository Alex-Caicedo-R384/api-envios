from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from sqlalchemy.exc import SQLAlchemyError
from db import db
import os

app = Flask(__name__)
CORS(app)

# ----------------------------
# CONFIG BD (DOCKER + LOCAL)
# ----------------------------
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/enviosdb"
)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# ----------------------------
# MODELO ENVÍO (COHERENTE)
# ----------------------------
class Envio(db.Model):
    __tablename__ = "envios"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    destinatario = db.Column(db.String(120), nullable=False)
    direccion = db.Column(db.String(200), nullable=False)
    estado = db.Column(db.String(30), nullable=False, default="Registrado")
    fecha_registro = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "destinatario": self.destinatario,
            "direccion": self.direccion,
            "estado": self.estado,
            "fecha_registro": str(self.fecha_registro),
        }

# ----------------------------
# SWAGGER UI
# ----------------------------
SWAGGER_URL = "/api-docs"
API_URL = "/static/openapi.yaml"

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={"app_name": "API de Envíos - Flask + PostgreSQL + Docker"}
)

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

# ----------------------------
# RESPUESTAS ESTÁNDAR
# ----------------------------
def ok(data, code=200):
    return jsonify({"success": True, "data": data}), code

def error(message, code=400):
    return jsonify({"success": False, "error": message}), code

# ----------------------------
# ENDPOINT HEALTH
# ----------------------------
@app.route("/health", methods=["GET"])
def health():
    return ok({"status": "ok"})

# ----------------------------
# LISTAR ENVIOS
# ----------------------------
@app.route("/envios", methods=["GET"])
def listar_envios():
    envios = Envio.query.all()
    return ok([e.to_dict() for e in envios])

# ----------------------------
# OBTENER ENVÍO POR ID
# ----------------------------
@app.route("/envios/<int:id>", methods=["GET"])
def obtener_envio(id):
    envio = Envio.query.get(id)
    if not envio:
        return error("Envío no encontrado", 404)
    return ok(envio.to_dict())

# ----------------------------
# CREAR ENVÍO
# ----------------------------
@app.route("/envios", methods=["POST"])
def crear_envio():
    data = request.json or {}

    # Validaciones
    required = ["destinatario", "direccion"]
    missing = [f for f in required if f not in data]

    if missing:
        return error(f"Faltan campos obligatorios: {', '.join(missing)}", 400)

    envio = Envio(
        destinatario=data["destinatario"],
        direccion=data["direccion"],
        estado=data.get("estado", "Registrado")
    )

    try:
        db.session.add(envio)
        db.session.commit()
        return ok(envio.to_dict(), 201)
    except SQLAlchemyError:
        db.session.rollback()
        return error("Error al guardar en la base de datos", 500)

# ----------------------------
# EJECUTAR APP
# ----------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Crear tablas en PostgreSQL
    app.run(host="0.0.0.0", port=8080)

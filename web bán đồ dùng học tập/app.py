from pathlib import Path

import pyodbc
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from auth_utils import current_user, refresh_session_user
from config import Config
from db import fetch_all
from routes.admin import admin_bp
from routes.admin_api import admin_api_bp
from routes.activity import activity_bp
from routes.auth import auth_bp
from routes.brands import brands_bp
from routes.categories import categories_bp
from routes.customers import customers_bp
from routes.orders import orders_bp
from routes.products import products_bp
from routes.reviews import reviews_bp
from routes.promotions import promotions_bp
from routes.site import site_bp

app = Flask(__name__)
app.config.from_object(Config)
app.json.ensure_ascii = False
app.url_map.strict_slashes = False
CORS(app)
IMAGE_DIR = Path(app.root_path) / "images"


app.register_blueprint(categories_bp, url_prefix="/api/categories")
app.register_blueprint(brands_bp,     url_prefix="/api/brands")
app.register_blueprint(products_bp,   url_prefix="/api/products")
app.register_blueprint(customers_bp,  url_prefix="/api/customers")
app.register_blueprint(orders_bp,     url_prefix="/api/orders")
app.register_blueprint(reviews_bp,    url_prefix="/api/reviews")
app.register_blueprint(promotions_bp, url_prefix="/api/promotions")
app.register_blueprint(activity_bp, url_prefix="/api/activity")
app.register_blueprint(admin_api_bp, url_prefix="/api/admin")
app.register_blueprint(site_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)


@app.context_processor
def inject_auth_state():
    categories = []
    try:
        if request.blueprint not in {"admin", "auth"}:
            categories = fetch_all(
                """
                SELECT CategoryID, CategoryName
                FROM dbo.Categories
                ORDER BY CategoryName
                """
            )
    except Exception:
        categories = []

    return {
        "current_user": current_user(),
        "header_categories": categories,
        "header_search": request.args.get("search", ""),
        "header_selected_category_id": request.args.get("category_id", type=int),
    }


@app.before_request
def sync_logged_in_user():
    refresh_session_user()


@app.errorhandler(pyodbc.Error)
def handle_database_error(error):
    message = "Không thể kết nối cơ sở dữ liệu. Hãy kiểm tra cấu hình SQL Server trong config.py."
    if request.path.startswith("/api/"):
        return jsonify({"error": message, "details": str(error)}), 503
    return (
        f"<h1>Lỗi cơ sở dữ liệu</h1><p>{message}</p><pre>{error}</pre>",
        503,
        {"Content-Type": "text/html; charset=utf-8"},
    )

@app.route("/api/health")
def health():
    database_connected = True
    details = None
    try:
        rows = fetch_all("SELECT TOP 1 name FROM sys.databases WHERE name = DB_NAME()")
        database_connected = bool(rows)
    except pyodbc.Error as exc:
        database_connected = False
        details = str(exc)

    payload = {
        "status": "ok" if database_connected else "degraded",
        "database": Config.DB_DATABASE,
        "driver": Config.DB_DRIVER,
        "database_connected": database_connected,
    }
    if details:
        payload["details"] = details
    return jsonify(payload), (200 if database_connected else 503)


@app.route("/images/<path:filename>")
def product_image(filename):
    return send_from_directory(IMAGE_DIR, filename)

if __name__ == "__main__":
    app.run(debug=True, port=3000)

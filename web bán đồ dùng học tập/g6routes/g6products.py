from pathlib import Path
import re
import unicodedata

from flask import Blueprint, jsonify, request

from g6db import fetch_one, get_db_connection, rows_to_dicts
from g6utils.g6image_uploads import IMAGE_EXTENSIONS, save_product_image

products_bp = Blueprint("products", __name__)
IMAGE_DIR = Path(__file__).resolve().parent.parent / "g6images"

PRODUCT_SELECT = """
    SELECT
        p.ProductID,
        p.SKU,
        p.ProductName,
        p.Description,
        p.CategoryID,
        c.CategoryName,
        p.BrandID,
        b.BrandName,
        p.Price,
        p.Stock,
        p.Unit,
        p.ImageURL,
        p.IsActive,
        p.CreatedAt,
        p.UpdatedAt
    FROM dbo.Products p
    INNER JOIN dbo.Categories c ON c.CategoryID = p.CategoryID
    LEFT JOIN dbo.Brands b ON b.BrandID = p.BrandID
"""


def normalize_text(value):
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def get_uploaded_image():
    return request.files.get("image") or request.files.get("image_file") or request.files.get("file")


def resolve_local_image(product):
    candidates = []

    sku = (product.get("SKU") or "").strip()
    name = (product.get("ProductName") or "").strip()

    if sku:
        candidates.append(sku)
        candidates.append(sku.lower())
        candidates.append(f"g6{sku}")
        candidates.append(f"g6{sku.lower()}")
    if name:
        candidates.append(name)
        candidates.append(normalize_text(name))
        candidates.append(f"g6{name}")
        candidates.append(f"g6{normalize_text(name)}")

    for base_name in candidates:
        if not base_name:
            continue
        for extension in IMAGE_EXTENSIONS:
            image_path = IMAGE_DIR / f"{base_name}{extension}"
            if image_path.exists():
                return f"/images/{image_path.name}"

    return None


def normalize_image_url(image_url):
    raw = (image_url or "").strip()
    if not raw:
        return None

    filename = Path(raw.replace("\\", "/")).name
    if not filename:
        return None

    direct_path = IMAGE_DIR / filename
    if direct_path.exists():
        return f"/images/{filename}"

    g6_direct_path = IMAGE_DIR / f"g6{filename}"
    if g6_direct_path.exists():
        return f"/images/{g6_direct_path.name}"

    stem = Path(filename).stem
    for extension in IMAGE_EXTENSIONS:
        candidate = IMAGE_DIR / f"{stem}{extension}"
        if candidate.exists():
            return f"/images/{candidate.name}"
        g6_candidate = IMAGE_DIR / f"g6{stem}{extension}"
        if g6_candidate.exists():
            return f"/images/{g6_candidate.name}"

    return None


def attach_image_url(product):
    image_url = normalize_image_url(product.get("ImageURL"))
    if image_url:
        product["ImageURL"] = image_url
        return product

    local_image = resolve_local_image(product)
    if local_image:
        product["ImageURL"] = local_image
    return product

# ======================
# GET ALL (filter + pagination)
# ======================
@products_bp.route("/", methods=["GET"])
def get_all():
    category_id = request.args.get("category_id", type=int)
    brand_id    = request.args.get("brand_id", type=int)
    is_active   = request.args.get("is_active")
    search      = request.args.get("search", "")
    min_price   = request.args.get("min_price", type=float)
    max_price   = request.args.get("max_price", type=float)

    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 12, type=int)
    page = max(page, 1)
    limit = max(min(limit, 100), 1)
    offset = (page - 1) * limit

    where_clauses = ["1 = 1"]
    params = []

    if category_id:
        where_clauses.append("p.CategoryID = ?")
        params.append(category_id)

    if brand_id:
        where_clauses.append("p.BrandID = ?")
        params.append(brand_id)

    if is_active is not None:
        where_clauses.append("p.IsActive = ?")
        params.append(1 if is_active.lower() == "true" else 0)

    if search:
        where_clauses.append("(p.ProductName LIKE ? OR ISNULL(p.Description, '') LIKE ? OR p.SKU LIKE ?)")
        keyword = f"%{search}%"
        sku_keyword = f"{search}%"
        params.extend([keyword, keyword, sku_keyword])

    if min_price is not None:
        where_clauses.append("p.Price >= ?")
        params.append(min_price)

    if max_price is not None:
        where_clauses.append("p.Price <= ?")
        params.append(max_price)

    where_sql = " WHERE " + " AND ".join(where_clauses)

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(f"SELECT COUNT(*) AS Total FROM dbo.Products p {where_sql}", params)
        total = cursor.fetchone()[0]

        cursor.execute(
            f"""
            {PRODUCT_SELECT}
            {where_sql}
            ORDER BY p.ProductID DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            """,
            params + [offset, limit],
        )
        result = [attach_image_url(item) for item in rows_to_dicts(cursor, cursor.fetchall())]
    finally:
        connection.close()

    return jsonify({"data": result, "total": total, "page": page, "limit": limit})


# ======================
# GET ONE
# ======================
@products_bp.route("/<int:product_id>", methods=["GET"])
def get_one(product_id):
    product = fetch_one(f"{PRODUCT_SELECT} WHERE p.ProductID = ?", (product_id,))
    if not product:
        return jsonify({"error": "Không tìm thấy sản phẩm"}), 404
    return jsonify(attach_image_url(product))


# ======================
# GET BY SKU
# ======================
@products_bp.route("/sku/<string:sku>", methods=["GET"])
def get_by_sku(sku):
    product = fetch_one(f"{PRODUCT_SELECT} WHERE p.SKU = ?", (sku,))
    if not product:
        return jsonify({"error": "Không tìm thấy sản phẩm"}), 404
    return jsonify(attach_image_url(product))


# ======================
# CREATE
# ======================
@products_bp.route("/", methods=["POST"])
def create():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    required_fields = ["SKU", "ProductName", "CategoryID", "Price"]
    missing_fields = [field for field in required_fields if data.get(field) in (None, "")]
    if missing_fields:
        return jsonify({"error": f"Thiếu trường bắt buộc: {', '.join(missing_fields)}"}), 400

    try:
        image_url = save_product_image(get_uploaded_image(), data.get("SKU")) or data.get("ImageURL")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO dbo.Products (
                SKU, ProductName, Description, CategoryID, BrandID,
                Price, Stock, Unit, ImageURL, IsActive
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["SKU"],
                data["ProductName"],
                data.get("Description"),
                data["CategoryID"],
                data.get("BrandID"),
                data["Price"],
                data.get("Stock", 0),
                data.get("Unit", "Cái"),
                image_url,
                data.get("IsActive", True),
            ),
        )
        connection.commit()
    finally:
        connection.close()

    return jsonify({"message": "Tạo sản phẩm thành công"}), 201


# ======================
# UPDATE
# ======================
@products_bp.route("/<int:product_id>", methods=["PUT"])
def update(product_id):
    data = request.form if request.form else (request.get_json(silent=True) or {})
    allowed_fields = [
        "SKU",
        "ProductName",
        "Description",
        "CategoryID",
        "BrandID",
        "Price",
        "Stock",
        "Unit",
        "ImageURL",
        "IsActive",
    ]
    payload = {field: data[field] for field in allowed_fields if field in data}
    try:
        uploaded_image_url = save_product_image(get_uploaded_image(), data.get("SKU"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if uploaded_image_url:
        payload["ImageURL"] = uploaded_image_url
    if not payload:
        return jsonify({"error": "Không có dữ liệu cần cập nhật"}), 400

    set_clause = ", ".join(f"{field} = ?" for field in payload)
    params = list(payload.values()) + [product_id]

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            UPDATE dbo.Products
            SET {set_clause}, UpdatedAt = GETDATE()
            WHERE ProductID = ?
            """,
            params,
        )
        if cursor.rowcount == 0:
            return jsonify({"error": "Không tìm thấy sản phẩm"}), 404
        connection.commit()
    finally:
        connection.close()

    return jsonify({"message": "Cập nhật sản phẩm thành công"})


# ======================
# DELETE
# ======================
@products_bp.route("/<int:product_id>", methods=["DELETE"])
def delete(product_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM dbo.Products WHERE ProductID = ?", (product_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Không tìm thấy sản phẩm"}), 404
        connection.commit()
    finally:
        connection.close()

    return jsonify({"message": "Đã xoá sản phẩm"})


# ======================
# UPDATE STOCK
# ======================
@products_bp.route("/<int:product_id>/stock", methods=["PATCH"])
def update_stock(product_id):
    data = request.get_json(silent=True) or {}
    delta = int(data.get("delta", 0))

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT Stock FROM dbo.Products WHERE ProductID = ?", (product_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Không tìm thấy sản phẩm"}), 404

        new_stock = max(0, row[0] + delta)
        cursor.execute(
            """
            UPDATE dbo.Products
            SET Stock = ?, UpdatedAt = GETDATE()
            WHERE ProductID = ?
            """,
            (new_stock, product_id),
        )
        connection.commit()
    finally:
        connection.close()

    return jsonify({"ProductID": product_id, "Stock": new_stock})


# ======================
# LOW STOCK
# ======================
@products_bp.route("/low-stock", methods=["GET"])
def low_stock():
    threshold = request.args.get("threshold", 10, type=int)
    threshold = max(threshold, 0)

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            {PRODUCT_SELECT}
            WHERE p.Stock <= ? AND p.IsActive = 1
            ORDER BY p.Stock ASC, p.ProductID DESC
            """,
            (threshold,),
        )
        result = [attach_image_url(item) for item in rows_to_dicts(cursor, cursor.fetchall())]
    finally:
        connection.close()

    return jsonify({"data": result, "threshold": threshold, "total": len(result)})


# ======================
# SEARCH SUGGESTIONS
# ======================
@products_bp.route("/suggestions", methods=["GET"])
def suggestions():
    keyword = (request.args.get("q") or "").strip()
    limit = request.args.get("limit", 8, type=int)
    limit = max(min(limit, 20), 1)

    if not keyword:
        return jsonify({"data": [], "total": 0})

    like_keyword = f"%{keyword}%"
    sku_keyword = f"{keyword}%"

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT TOP (?) p.ProductID, p.SKU, p.ProductName, p.Price, p.Stock, p.ImageURL
            FROM dbo.Products p
            WHERE p.IsActive = 1
              AND (p.ProductName LIKE ? OR ISNULL(p.Description, '') LIKE ? OR p.SKU LIKE ?)
            ORDER BY
              CASE WHEN p.ProductName LIKE ? THEN 0 ELSE 1 END,
              p.ProductID DESC
            """,
            (limit, like_keyword, like_keyword, sku_keyword, sku_keyword),
        )
        result = [attach_image_url(item) for item in rows_to_dicts(cursor, cursor.fetchall())]
    finally:
        connection.close()

    return jsonify({"data": result, "total": len(result)})


# ======================
# BEST SELLERS
# ======================
@products_bp.route("/best-sellers", methods=["GET"])
def best_sellers():
    limit = request.args.get("limit", 8, type=int)
    limit = max(min(limit, 20), 1)

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT TOP (?)
                p.ProductID,
                p.SKU,
                p.ProductName,
                p.Price,
                p.Stock,
                p.Unit,
                p.ImageURL,
                c.CategoryName,
                b.BrandName,
                ISNULL(SUM(oi.Quantity), 0) AS TotalSold
            FROM dbo.Products p
            INNER JOIN dbo.Categories c ON c.CategoryID = p.CategoryID
            LEFT JOIN dbo.Brands b ON b.BrandID = p.BrandID
            LEFT JOIN dbo.OrderItems oi ON oi.ProductID = p.ProductID
            LEFT JOIN dbo.Orders o ON o.OrderID = oi.OrderID AND o.OrderStatus <> 'cancelled'
            WHERE p.IsActive = 1
            GROUP BY
                p.ProductID, p.SKU, p.ProductName, p.Price, p.Stock, p.Unit, p.ImageURL,
                c.CategoryName, b.BrandName
            ORDER BY TotalSold DESC, p.ProductID DESC
            """
            ,
            (limit,),
        )
        result = [attach_image_url(item) for item in rows_to_dicts(cursor, cursor.fetchall())]
    finally:
        connection.close()

    return jsonify({"data": result, "total": len(result)})


# ======================
# RECENT PRODUCTS
# ======================
@products_bp.route("/recent", methods=["GET"])
def recent_products():
    limit = request.args.get("limit", 8, type=int)
    limit = max(min(limit, 20), 1)

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            {PRODUCT_SELECT}
            WHERE p.IsActive = 1
            ORDER BY p.CreatedAt DESC, p.ProductID DESC
            OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
            """,
            (limit,),
        )
        result = [attach_image_url(item) for item in rows_to_dicts(cursor, cursor.fetchall())]
    finally:
        connection.close()

    return jsonify({"data": result, "total": len(result)})

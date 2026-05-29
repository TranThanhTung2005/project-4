from flask import Blueprint, jsonify, request

from g6db import fetch_all, fetch_one, get_db_connection, row_to_dict

categories_bp = Blueprint("categories", __name__)

# ======================
# GET ALL
# ======================
@categories_bp.route("/", methods=["GET"])
def get_all():
    categories = fetch_all(
        """
        SELECT CategoryID, CategoryName, Slug, Description, CreatedAt
        FROM dbo.Categories
        ORDER BY CategoryID
        """
    )
    return jsonify(categories)


# ======================
# GET ONE
# ======================
@categories_bp.route("/<int:category_id>", methods=["GET"])
def get_one(category_id):
    category = fetch_one(
        """
        SELECT CategoryID, CategoryName, Slug, Description, CreatedAt
        FROM dbo.Categories
        WHERE CategoryID = ?
        """,
        (category_id,),
    )
    if not category:
        return jsonify({"error": "Không tìm thấy danh mục"}), 404
    return jsonify(category)


# ======================
# CREATE
# ======================
@categories_bp.route("/", methods=["POST"])
def create():
    data = request.get_json(silent=True) or {}
    if not data.get("CategoryName") or not data.get("Slug"):
        return jsonify({"error": "CategoryName và Slug là bắt buộc"}), 400

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO dbo.Categories (CategoryName, Slug, Description)
            OUTPUT INSERTED.CategoryID, INSERTED.CategoryName, INSERTED.Slug, INSERTED.Description, INSERTED.CreatedAt
            VALUES (?, ?, ?)
            """,
            (data["CategoryName"], data["Slug"], data.get("Description")),
        )
        created = row_to_dict(cursor, cursor.fetchone())
        connection.commit()
    finally:
        connection.close()

    return jsonify(created), 201


# ======================
# UPDATE
# ======================
@categories_bp.route("/<int:category_id>", methods=["PUT"])
def update(category_id):
    data = request.get_json(silent=True) or {}
    allowed_fields = ["CategoryName", "Slug", "Description"]
    payload = {field: data[field] for field in allowed_fields if field in data}
    if not payload:
        return jsonify({"error": "Không có dữ liệu cần cập nhật"}), 400

    set_clause = ", ".join(f"{field} = ?" for field in payload)
    params = list(payload.values()) + [category_id]

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(f"UPDATE dbo.Categories SET {set_clause} WHERE CategoryID = ?", params)
        if cursor.rowcount == 0:
            return jsonify({"error": "Không tìm thấy danh mục"}), 404
        connection.commit()
    finally:
        connection.close()

    return jsonify({"message": "Cập nhật danh mục thành công"})


# ======================
# DELETE
# ======================
@categories_bp.route("/<int:category_id>", methods=["DELETE"])
def delete(category_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM dbo.Categories WHERE CategoryID = ?", (category_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Không tìm thấy danh mục"}), 404
        connection.commit()
    finally:
        connection.close()

    return jsonify({"message": "Đã xoá danh mục"})


# ======================
# GET ALL WITH PRODUCT COUNTS
# ======================
@categories_bp.route("/with-counts", methods=["GET"])
def get_all_with_counts():
    categories = fetch_all(
        """
        SELECT
            c.CategoryID,
            c.CategoryName,
            c.Slug,
            c.Description,
            c.CreatedAt,
            COUNT(p.ProductID) AS ProductCount,
            ISNULL(SUM(CASE WHEN p.IsActive = 1 THEN 1 ELSE 0 END), 0) AS ActiveProductCount
        FROM dbo.Categories c
        LEFT JOIN dbo.Products p ON p.CategoryID = c.CategoryID
        GROUP BY c.CategoryID, c.CategoryName, c.Slug, c.Description, c.CreatedAt
        ORDER BY c.CategoryName
        """
    )
    return jsonify(categories)

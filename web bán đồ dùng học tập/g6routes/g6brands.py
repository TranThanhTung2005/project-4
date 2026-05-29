from flask import Blueprint, jsonify, request

from g6db import fetch_all, fetch_one, get_db_connection, row_to_dict

brands_bp = Blueprint("brands", __name__)

# ======================
# GET ALL
# ======================
@brands_bp.route("/", methods=["GET"])
def get_all():
    brands = fetch_all(
        """
        SELECT BrandID, BrandName, Country, Website, CreatedAt
        FROM dbo.Brands
        ORDER BY BrandID
        """
    )
    return jsonify(brands)


# ======================
# GET ONE
# ======================
@brands_bp.route("/<int:brand_id>", methods=["GET"])
def get_one(brand_id):
    brand = fetch_one(
        """
        SELECT BrandID, BrandName, Country, Website, CreatedAt
        FROM dbo.Brands
        WHERE BrandID = ?
        """,
        (brand_id,),
    )
    if not brand:
        return jsonify({"error": "Không tìm thấy thương hiệu"}), 404
    return jsonify(brand)


# ======================
# CREATE
# ======================
@brands_bp.route("/", methods=["POST"])
def create():
    data = request.get_json(silent=True) or {}
    if not data.get("BrandName"):
        return jsonify({"error": "BrandName là bắt buộc"}), 400

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO dbo.Brands (BrandName, Country, Website)
            OUTPUT INSERTED.BrandID, INSERTED.BrandName, INSERTED.Country, INSERTED.Website, INSERTED.CreatedAt
            VALUES (?, ?, ?)
            """,
            (data["BrandName"], data.get("Country"), data.get("Website")),
        )
        created = row_to_dict(cursor, cursor.fetchone())
        connection.commit()
    finally:
        connection.close()

    return jsonify(created), 201


# ======================
# UPDATE
# ======================
@brands_bp.route("/<int:brand_id>", methods=["PUT"])
def update(brand_id):
    data = request.get_json(silent=True) or {}
    allowed_fields = ["BrandName", "Country", "Website"]
    payload = {field: data[field] for field in allowed_fields if field in data}
    if not payload:
        return jsonify({"error": "Không có dữ liệu cần cập nhật"}), 400

    set_clause = ", ".join(f"{field} = ?" for field in payload)
    params = list(payload.values()) + [brand_id]

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(f"UPDATE dbo.Brands SET {set_clause} WHERE BrandID = ?", params)
        if cursor.rowcount == 0:
            return jsonify({"error": "Không tìm thấy thương hiệu"}), 404
        connection.commit()
    finally:
        connection.close()

    return jsonify({"message": "Cập nhật thương hiệu thành công"})


# ======================
# DELETE
# ======================
@brands_bp.route("/<int:brand_id>", methods=["DELETE"])
def delete(brand_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM dbo.Brands WHERE BrandID = ?", (brand_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Không tìm thấy thương hiệu"}), 404
        connection.commit()
    finally:
        connection.close()

    return jsonify({"message": "Đã xoá thương hiệu"})


# ======================
# GET ALL WITH PRODUCT COUNTS
# ======================
@brands_bp.route("/with-counts", methods=["GET"])
def get_all_with_counts():
    brands = fetch_all(
        """
        SELECT
            b.BrandID,
            b.BrandName,
            b.Country,
            b.Website,
            b.CreatedAt,
            COUNT(p.ProductID) AS ProductCount,
            ISNULL(SUM(CASE WHEN p.IsActive = 1 THEN 1 ELSE 0 END), 0) AS ActiveProductCount
        FROM dbo.Brands b
        LEFT JOIN dbo.Products p ON p.BrandID = b.BrandID
        GROUP BY b.BrandID, b.BrandName, b.Country, b.Website, b.CreatedAt
        ORDER BY b.BrandName
        """
    )
    return jsonify(brands)

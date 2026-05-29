from flask import Blueprint, jsonify, request

from g6auth_utils import current_user, require_auth
from g6db import fetch_one, get_db_connection, row_to_dict, rows_to_dicts

reviews_bp = Blueprint("reviews", __name__)

REVIEW_SELECT = """
    SELECT
        r.ReviewID,
        r.ProductID,
        p.ProductName,
        r.CustomerID,
        c.FullName AS CustomerName,
        r.Rating,
        r.Comment,
        r.CreatedAt
    FROM dbo.Reviews r
    INNER JOIN dbo.Products p ON p.ProductID = r.ProductID
    INNER JOIN dbo.Customers c ON c.CustomerID = r.CustomerID
"""

# ======================
# GET ALL
# ======================
@reviews_bp.route("/", methods=["GET"])
def get_all():
    product_id  = request.args.get("product_id", type=int)
    customer_id = request.args.get("customer_id", type=int)

    query = " WHERE 1 = 1"
    params = []

    if product_id:
        query += " AND r.ProductID = ?"
        params.append(product_id)

    if customer_id:
        query += " AND r.CustomerID = ?"
        params.append(customer_id)

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(f"{REVIEW_SELECT} {query} ORDER BY r.CreatedAt DESC", params)
        result = rows_to_dicts(cursor, cursor.fetchall())
    finally:
        connection.close()

    return jsonify(result)


# ======================
# GET ONE
# ======================
@reviews_bp.route("/<int:review_id>", methods=["GET"])
def get_one(review_id):
    review = fetch_one(f"{REVIEW_SELECT} WHERE r.ReviewID = ?", (review_id,))
    if not review:
        return jsonify({"error": "Không tìm thấy đánh giá"}), 404
    return jsonify(review)


# ======================
# CREATE
# ======================
@reviews_bp.route("/", methods=["POST"])
def create():
    data = request.get_json(silent=True) or {}
    if not data.get("ProductID") or not data.get("CustomerID"):
        return jsonify({"error": "ProductID và CustomerID là bắt buộc"}), 400

    rating = int(data.get("Rating", 0))
    if not (1 <= rating <= 5):
        return jsonify({"error": "Rating phải từ 1 đến 5"}), 400

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT ReviewID
            FROM dbo.Reviews
            WHERE ProductID = ? AND CustomerID = ?
            """,
            (data["ProductID"], data["CustomerID"]),
        )
        if cursor.fetchone():
            return jsonify({"error": "Đã đánh giá rồi"}), 409

        cursor.execute(
            """
            INSERT INTO dbo.Reviews (ProductID, CustomerID, Rating, Comment)
            OUTPUT INSERTED.ReviewID, INSERTED.ProductID, INSERTED.CustomerID, INSERTED.Rating, INSERTED.Comment, INSERTED.CreatedAt
            VALUES (?, ?, ?, ?)
            """,
            (data["ProductID"], data["CustomerID"], rating, data.get("Comment")),
        )
        created = row_to_dict(cursor, cursor.fetchone())
        connection.commit()
    finally:
        connection.close()

    return jsonify(created), 201


# ======================
# UPDATE
# ======================
@reviews_bp.route("/<int:review_id>", methods=["PUT"])
def update(review_id):
    data = request.get_json(silent=True) or {}
    payload = {}

    if "Rating" in data:
        rating = int(data["Rating"])
        if not 1 <= rating <= 5:
            return jsonify({"error": "Rating phải từ 1 đến 5"}), 400
        payload["Rating"] = rating

    if "Comment" in data:
        payload["Comment"] = data["Comment"]

    if not payload:
        return jsonify({"error": "Không có dữ liệu cần cập nhật"}), 400

    set_clause = ", ".join(f"{field} = ?" for field in payload)
    params = list(payload.values()) + [review_id]

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(f"UPDATE dbo.Reviews SET {set_clause} WHERE ReviewID = ?", params)
        if cursor.rowcount == 0:
            return jsonify({"error": "Không tìm thấy đánh giá"}), 404
        connection.commit()
    finally:
        connection.close()

    return jsonify({"message": "Cập nhật đánh giá thành công"})


# ======================
# DELETE
# ======================
@reviews_bp.route("/<int:review_id>", methods=["DELETE"])
def delete(review_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM dbo.Reviews WHERE ReviewID = ?", (review_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Không tìm thấy đánh giá"}), 404
        connection.commit()
    finally:
        connection.close()

    return jsonify({"message": "Đã xoá đánh giá"})


# ======================
# GET MY REVIEWS
# ======================
@reviews_bp.route("/mine", methods=["GET"])
@require_auth()
def my_reviews():
    user = current_user()
    customer_id = user.get("customer_id") if user else None
    if not customer_id:
        return jsonify({"error": "Tài khoản này chưa gắn với hồ sơ khách hàng"}), 400

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            {REVIEW_SELECT}
            WHERE r.CustomerID = ?
            ORDER BY r.CreatedAt DESC, r.ReviewID DESC
            """,
            (customer_id,),
        )
        result = rows_to_dicts(cursor, cursor.fetchall())
    finally:
        connection.close()

    return jsonify({"data": result, "total": len(result)})

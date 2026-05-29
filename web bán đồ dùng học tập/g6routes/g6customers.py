from flask import Blueprint, jsonify, request

from g6auth_utils import current_user, require_auth
from g6db import fetch_one, get_db_connection, row_to_dict, rows_to_dicts

customers_bp = Blueprint("customers", __name__)

# ======================
# GET ALL (search + pagination)
# ======================
@customers_bp.route("/", methods=["GET"])
def get_all():
    search = request.args.get("search", "").strip()
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    page = max(page, 1)
    limit = max(min(limit, 100), 1)
    offset = (page - 1) * limit

    query = """
        FROM dbo.Customers
        WHERE 1 = 1
    """
    params = []

    if search:
        query += " AND (FullName LIKE ? OR Email LIKE ? OR Phone LIKE ?)"
        keyword = f"%{search}%"
        params.extend([keyword, keyword, keyword])

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(f"SELECT COUNT(*) AS Total {query}", params)
        total = cursor.fetchone()[0]

        cursor.execute(
            f"""
            SELECT CustomerID, FullName, Email, Phone, Address, CreatedAt
            {query}
            ORDER BY CustomerID
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            """,
            params + [offset, limit],
        )
        customers = rows_to_dicts(cursor, cursor.fetchall())
    finally:
        connection.close()

    return jsonify({"data": customers, "total": total, "page": page, "limit": limit})


# ======================
# GET ONE
# ======================
@customers_bp.route("/<int:customer_id>", methods=["GET"])
def get_one(customer_id):
    customer = fetch_one(
        """
        SELECT CustomerID, FullName, Email, Phone, Address, CreatedAt
        FROM dbo.Customers
        WHERE CustomerID = ?
        """,
        (customer_id,),
    )
    if not customer:
        return jsonify({"error": "Không tìm thấy khách hàng"}), 404
    return jsonify(customer)


# ======================
# CREATE
# ======================
@customers_bp.route("/", methods=["POST"])
def create():
    data = request.get_json(silent=True) or {}
    if not data.get("FullName") or not data.get("Email"):
        return jsonify({"error": "FullName và Email là bắt buộc"}), 400

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO dbo.Customers (FullName, Email, Phone, Address)
            OUTPUT INSERTED.CustomerID, INSERTED.FullName, INSERTED.Email, INSERTED.Phone, INSERTED.Address, INSERTED.CreatedAt
            VALUES (?, ?, ?, ?)
            """,
            (data["FullName"], data["Email"], data.get("Phone"), data.get("Address")),
        )
        created = row_to_dict(cursor, cursor.fetchone())
        connection.commit()
    finally:
        connection.close()

    return jsonify(created), 201


# ======================
# UPDATE
# ======================
@customers_bp.route("/<int:customer_id>", methods=["PUT"])
def update(customer_id):
    data = request.get_json(silent=True) or {}
    allowed_fields = ["FullName", "Email", "Phone", "Address"]
    payload = {field: data[field] for field in allowed_fields if field in data}
    if not payload:
        return jsonify({"error": "Không có dữ liệu cần cập nhật"}), 400

    set_clause = ", ".join(f"{field} = ?" for field in payload)
    params = list(payload.values()) + [customer_id]

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(f"UPDATE dbo.Customers SET {set_clause} WHERE CustomerID = ?", params)
        if cursor.rowcount == 0:
            return jsonify({"error": "Không tìm thấy khách hàng"}), 404
        connection.commit()
    finally:
        connection.close()

    return jsonify({"message": "Cập nhật khách hàng thành công"})


# ======================
# DELETE
# ======================
@customers_bp.route("/<int:customer_id>", methods=["DELETE"])
def delete(customer_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM dbo.Customers WHERE CustomerID = ?", (customer_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Không tìm thấy khách hàng"}), 404
        connection.commit()
    finally:
        connection.close()

    return jsonify({"message": "Đã xoá khách hàng"})


# ======================
# GET MY PROFILE
# ======================
@customers_bp.route("/me", methods=["GET"])
@require_auth()
def my_profile():
    user = current_user()
    customer_id = user.get("customer_id") if user else None
    if not customer_id:
        return jsonify({"error": "Tài khoản này chưa gắn với hồ sơ khách hàng"}), 400

    customer = fetch_one(
        """
        SELECT CustomerID, FullName, Email, Phone, Address, CreatedAt
        FROM dbo.Customers
        WHERE CustomerID = ?
        """,
        (customer_id,),
    )
    if not customer:
        return jsonify({"error": "Không tìm thấy khách hàng"}), 404

    return jsonify(customer)


# ======================
# UPDATE MY PROFILE
# ======================
@customers_bp.route("/me", methods=["PUT"])
@require_auth()
def update_my_profile():
    user = current_user()
    customer_id = user.get("customer_id") if user else None
    if not customer_id:
        return jsonify({"error": "Tài khoản này chưa gắn với hồ sơ khách hàng"}), 400

    data = request.get_json(silent=True) or {}
    allowed_fields = ["FullName", "Phone", "Address"]
    payload = {field: data[field] for field in allowed_fields if field in data}
    if not payload:
        return jsonify({"error": "Không có dữ liệu cần cập nhật"}), 400

    set_clause = ", ".join(f"{field} = ?" for field in payload)
    params = list(payload.values()) + [customer_id]

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(f"UPDATE dbo.Customers SET {set_clause} WHERE CustomerID = ?", params)
        connection.commit()
    finally:
        connection.close()

    customer = fetch_one(
        """
        SELECT CustomerID, FullName, Email, Phone, Address, CreatedAt
        FROM dbo.Customers
        WHERE CustomerID = ?
        """,
        (customer_id,),
    )
    return jsonify(customer)

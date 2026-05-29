from flask import Blueprint, jsonify, request

from datetime import datetime, timedelta, timezone

from flask import current_app

from g6auth_utils import current_user, require_auth
from g6db import fetch_one, get_db_connection, log_admin_event, rows_to_dicts

orders_bp = Blueprint("orders", __name__)

VALID_STATUSES = {"pending", "confirmed", "shipping", "delivered", "cancelled"}
VALID_PAYMENT_METHODS = {"cash", "qr"}
PAYMENT_METHOD_LABELS = {
    "cash": "Tiền mặt khi nhận hàng",
    "qr": "QR ngân hàng MB",
}

ORDER_SELECT = """
    SELECT
        o.OrderID,
        o.CustomerID,
        c.FullName AS CustomerName,
        o.OrderStatus,
        o.ShippingAddress,
        o.Note,
        o.TotalAmount,
        o.Discount,
        o.FinalAmount,
        o.CreatedAt,
        o.UpdatedAt
    FROM dbo.Orders o
    INNER JOIN dbo.Customers c ON c.CustomerID = o.CustomerID
"""

# ======================
# GET ALL (pagination)
# ======================
@orders_bp.route("/", methods=["GET"])
def get_all():
    customer_id = request.args.get("customer_id", type=int)
    status = request.args.get("status")
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)

    page = max(page, 1)
    limit = max(min(limit, 100), 1)
    offset = (page - 1) * limit
    query = " FROM dbo.Orders o WHERE 1=1"
    params = []

    if customer_id:
        query += " AND o.CustomerID=?"
        params.append(customer_id)

    if status:
        query += " AND o.OrderStatus=?"
        params.append(status)

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(f"SELECT COUNT(*) AS Total {query}", params)
        total = cursor.fetchone()[0]
        cursor.execute(
            f"""
            {ORDER_SELECT}
            {query}
            ORDER BY o.CreatedAt DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            """,
            params + [offset, limit],
        )
        result = rows_to_dicts(cursor, cursor.fetchall())
    finally:
        connection.close()

    return jsonify({"data": result, "total": total, "page": page, "limit": limit})


# ======================
# GET ONE (kèm items)
# ======================
@orders_bp.route("/<int:order_id>", methods=["GET"])
def get_one(order_id):
    order = fetch_one(f"{ORDER_SELECT} WHERE o.OrderID = ?", (order_id,))
    if not order:
        return jsonify({"error": "Không tìm thấy đơn hàng"}), 404

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                oi.OrderItemID,
                oi.ProductID,
                p.ProductName,
                oi.Quantity,
                oi.UnitPrice,
                oi.Subtotal
            FROM dbo.OrderItems oi
            INNER JOIN dbo.Products p ON p.ProductID = oi.ProductID
            WHERE oi.OrderID = ?
            ORDER BY oi.OrderItemID
            """,
            (order_id,),
        )
        order["Items"] = rows_to_dicts(cursor, cursor.fetchall())
    finally:
        connection.close()

    return jsonify(order)


# ======================
# REORDER SOURCE
# ======================
@orders_bp.route("/<int:order_id>/reorder", methods=["GET"])
@require_auth()
def reorder_source(order_id):
    user = current_user()
    order = fetch_one(
        """
        SELECT OrderID, CustomerID
        FROM dbo.Orders
        WHERE OrderID = ?
        """,
        (order_id,),
    )
    if not order:
        return jsonify({"error": "Không tìm thấy đơn hàng"}), 404

    if user.get("role") != "admin" and order.get("CustomerID") != user.get("customer_id"):
        return jsonify({"error": "Bạn không có quyền truy cập đơn hàng này"}), 403

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                oi.ProductID,
                p.ProductName,
                oi.UnitPrice AS Price,
                oi.Quantity,
                p.Stock AS MaxStock
            FROM dbo.OrderItems oi
            INNER JOIN dbo.Products p ON p.ProductID = oi.ProductID
            WHERE oi.OrderID = ? AND p.IsActive = 1
            ORDER BY oi.OrderItemID
            """,
            (order_id,),
        )
        items = rows_to_dicts(cursor, cursor.fetchall())
    finally:
        connection.close()

    for item in items:
        item["Quantity"] = min(int(item.get("Quantity", 1)), int(item.get("MaxStock", 0) or 0)) or 1

    return jsonify({"order_id": order_id, "items": items, "total": len(items)})


# ======================
# CREATE ORDER
# ======================
@orders_bp.route("/", methods=["POST"])
@require_auth()
def create():
    user = current_user()
    data = request.get_json(silent=True) or {}
    items = data.get("Items") or []
    customer_id = user.get("customer_id") if user else None
    payment_method = (data.get("PaymentMethod") or "cash").strip().lower()

    if not customer_id:
        return jsonify({"error": "Tài khoản này chưa gắn với hồ sơ khách hàng"}), 400
    if not items:
        return jsonify({"error": "Phải có ít nhất 1 sản phẩm"}), 400
    if payment_method not in VALID_PAYMENT_METHODS:
        return jsonify({"error": "Phương thức thanh toán không hợp lệ"}), 400

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        total_amount = 0
        order_items = []

        for item in items:
            product_id = item.get("ProductID")
            quantity = int(item.get("Quantity", 0))
            if not product_id or quantity <= 0:
                return jsonify({"error": "Mỗi item cần ProductID và Quantity > 0"}), 400

            cursor.execute(
                """
                SELECT ProductID, ProductName, Price, Stock
                FROM dbo.Products
                WHERE ProductID = ? AND IsActive = 1
                """,
                (product_id,),
            )
            product = cursor.fetchone()
            if not product:
                return jsonify({"error": f"Không tìm thấy sản phẩm {product_id}"}), 404
            if product[3] < quantity:
                return jsonify({"error": f"Sản phẩm '{product[1]}' không đủ tồn kho"}), 400

            unit_price = float(product[2])
            total_amount += unit_price * quantity
            order_items.append((product_id, quantity, unit_price))

        raw_note = (data.get("Note") or "").strip()
        payment_note = f"Thanh toán: {PAYMENT_METHOD_LABELS[payment_method]}"
        note = f"{payment_note}\n{raw_note}" if raw_note else payment_note

        cursor.execute(
            """
            INSERT INTO dbo.Orders (
                CustomerID, OrderStatus, ShippingAddress, Note, TotalAmount, Discount
            )
            OUTPUT INSERTED.OrderID
            VALUES (?, 'pending', ?, ?, ?, ?)
            """,
            (
                customer_id,
                data.get("ShippingAddress"),
                note,
                total_amount,
                float(data.get("Discount", 0)),
            ),
        )
        order_id = cursor.fetchone()[0]

        for product_id, quantity, unit_price in order_items:
            cursor.execute(
                """
                INSERT INTO dbo.OrderItems (OrderID, ProductID, Quantity, UnitPrice)
                VALUES (?, ?, ?, ?)
                """,
                (order_id, product_id, quantity, unit_price),
            )
            cursor.execute(
                """
                UPDATE dbo.Products
                SET Stock = Stock - ?, UpdatedAt = GETDATE()
                WHERE ProductID = ?
                """,
                (quantity, product_id),
            )

        connection.commit()
    finally:
        connection.close()

    log_admin_event(
        event_type="checkout",
        title=f"{user['name']} đã tạo đơn hàng mới",
        details=f"Đơn #{order_id} | {len(order_items)} sản phẩm | Tổng tiền: {total_amount:,.0f}đ",
        actor_name=user["name"],
        actor_email=user["email"],
        related_order_id=order_id,
    )

    response = get_one(order_id)
    payload = response.get_json()
    payload["PaymentMethod"] = payment_method
    payload["PaymentMethodLabel"] = PAYMENT_METHOD_LABELS[payment_method]
    if payment_method == "qr":
        payload["QrExpiresAt"] = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        payload["PaymentBank"] = {
            "bankId": "MB",
            "accountNumber": current_app.config["MB_BANK_ACCOUNT_NUMBER"],
            "accountName": current_app.config["MB_BANK_ACCOUNT_NAME"],
        }
    return jsonify(payload), 201


# ======================
# UPDATE STATUS
# ======================
@orders_bp.route("/<int:order_id>/status", methods=["PATCH"])
def update_status(order_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("OrderStatus")

    if new_status not in VALID_STATUSES:
        return jsonify({"error": "Trạng thái không hợp lệ"}), 400

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE dbo.Orders
            SET OrderStatus = ?, UpdatedAt = GETDATE()
            WHERE OrderID = ?
            """,
            (new_status, order_id),
        )
        if cursor.rowcount == 0:
            return jsonify({"error": "Không tìm thấy đơn hàng"}), 404
        connection.commit()
    finally:
        connection.close()

    return jsonify({"message": "Cập nhật trạng thái thành công"})


# ======================
# DELETE
# ======================
@orders_bp.route("/<int:order_id>", methods=["DELETE"])
def delete(order_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT ProductID, Quantity FROM dbo.OrderItems WHERE OrderID = ?", (order_id,))
        items = cursor.fetchall()
        if not items and not fetch_one("SELECT OrderID FROM dbo.Orders WHERE OrderID = ?", (order_id,)):
            return jsonify({"error": "Không tìm thấy đơn hàng"}), 404

        for product_id, quantity in items:
            cursor.execute(
                """
                UPDATE dbo.Products
                SET Stock = Stock + ?, UpdatedAt = GETDATE()
                WHERE ProductID = ?
                """,
                (quantity, product_id),
            )

        cursor.execute("DELETE FROM dbo.Orders WHERE OrderID = ?", (order_id,))
        connection.commit()
    finally:
        connection.close()

    return jsonify({"message": "Đã xoá đơn hàng"})


# ======================
# MY ORDERS
# ======================
@orders_bp.route("/mine", methods=["GET"])
@require_auth()
def my_orders():
    user = current_user()
    customer_id = user.get("customer_id") if user else None

    if not customer_id:
        return jsonify({"error": "Tài khoản này chưa gắn với hồ sơ khách hàng"}), 400

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            {ORDER_SELECT}
            WHERE o.CustomerID = ?
            ORDER BY o.CreatedAt DESC, o.OrderID DESC
            """,
            (customer_id,),
        )
        result = rows_to_dicts(cursor, cursor.fetchall())
    finally:
        connection.close()

    return jsonify({"data": result, "total": len(result)})


# ======================
# ORDER STATS
# ======================
@orders_bp.route("/stats", methods=["GET"])
def stats():
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                COUNT(*) AS TotalOrders,
                ISNULL(SUM(CASE WHEN OrderStatus <> 'cancelled' THEN FinalAmount ELSE 0 END), 0) AS TotalRevenue,
                COUNT(CASE WHEN OrderStatus = 'pending' THEN 1 END) AS PendingOrders,
                COUNT(CASE WHEN OrderStatus = 'delivered' THEN 1 END) AS DeliveredOrders
            FROM dbo.Orders
            """
        )
        row = cursor.fetchone()
        result = rows_to_dicts(cursor, [row])[0] if row else {}
    finally:
        connection.close()

    return jsonify(result)


# ======================
# REVENUE OVERVIEW
# ======================
@orders_bp.route("/revenue-overview", methods=["GET"])
def revenue_overview():
    months = request.args.get("months", 6, type=int)
    months = max(min(months, 24), 1)

    summary = fetch_one(
        """
        SELECT
            ISNULL(SUM(CASE WHEN OrderStatus <> 'cancelled' THEN FinalAmount ELSE 0 END), 0) AS TotalRevenue,
            ISNULL(SUM(CASE WHEN OrderStatus = 'delivered' THEN FinalAmount ELSE 0 END), 0) AS DeliveredRevenue,
            ISNULL(SUM(CASE WHEN OrderStatus IN ('pending', 'confirmed', 'shipping') THEN FinalAmount ELSE 0 END), 0) AS PipelineRevenue,
            COUNT(CASE WHEN OrderStatus <> 'cancelled' THEN 1 END) AS RevenueOrders
        FROM dbo.Orders
        """
    ) or {"TotalRevenue": 0, "DeliveredRevenue": 0, "PipelineRevenue": 0, "RevenueOrders": 0}

    monthly = fetch_all(
        f"""
        SELECT TOP ({months})
            YEAR(CreatedAt) AS RevenueYear,
            MONTH(CreatedAt) AS RevenueMonth,
            ISNULL(SUM(CASE WHEN OrderStatus <> 'cancelled' THEN FinalAmount ELSE 0 END), 0) AS Revenue,
            COUNT(CASE WHEN OrderStatus <> 'cancelled' THEN 1 END) AS OrderCount
        FROM dbo.Orders
        GROUP BY YEAR(CreatedAt), MONTH(CreatedAt)
        ORDER BY RevenueYear DESC, RevenueMonth DESC
        """
    )

    return jsonify({"summary": summary, "monthly": monthly, "months": months})

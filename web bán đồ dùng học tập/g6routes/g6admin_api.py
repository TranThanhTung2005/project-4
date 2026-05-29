from flask import Blueprint, jsonify, request

from g6auth_utils import require_auth
from g6db import fetch_all, fetch_one, get_db_connection
from g6services.g6admin_context import get_admin_context

admin_api_bp = Blueprint("admin_api", __name__)


@admin_api_bp.route("/dashboard", methods=["GET"])
@require_auth(role="admin")
def dashboard():
    context = get_admin_context()
    return jsonify(
        {
            "metrics": context["metrics"],
            "revenue_summary": context["revenue_summary"],
            "monthly_revenue": context["monthly_revenue"],
            "revenue_by_status": context["revenue_by_status"],
            "recent_orders": context["orders"],
            "recent_products": context["products"],
            "pending_admin_requests": context["admin_requests"],
            "recent_activities": context["activities"],
        }
    )


@admin_api_bp.route("/products/<int:product_id>/toggle-active", methods=["PATCH"])
@require_auth(role="admin")
def toggle_product_active(product_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE dbo.Products
            SET IsActive = CASE WHEN IsActive = 1 THEN 0 ELSE 1 END,
                UpdatedAt = GETDATE()
            WHERE ProductID = ?
            """,
            (product_id,),
        )
        if cursor.rowcount == 0:
            return jsonify({"error": "Không tìm thấy sản phẩm"}), 404
        connection.commit()
    finally:
        connection.close()

    product = fetch_one(
        """
        SELECT ProductID, SKU, ProductName, IsActive, UpdatedAt
        FROM dbo.Products
        WHERE ProductID = ?
        """,
        (product_id,),
    )
    return jsonify(product)


@admin_api_bp.route("/accounts/pending-admin", methods=["GET"])
@require_auth(role="admin")
def pending_admin_accounts():
    accounts = fetch_all(
        """
        SELECT AccountID, FullName, Email, Role, AdminRequestStatus, RequestedRole, CreatedAt
        FROM dbo.Accounts
        WHERE RequestedRole = 'admin' AND ISNULL(AdminRequestStatus, 'none') = 'pending'
        ORDER BY AccountID DESC
        """
    )
    return jsonify({"data": accounts, "total": len(accounts)})


@admin_api_bp.route("/top-customers", methods=["GET"])
@require_auth(role="admin")
def top_customers():
    limit = request.args.get("limit", 10, type=int)
    limit = max(min(limit, 50), 1)
    customers = fetch_all(
        f"""
        SELECT TOP ({limit})
            c.CustomerID,
            c.FullName,
            c.Email,
            COUNT(o.OrderID) AS TotalOrders,
            ISNULL(SUM(CASE WHEN o.OrderStatus <> 'cancelled' THEN o.FinalAmount ELSE 0 END), 0) AS TotalSpent
        FROM dbo.Customers c
        LEFT JOIN dbo.Orders o ON o.CustomerID = c.CustomerID
        GROUP BY c.CustomerID, c.FullName, c.Email
        ORDER BY TotalSpent DESC, TotalOrders DESC, c.CustomerID DESC
        """
    )
    return jsonify({"data": customers, "total": len(customers)})

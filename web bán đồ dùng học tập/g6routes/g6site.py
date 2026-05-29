from flask import Blueprint, flash, redirect, render_template, request, url_for

from g6auth_utils import current_user, get_current_account, require_auth
from g6db import fetch_all, fetch_one, get_db_connection
from g6routes.g6products import attach_image_url

site_bp = Blueprint("site", __name__)

ORDER_STATUS_TABS = [
    {"key": "all", "label": "Tất cả"},
    {"key": "pending", "label": "Chờ xác nhận"},
    {"key": "confirmed", "label": "Đã xác nhận"},
    {"key": "shipping", "label": "Đang giao"},
    {"key": "delivered", "label": "Hoàn thành"},
    {"key": "cancelled", "label": "Đã hủy"},
]

ORDER_STATUS_LABELS = {tab["key"]: tab["label"] for tab in ORDER_STATUS_TABS}


@site_bp.route("/")
def home():
    categories = fetch_all(
        """
        SELECT CategoryID, CategoryName, Slug
        FROM dbo.Categories
        ORDER BY CategoryName
        """
    )
    active_promotions = fetch_all(
        """
        SELECT TOP 3 PromotionID, Code, Description, DiscountType, DiscountValue, MinOrderValue
        FROM dbo.Promotions
        WHERE IsActive = 1
          AND (StartsAt IS NULL OR StartsAt <= GETDATE())
          AND (ExpiresAt IS NULL OR ExpiresAt >= GETDATE())
        ORDER BY PromotionID DESC
        """
    )
    promotional_products = fetch_all(
        """
        SELECT TOP 6
            p.ProductID,
            p.SKU,
            p.ProductName,
            p.Description,
            p.Price,
            p.Stock,
            p.Unit,
            p.ImageURL,
            c.CategoryName,
            b.BrandName
        FROM dbo.Products p
        INNER JOIN dbo.Categories c ON c.CategoryID = p.CategoryID
        LEFT JOIN dbo.Brands b ON b.BrandID = p.BrandID
        WHERE p.IsActive = 1
        ORDER BY p.ProductID DESC
        """
    )
    promotional_products = [attach_image_url(product) for product in promotional_products]

    if active_promotions:
        for index, product in enumerate(promotional_products):
            promotion = active_promotions[index % len(active_promotions)]
            discount_value = int(promotion["DiscountValue"])
            if promotion["DiscountType"] == "percent":
                promotion_text = f"Giảm {discount_value}% với mã {promotion['Code']}"
            else:
                promotion_text = f"Giảm {discount_value:,.0f}đ với mã {promotion['Code']}"

            product["PromotionCode"] = promotion["Code"]
            product["PromotionText"] = promotion_text
            product["PromotionMinOrderValue"] = promotion["MinOrderValue"]

    return render_template(
        "g6user/g6index.html",
        current_user=current_user(),
        current_account=get_current_account(),
        categories=categories,
        selected_category_id=request.args.get("category_id", type=int),
        promotional_products=promotional_products,
        active_promotions=active_promotions,
    )


@site_bp.route("/cart")
def cart():
    return render_template("g6user/g6cart.html", current_user=current_user())


@site_bp.route("/cart-added")
def cart_added():
    return render_template("g6user/g6cart_added.html", current_user=current_user())


@site_bp.route("/profile", methods=["GET", "POST"])
@require_auth()
def profile():
    account = get_current_account()
    customer_id = account.get("CustomerID") if account else None
    if not customer_id:
        flash("Tài khoản này chưa gắn với hồ sơ khách hàng.", "error")
        return redirect(url_for("site.home"))

    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        address = (request.form.get("address") or "").strip()

        if not full_name:
            flash("Họ tên là bắt buộc.", "error")
            return redirect(url_for("site.profile"))

        connection = get_db_connection()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE dbo.Customers
                SET FullName = ?, Phone = ?, Address = ?
                WHERE CustomerID = ?
                """,
                (full_name, phone or None, address or None, customer_id),
            )
            cursor.execute(
                """
                UPDATE dbo.Accounts
                SET FullName = ?
                WHERE CustomerID = ?
                """,
                (full_name, customer_id),
            )
            connection.commit()
        finally:
            connection.close()

        flash("Đã cập nhật thông tin cá nhân.", "success")
        return redirect(url_for("site.profile"))

    customer = fetch_one(
        """
        SELECT CustomerID, FullName, Email, Phone, Address, CreatedAt
        FROM dbo.Customers
        WHERE CustomerID = ?
        """,
        (customer_id,),
    )
    orders = fetch_all(
        """
        SELECT TOP 5 OrderID, OrderStatus, FinalAmount, CreatedAt
        FROM dbo.Orders
        WHERE CustomerID = ?
        ORDER BY CreatedAt DESC, OrderID DESC
        """,
        (customer_id,),
    )
    return render_template(
        "g6user/g6profile.html",
        current_user=current_user(),
        current_account=account,
        customer=customer,
        recent_orders=orders,
    )


@site_bp.route("/orders/history")
@require_auth()
def order_history():
    account = get_current_account()
    customer_id = account.get("CustomerID") if account else None
    if not customer_id:
        flash("Tài khoản này chưa gắn với hồ sơ khách hàng.", "error")
        return redirect(url_for("site.home"))

    active_status = request.args.get("status", "all")
    if active_status not in ORDER_STATUS_LABELS:
        active_status = "all"

    where_sql = "WHERE o.CustomerID = ?"
    params = [customer_id]
    if active_status != "all":
        where_sql += " AND o.OrderStatus = ?"
        params.append(active_status)

    orders = fetch_all(
        f"""
        SELECT
            o.OrderID,
            o.OrderStatus,
            o.ShippingAddress,
            o.Note,
            o.TotalAmount,
            o.Discount,
            o.FinalAmount,
            o.CreatedAt,
            (
                SELECT COUNT(*)
                FROM dbo.OrderItems oi
                WHERE oi.OrderID = o.OrderID
            ) AS ItemCount
        FROM dbo.Orders o
        {where_sql}
        ORDER BY o.CreatedAt DESC, o.OrderID DESC
        """,
        tuple(params),
    )

    status_counts = fetch_all(
        """
        SELECT OrderStatus, COUNT(*) AS Total
        FROM dbo.Orders
        WHERE CustomerID = ?
        GROUP BY OrderStatus
        """,
        (customer_id,),
    )
    count_map = {row["OrderStatus"]: row["Total"] for row in status_counts}
    total_count = sum(count_map.values())
    status_tabs = []
    for tab in ORDER_STATUS_TABS:
        status_tabs.append({
            **tab,
            "count": total_count if tab["key"] == "all" else count_map.get(tab["key"], 0),
        })

    for order in orders:
        order["StatusLabel"] = ORDER_STATUS_LABELS.get(order["OrderStatus"], order["OrderStatus"])
        items = fetch_all(
            """
            SELECT
                oi.ProductID,
                p.ProductName,
                p.ImageURL,
                oi.Quantity,
                oi.UnitPrice,
                oi.Subtotal
            FROM dbo.OrderItems oi
            INNER JOIN dbo.Products p ON p.ProductID = oi.ProductID
            WHERE oi.OrderID = ?
            ORDER BY oi.OrderItemID
            """,
            (order["OrderID"],),
        )
        order["Items"] = [attach_image_url(item) for item in items]
    return render_template(
        "g6user/g6order_history.html",
        current_user=current_user(),
        current_account=account,
        orders=orders,
        status_tabs=status_tabs,
        active_status=active_status,
    )


@site_bp.route("/products/<int:product_id>")
def product_detail(product_id):
    product = fetch_one(
        """
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
        WHERE p.ProductID = ?
        """,
        (product_id,),
    )
    if not product:
        flash("Không tìm thấy sản phẩm.", "error")
        return redirect(url_for("site.home"))
    product = attach_image_url(product)

    reviews = fetch_all(
        """
        SELECT
            r.ReviewID,
            r.Rating,
            r.Comment,
            r.CreatedAt,
            c.FullName AS CustomerName
        FROM dbo.Reviews r
        INNER JOIN dbo.Customers c ON c.CustomerID = r.CustomerID
        WHERE r.ProductID = ?
        ORDER BY r.CreatedAt DESC, r.ReviewID DESC
        """,
        (product_id,),
    )
    review_summary = fetch_one(
        """
        SELECT
            COUNT(*) AS ReviewCount,
            CAST(ISNULL(AVG(CAST(Rating AS FLOAT)), 0) AS DECIMAL(4,2)) AS AverageRating
        FROM dbo.Reviews
        WHERE ProductID = ?
        """,
        (product_id,),
    ) or {"ReviewCount": 0, "AverageRating": 0}
    related_products = fetch_all(
        """
        SELECT TOP 4
            p.ProductID,
            p.ProductName,
            p.Price,
            p.Stock
        FROM dbo.Products p
        WHERE p.CategoryID = ? AND p.ProductID <> ? AND p.IsActive = 1
        ORDER BY p.ProductID DESC
        """,
        (product["CategoryID"], product_id),
    )

    return render_template(
        "g6user/g6product_detail.html",
        current_user=current_user(),
        current_account=get_current_account(),
        product=product,
        reviews=reviews,
        review_summary=review_summary,
        related_products=related_products,
    )


@site_bp.route("/products/<int:product_id>/reviews", methods=["POST"])
@require_auth()
def create_product_review(product_id):
    account = get_current_account()
    customer_id = account.get("CustomerID") if account else None
    if not customer_id:
        flash("Tài khoản này chưa gắn với khách hàng nên chưa thể đánh giá.", "error")
        return redirect(url_for("site.product_detail", product_id=product_id))

    rating = request.form.get("rating", type=int)
    comment = (request.form.get("comment") or "").strip()

    if not rating or not 1 <= rating <= 5:
        flash("Vui lòng chọn số sao từ 1 đến 5.", "error")
        return redirect(url_for("site.product_detail", product_id=product_id))

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT ReviewID
            FROM dbo.Reviews
            WHERE ProductID = ? AND CustomerID = ?
            """,
            (product_id, customer_id),
        )
        if cursor.fetchone():
            flash("Bạn đã đánh giá sản phẩm này rồi.", "error")
            return redirect(url_for("site.product_detail", product_id=product_id))

        cursor.execute(
            """
            INSERT INTO dbo.Reviews (ProductID, CustomerID, Rating, Comment)
            VALUES (?, ?, ?, ?)
            """,
            (product_id, customer_id, rating, comment or None),
        )
        connection.commit()
    finally:
        connection.close()

    flash("Cảm ơn bạn đã gửi đánh giá.", "success")
    return redirect(url_for("site.product_detail", product_id=product_id))

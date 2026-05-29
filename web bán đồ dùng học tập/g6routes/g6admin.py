from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from g6auth_utils import current_user, require_auth, require_primary_admin, is_primary_admin
from g6db import fetch_all, fetch_one, get_db_connection
from g6routes.g6products import attach_image_url
from g6services.g6admin_context import get_admin_context, get_product_column_names
from g6utils.g6image_uploads import save_product_image
from g6utils.g6admin_helpers import parse_form_datetime

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def redirect_back(default_endpoint="admin.dashboard"):
    return redirect(request.referrer or url_for(default_endpoint))


def parse_salary(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return None


def get_uploaded_image():
    return request.files.get("image") or request.files.get("image_file") or request.files.get("file")


def render_admin_page(template_name, section):
    context = get_admin_context()
    context["admin_section"] = section
    return render_template(template_name, current_user=current_user(), **context)


def render_admin_detail(template_name, section, **extra_context):
    context = {"admin_section": section, "current_user": current_user()}
    context.update(extra_context)
    return render_template(template_name, **context)


@admin_bp.route("/")
@admin_bp.route("/dashboard")
@require_auth(role="admin")
def dashboard():
    return render_admin_page("g6admin/g6dashboard.html", "dashboard")


@admin_bp.route("/accounts")
@require_auth(role="admin")
def accounts_page():
    return render_admin_page("g6admin/g6accounts.html", "accounts")


@admin_bp.route("/products")
@require_auth(role="admin")
def products_page():
    return render_admin_page("g6admin/g6products.html", "products")


@admin_bp.route("/orders")
@require_auth(role="admin")
def orders_page():
    return render_admin_page("g6admin/g6orders.html", "orders")


@admin_bp.route("/catalog")
@require_auth(role="admin")
def catalog_page():
    return render_admin_page("g6admin/g6catalog.html", "catalog")


@admin_bp.route("/promotions")
@require_auth(role="admin")
def promotions_page():
    return render_admin_page("g6admin/g6promotions.html", "promotions")


@admin_bp.route("/users")
@require_auth(role="admin")
def users_page():
    return render_admin_page("g6admin/g6users.html", "users")


@admin_bp.route("/employees")
@require_auth(role="admin")
def employees_page():
    return render_admin_page("g6admin/g6employees.html", "employees")


@admin_bp.route("/suppliers")
@require_auth(role="admin")
def suppliers_page():
    return render_admin_page("g6admin/g6suppliers.html", "suppliers")


@admin_bp.route("/categories/<int:category_id>")
@require_auth(role="admin")
def category_detail(category_id):
    category = fetch_one(
        """
        SELECT CategoryID, CategoryName, Slug, Description, CreatedAt
        FROM dbo.Categories
        WHERE CategoryID = ?
        """,
        (category_id,),
    )
    if not category:
        flash("Không tìm thấy danh mục.", "error")
        return redirect(url_for("admin.catalog_page"))

    products = fetch_all(
        """
        SELECT p.ProductID, p.ProductName, p.Price, p.Stock, p.IsActive, b.BrandName
        FROM dbo.Products p
        LEFT JOIN dbo.Brands b ON b.BrandID = p.BrandID
        WHERE p.CategoryID = ?
        ORDER BY p.ProductID DESC
        """,
        (category_id,),
    )
    return render_admin_detail(
        "g6admin/g6category_detail.html",
        "catalog",
        category=category,
        products=products,
    )


@admin_bp.route("/brands/<int:brand_id>")
@require_auth(role="admin")
def brand_detail(brand_id):
    brand = fetch_one(
        """
        SELECT BrandID, BrandName, Country, Website
        FROM dbo.Brands
        WHERE BrandID = ?
        """,
        (brand_id,),
    )
    if not brand:
        flash("Không tìm thấy thương hiệu.", "error")
        return redirect(url_for("admin.catalog_page"))

    products = fetch_all(
        """
        SELECT ProductID, ProductName, Price, Stock, CategoryID
        FROM dbo.Products
        WHERE BrandID = ?
        ORDER BY ProductID DESC
        """,
        (brand_id,),
    )
    return render_admin_detail(
        "g6admin/g6brand_detail.html",
        "catalog",
        brand=brand,
        products=products,
    )

@admin_bp.route("/employees/<int:employee_id>")
@require_auth(role="admin")
def employee_detail(employee_id):
    employee = fetch_one(
        """
        SELECT EmployeeID, FullName, Email, Phone, Position, HireDate, Salary, IsActive, CreatedAt
        FROM dbo.Employees
        WHERE EmployeeID = ?
        """,
        (employee_id,),
    )
    if not employee:
        flash("Không tìm thấy nhân viên.", "error")
        return redirect(url_for("admin.employees_page"))

    return render_admin_detail(
        "g6admin/g6employee_detail.html",
        "employees",
        employee=employee,
    )


@admin_bp.route("/suppliers/<int:supplier_id>")
@require_auth(role="admin")
def supplier_detail(supplier_id):
    supplier = fetch_one(
        """
        SELECT SupplierID, SupplierName, ContactName, Email, Phone, Address, CreatedAt
        FROM dbo.Suppliers
        WHERE SupplierID = ?
        """,
        (supplier_id,),
    )
    if not supplier:
        flash("Không tìm thấy nhà cung cấp.", "error")
        return redirect(url_for("admin.suppliers_page"))

    return render_admin_detail(
        "g6admin/g6supplier_detail.html",
        "suppliers",
        supplier=supplier,
    )


@admin_bp.route("/products/<int:product_id>")
@require_auth(role="admin")
def product_detail(product_id):
    product = fetch_one(
        """
        SELECT
            p.ProductID, p.SKU, p.ProductName, p.Description, p.Price, p.Stock, p.Unit,
            p.ImageURL, p.IsActive, p.CreatedAt, p.UpdatedAt,
            c.CategoryID, c.CategoryName,
            b.BrandID, b.BrandName
        FROM dbo.Products p
        INNER JOIN dbo.Categories c ON c.CategoryID = p.CategoryID
        LEFT JOIN dbo.Brands b ON b.BrandID = p.BrandID
        WHERE p.ProductID = ?
        """,
        (product_id,),
    )
    if not product:
        flash("Không tìm thấy sản phẩm.", "error")
        return redirect(url_for("admin.products_page"))
    product = attach_image_url(product)

    reviews = fetch_all(
        """
        SELECT TOP 10 r.ReviewID, r.Rating, r.Comment, r.CreatedAt, c.FullName AS CustomerName
        FROM dbo.Reviews r
        INNER JOIN dbo.Customers c ON c.CustomerID = r.CustomerID
        WHERE r.ProductID = ?
        ORDER BY r.CreatedAt DESC, r.ReviewID DESC
        """,
        (product_id,),
    )
    categories = fetch_all(
        """
        SELECT CategoryID, CategoryName, Slug, Description
        FROM dbo.Categories
        ORDER BY CategoryName
        """
    )
    brands = fetch_all(
        """
        SELECT BrandID, BrandName, Country, Website
        FROM dbo.Brands
        ORDER BY BrandName
        """
    )
    return render_admin_detail(
        "g6admin/g6product_detail.html",
        "products",
        product=product,
        reviews=reviews,
        categories=categories,
        brands=brands,
    )


@admin_bp.route("/orders/<int:order_id>")
@require_auth(role="admin")
def order_detail(order_id):
    order = fetch_one(
        """
        SELECT
            o.OrderID, o.TotalAmount, o.Discount, o.FinalAmount, o.OrderStatus,
            o.ShippingAddress, o.Note, o.CreatedAt, o.UpdatedAt,
            c.CustomerID, c.FullName AS CustomerName, c.Email, c.Phone, c.Address
        FROM dbo.Orders o
        INNER JOIN dbo.Customers c ON c.CustomerID = o.CustomerID
        WHERE o.OrderID = ?
        """,
        (order_id,),
    )
    if not order:
        flash("Không tìm thấy đơn hàng.", "error")
        return redirect(url_for("admin.orders_page"))

    items = fetch_all(
        """
        SELECT oi.OrderItemID, oi.Quantity, oi.UnitPrice, oi.Subtotal AS LineTotal, p.ProductID, p.ProductName
        FROM dbo.OrderItems oi
        INNER JOIN dbo.Products p ON p.ProductID = oi.ProductID
        WHERE oi.OrderID = ?
        ORDER BY oi.OrderItemID
        """,
        (order_id,),
    )
    return render_admin_detail(
        "g6admin/g6order_detail.html",
        "orders",
        order=order,
        items=items,
    )


@admin_bp.route("/accounts/<int:account_id>")
@require_auth(role="admin")
def account_detail(account_id):
    account = fetch_one(
        """
        SELECT
            a.AccountID, a.FullName, a.Email, a.Role, a.IsActive,
            ISNULL(a.AdminRequestStatus, 'none') AS AdminRequestStatus,
            a.RequestedRole, a.CreatedAt, a.CustomerID,
            c.Phone, c.Address,
            CASE WHEN a.Email = ? THEN CAST(1 AS bit) ELSE CAST(0 AS bit) END AS IsPrimaryAdmin
        FROM dbo.Accounts a
        LEFT JOIN dbo.Customers c ON c.CustomerID = a.CustomerID
        WHERE a.AccountID = ?
        """,
        (current_app.config["ADMIN_LOGIN_EMAIL"], account_id),
    )
    if not account:
        flash("Không tìm thấy tài khoản.", "error")
        return redirect(url_for("admin.accounts_page"))

    orders = fetch_all(
        """
        SELECT TOP 8 OrderID, TotalAmount, OrderStatus, CreatedAt
        FROM dbo.Orders
        WHERE CustomerID = ?
        ORDER BY CreatedAt DESC, OrderID DESC
        """,
        (account.get("CustomerID"),),
    ) if account.get("CustomerID") else []

    return render_admin_detail(
        "g6admin/g6account_detail.html",
        "accounts",
        account=account,
        orders=orders,
    )


@admin_bp.route("/promotions/<int:promotion_id>")
@require_auth(role="admin")
def promotion_detail(promotion_id):
    promotion = fetch_one(
        """
        SELECT
            PromotionID, Code, Description, DiscountType, DiscountValue, MinOrderValue,
            MaxUses, UsedCount, StartsAt, ExpiresAt, IsActive
        FROM dbo.Promotions
        WHERE PromotionID = ?
        """,
        (promotion_id,),
    )
    if not promotion:
        flash("Không tìm thấy khuyến mãi.", "error")
        return redirect(url_for("admin.promotions_page"))

    return render_admin_detail(
        "g6admin/g6promotion_detail.html",
        "promotions",
        promotion=promotion,
    )


@admin_bp.route("/customers/<int:customer_id>")
@require_auth(role="admin")
def customer_detail(customer_id):
    customer = fetch_one(
        """
        SELECT CustomerID, FullName, Email, Phone, Address, CreatedAt
        FROM dbo.Customers
        WHERE CustomerID = ?
        """,
        (customer_id,),
    )
    if not customer:
        flash("Không tìm thấy khách hàng.", "error")
        return redirect(url_for("admin.users_page"))

    orders = fetch_all(
        """
        SELECT TOP 8 OrderID, TotalAmount, OrderStatus, CreatedAt
        FROM dbo.Orders
        WHERE CustomerID = ?
        ORDER BY CreatedAt DESC, OrderID DESC
        """,
        (customer_id,),
    )
    reviews = fetch_all(
        """
        SELECT TOP 8 r.ReviewID, p.ProductID, p.ProductName, r.Rating, r.Comment, r.CreatedAt
        FROM dbo.Reviews r
        INNER JOIN dbo.Products p ON p.ProductID = r.ProductID
        WHERE r.CustomerID = ?
        ORDER BY r.CreatedAt DESC, r.ReviewID DESC
        """,
        (customer_id,),
    )
    return render_admin_detail(
        "g6admin/g6customer_detail.html",
        "users",
        customer=customer,
        orders=orders,
        reviews=reviews,
    )


@admin_bp.route("/reviews/<int:review_id>")
@require_auth(role="admin")
def review_detail(review_id):
    review = fetch_one(
        """
        SELECT
            r.ReviewID, r.Rating, r.Comment, r.CreatedAt,
            p.ProductID, p.ProductName,
            c.CustomerID, c.FullName AS CustomerName, c.Email
        FROM dbo.Reviews r
        INNER JOIN dbo.Products p ON p.ProductID = r.ProductID
        INNER JOIN dbo.Customers c ON c.CustomerID = r.CustomerID
        WHERE r.ReviewID = ?
        """,
        (review_id,),
    )
    if not review:
        flash("Không tìm thấy đánh giá.", "error")
        return redirect(url_for("admin.users_page"))

    return render_admin_detail(
        "g6admin/g6review_detail.html",
        "users",
        review=review,
    )


@admin_bp.route("/products/create", methods=["POST"])
@require_auth(role="admin")
def create_product():
    form = request.form
    try:
        sku = (form.get("sku") or "").strip()
        product_name = (form.get("product_name") or "").strip()
        category_id = int(form.get("category_id"))
        brand_id = int(form.get("brand_id")) if form.get("brand_id") else None
        price = float(form.get("price", 0))
        stock = int(form.get("stock", 0))

        if not sku or not product_name:
            flash("SKU và tên sản phẩm là bắt buộc.", "error")
            return redirect_back("admin.products_page")

        if category_id <= 0 or price <= 0 or stock <= 0 or (brand_id is not None and brand_id <= 0):
            flash("Các ô số phải lớn hơn 0.", "error")
            return redirect_back("admin.products_page")

        category_exists = fetch_one(
            "SELECT CategoryID FROM dbo.Categories WHERE CategoryID = ?",
            (category_id,),
        )
        if not category_exists:
            flash("Danh mục đã chọn không tồn tại.", "error")
            return redirect_back("admin.products_page")

        if brand_id is not None:
            brand_exists = fetch_one(
                "SELECT BrandID FROM dbo.Brands WHERE BrandID = ?",
                (brand_id,),
            )
            if not brand_exists:
                flash("Thương hiệu đã chọn không tồn tại.", "error")
                return redirect_back("admin.products_page")

        sku_duplicate = fetch_one(
            "SELECT ProductID FROM dbo.Products WHERE SKU = ?",
            (sku,),
        )
        if sku_duplicate:
            flash("SKU này đã tồn tại.", "error")
            return redirect_back("admin.products_page")

        product_columns = get_product_column_names()
        insert_columns = [
            "SKU", "ProductName", "Description", "CategoryID", "BrandID",
            "Price", "Stock", "Unit",
        ]
        insert_values = [
            sku,
            product_name,
            form.get("description") or None,
            category_id,
            brand_id,
            price,
            stock,
            form.get("unit") or "Cái",
        ]

        if "ImageURL" in product_columns:
            image_url = save_product_image(get_uploaded_image(), sku) or form.get("image_url") or None
            insert_columns.append("ImageURL")
            insert_values.append(image_url)
        if "IsActive" in product_columns:
            insert_columns.append("IsActive")
            insert_values.append(1 if form.get("is_active") == "on" else 0)

        placeholders = ", ".join(["?"] * len(insert_columns))
        column_sql = ", ".join(insert_columns)

        connection = get_db_connection()
        try:
            cursor = connection.cursor()
            cursor.execute(
                f"""
                INSERT INTO dbo.Products ({column_sql})
                VALUES ({placeholders})
                """,
                insert_values,
            )
            connection.commit()
        finally:
            connection.close()
        flash("Đã thêm sản phẩm mới.", "success")
    except Exception as exc:
        flash(f"Không thể thêm sản phẩm: {exc}", "error")

    return redirect_back("admin.products_page")


@admin_bp.route("/products/<int:product_id>/update", methods=["POST"])
@require_auth(role="admin")
def update_product(product_id):
    product = fetch_one(
        "SELECT ProductID, SKU FROM dbo.Products WHERE ProductID = ?",
        (product_id,),
    )
    if not product:
        flash("Không tìm thấy sản phẩm.", "error")
        return redirect_back("admin.products_page")
    
    form = request.form
    try:
        sku = (form.get("sku") or "").strip()
        product_name = (form.get("product_name") or "").strip()
        category_id = int(form.get("category_id"))
        brand_id = int(form.get("brand_id")) if form.get("brand_id") else None
        price = float(form.get("price", 0))
        stock = int(form.get("stock", 0))

        if not sku or not product_name:
            flash("SKU và tên sản phẩm là bắt buộc.", "error")
            return redirect_back("admin.products_page")

        if category_id <= 0 or price <= 0 or stock <= 0 or (brand_id is not None and brand_id <= 0):
            flash("Các ô số phải lớn hơn 0.", "error")
            return redirect_back("admin.products_page")

        category_exists = fetch_one(
            "SELECT CategoryID FROM dbo.Categories WHERE CategoryID = ?",
            (category_id,),
        )
        if not category_exists:
            flash("Danh mục đã chọn không tồn tại.", "error")
            return redirect_back("admin.products_page")

        if brand_id is not None:
            brand_exists = fetch_one(
                "SELECT BrandID FROM dbo.Brands WHERE BrandID = ?",
                (brand_id,),
            )
            if not brand_exists:
                flash("Thương hiệu đã chọn không tồn tại.", "error")
                return redirect_back("admin.products_page")

        if sku != product.get("SKU"):
            sku_duplicate = fetch_one(
                "SELECT ProductID FROM dbo.Products WHERE SKU = ?",
                (sku,),
            )
            if sku_duplicate:
                flash("SKU này đã tồn tại.", "error")
                return redirect_back("admin.products_page")

        product_columns = get_product_column_names()
        update_fields = [
            "SKU = ?",
            "ProductName = ?",
            "Description = ?",
            "CategoryID = ?",
            "BrandID = ?",
            "Price = ?",
            "Stock = ?",
            "Unit = ?",
        ]
        update_values = [
            sku,
            product_name,
            form.get("description") or None,
            category_id,
            brand_id,
            price,
            stock,
            form.get("unit") or "Cái",
        ]

        if "ImageURL" in product_columns:
            image_url = save_product_image(get_uploaded_image(), sku) or form.get("image_url") or None
            update_fields.append("ImageURL = ?")
            update_values.append(image_url)
        if "IsActive" in product_columns:
            update_fields.append("IsActive = ?")
            update_values.append(1 if form.get("is_active") == "on" else 0)
        if "UpdatedAt" in product_columns:
            update_fields.append("UpdatedAt = GETDATE()")

        connection = get_db_connection()
        try:
            cursor = connection.cursor()
            cursor.execute(
                f"""
                UPDATE dbo.Products
                SET {", ".join(update_fields)}
                WHERE ProductID = ?
                """,
                (*update_values, product_id),
            )
            connection.commit()
        finally:
            connection.close()
        flash("Đã cập nhật sản phẩm.", "success")
    except Exception as exc:
        flash(f"Không thể cập nhật sản phẩm: {exc}", "error")

    return redirect_back("admin.products_page")


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@require_auth(role="admin")
def delete_product(product_id):
    product = fetch_one(
        "SELECT ProductID FROM dbo.Products WHERE ProductID = ?",
        (product_id,),
    )
    if not product:
        flash("Không tìm thấy sản phẩm.", "error")
        return redirect_back("admin.products_page")
    
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM dbo.Products WHERE ProductID = ?", (product_id,))
        connection.commit()
        flash("Đã xoá sản phẩm.", "success")
    except Exception as exc:
        flash(f"Không thể xoá sản phẩm: {exc}", "error")
    finally:
        connection.close()
    return redirect_back("admin.products_page")


@admin_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@require_auth(role="admin")
def update_order_status(order_id):
    new_status = request.form.get("status")
    valid_statuses = {"pending", "confirmed", "shipping", "delivered", "cancelled"}
    
    if not new_status or new_status not in valid_statuses:
        flash("Trạng thái đơn hàng không hợp lệ.", "error")
        return redirect_back("admin.orders_page")
    
    order = fetch_one(
        "SELECT OrderID FROM dbo.Orders WHERE OrderID = ?",
        (order_id,),
    )
    if not order:
        flash("Không tìm thấy đơn hàng.", "error")
        return redirect_back("admin.orders_page")
    
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
        connection.commit()
        flash("Đã cập nhật trạng thái đơn hàng.", "success")
    except Exception as exc:
        flash(f"Không thể cập nhật trạng thái: {exc}", "error")
    finally:
        connection.close()
    return redirect_back("admin.orders_page")


@admin_bp.route("/categories/create", methods=["POST"])
@require_auth(role="admin")
def create_category():
    category_name = (request.form.get("category_name") or "").strip()
    slug = (request.form.get("slug") or "").strip()
    description = request.form.get("description") or None

    if not category_name or not slug:
        flash("Tên danh mục và slug là bắt buộc.", "error")
        return redirect_back("admin.catalog_page")

    duplicate = fetch_one(
        """
        SELECT CategoryID
        FROM dbo.Categories
        WHERE CategoryName = ? OR Slug = ?
        """,
        (category_name, slug),
    )
    if duplicate:
        flash("Danh mục hoặc slug đã tồn tại.", "error")
        return redirect_back("admin.catalog_page")

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO dbo.Categories (CategoryName, Slug, Description)
            VALUES (?, ?, ?)
            """,
            (category_name, slug, description),
        )
        connection.commit()
        flash("Đã thêm danh mục.", "success")
    except Exception as exc:
        flash(f"Không thể thêm danh mục: {exc}", "error")
    finally:
        connection.close()
    return redirect_back("admin.catalog_page")


@admin_bp.route("/categories/<int:category_id>/update", methods=["POST"])
@require_auth(role="admin")
def update_category(category_id):
    category = fetch_one(
        "SELECT CategoryID FROM dbo.Categories WHERE CategoryID = ?",
        (category_id,),
    )
    if not category:
        flash("Không tìm thấy danh mục.", "error")
        return redirect_back("admin.catalog_page")

    category_name = (request.form.get("category_name") or "").strip()
    slug = (request.form.get("slug") or "").strip()
    description = request.form.get("description") or None

    if not category_name or not slug:
        flash("Tên danh mục và slug là bắt buộc.", "error")
        return redirect_back("admin.catalog_page")

    duplicate = fetch_one(
        """
        SELECT CategoryID
        FROM dbo.Categories
        WHERE (CategoryName = ? OR Slug = ?) AND CategoryID <> ?
        """,
        (category_name, slug, category_id),
    )
    if duplicate:
        flash("Danh mục hoặc slug đã tồn tại.", "error")
        return redirect_back("admin.catalog_page")

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE dbo.Categories
            SET CategoryName = ?, Slug = ?, Description = ?
            WHERE CategoryID = ?
            """,
            (category_name, slug, description, category_id),
        )
        connection.commit()
        flash("Đã cập nhật danh mục.", "success")
    except Exception as exc:
        flash(f"Không thể cập nhật danh mục: {exc}", "error")
    finally:
        connection.close()
    return redirect_back("admin.catalog_page")


@admin_bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@require_auth(role="admin")
def delete_category(category_id):
    category = fetch_one(
        "SELECT CategoryID FROM dbo.Categories WHERE CategoryID = ?",
        (category_id,),
    )
    if not category:
        flash("Không tìm thấy danh mục.", "error")
        return redirect_back("admin.catalog_page")

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "DELETE FROM dbo.Categories WHERE CategoryID = ?",
            (category_id,),
        )
        connection.commit()
        flash("Đã xóa danh mục.", "success")
    except Exception as exc:
        flash(f"Không thể xóa danh mục: {exc}", "error")
    finally:
        connection.close()
    return redirect_back("admin.catalog_page")


@admin_bp.route("/brands/create", methods=["POST"])
@require_auth(role="admin")
def create_brand():
    brand_name = (request.form.get("brand_name") or "").strip()
    country = request.form.get("country") or None
    website = request.form.get("website") or None

    if not brand_name:
        flash("Tên thương hiệu là bắt buộc.", "error")
        return redirect_back("admin.catalog_page")

    duplicate = fetch_one(
        """
        SELECT BrandID
        FROM dbo.Brands
        WHERE BrandName = ?
        """,
        (brand_name,),
    )
    if duplicate:
        flash("Thương hiệu này đã tồn tại.", "error")
        return redirect_back("admin.catalog_page")

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO dbo.Brands (BrandName, Country, Website)
            VALUES (?, ?, ?)
            """,
            (brand_name, country, website),
        )
        connection.commit()
        flash("Đã thêm thương hiệu.", "success")
    except Exception as exc:
        flash(f"Không thể thêm thương hiệu: {exc}", "error")
    finally:
        connection.close()
    return redirect_back("admin.catalog_page")


@admin_bp.route("/brands/<int:brand_id>/update", methods=["POST"])
@require_auth(role="admin")
def update_brand(brand_id):
    brand = fetch_one(
        "SELECT BrandID FROM dbo.Brands WHERE BrandID = ?",
        (brand_id,),
    )
    if not brand:
        flash("Không tìm thấy thương hiệu.", "error")
        return redirect_back("admin.catalog_page")

    brand_name = (request.form.get("brand_name") or "").strip()
    country = request.form.get("country") or None
    website = request.form.get("website") or None

    if not brand_name:
        flash("Tên thương hiệu là bắt buộc.", "error")
        return redirect_back("admin.catalog_page")

    duplicate = fetch_one(
        """
        SELECT BrandID
        FROM dbo.Brands
        WHERE BrandName = ? AND BrandID <> ?
        """,
        (brand_name, brand_id),
    )
    if duplicate:
        flash("Thương hiệu này đã tồn tại.", "error")
        return redirect_back("admin.catalog_page")

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE dbo.Brands
            SET BrandName = ?, Country = ?, Website = ?
            WHERE BrandID = ?
            """,
            (brand_name, country, website, brand_id),
        )
        connection.commit()
        flash("Đã cập nhật thương hiệu.", "success")
    except Exception as exc:
        flash(f"Không thể cập nhật thương hiệu: {exc}", "error")
    finally:
        connection.close()
    return redirect_back("admin.catalog_page")


@admin_bp.route("/brands/<int:brand_id>/delete", methods=["POST"])
@require_auth(role="admin")
def delete_brand(brand_id):
    brand = fetch_one(
        "SELECT BrandID FROM dbo.Brands WHERE BrandID = ?",
        (brand_id,),
    )
    if not brand:
        flash("Không tìm thấy thương hiệu.", "error")
        return redirect_back("admin.catalog_page")

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "DELETE FROM dbo.Brands WHERE BrandID = ?",
            (brand_id,),
        )
        connection.commit()
        flash("Đã xóa thương hiệu.", "success")
    except Exception as exc:
        flash(f"Không thể xóa thương hiệu: {exc}", "error")
    finally:
        connection.close()
    return redirect_back("admin.catalog_page")


@admin_bp.route("/employees/create", methods=["POST"])
@require_auth(role="admin")
def create_employee():
    full_name = (request.form.get("full_name") or "").strip()
    email = (request.form.get("email") or "").strip()
    phone = (request.form.get("phone") or "").strip() or None
    position = (request.form.get("position") or "").strip()
    hire_date = (request.form.get("hire_date") or "").strip()
    salary = parse_salary(request.form.get("salary"))
    is_active = 1 if request.form.get("is_active") == "on" else 0

    if not full_name or not email or not position or not hire_date:
        flash("Tên, email, chức vụ và ngày vào làm là bắt buộc.", "error")
        return redirect_back("admin.employees_page")
    if salary is None or salary < 0:
        flash("Lương phải là số không âm.", "error")
        return redirect_back("admin.employees_page")
    if fetch_one("SELECT EmployeeID FROM dbo.Employees WHERE Email = ?", (email,)):
        flash("Email nhân viên đã tồn tại.", "error")
        return redirect_back("admin.employees_page")

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO dbo.Employees (FullName, Email, Phone, Position, HireDate, Salary, IsActive)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (full_name, email, phone, position, hire_date, salary, is_active),
        )
        connection.commit()
        flash("Đã thêm nhân viên.", "success")
    except Exception as exc:
        flash(f"Không thể thêm nhân viên: {exc}", "error")
    finally:
        connection.close()
    return redirect_back("admin.employees_page")


@admin_bp.route("/employees/<int:employee_id>/update", methods=["POST"])
@require_auth(role="admin")
def update_employee(employee_id):
    employee = fetch_one("SELECT EmployeeID FROM dbo.Employees WHERE EmployeeID = ?", (employee_id,))
    if not employee:
        flash("Không tìm thấy nhân viên.", "error")
        return redirect_back("admin.employees_page")

    full_name = (request.form.get("full_name") or "").strip()
    email = (request.form.get("email") or "").strip()
    phone = (request.form.get("phone") or "").strip() or None
    position = (request.form.get("position") or "").strip()
    hire_date = (request.form.get("hire_date") or "").strip()
    salary = parse_salary(request.form.get("salary"))
    is_active = 1 if request.form.get("is_active") == "on" else 0

    if not full_name or not email or not position or not hire_date:
        flash("Tên, email, chức vụ và ngày vào làm là bắt buộc.", "error")
        return redirect_back("admin.employees_page")
    if salary is None or salary < 0:
        flash("Lương phải là số không âm.", "error")
        return redirect_back("admin.employees_page")
    if fetch_one("SELECT EmployeeID FROM dbo.Employees WHERE Email = ? AND EmployeeID <> ?", (email, employee_id)):
        flash("Email nhân viên đã tồn tại.", "error")
        return redirect_back("admin.employees_page")

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE dbo.Employees
            SET FullName = ?, Email = ?, Phone = ?, Position = ?, HireDate = ?, Salary = ?, IsActive = ?
            WHERE EmployeeID = ?
            """,
            (full_name, email, phone, position, hire_date, salary, is_active, employee_id),
        )
        connection.commit()
        flash("Đã cập nhật nhân viên.", "success")
    except Exception as exc:
        flash(f"Không thể cập nhật nhân viên: {exc}", "error")
    finally:
        connection.close()
    return redirect_back("admin.employees_page")


@admin_bp.route("/employees/<int:employee_id>/delete", methods=["POST"])
@require_auth(role="admin")
def delete_employee(employee_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM dbo.Employees WHERE EmployeeID = ?", (employee_id,))
        connection.commit()
        flash("Đã xóa nhân viên.", "success")
    except Exception as exc:
        flash(f"Không thể xóa nhân viên: {exc}", "error")
    finally:
        connection.close()
    return redirect_back("admin.employees_page")


@admin_bp.route("/suppliers/create", methods=["POST"])
@require_auth(role="admin")
def create_supplier():
    supplier_name = (request.form.get("supplier_name") or "").strip()
    contact_name = (request.form.get("contact_name") or "").strip() or None
    email = (request.form.get("email") or "").strip() or None
    phone = (request.form.get("phone") or "").strip() or None
    address = (request.form.get("address") or "").strip() or None

    if not supplier_name:
        flash("Tên nhà cung cấp là bắt buộc.", "error")
        return redirect_back("admin.suppliers_page")
    if fetch_one("SELECT SupplierID FROM dbo.Suppliers WHERE SupplierName = ?", (supplier_name,)):
        flash("Nhà cung cấp đã tồn tại.", "error")
        return redirect_back("admin.suppliers_page")

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO dbo.Suppliers (SupplierName, ContactName, Email, Phone, Address)
            VALUES (?, ?, ?, ?, ?)
            """,
            (supplier_name, contact_name, email, phone, address),
        )
        connection.commit()
        flash("Đã thêm nhà cung cấp.", "success")
    except Exception as exc:
        flash(f"Không thể thêm nhà cung cấp: {exc}", "error")
    finally:
        connection.close()
    return redirect_back("admin.suppliers_page")


@admin_bp.route("/suppliers/<int:supplier_id>/update", methods=["POST"])
@require_auth(role="admin")
def update_supplier(supplier_id):
    supplier = fetch_one("SELECT SupplierID FROM dbo.Suppliers WHERE SupplierID = ?", (supplier_id,))
    if not supplier:
        flash("Không tìm thấy nhà cung cấp.", "error")
        return redirect_back("admin.suppliers_page")

    supplier_name = (request.form.get("supplier_name") or "").strip()
    contact_name = (request.form.get("contact_name") or "").strip() or None
    email = (request.form.get("email") or "").strip() or None
    phone = (request.form.get("phone") or "").strip() or None
    address = (request.form.get("address") or "").strip() or None

    if not supplier_name:
        flash("Tên nhà cung cấp là bắt buộc.", "error")
        return redirect_back("admin.suppliers_page")
    if fetch_one("SELECT SupplierID FROM dbo.Suppliers WHERE SupplierName = ? AND SupplierID <> ?", (supplier_name, supplier_id)):
        flash("Nhà cung cấp đã tồn tại.", "error")
        return redirect_back("admin.suppliers_page")

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE dbo.Suppliers
            SET SupplierName = ?, ContactName = ?, Email = ?, Phone = ?, Address = ?
            WHERE SupplierID = ?
            """,
            (supplier_name, contact_name, email, phone, address, supplier_id),
        )
        connection.commit()
        flash("Đã cập nhật nhà cung cấp.", "success")
    except Exception as exc:
        flash(f"Không thể cập nhật nhà cung cấp: {exc}", "error")
    finally:
        connection.close()
    return redirect_back("admin.suppliers_page")


@admin_bp.route("/suppliers/<int:supplier_id>/delete", methods=["POST"])
@require_auth(role="admin")
def delete_supplier(supplier_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM dbo.Suppliers WHERE SupplierID = ?", (supplier_id,))
        connection.commit()
        flash("Đã xóa nhà cung cấp.", "success")
    except Exception as exc:
        flash(f"Không thể xóa nhà cung cấp: {exc}", "error")
    finally:
        connection.close()
    return redirect_back("admin.suppliers_page")

@admin_bp.route("/promotions/create", methods=["POST"])
@require_auth(role="admin")
def create_promotion():
    code = (request.form.get("code") or "").strip()
    discount_type = request.form.get("discount_type")
    discount_value = float(request.form.get("discount_value", 0))
    min_order_value = float(request.form.get("min_order_value")) if request.form.get("min_order_value") else None
    max_uses = int(request.form.get("max_uses")) if request.form.get("max_uses") else None
    
    try:
        starts_at = parse_form_datetime(request.form.get("starts_at"))
        expires_at = parse_form_datetime(request.form.get("expires_at"))
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect_back("admin.promotions_page")
    
    if not code or not discount_type:
        flash("Mã khuyến mãi và loại giảm giá là bắt buộc.", "error")
        return redirect_back("admin.promotions_page")

    if starts_at and expires_at and expires_at <= starts_at:
        flash("Ngày kết thúc phải sau ngày bắt đầu.", "error")
        return redirect_back("admin.promotions_page")
    
    if discount_value <= 0 or (min_order_value is not None and min_order_value <= 0) or (max_uses is not None and max_uses <= 0):
        flash("Các ô số phải lớn hơn 0.", "error")
        return redirect_back("admin.promotions_page")
    
    duplicate = fetch_one(
        "SELECT PromotionID FROM dbo.Promotions WHERE Code = ?",
        (code,),
    )
    if duplicate:
        flash("Mã khuyến mãi này đã tồn tại.", "error")
        return redirect_back("admin.promotions_page")

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO dbo.Promotions (
                Code, Description, DiscountType, DiscountValue, MinOrderValue,
                MaxUses, StartsAt, ExpiresAt, IsActive
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                code,
                request.form.get("description") or None,
                discount_type,
                discount_value,
                min_order_value or None,
                max_uses,
                starts_at,
                expires_at,
                1 if request.form.get("is_active") == "on" else 0,
            ),
        )
        connection.commit()
        flash("Đã thêm khuyến mãi.", "success")
    except Exception as exc:
        flash(f"Không thể thêm khuyến mãi: {exc}", "error")
    finally:
        connection.close()
    return redirect_back("admin.promotions_page")


@admin_bp.route("/accounts/<int:account_id>/toggle", methods=["POST"])
@require_auth(role="admin")
def toggle_account(account_id):
    target_account = fetch_one(
        """
        SELECT AccountID, Role, Email
        FROM dbo.Accounts
        WHERE AccountID = ?
        """,
        (account_id,),
    )
    if not target_account:
        flash("Không tìm thấy tài khoản.", "error")
        return redirect_back("admin.accounts_page")

    if target_account.get("Role") == "admin":
        flash("Không thể khoá tài khoản admin.", "error")
        return redirect_back("admin.accounts_page")

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE dbo.Accounts
            SET IsActive = CASE WHEN IsActive = 1 THEN 0 ELSE 1 END
            WHERE AccountID = ?
            """,
            (account_id,),
        )
        connection.commit()
        flash("Đã cập nhật trạng thái tài khoản.", "success")
    except Exception as exc:
        flash(f"Không thể cập nhật trạng thái: {exc}", "error")
    finally:
        connection.close()
    return redirect_back("admin.accounts_page")


@admin_bp.route("/accounts/<int:account_id>/set-role", methods=["POST"])
@require_primary_admin
def set_account_role(account_id):
    new_role = request.form.get("role")
    if new_role not in {"user", "admin"}:
        flash("Vai trò không hợp lệ.", "error")
        return redirect_back("admin.accounts_page")

    target_account = fetch_one(
        """
        SELECT AccountID, Email, Role
        FROM dbo.Accounts
        WHERE AccountID = ?
        """,
        (account_id,),
    )
    if not target_account:
        flash("Không tìm thấy tài khoản.", "error")
        return redirect_back("admin.accounts_page")

    if target_account.get("Email") == current_app.config["ADMIN_LOGIN_EMAIL"]:
        flash("Không thể thay đổi vai trò của quản trị viên chính.", "error")
        return redirect_back("admin.accounts_page")

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE dbo.Accounts
            SET Role = ?,
                RequestedRole = CASE WHEN ? = 'admin' THEN NULL ELSE RequestedRole END,
                AdminRequestStatus = CASE WHEN ? = 'admin' THEN 'approved' ELSE ISNULL(AdminRequestStatus, 'none') END
            WHERE AccountID = ?
            """,
            (new_role, new_role, new_role, account_id),
        )
        connection.commit()
    finally:
        connection.close()

    flash("Đã cập nhật vai trò tài khoản.", "success")
    return redirect_back("admin.accounts_page")


@admin_bp.route("/accounts/<int:account_id>/approve-admin", methods=["POST"])
@require_primary_admin
def approve_admin_request(account_id):
    account = fetch_one(
        "SELECT AccountID FROM dbo.Accounts WHERE AccountID = ?",
        (account_id,),
    )
    if not account:
        flash("Không tìm thấy tài khoản.", "error")
        return redirect_back("admin.accounts_page")
    
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE dbo.Accounts
            SET Role = 'admin',
                RequestedRole = NULL,
                AdminRequestStatus = 'approved'
            WHERE AccountID = ?
            """,
            (account_id,),
        )
        connection.commit()
        flash("Đã cấp quyền quản trị viên.", "success")
    except Exception as exc:
        flash(f"Không thể cấp quyền: {exc}", "error")
    finally:
        connection.close()
    return redirect_back("admin.accounts_page")


@admin_bp.route("/accounts/<int:account_id>/reject-admin", methods=["POST"])
@require_primary_admin
def reject_admin_request(account_id):
    account = fetch_one(
        "SELECT AccountID FROM dbo.Accounts WHERE AccountID = ?",
        (account_id,),
    )
    if not account:
        flash("Không tìm thấy tài khoản.", "error")
        return redirect_back("admin.accounts_page")
    
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE dbo.Accounts
            SET RequestedRole = NULL,
                AdminRequestStatus = 'rejected'
            WHERE AccountID = ?
            """,
            (account_id,),
        )
        connection.commit()
        flash("Đã từ chối yêu cầu quản trị viên.", "success")
    except Exception as exc:
        flash(f"Không thể từ chối yêu cầu: {exc}", "error")
    finally:
        connection.close()
    return redirect_back("admin.accounts_page")


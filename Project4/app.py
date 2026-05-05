from functools import wraps
import os
import sqlite3

from flask import Flask, abort, flash, g, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "edustore.db")
IMAGE_DIR = os.path.join(BASE_DIR, "images")

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-edustore-secret-key"
app.config["PER_PAGE"] = 8


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query_all(sql, params=()):
    return get_db().execute(sql, params).fetchall()


def query_one(sql, params=()):
    return get_db().execute(sql, params).fetchone()


def execute(sql, params=()):
    db = get_db()
    cur = db.execute(sql, params)
    db.commit()
    return cur


def current_user():
    user_id = session.get("account_id")
    if not user_id:
        return None
    return query_one("SELECT * FROM g6_Accounts WHERE g6_AccountID = ?", (user_id,))


@app.context_processor
def inject_globals():
    return {
        "current_user": current_user(),
        "cart_count": sum(session.get("cart", {}).values()),
    }


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("account_id"):
            flash("Vui lòng đăng nhập để tiếp tục.", "warning")
            return redirect(url_for("login", next=request.full_path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user or user["g6_Role"] != "admin":
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def init_db():
    with app.app_context():
        db = get_db()
        db.executescript(
            """
            DROP TABLE IF EXISTS g6_OrderItems;
            DROP TABLE IF EXISTS g6_Orders;
            DROP TABLE IF EXISTS g6_AdminEvents;
            DROP TABLE IF EXISTS g6_Reviews;
            DROP TABLE IF EXISTS g6_Promotions;
            DROP TABLE IF EXISTS g6_Accounts;
            DROP TABLE IF EXISTS g6_Customers;
            DROP TABLE IF EXISTS g6_Products;
            DROP TABLE IF EXISTS g6_Suppliers;
            DROP TABLE IF EXISTS g6_Employees;
            DROP TABLE IF EXISTS g6_Brands;
            DROP TABLE IF EXISTS g6_Categories;

            CREATE TABLE g6_Categories (
                g6_CategoryID INTEGER PRIMARY KEY AUTOINCREMENT,
                g6_CategoryName TEXT NOT NULL UNIQUE,
                g6_Slug TEXT NOT NULL UNIQUE,
                g6_Description TEXT,
                g6_CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE g6_Brands (
                g6_BrandID INTEGER PRIMARY KEY AUTOINCREMENT,
                g6_BrandName TEXT NOT NULL UNIQUE,
                g6_Country TEXT,
                g6_Website TEXT,
                g6_CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE g6_Employees (
                g6_EmployeeID INTEGER PRIMARY KEY AUTOINCREMENT,
                g6_FullName TEXT NOT NULL,
                g6_Email TEXT NOT NULL UNIQUE,
                g6_Phone TEXT,
                g6_Position TEXT NOT NULL,
                g6_HireDate TEXT NOT NULL,
                g6_Salary INTEGER NOT NULL DEFAULT 0,
                g6_IsActive INTEGER NOT NULL DEFAULT 1,
                g6_CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE g6_Suppliers (
                g6_SupplierID INTEGER PRIMARY KEY AUTOINCREMENT,
                g6_SupplierName TEXT NOT NULL UNIQUE,
                g6_ContactName TEXT,
                g6_Email TEXT,
                g6_Phone TEXT,
                g6_Address TEXT,
                g6_CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE g6_Products (
                g6_ProductID INTEGER PRIMARY KEY AUTOINCREMENT,
                g6_SKU TEXT NOT NULL UNIQUE,
                g6_ProductName TEXT NOT NULL,
                g6_Description TEXT,
                g6_CategoryID INTEGER NOT NULL,
                g6_BrandID INTEGER,
                g6_Price INTEGER NOT NULL,
                g6_Stock INTEGER NOT NULL DEFAULT 0,
                g6_Unit TEXT NOT NULL DEFAULT 'Cái',
                g6_ImageURL TEXT,
                g6_IsActive INTEGER NOT NULL DEFAULT 1,
                g6_CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                g6_UpdatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (g6_CategoryID) REFERENCES g6_Categories(g6_CategoryID),
                FOREIGN KEY (g6_BrandID) REFERENCES g6_Brands(g6_BrandID)
            );

            CREATE TABLE g6_Customers (
                g6_CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
                g6_FullName TEXT NOT NULL,
                g6_Email TEXT NOT NULL UNIQUE,
                g6_Phone TEXT,
                g6_Address TEXT,
                g6_CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE g6_Accounts (
                g6_AccountID INTEGER PRIMARY KEY AUTOINCREMENT,
                g6_FullName TEXT NOT NULL,
                g6_Email TEXT NOT NULL UNIQUE,
                g6_Password TEXT NOT NULL,
                g6_Role TEXT NOT NULL CHECK (g6_Role IN ('admin', 'user')),
                g6_CustomerID INTEGER,
                g6_IsActive INTEGER NOT NULL DEFAULT 1,
                g6_AdminRequestStatus TEXT NOT NULL DEFAULT 'none',
                g6_RequestedRole TEXT,
                g6_CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (g6_CustomerID) REFERENCES g6_Customers(g6_CustomerID)
            );

            CREATE TABLE g6_AdminEvents (
                g6_EventID INTEGER PRIMARY KEY AUTOINCREMENT,
                g6_EventType TEXT NOT NULL,
                g6_Title TEXT NOT NULL,
                g6_Details TEXT,
                g6_ActorName TEXT,
                g6_ActorEmail TEXT,
                g6_RelatedOrderID INTEGER,
                g6_CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE g6_Orders (
                g6_OrderID INTEGER PRIMARY KEY AUTOINCREMENT,
                g6_CustomerID INTEGER NOT NULL,
                g6_OrderStatus TEXT NOT NULL DEFAULT 'pending',
                g6_ShippingAddress TEXT,
                g6_Note TEXT,
                g6_TotalAmount INTEGER NOT NULL DEFAULT 0,
                g6_Discount INTEGER NOT NULL DEFAULT 0,
                g6_CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                g6_UpdatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (g6_CustomerID) REFERENCES g6_Customers(g6_CustomerID)
            );

            CREATE TABLE g6_OrderItems (
                g6_OrderItemID INTEGER PRIMARY KEY AUTOINCREMENT,
                g6_OrderID INTEGER NOT NULL,
                g6_ProductID INTEGER NOT NULL,
                g6_Quantity INTEGER NOT NULL,
                g6_UnitPrice INTEGER NOT NULL,
                FOREIGN KEY (g6_OrderID) REFERENCES g6_Orders(g6_OrderID) ON DELETE CASCADE,
                FOREIGN KEY (g6_ProductID) REFERENCES g6_Products(g6_ProductID)
            );

            CREATE TABLE g6_Reviews (
                g6_ReviewID INTEGER PRIMARY KEY AUTOINCREMENT,
                g6_ProductID INTEGER NOT NULL,
                g6_CustomerID INTEGER NOT NULL,
                g6_Rating INTEGER NOT NULL,
                g6_Comment TEXT,
                g6_CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (g6_ProductID, g6_CustomerID)
            );

            CREATE TABLE g6_Promotions (
                g6_PromotionID INTEGER PRIMARY KEY AUTOINCREMENT,
                g6_Code TEXT NOT NULL UNIQUE,
                g6_Description TEXT,
                g6_DiscountType TEXT NOT NULL,
                g6_DiscountValue INTEGER NOT NULL,
                g6_MinOrderValue INTEGER NOT NULL DEFAULT 0,
                g6_MaxUses INTEGER,
                g6_UsedCount INTEGER NOT NULL DEFAULT 0,
                g6_StartsAt TEXT,
                g6_ExpiresAt TEXT,
                g6_IsActive INTEGER NOT NULL DEFAULT 1
            );
            """
        )
        seed_db(db)
        db.commit()


def seed_db(db):
    categories = [
        ("Văn phòng phẩm", "van-phong-pham", "Bút, thước, kéo, tẩy, hồ dán"),
        ("Sách giáo khoa", "sach-giao-khoa", "SGK các cấp tiểu học, THCS, THPT"),
        ("Sách tham khảo", "sach-tham-khao", "Sách nâng cao, luyện thi, bài tập"),
        ("Thiết bị điện tử", "thiet-bi-dien-tu", "Máy tính, bảng vẽ điện tử, tai nghe"),
        ("Dụng cụ vẽ", "dung-cu-ve", "Màu vẽ, cọ, giấy vẽ, khung tranh"),
        ("Balo & Túi học", "balo-tui-hoc", "Balo đi học, túi đựng sách các loại"),
    ]
    db.executemany("INSERT INTO g6_Categories (g6_CategoryName, g6_Slug, g6_Description) VALUES (?, ?, ?)", categories)

    brands = [
        ("Thiên Long", "Việt Nam", "https://thienlong.com.vn"),
        ("Hồng Hà", "Việt Nam", "https://honghavnn.vn"),
        ("Stabilo", "Đức", "https://stabilo.com"),
        ("Casio", "Nhật Bản", "https://casio.com"),
        ("Samsung", "Hàn Quốc", "https://samsung.com"),
        ("Staedtler", "Đức", "https://staedtler.com"),
    ]
    db.executemany("INSERT INTO g6_Brands (g6_BrandName, g6_Country, g6_Website) VALUES (?, ?, ?)", brands)

    products = [
        ("VPP-001", "Bút bi Thiên Long TL-027", "Ngòi 0.5mm mực xanh, viết êm", 1, 1, 5000, 500, "Cái"),
        ("VPP-002", "Bút chì Staedtler 2B", "Chì mềm, đường nét đẹp", 1, 6, 8000, 300, "Cái"),
        ("VPP-003", "Tẩy Stabilo hình chữ nhật", "Tẩy sạch, không để lại vết bẩn", 1, 3, 6000, 400, "Cái"),
        ("VPP-004", "Thước kẻ 30cm Thiên Long", "Nhựa trong suốt, có vạch mm", 1, 1, 12000, 200, "Cái"),
        ("VPP-005", "Hộp bút màu Stabilo 24 màu", "Màu dạ sáng, không lem", 5, 3, 85000, 150, "Hộp"),
        ("VPP-006", "Kéo học sinh Thiên Long", "Lưỡi thép không gỉ, tay cầm nhựa", 1, 1, 18000, 250, "Cái"),
        ("SGK-001", "SGK Toán 10 (Bộ Kết Nối)", "Sách giáo khoa Toán lớp 10", 2, 2, 32000, 300, "Cuốn"),
        ("SGK-002", "SGK Ngữ Văn 11 (Bộ KNTT)", "Sách giáo khoa Ngữ Văn lớp 11", 2, 2, 28000, 250, "Cuốn"),
        ("SGK-003", "SGK Vật Lý 12", "Sách giáo khoa Vật Lý lớp 12", 2, 2, 30000, 200, "Cuốn"),
        ("SGK-004", "SGK Tiếng Anh 9 Global Success", "NXB Giáo Dục Việt Nam", 2, 2, 26000, 280, "Cuốn"),
        ("STK-001", "Bộ đề thi thử THPT Quốc Gia Toán", "30 đề có đáp án chi tiết", 3, 2, 65000, 120, "Cuốn"),
        ("STK-002", "Ôn tập Tiếng Anh B1-B2", "Luyện 4 kỹ năng IELTS/TOEIC", 3, 2, 89000, 90, "Cuốn"),
        ("STK-003", "Bài tập Hóa học 11 nâng cao", "Có đáp án và giải thích từng bước", 3, 2, 55000, 110, "Cuốn"),
        ("DTE-001", "Máy tính Casio FX-580VN X", "570 hàm, màn hình tự nhiên, pin AA", 4, 4, 495000, 80, "Cái"),
        ("DTE-002", "Bảng vẽ điện tử Wacom Ctl-472", "Cảm ứng bút, kết nối USB", 4, 5, 1490000, 30, "Cái"),
        ("DTE-003", "Tai nghe Samsung AKG Type-C", "Âm bass tốt, giảm tiếng ồn", 4, 5, 390000, 60, "Cái"),
        ("DVE-001", "Màu nước Stabilo 12 màu", "Không độc hại, dễ pha trộn", 5, 3, 45000, 200, "Hộp"),
        ("DVE-002", "Cọ vẽ số 6 lông tổng hợp", "Cọ mềm, không xòe lông", 5, 6, 18000, 180, "Cái"),
        ("DVE-003", "Giấy vẽ A3 200gsm", "Bề mặt mịn, dùng được cho màu nước", 5, None, 35000, 100, "Tập"),
        ("BAL-001", "Balo học sinh Hồng Hà 3 ngăn", "Chống thấm, đệm lưng, quai điều chỉnh", 6, 2, 320000, 70, "Cái"),
        ("BAL-002", "Túi đeo chéo mini vải canvas", "Nhẹ, nhiều ngăn, khóa kim loại bền", 6, 2, 175000, 100, "Cái"),
    ]
    product_images = {
        "VPP-001": "tl-027.jpg",
        "VPP-002": "staedtler-2b.jpg",
        "VPP-003": "stabilo-eraser.jpg",
        "VPP-004": "ruler-30cm.jpg",
        "VPP-005": "stabilo-24-colors.jpg",
        "VPP-006": "scissors.jpg",
        "SGK-001": "sgk-toan-10.jpg",
        "SGK-002": "sgk-van-11.jpg",
        "SGK-003": "sgk-ly-12.jpg",
        "SGK-004": "sgk-ta-9.jpg",
        "STK-001": "on-thi-toan.jpg",
        "STK-002": "tieng-anh-b1.jpg",
        "STK-003": "bai-tap-hoa-11.jpg",
        "DTE-001": "casio-580vnx.jpeg",
        "DTE-002": "wacom-472.jpg",
        "DTE-003": "samsung-akg.jpg",
        "DVE-001": "stabilo-watercolor.jpg",
        "DVE-002": "brush-no6.jpg",
        "DVE-003": "paper-a3.jpg",
        "BAL-001": "balo-hong-ha.jpg",
        "BAL-002": "tui-canvas.jpg",
    }

    db.executemany(
        """
        INSERT INTO g6_Products
        (g6_SKU, g6_ProductName, g6_Description, g6_CategoryID, g6_BrandID, g6_Price, g6_Stock, g6_Unit, g6_ImageURL)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [(*p, f"/images/{product_images[p[0]]}") for p in products],
    )

    customers = [
        ("Nguyễn Minh Anh", "minha@email.com", "0901234567", "12 Lê Lợi, Hoàn Kiếm, Hà Nội"),
        ("Trần Quốc Bảo", "baotq@email.com", "0912345678", "45 Trần Phú, Hải Châu, Đà Nẵng"),
        ("Lê Thị Cẩm", "camlth@email.com", "0923456789", "89 Nguyễn Huệ, Q.1, TP.HCM"),
        ("Phạm Đức Dũng", "dungpd@email.com", "0934567890", "7 Bà Triệu, Hồng Bàng, Hải Phòng"),
        ("Võ Thị Hoa", "hoavt@email.com", "0945678901", "23 Hùng Vương, Pleiku, Gia Lai"),
    ]
    db.executemany("INSERT INTO g6_Customers (g6_FullName, g6_Email, g6_Phone, g6_Address) VALUES (?, ?, ?, ?)", customers)

    accounts = [
        ("Người dùng mẫu", "user@edustore.local", "user123", "user", 1, "none", None),
        ("Người dùng Minh Anh", "minha@email.com", "123456", "user", 1, "none", None),
        ("Người dùng Quốc Bảo", "baotq@email.com", "123456", "user", 2, "pending", "admin"),
        ("Quản trị viên chính", "admin@edustore.local", "admin123", "admin", None, "approved", None),
        ("Quản trị viên kho", "manager@edustore.local", "manager123", "admin", None, "approved", None),
    ]
    db.executemany(
        """
        INSERT INTO g6_Accounts
        (g6_FullName, g6_Email, g6_Password, g6_Role, g6_CustomerID, g6_AdminRequestStatus, g6_RequestedRole)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [(name, email, generate_password_hash(password), role, cid, status, requested) for name, email, password, role, cid, status, requested in accounts],
    )

    db.executemany(
        "INSERT INTO g6_Promotions (g6_Code, g6_Description, g6_DiscountType, g6_DiscountValue, g6_MinOrderValue, g6_MaxUses, g6_StartsAt, g6_ExpiresAt) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("BACK2SCHOOL", "Giảm 10% cho đơn từ 200.000đ", "percent", 10, 200000, 100, "2025-08-01", "2025-09-30"),
            ("GIAM50K", "Giảm 50.000đ cho đơn từ 500.000đ", "fixed", 50000, 500000, 50, "2025-01-01", "2025-12-31"),
            ("NEWUSER", "Giảm 5% không giới hạn đơn", "percent", 5, 0, 200, "2025-01-01", "2025-12-31"),
        ],
    )


@app.template_filter("vnd")
def vnd(value):
    return f"{int(value or 0):,}".replace(",", ".") + "đ"


@app.route("/images/<path:filename>")
def product_image(filename):
    return send_from_directory(IMAGE_DIR, filename)


@app.route("/")
def home():
    categories = query_all("SELECT * FROM g6_Categories ORDER BY g6_CategoryName")
    products = query_all(
        """
        SELECT p.*, c.g6_CategoryName, b.g6_BrandName
        FROM g6_Products p
        JOIN g6_Categories c ON c.g6_CategoryID = p.g6_CategoryID
        LEFT JOIN g6_Brands b ON b.g6_BrandID = p.g6_BrandID
        WHERE p.g6_IsActive = 1
        ORDER BY p.g6_ProductID DESC
        LIMIT 8
        """
    )
    return render_template("home.html", categories=categories, products=products)


@app.route("/products")
def products():
    keyword = request.args.get("q", "").strip()
    category_id = request.args.get("category", "").strip()
    brand_id = request.args.get("brand", "").strip()
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = app.config["PER_PAGE"]

    where = ["p.g6_IsActive = 1"]
    params = []
    if keyword:
        where.append("(p.g6_ProductName LIKE ? OR p.g6_SKU LIKE ? OR p.g6_Description LIKE ?)")
        like = f"%{keyword}%"
        params.extend([like, like, like])
    if category_id:
        where.append("p.g6_CategoryID = ?")
        params.append(category_id)
    if brand_id:
        where.append("p.g6_BrandID = ?")
        params.append(brand_id)

    where_sql = " AND ".join(where)
    total = query_one(f"SELECT COUNT(*) AS total FROM g6_Products p WHERE {where_sql}", params)["total"]
    offset = (page - 1) * per_page
    rows = query_all(
        f"""
        SELECT p.*, c.g6_CategoryName, b.g6_BrandName
        FROM g6_Products p
        JOIN g6_Categories c ON c.g6_CategoryID = p.g6_CategoryID
        LEFT JOIN g6_Brands b ON b.g6_BrandID = p.g6_BrandID
        WHERE {where_sql}
        ORDER BY p.g6_ProductID DESC
        LIMIT ? OFFSET ?
        """,
        [*params, per_page, offset],
    )
    return render_template(
        "products.html",
        products=rows,
        categories=query_all("SELECT * FROM g6_Categories ORDER BY g6_CategoryName"),
        brands=query_all("SELECT * FROM g6_Brands ORDER BY g6_BrandName"),
        total=total,
        page=page,
        pages=max((total + per_page - 1) // per_page, 1),
        filters={"q": keyword, "category": category_id, "brand": brand_id},
    )


@app.route("/products/<int:product_id>")
def product_detail(product_id):
    product = query_one(
        """
        SELECT p.*, c.g6_CategoryName, b.g6_BrandName
        FROM g6_Products p
        JOIN g6_Categories c ON c.g6_CategoryID = p.g6_CategoryID
        LEFT JOIN g6_Brands b ON b.g6_BrandID = p.g6_BrandID
        WHERE p.g6_ProductID = ?
        """,
        (product_id,),
    )
    if not product:
        abort(404)
    reviews = query_all(
        """
        SELECT r.*, c.g6_FullName
        FROM g6_Reviews r
        JOIN g6_Customers c ON c.g6_CustomerID = r.g6_CustomerID
        WHERE r.g6_ProductID = ?
        ORDER BY r.g6_CreatedAt DESC
        """,
        (product_id,),
    )
    return render_template("product_detail.html", product=product, reviews=reviews)


@app.route("/cart/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    product = query_one("SELECT g6_ProductID, g6_Stock FROM g6_Products WHERE g6_ProductID = ? AND g6_IsActive = 1", (product_id,))
    if not product:
        abort(404)
    qty = max(request.form.get("quantity", 1, type=int), 1)
    cart = session.setdefault("cart", {})
    key = str(product_id)
    cart[key] = min(cart.get(key, 0) + qty, product["g6_Stock"])
    session.modified = True
    flash("Đã thêm sản phẩm vào giỏ hàng.", "success")
    return redirect(request.referrer or url_for("products"))


@app.route("/cart", methods=["GET", "POST"])
def cart():
    if request.method == "POST":
        cart_data = {}
        for key, value in request.form.items():
            if key.startswith("qty_"):
                product_id = key.replace("qty_", "")
                qty = max(int(value or 0), 0)
                if qty > 0:
                    cart_data[product_id] = qty
        session["cart"] = cart_data
        flash("Đã cập nhật giỏ hàng.", "success")
        return redirect(url_for("cart"))

    items, total = cart_items()
    return render_template("cart.html", items=items, total=total)


def cart_items():
    cart_data = session.get("cart", {})
    if not cart_data:
        return [], 0
    ids = [int(pid) for pid in cart_data.keys()]
    placeholders = ",".join("?" for _ in ids)
    products_rows = query_all(f"SELECT * FROM g6_Products WHERE g6_ProductID IN ({placeholders})", ids)
    items = []
    total = 0
    for product in products_rows:
        qty = min(cart_data.get(str(product["g6_ProductID"]), 0), product["g6_Stock"])
        subtotal = qty * product["g6_Price"]
        total += subtotal
        items.append({"product": product, "quantity": qty, "subtotal": subtotal})
    return items, total


@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    user = current_user()
    items, total = cart_items()
    if not items:
        flash("Giỏ hàng đang trống.", "warning")
        return redirect(url_for("products"))

    if request.method == "POST":
        customer_id = ensure_customer_for_user(user, request.form)
        address = request.form.get("address", "").strip()
        note = request.form.get("note", "").strip()
        db = get_db()
        cur = db.execute(
            "INSERT INTO g6_Orders (g6_CustomerID, g6_ShippingAddress, g6_Note, g6_TotalAmount) VALUES (?, ?, ?, ?)",
            (customer_id, address, note, total),
        )
        order_id = cur.lastrowid
        for item in items:
            product = item["product"]
            db.execute(
                "INSERT INTO g6_OrderItems (g6_OrderID, g6_ProductID, g6_Quantity, g6_UnitPrice) VALUES (?, ?, ?, ?)",
                (order_id, product["g6_ProductID"], item["quantity"], product["g6_Price"]),
            )
            db.execute(
                "UPDATE g6_Products SET g6_Stock = g6_Stock - ?, g6_UpdatedAt = CURRENT_TIMESTAMP WHERE g6_ProductID = ?",
                (item["quantity"], product["g6_ProductID"]),
            )
        db.execute(
            "INSERT INTO g6_AdminEvents (g6_EventType, g6_Title, g6_Details, g6_ActorName, g6_ActorEmail, g6_RelatedOrderID) VALUES (?, ?, ?, ?, ?, ?)",
            ("order", "Đơn hàng mới", f"Tổng tiền {total}", user["g6_FullName"], user["g6_Email"], order_id),
        )
        db.commit()
        session["cart"] = {}
        flash("Đặt hàng thành công. Admin sẽ xử lý đơn hàng.", "success")
        return redirect(url_for("my_orders"))

    customer = query_one("SELECT * FROM g6_Customers WHERE g6_CustomerID = ?", (user["g6_CustomerID"],)) if user["g6_CustomerID"] else None
    return render_template("checkout.html", items=items, total=total, customer=customer)


def ensure_customer_for_user(user, form):
    if user["g6_CustomerID"]:
        return user["g6_CustomerID"]
    db = get_db()
    cur = db.execute(
        "INSERT INTO g6_Customers (g6_FullName, g6_Email, g6_Phone, g6_Address) VALUES (?, ?, ?, ?)",
        (user["g6_FullName"], user["g6_Email"], form.get("phone", ""), form.get("address", "")),
    )
    db.execute("UPDATE g6_Accounts SET g6_CustomerID = ? WHERE g6_AccountID = ?", (cur.lastrowid, user["g6_AccountID"]))
    db.commit()
    return cur.lastrowid


@app.route("/orders")
@login_required
def my_orders():
    user = current_user()
    if not user["g6_CustomerID"]:
        orders = []
    else:
        orders = query_all("SELECT *, g6_TotalAmount - g6_Discount AS g6_FinalAmount FROM g6_Orders WHERE g6_CustomerID = ? ORDER BY g6_OrderID DESC", (user["g6_CustomerID"],))
    return render_template("orders.html", orders=orders)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = query_one("SELECT * FROM g6_Accounts WHERE g6_Email = ? AND g6_IsActive = 1", (email,))
        if user and check_password_hash(user["g6_Password"], password):
            session["account_id"] = user["g6_AccountID"]
            flash("Đăng nhập thành công.", "success")
            return redirect(request.args.get("next") or url_for("home"))
        flash("Email hoặc mật khẩu không đúng.", "danger")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        try:
            db = get_db()
            cur = db.execute("INSERT INTO g6_Customers (g6_FullName, g6_Email, g6_Phone, g6_Address) VALUES (?, ?, ?, ?)", (name, email, phone, address))
            db.execute(
                "INSERT INTO g6_Accounts (g6_FullName, g6_Email, g6_Password, g6_Role, g6_CustomerID) VALUES (?, ?, ?, 'user', ?)",
                (name, email, generate_password_hash(password), cur.lastrowid),
            )
            db.commit()
            flash("Đăng ký thành công. Bạn có thể đăng nhập.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email đã tồn tại.", "danger")
    return render_template("register.html")


@app.route("/request-admin", methods=["POST"])
@login_required
def request_admin():
    user = current_user()
    execute(
        "UPDATE g6_Accounts SET g6_AdminRequestStatus = 'pending', g6_RequestedRole = 'admin' WHERE g6_AccountID = ?",
        (user["g6_AccountID"],),
    )
    execute(
        "INSERT INTO g6_AdminEvents (g6_EventType, g6_Title, g6_Details, g6_ActorName, g6_ActorEmail) VALUES (?, ?, ?, ?, ?)",
        ("role_request", "Yêu cầu quyền admin", "Người dùng xin xác nhận quyền quản trị", user["g6_FullName"], user["g6_Email"]),
    )
    flash("Đã gửi yêu cầu xác nhận quyền admin.", "success")
    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.clear()
    flash("Đã đăng xuất.", "info")
    return redirect(url_for("home"))


@app.route("/admin")
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    stats = {
        "products": query_one("SELECT COUNT(*) AS n FROM g6_Products")["n"],
        "orders": query_one("SELECT COUNT(*) AS n FROM g6_Orders")["n"],
        "customers": query_one("SELECT COUNT(*) AS n FROM g6_Customers")["n"],
        "revenue": query_one("SELECT COALESCE(SUM(g6_TotalAmount - g6_Discount), 0) AS n FROM g6_Orders WHERE g6_OrderStatus != 'cancelled'")["n"],
    }
    events = query_all("SELECT * FROM g6_AdminEvents ORDER BY g6_EventID DESC LIMIT 8")
    return render_template("admin/dashboard.html", stats=stats, events=events)


@app.route("/admin/products")
@admin_required
def admin_products():
    rows = query_all(
        """
        SELECT p.*, c.g6_CategoryName, b.g6_BrandName
        FROM g6_Products p
        JOIN g6_Categories c ON c.g6_CategoryID = p.g6_CategoryID
        LEFT JOIN g6_Brands b ON b.g6_BrandID = p.g6_BrandID
        ORDER BY p.g6_ProductID DESC
        """
    )
    return render_template("admin/products.html", products=rows)


@app.route("/admin/products/new", methods=["GET", "POST"])
@admin_required
def admin_product_new():
    return product_form()


@app.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_product_edit(product_id):
    product = query_one("SELECT * FROM g6_Products WHERE g6_ProductID = ?", (product_id,))
    if not product:
        abort(404)
    return product_form(product)


def product_form(product=None):
    if request.method == "POST":
        data = (
            request.form["sku"].strip(),
            request.form["name"].strip(),
            request.form["description"].strip(),
            request.form["category_id"],
            request.form.get("brand_id") or None,
            int(request.form["price"]),
            int(request.form["stock"]),
            request.form["unit"].strip(),
            request.form.get("image_url", "").strip(),
            1 if request.form.get("is_active") else 0,
        )
        if product:
            execute(
                """
                UPDATE g6_Products
                SET g6_SKU=?, g6_ProductName=?, g6_Description=?, g6_CategoryID=?, g6_BrandID=?,
                    g6_Price=?, g6_Stock=?, g6_Unit=?, g6_ImageURL=?, g6_IsActive=?, g6_UpdatedAt=CURRENT_TIMESTAMP
                WHERE g6_ProductID=?
                """,
                (*data, product["g6_ProductID"]),
            )
            flash("Đã cập nhật sản phẩm.", "success")
        else:
            execute(
                """
                INSERT INTO g6_Products
                (g6_SKU, g6_ProductName, g6_Description, g6_CategoryID, g6_BrandID, g6_Price, g6_Stock, g6_Unit, g6_ImageURL, g6_IsActive)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                data,
            )
            flash("Đã thêm sản phẩm.", "success")
        return redirect(url_for("admin_products"))
    return render_template(
        "admin/product_form.html",
        product=product,
        categories=query_all("SELECT * FROM g6_Categories ORDER BY g6_CategoryName"),
        brands=query_all("SELECT * FROM g6_Brands ORDER BY g6_BrandName"),
    )


@app.route("/admin/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def admin_product_delete(product_id):
    execute("UPDATE g6_Products SET g6_IsActive = 0 WHERE g6_ProductID = ?", (product_id,))
    flash("Đã ẩn sản phẩm khỏi trang bán hàng.", "success")
    return redirect(url_for("admin_products"))


@app.route("/admin/orders")
@admin_required
def admin_orders():
    orders = query_all(
        """
        SELECT o.*, o.g6_TotalAmount - o.g6_Discount AS g6_FinalAmount, c.g6_FullName, c.g6_Email
        FROM g6_Orders o
        JOIN g6_Customers c ON c.g6_CustomerID = o.g6_CustomerID
        ORDER BY o.g6_OrderID DESC
        """
    )
    return render_template("admin/orders.html", orders=orders)


@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def admin_order_status(order_id):
    status = request.form.get("status")
    if status not in {"pending", "confirmed", "shipping", "delivered", "cancelled"}:
        abort(400)
    execute("UPDATE g6_Orders SET g6_OrderStatus = ?, g6_UpdatedAt = CURRENT_TIMESTAMP WHERE g6_OrderID = ?", (status, order_id))
    flash("Đã cập nhật trạng thái đơn hàng.", "success")
    return redirect(url_for("admin_orders"))


@app.route("/admin/accounts")
@admin_required
def admin_accounts():
    accounts = query_all("SELECT * FROM g6_Accounts ORDER BY g6_AccountID DESC")
    return render_template("admin/accounts.html", accounts=accounts)


@app.route("/admin/accounts/<int:account_id>/approve", methods=["POST"])
@admin_required
def approve_account(account_id):
    action = request.form.get("action")
    if action == "approve":
        execute("UPDATE g6_Accounts SET g6_Role='admin', g6_AdminRequestStatus='approved' WHERE g6_AccountID=?", (account_id,))
        flash("Đã duyệt quyền admin.", "success")
    elif action == "reject":
        execute("UPDATE g6_Accounts SET g6_AdminRequestStatus='rejected', g6_RequestedRole=NULL WHERE g6_AccountID=?", (account_id,))
        flash("Đã từ chối yêu cầu.", "info")
    return redirect(url_for("admin_accounts"))


@app.cli.command("init-db")
def init_db_command():
    init_db()
    print("Initialized EduStore database.")


if __name__ == "__main__":
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True)

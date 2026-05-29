from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from g6auth_utils import authenticate, current_user, get_current_account, login_account, logout_account, require_auth
from g6db import fetch_one, get_db_connection

auth_bp = Blueprint("auth", __name__)


def normalize_next_url(value):
    next_url = (value or "").strip()
    if next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return ""


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        next_url = normalize_next_url(request.form.get("next"))
        account = authenticate(email, password)

        if account:
            login_account(account)
            if next_url:
                return redirect(next_url)
            if account["role"] == "admin":
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("site.home"))

        flash("Email hoặc mật khẩu chưa đúng.", "error")

    return render_template(
        "g6auth/g6login.html",
        next_url=normalize_next_url(request.args.get("next")),
        current_user=current_user(),
    )


@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_account()
    return redirect(url_for("site.home"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    next_url = normalize_next_url(request.values.get("next"))
    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        email = (request.form.get("email") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        address = (request.form.get("address") or "").strip()
        password = request.form.get("password") or ""
        request_admin_role = request.form.get("request_admin_role") == "on"

        if not full_name or not email or not password:
            flash("Vui lòng nhập họ tên, email và mật khẩu.", "error")
        else:
            try:
                existing = fetch_one(
                    """
                    SELECT AccountID
                    FROM dbo.Accounts
                    WHERE Email = ?
                    """,
                    (email,),
                )
                if existing:
                    flash("Email này đã tồn tại.", "error")
                else:
                    connection = get_db_connection()
                    try:
                        cursor = connection.cursor()
                        cursor.execute(
                            """
                            INSERT INTO dbo.Customers (FullName, Email, Phone, Address)
                            OUTPUT INSERTED.CustomerID
                            VALUES (?, ?, ?, ?)
                            """,
                            (full_name, email, phone or None, address or None),
                        )
                        customer_id = cursor.fetchone()[0]

                        cursor.execute(
                            """
                            INSERT INTO dbo.Accounts (
                                FullName, Email, Password, Role, CustomerID, AdminRequestStatus, RequestedRole
                            )
                            VALUES (?, ?, ?, 'user', ?, ?, ?)
                            """,
                            (
                                full_name,
                                email,
                                password,
                                customer_id,
                                "pending" if request_admin_role else "none",
                                "admin" if request_admin_role else None,
                            ),
                        )
                        connection.commit()
                    finally:
                        connection.close()

                    if request_admin_role:
                        flash("Đăng ký thành công và đã gửi yêu cầu xin quyền quản trị viên tới admin.", "success")
                    else:
                        flash("Đăng ký thành công. Bạn có thể đăng nhập ngay.", "success")
                    if next_url:
                        return redirect(url_for("auth.login", next=next_url))
                    return redirect(url_for("auth.login"))
            except Exception:
                flash("Chưa thể tạo tài khoản. Hãy kiểm tra bảng Accounts trong database.", "error")

    return render_template("g6auth/g6register.html", current_user=current_user(), next_url=next_url)


@auth_bp.route("/api/auth/me", methods=["GET"])
@require_auth()
def auth_me():
    account = get_current_account()
    user = current_user()
    if not account or not user:
        return jsonify({"error": "Bạn cần đăng nhập để tiếp tục"}), 401

    return jsonify(
        {
            "id": account.get("AccountID") or user.get("id"),
            "name": account.get("FullName") or user.get("name"),
            "email": account.get("Email") or user.get("email"),
            "role": account.get("Role") or user.get("role"),
            "customer_id": account.get("CustomerID") or user.get("customer_id"),
            "is_active": account.get("IsActive", True),
            "admin_request_status": account.get("AdminRequestStatus") or user.get("admin_request_status"),
            "requested_role": account.get("RequestedRole"),
            "is_primary_admin": bool(account.get("IsPrimaryAdmin")) or bool(user.get("is_primary_admin")),
        }
    )


@auth_bp.route("/api/auth/logout", methods=["POST"])
@require_auth()
def api_logout():
    logout_account()
    return jsonify({"message": "Đăng xuất thành công"})

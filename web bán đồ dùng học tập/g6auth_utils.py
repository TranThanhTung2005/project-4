from functools import wraps

from flask import current_app, flash, jsonify, redirect, request, session, url_for

from g6db import fetch_one


def get_accounts():
    config = current_app.config
    return {
        "user": {
            "email": config["USER_LOGIN_EMAIL"],
            "password": config["USER_LOGIN_PASSWORD"],
            "name": config["USER_LOGIN_NAME"],
            "role": "user",
        },
        "admin": {
            "email": config["ADMIN_LOGIN_EMAIL"],
            "password": config["ADMIN_LOGIN_PASSWORD"],
            "name": config["ADMIN_LOGIN_NAME"],
            "role": "admin",
        },
    }


def get_account_from_db(email):
    try:
        return fetch_one(
            """
            SELECT AccountID, FullName, Email, Password, Role, IsActive,
                   AdminRequestStatus, RequestedRole, CustomerID, IsPrimaryAdmin
            FROM dbo.Accounts
            WHERE Email = ? AND IsActive = 1
            """,
            (email,),
        )
    except Exception:
        try:
            account = fetch_one(
                """
                SELECT AccountID, FullName, Email, Password, Role, IsActive,
                       AdminRequestStatus, RequestedRole, CustomerID
                FROM dbo.Accounts
                WHERE Email = ? AND IsActive = 1
                """,
                (email,),
            )
            if account:
                account["IsPrimaryAdmin"] = 1 if account.get("Email") == current_app.config["ADMIN_LOGIN_EMAIL"] else 0
            return account
        except Exception:
            return None


def authenticate(email, password):
    account = get_account_from_db(email)
    if account:
        if account["Password"] == password:
            return {
                "id": account["AccountID"],
                "email": account["Email"],
                "password": account["Password"],
                "name": account["FullName"],
                "role": account["Role"],
                "customer_id": account.get("CustomerID"),
                "admin_request_status": account.get("AdminRequestStatus"),
                "is_primary_admin": bool(account.get("IsPrimaryAdmin")) or account.get("Email") == current_app.config["ADMIN_LOGIN_EMAIL"],
            }
        return None

    for fallback_account in get_accounts().values():
        if fallback_account["email"] == email and fallback_account["password"] == password:
            return fallback_account
    return None


def login_account(account):
    session.permanent = True
    session["auth_user"] = {
        "id": account.get("id"),
        "email": account["email"],
        "name": account["name"],
        "role": account["role"],
        "customer_id": account.get("customer_id"),
        "admin_request_status": account.get("admin_request_status"),
        "is_primary_admin": account.get("is_primary_admin", False),
    }
    session["runtime_session_token"] = current_app.config["RUNTIME_SESSION_TOKEN"]


def logout_account():
    session.pop("auth_user", None)


def current_user():
    return session.get("auth_user")


def is_logged_in():
    return current_user() is not None


def get_current_account():
    user = current_user()
    if not user:
        return None

    account = get_account_from_db(user["email"])
    if account:
        return account

    return {
        "AccountID": user.get("id"),
        "Email": user.get("email"),
        "FullName": user.get("name"),
        "Role": user.get("role"),
        "CustomerID": user.get("customer_id"),
        "AdminRequestStatus": user.get("admin_request_status"),
        "RequestedRole": None,
        "IsPrimaryAdmin": user.get("is_primary_admin", False),
    }


def refresh_session_user():
    user = current_user()
    if not user or not user.get("email"):
        return None

    if session.get("runtime_session_token") != current_app.config["RUNTIME_SESSION_TOKEN"]:
        logout_account()
        return None

    account = get_account_from_db(user["email"])
    if not account:
        logout_account()
        return None

    refreshed_user = {
        "id": account.get("AccountID"),
        "email": account.get("Email"),
        "name": account.get("FullName"),
        "role": account.get("Role"),
        "customer_id": account.get("CustomerID"),
        "admin_request_status": account.get("AdminRequestStatus"),
        "is_primary_admin": bool(account.get("IsPrimaryAdmin")) or account.get("Email") == current_app.config["ADMIN_LOGIN_EMAIL"],
    }
    session["auth_user"] = refreshed_user
    session["runtime_session_token"] = current_app.config["RUNTIME_SESSION_TOKEN"]
    session.permanent = True
    return refreshed_user


def require_auth(role=None):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Bạn cần đăng nhập để tiếp tục"}), 401
                return redirect(url_for("auth.login", next=request.path))
            if role and user.get("role") != role:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Bạn không có quyền truy cập"}), 403
                return redirect(url_for("auth.login", next=request.path))
            return view_func(*args, **kwargs)

        return wrapper

    return decorator


def is_primary_admin(user=None):
    active_user = user or current_user()
    if not active_user:
        return False
    return active_user.get("role") == "admin" and (
        bool(active_user.get("is_primary_admin")) or active_user.get("email") == current_app.config["ADMIN_LOGIN_EMAIL"]
    )


def require_primary_admin(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Bạn cần đăng nhập để tiếp tục"}), 401
            return redirect(url_for("auth.login", next=request.path))

        if not is_primary_admin(user):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Chỉ quản trị viên chính mới được quản lý quyền quản trị"}), 403
            flash("Chỉ quản trị viên chính mới được quản lý quyền quản trị.", "error")
            return redirect(url_for("admin.accounts_page"))

        return view_func(*args, **kwargs)

    return wrapper

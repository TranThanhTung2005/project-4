from flask import Blueprint, jsonify, request

from g6auth_utils import current_user, require_auth
from g6db import fetch_all, log_admin_event

activity_bp = Blueprint("activity", __name__)


@activity_bp.route("/cart-add", methods=["POST"])
def cart_add():
    data = request.get_json(silent=True) or {}
    user = current_user()

    product_name = data.get("product_name") or "Sản phẩm"
    quantity = int(data.get("quantity", 1))
    actor_name = user["name"] if user else "Khách"
    actor_email = user["email"] if user else "guest@local"

    log_admin_event(
        event_type="cart_add",
        title=f"{actor_name} đã thêm sản phẩm vào giỏ",
        details=f"Sản phẩm: {product_name} | Số lượng: {quantity}",
        actor_name=actor_name,
        actor_email=actor_email,
    )
    return jsonify({"message": "Đã ghi nhận hoạt động"}), 201


@activity_bp.route("/recent", methods=["GET"])
@require_auth(role="admin")
def recent():
    limit = request.args.get("limit", 20, type=int)
    limit = max(min(limit, 100), 1)
    events = fetch_all(
        """
        SELECT TOP (?) EventID, EventType, Title, Details, ActorName, ActorEmail, RelatedOrderID, CreatedAt
        FROM dbo.AdminEvents
        ORDER BY CreatedAt DESC, EventID DESC
        """,
        (limit,),
    )
    return jsonify({"data": events, "total": len(events)})

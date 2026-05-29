from datetime import datetime

from flask import Blueprint, jsonify, request

from g6db import fetch_all, fetch_one, get_db_connection, row_to_dict

promotions_bp = Blueprint("promotions", __name__)

PROMOTION_SELECT = """
    SELECT
        PromotionID,
        Code,
        Description,
        DiscountType,
        DiscountValue,
        MinOrderValue,
        MaxUses,
        UsedCount,
        StartsAt,
        ExpiresAt,
        IsActive
    FROM dbo.Promotions
"""


# ── Helper ──────────────────────────────────────────────────────────────────
def parse_datetime(value):
    """Chuyển string ngày tháng thành datetime object. Trả None nếu rỗng."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    formats = [
        "%Y-%m-%dT%H:%M:%S",   # 2024-12-31T23:59:59
        "%Y-%m-%dT%H:%M",      # 2024-12-31T23:59
        "%Y-%m-%d %H:%M:%S",   # 2024-12-31 23:59:59
        "%Y-%m-%d",            # 2024-12-31
        "%d/%m/%Y %H:%M:%S",   # 31/12/2024 23:59:59
        "%d/%m/%Y",            # 31/12/2024
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"Định dạng ngày không hợp lệ: '{value}'")


# ======================
# GET ALL
# ======================
@promotions_bp.route("/", methods=["GET"])
def get_all():
    return jsonify(fetch_all(f"{PROMOTION_SELECT} ORDER BY PromotionID DESC"))


# ======================
# GET ACTIVE
# ======================
@promotions_bp.route("/active", methods=["GET"])
def get_active():
    return jsonify(
        fetch_all(
            f"""
            {PROMOTION_SELECT}
            WHERE IsActive = 1
              AND (StartsAt IS NULL OR StartsAt <= GETDATE())
              AND (ExpiresAt IS NULL OR ExpiresAt >= GETDATE())
            ORDER BY PromotionID DESC
            """
        )
    )


# ======================
# GET ONE
# ======================
@promotions_bp.route("/<int:promotion_id>", methods=["GET"])
def get_one(promotion_id):
    promotion = fetch_one(f"{PROMOTION_SELECT} WHERE PromotionID = ?", (promotion_id,))
    if not promotion:
        return jsonify({"error": "Không tìm thấy khuyến mãi"}), 404
    return jsonify(promotion)


# ======================
# APPLY CODE
# ======================
@promotions_bp.route("/apply", methods=["POST"])
def apply_code():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").upper().strip()
    order_total = float(data.get("order_total", 0))
    if not code:
        return jsonify({"error": "code là bắt buộc"}), 400

    p = fetch_one(f"{PROMOTION_SELECT} WHERE Code = ? AND IsActive = 1", (code,))
    if not p:
        return jsonify({"error": "Mã không tồn tại"}), 404

    now = datetime.utcnow()
    starts = datetime.fromisoformat(p["StartsAt"]) if p["StartsAt"] else None
    expires = datetime.fromisoformat(p["ExpiresAt"]) if p["ExpiresAt"] else None

    if starts and now < starts:
        return jsonify({"error": "Chưa đến thời gian"}), 400
    if expires and now > expires:
        return jsonify({"error": "Đã hết hạn"}), 400
    if p["MaxUses"] and p["UsedCount"] >= p["MaxUses"]:
        return jsonify({"error": "Hết lượt dùng"}), 400
    if order_total < p["MinOrderValue"]:
        return jsonify({"error": "Không đủ giá trị đơn hàng"}), 400

    if p["DiscountType"] == "percent":
        discount = order_total * p["DiscountValue"] / 100
    else:
        discount = p["DiscountValue"]

    discount = min(discount, order_total)

    return jsonify({
        "code": p["Code"],
        "discount": discount,
        "final_amount": order_total - discount,
    })


# ======================
# CREATE
# ======================
@promotions_bp.route("/", methods=["POST"])
def create():
    data = request.get_json(silent=True) or {}

    required_fields = ["Code", "DiscountType", "DiscountValue"]
    missing_fields = [f for f in required_fields if data.get(f) in (None, "")]
    if missing_fields:
        return jsonify({"error": f"Thiếu trường bắt buộc: {', '.join(missing_fields)}"}), 400
    if data["DiscountType"] not in {"percent", "fixed"}:
        return jsonify({"error": "DiscountType không hợp lệ"}), 400

    # ── Parse & validate ngày ────────────────────────────────────────────────
    try:
        starts_at = parse_datetime(data.get("StartsAt"))
        expires_at = parse_datetime(data.get("ExpiresAt"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if starts_at and expires_at and expires_at <= starts_at:
        return jsonify({"error": "ExpiresAt phải sau StartsAt"}), 400
    # ────────────────────────────────────────────────────────────────────────

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO dbo.Promotions (
                Code, Description, DiscountType, DiscountValue, MinOrderValue,
                MaxUses, UsedCount, StartsAt, ExpiresAt, IsActive
            )
            OUTPUT INSERTED.PromotionID, INSERTED.Code, INSERTED.Description, INSERTED.DiscountType,
                   INSERTED.DiscountValue, INSERTED.MinOrderValue, INSERTED.MaxUses, INSERTED.UsedCount,
                   INSERTED.StartsAt, INSERTED.ExpiresAt, INSERTED.IsActive
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
            """,
            (
                data["Code"].upper(),
                data.get("Description"),
                data["DiscountType"],
                data["DiscountValue"],
                data.get("MinOrderValue", 0),
                data.get("MaxUses"),
                starts_at,   # datetime object, không phải string
                expires_at,  # datetime object, không phải string
                data.get("IsActive", True),
            ),
        )
        created = row_to_dict(cursor, cursor.fetchone())
        connection.commit()
    finally:
        connection.close()

    return jsonify(created), 201


# ======================
# DELETE
# ======================
@promotions_bp.route("/<int:promotion_id>", methods=["DELETE"])
def delete(promotion_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM dbo.Promotions WHERE PromotionID = ?", (promotion_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Không tìm thấy khuyến mãi"}), 404
        connection.commit()
    finally:
        connection.close()

    return jsonify({"message": "Đã xoá"})


# ======================
# UPDATE
# ======================
@promotions_bp.route("/<int:promotion_id>", methods=["PATCH"])
def update(promotion_id):
    data = request.get_json(silent=True) or {}
    allowed_fields = {
        "Code": "Code",
        "Description": "Description",
        "DiscountType": "DiscountType",
        "DiscountValue": "DiscountValue",
        "MinOrderValue": "MinOrderValue",
        "MaxUses": "MaxUses",
        "IsActive": "IsActive",
    }

    updates = []
    params = []

    for payload_key, column_name in allowed_fields.items():
        if payload_key in data:
            if payload_key == "DiscountType" and data[payload_key] not in {"percent", "fixed"}:
                return jsonify({"error": "DiscountType không hợp lệ"}), 400
            updates.append(f"{column_name} = ?")
            params.append(data[payload_key])

    if "StartsAt" in data:
        try:
            starts_at = parse_datetime(data.get("StartsAt"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        updates.append("StartsAt = ?")
        params.append(starts_at)

    if "ExpiresAt" in data:
        try:
            expires_at = parse_datetime(data.get("ExpiresAt"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        updates.append("ExpiresAt = ?")
        params.append(expires_at)

    if not updates:
        return jsonify({"error": "Không có dữ liệu cần cập nhật"}), 400

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            UPDATE dbo.Promotions
            SET {", ".join(updates)}
            WHERE PromotionID = ?
            """,
            (*params, promotion_id),
        )
        if cursor.rowcount == 0:
            return jsonify({"error": "Không tìm thấy khuyến mãi"}), 404
        connection.commit()
    finally:
        connection.close()

    return get_one(promotion_id)


# ======================
# TOGGLE ACTIVE
# ======================
@promotions_bp.route("/<int:promotion_id>/toggle", methods=["PATCH"])
def toggle(promotion_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE dbo.Promotions
            SET IsActive = CASE WHEN IsActive = 1 THEN 0 ELSE 1 END
            WHERE PromotionID = ?
            """,
            (promotion_id,),
        )
        if cursor.rowcount == 0:
            return jsonify({"error": "Không tìm thấy khuyến mãi"}), 404
        connection.commit()
    finally:
        connection.close()

    return get_one(promotion_id)

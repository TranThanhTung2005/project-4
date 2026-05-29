from datetime import date, datetime
from decimal import Decimal
import re

import pyodbc

from g6config import Config


TABLE_NAMES = {
    "Accounts", "AdminEvents", "Brands", "Categories", "Customers",
    "Employees", "OrderItems", "Orders", "Products", "Promotions",
    "Reviews", "Suppliers",
}

COLUMN_NAMES = {
    "AccountID", "ActorEmail", "ActorName", "Address", "AdminRequestStatus",
    "BrandID", "BrandName", "CategoryID", "CategoryName", "Code",
    "Comment", "ContactName", "Country", "CreatedAt", "CustomerID",
    "Description", "Details", "Discount", "DiscountType", "DiscountValue",
    "Email", "EmployeeID", "EventID", "EventType", "ExpiresAt",
    "FinalAmount", "FullName", "HireDate", "ImageURL", "IsActive",
    "MaxUses", "MinOrderValue", "Note", "OrderID", "OrderItemID",
    "OrderStatus", "Password", "Phone", "Position", "Price",
    "ProductID", "ProductName", "PromotionID", "Quantity", "Rating",
    "RelatedOrderID", "RequestedRole", "ReviewID", "Role", "SKU",
    "Salary", "ShippingAddress", "Slug", "StartsAt", "Stock",
    "Subtotal", "SupplierID", "SupplierName", "Title", "TotalAmount",
    "Unit", "UnitPrice", "UpdatedAt", "UsedCount", "Website",
}

SQL_IDENTIFIER_MAP = {
    name: f"g6_{name}" for name in sorted(TABLE_NAMES | COLUMN_NAMES, key=len, reverse=True)
}


# ================== HELPER ==================

def serialize_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def normalize_result_column(column_name):
    if isinstance(column_name, str) and column_name.startswith("g6_"):
        return column_name[3:]
    return column_name


def row_to_dict(cursor, row):
    columns = [normalize_result_column(column[0]) for column in cursor.description]
    return {column: serialize_value(value) for column, value in zip(columns, row)}


def rows_to_dicts(cursor, rows):
    return [row_to_dict(cursor, row) for row in rows]


# ================== CONNECTION ==================

def build_connection_strings():
    # ✅ Luôn dùng Windows Authentication
    auth_part = f"Trusted_Connection={Config.DB_TRUSTED_CONNECTION};"

    preferred_drivers = [
        Config.DB_DRIVER,
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "SQL Server Native Client 11.0",
        "SQL Server",
    ]

    installed_drivers = set(pyodbc.drivers())
    drivers = []

    for driver in preferred_drivers:
        if driver in installed_drivers and driver not in drivers:
            drivers.append(driver)

    # Server candidates
    server_candidates = [Config.DB_SERVER]

    server_candidates.extend(
        [
            r".\SQLEXPRESS01",
            r"localhost\SQLEXPRESS01",
            r".\SQLEXPRESS",
            r"localhost\SQLEXPRESS",
            "127.0.0.1",
            "localhost",
            ".",
        ]
    )

    unique_servers = []
    for server in server_candidates:
        if server and server not in unique_servers:
            unique_servers.append(server)

    connection_strings = []

    for driver in drivers:
        # ✅ Fix SSL lỗi
        encrypt_part = "Encrypt=no;TrustServerCertificate=yes;"

        for server in unique_servers:
            connection_strings.append(
                (
                    driver,
                    server,
                    f"DRIVER={{{driver}}};"
                    f"SERVER={server};"
                    f"DATABASE={Config.DB_DATABASE};"
                    f"{auth_part}"
                    f"{encrypt_part}"
                ),
            )

    return connection_strings


# ================== SQL PREFIX ==================

def use_prefixed_identifier(match):
    identifier = match.group(0)
    if identifier.startswith("g6_"):
        return identifier
    return SQL_IDENTIFIER_MAP.get(identifier, identifier)


def prefix_sql_identifiers(query):
    if not isinstance(query, str):
        return query

    for identifier in SQL_IDENTIFIER_MAP:
        query = re.sub(rf"(?<!g6_)\b{re.escape(identifier)}\b", use_prefixed_identifier, query)
    return query


# ================== WRAPPER ==================

class PrefixedCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, *params):
        return self._cursor.execute(prefix_sql_identifiers(query), *params)

    def executemany(self, query, params):
        return self._cursor.executemany(prefix_sql_identifiers(query), params)

    def __getattr__(self, name):
        return getattr(self._cursor, name)

    def __iter__(self):
        return iter(self._cursor)


class PrefixedConnection:
    def __init__(self, connection):
        self._connection = connection

    def cursor(self):
        return PrefixedCursor(self._connection.cursor())

    def __getattr__(self, name):
        return getattr(self._connection, name)


# ================== MAIN DB ==================

def get_db_connection():
    last_error = None

    for _, _, connection_string in build_connection_strings():
        try:
            return PrefixedConnection(pyodbc.connect(connection_string, timeout=5))
        except pyodbc.Error as exc:
            last_error = exc
            continue

    if last_error:
        raise last_error

    return PrefixedConnection(pyodbc.connect(Config.CONN_STR, timeout=5))


def fetch_all(query, params=()):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return rows_to_dicts(cursor, rows)
    finally:
        connection.close()


def fetch_one(query, params=()):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        if not row:
            return None
        return row_to_dict(cursor, row)
    finally:
        connection.close()


def log_admin_event(event_type, title, details=None, actor_name=None, actor_email=None, related_order_id=None):
    try:
        connection = get_db_connection()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO dbo.AdminEvents (
                    EventType, Title, Details, ActorName, ActorEmail, RelatedOrderID
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event_type, title, details, actor_name, actor_email, related_order_id),
            )
            connection.commit()
        finally:
            connection.close()
    except Exception:
        return None

    return True

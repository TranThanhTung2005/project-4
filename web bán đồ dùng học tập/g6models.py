"""
Metadata tham chiếu cho schema SQL Server.

Project này đã được chuẩn hoá theo hướng pyodbc nên không còn dùng ORM model.
File được giữ lại để mô tả nhanh tên bảng/chính sách cột nếu cần tái sử dụng.
"""

TABLES = {
    "categories": "dbo.g6_Categories",
    "brands": "dbo.g6_Brands",
    "products": "dbo.g6_Products",
    "customers": "dbo.g6_Customers",
    "orders": "dbo.g6_Orders",
    "order_items": "dbo.g6_OrderItems",
    "reviews": "dbo.g6_Reviews",
    "promotions": "dbo.g6_Promotions",
}

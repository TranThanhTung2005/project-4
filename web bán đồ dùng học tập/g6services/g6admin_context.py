from datetime import date

from g6auth_utils import is_primary_admin
from g6db import fetch_all, fetch_one


def previous_month(year, month):
    if month == 1:
        return year - 1, 12
    return year, month - 1


def build_virtual_revenue(monthly_revenue, months=5):
    if monthly_revenue:
        oldest = monthly_revenue[-1]
        anchor_year = int(oldest["RevenueYear"])
        anchor_month = int(oldest["RevenueMonth"])
        base_revenue = max(float(oldest.get("Revenue", 0)), 1200000)
    else:
        today = date.today()
        anchor_year = today.year
        anchor_month = today.month
        base_revenue = 1200000

    factors = [0.86, 0.8, 0.74, 0.68, 0.62]
    virtual_rows = []

    year = anchor_year
    month = anchor_month
    for index in range(months):
        year, month = previous_month(year, month)
        revenue = int(max(350000, round(base_revenue * factors[index % len(factors)])))
        order_count = max(1, int(revenue // 420000))
        virtual_rows.append(
            {
                "RevenueYear": year,
                "RevenueMonth": month,
                "Revenue": revenue,
                "OrderCount": order_count,
                "IsVirtual": True,
            }
        )

    return virtual_rows


def get_product_column_names():
    rows = fetch_all(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'Products'
        """
    )
    return {
        row["COLUMN_NAME"][3:] if row["COLUMN_NAME"].startswith("g6_") else row["COLUMN_NAME"]
        for row in rows
    }


def get_admin_context():
    metrics = {
        "products": fetch_one("SELECT COUNT(*) AS Total FROM dbo.Products") or {"Total": 0},
        "orders": fetch_one("SELECT COUNT(*) AS Total FROM dbo.Orders") or {"Total": 0},
        "customers": fetch_one("SELECT COUNT(*) AS Total FROM dbo.Customers") or {"Total": 0},
        "reviews": fetch_one("SELECT COUNT(*) AS Total FROM dbo.Reviews") or {"Total": 0},
        "accounts": fetch_one("SELECT COUNT(*) AS Total FROM dbo.Accounts") or {"Total": 0},
        "employees": fetch_one("SELECT COUNT(*) AS Total FROM dbo.Employees") or {"Total": 0},
        "suppliers": fetch_one("SELECT COUNT(*) AS Total FROM dbo.Suppliers") or {"Total": 0},
        "revenue": fetch_one(
            """
            SELECT
                ISNULL(SUM(CASE WHEN OrderStatus <> 'cancelled' THEN FinalAmount ELSE 0 END), 0) AS TotalRevenue,
                ISNULL(SUM(CASE WHEN OrderStatus = 'delivered' THEN FinalAmount ELSE 0 END), 0) AS DeliveredRevenue,
                ISNULL(SUM(CASE WHEN OrderStatus IN ('pending', 'confirmed', 'shipping') THEN FinalAmount ELSE 0 END), 0) AS ProcessingRevenue
            FROM dbo.Orders
            """
        ) or {"TotalRevenue": 0, "DeliveredRevenue": 0, "ProcessingRevenue": 0},
    }

    products = fetch_all(
        """
        SELECT TOP 12 p.ProductID, p.ProductName, p.SKU, p.Price, p.Stock, p.IsActive,
               c.CategoryName, b.BrandName
        FROM dbo.Products p
        INNER JOIN dbo.Categories c ON c.CategoryID = p.CategoryID
        LEFT JOIN dbo.Brands b ON b.BrandID = p.BrandID
        ORDER BY p.ProductID DESC
        """
    )
    orders = fetch_all(
        """
        SELECT TOP 10 o.OrderID, c.FullName AS CustomerName, o.TotalAmount, o.OrderStatus, o.CreatedAt
        FROM dbo.Orders o
        INNER JOIN dbo.Customers c ON c.CustomerID = o.CustomerID
        ORDER BY o.CreatedAt DESC
        """
    )
    customers = fetch_all(
        """
        SELECT TOP 10 CustomerID, FullName, Email, Phone, Address, CreatedAt
        FROM dbo.Customers
        ORDER BY CustomerID DESC
        """
    )
    reviews = fetch_all(
        """
        SELECT TOP 10 r.ReviewID, p.ProductName, c.FullName AS CustomerName, r.Rating, r.Comment, r.CreatedAt
        FROM dbo.Reviews r
        INNER JOIN dbo.Products p ON p.ProductID = r.ProductID
        INNER JOIN dbo.Customers c ON c.CustomerID = r.CustomerID
        ORDER BY r.CreatedAt DESC
        """
    )
    categories = fetch_all(
        """
        SELECT CategoryID, CategoryName, Slug, Description
        FROM dbo.Categories
        ORDER BY CategoryID DESC
        """
    )
    brands = fetch_all(
        """
        SELECT BrandID, BrandName, Country, Website
        FROM dbo.Brands
        ORDER BY BrandID DESC
        """
    )
    employees = fetch_all(
        """
        SELECT EmployeeID, FullName, Email, Phone, Position, HireDate, Salary, IsActive, CreatedAt
        FROM dbo.Employees
        ORDER BY EmployeeID DESC
        """
    )
    suppliers = fetch_all(
        """
        SELECT SupplierID, SupplierName, ContactName, Email, Phone, Address, CreatedAt
        FROM dbo.Suppliers
        ORDER BY SupplierID DESC
        """
    )
    promotions = fetch_all(
        """
        SELECT PromotionID, Code, DiscountType, DiscountValue, MinOrderValue, IsActive
        FROM dbo.Promotions
        ORDER BY PromotionID DESC
        """
    )
    accounts = fetch_all(
        """
        SELECT AccountID, FullName, Email, Role, IsActive,
               ISNULL(AdminRequestStatus, 'none') AS AdminRequestStatus,
               RequestedRole,
               CASE WHEN Email = 'admin@edustore.local' THEN CAST(1 AS bit) ELSE CAST(0 AS bit) END AS IsPrimaryAdmin
        FROM dbo.Accounts
        ORDER BY AccountID DESC
        """
    )
    activities = fetch_all(
        """
        SELECT TOP 20 EventID, EventType, Title, Details, ActorName, ActorEmail, RelatedOrderID, CreatedAt
        FROM dbo.AdminEvents
        ORDER BY CreatedAt DESC, EventID DESC
        """
    )
    admin_requests = fetch_all(
        """
        SELECT AccountID, FullName, Email, Role,
               ISNULL(AdminRequestStatus, 'none') AS AdminRequestStatus,
               RequestedRole,
               CASE WHEN Email = 'admin@edustore.local' THEN CAST(1 AS bit) ELSE CAST(0 AS bit) END AS IsPrimaryAdmin
        FROM dbo.Accounts
        WHERE RequestedRole = 'admin' AND ISNULL(AdminRequestStatus, 'none') = 'pending'
        ORDER BY AccountID DESC
        """
    )
    revenue_summary = fetch_one(
        """
        SELECT
            ISNULL(SUM(CASE WHEN OrderStatus <> 'cancelled' THEN FinalAmount ELSE 0 END), 0) AS TotalRevenue,
            ISNULL(SUM(CASE WHEN OrderStatus = 'delivered' THEN FinalAmount ELSE 0 END), 0) AS DeliveredRevenue,
            ISNULL(SUM(CASE WHEN OrderStatus IN ('pending', 'confirmed', 'shipping') THEN FinalAmount ELSE 0 END), 0) AS PipelineRevenue,
            COUNT(CASE WHEN OrderStatus <> 'cancelled' THEN 1 END) AS RevenueOrders
        FROM dbo.Orders
        """
    ) or {"TotalRevenue": 0, "DeliveredRevenue": 0, "PipelineRevenue": 0, "RevenueOrders": 0}
    monthly_revenue = fetch_all(
        """
        SELECT TOP 18
            YEAR(CreatedAt) AS RevenueYear,
            MONTH(CreatedAt) AS RevenueMonth,
            ISNULL(SUM(CASE WHEN OrderStatus <> 'cancelled' THEN FinalAmount ELSE 0 END), 0) AS Revenue,
            COUNT(CASE WHEN OrderStatus <> 'cancelled' THEN 1 END) AS OrderCount
        FROM dbo.Orders
        GROUP BY YEAR(CreatedAt), MONTH(CreatedAt)
        ORDER BY RevenueYear DESC, RevenueMonth DESC
        """
    )
    revenue_by_status = fetch_all(
        """
        SELECT
            OrderStatus,
            COUNT(*) AS OrderCount,
            ISNULL(SUM(FinalAmount), 0) AS Revenue
        FROM dbo.Orders
        GROUP BY OrderStatus
        ORDER BY OrderCount DESC, OrderStatus
        """
    )
    virtual_revenue = build_virtual_revenue(monthly_revenue, months=5)
    virtual_total_revenue = sum(item["Revenue"] for item in virtual_revenue)
    virtual_total_orders = sum(item["OrderCount"] for item in virtual_revenue)

    monthly_revenue = monthly_revenue + virtual_revenue
    revenue_summary["TotalRevenue"] += virtual_total_revenue
    revenue_summary["DeliveredRevenue"] += virtual_total_revenue
    revenue_summary["RevenueOrders"] += virtual_total_orders
    metrics["revenue"]["TotalRevenue"] += virtual_total_revenue
    metrics["revenue"]["DeliveredRevenue"] += virtual_total_revenue

    delivered_row = next((item for item in revenue_by_status if item["OrderStatus"] == "delivered"), None)
    if delivered_row:
        delivered_row["Revenue"] += virtual_total_revenue
        delivered_row["OrderCount"] += virtual_total_orders
    else:
        revenue_by_status.append(
            {
                "OrderStatus": "delivered",
                "OrderCount": virtual_total_orders,
                "Revenue": virtual_total_revenue,
            }
        )

    revenue_chart_max = max([item.get("Revenue", 0) for item in monthly_revenue], default=0)

    return {
        "metrics": metrics,
        "products": products,
        "orders": orders,
        "customers": customers,
        "reviews": reviews,
        "categories": categories,
        "brands": brands,
        "employees": employees,
        "suppliers": suppliers,
        "promotions": promotions,
        "accounts": accounts,
        "activities": activities,
        "admin_requests": admin_requests,
        "can_manage_admin_roles": is_primary_admin(),
        "revenue_summary": revenue_summary,
        "monthly_revenue": monthly_revenue,
        "revenue_by_status": revenue_by_status,
        "revenue_chart_max": revenue_chart_max,
    }

# EduStore API - Flask + pyodbc + SQL Server

EduStore là ứng dụng dịch vụ web bán đồ dùng học tập, có 2 phần chính:

- giao diện người dùng để xem sản phẩm, giỏ hàng, thanh toán, đánh giá
- giao diện quản trị để quản lý sản phẩm, đơn hàng, tài khoản, khuyến mãi, doanh thu

Back-end dùng Flask + `pyodbc`, kết nối trực tiếp SQL Server theo schema `dbo.*`.

## Cài đặt

```bash
pip install -r g6requirements.txt
```

Đảm bảo máy đã cài `ODBC Driver 18 for SQL Server` hoặc driver tương thích.

## Cấu hình kết nối DB

Project hiện kết nối theo kiểu quen thuộc khi bạn làm việc với SQL Server trong SSMS:

```
DB_DRIVER   = ODBC Driver 18 for SQL Server
DB_SERVER   = localhost\SQLEXPRESS
DB_DATABASE = EduStore
DB_USERNAME = sa
DB_PASSWORD = YourPassword123
DB_TRUSTED_CONNECTION = yes
```

Nếu bạn đăng nhập Windows giống cách mở DB trong SSMS, có thể bỏ `DB_USERNAME` và `DB_PASSWORD`, khi đó app sẽ dùng:

```text
Trusted_Connection=yes
```

Nếu bạn dùng SQL Server Authentication trong SSMS thì chỉ cần điền:

```text
DB_USERNAME
DB_PASSWORD
```

## Chạy server

```bash
python g6g6app.py
# → http://localhost:3000
```

Health check:

```bash
GET /api/health
```

---

## Tổng quan Endpoints

| Module        | Base URL              |
|---------------|-----------------------|
| Danh mục      | `/api/categories`     |
| Thương hiệu   | `/api/brands`         |
| Sản phẩm      | `/api/products`       |
| Khách hàng    | `/api/customers`      |
| Đơn hàng      | `/api/orders`         |
| Đánh giá      | `/api/reviews`        |
| Khuyến mãi    | `/api/promotions`     |
| Hoạt động     | `/api/activity`       |
| Xác thực      | `/api/auth`           |
| Admin API     | `/api/admin`          |

---

## Chi tiết API

### 📦 Sản phẩm `/api/products`

| Method | URL                        | Mô tả                        |
|--------|----------------------------|------------------------------|
| GET    | `/`                        | Danh sách (có filter + phân trang) |
| GET    | `/<id>`                    | Chi tiết sản phẩm            |
| GET    | `/sku/<sku>`               | Tìm theo SKU                 |
| GET    | `/recent`                  | Sản phẩm mới nhất            |
| GET    | `/best-sellers`            | Sản phẩm bán chạy            |
| GET    | `/low-stock`               | Sản phẩm sắp hết hàng        |
| GET    | `/suggestions`             | Gợi ý tìm kiếm               |
| POST   | `/`                        | Thêm sản phẩm mới            |
| PUT    | `/<id>`                    | Cập nhật sản phẩm            |
| DELETE | `/<id>`                    | Xoá sản phẩm                 |
| PATCH  | `/<id>/stock`              | Cập nhật tồn kho `{"delta": 10}` |

**Query params GET /:**
- `search` – tìm tên sản phẩm
- `category_id`, `brand_id`
- `min_price`, `max_price`
- `is_active=true/false`
- `page`, `limit`

### 🛒 Đơn hàng `/api/orders`

| Method | URL                 | Mô tả |
|--------|---------------------|------|
| GET    | `/`                 | Danh sách đơn hàng |
| GET    | `/<id>`             | Chi tiết đơn hàng |
| GET    | `/mine`             | Đơn hàng của người đang đăng nhập |
| GET    | `/stats`            | Thống kê nhanh đơn hàng |
| GET    | `/revenue-overview` | Tóm tắt doanh thu + doanh thu theo tháng |
| POST   | `/`                 | Tạo đơn hàng |
| PATCH  | `/<id>/status`      | Cập nhật trạng thái |
| DELETE | `/<id>`             | Xoá đơn hàng |

**Tạo đơn hàng POST /:**
```json
{
  "CustomerID": 1,
  "ShippingAddress": "12 Lê Lợi, Hà Nội",
  "Discount": 0,
  "Items": [
    {"ProductID": 1, "Quantity": 5},
    {"ProductID": 14, "Quantity": 1}
  ]
}
```
→ Tự tính `TotalAmount`, trừ tồn kho.

**Cập nhật trạng thái PATCH `/<id>/status`:**
```json
{"OrderStatus": "confirmed"}
```
Các trạng thái hợp lệ: `pending` → `confirmed` → `shipping` → `delivered` / `cancelled`

### 🎟️ Khuyến mãi `/api/promotions`

| Method | URL                    | Mô tả |
|--------|------------------------|------|
| GET    | `/`                    | Danh sách khuyến mãi |
| GET    | `/active`              | Khuyến mãi đang hoạt động |
| GET    | `/<id>`                | Chi tiết khuyến mãi |
| POST   | `/`                    | Tạo khuyến mãi |
| POST   | `/apply`               | Áp mã khuyến mãi |
| PATCH  | `/<id>`                | Cập nhật khuyến mãi |
| PATCH  | `/<id>/toggle`         | Bật/tắt khuyến mãi |
| DELETE | `/<id>`                | Xoá khuyến mãi |

**Áp dụng mã POST `/apply`:**
```json
{"code": "BACK2SCHOOL", "order_total": 300000}
```
→ Trả về số tiền được giảm và tổng cuối.

### 👤 Khách hàng `/api/customers`

| Method | URL      | Mô tả |
|--------|----------|------|
| GET    | `/`      | Danh sách khách hàng |
| GET    | `/me`    | Hồ sơ khách hàng hiện tại |
| GET    | `/<id>`  | Chi tiết khách hàng |
| POST   | `/`      | Tạo khách hàng |
| PUT    | `/<id>`  | Cập nhật khách hàng |
| DELETE | `/<id>`  | Xoá khách hàng |

### 🗂️ Danh mục `/api/categories`

| Method | URL             | Mô tả |
|--------|-----------------|------|
| GET    | `/`             | Danh sách danh mục |
| GET    | `/with-counts`  | Danh sách kèm số lượng sản phẩm |
| GET    | `/<id>`         | Chi tiết danh mục |
| POST   | `/`             | Tạo danh mục |
| PUT    | `/<id>`         | Cập nhật danh mục |
| DELETE | `/<id>`         | Xoá danh mục |

### 🏷️ Thương hiệu `/api/brands`

| Method | URL             | Mô tả |
|--------|-----------------|------|
| GET    | `/`             | Danh sách thương hiệu |
| GET    | `/with-counts`  | Danh sách kèm số lượng sản phẩm |
| GET    | `/<id>`         | Chi tiết thương hiệu |
| POST   | `/`             | Tạo thương hiệu |
| PUT    | `/<id>`         | Cập nhật thương hiệu |
| DELETE | `/<id>`         | Xoá thương hiệu |

### ⭐ Đánh giá `/api/reviews`

| Method | URL      | Mô tả |
|--------|----------|------|
| GET    | `/`      | Danh sách đánh giá |
| GET    | `/mine`  | Đánh giá của người đang đăng nhập |
| GET    | `/<id>`  | Chi tiết đánh giá |
| POST   | `/`      | Tạo đánh giá |
| PUT    | `/<id>`  | Cập nhật đánh giá |
| DELETE | `/<id>`  | Xoá đánh giá |

### 🧾 Hoạt động `/api/activity`

| Method | URL        | Mô tả |
|--------|------------|------|
| POST   | `/cart-add`| Ghi log thêm vào giỏ |
| GET    | `/recent`  | Lấy hoạt động gần đây cho admin |

### 🔐 Xác thực `/api/auth`

| Method | URL        | Mô tả |
|--------|------------|------|
| GET    | `/me`      | Lấy thông tin người đăng nhập hiện tại |
| POST   | `/logout`  | Đăng xuất qua API |

### 🛠️ Admin API `/api/admin`

| Method | URL                              | Mô tả |
|--------|----------------------------------|------|
| GET    | `/dashboard`                     | Dữ liệu tổng quan quản trị |
| GET    | `/accounts/pending-admin`        | Danh sách yêu cầu lên admin |
| GET    | `/top-customers`                | Top khách hàng chi tiêu cao |
| PATCH  | `/products/<id>/toggle-active`  | Bật/tắt trạng thái sản phẩm |

---

## Chức năng nghiệp vụ hiện có

Project hiện đã có đủ nền để phát triển theo yêu cầu môn:

- Web application dùng Flask + HTML/CSS/JS
- SQL Server với trên 5 bảng dữ liệu
- Hệ user: xem sản phẩm, lọc, tìm kiếm, giỏ hàng, thanh toán, đánh giá, đăng ký/đăng nhập
- Hệ admin: dashboard, quản lý sản phẩm, đơn hàng, tài khoản, khuyến mãi, danh mục, thương hiệu, người dùng, hoạt động
- API phục vụ cả frontend user và admin

Nếu tính theo nhóm chức năng + endpoint + màn quản trị, dự án đã vượt mức tối thiểu để phát triển lên mốc `60+ chức năng`.

## Gợi ý chia việc nhóm 4 người

### 2 thành viên làm API

- Thành viên 1: sản phẩm, danh mục, thương hiệu, tìm kiếm, tồn kho
- Thành viên 2: tài khoản, khách hàng, đơn hàng, khuyến mãi, đánh giá, activity

### 2 thành viên làm giao diện dùng API

- Thành viên 3: giao diện người dùng, chi tiết sản phẩm, giỏ hàng, thanh toán
- Thành viên 4: giao diện admin, dashboard, quản lý dữ liệu, biểu đồ doanh thu

---

## Cấu trúc chính

```
edustore/
├── g6app.py            # Entry point
├── g6config.py         # Cấu hình DB
├── g6db.py             # Helper kết nối + serialize pyodbc
├── g6models.py         # Metadata schema tham chiếu
├── g6requirements.txt
└── g6routes/
    ├── categories.py
    ├── brands.py
    ├── products.py
    ├── customers.py
    ├── orders.py
    ├── reviews.py
    └── promotions.py
```

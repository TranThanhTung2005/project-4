# EduStore Flask

Ứng dụng Flask được dựng theo CSDL `CSDL-G6.sql` cho đề tài website bán đồ dùng học tập.

## Chức năng chính

- Trang người dùng: xem danh mục, danh sách sản phẩm, chi tiết sản phẩm.
- Lọc, tìm kiếm, phân trang sản phẩm.
- Đăng ký, đăng nhập, đăng xuất.
- Giỏ hàng, cập nhật số lượng, đặt hàng.
- Người dùng gửi yêu cầu xin quyền admin.
- Trang admin: dashboard, sự kiện, CRUD sản phẩm, quản lý đơn hàng, duyệt quyền admin.

## Chạy ứng dụng

```powershell
py -m flask --app app init-db
py -m flask --app app run --debug
```

Mở trình duyệt tại `http://127.0.0.1:5000`.

## Tài khoản mẫu

- Admin: `admin@edustore.local` / `admin123`
- User: `user@edustore.local` / `user123`

## Ghi chú kỹ thuật

- File SQL gốc dùng SQL Server. Bản Flask này dùng SQLite `edustore.db` để dễ chạy cục bộ trong đồ án.
- Tên bảng và tên cột vẫn giữ dạng `g6_...` để bám sát CSDL đã gửi.
- Khi cần tạo lại dữ liệu mẫu, chạy lại `py -m flask --app app init-db`.

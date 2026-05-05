CREATE DATABASE EduStore COLLATE Vietnamese_CI_AS;
    PRINT '✅ Đã tạo database EduStore';

GO
 
USE EduStore;
GO
 
-- ============================================================
--  1. DANH MỤC SẢN PHẨM
-- ============================================================
CREATE TABLE dbo.g6_Categories (
    g6_CategoryID   INT           NOT NULL IDENTITY(1,1),
    g6_CategoryName NVARCHAR(100) NOT NULL,
    g6_Slug         VARCHAR(100)  NOT NULL,
    g6_Description  NVARCHAR(500) NULL,
    g6_CreatedAt    DATETIME2(0)  NOT NULL DEFAULT GETDATE(),
 
    CONSTRAINT PK_Categories      PRIMARY KEY (g6_CategoryID),
    CONSTRAINT UQ_Categories_Name UNIQUE (g6_CategoryName),
    CONSTRAINT UQ_Categories_Slug UNIQUE (g6_Slug)
);
GO
 
-- ============================================================
--  2. THƯƠNG HIỆU
-- ============================================================
CREATE TABLE dbo.g6_Brands (
    g6_BrandID   INT           NOT NULL IDENTITY(1,1),
    g6_BrandName NVARCHAR(100) NOT NULL,
    g6_Country   NVARCHAR(50)  NULL,
    g6_Website   VARCHAR(200)  NULL,
    g6_CreatedAt DATETIME2(0)  NOT NULL DEFAULT GETDATE(),
 
    CONSTRAINT PK_Brands      PRIMARY KEY (g6_BrandID),
    CONSTRAINT UQ_Brands_Name UNIQUE (g6_BrandName)
);
GO
 
-- ============================================================
--  3. NHÂN VIÊN
-- ============================================================
CREATE TABLE dbo.g6_Employees (
    g6_EmployeeID  INT           NOT NULL IDENTITY(1,1),
    g6_FullName    NVARCHAR(150) NOT NULL,
    g6_Email       VARCHAR(150)  NOT NULL,
    g6_Phone       VARCHAR(20)   NULL,
    g6_Position    NVARCHAR(100) NOT NULL,
    g6_HireDate    DATE          NOT NULL,
    g6_Salary      DECIMAL(15,0) NOT NULL DEFAULT 0,
    g6_IsActive    BIT           NOT NULL DEFAULT 1,
    g6_CreatedAt   DATETIME2(0)  NOT NULL DEFAULT GETDATE(),

    CONSTRAINT PK_Employees        PRIMARY KEY (g6_EmployeeID),
    CONSTRAINT UQ_Employees_Email  UNIQUE (g6_Email),
    CONSTRAINT CK_Employees_Salary CHECK (g6_Salary >= 0)
);
GO
 
-- ============================================================
--  4. NHÀ CUNG CẤP
-- ============================================================
CREATE TABLE dbo.g6_Suppliers (
    g6_SupplierID    INT           NOT NULL IDENTITY(1,1),
    g6_SupplierName  NVARCHAR(150) NOT NULL,
    g6_ContactName   NVARCHAR(150) NULL,
    g6_Email         VARCHAR(150)  NULL,
    g6_Phone         VARCHAR(20)   NULL,
    g6_Address       NVARCHAR(300) NULL,
    g6_CreatedAt     DATETIME2(0)  NOT NULL DEFAULT GETDATE(),

    CONSTRAINT PK_Suppliers       PRIMARY KEY (g6_SupplierID),
    CONSTRAINT UQ_Suppliers_Name  UNIQUE (g6_SupplierName)
);
GO
 
-- ============================================================
--  5. SẢN PHẨM
-- ============================================================
CREATE TABLE dbo.g6_Products (
    g6_ProductID   INT            NOT NULL IDENTITY(1,1),
    g6_SKU         VARCHAR(50)    NOT NULL,
    g6_ProductName NVARCHAR(200)  NOT NULL,
    g6_Description NVARCHAR(MAX)  NULL,
    g6_CategoryID  INT            NOT NULL,
    g6_BrandID     INT            NULL,
    g6_Price       DECIMAL(15,0)  NOT NULL,
    g6_Stock       INT            NOT NULL DEFAULT 0,
    g6_Unit        NVARCHAR(20)   NOT NULL DEFAULT N'Cái',
    g6_ImageURL    VARCHAR(500)   NULL,
    g6_IsActive    BIT            NOT NULL DEFAULT 1,
    g6_CreatedAt   DATETIME2(0)   NOT NULL DEFAULT GETDATE(),
    g6_UpdatedAt   DATETIME2(0)   NOT NULL DEFAULT GETDATE(),
 
    CONSTRAINT PK_Products          PRIMARY KEY (g6_ProductID),
    CONSTRAINT UQ_Products_SKU      UNIQUE (g6_SKU),
    CONSTRAINT FK_Products_Category FOREIGN KEY (g6_CategoryID) REFERENCES dbo.g6_Categories(g6_CategoryID),
    CONSTRAINT FK_Products_Brand    FOREIGN KEY (g6_BrandID)    REFERENCES dbo.g6_Brands(g6_BrandID),
    CONSTRAINT CK_Products_Price    CHECK (g6_Price >= 0),
    CONSTRAINT CK_Products_Stock    CHECK (g6_Stock >= 0)
);
 
CREATE INDEX IX_Products_Category ON dbo.g6_Products (g6_CategoryID);
CREATE INDEX IX_Products_Brand    ON dbo.g6_Products (g6_BrandID);
GO
 
-- ============================================================
--  4. KHÁCH HÀNG
-- ============================================================
CREATE TABLE dbo.g6_Customers (
    g6_CustomerID INT           NOT NULL IDENTITY(1,1),
    g6_FullName   NVARCHAR(150) NOT NULL,
    g6_Email      VARCHAR(150)  NOT NULL,
    g6_Phone      VARCHAR(20)   NULL,
    g6_Address    NVARCHAR(300) NULL,
    g6_CreatedAt  DATETIME2(0)  NOT NULL DEFAULT GETDATE(),
 
    CONSTRAINT PK_Customers       PRIMARY KEY (g6_CustomerID),
    CONSTRAINT UQ_Customers_Email UNIQUE (g6_Email)
);
GO



-- ============================================================
--  4.1. TÀI KHOẢN ĐĂNG NHẬP
-- ============================================================
CREATE TABLE dbo.g6_Accounts (
    g6_AccountID   INT           NOT NULL IDENTITY(1,1),
    g6_FullName    NVARCHAR(150) NOT NULL,
    g6_Email       VARCHAR(150)  NOT NULL,
    g6_Password    VARCHAR(255)  NOT NULL,
    g6_Role        VARCHAR(20)   NOT NULL,
    g6_CustomerID  INT           NULL,
    g6_IsActive    BIT           NOT NULL DEFAULT 1,
    g6_AdminRequestStatus VARCHAR(20) NOT NULL DEFAULT 'none',
    g6_RequestedRole VARCHAR(20) NULL,
    g6_CreatedAt   DATETIME2(0)  NOT NULL DEFAULT GETDATE(),

    CONSTRAINT PK_Accounts          PRIMARY KEY (g6_AccountID),
    CONSTRAINT UQ_Accounts_Email    UNIQUE (g6_Email),
    CONSTRAINT FK_Accounts_Customer FOREIGN KEY (g6_CustomerID) REFERENCES dbo.g6_Customers(g6_CustomerID),
    CONSTRAINT CK_Accounts_Role     CHECK (g6_Role IN ('admin', 'user')),
    CONSTRAINT CK_Accounts_RequestStatus CHECK (g6_AdminRequestStatus IN ('none', 'pending', 'approved', 'rejected'))
);
GO

-- ============================================================
--  4.2. NHẬT KÝ HOẠT ĐỘNG GỬI VỀ ADMIN
-- ============================================================
CREATE TABLE dbo.g6_AdminEvents (
    g6_EventID         INT            NOT NULL IDENTITY(1,1),
    g6_EventType       VARCHAR(50)    NOT NULL,
    g6_Title           NVARCHAR(200)  NOT NULL,
    g6_Details         NVARCHAR(1000) NULL,
    g6_ActorName       NVARCHAR(150)  NULL,
    g6_ActorEmail      VARCHAR(150)   NULL,
    g6_RelatedOrderID  INT            NULL,
    g6_CreatedAt       DATETIME2(0)   NOT NULL DEFAULT GETDATE(),

    CONSTRAINT PK_AdminEvents PRIMARY KEY (g6_EventID)
);
GO
 
-- ============================================================
--  5. ĐƠN HÀNG
-- ============================================================
CREATE TABLE dbo.g6_Orders (
    g6_OrderID         INT           NOT NULL IDENTITY(1,1),
    g6_CustomerID      INT           NOT NULL,
    g6_OrderStatus     VARCHAR(20)   NOT NULL DEFAULT 'pending',
    g6_ShippingAddress NVARCHAR(300) NULL,
    g6_Note            NVARCHAR(500) NULL,
    g6_TotalAmount     DECIMAL(15,0) NOT NULL DEFAULT 0,
    g6_Discount        DECIMAL(15,0) NOT NULL DEFAULT 0,
    g6_FinalAmount     AS (g6_TotalAmount - g6_Discount) PERSISTED,
    g6_CreatedAt       DATETIME2(0)  NOT NULL DEFAULT GETDATE(),
    g6_UpdatedAt       DATETIME2(0)  NOT NULL DEFAULT GETDATE(),
 
    CONSTRAINT PK_Orders          PRIMARY KEY (g6_OrderID),
    CONSTRAINT FK_Orders_Customer FOREIGN KEY (g6_CustomerID) REFERENCES dbo.g6_Customers(g6_CustomerID),
    CONSTRAINT CK_Orders_Status   CHECK (g6_OrderStatus IN ('pending','confirmed','shipping','delivered','cancelled')),
    CONSTRAINT CK_Orders_Amount   CHECK (g6_TotalAmount >= 0),
    CONSTRAINT CK_Orders_Discount CHECK (g6_Discount >= 0)
);
 
CREATE INDEX IX_Orders_Customer ON dbo.g6_Orders (g6_CustomerID);
CREATE INDEX IX_Orders_Status   ON dbo.g6_Orders (g6_OrderStatus);
GO
 
-- ============================================================
--  6. CHI TIẾT ĐƠN HÀNG
-- ============================================================
CREATE TABLE dbo.g6_OrderItems (
    g6_OrderItemID INT           NOT NULL IDENTITY(1,1),
    g6_OrderID     INT           NOT NULL,
    g6_ProductID   INT           NOT NULL,
    g6_Quantity    INT           NOT NULL,
    g6_UnitPrice   DECIMAL(15,0) NOT NULL,
    g6_Subtotal    AS (g6_Quantity * g6_UnitPrice) PERSISTED,
 
    CONSTRAINT PK_OrderItems         PRIMARY KEY (g6_OrderItemID),
    CONSTRAINT FK_OrderItems_Order   FOREIGN KEY (g6_OrderID)   REFERENCES dbo.g6_Orders(g6_OrderID)   ON DELETE CASCADE,
    CONSTRAINT FK_OrderItems_Product FOREIGN KEY (g6_ProductID) REFERENCES dbo.g6_Products(g6_ProductID),
    CONSTRAINT CK_OrderItems_Qty     CHECK (g6_Quantity > 0),
    CONSTRAINT CK_OrderItems_Price   CHECK (g6_UnitPrice >= 0)
);
 
CREATE INDEX IX_OrderItems_Order   ON dbo.g6_OrderItems (g6_OrderID);
CREATE INDEX IX_OrderItems_Product ON dbo.g6_OrderItems (g6_ProductID);
GO
 
-- ============================================================
--  7. ĐÁNH GIÁ SẢN PHẨM
-- ============================================================
CREATE TABLE dbo.g6_Reviews (
    g6_ReviewID   INT           NOT NULL IDENTITY(1,1),
    g6_ProductID  INT           NOT NULL,
    g6_CustomerID INT           NOT NULL,
    g6_Rating     TINYINT       NOT NULL,
    g6_Comment    NVARCHAR(MAX) NULL,
    g6_CreatedAt  DATETIME2(0)  NOT NULL DEFAULT GETDATE(),
 
    CONSTRAINT PK_Reviews         PRIMARY KEY (g6_ReviewID),
    CONSTRAINT FK_Reviews_Product FOREIGN KEY (g6_ProductID)  REFERENCES dbo.g6_Products(g6_ProductID)  ON DELETE CASCADE,
    CONSTRAINT FK_Reviews_Customer FOREIGN KEY (g6_CustomerID) REFERENCES dbo.g6_Customers(g6_CustomerID),
    CONSTRAINT UQ_Reviews_Once    UNIQUE (g6_ProductID, g6_CustomerID),
    CONSTRAINT CK_Reviews_Rating  CHECK (g6_Rating BETWEEN 1 AND 5)
);
GO
 
-- ============================================================
--  8. MÃ KHUYẾN MÃI
-- ============================================================
CREATE TABLE dbo.g6_Promotions (
    g6_PromotionID   INT           NOT NULL IDENTITY(1,1),
    g6_Code          VARCHAR(50)   NOT NULL,
    g6_Description   NVARCHAR(300) NULL,
    g6_DiscountType  VARCHAR(10)   NOT NULL,   -- 'percent' | 'fixed'
    g6_DiscountValue DECIMAL(15,0) NOT NULL,
    g6_MinOrderValue DECIMAL(15,0) NOT NULL DEFAULT 0,
    g6_MaxUses       INT           NULL,
    g6_UsedCount     INT           NOT NULL DEFAULT 0,
    g6_StartsAt      DATETIME2(0)  NULL,
    g6_ExpiresAt     DATETIME2(0)  NULL,
    g6_IsActive      BIT           NOT NULL DEFAULT 1,
 
    CONSTRAINT PK_Promotions       PRIMARY KEY (g6_PromotionID),
    CONSTRAINT UQ_Promotions_Code  UNIQUE (g6_Code),
    CONSTRAINT CK_Promotions_Type  CHECK (g6_DiscountType IN ('percent','fixed')),
    CONSTRAINT CK_Promotions_Value CHECK (g6_DiscountValue > 0)
);
GO

 
-- ============================================================
--  DỮ LIỆU MẪU
-- ============================================================
 
INSERT INTO dbo.g6_Categories (g6_CategoryName, g6_Slug, g6_Description) VALUES
(N'Văn phòng phẩm',   'van-phong-pham',   N'Bút, thước, kéo, tẩy, hồ dán'),
(N'Sách giáo khoa',   'sach-giao-khoa',   N'SGK các cấp tiểu học, THCS, THPT'),
(N'Sách tham khảo',   'sach-tham-khao',   N'Sách nâng cao, luyện thi, bài tập'),
(N'Thiết bị điện tử', 'thiet-bi-dien-tu', N'Máy tính, bảng vẽ điện tử, tai nghe'),
(N'Dụng cụ vẽ',       'dung-cu-ve',       N'Màu vẽ, cọ, giấy vẽ, khung tranh'),
(N'Balo & Túi học',   'balo-tui-hoc',     N'Balo đi học, túi đựng sách các loại');
 
INSERT INTO dbo.g6_Brands (g6_BrandName, g6_Country, g6_Website) VALUES
(N'Thiên Long', N'Việt Nam', 'https://thienlong.com.vn'),
(N'Hồng Hà',   N'Việt Nam', 'https://honghavnn.vn'),
(N'Stabilo',   N'Đức',      'https://stabilo.com'),
(N'Casio',     N'Nhật Bản', 'https://casio.com'),
(N'Samsung',   N'Hàn Quốc', 'https://samsung.com'),
(N'Staedtler', N'Đức',      'https://staedtler.com');
 
INSERT INTO dbo.g6_Employees (g6_FullName, g6_Email, g6_Phone, g6_Position, g6_HireDate, g6_Salary, g6_IsActive) VALUES
(N'Trần Thanh Tùng',  'tungtt@edustore.local',  '0988001001', N'Quản lý hệ thống',  '2024-01-15', 18000000, 1),
(N'Nguyễn Minh Khoa', 'khoanm@edustore.local',  '0988001002', N'Nhân viên kho',     '2024-03-10',  9500000, 1),
(N'Lê Thu Hà',        'halt@edustore.local',    '0988001003', N'Nhân viên bán hàng', '2024-05-20', 10500000, 1),
(N'Phạm Gia Huy',     'huypg@edustore.local',   '0988001004', N'Nhân viên hỗ trợ',   '2024-07-08',  9000000, 1),
(N'Đỗ Khánh Linh',    'linhdk@edustore.local',  '0988001005', N'Kế toán',            '2024-09-01', 12000000, 1);

INSERT INTO dbo.g6_Suppliers (g6_SupplierName, g6_ContactName, g6_Email, g6_Phone, g6_Address) VALUES
(N'Công ty Thiên Long',     N'Nguyễn Văn Nam', 'nam@thienlong-supply.vn', '0909000001', N'Quận 6, TP.HCM'),
(N'Công ty Hồng Hà',        N'Trần Thị Mai',  'mai@hongha-supply.vn',    '0909000002', N'Hai Bà Trưng, Hà Nội'),
(N'Stabilo Việt Nam',       N'Lê Quốc Bảo',   'bao@stabilo-vn.vn',       '0909000003', N'Quận 1, TP.HCM'),
(N'Casio Việt Nam',         N'Phạm Hải Long', 'long@casio-vn.vn',        '0909000004', N'Cầu Giấy, Hà Nội'),
(N'Samsung Accessories VN', N'Vũ Minh Đức',   'duc@samsungacc.vn',       '0909000005', N'Thủ Đức, TP.HCM');

INSERT INTO dbo.g6_Products (g6_SKU, g6_ProductName, g6_Description, g6_CategoryID, g6_BrandID, g6_Price, g6_Stock, g6_Unit, g6_ImageURL) VALUES
('VPP-001', N'Bút bi Thiên Long TL-027',         N'Ngòi 0.5mm mực xanh, viết êm',             1, 1,    5000, 500, N'Cái',  '/images/tl-027.jpg'),
('VPP-002', N'Bút chì Staedtler 2B',             N'Chì mềm, đường nét đẹp',                   1, 6,    8000, 300, N'Cái',  '/images/staedtler-2b.jpg'),
('VPP-003', N'Tẩy Stabilo hình chữ nhật',        N'Tẩy sạch, không để lại vết bẩn',            1, 3,    6000, 400, N'Cái',  '/images/stabilo-eraser.jpg'),
('VPP-004', N'Thước kẻ 30cm Thiên Long',         N'Nhựa trong suốt, có vạch mm',               1, 1,   12000, 200, N'Cái',  '/images/ruler-30cm.jpg'),
('VPP-005', N'Hộp bút màu Stabilo 24 màu',       N'Màu dạ sáng, không lem',                    5, 3,   85000, 150, N'Hộp',  '/images/stabilo-24-colors.jpg'),
('VPP-006', N'Kéo học sinh Thiên Long',          N'Lưỡi thép không gỉ, tay cầm nhựa',          1, 1,   18000, 250, N'Cái',  '/images/scissors.jpg'),
('SGK-001', N'SGK Toán 10 (Bộ Kết Nối)',         N'Sách giáo khoa Toán lớp 10',                2, 2,   32000, 300, N'Cuốn', '/images/sgk-toan-10.jpg'),
('SGK-002', N'SGK Ngữ Văn 11 (Bộ KNTT)',         N'Sách giáo khoa Ngữ Văn lớp 11',             2, 2,   28000, 250, N'Cuốn', '/images/sgk-van-11.jpg'),
('SGK-003', N'SGK Vật Lý 12',                    N'Sách giáo khoa Vật Lý lớp 12',              2, 2,   30000, 200, N'Cuốn', '/images/sgk-ly-12.jpg'),
('SGK-004', N'SGK Tiếng Anh 9 Global Success',   N'NXB Giáo Dục Việt Nam',                     2, 2,   26000, 280, N'Cuốn', '/images/sgk-ta-9.jpg'),
('STK-001', N'Bộ đề thi thử THPT Quốc Gia Toán', N'30 đề có đáp án chi tiết',                 3, 2,   65000, 120, N'Cuốn', '/images/on-thi-toan.jpg'),
('STK-002', N'Ôn tập Tiếng Anh B1-B2',           N'Luyện 4 kỹ năng IELTS/TOEIC',               3, 2,   89000,  90, N'Cuốn', '/images/tieng-anh-b1.jpg'),
('STK-003', N'Bài tập Hóa học 11 nâng cao',      N'Có đáp án và giải thích từng bước',          3, 2,   55000, 110, N'Cuốn', '/images/bai-tap-hoa-11.jpg'),
('DTE-001', N'Máy tính Casio FX-580VN X',        N'570 hàm, màn hình tự nhiên, pin AA',         4, 4,  495000,  80, N'Cái',  '/images/casio-580vnx.jpeg'),
('DTE-002', N'Bảng vẽ điện tử Wacom Ctl-472',    N'Cảm ứng bút, kết nối USB',                  4, 5, 1490000,  30, N'Cái',  '/images/wacom-472.jpg'),
('DTE-003', N'Tai nghe Samsung AKG Type-C',       N'Âm bass tốt, giảm tiếng ồn',                4, 5,  390000,  60, N'Cái',  '/images/samsung-akg.jpg'),
('DVE-001', N'Màu nước Stabilo 12 màu',          N'Không độc hại, dễ pha trộn',                 5, 3,   45000, 200, N'Hộp',  '/images/stabilo-watercolor.jpg'),
('DVE-002', N'Cọ vẽ số 6 lông tổng hợp',        N'Cọ mềm, không xòe lông',                    5, 6,   18000, 180, N'Cái',  '/images/brush-no6.jpg'),
('DVE-003', N'Giấy vẽ A3 200gsm',               N'Bề mặt mịn, dùng được cho màu nước',         5, NULL, 35000, 100, N'Tập',  '/images/paper-a3.jpg'),
('BAL-001', N'Balo học sinh Hồng Hà 3 ngăn',    N'Chống thấm, đệm lưng, quai điều chỉnh',      6, 2,  320000,  70, N'Cái',  '/images/balo-hong-ha.jpg'),
('BAL-002', N'Túi đeo chéo mini vải canvas',     N'Nhẹ, nhiều ngăn, khóa kim loại bền',         6, 2,  175000, 100, N'Cái',  '/images/tui-canvas.jpg');
 
INSERT INTO dbo.g6_Customers (g6_FullName, g6_Email, g6_Phone, g6_Address) VALUES
(N'Nguyễn Minh Anh', 'minha@email.com',  '0901234567', N'12 Lê Lợi, Hoàn Kiếm, Hà Nội'),
(N'Trần Quốc Bảo',   'baotq@email.com',  '0912345678', N'45 Trần Phú, Hải Châu, Đà Nẵng'),
(N'Lê Thị Cẩm',     'camlth@email.com', '0923456789', N'89 Nguyễn Huệ, Q.1, TP.HCM'),
(N'Phạm Đức Dũng',  'dungpd@email.com', '0934567890', N'7 Bà Triệu, Hồng Bàng, Hải Phòng'),
(N'Võ Thị Hoa',     'hoavt@email.com',  '0945678901', N'23 Hùng Vương, Pleiku, Gia Lai');

INSERT INTO dbo.g6_Accounts (g6_FullName, g6_Email, g6_Password, g6_Role, g6_CustomerID, g6_AdminRequestStatus, g6_RequestedRole) VALUES
(N'Người dùng mẫu',  'user@edustore.local',  'user123',  'user',  1, 'none', NULL),
(N'Người dùng Minh Anh', 'minha@email.com', '123456',   'user',  1, 'none', NULL),
(N'Người dùng Quốc Bảo', 'baotq@email.com', '123456',   'user',  2, 'pending', 'admin'),
(N'Quản trị viên chính', 'admin@edustore.local', 'admin123', 'admin', NULL, 'approved', NULL),
(N'Quản trị viên kho',   'manager@edustore.local', 'manager123', 'admin', NULL, 'approved', NULL);
 
INSERT INTO dbo.g6_Orders (g6_CustomerID, g6_OrderStatus, g6_ShippingAddress, g6_TotalAmount, g6_Discount) VALUES
(1, 'delivered', N'12 Lê Lợi, Hoàn Kiếm, Hà Nội',    995000,  0),
(2, 'shipping',  N'45 Trần Phú, Hải Châu, Đà Nẵng',   495000,  0),
(3, 'confirmed', N'89 Nguyễn Huệ, Q.1, TP.HCM',        154000,  0),
(4, 'pending',   N'7 Bà Triệu, Hồng Bàng, Hải Phòng',  320000,  0),
(1, 'delivered', N'12 Lê Lợi, Hoàn Kiếm, Hà Nội',     153000, 50000),
(5, 'cancelled', N'23 Hùng Vương, Pleiku, Gia Lai',      85000,  0);
 
-- Order 1: 100 bút bi + 1 máy tính Casio
INSERT INTO dbo.g6_OrderItems (g6_OrderID, g6_ProductID, g6_Quantity, g6_UnitPrice) VALUES
(1, 1,  100, 5000),
(1, 14,   1, 495000);
 
-- Order 2: 1 máy tính Casio
INSERT INTO dbo.g6_OrderItems (g6_OrderID, g6_ProductID, g6_Quantity, g6_UnitPrice) VALUES
(2, 14, 1, 495000);
 
-- Order 3: SGK Toán + Văn + sách ôn TA
INSERT INTO dbo.g6_OrderItems (g6_OrderID, g6_ProductID, g6_Quantity, g6_UnitPrice) VALUES
(3, 7,  1, 32000),
(3, 8,  1, 28000),
(3, 12, 1, 89000);
 
-- Order 4: 1 balo
INSERT INTO dbo.g6_OrderItems (g6_OrderID, g6_ProductID, g6_Quantity, g6_UnitPrice) VALUES
(4, 20, 1, 320000);
 
-- Order 5: màu nước + cọ + giấy vẽ (sau giảm 50k)
INSERT INTO dbo.g6_OrderItems (g6_OrderID, g6_ProductID, g6_Quantity, g6_UnitPrice) VALUES
(5, 17, 2, 45000),
(5, 18, 3, 18000),
(5, 19, 1, 35000);
 
-- Order 6: hộp bút màu (đã huỷ)
INSERT INTO dbo.g6_OrderItems (g6_OrderID, g6_ProductID, g6_Quantity, g6_UnitPrice) VALUES
(6, 5, 1, 85000);
 
INSERT INTO dbo.g6_Reviews (g6_ProductID, g6_CustomerID, g6_Rating, g6_Comment) VALUES
(14, 1, 5, N'Máy tính rất tốt, pin bền, phím bấm nhạy'),
(1,  2, 4, N'Bút bền, mực đều, giá hợp lý'),
(7,  3, 5, N'Sách in đẹp, nội dung rõ ràng dễ hiểu'),
(20, 4, 4, N'Balo chắc, đẹp, đeo thoải mái'),
(17, 1, 5, N'Màu đẹp, không độc, trẻ em dùng tốt'),
(15, 5, 4, N'Bảng vẽ mượt, kết nối dễ, cảm ứng nhạy');
 
INSERT INTO dbo.g6_Promotions (g6_Code, g6_Description, g6_DiscountType, g6_DiscountValue, g6_MinOrderValue, g6_MaxUses, g6_StartsAt, g6_ExpiresAt) VALUES
('BACK2SCHOOL', N'Giảm 10% cho đơn từ 200.000đ',    'percent', 10,    200000, 100, '2025-08-01', '2025-09-30'),
('GIAM50K',     N'Giảm 50.000đ cho đơn từ 500.000đ', 'fixed',  50000, 500000,  50, '2025-01-01', '2025-12-31'),
('NEWUSER',     N'Giảm 5% không giới hạn đơn',        'percent', 5,        0, 200, '2025-01-01', '2025-12-31');
-- ============================================================
--  KIỂM TRA
-- ============================================================
SELECT 'g6_Categories'  AS [Bảng], COUNT(*) AS [Bản ghi] FROM dbo.g6_Categories  UNION ALL
SELECT 'g6_Brands',                             COUNT(*) FROM dbo.g6_Brands       UNION ALL
SELECT 'g6_Employees',                          COUNT(*) FROM dbo.g6_Employees    UNION ALL
SELECT 'g6_Suppliers',                          COUNT(*) FROM dbo.g6_Suppliers    UNION ALL
SELECT 'g6_Products',                           COUNT(*) FROM dbo.g6_Products     UNION ALL
SELECT 'g6_Customers',                          COUNT(*) FROM dbo.g6_Customers    UNION ALL
SELECT 'g6_Accounts',                           COUNT(*) FROM dbo.g6_Accounts     UNION ALL
SELECT 'g6_AdminEvents',                        COUNT(*) FROM dbo.g6_AdminEvents  UNION ALL
SELECT 'g6_Orders',                             COUNT(*) FROM dbo.g6_Orders       UNION ALL
SELECT 'g6_OrderItems',                         COUNT(*) FROM dbo.g6_OrderItems   UNION ALL
SELECT 'g6_Reviews',                            COUNT(*) FROM dbo.g6_Reviews      UNION ALL
SELECT 'g6_Promotions',                         COUNT(*) FROM dbo.g6_Promotions;
 


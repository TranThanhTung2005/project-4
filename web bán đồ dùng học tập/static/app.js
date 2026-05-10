// app.js

const appContext = window.APP_CONTEXT || {};
const guestCartKey = "edustore_cart_guest";
const themeStorageKey = "edustore_theme";
let promoSlideIndex = 0;
let promoSlideTimer = null;

function applyTheme(theme) {
    const activeTheme = theme === "dark" ? "dark" : "light";
    document.documentElement.dataset.theme = activeTheme;
    localStorage.setItem(themeStorageKey, activeTheme);

    const toggle = document.getElementById("themeToggle");
    if (toggle) {
        const icon = toggle.querySelector(".theme-toggle-icon");
        if (icon) icon.textContent = activeTheme === "dark" ? "☾" : "☀";
        toggle.setAttribute(
            "aria-label",
            activeTheme === "dark" ? "Chuyển sang nền sáng" : "Chuyển sang nền tối"
        );
        toggle.title = activeTheme === "dark" ? "Chuyển sang nền sáng" : "Chuyển sang nền tối";
    }
}

function toggleTheme() {
    const currentTheme = document.documentElement.dataset.theme === "dark" ? "dark" : "light";
    applyTheme(currentTheme === "dark" ? "light" : "dark");
}

function initThemeToggle() {
    const toggle = document.getElementById("themeToggle");
    const savedTheme = localStorage.getItem(themeStorageKey);
    applyTheme(savedTheme || document.documentElement.dataset.theme || "light");
    if (toggle) {
        toggle.addEventListener("click", toggleTheme);
    }
}

function getCurrentCartKey() {
    if (appContext.currentUser && appContext.currentUser.email) {
        return `edustore_cart_${appContext.currentUser.email}`;
    }
    return guestCartKey;
}

function readCartFromStorage(key) {
    try {
        return JSON.parse(localStorage.getItem(key)) || [];
    } catch {
        return [];
    }
}

function syncCartWithCurrentUser() {
    const currentKey = getCurrentCartKey();
    const guestCart = readCartFromStorage(guestCartKey);
    const userCart = readCartFromStorage(currentKey);

    if (currentKey !== guestCartKey && guestCart.length > 0) {
        if (userCart.length === 0) {
            localStorage.setItem(currentKey, JSON.stringify(guestCart));
        } else {
            const merged = [...userCart];
            guestCart.forEach((guestItem) => {
                const existing = merged.find((item) => item.ProductID === guestItem.ProductID);
                if (existing) {
                    const maxStock = existing.MaxStock || guestItem.MaxStock || Infinity;
                    existing.Quantity = Math.min(existing.Quantity + guestItem.Quantity, maxStock);
                    existing.MaxStock = maxStock;
                } else {
                    merged.push(guestItem);
                }
            });
            localStorage.setItem(currentKey, JSON.stringify(merged));
        }
        localStorage.removeItem(guestCartKey);
    }

    return readCartFromStorage(currentKey);
}

let cart = syncCartWithCurrentUser();
let promoAnimationLock = false;
let promoPointerStartX = null;
let promoPointerDragging = false;
let promoSuppressClick = false;
let promoPointerTargetHref = null;

function notifyAdminCartEvent(productName, quantity) {
    fetch("/api/activity/cart-add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            product_name: productName,
            quantity: quantity
        })
    }).catch(() => {});
}

function loadProducts() {
    let searchInput = document.getElementById("search");
    let searchValue = searchInput ? searchInput.value : "";
    let categoryFilter = document.getElementById("category-filter");
    let categoryValue = categoryFilter ? categoryFilter.value : "";

    const query = new URLSearchParams({ search: searchValue });
    if (categoryValue) {
        query.set("category_id", categoryValue);
    }

    fetch(`/api/products?${query.toString()}`)
        .then(res => res.json())
        .then(data => {
            let products = data.data || data || []; 
            let html = "";

            if (products.length === 0) {
                html = "<p class='empty-msg'>Không tìm thấy sản phẩm nào.</p>";
            } else {
                products.forEach(p => {
                    let safeName = (p.ProductName || "").replace(/'/g, "\\'");
                    let imageHtml = p.ImageURL
                        ? `<img src="${p.ImageURL}" alt="${p.ProductName}" class="product-image" loading="lazy" onerror="this.closest('.product-media').classList.add('image-missing'); this.remove();">`
                        : "";
                    html += `
                        <div class="card">
                            <div class="product-media ${p.ImageURL ? "" : "image-missing"}">
                                ${imageHtml}
                                <div class="product-placeholder">EduStore</div>
                            </div>
                            <div class="card-tag">${p.CategoryName || "Sản phẩm"}</div>
                            <div class="card-info">
                                <h3>${p.ProductName}</h3>
                                ${p.BrandName ? `<p class="muted-line">${p.BrandName}</p>` : ""}
                                <p>💰 <b>${(p.Price || 0).toLocaleString()}</b> VND</p>
                                <p>📦 Kho: ${p.Stock || 0} ${p.Unit || ""}</p>
                            </div>
                            
                            <div class="quantity-selector">
                                <label>SL: </label>
                                <input type="number" id="qty-${p.ProductID}" value="1" min="1" max="${p.Stock}">
                            </div>

                            <button onclick="handleAddToCart(${p.ProductID}, '${safeName}', ${p.Price})">
                                ➕ Thêm vào giỏ
                            </button>
                            <a href="/products/${p.ProductID}" class="card-detail-link">Xem chi tiết</a>
                        </div>`;
                });
            }
            let productContainer = document.getElementById("products");
            if (productContainer) productContainer.innerHTML = html;
        })
        .catch(err => console.error("Lỗi:", err));
}

function selectHeaderCategory(categoryId, categoryLabel) {
    const categoryInput = document.getElementById("category-filter");
    const categoryLabelNode = document.getElementById("category-filter-label");
    if (categoryInput) {
        categoryInput.value = categoryId;
    }
    if (categoryLabelNode) {
        categoryLabelNode.textContent = categoryLabel;
    }

    if (window.location.pathname === "/") {
        loadProducts();
        return;
    }

    const searchInput = document.getElementById("search");
    const params = new URLSearchParams();
    if (searchInput && searchInput.value) {
        params.set("search", searchInput.value);
    }
    if (categoryId) {
        params.set("category_id", categoryId);
    }
    window.location.href = `/${params.toString() ? `?${params.toString()}` : ""}`;
}

function toggleHeaderSearch() {
    const searchToggle = document.querySelector(".nav-search-toggle");
    if (!searchToggle) return;
    searchToggle.classList.toggle("open");
}

function initHeaderInteractions() {
    document.addEventListener("click", (event) => {
        const searchToggle = document.querySelector(".nav-search-toggle");
        if (!searchToggle) return;
        if (!searchToggle.contains(event.target)) {
            searchToggle.classList.remove("open");
        }
    });
}

// Hàm lấy số lượng từ giao diện
function handleAddToCart(id, name, price) {
    const qtyInput = document.getElementById(`qty-${id}`);
    const quantity = parseInt(qtyInput.value);
    const maxStock = parseInt(qtyInput.max || "0");

    if (isNaN(quantity) || quantity <= 0) {
        alert("Vui lòng nhập số lượng hợp lệ!");
        return;
    }

    if (!isNaN(maxStock) && maxStock > 0 && quantity > maxStock) {
        alert("Số lượng vượt quá tồn kho hiện tại.");
        qtyInput.value = maxStock;
        return;
    }
    
    addToCart(id, name, price, quantity, maxStock);
}

// Hàm xử lý logic giỏ hàng (Đã cập nhật tham số quantity)
function addToCart(id, name, price, quantity, maxStock) {
    let item = cart.find(i => i.ProductID === id);
    
    if (item) {
        const limit = Number.isFinite(maxStock) && maxStock > 0 ? maxStock : (item.MaxStock || Infinity);
        item.Quantity = Math.min(item.Quantity + quantity, limit);
        item.MaxStock = limit;
    } else {
        cart.push({ 
            ProductID: id, 
            ProductName: name, 
            Price: price, 
            Quantity: quantity,
            MaxStock: Number.isFinite(maxStock) && maxStock > 0 ? maxStock : quantity
        });
    }

    localStorage.setItem(getCurrentCartKey(), JSON.stringify(cart));
    updateCartCount();
    notifyAdminCartEvent(name, quantity);

    const currentItem = cart.find(i => i.ProductID === id);
    if (currentItem && currentItem.MaxStock && currentItem.Quantity >= currentItem.MaxStock) {
        alert(`Giỏ hàng đã đạt tối đa tồn kho cho ${name}.`);
        return;
    }

    alert(`Đã thêm ${quantity} ${name} vào giỏ!`);
}

function updateCartCount() {
    let badge = document.getElementById("cart-count-badge");
    if (badge) {
        let count = cart.reduce((sum, i) => sum + i.Quantity, 0);
        badge.innerText = count;
    }
}

function saveCart() {
    localStorage.setItem(getCurrentCartKey(), JSON.stringify(cart));
    updateCartCount();
}

function changeCartQuantity(productId, delta) {
    const item = cart.find(i => i.ProductID === productId);
    if (!item) return;

    const limit = item.MaxStock && item.MaxStock > 0 ? item.MaxStock : Infinity;
    item.Quantity = Math.min(limit, Math.max(1, item.Quantity + delta));
    saveCart();
    renderCartPage();
}

function removeFromCart(productId) {
    cart = cart.filter(i => i.ProductID !== productId);
    saveCart();
    renderCartPage();
}

function renderCartPage() {
    let cartArea = document.getElementById("cart-content-area");
    let totalArea = document.getElementById("cart-total-price");
    if (!cartArea) return;

    if (cart.length === 0) {
        cartArea.innerHTML = `
            <div class="cart-empty-state">
                <div class="cart-empty-icon">🛍</div>
                <h3>Giỏ hàng của bạn đang trống</h3>
                <p>Thêm vài món đồ học tập để bắt đầu đơn hàng mới.</p>
                <a href="/" class="secondary-link">Quay lại trang sản phẩm</a>
            </div>
        `;
        if (totalArea) {
            totalArea.innerHTML = `
                <div class="summary-header">
                    <p class="eyebrow">Tóm tắt đơn hàng</p>
                    <h3>Chưa có sản phẩm nào</h3>
                </div>
            `;
        }
        return;
    }

    let html = `<div class="cart-list">`;
    let total = 0;
    let totalItems = 0;

    cart.forEach(item => {
        let subtotal = item.Price * item.Quantity;
        total += subtotal;
        totalItems += item.Quantity;
        html += `
            <article class="cart-item-card">
                <div class="cart-item-main">
                    <div class="cart-item-badge">EduStore</div>
                    <div>
                        <h3>${item.ProductName}</h3>
                        <p class="muted-line">Đơn giá: ${item.Price.toLocaleString()}đ</p>
                        ${item.MaxStock ? `<p class="muted-line">Tồn kho tối đa: ${item.MaxStock}</p>` : ""}
                    </div>
                </div>
                <div class="cart-item-actions">
                    <div class="cart-qty-control">
                        <button type="button" class="qty-btn" onclick="changeCartQuantity(${item.ProductID}, -1)">-</button>
                        <span>${item.Quantity}</span>
                        <button type="button" class="qty-btn" onclick="changeCartQuantity(${item.ProductID}, 1)" ${item.MaxStock && item.Quantity >= item.MaxStock ? "disabled" : ""}>+</button>
                    </div>
                    <strong class="cart-item-subtotal">${subtotal.toLocaleString()}đ</strong>
                    <button type="button" class="cart-remove-btn" onclick="removeFromCart(${item.ProductID})">Xóa</button>
                </div>
            </article>`;
    });

    html += "</div>";
    cartArea.innerHTML = html;
    if (totalArea) {
        totalArea.innerHTML = `
            <div class="summary-header">
                <p class="eyebrow">Tóm tắt đơn hàng</p>
                <h3>${totalItems} sản phẩm trong giỏ</h3>
            </div>
            <div class="summary-line">
                <span>Tạm tính</span>
                <strong>${total.toLocaleString()}đ</strong>
            </div>
            <div class="summary-line">
                <span>Phí vận chuyển</span>
                <strong>Miễn phí</strong>
            </div>
            <div class="summary-line summary-total">
                <span>Tổng thanh toán</span>
                <strong>${total.toLocaleString()}đ</strong>
            </div>
            <p class="summary-note">Đơn hàng sẽ được tạo với thông tin khách hàng mặc định hiện tại.</p>
        `;
    }
}

function checkout() {
    if (cart.length === 0) return alert("Giỏ hàng trống!");
    if (!appContext.currentUser) {
        alert("Bạn cần đăng nhập trước khi thanh toán.");
        window.location.href = appContext.loginUrl || "/login";
        return;
    }

    fetch("/api/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ Items: cart })
    })
    .then(async res => {
        const data = await res.json().catch(() => ({}));
        if (res.status === 401) {
            alert(data.error || "Bạn cần đăng nhập trước khi thanh toán.");
            window.location.href = appContext.loginUrl || "/login";
            return null;
        }
        if (res.ok) {
            alert("🎉 Đặt hàng thành công!");
            cart = [];
            localStorage.removeItem(getCurrentCartKey());
            window.location.href = "/"; 
        } else {
            alert(data.error || "Lỗi đặt hàng, vui lòng thử lại.");
        }
        return null;
    })
    .catch(err => alert("Lỗi kết nối: " + err));
}

function reorderOrder(orderId) {
    fetch(`/api/orders/${orderId}/reorder`)
        .then(async (res) => {
            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                alert(data.error || "Không thể lấy lại đơn hàng.");
                return null;
            }
            return data;
        })
        .then((data) => {
            if (!data) return;

            const existingCart = readCartFromStorage(getCurrentCartKey());
            const mergedCart = [...existingCart];

            data.items.forEach((orderItem) => {
                const found = mergedCart.find((item) => item.ProductID === orderItem.ProductID);
                if (found) {
                    const limit = orderItem.MaxStock || found.MaxStock || Infinity;
                    found.Quantity = Math.min(found.Quantity + orderItem.Quantity, limit);
                    found.MaxStock = limit;
                } else {
                    mergedCart.push({
                        ProductID: orderItem.ProductID,
                        ProductName: orderItem.ProductName,
                        Price: orderItem.Price,
                        Quantity: orderItem.Quantity,
                        MaxStock: orderItem.MaxStock
                    });
                }
            });

            cart = mergedCart;
            saveCart();
            window.location.href = "/cart";
        })
        .catch((err) => alert("Lỗi kết nối: " + err));
}

function renderPromoSlide(index, direction = 1) {
    const slides = Array.from(document.querySelectorAll(".promo-banner"));
    const dots = Array.from(document.querySelectorAll(".promo-dot"));
    if (!slides.length) return;

    const nextIndex = (index + slides.length) % slides.length;
    const currentIndex = slides.findIndex((slide) => slide.classList.contains("active"));

    if (currentIndex === -1) {
        promoSlideIndex = nextIndex;
        slides.forEach((slide, idx) => {
            slide.classList.toggle("active", idx === promoSlideIndex);
            slide.classList.remove("entering-from-right", "entering-from-left", "exiting-to-left", "exiting-to-right");
        });
    } else if (currentIndex !== nextIndex && !promoAnimationLock) {
        promoAnimationLock = true;
        const currentSlide = slides[currentIndex];
        const nextSlide = slides[nextIndex];

        slides.forEach((slide) => {
            slide.classList.remove("entering-from-right", "entering-from-left", "exiting-to-left", "exiting-to-right");
        });

        if (direction >= 0) {
            nextSlide.classList.add("active", "entering-from-right");
            currentSlide.classList.add("exiting-to-left");
        } else {
            nextSlide.classList.add("active", "entering-from-left");
            currentSlide.classList.add("exiting-to-right");
        }
        currentSlide.classList.remove("active");
        promoSlideIndex = nextIndex;

        window.setTimeout(() => {
            currentSlide.classList.remove("exiting-to-left", "exiting-to-right");
            nextSlide.classList.remove("entering-from-right", "entering-from-left");
            promoAnimationLock = false;
        }, 620);
    }

    dots.forEach((dot, idx) => {
        dot.classList.toggle("active", idx === promoSlideIndex);
    });
}

function restartPromoTimer() {
    if (promoSlideTimer) {
        clearInterval(promoSlideTimer);
    }
    if (document.querySelectorAll(".promo-banner").length > 1) {
        promoSlideTimer = setInterval(() => {
            renderPromoSlide(promoSlideIndex + 1, 1);
        }, 4500);
    }
}

function movePromoSlide(step) {
    if (promoAnimationLock) return;
    renderPromoSlide(promoSlideIndex + step, step);
    restartPromoTimer();
}

function getPromoDirection(targetIndex) {
    const slides = document.querySelectorAll(".promo-banner");
    const total = slides.length;
    if (!total) return 1;

    const forwardSteps = (targetIndex - promoSlideIndex + total) % total;
    const backwardSteps = (promoSlideIndex - targetIndex + total) % total;
    return forwardSteps <= backwardSteps ? 1 : -1;
}

function goToPromoSlide(index) {
    if (promoAnimationLock) return;
    const direction = getPromoDirection(index);
    renderPromoSlide(index, direction);
    restartPromoTimer();
}

function initPromoCarousel() {
    const carousel = document.getElementById("promo-carousel");
    const slides = document.querySelectorAll(".promo-banner");
    if (!slides.length) return;
    renderPromoSlide(0, 1);
    restartPromoTimer();

    if (!carousel) return;

    carousel.addEventListener("pointerdown", (event) => {
        if (promoAnimationLock) return;
        if (event.pointerType === "mouse" && event.button !== 0) return;
        if (event.target.closest(".promo-nav, .promo-dot")) return;
        promoPointerStartX = event.clientX;
        promoPointerDragging = true;
        promoSuppressClick = false;
        promoPointerTargetHref = event.target.closest(".promo-banner")?.href || null;
        carousel.classList.add("is-dragging");
        if (carousel.setPointerCapture) {
            carousel.setPointerCapture(event.pointerId);
        }
    });

    carousel.addEventListener("pointermove", (event) => {
        if (!promoPointerDragging || promoPointerStartX === null) return;
        event.preventDefault();
        const deltaX = event.clientX - promoPointerStartX;
        if (Math.abs(deltaX) < 60) return;

        promoPointerDragging = false;
        promoSuppressClick = true;
        promoPointerTargetHref = null;
        promoPointerStartX = null;
        carousel.classList.remove("is-dragging");

        if (deltaX < 0) {
            movePromoSlide(1);
        } else {
            movePromoSlide(-1);
        }
    });

    const resetPromoDrag = (event) => {
        const shouldFollowLink = !promoSuppressClick && promoPointerTargetHref;

        promoPointerDragging = false;
        promoPointerStartX = null;
        carousel.classList.remove("is-dragging");
        if (event && carousel.releasePointerCapture) {
            try {
                carousel.releasePointerCapture(event.pointerId);
            } catch {}
        }

        if (shouldFollowLink) {
            const targetHref = promoPointerTargetHref;
            promoPointerTargetHref = null;
            window.location.href = targetHref;
            return;
        }

        promoPointerTargetHref = null;
        promoSuppressClick = false;
    };

    carousel.addEventListener("pointerup", resetPromoDrag);
    carousel.addEventListener("pointercancel", resetPromoDrag);
    carousel.addEventListener("dragstart", (event) => event.preventDefault());
}

updateCartCount();
document.addEventListener("DOMContentLoaded", initThemeToggle);
document.addEventListener("DOMContentLoaded", initPromoCarousel);
document.addEventListener("DOMContentLoaded", initHeaderInteractions);

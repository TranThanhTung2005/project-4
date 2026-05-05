(() => {
  const moneyFormatter = new Intl.NumberFormat("vi-VN");

  function qs(selector, root = document) {
    return root.querySelector(selector);
  }

  function qsa(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
  }

  function clampNumber(value, min, max) {
    const parsed = Number.parseInt(value, 10);
    if (Number.isNaN(parsed)) return min;
    return Math.min(Math.max(parsed, min), max);
  }

  function markActiveNav() {
    const currentPath = window.location.pathname;
    qsa(".nav a").forEach((link) => {
      const href = link.getAttribute("href");
      if (!href || href === "#") return;
      const linkPath = new URL(href, window.location.origin).pathname;
      const active = linkPath === currentPath || (linkPath !== "/" && currentPath.startsWith(linkPath));
      link.classList.toggle("is-active", active);
    });
  }

  function initFlashMessages() {
    qsa(".flash").forEach((flash) => {
      const close = document.createElement("button");
      close.type = "button";
      close.className = "flash-close";
      close.setAttribute("aria-label", "Đóng thông báo");
      close.textContent = "×";
      close.addEventListener("click", () => flash.remove());
      flash.appendChild(close);

      window.setTimeout(() => {
        flash.classList.add("is-hiding");
        window.setTimeout(() => flash.remove(), 260);
      }, 4200);
    });
  }

  function initQuantityInputs() {
    qsa('input[type="number"][name="quantity"], input[type="number"][name^="qty_"]').forEach((input) => {
      const normalize = () => {
        const min = Number.parseInt(input.min || "1", 10);
        const max = Number.parseInt(input.max || "9999", 10);
        input.value = clampNumber(input.value, min, max);
      };
      input.addEventListener("input", () => {
        if (input.value === "") return;
        normalize();
      });
      input.addEventListener("blur", normalize);
    });
  }

  function initProductCards() {
    qsa(".product-card").forEach((card) => {
      const form = qs("form", card);
      const quantityInput = qs('input[name="quantity"]', card);
      const button = qs('button[type="submit"]', card);
      const title = qs("h3", card)?.textContent?.trim() || "sản phẩm";

      form?.addEventListener("submit", () => {
        if (quantityInput) {
          const min = Number.parseInt(quantityInput.min || "1", 10);
          const max = Number.parseInt(quantityInput.max || "9999", 10);
          quantityInput.value = clampNumber(quantityInput.value, min, max);
        }
        if (button) {
          button.dataset.originalText = button.textContent;
          button.textContent = `Đang thêm ${title}`;
          button.disabled = true;
        }
      });
    });
  }

  function initImageFallbacks() {
    qsa("img.product-img").forEach((img) => {
      img.addEventListener("error", () => {
        const label = img.alt || "EduStore";
        img.removeAttribute("src");
        img.classList.add("image-fallback");
        img.setAttribute(
          "style",
          `${img.getAttribute("style") || ""};background:linear-gradient(135deg,#e5f6f0,#fff3cf);`
        );
        img.parentElement?.classList.add("has-image-fallback");
        img.insertAdjacentHTML("afterend", `<div class="image-fallback-text">${label}</div>`);
      }, { once: true });
    });
  }

  function initCartPage() {
    const cartForm = qs('form[action=""], form[method="post"]');
    const totalNode = qsa(".table td:last-child").at(-1);
    if (!window.location.pathname.startsWith("/cart")) return;

    qsa('input[name^="qty_"]').forEach((input) => {
      input.addEventListener("input", () => {
        const row = input.closest("tr");
        const priceText = row?.children[1]?.textContent || "0";
        const price = Number.parseInt(priceText.replace(/\D/g, ""), 10) || 0;
        const qty = clampNumber(input.value, 0, Number.parseInt(input.max || "9999", 10));
        const subtotalCell = row?.children[3];
        if (subtotalCell) subtotalCell.textContent = `${moneyFormatter.format(price * qty)}đ`;
      });
    });

    cartForm?.addEventListener("submit", () => {
      qsa('input[name^="qty_"]').forEach((input) => {
        input.value = clampNumber(input.value, 0, Number.parseInt(input.max || "9999", 10));
      });
    });

    if (totalNode) totalNode.closest("table")?.classList.add("cart-table");
  }

  function initFormSubmitState() {
    qsa("form").forEach((form) => {
      if (form.dataset.jsSubmitState === "off") return;
      form.addEventListener("submit", () => {
        const button = qs('button[type="submit"]:not([name])', form);
        if (!button || button.disabled) return;
        button.dataset.originalText = button.textContent;
        button.textContent = "Đang xử lý...";
        button.disabled = true;
      });
    });
  }

  function initPasswordToggle() {
    qsa('input[type="password"]').forEach((input) => {
      const wrapper = document.createElement("div");
      wrapper.className = "password-wrap";
      input.parentNode.insertBefore(wrapper, input);
      wrapper.appendChild(input);

      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "password-toggle";
      toggle.textContent = "Hiện";
      toggle.addEventListener("click", () => {
        const showing = input.type === "text";
        input.type = showing ? "password" : "text";
        toggle.textContent = showing ? "Hiện" : "Ẩn";
      });
      wrapper.appendChild(toggle);
    });
  }

  function initAdminConfirmations() {
    qsa('form[action*="/delete"]').forEach((form) => {
      form.addEventListener("submit", (event) => {
        if (!window.confirm("Bạn chắc chắn muốn ẩn mục này?")) {
          event.preventDefault();
        }
      });
    });

    qsa('form[action*="/approve"] button[value="reject"]').forEach((button) => {
      button.addEventListener("click", (event) => {
        if (!window.confirm("Từ chối yêu cầu quyền admin này?")) {
          event.preventDefault();
        }
      });
    });
  }

  function initFilterShortcuts() {
    const filterForm = qs(".toolbar");
    if (!filterForm) return;

    qsa("select", filterForm).forEach((select) => {
      select.addEventListener("change", () => filterForm.requestSubmit());
    });

    const search = qs('input[name="q"]', filterForm);
    search?.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        search.value = "";
        filterForm.requestSubmit();
      }
    });
  }

  function initCartBadgePulse() {
    const badge = qs(".cart-badge");
    if (!badge) return;
    const count = Number.parseInt(badge.textContent || "0", 10);
    if (count > 0) badge.classList.add("has-items");
  }

  document.addEventListener("DOMContentLoaded", () => {
    markActiveNav();
    initFlashMessages();
    initQuantityInputs();
    initProductCards();
    initImageFallbacks();
    initCartPage();
    initPasswordToggle();
    initAdminConfirmations();
    initFilterShortcuts();
    initCartBadgePulse();
    initFormSubmitState();
  });
})();

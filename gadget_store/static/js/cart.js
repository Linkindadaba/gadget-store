/**
 * F.B Nation - Shopping Cart & Notification Logic
 * Handles asynchronous cart operations and premium UI feedback.
 */

// Helper: Get CSRF token for secure POST requests
function getCsrfToken() {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, 10) === 'csrftoken=') {
                cookieValue = decodeURIComponent(cookie.substring(10));
                break;
            }
        }
    }
    return cookieValue;
}

// Helper: Display non-blocking notifications
function showNotification(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '1500';
        document.body.appendChild(container);
    }

    const toastId = `toast-${Date.now()}`;
    const bgClass = type === 'success' ? 'bg-success' : (type === 'error' ? 'bg-danger' : 'bg-dark');
    const icon = type === 'success' ? 'bi-check-circle-fill' : 'bi-exclamation-circle-fill';

    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0 shadow-lg" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi ${icon} me-2"></i> ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>`;

    container.insertAdjacentHTML('beforeend', toastHtml);
    const toastEl = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
    toast.show();

    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}

// Logic: Add Product to Cart via AJAX
async function addToCart(productId) {
    const url = `/cart/add/${productId}/`;
    const formData = new FormData();
    formData.append('product_id', productId);
    formData.append('quantity', 1);

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            // Update navbar badge
            const badges = document.querySelectorAll('.cart-count-badge');
            badges.forEach(badge => {
                const totalItems = Number(data.cart_total_items ?? data.cart_count ?? 0);
                badge.textContent = totalItems;
                badge.classList.toggle('d-none', totalItems <= 0);
                // Subtle scale animation for the badge
                badge.animate([{ transform: 'scale(1)' }, { transform: 'scale(1.2)' }, { transform: 'scale(1)' }], { duration: 200 });
            });
            
            showNotification(data.message || 'Added to your cart!');
        } else {
            showNotification(data.message || 'Failed to add item.', 'error');
        }
    } catch (error) {
        showNotification('Network error occurred.', 'error');
    }
}

// Logic: Update Quantity on Cart Page
async function updateQty(productId, action) {
    // This assumes your backend URL pattern for quantity updates
    const url = `/cart/update/${productId}/${action}/`;
    window.location.href = url; // Standard fallback - can be upgraded to AJAX later
}

// Expose functions to global scope for HTML onclick handlers
window.getCsrfToken = getCsrfToken;
window.showNotification = showNotification;
window.addToCart = addToCart;
window.updateQty = updateQty;
/**
 * Cart.js - Shopping Cart JavaScript
 */

/**
 * Update cart item quantity
 * @param {string} productId - Product ID to update
 * @param {number} qty - New quantity
 */
function updateQty(productId, qty) {
    if (qty < 1) return;

    fetch(`/cart/update/${productId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCsrfToken()
        },
        body: `quantity=${qty}`
    })
        .then(response => {
            if (response.ok) {
                location.reload();
            } else {
                showNotification('Failed to update quantity', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('An error occurred', 'error');
        });
}

/**
 * Get CSRF token from cookie
 * @returns {string} CSRF token
 */
function getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Handle AJAX add to cart
 */
document.addEventListener('DOMContentLoaded', function () {
    const addToCartForms = document.querySelectorAll('.ajax-add-to-cart');

    addToCartForms.forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault();

            const productName = form.getAttribute('data-product-name');
            const formData = new FormData(form);

            fetch(form.getAttribute('action'), {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showNotification(`${productName} added to cart!`, 'success');
                        // Update cart count if available
                        const cartBadge = document.querySelector('.cart-badge');
                        if (cartBadge) {
                            cartBadge.textContent = data.cart_count;
                        }
                    } else {
                        showNotification(data.message || 'Failed to add to cart', 'error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showNotification('An error occurred', 'error');
                });
        });
    });
});

/**
 * Show notification toast
 * @param {string} message - Message to display
 * @param {string} type - Notification type (success, error, warning, info)
 * @param {number} duration - Duration in milliseconds
 */
function showNotification(message, type = 'info', duration = 3000) {
    const alertClass = `alert-${type}`;
    const alert = document.createElement('div');
    alert.className = `alert ${alertClass} position-fixed`;
    alert.setAttribute('role', 'alert');
    alert.style.cssText = `
        top: 80px;
        right: 20px;
        z-index: 9999;
        max-width: 400px;
        animation: slideIn 0.3s ease-out;
    `;
    alert.textContent = message;

    document.body.appendChild(alert);

    setTimeout(() => {
        alert.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => alert.remove(), 300);
    }, duration);
}

// Add CSS animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

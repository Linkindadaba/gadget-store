/**
 * Admin.js - Admin Panel JavaScript
 */

/**
 * Toggle mobile navigation menu
 */
function toggleMobileMenu() {
    const overlay = document.querySelector('.mobile-overlay');
    const nav = document.querySelector('.mobile-nav');
    const btn = document.querySelector('.mobile-menu-btn');

    if (!overlay || !nav) {
        console.warn('Mobile navigation elements not found');
        return;
    }

    overlay.classList.toggle('show');
    nav.classList.toggle('show');
    btn.setAttribute('aria-expanded', nav.classList.contains('show'));
}

/**
 * Close mobile navigation
 */
function closeMobileMenu() {
    const overlay = document.querySelector('.mobile-overlay');
    const nav = document.querySelector('.mobile-nav');
    const btn = document.querySelector('.mobile-menu-btn');

    if (overlay) overlay.classList.remove('show');
    if (nav) nav.classList.remove('show');
    if (btn) btn.setAttribute('aria-expanded', 'false');
}

/**
 * Initialize admin mobile navigation
 */
document.addEventListener('DOMContentLoaded', function () {
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const mobileOverlay = document.querySelector('.mobile-overlay');
    const mobileNav = document.querySelector('.mobile-nav');

    // Mobile menu button click
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', toggleMobileMenu);
    }

    // Close menu when overlay is clicked
    if (mobileOverlay) {
        mobileOverlay.addEventListener('click', closeMobileMenu);
    }

    // Close menu when a nav item is clicked
    if (mobileNav) {
        const navItems = mobileNav.querySelectorAll('a');
        navItems.forEach(item => {
            item.addEventListener('click', () => {
                // Don't close for dropdown toggles
                if (!item.classList.contains('nav-toggle')) {
                    closeMobileMenu();
                }
            });
        });
    }

    // Close menu on escape key
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            closeMobileMenu();
        }
    });

    // Highlight active nav item
    const currentUrl = window.location.pathname;
    if (mobileNav) {
        const navItems = mobileNav.querySelectorAll('a');
        navItems.forEach(item => {
            if (item.getAttribute('href') === currentUrl) {
                item.classList.add('active');
            }
        });
    }
});

/**
 * Show admin notification
 * @param {string} message - Message to display
 * @param {string} type - Type (success, error, warning, info)
 * @param {number} duration - Duration in ms
 */
function showAdminNotification(message, type = 'info', duration = 3000) {
    const alertClass = `alert alert-${type}`;
    const alert = document.createElement('div');
    alert.className = alertClass;
    alert.setAttribute('role', 'alert');
    alert.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        z-index: 9999;
        max-width: 400px;
        min-width: 300px;
        animation: slideIn 0.3s ease-out;
    `;
    alert.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span>${message}</span>
            <button type="button" class="btn-close" aria-label="Close" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;

    document.body.appendChild(alert);

    setTimeout(() => {
        if (alert.parentElement) {
            alert.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => alert.remove(), 300);
        }
    }, duration);
}

/**
 * Confirm action dialog
 * @param {string} message - Confirmation message
 * @returns {Promise<boolean>}
 */
async function confirmAction(message) {
    return new Promise(resolve => {
        if (confirm(message)) {
            resolve(true);
        } else {
            resolve(false);
        }
    });
}

/**
 * Add loading state to button
 * @param {HTMLElement} button - Button element
 * @param {string} loadingText - Text to show while loading
 */
function setButtonLoading(button, loadingText = 'Loading...') {
    button.disabled = true;
    button.setAttribute('data-original-text', button.textContent);
    button.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${loadingText}`;
}

/**
 * Remove loading state from button
 * @param {HTMLElement} button - Button element
 */
function resetButton(button) {
    button.disabled = false;
    button.textContent = button.getAttribute('data-original-text') || 'Submit';
}

// Add CSS animations
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

    @keyframes spin {
        from {
            transform: rotate(0deg);
        }
        to {
            transform: rotate(360deg);
        }
    }

    .spinner-border {
        display: inline-block;
        width: 1rem;
        height: 1rem;
        vertical-align: text-bottom;
        border: 0.25em solid currentColor;
        border-right-color: transparent;
        border-radius: 50%;
        animation: spin 0.75s linear infinite;
    }

    .spinner-border-sm {
        width: 0.875rem;
        height: 0.875rem;
        border-width: 0.2em;
    }
`;
document.head.appendChild(style);

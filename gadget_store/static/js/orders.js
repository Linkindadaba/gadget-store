/**
 * Orders Management - AJAX handlers for order cancellation and deletion
 */

// Get CSRF token from cookie or meta tag
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
  // If not found in cookie, try meta tag
  if (!cookieValue) {
    const meta = document.querySelector('[name="csrf-token"]');
    if (meta) {
      cookieValue = meta.getAttribute('content');
    }
  }
  return cookieValue;
}

/**
 * Cancel order via AJAX
 * @param {number} orderId - The ID of the order to cancel
 * @param {HTMLElement} button - The button element that triggered the action
 */
function cancelOrder(orderId, button) {
  // Show confirmation dialog
  if (!confirm('Are you sure you want to cancel this order? This action cannot be undone.')) {
    return;
  }

  const url = `/orders/${orderId}/cancel/`;
  const csrfToken = getCsrfToken();

  // Disable button and show loading state
  button.disabled = true;
  const originalText = button.textContent;
  button.textContent = 'Cancelling...';

  fetch(url, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrfToken,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({}),
  })
    .then((response) => {
      if (!response.ok) {
        return response.json().then((data) => {
          throw new Error(data.error || `HTTP error! status: ${response.status}`);
        });
      }
      return response.json();
    })
    .then((data) => {
      // Success - update UI
      showNotification('Order cancelled successfully', 'success');

      // Update the status badge
      const card = button.closest('.bg-white');
      const badge = card.querySelector('.badge');
      if (badge) {
        badge.classList.remove('bg-warning', 'text-dark');
        badge.classList.add('bg-danger');
        badge.textContent = 'Cancelled';
      }

      // Update or remove the payment button
      const paymentBtn = card.querySelector('.btn-primary-custom');
      if (paymentBtn) {
        paymentBtn.style.display = 'none';
      }

      // Hide or disable the cancel button
      button.style.display = 'none';
    })
    .catch((error) => {
      showNotification(`Error: ${error.message}`, 'danger');
      button.disabled = false;
      button.textContent = originalText;
    });
}

/**
 * Delete order via AJAX (staff only)
 * @param {number} orderId - The ID of the order to delete
 * @param {HTMLElement} button - The button element that triggered the action
 */
function deleteOrder(orderId, button) {
  // Show confirmation dialog
  if (
    !confirm(
      'Are you sure you want to delete this order? This action is permanent and cannot be undone.'
    )
  ) {
    return;
  }

  const url = `/orders/${orderId}/delete/`;
  const csrfToken = getCsrfToken();

  // Disable button and show loading state
  button.disabled = true;
  const originalText = button.textContent;
  button.textContent = 'Deleting...';

  fetch(url, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrfToken,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({}),
  })
    .then((response) => {
      if (!response.ok) {
        return response.json().then((data) => {
          throw new Error(data.error || `HTTP error! status: ${response.status}`);
        });
      }
      return response.json();
    })
    .then((data) => {
      // Success - remove the order card
      showNotification('Order deleted successfully', 'success');

      const card = button.closest('.col-12');
      if (card) {
        card.style.transition = 'opacity 0.3s';
        card.style.opacity = '0';
        setTimeout(() => {
          card.remove();

          // If no more orders, show empty state
          const ordersList = document.querySelector('.row.g-3');
          if (ordersList && ordersList.children.length === 0) {
            location.reload(); // Reload to show empty state
          }
        }, 300);
      }
    })
    .catch((error) => {
      showNotification(`Error: ${error.message}`, 'danger');
      button.disabled = false;
      button.textContent = originalText;
    });
}

/**
 * Show a notification toast
 * @param {string} message - The notification message
 * @param {string} type - The notification type (success, danger, warning, info)
 */
function showNotification(message, type = 'info') {
  // Create toast container if it doesn't exist
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    document.body.appendChild(container);
  }

  // Create toast element
  const toastId = 'toast-' + Date.now();
  const toast = document.createElement('div');
  toast.id = toastId;
  toast.className = `toast`;
  toast.setAttribute('role', 'alert');
  toast.setAttribute('aria-live', 'assertive');
  toast.setAttribute('aria-atomic', 'true');
  toast.innerHTML = `
    <div class="toast-header bg-${type} text-white border-0">
      <strong class="me-auto">Notification</strong>
      <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
    <div class="toast-body">
      ${message}
    </div>
  `;

  container.appendChild(toast);

  // Show toast
  const bsToast = new bootstrap.Toast(toast);
  bsToast.show();

  // Remove element after it's hidden
  toast.addEventListener('hidden.bs.toast', () => {
    toast.remove();
  });
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  // Attach event listeners to cancel buttons
  const cancelButtons = document.querySelectorAll('[data-action="cancel-order"]');
  cancelButtons.forEach((button) => {
    button.addEventListener('click', (e) => {
      e.preventDefault();
      const orderId = button.getAttribute('data-order-id');
      cancelOrder(orderId, button);
    });
  });

  // Attach event listeners to delete buttons
  const deleteButtons = document.querySelectorAll('[data-action="delete-order"]');
  deleteButtons.forEach((button) => {
    button.addEventListener('click', (e) => {
      e.preventDefault();
      const orderId = button.getAttribute('data-order-id');
      deleteOrder(orderId, button);
    });
  });
});

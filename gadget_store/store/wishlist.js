/**
 * wishlist.js
 * Handles AJAX toggling for the wishlist feature using the Fetch API.
 */

function getCookie(name) {
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

document.addEventListener('DOMContentLoaded', function() {
    const wishlistButtons = document.querySelectorAll('.wishlist-toggle');

    wishlistButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const productId = this.dataset.productId;
            const icon = this.querySelector('i');
            const url = `/wishlist/toggle/${productId}/`;

            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest',
                },
            })
            .then(response => {
                // If the user isn't logged in, Django might redirect (302) to login.
                // We check if the response redirected to a login page.
                if (response.redirected && response.url.includes('login')) {
                    window.location.href = response.url;
                    return;
                }
                return response.json();
            })
            .then(data => {
                if (data && data.success) {
                    if (data.is_wishlisted) {
                        // Item added: Fill the heart and color it red
                        icon.classList.replace('bi-heart', 'bi-heart-fill');
                        icon.classList.add('text-danger');
                    } else {
                        // Item removed: Outline heart and remove color
                        icon.classList.replace('bi-heart-fill', 'bi-heart');
                        icon.classList.remove('text-danger');
                    }
                }
            })
            .catch(error => console.error('Wishlist AJAX Error:', error));
        });
    });
});
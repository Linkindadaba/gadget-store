/**
 * F.B Nation - Live Search Suggestions
 */
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.querySelector('#main-search');
    const resultsDiv = document.querySelector('#search-results');

    if (!searchInput || !resultsDiv) return;

    searchInput.addEventListener('input', async (e) => {
        const query = e.target.value;
        if (query.length < 2) {
            resultsDiv.classList.add('d-none');
            return;
        }

        try {
            const response = await fetch(`/search-suggestions/?q=${encodeURIComponent(query)}`);
            const data = await response.json();

            if (data.results.length > 0) {
                let html = '<div class="list-group shadow-lg border-0 rounded-md overflow-hidden">';
                data.results.forEach(item => {
                    html += `
                        <a href="${item.url}" class="list-group-item list-group-item-action d-flex align-items-center p-3 border-0">
                            <img src="${item.image || '/static/images/placeholder.png'}" class="me-3 rounded" style="width: 40px; height: 40px; object-fit: contain;">
                            <div>
                                <div class="fw-bold text-dark">${item.name}</div>
                                <div class="text-primary small">GHS ${item.price.toFixed(2)}</div>
                            </div>
                        </a>`;
                });
                html += '</div>';
                resultsDiv.innerHTML = html;
                resultsDiv.classList.remove('d-none');
            } else {
                resultsDiv.classList.add('d-none');
            }
        } catch (error) {
            console.error('Search error:', error);
        }
    });

    // Close results when clicking outside
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !resultsDiv.contains(e.target)) {
            resultsDiv.classList.add('d-none');
        }
    });
});

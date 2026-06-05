/*dument.addEventLisMdocument.querySelectorAll('.messagelist li');
    messages.forEach(msg => {
    });

    // 2. Add loading state to Save buttons
    const saveButtons = document.querySelectorAll('.submit-row input[type="submit"]');
    saveButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const originalText = this.value;
            this.value = 'Processing...';
            this.classList.add('opacity-50');
        });
    });
 
});
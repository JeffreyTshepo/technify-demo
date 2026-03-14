// ========================================
// CHECKOUT PAGE - Django Version
// ========================================

document.addEventListener('DOMContentLoaded', function() {
    setupFormValidation();
});

// ========================================
// FORM VALIDATION
// ========================================
function setupFormValidation() {
    const form = document.getElementById('checkoutForm');
    
    if (form) {
        // Real-time validation only
        const requiredFields = form.querySelectorAll('[required]');
        requiredFields.forEach(field => {
            field.addEventListener('input', function() {
                if (this.value.trim()) {
                    this.style.borderColor = 'var(--input-border)';
                } else {
                    this.style.borderColor = 'var(--danger-color)';
                }
            });
        });
    }
}

// ========================================
// NOTIFICATION
// ========================================
function showNotification(message, type = 'success') {
    const existing = document.querySelector('.notification');
    if (existing) existing.remove();

    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        bottom: 30px;
        right: 30px;
        background: ${type === 'error' ? 'var(--danger-color)' : 'var(--primary-color)'};
        color: white;
        padding: 15px 25px;
        border-radius: 50px;
        font-weight: 600;
        box-shadow: var(--shadow-lg);
        z-index: 10000;
        animation: slideUp 0.3s ease;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

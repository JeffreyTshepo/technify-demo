// ========================================
// SHOPPING CART PAGE - Django Version
// ========================================

document.addEventListener('DOMContentLoaded', function() {
    setupCartControls();
});

// ========================================
// CART CONTROLS
// ========================================
function setupCartControls() {
    // Decrease quantity buttons
    document.querySelectorAll('.decrease-qty').forEach(button => {
        button.addEventListener('click', function() {
            const productId = this.dataset.productId;
            const qtyDisplay = this.closest('.qty-controls').querySelector('.qty-display');
            let currentQty = parseInt(qtyDisplay.textContent);
            
            if (currentQty > 1) {
                updateCartQuantity(productId, currentQty - 1);
            }
        });
    });

    // Increase quantity buttons
    document.querySelectorAll('.increase-qty').forEach(button => {
        button.addEventListener('click', function() {
            const productId = this.dataset.productId;
            const qtyDisplay = this.closest('.qty-controls').querySelector('.qty-display');
            let currentQty = parseInt(qtyDisplay.textContent);
            
            if (currentQty < 10) {
                updateCartQuantity(productId, currentQty + 1);
            }
        });
    });

    // Remove buttons
    document.querySelectorAll('.removeBtn').forEach(button => {
        button.addEventListener('click', function() {
            const productId = this.dataset.productId;
            removeFromCart(productId);
        });
    });
}

// ========================================
// UPDATE CART QUANTITY
// ========================================
function updateCartQuantity(productId, quantity) {
    fetch(`/update-cart/${productId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken
        },
        body: `quantity=${quantity}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Reload page to update totals
            window.location.reload();
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

// ========================================
// REMOVE FROM CART
// ========================================
function removeFromCart(productId) {
    if (confirm('Remove this item from your cart?')) {
        fetch(`/remove-from-cart/${productId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reload page
                window.location.reload();
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }
}
// ========================================
// PRODUCT DETAIL PAGE - Django Version
// ========================================

let currentImageIndex = 0;

document.addEventListener('DOMContentLoaded', function() {
    setupImageGallery();
    setupQuantityControls();
    setupAddToCart();
});

// ========================================
// IMAGE GALLERY & ZOOM
// ========================================
function setupImageGallery() {
    const mainImg = document.getElementById('imgMain');
    const thumbnails = document.querySelectorAll('.thumbnail');
    const modal = document.getElementById('imageModal');
    const modalImg = document.getElementById('modalImage');
    const closeModal = document.querySelector('.close-modal');
    const zoomBtn = document.getElementById('zoomBtn');
    const prevBtn = document.getElementById('prevImage');
    const nextBtn = document.getElementById('nextImage');

    // Thumbnail clicks
    thumbnails.forEach((thumb, index) => {
        thumb.addEventListener('click', function() {
            currentImageIndex = index;
            mainImg.src = this.src;
            
            thumbnails.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
        });
    });

    // Zoom functionality
    const openModal = () => {
        modal.classList.add('active');
        modal.style.display = 'flex';
        modalImg.src = mainImg.src;
        document.body.style.overflow = 'hidden';
    };

    const closeModalFn = () => {
        modal.classList.remove('active');
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    };

    if (zoomBtn) zoomBtn.addEventListener('click', openModal);
    if (mainImg) mainImg.addEventListener('click', openModal);
    if (closeModal) closeModal.addEventListener('click', closeModalFn);
    
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModalFn();
        });
    }

    // Modal navigation
    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            currentImageIndex = (currentImageIndex - 1 + thumbnails.length) % thumbnails.length;
            const newSrc = thumbnails[currentImageIndex].src;
            modalImg.src = newSrc;
            mainImg.src = newSrc;
            updateActiveThumbnail();
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            currentImageIndex = (currentImageIndex + 1) % thumbnails.length;
            const newSrc = thumbnails[currentImageIndex].src;
            modalImg.src = newSrc;
            mainImg.src = newSrc;
            updateActiveThumbnail();
        });
    }

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
        if (!modal.classList.contains('active')) return;
        
        if (e.key === 'Escape') closeModalFn();
        if (e.key === 'ArrowLeft' && prevBtn) prevBtn.click();
        if (e.key === 'ArrowRight' && nextBtn) nextBtn.click();
    });
}

function updateActiveThumbnail() {
    const thumbnails = document.querySelectorAll('.thumbnail');
    thumbnails.forEach((thumb, index) => {
        thumb.classList.toggle('active', index === currentImageIndex);
    });
}

// ========================================
// QUANTITY CONTROLS
// ========================================
function setupQuantityControls() {
    const qtyInput = document.getElementById('qtyInput');
    const decreaseBtn = document.getElementById('decreaseQty');
    const increaseBtn = document.getElementById('increaseQty');

    if (decreaseBtn) {
        decreaseBtn.addEventListener('click', () => {
            let qty = parseInt(qtyInput.value);
            if (qty > 1) {
                qtyInput.value = qty - 1;
            }
        });
    }

    if (increaseBtn) {
        increaseBtn.addEventListener('click', () => {
            let qty = parseInt(qtyInput.value);
            if (qty < 10) {
                qtyInput.value = qty + 1;
            }
        });
    }
}

// ========================================
// ADD TO CART
// ========================================
function setupAddToCart() {
    const addToCartBtn = document.getElementById('addToCartBtn');
    const qtyInput = document.getElementById('qtyInput');

    if (addToCartBtn) {
        addToCartBtn.addEventListener('click', function() {
            const productId = this.dataset.productId;
            const quantity = qtyInput ? parseInt(qtyInput.value) : 1;

            fetch(`/add-to-cart/${productId}/`, {
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
                    document.getElementById('cartCount').textContent = data.cart_count;
                    showNotification(data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Error adding to cart', 'error');
            });
        });
    }
}

// ========================================
// NOTIFICATION
// ========================================
function showNotification(message) {
    const existing = document.querySelector('.notification');
    if (existing) existing.remove();

    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        bottom: 30px;
        right: 30px;
        background: var(--primary-color);
        color: var(--button-text);
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
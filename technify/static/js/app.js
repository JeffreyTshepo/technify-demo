// ========================================
// HOMEPAGE JAVASCRIPT - COMPLETE FILE
// File: static/js/app.js
// ========================================

document.addEventListener('DOMContentLoaded', function() {
    initializeStoreSwitcher();
    setupAddToCart();
    initializeMobileNavigation();
    initializeCategoryScroll();
    setupResponsiveListeners();
    initializeTouchOptimizations();
});

// ========================================
// STORE MODE SWITCHER
// ========================================
function initializeStoreSwitcher() {
    const modeButtons = document.querySelectorAll('.mode-btn');
    
    modeButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const mode = this.dataset.mode;
            
            // Add loading state
            this.style.opacity = '0.6';
            this.style.pointerEvents = 'none';
            
            // Send AJAX request to set store mode
            fetch(`/set-store-mode/${mode}/`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show transition feedback
                    showNotification(`Switching to ${mode} mode...`, 'info');
                    
                    // Smooth reload with fade effect
                    document.body.style.opacity = '0';
                    setTimeout(() => {
                        window.location.reload();
                    }, 300);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.style.opacity = '1';
                this.style.pointerEvents = 'auto';
                showNotification('Failed to switch mode', 'error');
            });
        });
    });
}

// ========================================
// MOBILE NAVIGATION HANDLER
// ========================================
function initializeMobileNavigation() {
    const isMobile = window.innerWidth <= 768;
    
    if (isMobile) {
        // Smooth scroll to top on logo click
        const logo = document.querySelector('.logo');
        if (logo) {
            logo.addEventListener('click', function(e) {
                if (window.location.pathname === this.getAttribute('href')) {
                    e.preventDefault();
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                }
            });
        }
        
        // Optimize search bar for mobile
        const searchInput = document.querySelector('.search-bar input');
        if (searchInput) {
            // Prevent zoom on focus for iOS
            searchInput.addEventListener('focus', function() {
                this.style.fontSize = '16px';
            });
            
            // Clear button for mobile
            if (!document.querySelector('.search-clear')) {
                const clearBtn = document.createElement('button');
                clearBtn.className = 'search-clear';
                clearBtn.innerHTML = '×';
                clearBtn.type = 'button';
                clearBtn.style.cssText = `
                    position: absolute;
                    right: 95px;
                    top: 50%;
                    transform: translateY(-50%);
                    background: transparent;
                    border: none;
                    color: var(--text-color);
                    font-size: 24px;
                    font-weight: 700;
                    opacity: 0;
                    transition: opacity 0.2s;
                    cursor: pointer;
                    padding: 5px 10px;
                `;
                
                searchInput.parentElement.style.position = 'relative';
                searchInput.parentElement.appendChild(clearBtn);
                
                searchInput.addEventListener('input', function() {
                    clearBtn.style.opacity = this.value ? '0.5' : '0';
                });
                
                clearBtn.addEventListener('click', function() {
                    searchInput.value = '';
                    searchInput.focus();
                    this.style.opacity = '0';
                });
            }
        }
    }
}

// ========================================
// CATEGORY SCROLL HANDLER (Mobile)
// ========================================
function initializeCategoryScroll() {
    const categoryNav = document.querySelector('.category-nav');
    const categoryWrapper = document.querySelector('.category-nav-wrapper');
    const isMobile = window.innerWidth <= 768;
    
    if (categoryNav && isMobile) {
        // Scroll active category into view on page load
        const activeBtn = categoryNav.querySelector('.category-btn.active');
        if (activeBtn) {
            setTimeout(() => {
                const scrollLeft = activeBtn.offsetLeft - (window.innerWidth / 2) + (activeBtn.offsetWidth / 2);
                categoryNav.scrollTo({
                    left: Math.max(0, scrollLeft),
                    behavior: 'smooth'
                });
            }, 100);
        }
        
        // Add/remove 'scrolled' class for left fade indicator
        categoryNav.addEventListener('scroll', function() {
            if (categoryWrapper) {
                if (this.scrollLeft > 20) {
                    categoryWrapper.classList.add('scrolled');
                } else {
                    categoryWrapper.classList.remove('scrolled');
                }
            }
        });
        
        // Touch momentum optimization
        let touchStartX = 0;
        let touchStartScrollLeft = 0;
        
        categoryNav.addEventListener('touchstart', function(e) {
            touchStartX = e.touches[0].clientX;
            touchStartScrollLeft = this.scrollLeft;
        }, { passive: true });
        
        categoryNav.addEventListener('touchmove', function(e) {
            const touchX = e.touches[0].clientX;
            const diff = touchStartX - touchX;
            this.scrollLeft = touchStartScrollLeft + diff;
        }, { passive: true });
        
        // Check if scrolled on initial load
        if (categoryWrapper) {
            setTimeout(() => {
                if (categoryNav.scrollLeft > 20) {
                    categoryWrapper.classList.add('scrolled');
                }
            }, 200);
        }
    }
}

// ========================================
// ADD TO CART - Enhanced for Mobile
// ========================================
function setupAddToCart() {
    const addToCartButtons = document.querySelectorAll('.add-to-cart');
    
    addToCartButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const productId = this.dataset.productId;
            const originalText = this.innerHTML;
            
            // Disable button and show loading
            this.disabled = true;
            this.innerHTML = '<span>Adding...</span>';
            this.style.opacity = '0.7';
            
            // Send AJAX request
            fetch(`/add-to-cart/${productId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken
                },
                body: 'quantity=1'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update cart count with animation
                    const cartBadge = document.getElementById('cartCount');
                    if (cartBadge) {
                        cartBadge.style.transform = 'scale(1.3)';
                        cartBadge.textContent = data.cart_count;
                        setTimeout(() => {
                            cartBadge.style.transform = 'scale(1)';
                        }, 200);
                    }
                    
                    // Success feedback
                    this.innerHTML = '<span>✓ Added</span>';
                    this.style.background = 'var(--success-color)';
                    
                    // Show notification
                    showNotification(data.message);
                    
                    // Reset button after delay
                    setTimeout(() => {
                        this.innerHTML = originalText;
                        this.style.opacity = '1';
                        this.style.background = '';
                        this.disabled = false;
                    }, 2000);
                } else {
                    throw new Error(data.message || 'Failed to add to cart');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.innerHTML = originalText;
                this.style.opacity = '1';
                this.disabled = false;
                showNotification(error.message || 'Error adding to cart', 'error');
            });
        });
    });
}

// ========================================
// RESPONSIVE LISTENERS
// ========================================
function setupResponsiveListeners() {
    let resizeTimer;
    let lastWidth = window.innerWidth;
    
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        
        resizeTimer = setTimeout(() => {
            const currentWidth = window.innerWidth;
            
            // Only reinitialize if crossing mobile/desktop breakpoint
            if ((lastWidth <= 768 && currentWidth > 768) || 
                (lastWidth > 768 && currentWidth <= 768)) {
                
                // Reinitialize components
                initializeMobileNavigation();
                initializeCategoryScroll();
                initializeTouchOptimizations();
                
                lastWidth = currentWidth;
            }
        }, 250);
    });
    
    // Handle orientation changes
    window.addEventListener('orientationchange', function() {
        setTimeout(() => {
            initializeMobileNavigation();
            initializeCategoryScroll();
        }, 300);
    });
}

// ========================================
// TOUCH OPTIMIZATIONS
// ========================================
function initializeTouchOptimizations() {
    const isMobile = window.innerWidth <= 768;
    
    if (isMobile) {
        // Improve product card touch feedback
        const productCards = document.querySelectorAll('.product-card');
        productCards.forEach(card => {
            card.addEventListener('touchstart', function() {
                this.style.transform = 'scale(0.98)';
            }, { passive: true });
            
            card.addEventListener('touchend', function() {
                this.style.transform = '';
            }, { passive: true });
        });
        
        // Prevent double-tap zoom on buttons
        const buttons = document.querySelectorAll('button, .btn, .mode-btn, .category-btn');
        buttons.forEach(btn => {
            btn.addEventListener('touchend', function(e) {
                e.preventDefault();
                this.click();
            });
        });
        
        // Improve scroll performance
        if ('scrollRestoration' in history) {
            history.scrollRestoration = 'manual';
        }
    }
}

// ========================================
// NOTIFICATION SYSTEM
// ========================================
function showNotification(message, type = 'success') {
    // Remove existing notification
    const existing = document.querySelector('.notification');
    if (existing) existing.remove();
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    // Icon based on type
    const icons = {
        success: '✓',
        error: '⚠',
        info: 'ℹ'
    };
    
    const icon = document.createElement('span');
    icon.textContent = icons[type] || icons.success;
    icon.style.cssText = `
        margin-right: 10px;
        font-size: 18px;
    `;
    
    notification.insertBefore(icon, notification.firstChild);
    
    // Responsive positioning
    const isMobile = window.innerWidth <= 768;
    
    notification.style.cssText = `
        position: fixed;
        ${isMobile ? 'bottom: 20px; left: 50%; transform: translateX(-50%);' : 'bottom: 30px; right: 30px;'}
        background: ${type === 'error' ? 'var(--danger-color)' : type === 'info' ? 'var(--secondary-color)' : 'var(--success-color)'};
        color: white;
        padding: ${isMobile ? '12px 20px' : '15px 25px'};
        border-radius: 50px;
        font-weight: 600;
        font-size: ${isMobile ? '14px' : '15px'};
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        z-index: 10000;
        animation: slideUp 0.3s ease;
        display: flex;
        align-items: center;
        max-width: ${isMobile ? '90%' : '400px'};
        text-align: center;
    `;
    
    document.body.appendChild(notification);
    
    // Auto dismiss
    setTimeout(() => {
        notification.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
    
    // Dismiss on tap (mobile)
    if (isMobile) {
        notification.addEventListener('click', function() {
            this.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => this.remove(), 300);
        });
    }
}

// ========================================
// ANIMATIONS
// ========================================
const style = document.createElement('style');
style.textContent = `
    @keyframes slideUp {
        from {
            opacity: 0;
            transform: translateY(20px) ${window.innerWidth <= 768 ? 'translateX(-50%)' : ''};
        }
        to {
            opacity: 1;
            transform: translateY(0) ${window.innerWidth <= 768 ? 'translateX(-50%)' : ''};
        }
    }
    
    @keyframes fadeOut {
        from {
            opacity: 1;
        }
        to {
            opacity: 0;
        }
    }
    
    .notification {
        animation: slideUp 0.3s ease !important;
    }
`;
document.head.appendChild(style);

// ========================================
// INITIALIZE ON LOAD
// ========================================
window.addEventListener('load', function() {
    // Fade in page
    document.body.style.opacity = '1';
    document.body.style.transition = 'opacity 0.3s ease';
});

// ========================================
// NETWORK STATUS
// ========================================
window.addEventListener('online', () => {
    showNotification('Back online', 'success');
});

window.addEventListener('offline', () => {
    showNotification('No internet connection', 'error');
});

console.log('✓ Responsive homepage initialized');
console.log(`Device: ${window.innerWidth <= 768 ? 'Mobile' : 'Desktop'}`);
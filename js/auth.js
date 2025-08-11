// Authentication Management
class AuthManager {
    constructor() {
        this.apiUrl = '/api';
        this.currentUser = null;
        this.token = localStorage.getItem('tprc_token');
        this.refreshTimer = null;
    }

    // Check if user is authenticated
    isAuthenticated() {
        const token = localStorage.getItem('tprc_token');
        const expiry = localStorage.getItem('tprc_token_expiry');
        
        if (!token || !expiry) {
            return false;
        }
        
        // Check if token is expired
        if (new Date().getTime() > parseInt(expiry)) {
            this.logout();
            return false;
        }
        
        return true;
    }

    // Login user
    async login(email, password, rememberMe = false) {
        try {
            const response = await fetch(`${this.apiUrl}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email: email,
                    password: password,
                    remember_me: rememberMe
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Login failed');
            }

            // Store authentication data
            localStorage.setItem('tprc_token', data.token);
            localStorage.setItem('tprc_user', JSON.stringify(data.user));
            localStorage.setItem('tprc_company', JSON.stringify(data.company));
            
            // Set token expiry (24 hours or 30 days if remember me)
            const expiryTime = rememberMe ? 
                new Date().getTime() + (30 * 24 * 60 * 60 * 1000) : // 30 days
                new Date().getTime() + (24 * 60 * 60 * 1000); // 24 hours
            
            localStorage.setItem('tprc_token_expiry', expiryTime.toString());

            this.token = data.token;
            this.currentUser = data.user;
            
            // Start token refresh timer
            this.startTokenRefresh();

            return data;
        } catch (error) {
            console.error('Login error:', error);
            throw error;
        }
    }

    // Logout user
    logout() {
        // Clear local storage
        localStorage.removeItem('tprc_token');
        localStorage.removeItem('tprc_user');
        localStorage.removeItem('tprc_company');
        localStorage.removeItem('tprc_token_expiry');
        
        // Clear instance variables
        this.token = null;
        this.currentUser = null;
        
        // Stop token refresh
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
        
        // Notify server of logout
        fetch(`${this.apiUrl}/auth/logout`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json'
            }
        }).catch(error => {
            console.error('Logout error:', error);
        });

        // Redirect to login
        window.location.href = 'index.html';
    }

    // Get current user
    getCurrentUser() {
        if (this.currentUser) {
            return this.currentUser;
        }
        
        const userStr = localStorage.getItem('tprc_user');
        if (userStr) {
            this.currentUser = JSON.parse(userStr);
            return this.currentUser;
        }
        
        return null;
    }

    // Get current company
    getCurrentCompany() {
        const companyStr = localStorage.getItem('tprc_company');
        if (companyStr) {
            return JSON.parse(companyStr);
        }
        return null;
    }

    // Get authorization token
    getToken() {
        return this.token || localStorage.getItem('tprc_token');
    }

    // Refresh token
    async refreshToken() {
        try {
            const response = await fetch(`${this.apiUrl}/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.getToken()}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error('Token refresh failed');
            }

            const data = await response.json();
            
            // Update stored token
            localStorage.setItem('tprc_token', data.token);
            this.token = data.token;
            
            // Update expiry
            const expiryTime = new Date().getTime() + (24 * 60 * 60 * 1000); // 24 hours
            localStorage.setItem('tprc_token_expiry', expiryTime.toString());

            return data.token;
        } catch (error) {
            console.error('Token refresh error:', error);
            this.logout();
            throw error;
        }
    }

    // Start automatic token refresh
    startTokenRefresh() {
        // Refresh token every 23 hours
        this.refreshTimer = setInterval(() => {
            this.refreshToken().catch(error => {
                console.error('Automatic token refresh failed:', error);
            });
        }, 23 * 60 * 60 * 1000); // 23 hours
    }

    // Reset password
    async resetPassword(email) {
        try {
            const response = await fetch(`${this.apiUrl}/auth/reset-password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email: email })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Password reset failed');
            }

            return data;
        } catch (error) {
            console.error('Password reset error:', error);
            throw error;
        }
    }

    // Change password
    async changePassword(currentPassword, newPassword) {
        try {
            const response = await fetch(`${this.apiUrl}/auth/change-password`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.getToken()}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Password change failed');
            }

            return data;
        } catch (error) {
            console.error('Password change error:', error);
            throw error;
        }
    }

    // Get authenticated fetch headers
    getAuthHeaders() {
        const headers = {
            'Content-Type': 'application/json',
        };
        
        const token = this.getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        return headers;
    }

    // Make authenticated API request
    async authenticatedFetch(url, options = {}) {
        const headers = {
            ...this.getAuthHeaders(),
            ...(options.headers || {})
        };

        const response = await fetch(url, {
            ...options,
            headers
        });

        // Handle token expiry
        if (response.status === 401) {
            this.logout();
            throw new Error('Authentication expired');
        }

        return response;
    }
}

// Create global auth manager instance
const authManager = new AuthManager();

// Global authentication functions
function isAuthenticated() {
    return authManager.isAuthenticated();
}

function getCurrentUser() {
    return authManager.getCurrentUser();
}

function getCurrentCompany() {
    return authManager.getCurrentCompany();
}

function logout() {
    authManager.logout();
}

// Handle login form submission
async function handleLogin(event) {
    event.preventDefault();
    
    const form = event.target;
    const email = form.email.value;
    const password = form.password.value;
    const rememberMe = form.querySelector('#remember-me').checked;
    
    const loginBtn = document.getElementById('login-btn');
    const errorDiv = document.getElementById('login-error');
    const errorMessage = document.getElementById('error-message');
    
    // Show loading state
    loginBtn.disabled = true;
    loginBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Signing In...';
    errorDiv.classList.add('d-none');
    
    try {
        await authManager.login(email, password, rememberMe);
        
        // Redirect to dashboard
        window.location.href = 'dashboard.html';
    } catch (error) {
        // Show error message
        errorMessage.textContent = error.message;
        errorDiv.classList.remove('d-none');
        
        // Reset button
        loginBtn.disabled = false;
        loginBtn.innerHTML = '<i class="fas fa-sign-in-alt me-2"></i>Sign In';
    }
}

// Handle forgot password
async function handleForgotPassword() {
    const email = document.getElementById('email').value;
    
    if (!email) {
        alert('Please enter your email address first');
        return;
    }
    
    try {
        await authManager.resetPassword(email);
        alert('Password reset instructions have been sent to your email address.');
    } catch (error) {
        alert('Error sending password reset: ' + error.message);
    }
}

// Initialize authentication on page load
document.addEventListener('DOMContentLoaded', function() {
    // Check if user is already authenticated and redirect if needed
    if (window.location.pathname.includes('index.html') && isAuthenticated()) {
        window.location.href = 'dashboard.html';
    }
    
    // Setup forgot password link
    const forgotPasswordLink = document.getElementById('forgot-password');
    if (forgotPasswordLink) {
        forgotPasswordLink.addEventListener('click', function(e) {
            e.preventDefault();
            handleForgotPassword();
        });
    }
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        authManager,
        isAuthenticated,
        getCurrentUser,
        getCurrentCompany,
        logout,
        handleLogin
    };
}

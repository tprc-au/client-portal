// HubSpot API Integration
class HubSpotAPI {
    constructor() {
        this.baseUrl = '/api/hubspot';
        this.authManager = authManager;
    }

    // Generic API request method
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        try {
            const response = await this.authManager.authenticatedFetch(url, {
                method: 'GET',
                ...options
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`HubSpot API Error (${endpoint}):`, error);
            throw error;
        }
    }

    // Get user profile and company information
    async getUserProfile() {
        return await this.request('/user/profile');
    }

    // Get company details
    async getCompanyDetails(companyId) {
        return await this.request(`/companies/${companyId}`);
    }

    // Get company profile with all details
    async getCompanyProfile() {
        return await this.request('/company/profile');
    }

    // Get job orders for the current company
    async getJobOrders(filters = {}) {
        const params = new URLSearchParams(filters);
        return await this.request(`/job-orders?${params}`);
    }

    // Get specific job order details
    async getJobOrder(jobOrderId) {
        return await this.request(`/job-orders/${jobOrderId}`);
    }

    // Get candidates for a job order
    async getCandidates(jobOrderId, filters = {}) {
        const params = new URLSearchParams(filters);
        return await this.request(`/job-orders/${jobOrderId}/candidates?${params}`);
    }

    // Get specific candidate details
    async getCandidate(candidateId) {
        return await this.request(`/candidates/${candidateId}`);
    }

    // Get candidate documents
    async getCandidateDocuments(candidateId) {
        return await this.request(`/candidates/${candidateId}/documents`);
    }

    // Get candidate assessments/test results
    async getCandidateAssessments(candidateId) {
        return await this.request(`/candidates/${candidateId}/assessments`);
    }

    // Submit candidate action (approve/reject/reserve)
    async submitCandidateAction(candidateId, actionData) {
        return await this.request(`/candidates/${candidateId}/actions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(actionData)
        });
    }

    // Trigger workflow (for advanced integrations)
    async triggerWorkflow(workflowType, data) {
        return await this.request('/workflows/trigger', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                workflowType,
                data
            })
        });
    }

    // Submit candidate action (approve, reject, interview)
    async submitCandidateAction(actionData) {
        return await this.request('/candidates/action', {
            method: 'POST',
            body: JSON.stringify(actionData)
        });
    }

    // Get dashboard statistics
    async getDashboardStats() {
        return await this.request('/dashboard/stats');
    }

    // Get recent activity
    async getRecentActivity(limit = 10) {
        return await this.request(`/activity/recent?limit=${limit}`);
    }

    // Document management
    async uploadDocument(formData) {
        return await this.authManager.authenticatedFetch(`${this.baseUrl}/documents/upload`, {
            method: 'POST',
            body: formData // FormData object
        }).then(response => {
            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }
            return response.json();
        });
    }

    // Get company documents
    async getCompanyDocuments(category = null) {
        const params = category ? `?category=${category}` : '';
        return await this.request(`/documents${params}`);
    }

    // Delete document
    async deleteDocument(documentId) {
        return await this.request(`/documents/${documentId}`, {
            method: 'DELETE'
        });
    }

    // Save additional company information
    async saveAdditionalInfo(data) {
        return await this.request('/companies/additional-info', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    // Support ticket submission
    async submitSupportTicket(ticketData) {
        return await this.request('/support/tickets', {
            method: 'POST',
            body: JSON.stringify(ticketData)
        });
    }

    // Get support tickets for the company
    async getSupportTickets() {
        return await this.request('/support/tickets');
    }

    // Get knowledge base articles
    async getKnowledgeBaseArticles(searchTerm = '') {
        const params = searchTerm ? `?search=${encodeURIComponent(searchTerm)}` : '';
        return await this.request(`/support/kb${params}`);
    }

    // Search functionality
    async searchJobOrders(searchTerm) {
        return await this.request(`/search/job-orders?q=${encodeURIComponent(searchTerm)}`);
    }

    async searchCandidates(searchTerm, jobOrderId = null) {
        const params = new URLSearchParams({ q: searchTerm });
        if (jobOrderId) params.append('job_order_id', jobOrderId);
        return await this.request(`/search/candidates?${params}`);
    }

    // Candidate documents
    async getCandidateDocuments(candidateId) {
        try {
            return await this.request(`/candidates/${candidateId}/documents`);
        } catch (error) {
            console.error(`Error getting candidate documents for ${candidateId}:`, error);
            return []; // Return empty array on error
        }
    }

    // Candidate assessments
    async getCandidateAssessments(candidateId) {
        try {
            return await this.request(`/candidates/${candidateId}/assessments`);
        } catch (error) {
            console.error(`Error getting candidate assessments for ${candidateId}:`, error);
            return { 
                technical_scores: null, 
                personality: null, 
                links: null 
            }; // Return empty structure on error
        }
    }

    // Workflow triggers
    async triggerWorkflow(workflowType, data) {
        return await this.request('/workflows/trigger', {
            method: 'POST',
            body: JSON.stringify({
                workflow_type: workflowType,
                data: data
            })
        });
    }

    // Interview scheduling
    async scheduleInterview(candidateId, interviewData) {
        return await this.request(`/candidates/${candidateId}/interview`, {
            method: 'POST',
            body: JSON.stringify(interviewData)
        });
    }

    // Assessment/Scorecard management
    async getAssessment(assessmentId) {
        return await this.request(`/assessments/${assessmentId}`);
    }

    async submitAssessment(assessmentId, assessmentData) {
        return await this.request(`/assessments/${assessmentId}`, {
            method: 'PUT',
            body: JSON.stringify(assessmentData)
        });
    }

    // Notifications
    async getNotifications(unreadOnly = false) {
        const params = unreadOnly ? '?unread_only=true' : '';
        return await this.request(`/notifications${params}`);
    }

    async markNotificationRead(notificationId) {
        return await this.request(`/notifications/${notificationId}/read`, {
            method: 'PUT'
        });
    }

    // File management
    async getFileUrl(fileId) {
        return await this.request(`/files/${fileId}/url`);
    }

    async downloadFile(fileId) {
        const response = await this.authManager.authenticatedFetch(`${this.baseUrl}/files/${fileId}/download`);
        
        if (!response.ok) {
            throw new Error(`Download failed: ${response.statusText}`);
        }
        
        return response.blob();
    }

    // Analytics and reporting
    async getJobOrderAnalytics(jobOrderId) {
        return await this.request(`/analytics/job-orders/${jobOrderId}`);
    }

    async getCompanyAnalytics(dateRange = '30d') {
        return await this.request(`/analytics/company?range=${dateRange}`);
    }

    // Bulk operations
    async bulkActionCandidates(candidateIds, action, actionData) {
        return await this.request('/candidates/bulk-action', {
            method: 'POST',
            body: JSON.stringify({
                candidate_ids: candidateIds,
                action: action,
                data: actionData
            })
        });
    }

    // Export functionality
    async exportJobOrderData(jobOrderId, format = 'csv') {
        const response = await this.authManager.authenticatedFetch(
            `${this.baseUrl}/job-orders/${jobOrderId}/export?format=${format}`
        );
        
        if (!response.ok) {
            throw new Error(`Export failed: ${response.statusText}`);
        }
        
        return response.blob();
    }

    async exportCandidateData(candidateIds, format = 'csv') {
        const response = await this.authManager.authenticatedFetch(`${this.baseUrl}/candidates/export?format=${format}`, {
            method: 'POST',
            body: JSON.stringify({ candidate_ids: candidateIds })
        });
        
        if (!response.ok) {
            throw new Error(`Export failed: ${response.statusText}`);
        }
        
        return response.blob();
    }
}

// Create global HubSpot API instance
const hubspotAPI = new HubSpotAPI();

// Utility functions for common operations
async function loadUserProfile() {
    try {
        const profile = await hubspotAPI.getUserProfile();
        
        // Update user name in navbar
        const userNameElements = document.querySelectorAll('#user-name');
        userNameElements.forEach(element => {
            element.textContent = profile.user.name || profile.user.email;
        });

        // Update company name
        const companyNameElements = document.querySelectorAll('#company-name');
        companyNameElements.forEach(element => {
            element.textContent = profile.company.name;
        });

        return profile;
    } catch (error) {
        console.error('Error loading user profile:', error);
        showError('Failed to load user profile');
        return null;
    }
}

async function loadStatistics() {
    try {
        const stats = await hubspotAPI.getDashboardStats();
        
        // Update stat cards
        document.getElementById('active-jobs-count').textContent = stats.active_jobs || 0;
        document.getElementById('candidates-count').textContent = stats.available_candidates || 0;
        document.getElementById('pending-reviews-count').textContent = stats.pending_reviews || 0;
        document.getElementById('selections-count').textContent = stats.selections_made || 0;

        return stats;
    } catch (error) {
        console.error('Error loading statistics:', error);
        // Set counts to 0 on error
        document.getElementById('active-jobs-count').textContent = '0';
        document.getElementById('candidates-count').textContent = '0';
        document.getElementById('pending-reviews-count').textContent = '0';
        document.getElementById('selections-count').textContent = '0';
        return null;
    }
}

async function loadJobOrders(filters = {}) {
    try {
        const jobOrders = await hubspotAPI.getJobOrders(filters);
        const tableBody = document.getElementById('job-orders-table');
        
        if (!tableBody) return jobOrders;

        if (jobOrders.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-4">
                        <i class="fas fa-briefcase fa-2x text-muted mb-2"></i>
                        <p class="mb-0">No job orders found</p>
                    </td>
                </tr>
            `;
            return jobOrders;
        }

        tableBody.innerHTML = jobOrders.map(job => `
            <tr>
                <td>
                    <strong>${escapeHtml(job.title)}</strong>
                    <br>
                    <small class="text-muted">${escapeHtml(job.reference || '')}</small>
                </td>
                <td>${escapeHtml(job.position_type || 'N/A')}</td>
                <td>${escapeHtml(job.location || 'N/A')}</td>
                <td>
                    <span class="badge bg-info">${job.candidate_count || 0} candidates</span>
                </td>
                <td>
                    <span class="status-badge status-${job.status.toLowerCase().replace(' ', '-')}">${job.status}</span>
                </td>
                <td>${formatDate(job.created_date)}</td>
                <td>
                    <div class="btn-group" role="group">
                        <a href="job-order.html?id=${job.id}" class="btn btn-outline-primary btn-sm">
                            <i class="fas fa-eye"></i>
                        </a>
                        <button class="btn btn-outline-info btn-sm" onclick="showJobDetails(${job.id})">
                            <i class="fas fa-info-circle"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

        return jobOrders;
    } catch (error) {
        console.error('Error loading job orders:', error);
        const tableBody = document.getElementById('job-orders-table');
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-4 text-danger">
                        <i class="fas fa-exclamation-triangle fa-2x mb-2"></i>
                        <p class="mb-0">Error loading job orders: ${error.message}</p>
                    </td>
                </tr>
            `;
        }
        return [];
    }
}

async function loadRecentActivity() {
    try {
        const activities = await hubspotAPI.getRecentActivity();
        const activityDiv = document.getElementById('recent-activity');
        
        if (!activityDiv) return activities;

        if (activities.length === 0) {
            activityDiv.innerHTML = `
                <div class="text-center py-3 text-muted">
                    <i class="fas fa-history fa-2x mb-2"></i>
                    <p class="mb-0">No recent activity</p>
                </div>
            `;
            return activities;
        }

        activityDiv.innerHTML = activities.map(activity => `
            <div class="activity-item d-flex align-items-start mb-3">
                <div class="activity-icon me-3">
                    <i class="fas ${getActivityIcon(activity.type)} text-${getActivityColor(activity.type)}"></i>
                </div>
                <div class="activity-content flex-grow-1">
                    <p class="mb-1">${escapeHtml(activity.description)}</p>
                    <small class="text-muted">${formatRelativeTime(activity.timestamp)}</small>
                </div>
            </div>
        `).join('');

        return activities;
    } catch (error) {
        console.error('Error loading recent activity:', error);
        const activityDiv = document.getElementById('recent-activity');
        if (activityDiv) {
            activityDiv.innerHTML = `
                <div class="text-center py-3 text-danger">
                    <p class="mb-0">Error loading activity: ${error.message}</p>
                </div>
            `;
        }
        return [];
    }
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
}

function formatRelativeTime(dateString) {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    const now = new Date();
    const diffInMs = now - date;
    const diffInHours = Math.floor(diffInMs / (1000 * 60 * 60));
    
    if (diffInHours < 1) return 'Just now';
    if (diffInHours < 24) return `${diffInHours} hours ago`;
    
    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays < 7) return `${diffInDays} days ago`;
    
    return date.toLocaleDateString();
}

function getActivityIcon(type) {
    const icons = {
        'candidate_reviewed': 'fa-user-check',
        'interview_scheduled': 'fa-calendar',
        'document_uploaded': 'fa-file-upload',
        'job_order_created': 'fa-briefcase',
        'candidate_approved': 'fa-thumbs-up',
        'candidate_rejected': 'fa-thumbs-down',
        'default': 'fa-info-circle'
    };
    return icons[type] || icons.default;
}

function getActivityColor(type) {
    const colors = {
        'candidate_reviewed': 'info',
        'interview_scheduled': 'warning',
        'document_uploaded': 'success',
        'job_order_created': 'primary',
        'candidate_approved': 'success',
        'candidate_rejected': 'danger',
        'default': 'secondary'
    };
    return colors[type] || colors.default;
}

function showError(message) {
    console.error(message);
    // You can implement a toast notification or alert here
    if (typeof showAlert === 'function') {
        showAlert('danger', message);
    }
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        HubSpotAPI,
        hubspotAPI,
        loadUserProfile,
        loadStatistics,
        loadJobOrders,
        loadRecentActivity
    };
}

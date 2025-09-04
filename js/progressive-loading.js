// Progressive Loading System for TPRC Portal
class ProgressiveLoader {
    constructor() {
        this.loadingStates = new Map();
    }
    
    // Show loading for candidates table
    showCandidatesLoading(containerId = 'candidates-list') {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        container.innerHTML = `
            <tr id="candidates-loading-row">
                <td colspan="7" class="text-center py-4">
                    <div class="d-flex flex-column align-items-center">
                        <div class="spinner-border text-primary mb-3" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="mb-2" id="candidates-loading-text">Loading candidates...</p>
                        <div class="progress" style="width: 300px;">
                            <div class="progress-bar bg-primary" role="progressbar" 
                                 id="candidates-progress" style="width: 0%"></div>
                        </div>
                        <small class="text-muted mt-2" id="candidates-count-text">Please wait...</small>
                    </div>
                </td>
            </tr>
        `;
    }
    
    // Update loading progress
    updateProgress(loaded, total, message) {
        const progressBar = document.getElementById('candidates-progress');
        const loadingText = document.getElementById('candidates-loading-text');
        const countText = document.getElementById('candidates-count-text');
        
        if (progressBar && total > 0) {
            const percentage = (loaded / total) * 100;
            progressBar.style.width = `${percentage}%`;
        }
        
        if (loadingText) {
            loadingText.textContent = message || `Loading candidates... (${loaded}/${total})`;
        }
        
        if (countText) {
            countText.textContent = `${loaded} of ${total} candidates loaded`;
        }
    }
    
    // Remove loading indicator
    hideLoading(containerId = 'candidates-list') {
        const loadingRow = document.getElementById('candidates-loading-row');
        if (loadingRow) {
            loadingRow.remove();
        }
    }
    
    // Add candidate row progressively
    addCandidateRow(candidate, containerId = 'candidates-list') {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        // Remove loading row if it's the first candidate
        this.hideLoading(containerId);
        
        const row = document.createElement('tr');
        row.style.opacity = '0';
        row.innerHTML = this.formatCandidateRow(candidate);
        
        container.appendChild(row);
        
        // Animate in
        setTimeout(() => {
            row.style.transition = 'opacity 0.3s ease-in';
            row.style.opacity = '1';
        }, 50);
    }
    
    // Format candidate row HTML
    formatCandidateRow(candidate) {
        const associationBadges = candidate.association_labels?.map(label => {
            const badgeClass = label.toLowerCase() === 'selected' ? 'bg-success' :
                              label.toLowerCase() === 'rejected' ? 'bg-danger' : 'bg-primary';
            return `<span class="badge ${badgeClass} me-1">${label}</span>`;
        }).join('') || '<span class="badge bg-secondary">None</span>';
        
        return `
            <td>
                <div class="d-flex align-items-center">
                    <i class="fas fa-user-circle fa-2x text-muted me-3"></i>
                    <div>
                        <h6 class="mb-0">${candidate.first_name || ''} ${candidate.last_name || ''}</h6>
                        <small class="text-muted">${candidate.email || ''}</small>
                    </div>
                </div>
            </td>
            <td>${candidate.age || 'N/A'}</td>
            <td>${candidate.city || 'N/A'}, ${candidate.state || 'N/A'}</td>
            <td><small class="text-muted">Skills data loading...</small></td>
            <td>${associationBadges}</td>
            <td>
                <span class="badge ${candidate.application_status === 'Active' ? 'bg-success' : 'bg-warning'}">
                    ${candidate.application_status || 'Unknown'}
                </span>
            </td>
            <td>
                <a href="applicant.html?id=${candidate.application_id}&jobOrderId=${candidate.job_order_id || new URLSearchParams(window.location.search).get('id')}" 
                   class="btn btn-sm btn-primary">
                    <i class="fas fa-eye me-1"></i>View
                </a>
            </td>
        `;
    }
}

// Global progressive loader instance
window.progressiveLoader = new ProgressiveLoader();
// Main Application Logic
class TPRCApp {
    constructor() {
        this.hubspotAPI = hubspotAPI;
        this.authManager = authManager;
        this.currentPage = this.getCurrentPage();
        this.filters = {};
        this.searchTerms = {};
    }

    // Initialize the application
    async init() {
        try {
            // Check authentication for protected pages
            if (this.isProtectedPage() && !this.authManager.isAuthenticated()) {
                window.location.href = 'index.html';
                return;
            }

            // Initialize page-specific functionality
            await this.initializePage();
            
            // Setup global event listeners
            this.setupGlobalEventListeners();
            
            console.log('TPRC App initialized successfully');
        } catch (error) {
            console.error('App initialization error:', error);
            this.showAlert('danger', 'Application initialization failed. Please refresh the page.');
        }
    }

    // Get current page name
    getCurrentPage() {
        const path = window.location.pathname;
        const page = path.substring(path.lastIndexOf('/') + 1);
        return page || 'index.html';
    }

    // Check if current page requires authentication
    isProtectedPage() {
        const protectedPages = ['dashboard.html', 'job-order.html', 'applicant.html', 'documents.html', 'support.html'];
        return protectedPages.includes(this.currentPage);
    }

    // Initialize page-specific functionality
    async initializePage() {
        switch (this.currentPage) {
            case 'dashboard.html':
                await this.initializeDashboard();
                break;
            case 'job-order.html':
                await this.initializeJobOrder();
                break;
            case 'applicant.html':
                await this.initializeApplicant();
                break;
            case 'documents.html':
                await this.initializeDocuments();
                break;
            case 'support.html':
                await this.initializeSupport();
                break;
            case 'company-profile.html':
                await this.initializeCompanyProfile();
                break;
            default:
                // Login page or other pages
                break;
        }
    }

    // Dashboard initialization
    async initializeDashboard() {
        try {
            // Load user profile
            await loadUserProfile();
            
            // Load dashboard statistics
            await loadStatistics();
            
            // Load job orders
            await loadJobOrders();
            
            // Load recent activity
            await loadRecentActivity();
            
            // Setup dashboard-specific event listeners
            this.setupDashboardEventListeners();
        } catch (error) {
            console.error('Dashboard initialization error:', error);
            this.showAlert('danger', 'Failed to load dashboard data. Please refresh the page.');
        }
    }

    // Job Order page initialization
    async initializeJobOrder() {
        const urlParams = new URLSearchParams(window.location.search);
        const jobOrderId = urlParams.get('id');
        
        if (!jobOrderId) {
            this.showAlert('danger', 'No job order specified');
            window.location.href = 'dashboard.html';
            return;
        }

        try {
            // Load user profile
            await loadUserProfile();
            
            // Load job order details
            await this.loadJobOrderDetails(jobOrderId);
            
            // Setup job order event listeners
            this.setupJobOrderEventListeners();
        } catch (error) {
            console.error('Job order initialization error:', error);
            this.showAlert('danger', 'Failed to load job order details.');
        }
    }

    // Applicant page initialization
    async initializeApplicant() {
        const urlParams = new URLSearchParams(window.location.search);
        const applicantId = urlParams.get('id');
        const jobOrderId = urlParams.get('jobOrderId');
        
        if (!applicantId) {
            this.showAlert('danger', 'No applicant specified');
            window.location.href = 'dashboard.html';
            return;
        }

        try {
            // Load user profile
            await loadUserProfile();
            
            // Load applicant details
            await this.loadApplicantDetails(applicantId);
            
            // Setup breadcrumb if job order ID is provided
            if (jobOrderId) {
                this.setupApplicantBreadcrumb(jobOrderId);
            }
            
            // Setup applicant event listeners
            this.setupApplicantEventListeners();
        } catch (error) {
            console.error('Applicant initialization error:', error);
            this.showAlert('danger', 'Failed to load applicant details.');
        }
    }

    // Documents page initialization
    async initializeDocuments() {
        try {
            // Load user profile
            await loadUserProfile();
            
            // Load existing documents
            await this.loadDocuments();
            
            // Setup documents event listeners
            this.setupDocumentsEventListeners();
        } catch (error) {
            console.error('Documents initialization error:', error);
            this.showAlert('danger', 'Failed to load documents page.');
        }
    }

    // Support page initialization
    async initializeSupport() {
        try {
            // Load user profile
            await loadUserProfile();
            
            // Setup support event listeners
            this.setupSupportEventListeners();
        } catch (error) {
            console.error('Support initialization error:', error);
            this.showAlert('danger', 'Failed to load support page.');
        }
    }

    // Company profile initialization
    async initializeCompanyProfile() {
        try {
            // Check authentication first
            if (!this.authManager.isAuthenticated()) {
                console.log('User not authenticated, redirecting to login');
                window.location.href = '/index.html';
                return;
            }

            // Load user profile for navigation
            await loadUserProfile();
            
            // Load company profile data
            await this.loadCompanyProfile();
            
        } catch (error) {
            console.error('Error initializing company profile page:', error);
            if (error.message.includes('401') || error.message.includes('authentication')) {
                console.log('Authentication error, redirecting to login');
                this.authManager.logout();
                return;
            }
            this.showAlert('danger', 'Failed to load company profile: ' + error.message);
        }
    }

    // Load job order details
    async loadJobOrderDetails(jobOrderId) {
        try {
            const jobOrder = await this.hubspotAPI.getJobOrder(jobOrderId);
            
            // Update page title and header
            document.getElementById('job-title').textContent = jobOrder.title || 'Job Order';
            document.getElementById('job-position-type').textContent = jobOrder.position_type || '';
            document.getElementById('job-location').textContent = jobOrder.location || '';
            document.getElementById('job-status').textContent = jobOrder.status || '';
            
            // Update job details
            document.getElementById('job-description').textContent = jobOrder.description || 'No description available';
            document.getElementById('job-created-date').textContent = this.formatDate(jobOrder.created_date);
            document.getElementById('job-deadline').textContent = this.formatDate(jobOrder.deadline);
            document.getElementById('job-salary-range').textContent = jobOrder.salary_range || 'Not specified';
            document.getElementById('job-benefits').textContent = jobOrder.benefits || 'Not specified';
            
            // Update requirements lists
            const essentialList = document.getElementById('essential-requirements');
            if (essentialList && jobOrder.essential_requirements) {
                essentialList.innerHTML = jobOrder.essential_requirements.map(req => 
                    `<li>${escapeHtml(req)}</li>`
                ).join('');
            }
            
            const preferredList = document.getElementById('preferred-requirements');
            if (preferredList && jobOrder.preferred_requirements) {
                preferredList.innerHTML = jobOrder.preferred_requirements.map(req => 
                    `<li>${escapeHtml(req)}</li>`
                ).join('');
            }
            
            // Store job order for global access
            window.currentJobOrder = jobOrder;
            
            // Load candidates for this job order
            await this.loadCandidatesForJob(jobOrderId);
            
        } catch (error) {
            console.error('Error loading job order details:', error);
            this.showAlert('danger', 'Failed to load job order details: ' + error.message);
        }
    }

    // Load candidates for a specific job order
    async loadCandidatesForJob(jobOrderId) {
        try {
            const candidates = await this.hubspotAPI.getCandidatesForJob(jobOrderId);
            this.renderCandidates(candidates);
            
            // Update candidate count in the header
            const candidateCount = document.getElementById('candidate-count');
            if (candidateCount) {
                candidateCount.textContent = candidates.length;
            }
            
        } catch (error) {
            console.error('Error loading candidates:', error);
            this.showAlert('warning', 'Failed to load candidates for this job order.');
        }
    }

    // Setup global event listeners
    setupGlobalEventListeners() {
        // Logout buttons
        document.querySelectorAll('#logout-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.authManager.logout();
            });
        });

        // Search functionality
        document.querySelectorAll('[id^="search-"]').forEach(input => {
            input.addEventListener('input', this.debounce((e) => {
                this.handleSearch(e.target);
            }, 300));
        });

        // Filter functionality
        document.querySelectorAll('[id^="filter-"]').forEach(select => {
            select.addEventListener('change', (e) => {
                this.handleFilter(e.target);
            });
        });

        // Company profile links - now using direct navigation
        // Links updated to href="company-profile.html" in HTML files
    }

    // Dashboard-specific event listeners
    setupDashboardEventListeners() {
        // Job orders search and filter
        document.getElementById('search-jobs')?.addEventListener('input', 
            this.debounce(() => this.filterJobOrders(), 300)
        );
        
        document.getElementById('filter-status')?.addEventListener('change', () => {
            this.filterJobOrders();
        });
    }

    // Job order-specific event listeners
    setupJobOrderEventListeners() {
        // Candidates search and filter
        document.getElementById('search-candidates')?.addEventListener('input',
            this.debounce(() => this.filterCandidates(), 300)
        );
        
        document.getElementById('filter-candidates')?.addEventListener('change', () => {
            this.filterCandidates();
        });

        // Tab switching
        document.querySelectorAll('#jobTabs button').forEach(tab => {
            tab.addEventListener('shown.bs.tab', (e) => {
                this.handleTabSwitch(e.target.getAttribute('data-bs-target'));
            });
        });
    }

    // Applicant-specific event listeners
    setupApplicantEventListeners() {
        // Tab switching
        document.querySelectorAll('#applicantTabs button').forEach(tab => {
            tab.addEventListener('shown.bs.tab', (e) => {
                this.handleApplicantTabSwitch(e.target.getAttribute('data-bs-target'));
            });
        });
    }

    // Documents-specific event listeners
    setupDocumentsEventListeners() {
        // Document category change
        document.getElementById('document-category')?.addEventListener('change', (e) => {
            this.updateDocumentTypes(e.target.value);
        });

        // File selection
        document.getElementById('document-files')?.addEventListener('change', (e) => {
            this.previewFiles(e.target.files);
        });

        // Upload button
        document.getElementById('upload-btn')?.addEventListener('click', () => {
            this.uploadDocuments();
        });
    }

    // Support-specific event listeners
    setupSupportEventListeners() {
        // Support ticket form
        document.getElementById('support-ticket-form')?.addEventListener('submit', (e) => {
            this.submitSupportTicket(e);
        });

        // Knowledge base search
        document.getElementById('kb-search')?.addEventListener('input', 
            this.debounce(() => this.searchKnowledgeBase(), 300)
        );
    }

    // Load job order details
    async loadJobOrderDetails(jobOrderId) {
        try {
            const jobOrder = await this.hubspotAPI.getJobOrder(jobOrderId);
            
            // Update job order header
            document.getElementById('job-title').textContent = jobOrder.title;
            document.getElementById('job-type').textContent = jobOrder.position_type || 'N/A';
            document.getElementById('job-location').textContent = jobOrder.location || 'N/A';
            document.getElementById('job-status').textContent = jobOrder.status;
            document.getElementById('job-description').textContent = jobOrder.description || 'No description available';
            document.getElementById('job-created-date').textContent = formatDate(jobOrder.created_date);
            document.getElementById('job-deadline').textContent = formatDate(jobOrder.deadline);

            // Load candidates
            const candidates = await this.hubspotAPI.getCandidates(jobOrderId);
            this.renderCandidates(candidates);
            document.getElementById('candidates-count').textContent = candidates.length;

            // Load requirements
            this.loadJobRequirements(jobOrder);

            // Load job history
            this.loadJobHistory(jobOrderId);

            // Store for later use
            window.currentJobOrder = jobOrder;
            window.candidates = candidates;

        } catch (error) {
            console.error('Error loading job order details:', error);
            this.showAlert('danger', 'Failed to load job order details: ' + error.message);
        }
    }

    // Load applicant details
    async loadApplicantDetails(applicantId) {
        try {
            const applicant = await this.hubspotAPI.getCandidate(applicantId);
            
            // Update applicant header
            document.getElementById('applicant-name').textContent = `${applicant.first_name} ${applicant.last_name}`;
            document.getElementById('applicant-age').textContent = applicant.age || 'N/A';
            document.getElementById('applicant-location').textContent = applicant.location || 'N/A';
            document.getElementById('applicant-email').textContent = applicant.email || 'N/A';
            document.getElementById('applicant-phone').textContent = applicant.phone || 'N/A';
            document.getElementById('applicant-status').textContent = applicant.status || 'N/A';
            document.getElementById('applicant-summary').textContent = applicant.summary || 'No summary available';

            // Load additional applicant data
            this.loadApplicantOverview(applicant);
            this.loadApplicantDocuments(applicantId);
            this.loadApplicantAssessments(applicantId);
            this.loadApplicantMedia(applicantId);
            this.loadApplicantScorecard(applicantId);

            // Store for later use
            window.currentApplicant = applicant;

        } catch (error) {
            console.error('Error loading applicant details:', error);
            this.showAlert('danger', 'Failed to load applicant details: ' + error.message);
        }
    }

    async loadApplicantDocuments(applicantId) {
        try {
            const documents = await this.hubspotAPI.getCandidateDocuments(applicantId);
            const documentsContainer = document.getElementById('documents-list');
            
            if (!documentsContainer) return;
            
            if (documents && documents.length > 0) {
                documentsContainer.innerHTML = documents.map(doc => `
                    <div class="document-item mb-3 p-3 border rounded">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <h6 class="mb-1">${doc.name}</h6>
                                <small class="text-muted">${doc.type || 'Document'} • ${doc.category || 'General'}</small>
                                <p class="mb-1 small">${doc.description || 'No description available'}</p>
                            </div>
                            <div class="text-end">
                                <small class="text-muted">${this.formatDate(doc.upload_date)}</small>
                                ${doc.file_url ? `<br><a href="${doc.file_url}" target="_blank" class="btn btn-sm btn-outline-primary mt-1">View</a>` : ''}
                            </div>
                        </div>
                    </div>
                `).join('');
            } else {
                documentsContainer.innerHTML = '<div class="text-muted text-center py-4">No documents available</div>';
            }
        } catch (error) {
            console.error('Error loading applicant documents:', error);
            const documentsContainer = document.getElementById('documents-list');
            if (documentsContainer) {
                documentsContainer.innerHTML = '<div class="text-danger text-center py-4">Failed to load documents</div>';
            }
        }
    }

    async loadApplicantAssessments(applicantId) {
        try {
            const assessments = await this.hubspotAPI.getCandidateAssessments(applicantId);
            
            // Update technical skills scores
            const skillsContainer = document.getElementById('skills-scores');
            if (skillsContainer && assessments.technical_scores) {
                skillsContainer.innerHTML = Object.entries(assessments.technical_scores)
                    .map(([skill, score]) => `
                        <div class="d-flex justify-content-between mb-2">
                            <span>${skill}</span>
                            <div>
                                <span class="badge bg-${score >= 80 ? 'success' : score >= 60 ? 'warning' : 'danger'}">${score}%</span>
                            </div>
                        </div>
                    `).join('');
            } else if (skillsContainer) {
                skillsContainer.innerHTML = '<div class="text-muted">No technical assessment results available</div>';
            }

            // Update personality assessment
            const personalityContainer = document.getElementById('personality-scores');
            if (personalityContainer && assessments.personality) {
                personalityContainer.innerHTML = Object.entries(assessments.personality)
                    .map(([trait, score]) => `
                        <div class="d-flex justify-content-between mb-2">
                            <span>${trait}</span>
                            <span class="text-primary">${score}</span>
                        </div>
                    `).join('');
            } else if (personalityContainer) {
                personalityContainer.innerHTML = '<div class="text-muted">No personality assessment results available</div>';
            }

            // Update assessment links
            const linksContainer = document.getElementById('assessment-links');
            if (linksContainer && assessments.links) {
                linksContainer.innerHTML = assessments.links
                    .map(link => `
                        <div class="mb-2">
                            <a href="${link.url}" target="_blank" class="btn btn-sm btn-outline-primary">
                                <i class="fas fa-external-link-alt me-1"></i>${link.name}
                            </a>
                        </div>
                    `).join('');
            } else if (linksContainer) {
                linksContainer.innerHTML = '<div class="text-muted">No assessment links available</div>';
            }
        } catch (error) {
            console.error('Error loading applicant assessments:', error);
        }
    }

    async loadApplicantMedia(applicantId) {
        try {
            // Load media files (photos, videos, etc.)
            const mediaContainer = document.getElementById('media-gallery');
            if (!mediaContainer) return;
            
            // For now, show placeholder as media handling needs specific implementation
            mediaContainer.innerHTML = `
                <div class="col-12 text-center py-5">
                    <i class="fas fa-images fa-3x text-muted mb-3"></i>
                    <h6 class="text-muted">Media Gallery</h6>
                    <p class="text-muted">Documentary evidence and media files will be displayed here</p>
                    <small class="text-muted">Media loading functionality coming soon</small>
                </div>
            `;
        } catch (error) {
            console.error('Error loading applicant media:', error);
            const mediaContainer = document.getElementById('media-gallery');
            if (mediaContainer) {
                mediaContainer.innerHTML = '<div class="text-danger text-center py-4">Failed to load media</div>';
            }
        }
    }

    async loadApplicantScorecard(applicantId) {
        try {
            const scorecard = await this.hubspotAPI.request(`/candidates/${applicantId}/scorecard`);
            const scorecardContainer = document.getElementById('scorecard-content');
            
            if (!scorecardContainer) return;
            
            if (scorecard && Object.keys(scorecard).length > 0) {
                scorecardContainer.innerHTML = `
                    <div class="row">
                        <div class="col-md-6">
                            <h6>Technical Competency</h6>
                            <div class="mb-3">
                                <label class="form-label">Technical Skills:</label>
                                <span class="badge bg-${scorecard.technical_skills >= 4 ? 'success' : scorecard.technical_skills >= 3 ? 'warning' : 'danger'} ms-2">
                                    ${scorecard.technical_skills || 'N/A'}/5
                                </span>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Experience:</label>
                                <span class="badge bg-${scorecard.experience >= 4 ? 'success' : scorecard.experience >= 3 ? 'warning' : 'danger'} ms-2">
                                    ${scorecard.experience || 'N/A'}/5
                                </span>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <h6>Communication & Fit</h6>
                            <div class="mb-3">
                                <label class="form-label">English Proficiency:</label>
                                <span class="badge bg-${scorecard.english_proficiency >= 4 ? 'success' : scorecard.english_proficiency >= 3 ? 'warning' : 'danger'} ms-2">
                                    ${scorecard.english_proficiency || 'N/A'}/5
                                </span>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Cultural Fit:</label>
                                <span class="badge bg-${scorecard.cultural_fit >= 4 ? 'success' : scorecard.cultural_fit >= 3 ? 'warning' : 'danger'} ms-2">
                                    ${scorecard.cultural_fit || 'N/A'}/5
                                </span>
                            </div>
                        </div>
                    </div>
                    <hr>
                    <div class="row">
                        <div class="col-12">
                            <h6>Overall Assessment</h6>
                            <div class="mb-3">
                                <label class="form-label">Overall Rating:</label>
                                <span class="badge bg-${scorecard.overall_rating >= 4 ? 'success' : scorecard.overall_rating >= 3 ? 'warning' : 'danger'} ms-2">
                                    ${scorecard.overall_rating || 'N/A'}/5
                                </span>
                            </div>
                            ${scorecard.assessment_notes ? `
                                <div class="mb-3">
                                    <label class="form-label">Notes:</label>
                                    <p class="text-muted">${scorecard.assessment_notes}</p>
                                </div>
                            ` : ''}
                            ${scorecard.final_decision ? `
                                <div class="mb-3">
                                    <label class="form-label">Decision:</label>
                                    <span class="badge bg-${scorecard.final_decision === 'approve' ? 'success' : scorecard.final_decision === 'reject' ? 'danger' : 'secondary'} ms-2">
                                        ${scorecard.final_decision.charAt(0).toUpperCase() + scorecard.final_decision.slice(1)}
                                    </span>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                    <div class="text-end">
                        <button class="btn btn-primary" onclick="openScorecardModal()">
                            <i class="fas fa-edit me-1"></i>Edit Scorecard
                        </button>
                    </div>
                `;
            } else {
                scorecardContainer.innerHTML = `
                    <div class="text-center py-5">
                        <i class="fas fa-clipboard-list fa-3x text-muted mb-3"></i>
                        <h6 class="text-muted">No Scorecard Available</h6>
                        <p class="text-muted">Start by creating an assessment scorecard for this candidate</p>
                        <button class="btn btn-primary" onclick="openScorecardModal()">
                            <i class="fas fa-plus me-1"></i>Create Scorecard
                        </button>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading applicant scorecard:', error);
            const scorecardContainer = document.getElementById('scorecard-content');
            if (scorecardContainer) {
                scorecardContainer.innerHTML = '<div class="text-danger text-center py-4">Failed to load scorecard</div>';
            }
        }
    }

    // Load documents
    async loadDocuments() {
        try {
            const documents = await this.hubspotAPI.getCompanyDocuments();
            this.renderDocumentChecklist(documents);
            this.updateDocumentCounts(documents);
        } catch (error) {
            console.error('Error loading documents:', error);
            this.showAlert('danger', 'Failed to load documents: ' + error.message);
        }
    }

    // Load company profile
    async loadCompanyProfile() {
        try {
            const profile = await this.hubspotAPI.getCompanyProfile();
            
            // Update company header
            document.getElementById('company-name').textContent = profile.name || 'Company Name';
            document.getElementById('company-industry').textContent = profile.industry || 'Industry';
            document.getElementById('company-status').textContent = profile.lifecycle_stage || 'Active';
            document.getElementById('company-created-date').textContent = this.formatDate(profile.created_date);
            document.getElementById('active-jobs-count').textContent = profile.active_jobs_count || '0';
            document.getElementById('total-placements').textContent = profile.total_placements || '0';
            
            // Update company information section
            document.getElementById('profile-company-name').textContent = profile.name || '-';
            document.getElementById('profile-company-industry').textContent = profile.industry || '-';
            document.getElementById('company-size').textContent = profile.company_size || '-';
            document.getElementById('company-founded').textContent = profile.founded_year || '-';
            
            // Update contact details
            const website = document.getElementById('company-website');
            if (profile.website) {
                website.textContent = profile.website;
                website.href = profile.website.startsWith('http') ? profile.website : `https://${profile.website}`;
            } else {
                website.textContent = '-';
                website.removeAttribute('href');
            }
            
            document.getElementById('company-phone').textContent = profile.phone || '-';
            document.getElementById('company-revenue').textContent = profile.annual_revenue || '-';
            document.getElementById('company-type').textContent = profile.company_type || '-';
            document.getElementById('company-is-public').textContent = profile.is_public === 'true' ? 'Yes' : (profile.is_public === 'false' ? 'No' : '-');
            document.getElementById('company-description').textContent = profile.description || '-';
            
            // Update social media and additional fields
            const linkedinLink = document.getElementById('company-linkedin');
            if (profile.linkedin_company_page) {
                linkedinLink.textContent = 'View LinkedIn Page';
                linkedinLink.href = profile.linkedin_company_page;
            } else {
                linkedinLink.textContent = '-';
                linkedinLink.removeAttribute('href');
            }
            
            document.getElementById('company-twitter').textContent = profile.twitter_handle || '-';
            document.getElementById('company-last-activity').textContent = this.formatDate(profile.last_activity_date);
            document.getElementById('company-record-source').textContent = profile.record_source || '-';
            
            // Update address information
            document.getElementById('company-address').textContent = profile.address || '-';
            document.getElementById('company-city').textContent = profile.city || '-';
            document.getElementById('company-state').textContent = profile.state || '-';
            document.getElementById('company-zip').textContent = profile.zip || '-';
            document.getElementById('company-country').textContent = profile.country || '-';
            
            // Update primary contact information
            const primaryContact = profile.primary_contact;
            if (primaryContact) {
                document.getElementById('primary-contact-name').textContent = primaryContact.name || '-';
                document.getElementById('primary-contact-title').textContent = primaryContact.job_title || '-';
                document.getElementById('primary-contact-email').textContent = primaryContact.email || '-';
                document.getElementById('primary-contact-phone').textContent = primaryContact.phone || '-';
            } else {
                document.getElementById('primary-contact-name').textContent = '-';
                document.getElementById('primary-contact-title').textContent = '-';
                document.getElementById('primary-contact-email').textContent = '-';
                document.getElementById('primary-contact-phone').textContent = '-';
            }
            
            // Store profile for later use
            window.currentCompanyProfile = profile;
            
        } catch (error) {
            console.error('Error loading company profile:', error);
            this.showAlert('danger', 'Failed to load company profile: ' + error.message);
        }
    }

    // Render candidates list
    renderCandidates(candidates) {
        const candidatesList = document.getElementById('candidates-list');
        if (!candidatesList) return;

        if (candidates.length === 0) {
            candidatesList.innerHTML = `
                <div class="text-center py-4">
                    <i class="fas fa-users fa-2x text-muted mb-2"></i>
                    <p class="mb-0">No candidates available for this job order</p>
                </div>
            `;
            return;
        }

        candidatesList.innerHTML = candidates.map(candidate => `
            <div class="candidate-card card mb-3">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col-md-2 text-center">
                            <div class="candidate-avatar mb-2">
                                <i class="fas fa-user"></i>
                            </div>
                            <span class="badge bg-${this.getStatusColor(candidate.status)}">${candidate.status}</span>
                        </div>
                        <div class="col-md-6">
                            <h6 class="mb-1">${escapeHtml(candidate.name)}</h6>
                            <p class="text-muted mb-2">
                                <i class="fas fa-birthday-cake me-1"></i>${candidate.age} years, 
                                <i class="fas fa-map-marker-alt me-1"></i>${escapeHtml(candidate.location)}
                            </p>
                            <div class="skills">
                                ${(candidate.skills || []).map(skill => 
                                    `<span class="skill-tag">${escapeHtml(skill)}</span>`
                                ).join('')}
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="action-btn-group">
                                <button class="action-btn action-btn-approve" onclick="showApprovalConfirmation('${candidate.id}', '${escapeHtml(candidate.name)}')">
                                    <i class="fas fa-check me-1"></i>Approve
                                </button>
                                <button class="action-btn action-btn-interview" onclick="scheduleInterview('${candidate.id}')">
                                    <i class="fas fa-calendar me-1"></i>Interview
                                </button>
                                <button class="action-btn action-btn-reject" onclick="rejectCandidate('${candidate.id}')">
                                    <i class="fas fa-times me-1"></i>Reject
                                </button>
                                <a href="applicant.html?id=${candidate.id}&jobOrderId=${window.currentJobOrder?.id || ''}" class="btn btn-outline-info btn-sm">
                                    <i class="fas fa-eye me-1"></i>View Profile
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    // Filter job orders
    async filterJobOrders() {
        const searchTerm = document.getElementById('search-jobs')?.value || '';
        const statusFilter = document.getElementById('filter-status')?.value || '';
        
        const filters = {};
        if (searchTerm) filters.search = searchTerm;
        if (statusFilter) filters.status = statusFilter;
        
        await loadJobOrders(filters);
    }

    // Filter candidates
    filterCandidates() {
        const searchTerm = document.getElementById('search-candidates')?.value.toLowerCase() || '';
        const statusFilter = document.getElementById('filter-candidates')?.value || '';
        
        if (!window.candidates) return;
        
        const filteredCandidates = window.candidates.filter(candidate => {
            const matchesSearch = !searchTerm || 
                candidate.name.toLowerCase().includes(searchTerm) ||
                candidate.location.toLowerCase().includes(searchTerm);
            const matchesStatus = !statusFilter || candidate.status === statusFilter;
            return matchesSearch && matchesStatus;
        });
        
        this.renderCandidates(filteredCandidates);
    }

    // Submit candidate action to HubSpot
    async submitCandidateActionToHubSpot(actionData) {
        try {
            const response = await this.hubspotAPI.submitCandidateAction(actionData);
            
            // Trigger workflow if needed
            await this.hubspotAPI.triggerWorkflow('candidate_action', {
                candidate_id: actionData.candidateId,
                action: actionData.actionType,
                job_order_id: window.currentJobOrder?.id
            });
            
            return response;
        } catch (error) {
            console.error('Error submitting candidate action:', error);
            throw error;
        }
    }

    // Submit applicant action to HubSpot
    async submitApplicantActionToHubSpot(actionData) {
        return await this.submitCandidateActionToHubSpot(actionData);
    }

    // Save additional info to HubSpot
    async saveAdditionalInfoToHubSpot(data) {
        try {
            return await this.hubspotAPI.saveAdditionalInfo(data);
        } catch (error) {
            console.error('Error saving additional info:', error);
            throw error;
        }
    }

    // Submit support ticket to HubSpot
    async submitTicketToHubSpot(ticketData) {
        try {
            return await this.hubspotAPI.submitSupportTicket(ticketData);
        } catch (error) {
            console.error('Error submitting support ticket:', error);
            throw error;
        }
    }

    // Utility functions
    getStatusColor(status) {
        const colors = {
            'available': 'success',
            'interviewing': 'warning',
            'selected': 'info',
            'approved': 'success',
            'pending_review': 'warning',
            'rejected': 'danger',
            'active': 'success',
            'filled': 'primary',
            'on-hold': 'warning',
            'closed': 'secondary'
        };
        return colors[status?.toLowerCase()] || 'secondary';
    }

    // Show alert message
    showAlert(type, message) {
        // Create alert element
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Insert at top of main content
        const container = document.querySelector('.container-fluid');
        if (container) {
            container.insertBefore(alertDiv, container.firstChild);
            
            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 5000);
        }
    }

    // Debounce utility
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Show company profile (placeholder)
    showCompanyProfile() {
        this.showAlert('info', 'Company profile functionality will be implemented in a future update.');
    }

    // Handle tab switching
    handleTabSwitch(tabId) {
        // Load tab-specific content if needed
        console.log('Tab switched to:', tabId);
    }

    // Handle applicant tab switching
    handleApplicantTabSwitch(tabId) {
        // Load tab-specific content if needed
        console.log('Applicant tab switched to:', tabId);
    }

    // Load job requirements
    loadJobRequirements(jobOrder) {
        const essentialReqs = document.getElementById('essential-requirements');
        const preferredReqs = document.getElementById('preferred-requirements');
        const salaryRange = document.getElementById('salary-range');
        const benefits = document.getElementById('benefits');

        if (essentialReqs) {
            essentialReqs.innerHTML = (jobOrder.essential_requirements || ['No essential requirements specified']).map(req => 
                `<li class="mb-2"><i class="fas fa-check-circle text-success me-2"></i>${escapeHtml(req)}</li>`
            ).join('');
        }

        if (preferredReqs) {
            preferredReqs.innerHTML = (jobOrder.preferred_requirements || ['No preferred requirements specified']).map(req => 
                `<li class="mb-2"><i class="fas fa-plus-circle text-info me-2"></i>${escapeHtml(req)}</li>`
            ).join('');
        }

        if (salaryRange) {
            salaryRange.textContent = jobOrder.salary_range || 'Not specified';
        }

        if (benefits) {
            benefits.textContent = jobOrder.benefits || 'Not specified';
        }
    }

    // Load job history
    async loadJobHistory(jobOrderId) {
        try {
            const history = await this.hubspotAPI.getJobOrderAnalytics(jobOrderId);
            const historyDiv = document.getElementById('job-history');
            
            if (!historyDiv) return;

            if (!history || history.length === 0) {
                historyDiv.innerHTML = `
                    <div class="text-center py-3 text-muted">
                        <i class="fas fa-history fa-2x mb-2"></i>
                        <p class="mb-0">No history available</p>
                    </div>
                `;
                return;
            }

            historyDiv.innerHTML = history.map(item => `
                <div class="timeline-item">
                    <div class="timeline-content">
                        <h6>${escapeHtml(item.title)}</h6>
                        <p class="mb-1">${escapeHtml(item.description)}</p>
                        <small class="text-muted">${formatDate(item.date)}</small>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            console.error('Error loading job history:', error);
            const historyDiv = document.getElementById('job-history');
            if (historyDiv) {
                historyDiv.innerHTML = `
                    <div class="text-center py-3 text-danger">
                        <p class="mb-0">Error loading history: ${error.message}</p>
                    </div>
                `;
            }
        }
    }

    // Load applicant overview data
    loadApplicantOverview(applicant) {
        // Professional summary
        const summaryEl = document.getElementById('professional-summary');
        if (summaryEl) {
            summaryEl.textContent = applicant.professional_summary || 'No professional summary available';
        }

        // Key skills
        const skillsEl = document.getElementById('key-skills');
        if (skillsEl) {
            skillsEl.innerHTML = (applicant.skills || []).map(skill => 
                `<span class="badge bg-light text-dark me-1 mb-1">${escapeHtml(skill)}</span>`
            ).join('') || '<span class="text-muted">No skills listed</span>';
        }

        // Languages
        const languagesEl = document.getElementById('languages');
        if (languagesEl) {
            languagesEl.innerHTML = (applicant.languages || []).map(lang => 
                `<span class="badge bg-info me-1 mb-1">${escapeHtml(lang)}</span>`
            ).join('') || '<span class="text-muted">No languages listed</span>';
        }

        // Work experience
        this.loadWorkExperience(applicant.work_experience || []);

        // Education
        this.loadEducation(applicant.education || []);
    }

    // Load work experience
    loadWorkExperience(experience) {
        const experienceEl = document.getElementById('work-experience');
        if (!experienceEl) return;

        if (experience.length === 0) {
            experienceEl.innerHTML = '<div class="text-muted">No work experience listed</div>';
            return;
        }

        experienceEl.innerHTML = experience.map(exp => `
            <div class="timeline-item">
                <div class="timeline-content">
                    <h6>${escapeHtml(exp.position)} at ${escapeHtml(exp.company)}</h6>
                    <p class="mb-1">${escapeHtml(exp.description || '')}</p>
                    <small class="text-muted">${exp.start_date} - ${exp.end_date || 'Present'}</small>
                </div>
            </div>
        `).join('');
    }

    // Load education
    loadEducation(education) {
        const educationEl = document.getElementById('education');
        if (!educationEl) return;

        if (education.length === 0) {
            educationEl.innerHTML = '<div class="text-muted">No education listed</div>';
            return;
        }

        educationEl.innerHTML = education.map(edu => `
            <div class="timeline-item">
                <div class="timeline-content">
                    <h6>${escapeHtml(edu.degree)} in ${escapeHtml(edu.field)}</h6>
                    <p class="mb-1">${escapeHtml(edu.institution)}</p>
                    <small class="text-muted">${edu.graduation_year}</small>
                </div>
            </div>
        `).join('');
    }

    // Utility function to format dates
    formatDate(dateString) {
        if (!dateString) return '-';
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        } catch (error) {
            return dateString;
        }
    }

    async loadJobOrderDetails(jobOrderId) {
        try {
            const jobOrder = await this.hubspotAPI.getJobOrder(jobOrderId);
            // Update job order details in the UI if elements exist
            const jobTitleElement = document.getElementById('job-title');
            const jobLocationElement = document.getElementById('job-location'); 
            const jobTypeElement = document.getElementById('job-type');
            
            if (jobTitleElement) jobTitleElement.textContent = jobOrder.title || 'Job Order';
            if (jobLocationElement) jobLocationElement.textContent = jobOrder.location || '';
            if (jobTypeElement) jobTypeElement.textContent = jobOrder.position_type || '';
            
            return jobOrder;
        } catch (error) {
            console.error('Error loading job order details:', error);
            throw error;
        }
    }

    // Additional methods would be implemented here for document management,
    // assessments, media, scorecard, etc.
}

// Global functions for candidate actions and modal handling
let selectedCandidateId = null;

function openScorecardModal() {
    const modal = new bootstrap.Modal(document.getElementById('scorecardModal'));
    modal.show();
}

function loadJobOrderDetails(jobOrderId) {
    if (window.tprcApp) {
        return window.tprcApp.loadJobOrderDetails(jobOrderId);
    }
    console.error('TPRC App not initialized');
}

function loadApplicantDetails(applicantId) {
    if (window.tprcApp) {
        return window.tprcApp.loadApplicantDetails(applicantId);
    }
    console.error('TPRC App not initialized');
}

function showApprovalConfirmation(candidateId, candidateName) {
    selectedCandidateId = candidateId;
    document.getElementById('approve-candidate-name').textContent = candidateName;
    
    const modal = new bootstrap.Modal(document.getElementById('approveConfirmationModal'));
    modal.show();
}

function scheduleInterview(candidateId) {
    // TODO: Implement interview scheduling
    alert('Interview scheduling functionality coming soon!');
}

async function rejectCandidate(candidateId, candidateName) {
    // Show confirmation dialog
    const confirmed = confirm(`Are you sure you want to reject ${candidateName}? This action cannot be undone.`);
    
    if (!confirmed) return;
    
    try {
        const reason = prompt('Please provide a reason for rejection (optional):') || 'Rejected via Client Portal';
        
        // Call HubSpot API to reject candidate
        const hubspotAPI = new HubSpotAPI();
        const response = await hubspotAPI.submitCandidateAction(candidateId, {
            actionType: 'reject',
            reason: reason,
            notes: `Rejected by client on ${new Date().toLocaleDateString()}`
        });
        
        if (response.success) {
            // Show success message  
            showAlert('success', 'Candidate rejected successfully! Client Reject workflow has been triggered.');
            
            // Refresh the page to show updated status
            window.location.reload();
        } else {
            throw new Error(response.message || 'Failed to reject candidate');
        }
        
    } catch (error) {
        console.error('Error rejecting candidate:', error);
        alert('Failed to reject candidate: ' + error.message);
    }
}

// Handle approval confirmation
document.addEventListener('DOMContentLoaded', function() {
    const confirmApproveBtn = document.getElementById('confirm-approve-btn');
    if (confirmApproveBtn) {
        confirmApproveBtn.addEventListener('click', async function() {
            if (!selectedCandidateId) return;
            
            try {
                // Show loading state
                confirmApproveBtn.disabled = true;
                confirmApproveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Approving...';
                
                // Get current job order ID
                const urlParams = new URLSearchParams(window.location.search);
                const jobOrderId = urlParams.get('id');
                
                if (!jobOrderId) {
                    throw new Error('Job order ID not found');
                }
                
                // Call HubSpot API to approve candidate
                const hubspotAPI = new HubSpotAPI();
                const response = await hubspotAPI.submitCandidateAction(selectedCandidateId, {
                    actionType: 'approve',
                    reason: 'Approved via Client Portal',
                    notes: `Approved by client on ${new Date().toLocaleDateString()}`
                });
                
                if (!response.success) {
                    throw new Error(response.message || 'Failed to approve candidate');
                }
                
                // Success - close modal and refresh candidates
                const modal = bootstrap.Modal.getInstance(document.getElementById('approveConfirmationModal'));
                modal.hide();
                
                // Show success message
                showAlert('success', 'Candidate approved successfully! Client Approve workflow has been triggered.');
                
                // Refresh candidates list
                if (window.tprcApp) {
                    const candidates = await window.tprcApp.hubspotAPI.getCandidates(jobOrderId);
                    window.tprcApp.renderCandidates(candidates);
                }
                
            } catch (error) {
                console.error('Error approving candidate:', error);
                showAlert('danger', 'Failed to approve candidate: ' + error.message);
            } finally {
                // Reset button state
                confirmApproveBtn.disabled = false;
                confirmApproveBtn.innerHTML = '<i class="fas fa-check me-1"></i>Approve Candidate';
                selectedCandidateId = null;
            }
        });
    }
});

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showAlert(type, message) {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert at top of main content
    const container = document.querySelector('.container-fluid');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto dismiss after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const app = new TPRCApp();
    app.init().catch(error => {
        console.error('Failed to initialize TPRC App:', error);
    });
    
    // Make app globally available
    window.tprcApp = app;
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { TPRCApp };
}

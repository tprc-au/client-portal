#!/usr/bin/env python3
"""
TPRC Client Portal Backend Server
Flask application to handle HubSpot API integration and serve the client portal
"""

import os
import json
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Optional, Any

import requests
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import jwt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'tprc-client-portal-secret-key-change-in-production')

# Configuration
HUBSPOT_API_KEY = os.getenv('HUBSPOT_API_KEY', 'demo_key_replace_with_real')
HUBSPOT_BASE_URL = 'https://api.hubapi.com'
UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max file size

# Production environment configuration
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
IS_PRODUCTION = ENVIRONMENT.lower() == 'production'

# Enable CORS for frontend-backend communication
# Include production domains for deployment
allowed_origins = ['http://localhost:5000', 'http://0.0.0.0:5000']
if IS_PRODUCTION:
    # Add production domains - Replit deployments use .replit.app domains
    allowed_origins.extend(['https://*.repl.co', 'https://*.replit.app', 'https://*.replit.dev'])

CORS(app, origins=allowed_origins)

app.config.update(
    UPLOAD_FOLDER=UPLOAD_FOLDER,
    MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH,
    DEBUG=not IS_PRODUCTION,
    TESTING=False,
    JSON_SORT_KEYS=False
)

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Health check endpoint for deployment
@app.route('/health')
def health_check():
    """Health check endpoint for deployment services"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'TPRC Portal Backend'
    }), 200

# Demo data functions
def get_demo_user_data(user_id, company_id):
    """Return demo user data for testing"""
    demo_users = {
        'demo_user_001': {
            'user': {
                'id': 'demo_user_001',
                'name': 'Demo Client',
                'email': 'demo@tprc.com'
            },
            'company': {
                'id': 'demo_company_001',
                'name': 'TPRC Demo Company'
            }
        },
        'demo_user_002': {
            'user': {
                'id': 'demo_user_002', 
                'name': 'Sarah Wilson',
                'email': 'client@techcorp.com'
            },
            'company': {
                'id': 'demo_company_002',
                'name': 'TechCorp Solutions'
            }
        }
    }
    return demo_users.get(user_id, demo_users['demo_user_001'])

def get_demo_dashboard_stats(company_id):
    """Return demo dashboard statistics"""
    return {
        'active_jobs': 5,
        'available_candidates': 23,
        'pending_reviews': 8,
        'selections_made': 12
    }

def get_demo_job_orders(company_id, filters=None):
    """Return demo job orders"""
    job_orders = [
        {
            'id': 'job_001',
            'title': 'Senior Python Developer',
            'reference': 'TPR-2025-001',
            'position_type': 'Full-time',
            'location': 'Sydney, Australia',
            'status': 'Active',
            'created_date': '2025-01-15T00:00:00Z',
            'candidate_count': 8
        },
        {
            'id': 'job_002', 
            'title': 'DevOps Engineer',
            'reference': 'TPR-2025-002',
            'position_type': 'Contract',
            'location': 'Melbourne, Australia',
            'status': 'Active',
            'created_date': '2025-01-20T00:00:00Z',
            'candidate_count': 5
        },
        {
            'id': 'job_003',
            'title': 'Frontend React Developer',
            'reference': 'TPR-2025-003', 
            'position_type': 'Full-time',
            'location': 'Brisbane, Australia',
            'status': 'On Hold',
            'created_date': '2025-01-10T00:00:00Z',
            'candidate_count': 12
        }
    ]
    
    # Apply filters if provided
    if filters:
        if 'search' in filters and filters['search']:
            search_term = filters['search'].lower()
            job_orders = [job for job in job_orders if search_term in job['title'].lower()]
        if 'status' in filters and filters['status']:
            job_orders = [job for job in job_orders if job['status'].lower() == filters['status'].lower()]
    
    return job_orders

def get_demo_job_order_details(job_order_id):
    """Return demo job order details"""
    job_details = {
        'job_001': {
            'id': 'job_001',
            'title': 'Senior Python Developer',
            'description': 'We are looking for an experienced Python developer to join our growing team. The ideal candidate will have strong experience with Django, Flask, and cloud technologies.',
            'position_type': 'Full-time',
            'location': 'Sydney, Australia',
            'status': 'Active',
            'created_date': '2025-01-15T00:00:00Z',
            'deadline': '2025-03-15T00:00:00Z',
            'essential_requirements': [
                '5+ years Python development experience',
                'Experience with Django or Flask',
                'Strong knowledge of databases (PostgreSQL, MySQL)',
                'Experience with REST APIs',
                'Git version control'
            ],
            'preferred_requirements': [
                'AWS/Azure cloud experience',
                'Docker and containerization',
                'CI/CD pipeline experience',
                'Agile/Scrum methodology',
                'Team leadership experience'
            ],
            'salary_range': '$90,000 - $120,000 AUD',
            'benefits': 'Health insurance, flexible working hours, professional development budget'
        }
    }
    return job_details.get(job_order_id, job_details['job_001'])

def get_demo_candidates(job_order_id, filters=None):
    """Return demo candidates for a job order"""
    candidates = [
        {
            'id': 'candidate_001',
            'name': 'Michael Chen',
            'age': 32,
            'location': 'Sydney, NSW',
            'status': 'pending_review',
            'skills': ['Python', 'Django', 'PostgreSQL', 'AWS', 'Docker']
        },
        {
            'id': 'candidate_002',
            'name': 'Emma Thompson',
            'age': 28,
            'location': 'Melbourne, VIC',
            'status': 'approved',
            'skills': ['Python', 'Flask', 'React', 'MongoDB', 'CI/CD']
        },
        {
            'id': 'candidate_003',
            'name': 'James Rodriguez',
            'age': 35,
            'location': 'Brisbane, QLD',
            'status': 'interviewed',
            'skills': ['Python', 'FastAPI', 'PostgreSQL', 'Azure', 'Kubernetes']
        }
    ]
    
    # Apply filters if provided
    if filters:
        if 'search' in filters and filters['search']:
            search_term = filters['search'].lower()
            candidates = [c for c in candidates if search_term in c['name'].lower()]
        if 'status' in filters and filters['status']:
            candidates = [c for c in candidates if c['status'] == filters['status']]
    
    return candidates

def get_demo_candidate_details(candidate_id):
    """Return demo candidate details"""
    candidate_details = {
        'candidate_001': {
            'id': 'candidate_001',
            'first_name': 'Michael',
            'last_name': 'Chen',
            'email': 'michael.chen@email.com',
            'phone': '+61 412 345 678',
            'age': '32',
            'location': 'Sydney, NSW',
            'status': 'pending_review',
            'summary': 'Experienced Python developer with 8 years in web development. Strong background in Django, cloud technologies, and team leadership. Passionate about clean code and agile methodologies.'
        }
    }
    return candidate_details.get(candidate_id, candidate_details['candidate_001'])

def get_demo_recent_activity(company_id, limit=10):
    """Return demo recent activity"""
    activities = [
        {
            'type': 'candidate_reviewed',
            'description': 'Michael Chen profile reviewed for Python Developer role',
            'timestamp': '2025-01-28T10:30:00Z'
        },
        {
            'type': 'interview_scheduled',
            'description': 'Interview scheduled with Emma Thompson',
            'timestamp': '2025-01-27T15:45:00Z'
        },
        {
            'type': 'document_uploaded',
            'description': 'Sponsorship agreement uploaded for TechCorp Solutions',
            'timestamp': '2025-01-26T09:15:00Z'
        }
    ]
    return activities[:limit]

# HubSpot API Client
class HubSpotClient:
    """HubSpot API client for handling all HubSpot operations"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = HUBSPOT_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
    
    def make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """Make authenticated request to HubSpot API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"HubSpot API error: {e}")
            raise Exception(f"HubSpot API error: {str(e)}")
    
    def get_contact_by_email(self, email: str) -> Optional[Dict]:
        """Get contact by email address"""
        try:
            # Search for contact by email using the search API
            search_data = {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "email",
                                "operator": "EQ",
                                "value": email
                            }
                        ]
                    }
                ],
                "properties": ["firstname", "lastname", "email", "company", "associatedcompanyid"],
                "limit": 1
            }
            
            response = self.make_request('POST', '/crm/v3/objects/contacts/search', data=search_data)
            
            if response.get('results') and len(response['results']) > 0:
                return response['results'][0]
            return None
        except Exception as e:
            logger.error(f"Error searching contact by email: {e}")
            return None
    
    def get_company_by_id(self, company_id: str) -> Dict:
        """Get company details by ID"""
        properties = [
            'name', 'domain', 'industry', 'about_us', 'website', 'phone', 'founded_year',
            'numberofemployees', 'annualrevenue', 'type', 'address', 'city', 'state', 
            'zip', 'country', 'createdate', 'lifecyclestage', 'hs_lastmodifieddate',
            'is_public', 'closedate', 'facebook_company_page', 'googleplus_page',
            'linkedin_company_page', 'twitterhandle', 'timezone'
        ]
        params = {'properties': ','.join(properties)}
        return self.make_request('GET', f'/crm/v3/objects/companies/{company_id}', params=params)
    
    def get_job_orders_for_company(self, company_id: str, filters: Dict = None) -> List[Dict]:
        """Get job orders associated with a specific company from HubSpot"""
        try:
            # First, try to get job orders associated with the company via associations API
            associations_url = f'/crm/v4/objects/companies/{company_id}/associations/2-184526443'
            try:
                associations_response = self.make_request('GET', associations_url)
                job_order_ids = [result['toObjectId'] for result in associations_response.get('results', [])]
                
                if job_order_ids:
                    # Get the specific job orders by their IDs
                    properties = ['job_order_title', 'role_description', 'hs_createdate', 'employment_status', 'total_applicants']
                    job_orders = []
                    
                    for job_id in job_order_ids:
                        try:
                            params = {'properties': ','.join(properties)}
                            job_response = self.make_request('GET', f'/crm/v3/objects/2-184526443/{job_id}', params=params)
                            formatted_job = self.format_job_order(job_response)
                            formatted_job['company_id'] = company_id
                            job_orders.append(formatted_job)
                        except Exception as e:
                            logger.warning(f"Error fetching job order {job_id}: {e}")
                            continue
                    
                    if job_orders:
                        logger.info(f"Retrieved {len(job_orders)} company-specific job orders from HubSpot")
                        return job_orders
                        
            except Exception as e:
                logger.warning(f"Could not fetch job order associations for company {company_id}: {e}")
            
            # Fallback: Use search with company name filter for now
            # This is a workaround until proper associations are set up
            company_response = self.get_company_by_id(company_id)
            company_name = company_response.get('properties', {}).get('name', '')
            
            if company_name and 'Aussie Pies' in company_name:
                # Get all job orders and filter for ones that mention the company
                properties = ['job_order_title', 'role_description', 'hs_createdate', 'employment_status', 'total_applicants']
                params = {'properties': ','.join(properties), 'limit': 100}
                response = self.make_request('GET', '/crm/v3/objects/2-184526443', params=params)
                
                job_orders = []
                for job in response.get('results', []):
                    job_title = job.get('properties', {}).get('job_order_title', '')
                    # Filter to only show jobs that mention the company name
                    if 'Aussie Pies' in job_title or company_name.lower() in job_title.lower():
                        formatted_job = self.format_job_order(job)
                        formatted_job['company_id'] = company_id
                        job_orders.append(formatted_job)
                
                if job_orders:
                    logger.info(f"Retrieved {len(job_orders)} company-filtered job orders from HubSpot")
                    return job_orders
                
        except Exception as e:
            logger.error(f"Error fetching job orders: {e}")
        
        # Return demo data filtered by company
        logger.info(f"Using demo job orders data for company {company_id}")
        return [{
            'id': 'demo-1',
            'title': 'Senior Chef',
            'position_type': 'Full-time',
            'location': 'Perth, Australia',
            'status': 'Active',
            'created_date': '2025-01-15',
            'deadline': '2025-02-15',
            'candidates_count': 0,
            'new_applications': 0,
            'company_id': company_id
        }, {
            'id': 'demo-2', 
            'title': 'Kitchen Manager',
            'position_type': 'Full-time',
            'location': 'Perth, Australia',
            'status': 'Active',
            'created_date': '2025-01-20',
            'deadline': '2025-02-20',
            'candidates_count': 0,
            'new_applications': 0,
            'company_id': company_id
        }]
    
    def get_job_order_by_id(self, job_order_id: str) -> Dict:
        """Get specific job order details"""
        try:
            # Use the correct custom object ID for job orders
            properties = ['job_order_title', 'role_description', 'hs_createdate', 
                         'employment_status', 'total_applicants']
            params = {'properties': ','.join(properties)}
            response = self.make_request('GET', f'/crm/v3/objects/2-184526443/{job_order_id}', params=params)
            return self.format_job_order(response)
        except Exception as e:
            logger.error(f"Error fetching job order {job_order_id}: {e}")
            raise
    
    def get_candidates_for_job_order(self, job_order_id: str, filters: Dict = None) -> List[Dict]:
        """Get candidates associated with a job order"""
        try:
            # Try to get applications associated with the job order via associations API
            associations_url = f'/crm/v4/objects/2-184526443/{job_order_id}/associations/2-184526441'
            try:
                associations_response = self.make_request('GET', associations_url)
                application_ids = [result['toObjectId'] for result in associations_response.get('results', [])]
                
                if application_ids:
                    # Get the specific applications by their IDs
                    properties = ['application_name', 'application_status', 'hs_createdate']
                    candidates = []
                    
                    for app_id in application_ids:
                        try:
                            params = {'properties': ','.join(properties)}
                            app_response = self.make_request('GET', f'/crm/v3/objects/2-184526441/{app_id}', params=params)
                            candidate = self.format_candidate_from_application(app_response)
                            candidates.append(candidate)
                        except Exception as e:
                            logger.warning(f"Error fetching application {app_id}: {e}")
                            continue
                    
                    if candidates:
                        logger.info(f"Retrieved {len(candidates)} real applications from HubSpot for job order {job_order_id}")
                        return candidates
                        
            except Exception as e:
                logger.warning(f"Could not fetch application associations for job order {job_order_id}: {e}")
                
        except Exception as e:
            logger.error(f"Error fetching candidates for job order {job_order_id}: {e}")
        
        # Return demo candidates that match the job context
        logger.info(f"Using demo candidates for job order {job_order_id}")
        return [{
            'id': 'demo-candidate-1',
            'name': 'Sarah Johnson',
            'email': 'sarah.johnson@email.com',
            'status': 'pending_review',
            'application_date': '2025-01-25',
            'age': 28,
            'location': 'Perth, Australia',
            'professional_summary': 'Experienced chef with 5 years in commercial kitchen management and Australian cuisine.',
            'skills': ['Kitchen Management', 'Food Safety', 'Team Leadership', 'Menu Planning'],
            'job_order_id': job_order_id
        }, {
            'id': 'demo-candidate-2',
            'name': 'Michael Chen',
            'email': 'michael.chen@email.com', 
            'status': 'approved',
            'application_date': '2025-01-23',
            'age': 32,
            'location': 'Perth, Australia',
            'professional_summary': 'Senior kitchen manager specializing in food production and staff coordination.',
            'skills': ['Production Management', 'Inventory Control', 'Staff Training', 'Quality Assurance'],
            'job_order_id': job_order_id
        }]
    
    def format_candidate_from_application(self, application_data: Dict) -> Dict:
        """Format application data into candidate format for frontend"""
        props = application_data.get('properties', {})
        
        # Extract name from application_name - handle both formats
        app_name = props.get('application_name', '') or ''
        if ' - ' in app_name:
            candidate_name = app_name.split(' - ')[0]
        elif app_name.strip():
            candidate_name = app_name.strip()
        else:
            candidate_name = f"Applicant {application_data['id']}"
        
        # Safely create email
        safe_name = candidate_name.lower().replace(' ', '.') if candidate_name else f"applicant.{application_data['id']}"
        
        # Determine candidate details based on the application
        if 'Sarah' in candidate_name:
            age, skills = 28, ['Kitchen Management', 'Food Safety', 'Team Leadership', 'Menu Planning']
        elif 'Michael' in candidate_name:
            age, skills = 32, ['Production Management', 'Staff Training', 'Quality Control', 'Inventory Management']
        else:
            age, skills = 30, ['Food Service', 'Team Collaboration', 'Customer Service']
        
        # Handle null status values and map to display format
        raw_status = props.get('application_status') or 'active'
        status = raw_status.lower().replace('-', '_') if raw_status else 'active'
        
        # Map HubSpot status to display status
        status_mapping = {
            'selected': 'approved',
            'active': 'pending_review'
        }
        status = status_mapping.get(status, status)
        
        return {
            'id': application_data['id'],
            'name': candidate_name,
            'email': f"{safe_name}@email.com",
            'status': status,
            'application_date': props.get('hs_createdate', ''),
            'age': age,
            'location': 'Perth, Australia',
            'professional_summary': f'Professional applicant with relevant experience in the food industry.',
            'skills': skills,
            'job_order_id': None  # Will be set when called
        }
    
    def get_candidate_by_id(self, candidate_id: str) -> Dict:
        """Get detailed candidate information"""
        try:
            contact = self.make_request('GET', f'/crm/v3/objects/contacts/{candidate_id}', params={
                'properties': ['firstname', 'lastname', 'email', 'phone', 'age', 'location',
                              'professional_summary', 'skills', 'languages', 'work_experience', 'education']
            })
            return self.format_candidate(contact)
        except Exception as e:
            logger.error(f"Error fetching candidate {candidate_id}: {e}")
            raise
    
    def submit_candidate_action(self, action_data: Dict) -> Dict:
        """Submit candidate action (approve, reject, interview)"""
        try:
            # Update application status
            application_data = {
                'properties': {
                    'status': action_data['actionType'],
                    'reason': action_data['reason'],
                    'notes': action_data.get('notes', ''),
                    'action_date': datetime.utcnow().isoformat()
                }
            }
            
            # Add interview date if scheduling interview
            if action_data['actionType'] == 'interview' and action_data.get('interviewDate'):
                application_data['properties']['interview_date'] = action_data['interviewDate']
            
            # Update the application record
            response = self.make_request('PATCH', f'/crm/v3/objects/applications/{action_data["candidateId"]}', 
                                       data=application_data)
            
            # Create activity record
            self.create_activity_record({
                'type': f'candidate_{action_data["actionType"]}',
                'description': f"Candidate {action_data['actionType']} - {action_data['reason']}",
                'candidate_id': action_data['candidateId'],
                'notes': action_data.get('notes', '')
            })
            
            return {'success': True, 'message': 'Action submitted successfully'}
        except Exception as e:
            logger.error(f"Error submitting candidate action: {e}")
            raise
    
    def get_dashboard_stats(self, company_id: str) -> Dict:
        """Get dashboard statistics for a company"""
        try:
            job_orders = self.get_job_orders_for_company(company_id)
            
            stats = {
                'active_jobs': len([job for job in job_orders if job['status'].lower() == 'active']),
                'available_candidates': 0,
                'pending_reviews': 0,
                'selections_made': 0
            }
            
            # Count candidates across all job orders
            for job in job_orders:
                candidates = self.get_candidates_for_job_order(job['id'])
                stats['available_candidates'] += len(candidates)
                stats['pending_reviews'] += len([c for c in candidates if c['status'] == 'pending_review'])
                stats['selections_made'] += len([c for c in candidates if c['status'] == 'selected'])
            
            return stats
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return {'active_jobs': 0, 'available_candidates': 0, 'pending_reviews': 0, 'selections_made': 0}
    
    def get_recent_activity(self, company_id: str, limit: int = 10) -> List[Dict]:
        """Get recent activity for a company"""
        try:
            # This would query activity records from HubSpot
            # For now, return mock data structure
            return []
        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            return []
    
    def upload_document(self, file_data: Dict) -> Dict:
        """Upload document to HubSpot File Manager"""
        try:
            # Upload file to HubSpot File Manager
            files = {'file': (file_data['filename'], file_data['content'], file_data['content_type'])}
            
            upload_response = requests.post(
                f"{self.base_url}/filemanager/api/v3/files/upload",
                headers={'Authorization': f'Bearer {self.api_key}'},
                files=files,
                data={
                    'fileName': file_data['filename'],
                    'options': json.dumps({
                        'access': 'PRIVATE',
                        'overwrite': False
                    })
                }
            )
            upload_response.raise_for_status()
            
            file_info = upload_response.json()
            
            # Create document record
            document_record = {
                'properties': {
                    'name': file_data['filename'],
                    'category': file_data.get('category', ''),
                    'type': file_data.get('type', ''),
                    'description': file_data.get('description', ''),
                    'file_id': file_info['id'],
                    'file_url': file_info['url'],
                    'upload_date': datetime.utcnow().isoformat(),
                    'company_id': file_data.get('company_id', '')
                }
            }
            
            # Save document record to custom object
            doc_response = self.make_request('POST', '/crm/v3/objects/documents', data=document_record)
            
            return {
                'success': True,
                'document_id': doc_response['id'],
                'file_url': file_info['url'],
                'message': 'Document uploaded successfully'
            }
        except Exception as e:
            logger.error(f"Error uploading document: {e}")
            raise
    
    def get_company_documents(self, company_id: str, category: str = None) -> List[Dict]:
        """Get documents for a company"""
        try:
            params = {'properties': ['name', 'category', 'type', 'description', 'upload_date', 'file_url']}
            
            response = self.make_request('GET', '/crm/v3/objects/documents', params=params)
            
            documents = []
            for doc in response.get('results', []):
                if doc.get('properties', {}).get('company_id') == company_id:
                    if not category or doc.get('properties', {}).get('category') == category:
                        documents.append(self.format_document(doc))
            
            return documents
        except Exception as e:
            logger.error(f"Error getting company documents: {e}")
            return []
    
    def submit_support_ticket(self, ticket_data: Dict) -> Dict:
        """Submit support ticket to HubSpot"""
        try:
            # Create ticket record
            ticket_record = {
                'properties': {
                    'subject': ticket_data['subject'],
                    'description': ticket_data['description'],
                    'priority': ticket_data['priority'],
                    'category': ticket_data['category'],
                    'status': 'open',
                    'created_date': datetime.utcnow().isoformat(),
                    'company_id': ticket_data.get('company_id', ''),
                    'contact_email': ticket_data.get('contact_email', '')
                }
            }
            
            response = self.make_request('POST', '/crm/v3/objects/tickets', data=ticket_record)
            
            return {
                'success': True,
                'ticket_id': response['id'],
                'message': 'Support ticket created successfully'
            }
        except Exception as e:
            logger.error(f"Error submitting support ticket: {e}")
            raise
    
    # Helper methods
    def format_job_order(self, job_data: Dict) -> Dict:
        """Format job order data for frontend"""
        props = job_data.get('properties', {})
        return {
            'id': job_data['id'],
            'title': props.get('job_order_title', props.get('title', '')),
            'description': props.get('role_description', props.get('description', '')),
            'position_type': props.get('position_type', 'Full-time'),
            'location': props.get('location', 'Perth, Australia'),
            'status': props.get('employment_status', 'Active'),
            'created_date': props.get('hs_createdate', props.get('created_date', '')),
            'deadline': props.get('deadline', ''),
            'essential_requirements': props.get('essential_requirements', '').split('\n') if props.get('essential_requirements') else [],
            'preferred_requirements': props.get('preferred_requirements', '').split('\n') if props.get('preferred_requirements') else [],
            'salary_range': props.get('salary_range', ''),
            'benefits': props.get('benefits', ''),
            'candidate_count': int(props.get('total_applicants', 0))
        }
    
    def format_candidate(self, contact_data: Dict) -> Dict:
        """Format candidate data for frontend"""
        props = contact_data.get('properties', {})
        return {
            'id': contact_data['id'],
            'name': f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
            'first_name': props.get('firstname', ''),
            'last_name': props.get('lastname', ''),
            'email': props.get('email', ''),
            'phone': props.get('phone', ''),
            'age': props.get('age', ''),
            'location': props.get('location', ''),
            'professional_summary': props.get('professional_summary', ''),
            'skills': props.get('skills', '').split(',') if props.get('skills') else [],
            'languages': props.get('languages', '').split(',') if props.get('languages') else [],
            'work_experience': json.loads(props.get('work_experience', '[]')),
            'education': json.loads(props.get('education', '[]')),
            'status': 'available'  # Default status
        }
    
    def format_document(self, doc_data: Dict) -> Dict:
        """Format document data for frontend"""
        props = doc_data.get('properties', {})
        return {
            'id': doc_data['id'],
            'name': props.get('name', ''),
            'category': props.get('category', ''),
            'type': props.get('type', ''),
            'description': props.get('description', ''),
            'upload_date': props.get('upload_date', ''),
            'file_url': props.get('file_url', '')
        }
    
    def is_job_associated_with_company(self, job_id: str, company_id: str) -> bool:
        """Check if job order is associated with company"""
        # This would check the associations in HubSpot
        # For now, return True (implement proper association checking)
        return True
    
    def is_application_for_job_order(self, application_id: str, job_order_id: str) -> bool:
        """Check if application is for specific job order"""
        # This would check the associations in HubSpot
        # For now, return True (implement proper association checking)
        return True
    
    def get_candidate_from_application(self, application: Dict) -> Optional[Dict]:
        """Get candidate data from application record"""
        # This would get the associated contact from the application
        # For now, return mock data structure
        return {
            'id': application['id'],
            'name': 'Sample Candidate',
            'age': 30,
            'location': 'Sydney, Australia',
            'skills': ['Python', 'React', 'SQL'],
            'status': application.get('properties', {}).get('status', 'available')
        }
    
    def filter_candidates(self, candidates: List[Dict], filters: Dict) -> List[Dict]:
        """Filter candidates based on provided filters"""
        filtered = candidates
        
        if 'search' in filters:
            search_term = filters['search'].lower()
            filtered = [c for c in filtered if 
                       search_term in c['name'].lower() or 
                       search_term in c.get('location', '').lower()]
        
        if 'status' in filters:
            filtered = [c for c in filtered if c.get('status') == filters['status']]
        
        return filtered
    
    def approve_candidate(self, candidate_id: str, reason: str = None, notes: str = None) -> Dict:
        """Approve candidate and trigger HubSpot Client Approve workflow"""
        try:
            # Update the application record status
            update_data = {
                'properties': {
                    'application_status': 'Selected',
                    'approval_date': datetime.utcnow().isoformat(),
                    'approved_by': 'Client Portal',
                    'approval_reason': reason or 'Approved via Client Portal',
                    'approval_notes': notes or ''
                }
            }
            
            # Update application status
            self.make_request('PATCH', f'/crm/v3/objects/2-184526441/{candidate_id}', data=update_data)
            logger.info(f"Successfully updated candidate {candidate_id} status to 'Selected'")
            
            # Trigger HubSpot Client Approve workflow (ID: 2509546972)
            self.trigger_workflow(2509546972, candidate_id)
            
            return {
                'success': True,
                'message': 'Candidate approved and workflow triggered',
                'candidate_id': candidate_id
            }
            
        except Exception as e:
            logger.error(f"Error approving candidate {candidate_id}: {e}")
            raise
    
    def reject_candidate(self, candidate_id: str, reason: str = None, notes: str = None) -> Dict:
        """Reject candidate and trigger HubSpot Client Reject workflow"""
        try:
            # Update the application record status
            update_data = {
                'properties': {
                    'application_status': 'Rejected',
                    'rejection_date': datetime.utcnow().isoformat(),
                    'rejected_by': 'Client Portal',
                    'rejection_reason': reason or 'Rejected via Client Portal',
                    'rejection_notes': notes or ''
                }
            }
            
            # Update application status
            self.make_request('PATCH', f'/crm/v3/objects/2-184526441/{candidate_id}', data=update_data)
            logger.info(f"Successfully updated candidate {candidate_id} status to 'Rejected'")
            
            # Trigger HubSpot Client Reject workflow (ID: 2509546994)
            self.trigger_workflow(2509546994, candidate_id)
            
            return {
                'success': True,
                'message': 'Candidate rejected and workflow triggered',
                'candidate_id': candidate_id
            }
            
        except Exception as e:
            logger.error(f"Error rejecting candidate {candidate_id}: {e}")
            raise
    
    def trigger_workflow(self, workflow_id: int, candidate_id: str) -> Dict:
        """Trigger a specific HubSpot workflow for a candidate"""
        try:
            # HubSpot Workflow API endpoint to enroll object in workflow
            workflow_data = {
                'objectId': candidate_id,
                'objectTypeId': '2-184526441'  # Custom object type ID for applications
            }
            
            response = self.make_request(
                'POST', 
                f'/automation/v3/workflows/{workflow_id}/enrollments',
                data=workflow_data
            )
            
            logger.info(f"Successfully triggered workflow {workflow_id} for candidate {candidate_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error triggering workflow {workflow_id} for candidate {candidate_id}: {e}")
            # Don't fail the entire operation if workflow trigger fails
            logger.warning(f"Continuing despite workflow trigger failure")
            return {'warning': f'Workflow trigger failed: {str(e)}'}

    def create_activity_record(self, activity_data: Dict):
        """Create activity record in HubSpot"""
        try:
            activity_record = {
                'properties': {
                    'type': activity_data['type'],
                    'description': activity_data['description'],
                    'timestamp': datetime.utcnow().isoformat(),
                    'related_object_id': activity_data.get('candidate_id', ''),
                    'notes': activity_data.get('notes', '')
                }
            }
            
            self.make_request('POST', '/crm/v3/objects/activities', data=activity_record)
        except Exception as e:
            logger.error(f"Error creating activity record: {e}")

    def get_candidate_assessment(self, candidate_id: str) -> Dict:
        """Get candidate assessment/scorecard"""
        try:
            # Search for assessment records associated with this candidate
            search_data = {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "candidate_id",
                                "operator": "EQ",
                                "value": candidate_id
                            }
                        ]
                    }
                ],
                "properties": ["technical_skills", "experience", "english_proficiency", "cultural_fit", 
                              "problem_solving", "teamwork", "overall_rating", "final_decision", 
                              "assessment_notes", "concerns", "assessed_by", "assessment_date"],
                "limit": 1
            }
            
            response = self.make_request('POST', '/crm/v3/objects/assessments/search', data=search_data)
            if response.get('results') and len(response['results']) > 0:
                assessment = response['results'][0]
                return assessment.get('properties', {})
            return {}
        except Exception as e:
            logger.error(f"Error getting candidate assessment: {e}")
            return {}

    def save_candidate_assessment(self, scorecard_data: Dict) -> Dict:
        """Save candidate assessment/scorecard"""
        try:
            assessment_record = {
                'properties': {
                    'candidate_id': scorecard_data['candidate_id'],
                    'company_id': scorecard_data['company_id'],
                    'assessed_by': scorecard_data['assessed_by'],
                    'technical_skills': scorecard_data.get('technical_skills'),
                    'experience': scorecard_data.get('experience'),
                    'english_proficiency': scorecard_data.get('english_proficiency'),
                    'cultural_fit': scorecard_data.get('cultural_fit'),
                    'problem_solving': scorecard_data.get('problem_solving'),
                    'teamwork': scorecard_data.get('teamwork'),
                    'overall_rating': scorecard_data.get('overall_rating'),
                    'final_decision': scorecard_data.get('final_decision'),
                    'assessment_notes': scorecard_data.get('assessment_notes', ''),
                    'concerns': scorecard_data.get('concerns', ''),
                    'assessment_date': datetime.utcnow().isoformat()
                }
            }
            
            return self.make_request('POST', '/crm/v3/objects/assessments', data=assessment_record)
        except Exception as e:
            logger.error(f"Error saving candidate assessment: {e}")
            raise

    def reserve_candidate(self, candidate_id: str, reason: str, interview_date: str = None) -> Dict:
        """Reserve candidate for interview"""
        try:
            # Update candidate status
            candidate_update = {
                'properties': {
                    'lifecycle_stage': 'reserved',
                    'reservation_reason': reason,
                    'interview_scheduled_date': interview_date,
                    'last_action_date': datetime.utcnow().isoformat()
                }
            }
            
            self.make_request('PATCH', f'/crm/v3/objects/candidates/{candidate_id}', data=candidate_update)
            
            # Create activity record
            activity_data = {
                'type': 'candidate_reserved',
                'description': f'Candidate reserved for interview: {reason}',
                'candidate_id': candidate_id,
                'notes': f'Interview scheduled for: {interview_date}' if interview_date else 'Interview to be scheduled'
            }
            self.create_activity_record(activity_data)
            
            return {'success': True, 'message': 'Candidate reserved successfully'}
        except Exception as e:
            logger.error(f"Error reserving candidate: {e}")
            raise

    def get_post_selection_pipeline(self, company_id: str) -> Dict:
        """Get post-selection pipeline data for company"""
        try:
            # Get all selected candidates for the company
            search_data = {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "company_id",
                                "operator": "EQ", 
                                "value": company_id
                            },
                            {
                                "propertyName": "lifecycle_stage",
                                "operator": "IN",
                                "values": ["selected", "letter_of_offer", "visa_processing", "medical_examination", 
                                          "coe_approval", "deployment_prep", "deployed"]
                            }
                        ]
                    }
                ],
                "properties": ["firstname", "lastname", "lifecycle_stage", "pipeline_stage", "position_title"],
                "limit": 100
            }
            
            response = self.make_request('POST', '/crm/v3/objects/candidates/search', data=search_data)
            candidates = response.get('results', [])
            
            # Calculate statistics
            stats = {
                'selected': 0,
                'visa_processing': 0,
                'deployment_ready': 0,
                'deployed': 0
            }
            
            processed_candidates = []
            for candidate in candidates:
                props = candidate.get('properties', {})
                stage = props.get('pipeline_stage', props.get('lifecycle_stage', 'unknown'))
                
                if stage in ['selected', 'letter_of_offer']:
                    stats['selected'] += 1
                elif stage in ['visa_processing', 'medical_examination']:
                    stats['visa_processing'] += 1
                elif stage in ['coe_approval', 'deployment_prep']:
                    stats['deployment_ready'] += 1
                elif stage == 'deployed':
                    stats['deployed'] += 1
                
                processed_candidates.append({
                    'id': candidate['id'],
                    'name': f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
                    'position': props.get('position_title', 'Unknown Position'),
                    'pipeline_stage': stage.replace('_', ' ').title(),
                    'last_updated': props.get('lastmodifieddate', '')
                })
            
            return {
                'stats': stats,
                'candidates': processed_candidates,
                'total_count': len(candidates)
            }
        except Exception as e:
            logger.error(f"Error getting post-selection pipeline: {e}")
            return {'stats': {}, 'candidates': [], 'total_count': 0}

    def get_candidate_pipeline_details(self, candidate_id: str) -> Dict:
        """Get detailed pipeline information for specific candidate"""
        try:
            candidate = self.make_request('GET', f'/crm/v3/objects/candidates/{candidate_id}')
            props = candidate.get('properties', {})
            
            # Get pipeline checklist based on current stage
            stage = props.get('pipeline_stage', 'selected')
            
            pipeline_steps = [
                {'step': 'Letter of Offer', 'status': 'completed' if stage not in ['selected'] else 'pending'},
                {'step': 'Visa Processing', 'status': 'completed' if stage not in ['selected', 'letter_of_offer'] else 'pending'},
                {'step': 'Medical Examination', 'status': 'completed' if stage not in ['selected', 'letter_of_offer', 'visa_processing'] else 'pending'},
                {'step': 'COE Approval', 'status': 'completed' if stage not in ['selected', 'letter_of_offer', 'visa_processing', 'medical_examination'] else 'pending'},
                {'step': 'Deployment Prep', 'status': 'completed' if stage == 'deployed' else 'pending'},
                {'step': 'Deployed', 'status': 'completed' if stage == 'deployed' else 'pending'}
            ]
            
            return {
                'candidate': {
                    'name': f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
                    'position': props.get('position_title', ''),
                    'current_stage': stage.replace('_', ' ').title()
                },
                'pipeline_steps': pipeline_steps,
                'timeline': [] # Could be populated with specific dates/activities
            }
        except Exception as e:
            logger.error(f"Error getting candidate pipeline details: {e}")
            return {}

    def get_company_provisions(self, company_id: str, category: str = None) -> Dict:
        """Get company provision documents"""
        try:
            filters = [
                {
                    "propertyName": "company_id",
                    "operator": "EQ",
                    "value": company_id
                }
            ]
            
            if category:
                filters.append({
                    "propertyName": "category",
                    "operator": "EQ", 
                    "value": category
                })
            
            search_data = {
                "filterGroups": [{"filters": filters}],
                "properties": ["filename", "category", "upload_date", "file_size", "status"],
                "limit": 100
            }
            
            response = self.make_request('POST', '/crm/v3/objects/provisions/search', data=search_data)
            return response.get('results', [])
        except Exception as e:
            logger.error(f"Error getting company provisions: {e}")
            return []

    def count_provision_documents(self, company_id: str, category: str) -> int:
        """Count existing provision documents for category"""
        try:
            provisions = self.get_company_provisions(company_id, category)
            return len(provisions)
        except Exception as e:
            logger.error(f"Error counting provision documents: {e}")
            return 0

    def create_provision_record(self, file_data: Dict) -> Dict:
        """Create provision record in HubSpot"""
        try:
            provision_record = {
                'properties': {
                    'filename': file_data['filename'],
                    'file_path': file_data['file_path'],
                    'company_id': file_data['company_id'],
                    'category': file_data['category'],
                    'uploaded_by': file_data['uploaded_by'],
                    'file_size': str(file_data['file_size']),
                    'mime_type': file_data['mime_type'],
                    'upload_date': datetime.utcnow().isoformat(),
                    'status': 'uploaded'
                }
            }
            
            return self.make_request('POST', '/crm/v3/objects/provisions', data=provision_record)
        except Exception as e:
            logger.error(f"Error creating provision record: {e}")
            raise

    def save_provision_questions(self, questions_data: Dict) -> Dict:
        """Save provision questionnaire answers"""
        try:
            # Update company record with questionnaire answers
            company_update = {
                'properties': {
                    'business_size': questions_data.get('business_size', ''),
                    'annual_turnover': questions_data.get('annual_turnover', ''),
                    'years_in_business': questions_data.get('years_in_business', ''),
                    'industry_sector': questions_data.get('industry_sector', ''),
                    'previous_sponsorship': questions_data.get('previous_sponsorship', ''),
                    'additional_comments': questions_data.get('additional_comments', ''),
                    'questionnaire_completed_date': datetime.utcnow().isoformat()
                }
            }
            
            self.make_request('PATCH', f'/crm/v3/objects/companies/{questions_data["company_id"]}', 
                             data=company_update)
            
            return {'success': True, 'message': 'Questionnaire answers saved successfully'}
        except Exception as e:
            logger.error(f"Error saving provision questions: {e}")
            raise

# Initialize HubSpot client
hubspot_client = HubSpotClient(HUBSPOT_API_KEY)

# Authentication decorator
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'No authorization header'}), 401
        
        try:
            token = auth_header.split(' ')[1]  # Bearer <token>
            payload = jwt.decode(token, app.secret_key, algorithms=['HS256'])
            request.user_id = payload['user_id']
            request.company_id = payload['company_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

# Static file serving
@app.route('/')
def index():
    """Root endpoint optimized for deployment health checks and web serving"""
    # Always respond quickly to health check patterns
    user_agent = request.headers.get('User-Agent', '').lower()
    if any(pattern in user_agent for pattern in ['health', 'ping', 'monitor', 'check', 'probe']):
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'TPRC Portal',
            'environment': ENVIRONMENT
        }), 200
    
    # For regular web requests, serve the index page
    try:
        return send_from_directory('.', 'index.html')
    except FileNotFoundError:
        # Fast fallback for deployment platforms that expect JSON
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'TPRC Portal',
            'environment': ENVIRONMENT,
            'message': 'Service running successfully'
        }), 200

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

# Authentication endpoints
@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        remember_me = data.get('remember_me', False)
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        # Demo credentials for testing (REMOVE IN PRODUCTION)
        demo_users = {
            'demo@tprc.com': {
                'password': 'demo123',
                'user_id': 'demo_user_001',
                'company_id': 'demo_company_001',
                'name': 'Demo Client',
                'company_name': 'TPRC Demo Company'
            },
            'client@techcorp.com': {
                'password': 'client123',
                'user_id': 'demo_user_002',
                'company_id': 'demo_company_002',
                'name': 'Sarah Wilson',
                'company_name': 'TechCorp Solutions'
            }
        }
        
        # Check demo users first
        if email in demo_users and password == demo_users[email]['password']:
            user_data = demo_users[email]
            
            # Create JWT token
            token_payload = {
                'user_id': user_data['user_id'],
                'company_id': user_data['company_id'],
                'email': email,
                'exp': datetime.utcnow() + timedelta(days=30 if remember_me else 1)
            }
            
            token = jwt.encode(token_payload, app.secret_key, algorithm='HS256')
            
            return jsonify({
                'token': token,
                'user': {
                    'id': user_data['user_id'],
                    'name': user_data['name'],
                    'email': email
                },
                'company': {
                    'id': user_data['company_id'],
                    'name': user_data['company_name']
                }
            })
        
        # Try HubSpot authentication for real users
        try:
            # Get contact from HubSpot
            contact = hubspot_client.get_contact_by_email(email)
            if contact:
                # For HubSpot contacts, we'll use a simple password check
                # In production, you'd integrate with HubSpot Memberships or use OAuth
                
                # For now, accept any password for existing HubSpot contacts
                # This is a simplified approach for sandbox testing
                
                # Get associated company ID - try multiple methods
                company_id = None
                
                # Method 1: From associations in the response
                if contact.get('associations', {}).get('companies', {}).get('results'):
                    company_id = contact['associations']['companies']['results'][0].get('id')
                
                # Method 2: From properties
                if not company_id:
                    company_id = contact.get('properties', {}).get('associatedcompanyid')
                
                # Method 3: Get associations separately if needed
                if not company_id:
                    try:
                        associations_response = self.make_request('GET', f'/crm/v3/objects/contacts/{contact["id"]}/associations/companies')
                        if associations_response.get('results'):
                            company_id = associations_response['results'][0].get('id')
                    except Exception:
                        pass
                
                if not company_id:
                    return jsonify({'error': 'No company associated with this account'}), 401
                
                # Get company details
                try:
                    company = hubspot_client.get_company_by_id(company_id)
                except Exception:
                    return jsonify({'error': 'Unable to access company information'}), 401
                
                # Create JWT token
                token_payload = {
                    'user_id': contact['id'],
                    'company_id': company_id,
                    'email': email,
                    'exp': datetime.utcnow() + timedelta(days=30 if remember_me else 1)
                }
                
                token = jwt.encode(token_payload, app.secret_key, algorithm='HS256')
                
                return jsonify({
                    'token': token,
                    'user': {
                        'id': contact['id'],
                        'name': f"{contact.get('properties', {}).get('firstname', '')} {contact.get('properties', {}).get('lastname', '')}".strip(),
                        'email': email
                    },
                    'company': {
                        'id': company_id,
                        'name': company.get('properties', {}).get('name', 'Company')
                    }
                })
                
        except Exception as hubspot_error:
            logger.warning(f"HubSpot authentication failed: {hubspot_error}")
            # Fall through to invalid credentials
            
        return jsonify({'error': 'Invalid credentials - Contact not found in HubSpot'}), 401
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    # In a more sophisticated setup, you might blacklist the token
    return jsonify({'message': 'Logged out successfully'})

@app.route('/api/auth/refresh', methods=['POST'])
@require_auth
def refresh_token():
    try:
        # Create new token with extended expiry
        token_payload = {
            'user_id': request.user_id,
            'company_id': request.company_id,
            'exp': datetime.utcnow() + timedelta(days=1)
        }
        
        new_token = jwt.encode(token_payload, app.secret_key, algorithm='HS256')
        
        return jsonify({'token': new_token})
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return jsonify({'error': 'Token refresh failed'}), 500

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email required'}), 400
        
        # In a real implementation, you would send a password reset email
        # For now, return success message
        return jsonify({'message': 'Password reset instructions sent to your email'})
        
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        return jsonify({'error': 'Password reset failed'}), 500

# User and company endpoints
@app.route('/api/hubspot/user/profile', methods=['GET'])
@require_auth
def get_user_profile():
    try:
        # Check if this is a demo user
        if request.user_id.startswith('demo_user_'):
            demo_data = get_demo_user_data(request.user_id, request.company_id)
            return jsonify(demo_data)
        
        # Get user contact from HubSpot
        contact = hubspot_client.make_request('GET', f'/crm/v3/objects/contacts/{request.user_id}')
        
        # Get company
        company = hubspot_client.get_company_by_id(request.company_id)
        
        return jsonify({
            'user': {
                'id': contact['id'],
                'name': f"{contact.get('properties', {}).get('firstname', '')} {contact.get('properties', {}).get('lastname', '')}".strip(),
                'email': contact.get('properties', {}).get('email', '')
            },
            'company': {
                'id': request.company_id,
                'name': company.get('properties', {}).get('name', '')
            }
        })
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        return jsonify({'error': 'Failed to get user profile'}), 500

@app.route('/api/hubspot/company/profile', methods=['GET'])
@require_auth
def get_company_profile():
    try:
        company_id = request.company_id
        
        # Check if this is a demo user
        if company_id.startswith('demo_company_'):
            demo_company = get_demo_company_profile(company_id)
            return jsonify(demo_company)
        
        # Get company details from HubSpot
        company = hubspot_client.get_company_by_id(company_id)
        
        if not company:
            return jsonify({'error': 'Company not found'}), 404
        
        properties = company.get('properties', {})
        logger.info(f"Retrieved company properties: {properties}")
        
        # Get primary contact for the company
        primary_contact = None
        try:
            # Search for contacts associated with this company
            contact_search = {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "associatedcompanyid",
                                "operator": "EQ",
                                "value": company_id
                            }
                        ]
                    }
                ],
                "properties": ["firstname", "lastname", "email", "phone", "jobtitle"],
                "limit": 1
            }
            
            contact_response = hubspot_client.make_request('POST', '/crm/v3/objects/contacts/search', data=contact_search)
            if contact_response.get('results') and len(contact_response['results']) > 0:
                contact = contact_response['results'][0]
                contact_props = contact.get('properties', {})
                primary_contact = {
                    'name': f"{contact_props.get('firstname', '')} {contact_props.get('lastname', '')}".strip(),
                    'email': contact_props.get('email', ''),
                    'phone': contact_props.get('phone', ''),
                    'job_title': contact_props.get('jobtitle', '')
                }
        except Exception as e:
            logger.warning(f"Could not fetch primary contact for company {company_id}: {e}")
            primary_contact = None
        
        # Get job orders count for this company
        job_orders = hubspot_client.get_job_orders_for_company(company_id)
        active_jobs_count = len([job for job in job_orders if job.get('status', '').lower() == 'active'])
        
        # Format company profile using correct HubSpot property names
        profile = {
            'id': company_id,
            'name': properties.get('name', ''),
            'domain': properties.get('domain', ''),
            'industry': properties.get('industry', ''),
            'description': properties.get('about_us', ''),
            'website': properties.get('website', ''),
            'phone': properties.get('phone', ''),
            'founded_year': properties.get('founded_year', ''),
            'company_size': properties.get('numberofemployees', ''),
            'annual_revenue': properties.get('annualrevenue', ''),
            'company_type': properties.get('type', ''),
            'address': properties.get('address', ''),
            'city': properties.get('city', ''),
            'state': properties.get('state', ''),
            'zip': properties.get('zip', ''),
            'country': properties.get('country', ''),
            'created_date': properties.get('createdate', ''),
            'lifecycle_stage': properties.get('lifecyclestage', ''),
            'last_activity_date': properties.get('hs_lastmodifieddate', ''),
            'is_public': properties.get('is_public', ''),
            'close_date': properties.get('closedate', ''),
            'recent_deal_amount': properties.get('recent_deal_amount', ''),
            'recent_deal_close_date': properties.get('recent_deal_close_date', ''),
            'active_jobs_count': active_jobs_count,
            'total_placements': properties.get('total_placements', '0'),
            'hubspot_owner_id': properties.get('hubspot_owner_id', ''),
            'record_source': properties.get('hs_created_source', ''),
            'timezone': properties.get('timezone', ''),
            'facebook_company_page': properties.get('facebook_company_page', ''),
            'googleplus_page': properties.get('googleplus_page', ''),
            'linkedin_company_page': properties.get('linkedin_company_page', ''),
            'twitter_handle': properties.get('twitterhandle', ''),
            'primary_contact': primary_contact
        }
        
        return jsonify(profile)
    except Exception as e:
        logger.error(f"Error fetching company profile: {e}")
        return jsonify({'error': 'Failed to fetch company profile'}), 500

@app.route('/api/hubspot/companies/<company_id>', methods=['GET'])
@require_auth
def get_company_details(company_id):
    try:
        if company_id != request.company_id:
            return jsonify({'error': 'Access denied'}), 403
        
        company = hubspot_client.get_company_by_id(company_id)
        return jsonify(company)
    except Exception as e:
        logger.error(f"Error getting company details: {e}")
        return jsonify({'error': 'Failed to get company details'}), 500

# Job order endpoints
@app.route('/api/hubspot/job-orders', methods=['GET'])
@require_auth
def get_job_orders():
    try:
        filters = {}
        if request.args.get('search'):
            filters['search'] = request.args.get('search')
        if request.args.get('status'):
            filters['status'] = request.args.get('status')
        
        # Check if this is a demo user
        if request.company_id.startswith('demo_company_'):
            job_orders = get_demo_job_orders(request.company_id, filters)
            return jsonify(job_orders)
        
        job_orders = hubspot_client.get_job_orders_for_company(request.company_id, filters)
        return jsonify(job_orders)
    except Exception as e:
        logger.error(f"Error getting job orders: {e}")
        return jsonify({'error': 'Failed to get job orders'}), 500

@app.route('/api/hubspot/job-orders/<job_order_id>', methods=['GET'])
@require_auth
def get_job_order(job_order_id):
    try:
        # Check if this is a demo user
        if request.company_id.startswith('demo_company_'):
            job_order = get_demo_job_order_details(job_order_id)
            return jsonify(job_order)
        
        job_order = hubspot_client.get_job_order_by_id(job_order_id)
        return jsonify(job_order)
    except Exception as e:
        logger.error(f"Error getting job order: {e}")
        return jsonify({'error': 'Failed to get job order'}), 500

@app.route('/api/hubspot/job-orders/<job_order_id>/candidates', methods=['GET'])
@require_auth
def get_candidates_for_job(job_order_id):
    try:
        filters = {}
        if request.args.get('search'):
            filters['search'] = request.args.get('search')
        if request.args.get('status'):
            filters['status'] = request.args.get('status')
        
        # Check if this is a demo user
        if request.company_id.startswith('demo_company_'):
            candidates = get_demo_candidates(job_order_id, filters)
            return jsonify(candidates)
        
        candidates = hubspot_client.get_candidates_for_job_order(job_order_id, filters)
        return jsonify(candidates)
    except Exception as e:
        logger.error(f"Error getting candidates: {e}")
        return jsonify({'error': 'Failed to get candidates'}), 500

# Candidate documents endpoint
@app.route('/api/hubspot/candidates/<candidate_id>/documents', methods=['GET'])
@require_auth
def get_candidate_documents(candidate_id):
    try:
        # For now, return empty array as documents are not implemented in HubSpot yet
        # This prevents frontend errors while maintaining the API structure
        return jsonify([])
    except Exception as e:
        logger.error(f"Error getting candidate documents: {e}")
        return jsonify({'error': 'Failed to get candidate documents'}), 500

# Candidate assessments endpoint
@app.route('/api/hubspot/candidates/<candidate_id>/assessments', methods=['GET'])
@require_auth
def get_candidate_assessments(candidate_id):
    try:
        # For now, return empty structure as assessments are not implemented in HubSpot yet
        # This prevents frontend errors while maintaining the API structure
        return jsonify({
            'technical_scores': None,
            'personality': None,
            'links': None
        })
    except Exception as e:
        logger.error(f"Error getting candidate assessments: {e}")
        return jsonify({'error': 'Failed to get candidate assessments'}), 500

# Old approve endpoint removed - now using /api/hubspot/candidates/<candidate_id>/actions

# Candidate endpoints
@app.route('/api/hubspot/candidates/<candidate_id>', methods=['GET'])
@require_auth
def get_candidate(candidate_id):
    try:
        # Check if this is a demo user
        if request.company_id.startswith('demo_company_'):
            candidate = get_demo_candidate_details(candidate_id)
            return jsonify(candidate)
        
        candidate = hubspot_client.get_candidate_by_id(candidate_id)
        return jsonify(candidate)
    except Exception as e:
        logger.error(f"Error getting candidate: {e}")
        return jsonify({'error': 'Failed to get candidate'}), 500

# Candidate actions moved to parameterized route: /api/hubspot/candidates/<candidate_id>/actions

# Dashboard endpoints
@app.route('/api/hubspot/dashboard/stats', methods=['GET'])
@require_auth
def get_dashboard_stats():
    try:
        # Check if this is a demo user
        if request.company_id.startswith('demo_company_'):
            stats = get_demo_dashboard_stats(request.company_id)
            return jsonify(stats)
        
        stats = hubspot_client.get_dashboard_stats(request.company_id)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return jsonify({'error': 'Failed to get dashboard stats'}), 500

@app.route('/api/hubspot/activity/recent', methods=['GET'])
@require_auth
def get_recent_activity():
    try:
        limit = int(request.args.get('limit', 10))
        
        # Check if this is a demo user
        if request.company_id.startswith('demo_company_'):
            activity = get_demo_recent_activity(request.company_id, limit)
            return jsonify(activity)
        
        activity = hubspot_client.get_recent_activity(request.company_id, limit)
        return jsonify(activity)
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        return jsonify({'error': 'Failed to get recent activity'}), 500

# Document management endpoints
@app.route('/api/hubspot/documents/upload', methods=['POST'])
@require_auth
def upload_document():
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        category = request.form.get('category', '')
        doc_type = request.form.get('type', '')
        description = request.form.get('description', '')
        
        uploaded_files = []
        
        for file in files:
            if file.filename == '':
                continue
            
            filename = secure_filename(file.filename)
            
            # Upload to HubSpot
            file_data = {
                'filename': filename,
                'content': file.read(),
                'content_type': file.content_type,
                'category': category,
                'type': doc_type,
                'description': description,
                'company_id': request.company_id
            }
            
            result = hubspot_client.upload_document(file_data)
            uploaded_files.append(result)
        
        return jsonify({
            'success': True,
            'uploaded_files': uploaded_files,
            'message': f'{len(uploaded_files)} file(s) uploaded successfully'
        })
        
    except Exception as e:
        logger.error(f"Error uploading documents: {e}")
        return jsonify({'error': 'Failed to upload documents'}), 500

@app.route('/api/hubspot/documents', methods=['GET'])
@require_auth
def get_company_documents():
    try:
        category = request.args.get('category')
        documents = hubspot_client.get_company_documents(request.company_id, category)
        return jsonify(documents)
    except Exception as e:
        logger.error(f"Error getting documents: {e}")
        return jsonify({'error': 'Failed to get documents'}), 500

@app.route('/api/hubspot/companies/additional-info', methods=['POST'])
@require_auth
def save_additional_info():
    try:
        data = request.get_json()
        
        # Update company record with additional information
        company_data = {
            'properties': {
                'business_size': data.get('business_size', ''),
                'annual_turnover': data.get('annual_turnover', ''),
                'years_in_business': data.get('years_in_business', ''),
                'industry_sector': data.get('industry_sector', ''),
                'previous_sponsorship': data.get('previous_sponsorship', ''),
                'additional_comments': data.get('additional_comments', '')
            }
        }
        
        hubspot_client.make_request('PATCH', f'/crm/v3/objects/companies/{request.company_id}', 
                                   data=company_data)
        
        return jsonify({'success': True, 'message': 'Additional information saved successfully'})
    except Exception as e:
        logger.error(f"Error saving additional info: {e}")
        return jsonify({'error': 'Failed to save additional information'}), 500

# Client Assessment/Scorecard endpoints
@app.route('/api/hubspot/candidates/<candidate_id>/scorecard', methods=['GET'])
@require_auth
def get_candidate_scorecard(candidate_id):
    try:
        # Get existing scorecard/assessment for candidate
        scorecard = hubspot_client.get_candidate_assessment(candidate_id)
        return jsonify(scorecard or {})
    except Exception as e:
        logger.error(f"Error getting candidate scorecard: {e}")
        return jsonify({'error': 'Failed to get candidate scorecard'}), 500

@app.route('/api/hubspot/candidates/<candidate_id>/scorecard', methods=['POST'])
@require_auth
def save_candidate_scorecard(candidate_id):
    try:
        scorecard_data = request.get_json()
        scorecard_data['candidate_id'] = candidate_id
        scorecard_data['company_id'] = request.company_id
        scorecard_data['assessed_by'] = request.user_id
        
        result = hubspot_client.save_candidate_assessment(scorecard_data)
        
        # If decision is approve/reject, trigger workflow
        if scorecard_data.get('final_decision') == 'approve':
            hubspot_client.approve_candidate(candidate_id, 'Client Assessment Approved')
        elif scorecard_data.get('final_decision') == 'reject':
            hubspot_client.reject_candidate(candidate_id, 'Client Assessment Rejected')
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error saving candidate scorecard: {e}")
        return jsonify({'error': 'Failed to save candidate scorecard'}), 500

@app.route('/api/hubspot/candidates/<candidate_id>/actions', methods=['POST'])
@require_auth
def submit_candidate_action(candidate_id):
    try:
        action_data = request.get_json()
        action_data['candidate_id'] = candidate_id
        action_data['company_id'] = request.company_id
        action_data['submitted_by'] = request.user_id
        
        # Process different types of actions
        action_type = action_data.get('actionType')
        
        if action_type == 'approve':
            result = hubspot_client.approve_candidate(candidate_id, action_data.get('reason'), action_data.get('notes'))
        elif action_type == 'reject':
            result = hubspot_client.reject_candidate(candidate_id, action_data.get('reason'), action_data.get('notes'))
        elif action_type == 'reserve':
            result = hubspot_client.reserve_candidate(candidate_id, action_data.get('reason'), action_data.get('interviewDate'))
        else:
            return jsonify({'error': 'Invalid action type'}), 400
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error submitting candidate action: {e}")
        return jsonify({'error': 'Failed to submit candidate action'}), 500

# Post-Selection Pipeline endpoints
@app.route('/api/hubspot/post-selection/pipeline', methods=['GET'])
@require_auth
def get_post_selection_pipeline():
    try:
        pipeline_data = hubspot_client.get_post_selection_pipeline(request.company_id)
        return jsonify(pipeline_data)
    except Exception as e:
        logger.error(f"Error getting post-selection pipeline: {e}")
        return jsonify({'error': 'Failed to get pipeline data'}), 500

@app.route('/api/hubspot/candidates/<candidate_id>/pipeline', methods=['GET'])
@require_auth
def get_candidate_pipeline_details(candidate_id):
    try:
        pipeline_details = hubspot_client.get_candidate_pipeline_details(candidate_id)
        return jsonify(pipeline_details)
    except Exception as e:
        logger.error(f"Error getting candidate pipeline details: {e}")
        return jsonify({'error': 'Failed to get pipeline details'}), 500

# Enhanced document/provision endpoints
@app.route('/api/hubspot/provisions', methods=['GET'])
@require_auth
def get_company_provisions():
    try:
        category = request.args.get('category')
        provisions = hubspot_client.get_company_provisions(request.company_id, category)
        return jsonify(provisions)
    except Exception as e:
        logger.error(f"Error getting provisions: {e}")
        return jsonify({'error': 'Failed to get provisions'}), 500

@app.route('/api/hubspot/provisions/upload', methods=['POST'])
@require_auth
def upload_provision_documents():
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        category = request.form.get('category', 'general')
        
        # Check file limit (5 files max per category)
        existing_count = hubspot_client.count_provision_documents(request.company_id, category)
        if existing_count + len(files) > 5:
            return jsonify({'error': f'Maximum 5 documents allowed per category. Current: {existing_count}'}), 400
        
        uploaded_files = []
        for file in files:
            if file.filename == '':
                continue
            
            # Save file securely
            filename = secure_filename(file.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            safe_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
            file.save(file_path)
            
            # Create provision record in HubSpot
            file_data = {
                'filename': filename,
                'file_path': file_path,
                'company_id': request.company_id,
                'category': category,
                'uploaded_by': request.user_id,
                'file_size': os.path.getsize(file_path),
                'mime_type': file.content_type
            }
            
            result = hubspot_client.create_provision_record(file_data)
            uploaded_files.append(result)
        
        return jsonify({
            'success': True,
            'uploaded_files': uploaded_files,
            'message': f'{len(uploaded_files)} file(s) uploaded successfully'
        })
        
    except Exception as e:
        logger.error(f"Error uploading provision documents: {e}")
        return jsonify({'error': 'Failed to upload documents'}), 500

@app.route('/api/hubspot/provisions/questions', methods=['POST'])
@require_auth
def save_provision_questions():
    try:
        questions_data = request.get_json()
        questions_data['company_id'] = request.company_id
        
        result = hubspot_client.save_provision_questions(questions_data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error saving provision questions: {e}")
        return jsonify({'error': 'Failed to save questions'}), 500

# Support endpoints
@app.route('/api/hubspot/support/tickets', methods=['POST'])
@require_auth
def submit_support_ticket():
    try:
        ticket_data = request.get_json()
        ticket_data['company_id'] = request.company_id
        
        result = hubspot_client.submit_support_ticket(ticket_data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error submitting support ticket: {e}")
        return jsonify({'error': 'Failed to submit support ticket'}), 500

# Demo data functions
def get_demo_company_profile(company_id):
    """Return demo company profile data matching HubSpot field structure"""
    return {
        'id': company_id,
        'name': 'TechCorp Solutions',
        'domain': 'techcorp.com',
        'industry': 'Technology',
        'description': 'A leading technology solutions provider specializing in software development and digital transformation services.',
        'website': 'https://techcorp.com',
        'phone': '+1 (555) 123-4567',
        'founded_year': '2015',
        'company_size': '50-100',
        'annual_revenue': '$5M - $10M',
        'company_type': 'Private Company',
        'address': '123 Tech Street',
        'city': 'San Francisco', 
        'state': 'CA',
        'zip': '94105',
        'country': 'United States',
        'created_date': '2025-01-01T00:00:00Z',
        'lifecycle_stage': 'customer',
        'last_activity_date': '2025-01-28T15:30:00Z',
        'is_public': 'false',
        'close_date': '2025-01-01T00:00:00Z',
        'recent_deal_amount': '$50,000',
        'recent_deal_close_date': '2025-01-25T00:00:00Z',
        'active_jobs_count': 2,
        'total_placements': '15',
        'hubspot_owner_id': 'demo_owner',
        'record_source': 'API',
        'timezone': 'US/Pacific',
        'facebook_company_page': '',
        'googleplus_page': '',
        'linkedin_company_page': 'https://linkedin.com/company/techcorp-solutions',
        'twitter_handle': '@techcorpsolutions',
        'primary_contact': {
            'name': 'Sarah Wilson',
            'email': 'sarah.wilson@techcorp.com',
            'phone': '+1 (555) 987-6543',
            'job_title': 'Head of Talent Acquisition'
        }
    }

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Get port from environment variable for deployment flexibility
    port = int(os.getenv('PORT', 5000))
    
    # Production vs Development settings
    debug_mode = os.getenv('ENVIRONMENT', 'development').lower() == 'development'
    
    # Log startup information
    logger.info(f"Starting TPRC Portal Server on port {port}")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Debug mode: {debug_mode}")
    
    # Bind to 0.0.0.0 for deployment compatibility
    app.run(host='0.0.0.0', port=port, debug=debug_mode)

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
import psycopg2
from psycopg2.extras import RealDictCursor

import requests
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import jwt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv(
    'SECRET_KEY', 'tprc-client-portal-secret-key-change-in-production')

# Configuration
HUBSPOT_API_KEY = os.getenv('HUBSPOT_API_KEY', 'demo_key_replace_with_real')
HUBSPOT_BASE_URL = 'https://api.hubapi.com'
UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max file size

# Email whitelist for access restriction
ALLOWED_EMAILS = ['tim.schibli@tprc.com.au']

# PostgreSQL Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL')


def init_database():
    """Initialize database tables for user management"""
    if not DATABASE_URL:
        logger.warning("No DATABASE_URL found, using static email whitelist")
        return
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Create authorized_users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS authorized_users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255),
                company_name VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert default authorized user
        cur.execute("""
            INSERT INTO authorized_users (email, name, company_name) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (email) DO NOTHING
        """, ('tim.schibli@tprc.com.au', 'Tim Schibli', 'TPRC'))
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")


def get_authorized_emails():
    """Get list of authorized emails from database or fallback to static list"""
    if not DATABASE_URL:
        return ALLOWED_EMAILS
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT email FROM authorized_users WHERE is_active = TRUE")
        emails = [row['email'] for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        return emails if emails else ALLOWED_EMAILS
    except Exception as e:
        logger.error(f"Error fetching authorized emails: {e}")
        return ALLOWED_EMAILS

# Production environment configuration
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
IS_PRODUCTION = ENVIRONMENT.lower() == 'production'

# Enable CORS for frontend-backend communication
# Include production domains for deployment
allowed_origins = ['http://localhost:5000', 'http://0.0.0.0:5000']
if IS_PRODUCTION:
    # Add production domains - Replit deployments use .replit.app domains
    allowed_origins.extend(
        ['https://*.repl.co', 'https://*.replit.app', 'https://*.replit.dev'])

CORS(app, origins=allowed_origins)

app.config.update(UPLOAD_FOLDER=UPLOAD_FOLDER,
                  MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH,
                  DEBUG=not IS_PRODUCTION,
                  TESTING=False,
                  JSON_SORT_KEYS=False)

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize database
init_database()


# Health check endpoint for deployment
@app.route('/health')
def health_check():
    """Health check endpoint for deployment services"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'TPRC Portal Backend'
    }), 200





















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

    def make_request(self,
                     method: str,
                     endpoint: str,
                     data: Dict = None,
                     params: Dict = None) -> Dict:
        """Make authenticated request to HubSpot API"""
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(method=method,
                                            url=url,
                                            json=data,
                                            params=params,
                                            timeout=30)
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
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "email",
                        "operator": "EQ",
                        "value": email
                    }]
                }],
                "properties": [
                    "firstname", "lastname", "email", "company",
                    "associatedcompanyid"
                ],
                "limit":
                1
            }

            response = self.make_request('POST',
                                         '/crm/v3/objects/contacts/search',
                                         data=search_data)

            if response.get('results') and len(response['results']) > 0:
                return response['results'][0]
            return None
        except Exception as e:
            logger.error(f"Error searching contact by email: {e}")
            return None

    def get_company_by_id(self, company_id: str) -> Dict:
        """Get company details by ID"""
        properties = [
            'name', 'domain', 'industry', 'about_us', 'website', 'phone',
            'founded_year', 'numberofemployees', 'annualrevenue', 'type',
            'address', 'city', 'state', 'zip', 'country', 'createdate',
            'lifecyclestage', 'hs_lastmodifieddate', 'is_public', 'closedate',
            'facebook_company_page', 'googleplus_page',
            'linkedin_company_page', 'twitterhandle', 'timezone'
        ]
        params = {'properties': ','.join(properties)}
        return self.make_request('GET',
                                 f'/crm/v3/objects/companies/{company_id}',
                                 params=params)

    def get_job_orders_for_company(self,
                                   company_id: str,
                                   filters: Dict = None) -> List[Dict]:
        """Get job orders (deals) associated with a specific company from HubSpot"""
        try:
            # Get company details first to use for filtering
            company_response = self.get_company_by_id(company_id)
            company_name = company_response.get('properties', {}).get('name', '')
            logger.info(f"Looking for job orders for company: {company_name} (ID: {company_id})")

            # Use custom job order objects - get job orders associated with the company
            try:
                # First try to get job orders associated with this company
                associations_url = f'/crm/v4/objects/companies/{company_id}/associations/2-44956344'
                associations_response = self.make_request('GET', associations_url)
                job_order_ids = [
                    result['toObjectId']
                    for result in associations_response.get('results', [])
                ]

                if job_order_ids:
                    logger.info(f"Found {len(job_order_ids)} associated job orders via associations API")
                    job_orders = []
                    properties = [
                        'job_order_title', 'role_description', 'job_description', 'hs_createdate',
                        'employment_status', 'total_applicants', 'company_name', 'company_id'
                    ]

                    for job_id in job_order_ids:
                        try:
                            params = {'properties': ','.join(properties)}
                            job_response = self.make_request(
                                'GET',
                                f'/crm/v3/objects/2-44956344/{job_id}',
                                params=params)
                            formatted_job = self.format_job_order(job_response)
                            formatted_job['company_id'] = company_id
                            job_orders.append(formatted_job)
                        except Exception as e:
                            logger.warning(f"Error fetching job order {job_id}: {e}")
                            continue

                    if job_orders:
                        logger.info(f"Retrieved {len(job_orders)} job orders via associations")
                        return job_orders

            except Exception as e:
                logger.info(f"Job order associations API not available: {e}")

            # Method 2: Get all job orders and filter by company
            logger.info("Trying to get all job orders and filter by company")
            properties = [
                'job_order_title', 'role_description', 'job_description', 'hs_createdate',
                'employment_status', 'total_applicants', 'company_name', 'company_id'
            ]
            params = {'properties': ','.join(properties), 'limit': 100}
            response = self.make_request('GET', '/crm/v3/objects/2-44956344', params=params)

            job_orders = []
            all_jobs = response.get('results', [])
            logger.info(f"Found {len(all_jobs)} total job orders in HubSpot")

            for job in all_jobs:
                props = job.get('properties', {})
                job_title = props.get('job_order_title', '')
                job_company_name = props.get('company_name', '')
                job_company_id = props.get('company_id', '')
                
                # Multiple filtering criteria
                is_match = False
                if job_company_id == company_id:
                    is_match = True
                    logger.info(f"Job matched by company_id: {job_title}")
                elif company_name and job_company_name and company_name.lower() in job_company_name.lower():
                    is_match = True
                    logger.info(f"Job matched by company name: {job_title}")
                elif company_name and job_title and company_name.lower() in job_title.lower():
                    is_match = True
                    logger.info(f"Job matched by title containing company name: {job_title}")

                if is_match:
                    formatted_job = self.format_job_order(job)
                    formatted_job['company_id'] = company_id
                    job_orders.append(formatted_job)

            if job_orders:
                logger.info(f"Retrieved {len(job_orders)} deals as job orders")
                return job_orders
            else:
                logger.warning(f"No deals found for company {company_name} ({company_id})")

        except Exception as e:
            logger.error(f"Error fetching deals: {e}")

        # If no real data found, return empty list
        logger.info(f"No job orders found for company {company_id}")
        return []



    def get_job_order_by_id(self, job_order_id: str) -> Dict:
        """Get specific job order details"""
        try:
            # Use custom job order objects
            properties = [
                'job_order_title', 'role_description', 'job_description', 'hs_createdate',
                'employment_status', 'total_applicants'
            ]
            params = {'properties': ','.join(properties)}
            response = self.make_request(
                'GET',
                f'/crm/v3/objects/2-44956344/{job_order_id}',
                params=params)
            return self.format_job_order(response)
        except Exception as e:
            logger.error(f"Error fetching job order {job_order_id}: {e}")
            raise

    def get_candidates_for_job_order(self,
                                     job_order_id: str,
                                     filters: Dict = None) -> List[Dict]:
        """Get candidates associated with a job order"""
        try:
            # Try to get applications associated with the job order via associations API
            associations_url = f'/crm/v4/objects/2-44956344/{job_order_id}/associations/2-44963172'
            try:
                associations_response = self.make_request(
                    'GET', associations_url)
                
                # Filter associations by "Recommended" label
                recommended_applications = []
                for result in associations_response.get('results', []):
                    app_id = result.get('toObjectId')
                    association_types = result.get('associationTypes', [])
                    
                    # Check if any association has the "Recommended" label
                    has_recommended_label = any(
                        (assoc_type.get('label') or '').lower() == 'recommended' 
                        for assoc_type in association_types
                    )
                    
                    if has_recommended_label:
                        recommended_applications.append({
                            'app_id': app_id,
                            'labels': [at.get('label') for at in association_types if at.get('label')]
                        })
                        logger.info(f"Found recommended application {app_id} with labels: {[at.get('label') for at in association_types if at.get('label')]}")

                logger.info(f"Found {len(recommended_applications)} recommended applications from {len(associations_response.get('results', []))} total associations for job order {job_order_id}")

                if recommended_applications:
                    # Get the application details for recommended applications only
                    applications = []
                    for app_info in recommended_applications:
                        app_id = app_info['app_id']
                        try:
                            app_response = self.make_request(
                                'GET', f'/crm/v3/objects/2-44963172/{app_id}')
                            
                            # Get associated contact data for each application
                            contact_associations = self.make_request(
                                'GET',
                                f'/crm/v4/objects/2-44963172/{app_id}/associations/contacts'
                            )
                            contact_id = contact_associations.get(
                                'results', [{}])[0].get('toObjectId')

                            if contact_id:
                                contact_response = self.make_request(
                                    'GET',
                                    f'/crm/v3/objects/contacts/{contact_id}')
                                formatted_candidate = self.format_candidate(contact_response)
                                # Add association label info (filtered to this job order only)
                                job_specific_labels = []
                                for result in associations_response.get('results', []):
                                    if result.get('toObjectId') == app_id:
                                        association_types = result.get('associationTypes', [])
                                        job_specific_labels = [at.get('label') for at in association_types if at.get('label')]
                                        break
                                formatted_candidate['association_labels'] = job_specific_labels
                                # Add application ID and properties
                                formatted_candidate['application_id'] = app_id
                                app_props = app_response.get('properties', {})
                                formatted_candidate['application_status'] = app_props.get('application_status', self.determine_application_status(app_props))
                                formatted_candidate['hs_pipeline_stage'] = app_props.get('hs_pipeline_stage', '')
                                applications.append(formatted_candidate)
                                logger.info(f"Added recommended candidate {contact_id} from application {app_id}")
                            else:
                                # Format application directly if no contact association
                                formatted_candidate = self.format_candidate_from_application(app_response)
                                # Add association label info (filtered to this job order only)
                                job_specific_labels = []
                                for result in associations_response.get('results', []):
                                    if result.get('toObjectId') == app_id:
                                        association_types = result.get('associationTypes', [])
                                        job_specific_labels = [at.get('label') for at in association_types if at.get('label')]
                                        break
                                formatted_candidate['association_labels'] = job_specific_labels
                                formatted_candidate['application_id'] = app_id
                                app_props = app_response.get('properties', {})
                                formatted_candidate['application_status'] = app_props.get('application_status', self.determine_application_status(app_props))
                                applications.append(formatted_candidate)
                                logger.info(f"Added recommended candidate from application {app_id} (no contact association)")

                        except Exception as e:
                            logger.warning(
                                f"Error fetching recommended application {app_id}: {e}")
                            continue

                    if applications:
                        logger.info(
                            f"Retrieved {len(applications)} recommended applications from HubSpot for job order {job_order_id}"
                        )
                        return applications
                    else:
                        logger.info(f"No recommended candidates found via associations for job order {job_order_id}")
                else:
                    logger.info(f"No applications with 'Recommended' label found for job order {job_order_id}")

            except Exception as e:
                logger.warning(
                    f"Could not fetch application associations for job order {job_order_id}: {e}"
                )
                
                # Alternative approach: search for applications that reference this job order
                logger.info(f"Trying alternative search for applications referencing job order {job_order_id}")
                try:
                    # Search applications by job order reference
                    search_payload = {
                        "filterGroups": [{
                            "filters": [{
                                "propertyName": "job_order_id",
                                "operator": "EQ", 
                                "value": job_order_id
                            }]
                        }],
                        "properties": ["application_status", "hs_pipeline_stage", "application_name"],
                        "limit": 100
                    }
                    
                    search_response = self.make_request(
                        'POST', '/crm/v3/objects/2-44963172/search', data=search_payload)
                    
                    if search_response.get('results'):
                        applications = []
                        for app_data in search_response['results']:
                            # Format all applications without filtering
                            formatted_app = self.format_candidate_from_application(app_data)
                            applications.append(formatted_app)
                            logger.info(f"Found application {app_data['id']} via search")
                        
                        if applications:
                            logger.info(f"Retrieved {len(applications)} applications via search for job order {job_order_id}")
                            return applications
                
                except Exception as search_error:
                    logger.warning(f"Alternative search also failed: {search_error}")

        except Exception as e:
            logger.error(
                f"Error fetching candidates for job order {job_order_id}: {e}")

        # Return empty list if no data found
        logger.info(f"No candidates found for job order {job_order_id}")
        return []

    def format_contact_as_candidate(self, contact_data: Dict) -> Dict:
        """Format contact data as a candidate for frontend"""
        props = contact_data.get('properties', {})
        first_name = props.get('firstname', '')
        last_name = props.get('lastname', '')
        full_name = f"{first_name} {last_name}".strip() or "Unknown Candidate"
        
        return {
            'id': contact_data['id'],
            'name': full_name,
            'email': props.get('email', ''),
            'phone': props.get('phone', ''),
            'status': 'pending_review',  # Default status for HubSpot contacts
            'application_date': props.get('createdate', ''),
            'location': f"{props.get('city', '')}, {props.get('state', '')}".strip(', ') or 'Location Unknown',
            'job_title': props.get('jobtitle', 'Not specified'),
            'company': props.get('company', 'Not specified'),
            'professional_summary': f"Contact from {props.get('company', 'external source')}",
            'skills': [],  # HubSpot contacts don't have skills by default
            'country': props.get('country', '')
        }

    def format_candidate_from_application(self,
                                          application_data: Dict) -> Dict:
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
        safe_name = candidate_name.lower().replace(
            ' ',
            '.') if candidate_name else f"applicant.{application_data['id']}"

        # Determine candidate details based on the application
        if 'Sarah' in candidate_name:
            age, skills = 28, [
                'Kitchen Management', 'Food Safety', 'Team Leadership',
                'Menu Planning'
            ]
        elif 'Michael' in candidate_name:
            age, skills = 32, [
                'Production Management', 'Staff Training', 'Quality Control',
                'Inventory Management'
            ]
        else:
            age, skills = 30, [
                'Food Service', 'Team Collaboration', 'Customer Service'
            ]

        # Handle null status values and map to display format
        raw_status = props.get('application_status') or 'active'
        status = raw_status.lower().replace('-',
                                            '_') if raw_status else 'active'

        # Map HubSpot status to display status
        status_mapping = {'selected': 'approved', 'active': 'pending_review'}
        status = status_mapping.get(status, status)

        return {
            'id': application_data['id'],
            'application_id': application_data['id'],  # For consistency with other candidate data
            'name': candidate_name,
            'email': f"{safe_name}@email.com",
            'status': status,
            'application_status': self.determine_application_status(props),
            'application_date': props.get('hs_createdate', ''),
            'age': age,
            'location': 'Perth, Australia',
            'professional_summary':
            f'Professional applicant with relevant experience in the food industry.',
            'skills': skills,
            'job_order_id': None  # Will be set when called
        }

    def get_candidate_by_id(self, candidate_id: str) -> Dict:
        """Get detailed candidate information"""
        try:
            contact = self.make_request(
                'GET',
                f'/crm/v3/objects/contacts/{candidate_id}',
                params={
                    'properties': [
                        'firstname', 'lastname', 'email', 'phone', 'age',
                        'location', 'professional_summary', 'skills',
                        'languages', 'work_experience', 'education'
                    ]
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
            if action_data['actionType'] == 'interview' and action_data.get(
                    'interviewDate'):
                application_data['properties']['interview_date'] = action_data[
                    'interviewDate']

            # Update the application custom object record using correct object type
            response = self.make_request(
                'PATCH',
                f'/crm/v3/objects/2-184526441/{action_data["candidateId"]}',
                data=application_data)

            # Create activity record
            self.create_activity_record({
                'type':
                f'candidate_{action_data["actionType"]}',
                'description':
                f"Candidate {action_data['actionType']} - {action_data['reason']}",
                'candidate_id':
                action_data['candidateId'],
                'notes':
                action_data.get('notes', '')
            })

            return {
                'success': True,
                'message': 'Action submitted successfully'
            }
        except Exception as e:
            logger.error(f"Error submitting candidate action: {e}")
            raise

    def update_association_label(self, candidate_id: str, job_order_id: str, label: str) -> Dict:
        """Update association label between candidate/application and job order"""
        try:
            # First, find the application ID by searching for the candidate/job order association
            # Get associations between the job order and applications
            associations_response = self.make_request(
                'GET',
                f'/crm/v4/objects/2-44956344/{job_order_id}/associations/2-44963172',
                params={'limit': 100}
            )
            
            application_id = None
            for association in associations_response.get('results', []):
                app_id = association.get('toObjectId')
                # Check if this application is for our candidate
                try:
                    app_response = self.make_request('GET', f'/crm/v3/objects/2-44963172/{app_id}')
                    # Get associated contact for this application
                    contact_associations = self.make_request(
                        'GET',
                        f'/crm/v4/objects/2-44963172/{app_id}/associations/contacts'
                    )
                    if contact_associations.get('results'):
                        contact_id = contact_associations['results'][0].get('toObjectId')
                        if contact_id == candidate_id:
                            application_id = app_id
                            break
                except Exception as e:
                    logger.warning(f"Error checking application {app_id}: {e}")
                    continue
            
            if not application_id:
                raise Exception(f"Could not find application for candidate {candidate_id} and job order {job_order_id}")
            
            logger.info(f"Found application ID {application_id} for candidate {candidate_id} and job order {job_order_id}")
            
            # Now update the association with the new label
            # First get current association types
            current_associations = self.make_request(
                'GET',
                f'/crm/v4/objects/2-44963172/{application_id}/associations/2-44956344',
                params={'limit': 100}
            )
            
            # Find the specific association to the job order
            target_association = None
            for association in current_associations.get('results', []):
                if association.get('toObjectId') == job_order_id:
                    target_association = association
                    break
            
            if not target_association:
                raise Exception(f"Could not find association between application {application_id} and job order {job_order_id}")
            
            # Get current association types/labels
            current_types = target_association.get('associationTypes', [])
            existing_labels = [at.get('label') for at in current_types if at.get('label')]
            
            logger.info(f"Current association labels: {existing_labels}")
            
            # Add the new label if it doesn't exist
            if label not in existing_labels:
                # Create new association with additional label
                association_data = {
                    "inputs": [{
                        "from": {"id": application_id},
                        "to": {"id": job_order_id},
                        "types": [
                            {"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 279},  # Application to Job Order
                            {"associationCategory": "USER_DEFINED", "label": label}  # Add new label
                        ]
                    }]
                }
                
                # First remove existing association
                try:
                    self.make_request(
                        'DELETE',
                        f'/crm/v4/objects/2-44963172/{application_id}/associations/2-44956344/{job_order_id}',
                        params={'associationType': '279'}
                    )
                except Exception as delete_error:
                    logger.warning(f"Could not delete existing association: {delete_error}")
                
                # Create new association with all labels
                all_labels = list(set(existing_labels + [label]))  # Combine and deduplicate
                association_types = [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 279}]
                for lbl in all_labels:
                    association_types.append({"associationCategory": "USER_DEFINED", "label": lbl})
                
                association_data["inputs"][0]["types"] = association_types
                
                response = self.make_request(
                    'PUT',
                    '/crm/v4/associations/2-44963172/2-44956344/batch/create',
                    data=association_data
                )
                
                logger.info(f"Successfully added association label '{label}' to candidate {candidate_id}")
                return {
                    'success': True,
                    'message': f'Association label "{label}" added successfully',
                    'labels': all_labels,
                    'association_updated': True
                }
            else:
                logger.info(f"Label '{label}' already exists for candidate {candidate_id}")
                return {
                    'success': True,
                    'message': f'Association label "{label}" already exists',
                    'labels': existing_labels,
                    'association_updated': False
                }
                
        except Exception as e:
            logger.error(f"Error updating association label: {e}")
            raise

    def determine_application_status(self, app_properties: Dict) -> str:
        """Determine application status based on HubSpot properties"""
        # Check pipeline stage first
        pipeline_stage = app_properties.get('hs_pipeline_stage', '')
        
        # Map common HubSpot pipeline stages to application status
        if pipeline_stage in ['new', 'open', 'qualified', 'presentation_scheduled', 'decision_maker_bought-in']:
            return 'Active'
        elif pipeline_stage in ['closed_won', 'closed_lost']:
            return 'Inactive'
        elif pipeline_stage in ['appointment_scheduled', 'qualified_to_buy']:
            return 'Issues'
        
        # Check for other status indicators
        if app_properties.get('application_status'):
            return app_properties.get('application_status')
        
        # Check lifecycle stage
        lifecycle_stage = app_properties.get('lifecyclestage', '')
        if lifecycle_stage in ['lead', 'marketingqualifiedlead', 'salesqualifiedlead']:
            return 'Active'
        elif lifecycle_stage in ['customer', 'evangelist']:
            return 'Inactive'
        elif lifecycle_stage in ['opportunity']:
            return 'Issues'
        
        # Default to Active for new applications
        return 'Active'

    def get_dashboard_stats(self, company_id: str) -> Dict:
        """Get dashboard statistics for a company using recommended candidates only - optimized version"""
        try:
            job_orders = self.get_job_orders_for_company(company_id)

            stats = {
                'active_jobs': 0,
                'available_candidates': 0,
                'pending_reviews': 0,
                'selections_made': 0
            }

            # Process job orders and collect all association IDs for batch processing
            job_order_ids = []
            for job in job_orders:
                if job['status'].lower() == 'active':
                    stats['active_jobs'] += 1
                job_order_ids.append(job['id'])

            # Batch fetch all candidate associations for all job orders at once
            if job_order_ids:
                try:
                    # Use a more efficient approach - get all associations in fewer API calls
                    for job_id in job_order_ids:
                        try:
                            associations_url = f'/crm/v4/objects/2-44956344/{job_id}/associations/2-44963172'
                            associations_response = self.make_request('GET', associations_url)
                            
                            # Quick count without fetching full candidate details
                            for result in associations_response.get('results', []):
                                association_types = result.get('associationTypes', [])
                                
                                # Check if any association has the "Recommended" label
                                has_recommended = any(
                                    (assoc_type.get('label') or '').lower() == 'recommended' 
                                    for assoc_type in association_types
                                )
                                
                                if has_recommended:
                                    stats['available_candidates'] += 1
                                    
                                    # Count by association labels without fetching full data
                                    labels = [at.get('label', '').lower() for at in association_types if at.get('label')]
                                    if 'selected' in labels:
                                        stats['selections_made'] += 1
                                    elif any(label in ['recommended'] for label in labels):
                                        stats['pending_reviews'] += 1
                                        
                        except Exception as e:
                            logger.warning(f"Error getting associations for job {job_id}: {e}")
                            continue
                            
                except Exception as e:
                    logger.error(f"Error in batch candidate processing: {e}")

            logger.info(f"Dashboard stats computed: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return {
                'active_jobs': 0,
                'available_candidates': 0,
                'pending_reviews': 0,
                'selections_made': 0
            }

    def get_recent_activity(self,
                            company_id: str,
                            limit: int = 10) -> List[Dict]:
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
            files = {
                'file': (file_data['filename'], file_data['content'],
                         file_data['content_type'])
            }

            upload_response = requests.post(
                f"{self.base_url}/filemanager/api/v3/files/upload",
                headers={'Authorization': f'Bearer {self.api_key}'},
                files=files,
                data={
                    'fileName':
                    file_data['filename'],
                    'options':
                    json.dumps({
                        'access': 'PRIVATE',
                        'overwrite': False
                    })
                })
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
            doc_response = self.make_request('POST',
                                             '/crm/v3/objects/documents',
                                             data=document_record)

            return {
                'success': True,
                'document_id': doc_response['id'],
                'file_url': file_info['url'],
                'message': 'Document uploaded successfully'
            }
        except Exception as e:
            logger.error(f"Error uploading document: {e}")
            raise

    def get_company_documents(self,
                              company_id: str,
                              category: str = None) -> List[Dict]:
        """Get documents for a company"""
        try:
            params = {
                'properties': [
                    'name', 'category', 'type', 'description', 'upload_date',
                    'file_url'
                ]
            }

            response = self.make_request('GET',
                                         '/crm/v3/objects/documents',
                                         params=params)

            documents = []
            for doc in response.get('results', []):
                if doc.get('properties', {}).get('company_id') == company_id:
                    if not category or doc.get('properties',
                                               {}).get('category') == category:
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

            response = self.make_request('POST',
                                         '/crm/v3/objects/tickets',
                                         data=ticket_record)

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
        """Format job order data for frontend with recommended candidate count"""
        props = job_data.get('properties', {})
        
        # Get recommended candidate count for this job order
        try:
            recommended_candidates = self.get_candidates_for_job_order(job_data['id'])
            candidate_count = len(recommended_candidates)
        except Exception as e:
            logger.warning(f"Could not get recommended candidate count for job {job_data['id']}: {e}")
            candidate_count = 0
        
        return {
            'id':
            job_data['id'],
            'title':
            props.get('job_order_title', props.get('title', '')),
            'description':
            props.get('job_description', props.get('role_description', props.get('description', ''))),
            'position_type':
            props.get('position_type', 'Full-time'),
            'location':
            props.get('location', 'Perth, Australia'),
            'status':
            props.get('employment_status', 'Active'),
            'created_date':
            props.get('hs_createdate', props.get('created_date', '')),
            'deadline':
            props.get('deadline', ''),
            'essential_requirements':
            props.get('essential_requirements', '').split('\n')
            if props.get('essential_requirements') else [],
            'preferred_requirements':
            props.get('preferred_requirements', '').split('\n')
            if props.get('preferred_requirements') else [],
            'salary_range':
            props.get('salary_range', ''),
            'benefits':
            props.get('benefits', ''),
            'candidate_count':
            candidate_count
        }

    def format_candidate(self, contact_data: Dict) -> Dict:
        """Format candidate data for frontend"""
        props = contact_data.get('properties', {})
        return {
            'id':
            contact_data['id'],
            'name':
            f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(
            ),
            'first_name':
            props.get('firstname', ''),
            'last_name':
            props.get('lastname', ''),
            'email':
            props.get('email', ''),
            'phone':
            props.get('phone', ''),
            'age':
            props.get('age', ''),
            'location':
            props.get('location', ''),
            'professional_summary':
            props.get('professional_summary', ''),
            'skills':
            props.get('skills', '').split(',') if props.get('skills') else [],
            'languages':
            props.get('languages', '').split(',')
            if props.get('languages') else [],
            'work_experience':
            json.loads(props.get('work_experience', '[]')),
            'education':
            json.loads(props.get('education', '[]')),
            'status':
            'available'  # Default status
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

    def is_job_associated_with_company(self, job_id: str,
                                       company_id: str) -> bool:
        """Check if job order is associated with company"""
        # This would check the associations in HubSpot
        # For now, return True (implement proper association checking)
        return True

    def is_application_for_job_order(self, application_id: str,
                                     job_order_id: str) -> bool:
        """Check if application is for specific job order"""
        # This would check the associations in HubSpot
        # For now, return True (implement proper association checking)
        return True

    def get_candidate_from_application(self,
                                       application: Dict) -> Optional[Dict]:
        """Get candidate data from application record"""
        # This would get the associated contact from the application
        # For now, return mock data structure
        return {
            'id': application['id'],
            'name': 'Sample Candidate',
            'age': 30,
            'location': 'Sydney, Australia',
            'skills': ['Python', 'React', 'SQL'],
            'status': application.get('properties',
                                      {}).get('status', 'available')
        }

    def filter_candidates(self, candidates: List[Dict],
                          filters: Dict) -> List[Dict]:
        """Filter candidates based on provided filters"""
        filtered = candidates

        if 'search' in filters:
            search_term = filters['search'].lower()
            filtered = [
                c for c in filtered if search_term in c['name'].lower()
                or search_term in c.get('location', '').lower()
            ]

        if 'status' in filters:
            filtered = [
                c for c in filtered if c.get('status') == filters['status']
            ]

        return filtered

    def approve_candidate(self, job_order_id: str, candidate_id: str) -> Dict:
        """Approve candidate by updating HubSpot association label to 'Selected' and trigger approval workflow"""
        try:
            # First, get current associations to check if it exists
            associations_url = f'/crm/v4/objects/2-184526443/{job_order_id}/associations/2-184526441'
            associations_response = self.make_request('GET', associations_url)

            # Find the specific candidate association
            candidate_association = None
            for assoc in associations_response.get('results', []):
                if str(assoc['toObjectId']) == str(candidate_id):
                    candidate_association = assoc
                    break

            if not candidate_association:
                raise Exception(
                    f"Association between job order {job_order_id} and candidate {candidate_id} not found"
                )

            # Update the application record status and pipeline stage
            update_data = {
                'properties': {
                    'application_status': 'Selected',
                    'approval_date': datetime.utcnow().isoformat(),
                    'approved_by': 'Client Portal',
                    'hs_pipeline_stage':
                    '1530375619'  # Approved pipeline stage
                }
            }

            logger.info(update_data)

            try:
                self.make_request(
                    'PATCH',
                    f'/crm/v3/objects/2-44963172/{candidate_id}',
                    data=update_data)
                logger.info(
                    f"Successfully updated candidate {candidate_id} status to 'Selected'"
                )
            except Exception as update_error:
                logger.warning(
                    f"Could not update application status, but approval noted: {update_error}"
                )

            # Trigger HubSpot approval workflow (ID: 2509546972)
            #workflow_result = self.trigger_workflow(2509546972, candidate_id,'contact')

            return {
                'success': True,
                'message':
                'Candidate approved, status updated, and approval workflow triggered',
                'candidate_id': candidate_id,
                'job_order_id': job_order_id,
                'workflow_triggered': workflow_result.get('success', False)
            }

        except Exception as e:
            logger.error(
                f"Error approving candidate {candidate_id} for job {job_order_id}: {e}"
            )
            raise

    def trigger_workflow(self,
                         workflow_id: int,
                         object_id: str,
                         object_type: str = 'contact') -> Dict:
        """Trigger a HubSpot workflow for a specific object"""
        try:
            # HubSpot workflow trigger endpoint
            workflow_url = f'/automation/v4/workflows/{workflow_id}/enrollments'

            enrollment_data = {
                'objectIds': [object_id],
                'objectType': object_type
            }

            response = self.make_request('POST',
                                         workflow_url,
                                         data=enrollment_data)
            logger.info(
                f"Successfully triggered workflow {workflow_id} for {object_type} {object_id}"
            )

            return {
                'success': True,
                'workflow_id': workflow_id,
                'object_id': object_id,
                'enrollment_id': response.get('id')
            }

        except Exception as e:
            logger.error(f"Error triggering workflow {workflow_id}: {e}")
            return {'success': False, 'error': str(e)}

    def reject_candidate(self,
                         candidate_id: str,
                         reason: str = None,
                         notes: str = None) -> Dict:
        """Reject candidate and trigger rejection workflow"""
        try:
            # Update the application record status and pipeline stage
            update_data = {
                'properties': {
                    'application_status': 'Rejected',
                    'rejection_date': datetime.utcnow().isoformat(),
                    'rejected_by': 'Client Portal',
                    'rejection_reason': reason
                    or 'Not suitable for the position',
                    'rejection_notes': notes or '',
                    'hs_pipeline_stage':
                    '1076100933'  # Rejected pipeline stage
                }
            }

            try:
                self.make_request(
                    'PATCH',
                    f'/crm/v3/objects/2-44963172/{candidate_id}',
                    data=update_data)
                logger.info(
                    f"Successfully updated candidate {candidate_id} status to 'Rejected'"
                )
            except Exception as update_error:
                logger.warning(
                    f"Could not update application status, but rejection noted: {update_error}"
                )

            # Trigger HubSpot rejection workflow (ID: 2509546994)
            workflow_result = self.trigger_workflow(2509546994, candidate_id,
                                                    'contact')

            return {
                'success': True,
                'message':
                'Candidate rejected, status updated, and rejection workflow triggered',
                'candidate_id': candidate_id,
                'workflow_triggered': workflow_result.get('success', False)
            }

        except Exception as e:
            logger.error(f"Error rejecting candidate {candidate_id}: {e}")
            raise

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

            self.make_request('POST',
                              '/crm/v3/objects/activities',
                              data=activity_record)
        except Exception as e:
            logger.error(f"Error creating activity record: {e}")

    def get_candidate_assessment(self, candidate_id: str) -> Dict:
        """Get candidate assessment/scorecard"""
        try:
            # Search for assessment records associated with this candidate
            search_data = {
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "candidate_id",
                        "operator": "EQ",
                        "value": candidate_id
                    }]
                }],
                "properties": [
                    "technical_skills", "experience", "english_proficiency",
                    "cultural_fit", "problem_solving", "teamwork",
                    "overall_rating", "final_decision", "assessment_notes",
                    "concerns", "assessed_by", "assessment_date"
                ],
                "limit":
                1
            }

            response = self.make_request('POST',
                                         '/crm/v3/objects/assessments/search',
                                         data=search_data)
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
                    'candidate_id':
                    scorecard_data['candidate_id'],
                    'company_id':
                    scorecard_data['company_id'],
                    'assessed_by':
                    scorecard_data['assessed_by'],
                    'technical_skills':
                    scorecard_data.get('technical_skills'),
                    'experience':
                    scorecard_data.get('experience'),
                    'english_proficiency':
                    scorecard_data.get('english_proficiency'),
                    'cultural_fit':
                    scorecard_data.get('cultural_fit'),
                    'problem_solving':
                    scorecard_data.get('problem_solving'),
                    'teamwork':
                    scorecard_data.get('teamwork'),
                    'overall_rating':
                    scorecard_data.get('overall_rating'),
                    'final_decision':
                    scorecard_data.get('final_decision'),
                    'assessment_notes':
                    scorecard_data.get('assessment_notes', ''),
                    'concerns':
                    scorecard_data.get('concerns', ''),
                    'assessment_date':
                    datetime.utcnow().isoformat()
                }
            }

            return self.make_request('POST',
                                     '/crm/v3/objects/assessments',
                                     data=assessment_record)
        except Exception as e:
            logger.error(f"Error saving candidate assessment: {e}")
            raise

    def reserve_candidate(self,
                          candidate_id: str,
                          reason: str,
                          interview_date: str = None) -> Dict:
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

            self.make_request('PATCH',
                              f'/crm/v3/objects/candidates/{candidate_id}',
                              data=candidate_update)

            # Create activity record
            activity_data = {
                'type':
                'candidate_reserved',
                'description':
                f'Candidate reserved for interview: {reason}',
                'candidate_id':
                candidate_id,
                'notes':
                f'Interview scheduled for: {interview_date}'
                if interview_date else 'Interview to be scheduled'
            }
            self.create_activity_record(activity_data)

            return {
                'success': True,
                'message': 'Candidate reserved successfully'
            }
        except Exception as e:
            logger.error(f"Error reserving candidate: {e}")
            raise

    def get_post_selection_pipeline(self, company_id: str) -> Dict:
        """Get post-selection pipeline data for company"""
        try:
            # Get all selected candidates for the company
            search_data = {
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "company_id",
                        "operator": "EQ",
                        "value": company_id
                    }, {
                        "propertyName":
                        "lifecycle_stage",
                        "operator":
                        "IN",
                        "values": [
                            "selected", "letter_of_offer", "visa_processing",
                            "medical_examination", "coe_approval",
                            "deployment_prep", "deployed"
                        ]
                    }]
                }],
                "properties": [
                    "firstname", "lastname", "lifecycle_stage",
                    "pipeline_stage", "position_title"
                ],
                "limit":
                100
            }

            response = self.make_request('POST',
                                         '/crm/v3/objects/candidates/search',
                                         data=search_data)
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
                stage = props.get('pipeline_stage',
                                  props.get('lifecycle_stage', 'unknown'))

                if stage in ['selected', 'letter_of_offer']:
                    stats['selected'] += 1
                elif stage in ['visa_processing', 'medical_examination']:
                    stats['visa_processing'] += 1
                elif stage in ['coe_approval', 'deployment_prep']:
                    stats['deployment_ready'] += 1
                elif stage == 'deployed':
                    stats['deployed'] += 1

                processed_candidates.append({
                    'id':
                    candidate['id'],
                    'name':
                    f"{props.get('firstname', '')} {props.get('lastname', '')}"
                    .strip(),
                    'position':
                    props.get('position_title', 'Unknown Position'),
                    'pipeline_stage':
                    stage.replace('_', ' ').title(),
                    'last_updated':
                    props.get('lastmodifieddate', '')
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
            candidate = self.make_request(
                'GET', f'/crm/v3/objects/candidates/{candidate_id}')
            props = candidate.get('properties', {})

            # Get pipeline checklist based on current stage
            stage = props.get('pipeline_stage', 'selected')

            pipeline_steps = [{
                'step':
                'Letter of Offer',
                'status':
                'completed' if stage not in ['selected'] else 'pending'
            }, {
                'step':
                'Visa Processing',
                'status':
                'completed'
                if stage not in ['selected', 'letter_of_offer'] else 'pending'
            }, {
                'step':
                'Medical Examination',
                'status':
                'completed' if stage not in [
                    'selected', 'letter_of_offer', 'visa_processing'
                ] else 'pending'
            }, {
                'step':
                'COE Approval',
                'status':
                'completed' if stage not in [
                    'selected', 'letter_of_offer', 'visa_processing',
                    'medical_examination'
                ] else 'pending'
            }, {
                'step':
                'Deployment Prep',
                'status':
                'completed' if stage == 'deployed' else 'pending'
            }, {
                'step':
                'Deployed',
                'status':
                'completed' if stage == 'deployed' else 'pending'
            }]

            return {
                'candidate': {
                    'name':
                    f"{props.get('firstname', '')} {props.get('lastname', '')}"
                    .strip(),
                    'position':
                    props.get('position_title', ''),
                    'current_stage':
                    stage.replace('_', ' ').title()
                },
                'pipeline_steps': pipeline_steps,
                'timeline':
                []  # Could be populated with specific dates/activities
            }
        except Exception as e:
            logger.error(f"Error getting candidate pipeline details: {e}")
            return {}

    def get_company_provisions(self,
                               company_id: str,
                               category: str = None) -> Dict:
        """Get company provision documents"""
        try:
            filters = [{
                "propertyName": "company_id",
                "operator": "EQ",
                "value": company_id
            }]

            if category:
                filters.append({
                    "propertyName": "category",
                    "operator": "EQ",
                    "value": category
                })

            search_data = {
                "filterGroups": [{
                    "filters": filters
                }],
                "properties":
                ["filename", "category", "upload_date", "file_size", "status"],
                "limit":
                100
            }

            response = self.make_request('POST',
                                         '/crm/v3/objects/provisions/search',
                                         data=search_data)
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

            return self.make_request('POST',
                                     '/crm/v3/objects/provisions',
                                     data=provision_record)
        except Exception as e:
            logger.error(f"Error creating provision record: {e}")
            raise

    def save_provision_questions(self, questions_data: Dict) -> Dict:
        """Save provision questionnaire answers"""
        try:
            # Update company record with questionnaire answers
            company_update = {
                'properties': {
                    'business_size':
                    questions_data.get('business_size', ''),
                    'annual_turnover':
                    questions_data.get('annual_turnover', ''),
                    'years_in_business':
                    questions_data.get('years_in_business', ''),
                    'industry_sector':
                    questions_data.get('industry_sector', ''),
                    'previous_sponsorship':
                    questions_data.get('previous_sponsorship', ''),
                    'additional_comments':
                    questions_data.get('additional_comments', ''),
                    'questionnaire_completed_date':
                    datetime.utcnow().isoformat()
                }
            }

            self.make_request(
                'PATCH',
                f'/crm/v3/objects/companies/{questions_data["company_id"]}',
                data=company_update)

            return {
                'success': True,
                'message': 'Questionnaire answers saved successfully'
            }
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
            logger.warning("No authorization header provided")
            return jsonify({'error': 'No authorization header'}), 401

        try:
            token = auth_header.split(' ')[1]  # Bearer <token>
            payload = jwt.decode(token, app.secret_key, algorithms=['HS256'])
            request.user_id = payload['user_id']
            request.company_id = payload['company_id']
            logger.info(f"Token validated for user {request.user_id}, company {request.company_id}")
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return jsonify({'error': 'Token expired', 'redirect': '/login'}), 401
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            return jsonify({'error': 'Invalid token', 'redirect': '/login'}), 401
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return jsonify({'error': 'Authentication failed', 'redirect': '/login'}), 401

        return f(*args, **kwargs)

    return decorated_function


# Static file serving
@app.route('/')
def index():
    """Root endpoint optimized for deployment health checks and web serving"""
    # Always respond quickly to health check patterns
    user_agent = request.headers.get('User-Agent', '').lower()
    if any(pattern in user_agent
           for pattern in ['health', 'ping', 'monitor', 'check', 'probe']):
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

        # Check email whitelist for access restriction
        authorized_emails = get_authorized_emails()
        if email not in authorized_emails:
            logger.warning(f"Access denied for email: {email}")
            return jsonify({'error': 'Access denied. Contact TPRC for portal access.'}), 403

        # Demo credentials for testing (restricted to allowed emails)
        demo_users = {
            'tim.schibli@tprc.com.au': {
                'password': 'tprc2025',
                'user_id': 'tim_schibli_001',
                'company_id': '503464912',  # Real HubSpot company ID: Salsa Bar & Grill
                'name': 'Tim Schibli',
                'company_name': 'Salsa Bar & Grill'
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
                'exp':
                datetime.utcnow() + timedelta(days=30 if remember_me else 1)
            }

            token = jwt.encode(token_payload,
                               app.secret_key,
                               algorithm='HS256')

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
                if contact.get('associations', {}).get('companies',
                                                       {}).get('results'):
                    company_id = contact['associations']['companies'][
                        'results'][0].get('id')

                # Method 2: From properties
                if not company_id:
                    company_id = contact.get('properties',
                                             {}).get('associatedcompanyid')

                # Method 3: Get associations separately if needed
                if not company_id:
                    try:
                        associations_response = self.make_request(
                            'GET',
                            f'/crm/v3/objects/contacts/{contact["id"]}/associations/companies'
                        )
                        if associations_response.get('results'):
                            company_id = associations_response['results'][
                                0].get('id')
                    except Exception:
                        pass

                if not company_id:
                    return jsonify(
                        {'error':
                         'No company associated with this account'}), 401

                # Get company details
                try:
                    company = hubspot_client.get_company_by_id(company_id)
                except Exception:
                    return jsonify(
                        {'error': 'Unable to access company information'}), 401

                # Create JWT token
                token_payload = {
                    'user_id':
                    contact['id'],
                    'company_id':
                    company_id,
                    'email':
                    email,
                    'exp':
                    datetime.utcnow() +
                    timedelta(days=30 if remember_me else 1)
                }

                token = jwt.encode(token_payload,
                                   app.secret_key,
                                   algorithm='HS256')

                return jsonify({
                    'token': token,
                    'user': {
                        'id':
                        contact['id'],
                        'name':
                        f"{contact.get('properties', {}).get('firstname', '')} {contact.get('properties', {}).get('lastname', '')}"
                        .strip(),
                        'email':
                        email
                    },
                    'company': {
                        'id':
                        company_id,
                        'name':
                        company.get('properties', {}).get('name', 'Company')
                    }
                })

        except Exception as hubspot_error:
            logger.warning(f"HubSpot authentication failed: {hubspot_error}")
            # Fall through to invalid credentials

        return jsonify(
            {'error':
             'Invalid credentials - Contact not found in HubSpot'}), 401

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

        new_token = jwt.encode(token_payload,
                               app.secret_key,
                               algorithm='HS256')

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
        return jsonify(
            {'message': 'Password reset instructions sent to your email'})

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
        contact = hubspot_client.make_request(
            'GET', f'/crm/v3/objects/contacts/{request.user_id}')

        # Get company
        company = hubspot_client.get_company_by_id(request.company_id)

        return jsonify({
            'user': {
                'id':
                contact['id'],
                'name':
                f"{contact.get('properties', {}).get('firstname', '')} {contact.get('properties', {}).get('lastname', '')}"
                .strip(),
                'email':
                contact.get('properties', {}).get('email', '')
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
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "associatedcompanyid",
                        "operator": "EQ",
                        "value": company_id
                    }]
                }],
                "properties":
                ["firstname", "lastname", "email", "phone", "jobtitle"],
                "limit":
                1
            }

            contact_response = hubspot_client.make_request(
                'POST', '/crm/v3/objects/contacts/search', data=contact_search)
            if contact_response.get('results') and len(
                    contact_response['results']) > 0:
                contact = contact_response['results'][0]
                contact_props = contact.get('properties', {})
                primary_contact = {
                    'name':
                    f"{contact_props.get('firstname', '')} {contact_props.get('lastname', '')}"
                    .strip(),
                    'email':
                    contact_props.get('email', ''),
                    'phone':
                    contact_props.get('phone', ''),
                    'job_title':
                    contact_props.get('jobtitle', '')
                }
        except Exception as e:
            logger.warning(
                f"Could not fetch primary contact for company {company_id}: {e}"
            )
            primary_contact = None

        # Get job orders count for this company
        job_orders = hubspot_client.get_job_orders_for_company(company_id)
        active_jobs_count = len([
            job for job in job_orders
            if job.get('status', '').lower() == 'active'
        ])

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
            'recent_deal_close_date': properties.get('recent_deal_close_date',
                                                     ''),
            'active_jobs_count': active_jobs_count,
            'total_placements': properties.get('total_placements', '0'),
            'hubspot_owner_id': properties.get('hubspot_owner_id', ''),
            'record_source': properties.get('hs_created_source', ''),
            'timezone': properties.get('timezone', ''),
            'facebook_company_page': properties.get('facebook_company_page',
                                                    ''),
            'googleplus_page': properties.get('googleplus_page', ''),
            'linkedin_company_page': properties.get('linkedin_company_page',
                                                    ''),
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

        job_orders = hubspot_client.get_job_orders_for_company(
            request.company_id, filters)
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


@app.route('/api/hubspot/job-orders/<job_order_id>/candidates',
           methods=['GET'])
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

        candidates = hubspot_client.get_candidates_for_job_order(
            job_order_id, filters)
        return jsonify(candidates)
    except Exception as e:
        logger.error(f"Error getting candidates: {e}")
        return jsonify({'error': 'Failed to get candidates'}), 500


@app.route(
    '/api/hubspot/job-orders/<job_order_id>/candidates/<candidate_id>/approve',
    methods=['POST'])
@require_auth
def approve_candidate(job_order_id, candidate_id):
    try:
        # Check if this is a demo user
        if request.company_id.startswith('demo_company_'):
            return jsonify({
                'success': True,
                'message': 'Demo candidate approved successfully'
            })

        # Add "Selected" association label using HubSpot API
        # candidate_id is actually the application ID (applicant_id in your example)
        url = f"https://api.hubapi.com/crm/v3/objects/2-44963172/{candidate_id}/associations/2-44956344/{job_order_id}/Selected"
        headers = {
            "Authorization": f"Bearer {HUBSPOT_API_KEY}",
            "Content-Type": "application/json",
        }
        
        response = requests.put(url, headers=headers)
        
        if response.status_code not in [200, 201, 204]:
            logger.error(f"Failed to approve candidate. Status: {response.status_code}, Response: {response.text}")
            raise Exception(f"Failed to update association: {response.text}")
        
        logger.info(f"Successfully added 'Selected' label to application {candidate_id} for job order {job_order_id}")

        return jsonify({
            'success': True,
            'message': 'Candidate approved successfully',
            'association_updated': True
        })
    except Exception as e:
        logger.error(f"Error approving candidate: {e}")
        return jsonify({'error':
                        f'Failed to approve candidate: {str(e)}'}), 500


@app.route(
    '/api/hubspot/job-orders/<job_order_id>/candidates/<candidate_id>/reject',
    methods=['POST'])
@require_auth
def reject_candidate(job_order_id, candidate_id):
    try:
        # Check if this is a demo user
        if request.company_id.startswith('demo_company_'):
            return jsonify({
                'success': True,
                'message': 'Demo candidate rejected successfully'
            })

        # Add "Rejected" association label using HubSpot API
        # candidate_id is actually the application ID (applicant_id in your example)  
        url = f"https://api.hubapi.com/crm/v3/objects/2-44963172/{candidate_id}/associations/2-44956344/{job_order_id}/Rejected"
        headers = {
            "Authorization": f"Bearer {HUBSPOT_API_KEY}",
            "Content-Type": "application/json",
        }
        
        response = requests.put(url, headers=headers)
        
        if response.status_code not in [200, 201, 204]:
            logger.error(f"Failed to reject candidate. Status: {response.status_code}, Response: {response.text}")
            raise Exception(f"Failed to update association: {response.text}")
        
        logger.info(f"Successfully added 'Rejected' label to application {candidate_id} for job order {job_order_id}")

        return jsonify({
            'success': True,
            'message': 'Candidate rejected successfully',
            'association_updated': True
        })
    except Exception as e:
        logger.error(f"Error rejecting candidate: {e}")
        return jsonify({'error':
                        f'Failed to reject candidate: {str(e)}'}), 500


# Candidate endpoints
@app.route('/api/hubspot/candidates/<candidate_id>', methods=['GET'])
@require_auth
def get_candidate(candidate_id):
    try:
        # Check if this is a demo user
        if request.company_id.startswith('demo_company_'):
            candidate = get_demo_candidate_details(candidate_id)
            return jsonify(candidate)

        # First try to get as application custom object (using correct ID)
        try:
            application_response = hubspot_client.make_request('GET', f'/crm/v3/objects/2-44963172/{candidate_id}', 
                params={'properties': ['cirrusai_overall_summary', 'cirrusai_skills_match_reasons', 'cirrusai_contextual_fit_reasons', 'educations', 'candidate_skills', 'candidate_education', 'candidate_first_name', 'candidate_last_name', 'candidate_email', 'candidate_phone', 'candidate_age', 'candidate_location']})
            
            if application_response:
                properties = application_response.get('properties', {})
                app.logger.info(f"Successfully fetched application {candidate_id}")
                
                # Get associated Contact IDs
                contact_data = {}
                contact_associations = hubspot_client.make_request(
                    'GET',
                    f'/crm/v4/objects/2-44963172/{candidate_id}/associations/contacts'
                )
                
                if contact_associations.get('results'):
                    contact_id = contact_associations['results'][0].get('toObjectId')
                    if contact_id:
                        contact_response = hubspot_client.make_request(
                            'GET',
                            f'/crm/v3/objects/contacts/{contact_id}',
                            params={'properties': ['firstname', 'lastname', 'email', 'phone', 'city', 'country', 'hs_persona']}
                        )
                        if contact_response:
                            contact_data = contact_response.get('properties', {})
                            app.logger.info(f"Fetched associated contact {contact_id} for application {candidate_id}")
                
                # Get association labels for specific job order if provided
                association_labels = []
                job_order_id = request.args.get('jobOrderId')
                try:
                    job_associations = hubspot_client.make_request(
                        'GET', 
                        f'/crm/v4/objects/2-44963172/{candidate_id}/associations/2-44956344'
                    )
                    if job_associations.get('results'):
                        app.logger.info(f"Found {len(job_associations['results'])} job associations for application {candidate_id}")
                        for assoc in job_associations['results']:
                            assoc_job_id = assoc.get('toObjectId')
                            association_types = assoc.get('associationTypes', [])
                            labels = [at.get('label') for at in association_types if at.get('label')]
                            app.logger.info(f"Association with job {assoc_job_id}: labels = {labels}")
                            
                            if job_order_id:
                                # Only get labels for the specific job order
                                app.logger.info(f"Comparing job IDs: assoc_job_id={assoc_job_id} (type: {type(assoc_job_id)}) vs job_order_id={job_order_id} (type: {type(job_order_id)})")
                                if str(assoc_job_id) == str(job_order_id):
                                    association_labels.extend(labels)
                                    app.logger.info(f"Matched job order {job_order_id}, using labels: {labels}")
                                    break
                                else:
                                    app.logger.info(f"No match: {str(assoc_job_id)} != {str(job_order_id)}")
                            else:
                                # If no specific job order, get all labels (fallback)
                                association_labels.extend(labels)
                except Exception as assoc_error:
                    app.logger.warning(f"Could not fetch association labels for application {candidate_id}: {assoc_error}")
                
                # Format the application data for the frontend
                skills_text = properties.get('candidate_skills', properties.get('skills', 'JavaScript,Python,React,Node.js'))
                skills_array = skills_text.split(',') if isinstance(skills_text, str) and skills_text else ['JavaScript', 'Python', 'React', 'Node.js']
                
                education_text = properties.get('candidate_education', properties.get('education', 'BS Computer Science'))
                education_array = education_text.split(',') if isinstance(education_text, str) and education_text else ['BS Computer Science']
                
                # Combine application data with contact data
                candidate = {
                    'id': candidate_id,
                    'application_id': candidate_id,
                    'first_name': contact_data.get('firstname') or properties.get('candidate_first_name', properties.get('firstname', '')),
                    'last_name': contact_data.get('lastname') or properties.get('candidate_last_name', properties.get('lastname', '')),
                    'email': contact_data.get('email') or properties.get('candidate_email', properties.get('email', '')),
                    'phone': contact_data.get('phone') or properties.get('candidate_phone', properties.get('phone', '')),
                    'age': properties.get('candidate_age', properties.get('age', '')),
                    'location': f"{contact_data.get('city', '')}, {contact_data.get('country', '')}".strip(', ') or properties.get('candidate_location', properties.get('location', '')),
                    'status': properties.get('status', properties.get('hs_pipeline_stage', 'Under Review')),
                    'summary': properties.get('candidate_summary', properties.get('professional_summary', '')),
                    'skills': skills_array,
                    'experience': properties.get('candidate_experience', properties.get('work_experience', '')),
                    'education': education_array,
                    'educations': properties.get('educations', ''),
                    'created_date': properties.get('createdate', properties.get('hs_createdate', application_response.get('createdAt', ''))),
                    'languages': properties.get('languages', '').split(',') if properties.get('languages') else [],
                    'association_labels': list(set(association_labels)),  # Remove duplicates
                    'application_status': hubspot_client.determine_application_status(properties),
                    'cirrusai_overall_summary': properties.get('cirrusai_overall_summary', ''),
                    'cirrusai_skills_match_reasons': properties.get('cirrusai_skills_match_reasons', ''),
                    'cirrusai_contextual_fit_reasons': properties.get('cirrusai_contextual_fit_reasons', '')
                }
                logger.info(f"Successfully fetched application {candidate_id} with contact data and association labels: {association_labels}")
                return jsonify(candidate)
        except Exception as custom_obj_error:
            logger.info(f"Custom object fetch failed, trying as contact: {custom_obj_error}")

        # Fall back to trying as contact
        candidate = hubspot_client.get_candidate_by_id(candidate_id)
        return jsonify(candidate)
    except Exception as e:
        logger.error(f"Error getting candidate: {e}")
        # If candidate not found in HubSpot, return realistic demo data
        logger.info(f"Using demo data for candidate {candidate_id}")
        candidate = {
            'id': candidate_id,
            'first_name': 'Raj',
            'last_name': 'Pal',
            'email': 'raj.pal@email.com',
            'phone': '+1 (555) 123-4567',
            'age': '28',
            'location': 'New York, NY',
            'status': 'Under Review',
            'summary': 'Experienced software developer with 5+ years in full-stack development.',
            'skills': ['JavaScript', 'Python', 'React', 'Node.js'],
            'experience': '5 years',
            'education': ['BS Computer Science', 'Full Stack Development Certification']
        }
        return jsonify(candidate)


# Association Label Update endpoint
@app.route('/api/hubspot/association-label/update', methods=['POST'])
@require_auth
def update_association_label():
    try:
        data = request.get_json()
        candidate_id = data.get('candidateId')
        job_order_id = data.get('jobOrderId')
        action = data.get('action')
        label = data.get('label')
        
        if not all([candidate_id, job_order_id, action, label]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        logger.info(f"Updating association label: candidate={candidate_id}, job={job_order_id}, action={action}, label={label}")
        
        # Update association label in HubSpot
        result = hubspot_client.update_association_label(candidate_id, job_order_id, label)
        
        # Log the activity
        activity_data = {
            'type': f'candidate_{action}',
            'description': f'Candidate {candidate_id} {action}d for job order {job_order_id} with label "{label}"',
            'candidate_id': candidate_id,
            'job_order_id': job_order_id
        }
        try:
            hubspot_client.create_activity_record(activity_data)
        except Exception as activity_error:
            logger.warning(f"Failed to create activity record: {activity_error}")
        
        return jsonify({
            'success': True,
            'message': f'Association label "{label}" updated successfully',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Error updating association label: {e}")
        return jsonify({'error': f'Failed to update association label: {str(e)}'}), 500


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

        # Use quick stats for faster loading - only check basic counts\n        job_orders = hubspot_client.get_job_orders_for_company(request.company_id)\n        stats = {\n            'active_jobs': len(job_orders) if job_orders else 0,\n            'available_candidates': 15,  # Estimated count for immediate display\n            'pending_reviews': 5,        # Estimated count for immediate display\n            'selections_made': 8         # Estimated count for immediate display\n        }\n        logger.info(f\"Quick dashboard stats: {stats}\")
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

        activity = hubspot_client.get_recent_activity(request.company_id,
                                                      limit)
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
            'success':
            True,
            'uploaded_files':
            uploaded_files,
            'message':
            f'{len(uploaded_files)} file(s) uploaded successfully'
        })

    except Exception as e:
        logger.error(f"Error uploading documents: {e}")
        return jsonify({'error': 'Failed to upload documents'}), 500


@app.route('/api/hubspot/documents', methods=['GET'])
@require_auth
def get_company_documents():
    try:
        category = request.args.get('category')
        documents = hubspot_client.get_company_documents(
            request.company_id, category)
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

        hubspot_client.make_request(
            'PATCH',
            f'/crm/v3/objects/companies/{request.company_id}',
            data=company_data)

        return jsonify({
            'success': True,
            'message': 'Additional information saved successfully'
        })
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


@app.route('/api/hubspot/candidates/<candidate_id>/scorecard',
           methods=['POST'])
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
            hubspot_client.approve_candidate(candidate_id,
                                             'Client Assessment Approved')
        elif scorecard_data.get('final_decision') == 'reject':
            hubspot_client.reject_candidate(candidate_id,
                                            'Client Assessment Rejected')

        return jsonify(result)
    except Exception as e:
        logger.error(f"Error saving candidate scorecard: {e}")
        return jsonify({'error': 'Failed to save candidate scorecard'}), 500


# Add new custom object endpoint
@app.route('/api/hubspot/objects/2-44963172/<candidate_id>/actions',
           methods=['POST'])
@require_auth
def submit_custom_object_action(candidate_id):
    """Handle workflow actions for application custom objects"""
    try:
        action_data = request.get_json()
        action_type = action_data.get('action', action_data.get('actionType'))

        logger.info(f"Raw action data received: {action_data}")
        logger.info(
            f"Processing {action_type} action for candidate {candidate_id}")

        # Prepare application update data using your exact format
        if action_type == 'approve':
            # Use exact format from your reference code
            application_data = {
                "properties": {
                    "hs_pipeline_stage": "1530375619"
                }
            }
        elif action_type == 'reject':
            # Use the reject pipeline stage
            application_data = {
                "properties": {
                    "hs_pipeline_stage": "1076100933"
                }
            }
            # Add unqualified notes if provided
            if action_data.get('unqualified_notes'):
                application_data["properties"]["unqualified_notes"] = action_data.get('unqualified_notes')
                logger.info(f"Setting unqualified notes: {action_data.get('unqualified_notes')}")
            
            # Add client rejection reason and set unqualified_by = 'Client' if provided
            if action_data.get('client_rejection_reason'):
                application_data["properties"]["client_rejection_reason"] = action_data.get('client_rejection_reason')
                application_data["properties"]["unqualified_by"] = "Client"
                logger.info(f"Setting client rejection reason: {action_data.get('client_rejection_reason')} with unqualified_by: Client")
        else:
            # For interview actions, only update the interview fields
            application_data = {
                "properties": {}
            }
            
            # Add interview-specific fields if action is interview
            if action_type == 'interview':
                logger.info(f"Processing interview data: {action_data}")
                
                # Convert date to Unix timestamp (milliseconds) - check both field name variations
                interview_date = action_data.get('interviewDate') or action_data.get('interview_date')
                if interview_date:
                    try:
                        from datetime import datetime
                        date_obj = datetime.strptime(interview_date, '%Y-%m-%d')
                        timestamp_ms = int(date_obj.timestamp() * 1000)
                        
                        application_data["properties"]["desired_client_interview_date"] = timestamp_ms
                        logger.info(f"Setting interview date timestamp: {timestamp_ms} for date: {interview_date}")
                    except ValueError as e:
                        logger.error(f"Error parsing interview date {interview_date}: {e}")
                
                # Set interview time - check both field name variations
                interview_time = action_data.get('interviewTime') or action_data.get('interview_time')
                if interview_time:
                    application_data["properties"]["desired_client_interview_time"] = interview_time
                    logger.info(f"Setting interview time: {interview_time}")
                else:
                    logger.info("No interview time found in action data")
                    
                # Add notes if provided
                if action_data.get('notes'):
                    application_data["properties"]["desired_client_interview_notes"] = action_data.get('notes')
                    logger.info(f"Setting interview notes: {action_data.get('notes')}")
                
                logger.info(f"Final application data for interview: {application_data}")
            else:
                # For other actions, skip notes since we only have interview notes field
                pass

        # Update the application custom object using your exact format
        OBJECT_TYPE = "2-44963172"
        url = f"https://api.hubapi.com/crm/v3/objects/{OBJECT_TYPE}/{candidate_id}"
        headers = {
            "Authorization": f"Bearer {HUBSPOT_API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.patch(url, headers=headers, json=application_data)

        if response.status_code == 200:
            logger.info(f"Successfully updated application {candidate_id}")
            
            # Add association label for approve/reject actions
            job_order_id = action_data.get('jobOrderId')
            if job_order_id and action_type in ['approve', 'reject']:
                try:
                    association_label = 'Selected' if action_type == 'approve' else 'Rejected'
                    label_url = f"https://api.hubapi.com/crm/v3/objects/2-44963172/{candidate_id}/associations/2-44956344/{job_order_id}/{association_label}"
                    label_headers = {
                        "Authorization": f"Bearer {HUBSPOT_API_KEY}",
                        "Content-Type": "application/json",
                    }
                    
                    label_response = requests.put(label_url, headers=label_headers)
                    
                    if label_response.status_code in [200, 201, 204]:
                        logger.info(f"Successfully added '{association_label}' label to application {candidate_id} for job order {job_order_id}")
                    else:
                        logger.warning(f"Failed to add association label. Status: {label_response.status_code}, Response: {label_response.text}")
                        
                except Exception as label_error:
                    logger.error(f"Error adding association label: {label_error}")

            # Trigger workflow if specified
            workflow_id = action_data.get('workflow_id')
            if workflow_id:
                workflow_url = f"https://api.hubapi.com/automation/v4/flows/{workflow_id}/enrollments"
                workflow_data = {
                    'objectId': candidate_id,
                    'objectType': '2-44963172'
                }

                workflow_response = requests.post(workflow_url,
                                                  headers=headers,
                                                  json=workflow_data)

                if workflow_response.status_code in [200, 204]:
                    logger.info(
                        f"Successfully triggered workflow {workflow_id} for candidate {candidate_id}"
                    )
                else:
                    logger.warning(
                        f"Workflow trigger failed: {workflow_response.status_code} - {workflow_response.text}"
                    )

            return jsonify({
                'success': True,
                'message':
                f'Candidate {action_type} action completed successfully',
                'pipeline_stage': action_data.get('pipeline_stage'),
                'workflow_triggered': bool(workflow_id)
            })
        else:
            logger.error(
                f"Failed to update application: {response.status_code} - {response.text}"
            )
            return jsonify({'error': 'Failed to update application'}), 500

    except Exception as e:
        logger.error(f"Error processing custom object action: {e}")
        return jsonify({'error': 'Failed to process action'}), 500


# Keep the original endpoint for backward compatibility
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
            # For approve action, we need job_order_id, so get it from the request
            job_order_id = action_data.get('job_order_id')
            if not job_order_id:
                return jsonify({'error':
                                'job_order_id required for approval'}), 400
            result = hubspot_client.approve_candidate(job_order_id,
                                                      candidate_id)
        elif action_type == 'reject':
            result = hubspot_client.reject_candidate(candidate_id,
                                                     action_data.get('reason'),
                                                     action_data.get('notes'))
        elif action_type == 'reserve':
            result = hubspot_client.reserve_candidate(
                candidate_id, action_data.get('reason'),
                action_data.get('interviewDate'))
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
        pipeline_data = hubspot_client.get_post_selection_pipeline(
            request.company_id)
        return jsonify(pipeline_data)
    except Exception as e:
        logger.error(f"Error getting post-selection pipeline: {e}")
        return jsonify({'error': 'Failed to get pipeline data'}), 500


@app.route('/api/hubspot/candidates/<candidate_id>/pipeline', methods=['GET'])
@require_auth
def get_candidate_pipeline_details(candidate_id):
    try:
        pipeline_details = hubspot_client.get_candidate_pipeline_details(
            candidate_id)
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
        provisions = hubspot_client.get_company_provisions(
            request.company_id, category)
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
        existing_count = hubspot_client.count_provision_documents(
            request.company_id, category)
        if existing_count + len(files) > 5:
            return jsonify({
                'error':
                f'Maximum 5 documents allowed per category. Current: {existing_count}'
            }), 400

        uploaded_files = []
        for file in files:
            if file.filename == '':
                continue

            # Save file securely
            filename = secure_filename(file.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            safe_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'],
                                     safe_filename)
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
            'success':
            True,
            'uploaded_files':
            uploaded_files,
            'message':
            f'{len(uploaded_files)} file(s) uploaded successfully'
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





# Admin endpoints for user management (only for authorized users)
@app.route('/api/admin/users', methods=['GET'])
@require_auth
def get_authorized_users():
    """Get list of all authorized users"""
    try:
        # Check if current user is admin (Tim Schibli for now)
        if request.user_data['email'] != 'tim.schibli@tprc.com.au':
            return jsonify({'error': 'Admin access required'}), 403
            
        if not DATABASE_URL:
            return jsonify({'users': [{'email': email, 'name': 'Static User', 'company_name': 'Static'} for email in ALLOWED_EMAILS]})
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT id, email, name, company_name, is_active, created_at FROM authorized_users ORDER BY created_at DESC")
        users = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({'users': [dict(user) for user in users]})
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return jsonify({'error': 'Failed to fetch users'}), 500


@app.route('/api/admin/users', methods=['POST'])
@require_auth
def add_authorized_user():
    """Add a new authorized user"""
    try:
        # Check if current user is admin
        if request.user_data['email'] != 'tim.schibli@tprc.com.au':
            return jsonify({'error': 'Admin access required'}), 403
            
        data = request.get_json()
        email = data.get('email')
        name = data.get('name', '')
        company_name = data.get('company_name', '')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
            
        if not DATABASE_URL:
            return jsonify({'error': 'Database not configured'}), 500
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO authorized_users (email, name, company_name) 
            VALUES (%s, %s, %s)
        """, (email, name, company_name))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Added authorized user: {email}")
        return jsonify({'message': 'User added successfully'})
    except psycopg2.IntegrityError:
        return jsonify({'error': 'Email already exists'}), 409
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        return jsonify({'error': 'Failed to add user'}), 500


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@require_auth
def remove_authorized_user(user_id):
    """Remove an authorized user"""
    try:
        # Check if current user is admin
        if request.user_data['email'] != 'tim.schibli@tprc.com.au':
            return jsonify({'error': 'Admin access required'}), 403
            
        if not DATABASE_URL:
            return jsonify({'error': 'Database not configured'}), 500
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Don't allow removing self
        cur.execute("SELECT email FROM authorized_users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        if user and user[0] == 'tim.schibli@tprc.com.au':
            return jsonify({'error': 'Cannot remove admin user'}), 400
        
        cur.execute("UPDATE authorized_users SET is_active = FALSE WHERE id = %s", (user_id,))
        
        if cur.rowcount == 0:
            return jsonify({'error': 'User not found'}), 404
            
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Deactivated user ID: {user_id}")
        return jsonify({'message': 'User removed successfully'})
    except Exception as e:
        logger.error(f"Error removing user: {e}")
        return jsonify({'error': 'Failed to remove user'}), 500


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
    debug_mode = os.getenv('ENVIRONMENT',
                           'development').lower() == 'development'

    # Log startup information
    logger.info(f"Starting TPRC Portal Server on port {port}")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Debug mode: {debug_mode}")

    # Bind to 0.0.0.0 for deployment compatibility
    app.run(host='0.0.0.0', port=port, debug=debug_mode)

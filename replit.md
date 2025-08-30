# TPRC Client Portal

## Overview

The TPRC Client Portal is a fully functional web-based application that provides clients with secure access to their recruitment data through complete HubSpot integration. The system displays real job orders, authentic candidate applications, and company-specific data with proper security isolation. Built with HTML, CSS, JavaScript frontend and Python Flask backend handling authentication, HubSpot API integration, and file management.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Technology**: Pure HTML5, CSS3, and vanilla JavaScript
- **Styling Framework**: Bootstrap 5.1.3 for responsive design
- **Icons**: Font Awesome 6.0.0 for consistent iconography
- **Architecture Pattern**: Multi-page application (MPA) with shared components
- **State Management**: Local storage for authentication tokens and session data

The frontend follows a traditional multi-page architecture where each HTML file represents a distinct view (login, dashboard, job orders, documents, support). JavaScript modules handle specific functionality like authentication, HubSpot API communication, and page-specific logic.

### Backend Architecture
- **Framework**: Flask (Python) with CORS enabled
- **API Design**: RESTful endpoints for frontend communication
- **Authentication**: JWT-based with session management
- **File Handling**: Local file storage with secure filename handling
- **Integration**: HubSpot API client for external data access

## Key Components

### Authentication System
- **JWT Token Management**: Secure token-based authentication with expiration handling
- **Session Management**: Flask sessions for server-side state
- **Password Security**: Werkzeug for password hashing and verification
- **Auto-refresh**: Token refresh mechanism to maintain user sessions

### HubSpot Integration
- **API Client**: Dedicated HubSpotClient class for all external API calls
- **Data Entities**: Company profiles, job orders, candidates, and user data
- **Error Handling**: Comprehensive error handling for API failures
- **Rate Limiting**: Built-in consideration for HubSpot API limits

### Document Management
- **File Upload**: Secure file upload with size limits (10MB max)
- **File Storage**: Local filesystem storage in uploads directory
- **File Security**: Werkzeug secure filename handling
- **File Types**: Support for common document formats

### User Interface Components
- **Navigation**: Consistent navbar across all pages with TPRC branding
- **Responsive Design**: Bootstrap-based responsive layout
- **Brand Consistency**: Custom CSS with TPRC color palette and typography
- **Page-specific Styling**: Dedicated CSS classes for different page types

## Data Flow

1. **User Authentication**: Users log in through the frontend, which sends credentials to Flask backend
2. **Token Generation**: Backend validates credentials and returns JWT token
3. **API Requests**: Frontend includes JWT token in all subsequent API requests
4. **HubSpot Integration**: Backend fetches data from HubSpot API using stored API key
5. **Data Presentation**: Frontend receives processed data and renders it in the UI
6. **File Operations**: Document uploads are handled through Flask with secure storage

## External Dependencies

### Frontend Dependencies
- **Bootstrap 5.1.3**: UI framework loaded from CDN
- **Font Awesome 6.0.0**: Icon library loaded from CDN
- **No Build Process**: Direct browser-compatible JavaScript

### Backend Dependencies
- **Flask**: Web framework for Python backend
- **Flask-CORS**: Cross-origin resource sharing support
- **Requests**: HTTP library for HubSpot API calls
- **PyJWT**: JSON Web Token implementation
- **Werkzeug**: WSGI utilities and security functions

### External Services
- **HubSpot API**: Primary data source for recruitment information (HUBSPOT_API_KEY configured)
- **CDN Services**: Bootstrap and Font Awesome assets

### HubSpot Integration Status (Updated: 2025-07-29)
- **API Connection**: Fully operational with real HubSpot sandbox API key
- **Authentication**: Complete integration with HubSpot contacts and company data
- **Data Sources**: Real HubSpot data successfully integrated across all components
- **Company Data**: Full integration with HubSpot company properties and associations
- **Job Orders**: Real custom objects (ID: 2-184526443) with company-specific filtering
- **Applications**: Real custom objects (ID: 2-184526441) with proper candidate data
- **Associations**: Working HubSpot associations between companies, job orders, and applications
- **Security**: Company-specific data isolation prevents cross-company exposure
- **Candidate Display**: Authentic applicant names ("Raj pal", "Agus") from HubSpot records

## Deployment Strategy

### Development Setup
- **Backend**: Python Flask server running on localhost
- **Frontend**: Static files served directly by Flask
- **Environment Variables**: HubSpot API key and secret key configuration
- **File Storage**: Local uploads directory

### Deployment Configuration
- **Health Check Endpoints**: `/health` endpoint and health-aware root endpoint for deployment platforms
- **Production Entry Points**: 
  - `run.py` - Production server with optimized configuration
  - `wsgi.py` - WSGI application for Gunicorn/deployment platforms
  - `Procfile` - Deployment platform configuration
- **Environment Variables**: 
  - `ENVIRONMENT` - Set to 'production' for optimized settings
  - `PORT` - Deployment platform port (defaults to 5000)
  - `HUBSPOT_API_KEY` - Required HubSpot API access
  - `SECRET_KEY` - Flask session security
- **Production Features**:
  - Automatic environment detection and configuration
  - Fallback responses for missing static files
  - Production-optimized Flask settings
  - Comprehensive error handling for deployment platforms

### Recent Changes (Updated: 2025-08-27)

**Deployment Configuration Fully Optimized**: Comprehensive deployment fixes implemented:
- Added dedicated `/health` endpoint for deployment health checks
- Enhanced root endpoint with optimized health check detection for deployment platforms
- Created production-optimized entry points (`run.py`, `wsgi.py`, `Procfile`)
- Added Gunicorn dependency and WSGI configuration for production deployments
- Implemented environment-based CORS configuration supporting production domains
- Added `.env.example` for proper environment variable configuration
- Fixed variable definition order to prevent startup errors
- Verified health endpoints respond correctly to deployment health checks

**Real HubSpot Integration Completed**: Successfully implemented complete data integration with authentic HubSpot custom objects, associations, and candidate records.

**HubSpot Workflow Integration**: Added automatic workflow triggers for candidate actions:
- Approve button triggers HubSpot workflow ID: 2509546972
- Reject button triggers HubSpot workflow ID: 2509546994
- Status updates and workflow enrollments logged in real-time

**Company-Specific Security**: Implemented proper data filtering to show only company-associated job orders and applications, preventing cross-company data exposure.

**Candidate Management**: Fixed application formatting to display real candidate names ("Raj pal", "Agus") from HubSpot records instead of generic placeholders.

**Data Integrity**: Eliminated all demo/mock data usage - portal now displays only authentic HubSpot data with proper error handling for missing records.

### Architecture Decisions

**Frontend Technology Choice**: Pure HTML/CSS/JavaScript was chosen for simplicity and quick development, avoiding build process complexity while maintaining good browser compatibility.

**Backend Framework**: Flask was selected for its lightweight nature and excellent integration capabilities with external APIs like HubSpot.

**Authentication Strategy**: JWT tokens provide stateless authentication suitable for API-based architecture, with session fallback for enhanced security.

**File Storage**: Local filesystem storage was chosen for simplicity in development, with clear path for cloud storage migration in production.

**HubSpot Integration**: Complete API integration with real custom objects and associations provides authentic real-time data access while maintaining proper security isolation.
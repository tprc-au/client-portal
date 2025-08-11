# HubSpot Integration Setup Guide

## Current Status
The TPRC Client Portal is now configured to connect to your HubSpot sandbox. However, to fully utilize all features, your HubSpot Private App needs specific scopes and custom objects.

## Required HubSpot Private App Scopes

Your HubSpot Private App needs these scopes for full functionality:

### Essential Scopes:
- `crm.objects.contacts.read` - Read contact information (client users)
- `crm.objects.companies.read` - Read company information
- `tickets.read` - Read support tickets
- `tickets.write` - Create support tickets

### For Advanced Features:
- `crm.objects.custom.read` - Read custom objects (job orders, applications)
- `crm.objects.custom.write` - Create/update custom objects
- `files.ui_hidden.read` - Access uploaded documents
- `files.ui_hidden.write` - Upload documents

## Custom Objects Needed

For the recruitment portal to work with real data, you'll need these custom objects in HubSpot:

### 1. Job Orders Custom Object
Properties:
- title (text)
- description (long text)
- position_type (dropdown: Full-time, Part-time, Contract)
- location (text)
- status (dropdown: Active, On Hold, Closed, Filled)
- essential_requirements (long text)
- preferred_requirements (long text)
- salary_range (text)
- benefits (long text)
- deadline (date)

Associations: Companies

### 2. Applications Custom Object  
Properties:
- application_date (date)
- status (dropdown: pending_review, approved, rejected, interviewed, selected)
- notes (long text)
- interview_date (date)

Associations: Contacts, Job Orders

### 3. Documents Custom Object
Properties:
- name (text)
- category (dropdown: sponsorship, nomination, other)
- type (text)
- description (text)
- file_url (text)
- upload_date (date)

Associations: Companies, Contacts

## Current Portal Capabilities

With the current setup, the portal can:

✅ Authenticate users against HubSpot contacts
✅ Access company information
✅ Display basic dashboard (will show demo data until custom objects are created)
✅ Handle document uploads (basic file storage)
✅ Support ticket functionality (if tickets scope is enabled)

## Next Steps

1. **Update HubSpot Private App Scopes**: Add the required scopes listed above
2. **Create Custom Objects**: Set up the job orders, applications, and documents objects
3. **Test Authentication**: Try logging in with a contact email from your HubSpot sandbox
4. **Configure Client Data**: Add contacts and companies that will use the portal

## Testing Authentication

Once scopes are updated, you can test with any contact email in your HubSpot sandbox:
- Email: Any contact email from your HubSpot
- Password: Any password (simplified for sandbox testing)

## Fallback Mode

Until custom objects are created, the portal will use demo data to show functionality. The authentication will work with real HubSpot contacts once the scopes are properly configured.
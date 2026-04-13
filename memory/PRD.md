# Spatial+ Office Automation Frontend - PRD

## Original Problem Statement
Build a multi-tenant AI-powered Office Automation web app frontend. Frontend-only React app connecting to a FastAPI backend and n8n webhook workflows built separately.

## User Personas
- **Admin Users**: Manage invoices, meetings, approvals, HR integrations
- **Finance Team**: Upload and track invoices, approve payments
- **Operations Team**: Summarize meetings, manage action items

## Tech Stack
- React with React Router
- Tailwind CSS + Shadcn/ui components
- Axios for API calls
- Mock API responses (backend not yet built)

## Core Requirements (Static)
1. Landing page with Google OAuth flow
2. Dashboard with summary metrics and activity feed
3. Invoice Manager with upload, processing status, and log
4. Meeting Summarizer with audio/transcript upload
5. Approval Center for pending items
6. HR Connect webhook configuration
7. Settings with vendor management and preferences

## What's Been Implemented (Jan 2026)
- [x] Landing page with Connect Google Account CTA
- [x] OAuth simulation with success state
- [x] Dashboard with 4 summary cards and activity feed
- [x] Invoice Manager with upload zone, stepper, and invoice log
- [x] Meeting Summarizer with Upload Audio/Paste Transcript tabs
- [x] Approval Center with approval cards (Approve/Edit/Cancel)
- [x] HR Connect with webhook configuration modal
- [x] Settings with Connected Accounts, Vendors, Notifications
- [x] Responsive sidebar navigation
- [x] Mock API layer with realistic sample data
- [x] All data-testid attributes for testability

## Prioritized Backlog

### P0 - Critical (Done)
- All core pages implemented

### P1 - High Priority (Next)
- Connect to actual FastAPI backend when ready
- Implement real Google OAuth flow
- Add loading states for async operations

### P2 - Medium Priority
- Invoice OCR preview before submission
- Meeting summary export to PDF
- Batch approval functionality
- Email notification integrations

### P3 - Nice to Have
- Dark mode toggle
- Mobile bottom navigation bar
- LinkedIn integration (marked as Coming Soon)
- Real-time webhook status updates

## Next Tasks
1. Backend integration when FastAPI is ready
2. Real OAuth implementation with Google
3. File upload to actual storage (S3/cloud)
4. WebSocket for real-time status updates

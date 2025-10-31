# Example Prompts for Cahoots

This document contains example prompts for testing **full project generation** at various complexity levels with different amounts of detail and formatting.

---

## 🟢 Atomic Tasks (Minimal/No Decomposition)

These are small, well-defined features that should generate 1-5 implementation tasks.

### 1. Simple CRUD Feature (Minimal Detail)
```
Build a task management app where users can create, view, update, and delete tasks
```

### 2. Basic TODO App (With Specifications)
```
Create a simple TODO list application with:
- Add new tasks with title and description
- Mark tasks as complete/incomplete
- Delete tasks
- Filter by status (all, active, completed)
```

### 3. Contact Form (Technical Details)
```
Build a contact form with name, email, and message fields.
Validate email format. Send submissions to an API endpoint.
Store submissions in a database. Display success/error messages.
Tech stack: React frontend, Node.js/Express backend, PostgreSQL database.
```

### 4. URL Shortener (Concise Format)
```
URL shortener service: user enters long URL, system generates short code,
redirects short URL to original. Track click counts.
```

### 5. Weather Widget (List Format)
**Requirements:**
- Display current weather for user's location
- Show temperature, conditions, humidity
- Use OpenWeatherMap API
- Auto-refresh every 15 minutes
- Mobile responsive design

---

## 🟡 Medium Complexity (Moderate Decomposition)

These features require 10-25 implementation tasks with multiple components.

### 1. Blog Platform (Detailed Requirements)
```
Build a blog platform with the following features:

Authentication:
- User registration and login (email/password)
- JWT token-based authentication
- Password reset via email

Content Management:
- Create, edit, delete blog posts
- Rich text editor with markdown support
- Draft and publish workflow
- Featured images for posts
- Categories and tags

Reader Features:
- Browse posts by category/tag
- Search functionality
- Commenting system (logged-in users only)
- Like/bookmark posts
- RSS feed generation

Tech Stack: React, Node.js/Express, MongoDB
```

### 2. Recipe Sharing App (Structured Format)
**Core Features:**
1. Recipe CRUD operations (title, ingredients, steps, prep time, servings)
2. Image upload for recipe photos (AWS S3 or similar)
3. User profiles with favorite recipes
4. Rating and review system (1-5 stars + text review)
5. Search and filter (by cuisine, dietary restrictions, cook time)
6. Ingredient-based search ("I have chicken and rice")

**Tech Requirements:**
- Frontend: React with TypeScript
- Backend: Python/FastAPI
- Database: PostgreSQL
- Image storage: AWS S3 or Cloudinary

### 3. Expense Tracker (Bullet Points)
Create an expense tracking application:
* User authentication with email/password
* Add expenses: amount, category, date, description, receipt photo
* Categories: Food, Transport, Entertainment, Bills, Shopping, Other
* Monthly budget setting per category
* Dashboard with charts: spending by category, trends over time
* Export data as CSV or PDF
* Recurring expense support (monthly bills)
* Multi-currency support
* Mobile-friendly responsive design

### 4. Event Booking System (Paragraph Format)
Build an event booking platform where organizers can create events with details like name, description, date, time, location, capacity, and ticket price. Users should be able to browse upcoming events, filter by category and date, and purchase tickets. Include a payment integration with Stripe. Send confirmation emails after booking. Organizers get a dashboard to view bookings, check-in attendees, and export attendee lists. Include calendar integration (Google Calendar, iCal). Support for free and paid events. Tech stack: React, Node.js, PostgreSQL, Stripe API, SendGrid for emails.

### 5. Fitness Workout Logger (Mixed Format)
**Overview:** Workout tracking app for gym enthusiasts

**Core Functionality:**
- Exercise library with instructions and videos (pre-populated database)
- Create custom workout routines (select exercises, sets, reps, rest time)
- Log completed workouts with weights and notes
- Track progress over time with charts
- Body measurement tracking (weight, body fat %, muscle mass)
- Personal records (PRs) for each exercise
- Rest timer between sets
- Workout history calendar view

**Tech Stack:** React Native, Node.js/Express, PostgreSQL, AWS S3 for videos

---

## 🟠 Complex Tasks (Significant Decomposition)

These projects require 30-60 implementation tasks with multiple integrated systems.

### 1. Social Learning Platform
```
Build a comprehensive online learning platform with social features:

USER MANAGEMENT:
- Multi-role authentication (students, instructors, admins)
- User profiles with bio, avatar, skills, achievements
- OAuth integration (Google, GitHub)
- Email verification and password reset

COURSE CREATION & MANAGEMENT:
- Instructors create courses with modules and lessons
- Support multiple content types: video, text, quizzes, assignments
- Video upload and streaming (AWS S3 + CloudFront or Vimeo)
- Rich text editor with code syntax highlighting
- Course categories and difficulty levels
- Draft/published workflow
- Course pricing (free, one-time, subscription)

LEARNING EXPERIENCE:
- Video player with playback speed control, subtitles
- Progress tracking (% complete per course)
- Note-taking during lessons
- Downloadable resources
- Interactive quizzes with instant feedback
- Assignments with file submission
- Discussion forums per course
- Live Q&A sessions (WebRTC integration)

SOCIAL FEATURES:
- Follow instructors and students
- Activity feed (course completions, new courses, achievements)
- Direct messaging
- Study groups/communities
- Certificate generation upon completion

DISCOVERY & SEARCH:
- Course catalog with filters (category, level, price, rating)
- Full-text search across courses
- Personalized recommendations
- Trending courses
- Instructor profiles with ratings

PAYMENTS & SUBSCRIPTIONS:
- Stripe integration for payments
- Support one-time purchases and subscriptions
- Revenue sharing for instructors
- Coupon/discount codes
- Invoicing and receipt generation

ANALYTICS:
- Student dashboard: progress, completed courses, certificates
- Instructor dashboard: earnings, student enrollments, engagement metrics
- Admin dashboard: platform metrics, user growth, revenue

TECHNICAL REQUIREMENTS:
- Frontend: React with TypeScript, Redux for state management
- Backend: Node.js/Express or Python/FastAPI
- Database: PostgreSQL with Redis for caching
- Video storage: AWS S3
- CDN: CloudFront
- Real-time features: Socket.io or WebSockets
- Email service: SendGrid or AWS SES
- Search: Elasticsearch (optional)
```

### 2. Project Management Tool
**PROJECT:** Asana/Trello alternative with advanced features

**CORE FEATURES:**

Workspace Management:
- Multi-tenant architecture (separate workspaces per organization)
- Workspace branding (logo, colors)
- Invite team members by email
- Role-based permissions (admin, member, guest)

Project Organization:
- Create unlimited projects per workspace
- Multiple views: Board (Kanban), List, Calendar, Gantt chart, Timeline
- Custom fields per project (text, number, dropdown, date, checkbox)
- Project templates for common workflows
- Project archiving and restoration

Task Management:
- Create tasks with title, description, assignee, due date, priority, labels
- Subtasks and checklists
- Task dependencies ("blocks"/"blocked by" relationships)
- Recurring tasks (daily, weekly, monthly)
- Time estimates and time tracking
- Custom statuses per project (To Do, In Progress, Review, Done, etc.)
- Bulk operations (move, update, delete multiple tasks)

Collaboration:
- Comments on tasks with @mentions
- File attachments (images, documents, PDFs)
- Activity log per task
- Real-time updates via WebSockets
- Notifications (in-app, email, optional Slack/Discord integration)

Automation:
- Workflow automation rules (when task moves to "Done", notify assignee)
- Custom automations with triggers and actions
- Integration webhooks

Reporting & Analytics:
- Project progress dashboards
- Burndown charts (for sprint planning)
- Team workload view (tasks per person)
- Time reports (logged time per project/person)
- Custom report builder
- Export reports as CSV/PDF

Search & Filters:
- Full-text search across tasks, comments, attachments
- Advanced filtering (assignee, due date, priority, labels, custom fields)
- Saved filters
- Search across all projects or specific workspace

Mobile App:
- React Native mobile app (iOS/Android)
- Offline support with sync
- Push notifications
- Camera integration for attachments

**TECHNICAL ARCHITECTURE:**
- Frontend: React with TypeScript, Zustand or Redux
- Backend: Python/FastAPI or Node.js with TypeScript
- Database: PostgreSQL
- Real-time: WebSockets (Socket.io or native WS)
- File storage: AWS S3
- Search: PostgreSQL full-text search or Elasticsearch
- Caching: Redis
- Queue: Celery or Bull for background jobs
- Email: SendGrid
- Mobile: React Native

### 3. E-commerce Platform with Vendor Marketplace
Build a full-featured e-commerce marketplace where multiple vendors can sell products (think Etsy or Amazon marketplace):

VENDOR MANAGEMENT
- Vendor registration and approval workflow
- Vendor dashboard: inventory, orders, analytics, earnings
- Store customization (banner, logo, description)
- Vendor verification (business documents, tax ID)
- Commission structure configuration (per vendor or global)
- Vendor ratings and reviews

PRODUCT CATALOG
- Product CRUD with title, description, price, SKU, barcode
- Multiple product images with zoom
- Product variants (size, color, material) with separate pricing
- Inventory tracking with low stock alerts
- Categories and subcategories (nested)
- Product tags and attributes (filterable)
- Digital product support (downloads)
- Bulk product import/export (CSV)

SHOPPING EXPERIENCE
- Advanced product search with filters
- Autocomplete search suggestions
- Product recommendations (also bought, similar items)
- Shopping cart with session persistence
- Guest checkout and registered user checkout
- Wishlist and product comparison
- Recently viewed products
- Customer reviews and ratings with photos

CHECKOUT & PAYMENTS
- Multi-step checkout (cart → shipping → payment → confirmation)
- Multiple shipping addresses per user
- Shipping calculator (rates from carrier APIs)
- Multiple payment methods (credit card, PayPal, Apple Pay, Google Pay)
- Stripe and PayPal integration
- Tax calculation (based on location)
- Discount codes and promotional campaigns
- Gift cards and store credit
- Split payments (partial gift card + credit card)

ORDER MANAGEMENT
- Order tracking with status updates (processing, shipped, delivered)
- Email notifications at each stage
- Packing slips and shipping labels
- Return and refund workflow
- Order cancellation (before shipping)
- Vendor fulfillment dashboard
- Multi-vendor orders (split across vendors)
- Admin order management panel

SHIPPING & LOGISTICS
- Integration with shipping carriers (UPS, FedEx, USPS, DHL)
- Real-time shipping rate calculation
- Tracking number generation
- Shipping label printing
- International shipping support
- Free shipping rules (over $X, certain products)
- Pickup option for local customers

USER ACCOUNTS
- Customer registration and login (email/password, OAuth)
- Order history with re-order option
- Saved addresses and payment methods
- Account dashboard
- Email preferences (marketing, order updates)

ADMIN FEATURES
- Super admin dashboard (sales, revenue, user metrics)
- Vendor approval and management
- Platform-wide product moderation
- Commission and payout management
- Dispute resolution system
- Platform settings and configuration
- User management (suspend, delete)
- Marketing campaigns (email blasts, promotions)

ANALYTICS & REPORTING
- Sales reports (daily, weekly, monthly)
- Product performance analytics
- Customer behavior analytics (conversion funnel)
- Vendor performance reports
- Inventory reports
- Revenue forecasting

ADDITIONAL FEATURES
- Blog/content marketing section
- Email marketing integration (Mailchimp)
- Abandoned cart recovery emails
- Social media sharing
- Affiliate program (optional)
- Multi-language support
- Multi-currency support

TECHNICAL STACK
- Frontend: Next.js (React) with TypeScript, TailwindCSS
- Backend: Python/Django or Node.js/NestJS
- Database: PostgreSQL
- Search: Elasticsearch or Algolia
- Cache: Redis
- Queue: Celery (Python) or Bull (Node.js)
- Storage: AWS S3
- CDN: CloudFront or Cloudflare
- Payment: Stripe, PayPal APIs
- Shipping: EasyPost or ShipStation API
- Email: SendGrid or AWS SES
- Analytics: Mixpanel or custom

---

## 🔴 Epic Tasks (Full Applications, 60+ tasks)

These are large-scale projects requiring extensive decomposition.

### 1. Healthcare Patient Portal
**Build a comprehensive patient portal and practice management system for healthcare providers**

PATIENT-FACING FEATURES:
• Patient registration with medical history intake forms
• Appointment scheduling with calendar view (filter by provider, specialty, location)
• Video telemedicine consultations (WebRTC integration)
• Secure messaging with healthcare providers (HIPAA-compliant)
• Medical records access (lab results, imaging, prescriptions, visit summaries)
• Prescription refill requests with pharmacy integration
• Bill payment and insurance information management
• Upload medical documents (insurance cards, referral letters)
• Family account linking (parents managing children's accounts)
• Appointment reminders (email, SMS via Twilio)
• Health tracking (symptoms, vitals, medications)
• Find a provider search with filters (specialty, location, insurance, availability)

PROVIDER-FACING FEATURES:
• Provider dashboard with daily schedule
• Patient charts (medical history, allergies, medications, visit notes)
• Clinical note templates (SOAP notes)
• E-prescribing with pharmacy database integration
• Lab order entry and results review
• Appointment management (schedule, reschedule, cancel, no-shows)
• Billing and coding (ICD-10, CPT codes)
• Patient messaging with priority flags
• Telehealth video interface
• Referral management
• Document scanning and upload

ADMIN FEATURES:
• Practice management dashboard (appointments, revenue, patient volume)
• User management (patients, providers, staff) with role-based access
• Appointment scheduling templates (provider availability, time slots)
• Insurance provider management
• Billing reports and claim tracking
• HIPAA audit logs
• System settings and configuration
• Analytics and reporting (patient demographics, appointment types, revenue)

INTEGRATIONS:
• EHR/EMR integration (HL7 FHIR standard)
• Pharmacy databases (for e-prescribing)
• Insurance eligibility verification APIs
• Laboratory interfaces (for ordering and results)
• Payment processing (Stripe, Square)
• SMS notifications (Twilio)
• Calendar sync (Google Calendar, Outlook)

COMPLIANCE & SECURITY:
• HIPAA compliance (encryption at rest and in transit)
• Two-factor authentication
• Audit logging for all PHI access
• Automatic session timeout
• Consent forms and digital signatures
• Data backup and disaster recovery
• Business Associate Agreements (BAA) tracking

TECHNICAL REQUIREMENTS:
- Frontend: React with TypeScript, HIPAA-compliant UI design
- Backend: Python/Django or Node.js with strict security policies
- Database: PostgreSQL with encryption
- File storage: AWS S3 with server-side encryption
- Video: Twilio Video or Agora.io for telemedicine
- Real-time: WebSockets for secure messaging
- Queue: Celery or RabbitMQ for background processing
- Email/SMS: SendGrid + Twilio
- Deployment: HIPAA-compliant hosting (AWS with BAA, Azure Health, or GCP)
- Monitoring: HIPAA-compliant logging (no PHI in logs)

### 2. Real Estate Listing Platform
**Create a comprehensive real estate platform for buyers, sellers, and agents (Zillow/Realtor.com alternative)**

USER TYPES & AUTHENTICATION
- Multi-role system: Buyers, Sellers, Agents, Brokers, Admins
- Email/password registration with email verification
- OAuth (Google, Facebook)
- Agent/Broker verification system (license validation)
- Public profile pages for agents with bio, listings, reviews, contact info

PROPERTY LISTINGS
- Create listing: address, price, beds, baths, sqft, lot size, year built, property type (house, condo, townhouse, land, commercial)
- Multiple high-quality photos (up to 50) with drag-to-reorder
- Virtual tour integration (360° photos, Matterport embeds)
- Video tours (YouTube, Vimeo embeds or direct upload)
- Detailed property descriptions with rich text editor
- Amenities checklist (pool, garage, fireplace, AC, etc.)
- HOA information and fees
- Property history (previous sales, price changes)
- Neighborhood info (schools, crime stats, walkability score via APIs)
- Map view with property pin
- Status: Active, Pending, Sold, Off Market
- Featured/Premium listings (paid promotion)

SEARCH & DISCOVERY
- Map-based search with drawing custom boundaries
- Filter by: price range, beds, baths, sqft, property type, lot size, year built, keywords
- Save searches with email alerts for new matches
- Sort by: price, newest, price reduced, square footage
- Nearby searches (find similar properties in area)
- School district search
- Open house calendar view
- Recently viewed properties

AGENT FEATURES
- Agent dashboard with all their listings
- Lead management (inquiries from buyers)
- CRM integration (HubSpot, Salesforce)
- Automated follow-up emails
- MLS integration (import listings from Multiple Listing Service)
- Comparative Market Analysis (CMA) tool
- Client portal (share properties with clients)
- Performance analytics (views, leads, conversions)
- Team management (brokers managing multiple agents)

BUYER TOOLS
- Mortgage calculator with rates (integrate live rate APIs)
- Affordability calculator
- Saved properties and notes
- Schedule showing requests with agents
- Make offers (digital offer forms)
- Favorites/watchlist with price drop alerts
- Neighborhood comparison tool
- Commute time calculator (Google Maps API)

COMMUNICATION
- Secure messaging between buyers and agents
- Showing request scheduling
- Email notifications (new listings, price drops, messages)
- SMS alerts (Twilio integration)
- Video chat for virtual showings

MOBILE APP
- Native iOS and Android apps (React Native)
- Push notifications
- Location-based search (nearby properties)
- Camera integration for reverse image search
- Offline saved searches

MONETIZATION
- Premium listings for agents (featured placement)
- Lead generation subscriptions for agents
- Advertising (banner ads, sponsored listings)
- Freemium model (basic free, advanced features paid)

ADMIN FEATURES
- Listing moderation (approve/reject new listings)
- User management (suspend spam accounts)
- Agent verification workflow
- Platform analytics (listings, users, revenue, engagement)
- Payment management (subscriptions, refunds)
- Content management (blog posts, guides)
- Featured listings management

DATA INTEGRATIONS
- MLS data feeds (listing imports)
- School ratings API (GreatSchools)
- Crime data API
- Walk Score API
- Google Maps API (geocoding, directions, Street View)
- Mortgage rate APIs
- Property tax records
- Census data (demographics)

ADDITIONAL FEATURES
- Blog section with SEO-optimized content
- Real estate guides (first-time buyer tips, etc.)
- Agent reviews and ratings
- Email marketing (newsletters with new listings)
- Social media sharing
- Print-friendly listing PDFs
- Referral program (refer agent, get reward)

TECHNICAL ARCHITECTURE
- Frontend: Next.js (React) with SSR for SEO, TypeScript, TailwindCSS
- Backend: Python/Django or Node.js/NestJS with TypeScript
- Database: PostgreSQL with PostGIS for geospatial queries
- Search: Elasticsearch for fast property search
- Cache: Redis for frequently accessed data
- Storage: AWS S3 + CloudFront CDN
- Maps: Google Maps JavaScript API
- Email: SendGrid
- SMS: Twilio
- Queue: Celery or Bull for background jobs
- Analytics: Google Analytics + custom dashboard
- Mobile: React Native
- Deployment: AWS or GCP with auto-scaling

### 3. Music Streaming Platform
Build a Spotify-like music streaming service with social features and artist tools.

(Include artist uploads, playlists, discovery algorithms, social following, lyrics, podcasts, offline downloads, family plans, analytics for artists, recommendation engine, collaborative playlists, integration with smart speakers, concert listings, merchandise store, etc.)

Tech: React, Node.js, PostgreSQL, Redis, Elasticsearch, AWS S3, audio streaming CDN, ML for recommendations

---

## Tips for Writing Effective Prompts

### ✅ DO:
- Specify tech stack preferences (React, Python, PostgreSQL, etc.)
- Include key features and requirements
- Mention integrations (Stripe, Twilio, AWS, etc.)
- Define user roles (admin, user, guest, etc.)
- Describe data models (users, products, orders, etc.)
- Include non-functional requirements (performance, security, compliance)

### ❌ DON'T:
- Reference existing repositories (for these test prompts)
- Say "fix bug in line 42" (no existing codebase)
- Assume context that doesn't exist
- Be too vague ("build something cool")

### Formatting Styles That Work:
- **Paragraphs:** Natural language description
- **Bullet points:** Clear feature lists
- **Structured sections:** Organized by category
- **Mixed format:** Combine styles for clarity

---

## Complexity Guidelines

**Atomic (1-5 tasks):** Single feature, minimal dependencies, straightforward implementation

**Medium (10-25 tasks):** Multiple components, some integrations, moderate complexity

**Complex (30-60 tasks):** Multiple integrated systems, external APIs, advanced features

**Epic (60+ tasks):** Full applications, multiple user types, extensive feature sets

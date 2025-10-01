# Example Prompts for Cahoots

This document contains example prompts of varying complexity and detail to help you understand how to use Cahoots effectively.

## Simple/Atomic Tasks (No Decomposition)

These tasks are straightforward and don't require breaking down into subtasks:

### 1. Fix a Bug
```
Fix the login button not responding on mobile devices
```

### 2. Update Text
```
Change the homepage title from "Welcome" to "Welcome to Cahoots"
```

### 3. Add Simple Validation
```
Add email validation to the registration form
```

### 4. Update Styling
```
Change the primary button color from blue to green
```

### 5. Simple Configuration
```
Increase the session timeout from 30 minutes to 1 hour
```

---

## Medium Complexity Tasks (1-2 Levels)

These tasks require some breakdown but are relatively straightforward:

### 1. Add a Feature
```
Add a "forgot password" feature that sends a reset link via email
```

**Expected Breakdown:**
- Create password reset request endpoint
- Generate secure reset tokens
- Send email with reset link
- Create reset password form
- Validate token and update password

### 2. API Integration
```
Integrate Stripe payment processing for subscription payments
```

**Expected Breakdown:**
- Set up Stripe API credentials
- Create payment intent endpoint
- Add Stripe checkout component
- Handle webhook events
- Store payment records in database

### 3. Data Export
```
Allow users to export their task history as a CSV file
```

**Expected Breakdown:**
- Create export endpoint
- Generate CSV from task data
- Add download button to UI
- Handle large datasets with pagination

### 4. Search Feature
```
Add search functionality to filter tasks by title, description, and tags
```

**Expected Breakdown:**
- Create search API endpoint
- Add search input to UI
- Implement debounced search
- Display filtered results
- Add search filters (date range, status)

---

## Complex Tasks (3+ Levels)

These tasks require significant decomposition and planning:

### 1. User Authentication System
```
Build a complete user authentication system with email/password login,
Google OAuth, JWT tokens, password reset, and email verification
```

**Expected Breakdown:**
- **Authentication Backend**
  - Email/password registration
  - Login with JWT generation
  - Password hashing and validation
  - Google OAuth integration
  - Token refresh mechanism
- **Email Verification**
  - Generate verification tokens
  - Send verification emails
  - Verification endpoint
  - Resend verification option
- **Password Reset**
  - Request reset token
  - Send reset email
  - Reset password form
  - Token validation
- **Frontend Components**
  - Login form
  - Registration form
  - OAuth buttons
  - Password reset flow
  - Email verification UI

### 2. Real-time Collaboration
```
Implement real-time collaboration so multiple users can edit the same
document simultaneously with live updates, presence indicators, and
conflict resolution
```

**Expected Breakdown:**
- **WebSocket Infrastructure**
  - Set up WebSocket server
  - Connection management
  - Authentication for WebSocket connections
  - Room-based message routing
- **Operational Transformation (OT)**
  - Implement OT algorithm for text
  - Handle concurrent edits
  - Conflict resolution logic
  - Undo/redo with OT
- **Presence System**
  - Track active users
  - Show cursor positions
  - Display user avatars
  - Activity indicators
- **Frontend Integration**
  - WebSocket client
  - Real-time editor updates
  - Presence UI components
  - Offline handling and sync

### 3. Analytics Dashboard
```
Create a comprehensive analytics dashboard that shows user engagement
metrics, task completion rates, time tracking, custom reports, and
data visualization with charts and graphs
```

**Expected Breakdown:**
- **Data Collection**
  - Event tracking system
  - User activity logging
  - Task metrics collection
  - Time tracking implementation
- **Data Processing**
  - Aggregation jobs
  - Data warehouse setup
  - Metrics calculation
  - Report generation
- **API Endpoints**
  - Metrics endpoints
  - Date range filtering
  - Custom report builder
  - Export functionality
- **Visualization Layer**
  - Chart components (line, bar, pie)
  - Interactive dashboards
  - Real-time updates
  - Responsive design
- **Reports & Insights**
  - Predefined report templates
  - Custom report builder
  - Scheduled reports
  - PDF export

---

## Epic-Level Tasks (Project Scale)

These are large initiatives that span multiple features:

### 1. Mobile Application
```
Build a native mobile app for iOS and Android with offline support,
push notifications, camera integration, biometric authentication,
and sync with the web platform
```

**High-level Epic Breakdown:**
- **Infrastructure & Setup**
  - React Native project setup
  - CI/CD pipeline
  - App store configuration
- **Core Features**
  - User authentication
  - Offline data storage
  - Background sync
  - Push notifications
- **Platform-Specific Features**
  - Biometric authentication
  - Camera integration
  - Native UI components
- **Testing & Deployment**
  - Unit and integration tests
  - Beta testing program
  - App store submission

### 2. Multi-tenant SaaS Platform
```
Transform the application into a multi-tenant SaaS platform with
team workspaces, role-based permissions, billing integration,
admin dashboards, usage tracking, and API access
```

**High-level Epic Breakdown:**
- **Tenant Management**
  - Workspace creation and management
  - Team invitations
  - Tenant isolation
  - Data migration tools
- **Access Control**
  - Role-based permissions system
  - Permission inheritance
  - Resource-level access
  - Audit logging
- **Billing & Subscriptions**
  - Subscription plans
  - Billing integration (Stripe)
  - Usage tracking
  - Invoice generation
- **Admin Features**
  - Tenant admin dashboard
  - User management
  - Usage analytics
  - Support tools
- **API Platform**
  - REST API
  - API keys
  - Rate limiting
  - Developer documentation

### 3. E-commerce Platform
```
Build a full e-commerce platform with product catalog, shopping cart,
checkout, payment processing, order management, inventory tracking,
shipping integration, customer reviews, and analytics
```

**High-level Epic Breakdown:**
- **Product Management**
  - Product catalog
  - Categories and tags
  - Variants (size, color, etc.)
  - Inventory tracking
  - Image gallery
- **Shopping Experience**
  - Product search and filters
  - Shopping cart
  - Wishlist
  - Product recommendations
- **Checkout & Payments**
  - Multi-step checkout
  - Payment gateway integration
  - Multiple payment methods
  - Tax calculation
  - Discount codes
- **Order Management**
  - Order processing
  - Order tracking
  - Return/refund handling
  - Customer notifications
- **Shipping & Fulfillment**
  - Shipping calculator
  - Carrier integration
  - Label printing
  - Tracking numbers
- **Customer Features**
  - Reviews and ratings
  - Customer accounts
  - Order history
  - Support tickets

---

## Tips for Writing Good Prompts

### Be Specific About Requirements
❌ **Bad:** "Add user login"
✅ **Good:** "Add user login with email/password authentication, password requirements (min 8 chars, 1 number, 1 special char), and remember me functionality"

### Include Technical Constraints
❌ **Bad:** "Make the app faster"
✅ **Good:** "Optimize the task list to load in under 2 seconds by implementing pagination (50 items per page) and lazy loading images"

### Specify Success Criteria
❌ **Bad:** "Improve the search"
✅ **Good:** "Improve search to return results in under 500ms, support partial matches, and highlight matching text"

### Break Down Ambiguous Tasks
❌ **Bad:** "Fix the bugs"
✅ **Good:** "Fix the login button not responding on mobile Safari and the task list scrolling issue on Chrome"

### Provide Context
❌ **Bad:** "Add notifications"
✅ **Good:** "Add in-app notifications for task assignments, comments, and deadline reminders. Include a notification center with mark as read functionality"

---

## Complexity Indicators

Cahoots uses these factors to determine task complexity:

- **Number of components involved** (frontend, backend, database, external APIs)
- **Technical dependencies** (requires other tasks to be completed first)
- **Uncertainty level** (clear requirements vs. exploration needed)
- **Integration points** (external services, third-party APIs)
- **Testing requirements** (simple validation vs. comprehensive test suite)
- **Domain complexity** (simple CRUD vs. complex business logic)

The system will automatically break down complex tasks into manageable subtasks based on these factors.
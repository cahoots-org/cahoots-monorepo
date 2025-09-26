# Cahoots Project Manager Frontend

A modern React application for the Cahoots Project Manager, providing a JIRA-style task board for task decomposition.

## Features

- Create and manage decomposition tasks
- Real-time updates via WebSocket connection
- JIRA-style task board with columns
- Modern UI built with React and Tailwind CSS

## Getting Started

### Prerequisites

- Node.js 14.x or later
- npm 7.x or later

### Installation

1. Install dependencies:

```bash
npm install
```

2. Create an `.env.local` file in the root directory with the following:

```
REACT_APP_API_URL=http://localhost:8000
```

Adjust the URL if your API is running on a different host or port.

### Development

To start the development server:

```bash
npm start
```

The application will be available at http://localhost:3000.

### Building for Production

To create a production build:

```bash
npm run build
```

The build will be created in the `build` directory.

## Project Structure

- `src/components` - Reusable UI components
- `src/context` - React context for state management
- `src/hooks` - Custom React hooks
- `src/pages` - Application pages/routes
- `src/utils` - Utility functions

## Integration with Backend

The frontend communicates with the Cahoots backend via:

1. RESTful API endpoints for CRUD operations
2. WebSocket connection for real-time updates

## Technologies Used

- React 18
- React Router v6
- Tailwind CSS
- Axios for HTTP requests
- WebSockets for real-time communication 
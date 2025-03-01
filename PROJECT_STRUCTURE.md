# Project Directory Structure Documentation

This document provides a comprehensive overview of the project's directory structure, explaining the purpose and contents of each directory and subdirectory.

## Root Directory

- `/` - The root directory of the project containing all code, configuration, and documentation.

## Core Directories

### `/config`
- Contains configuration files for the application.
  - `/config/agents` - Configuration files for AI agents and their behaviors.

### `/docker`
- Docker-related files for containerization and deployment.
  - `/docker/agent` - Docker configuration for agent services.
  - `/docker/base` - Base Docker images and configurations.
  - `/docker/master` - Master Docker configuration for orchestration.
  - `/docker/scripts` - Scripts used during Docker build and runtime.
    - `/docker/scripts/templates` - Template files used by Docker scripts.
  - `/docker/services` - Docker configurations for microservices.
  - `/docker/web` - Docker configuration for web server.
  - `/docker/web-client` - Docker configuration for the frontend client.

### `/docs`
- Documentation for the project.
  - `/docs/api` - API documentation and specifications.
  - `/docs/brand_guidelines` - Brand identity guidelines.
  - `/docs/business_cards_stationery` - Design files for business materials.
  - `/docs/email_templates` - Email templates for system notifications.
  - `/docs/knowledge_graphs` - Documentation for knowledge graph structures.
  - `/docs/logo` - Logo files and variations.
  - `/docs/marketing_brochure` - Marketing materials.
  - `/docs/operations` - Operational procedures and documentation.
  - `/docs/presentation_deck` - Presentation materials.
  - `/docs/promotional_videos` - Video assets for promotion.
  - `/docs/social_media_graphics` - Graphics for social media.
  - `/docs/user_guides_documentation` - End-user documentation.
  - `/docs/validation` - Validation and verification documentation.

### `/k8s`
- Kubernetes configuration for container orchestration.
  - `/k8s/base` - Base Kubernetes configurations.
    - `/k8s/base/scripts` - Scripts for Kubernetes deployment.
  - `/k8s/dev` - Development environment Kubernetes configurations.
  - `/k8s/local` - Local development Kubernetes configurations.

### `/libs`
- Shared libraries and modules used across the application.
  - `/libs/context` - Context management library.
    - `/libs/context/cahoots_context` - Core context functionality.
  - `/libs/core` - Core functionality shared across services.
    - `/libs/core/cahoots_core` - Core business logic and utilities.
  - `/libs/events` - Event handling and messaging library.
    - `/libs/events/cahoots_events` - Event definitions and handlers.
  - `/libs/sdlc` - Software Development Lifecycle management library.
    - `/libs/sdlc/api` - API interfaces for SDLC functionality.
    - `/libs/sdlc/application` - Application layer for SDLC.
    - `/libs/sdlc/domain` - Domain models and business logic for SDLC.
    - `/libs/sdlc/infrastructure` - Infrastructure implementations for SDLC.

### `/scripts`
- Utility scripts for development, deployment, and maintenance.

### `/services`
- Microservices that make up the application.
  - `/services/agents` - AI agent services.
    - `/services/agents/cahoots_agents` - Core agent functionality.
    - `/services/agents/default` - Default agent implementations.
  - `/services/api` - API service for external communication.
    - `/services/api/api` - API endpoints and controllers.
    - `/services/api/cli` - Command-line interface tools.
    - `/services/api/core` - Core API functionality.
    - `/services/api/migrations` - Database migration scripts.
    - `/services/api/schemas` - Data schemas and validation.
    - `/services/api/services` - Service layer implementations.
    - `/services/api/templates` - Template files used by the API.
    - `/services/api/utils` - Utility functions for the API.
  - `/services/context-manager` - Service for managing context across the application.
    - `/services/context-manager/cahoots_context_manager` - Core context management functionality.

### `/tests`
- Test files and test infrastructure.
  - `/tests/features` - Feature tests (BDD/Behavior-Driven Development).
    - `/tests/features/handlers` - Test handlers for feature tests.
    - `/tests/features/infrastructure` - Test infrastructure for features.
    - `/tests/features/steps` - Step definitions for BDD tests.
    - `/tests/features/views` - View tests for UI components.

### `/web-client`
- Frontend web client application.
  - `/web-client/certs` - SSL certificates for local development.
  - `/web-client/public` - Static public assets.
  - `/web-client/scripts` - Utility scripts for the web client.
  - `/web-client/src` - Source code for the web client.
    - `/web-client/src/assets` - Static assets used in the application.
    - `/web-client/src/components` - Reusable UI components.
    - `/web-client/src/config` - Configuration for the web client.
    - `/web-client/src/lib` - Library code and utilities.
    - `/web-client/src/pages` - Page components for routing.
    - `/web-client/src/stores` - State management stores.

## Excluded Directories (in .gitignore)

The following directories are excluded from version control:

- `/__pycache__/` - Python bytecode cache files.
- `/venv/` - Python virtual environment.
- `/.vscode/` - VS Code editor configuration.
- `/.idea/` - JetBrains IDE configuration.
- `/bin/`, `/lib/`, `/include/` - Virtual environment directories.
- `/workspace/` - Generated workspace files.
- `/node_modules/` - JavaScript dependencies.
- `/.pytest_cache/` - Pytest cache files.
- `/htmlcov/` - HTML coverage reports.

## Special Notes on Directory Structure

1. **API Structure**: The API service follows a layered architecture with clear separation between API endpoints, core business logic, and data access.

2. **Library Organization**: Shared functionality is organized in the `/libs` directory to promote code reuse across services.

3. **Microservices**: The application follows a microservices architecture with each service in the `/services` directory having a specific responsibility.

4. **Testing**: The project uses Behavior-Driven Development (BDD) with feature tests in the `/tests/features` directory.

5. **Frontend**: The web client is a modern React application with a component-based architecture. 
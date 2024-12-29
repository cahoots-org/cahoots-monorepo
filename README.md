# AI Development Team

An autonomous AI development team that collaborates to build software projects. The system uses multiple specialized AI agents (Project Manager, Developer, UX Designer, and Tester) working together through a microservices architecture.

## Features

- 🤖 Multiple specialized AI agents
- 📊 Project management with Trello integration
- 💻 Code generation and review
- 🎨 UX design and mockup creation
- ✅ Automated testing and quality assurance
- 🔄 GitHub integration for version control

## Prerequisites

- Python <=3.12.0
- Docker (for containerized deployment)
- Google Cloud SDK (for production deployment)
- Git

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
GITHUB_API_KEY=your_github_token
TRELLO_API_KEY=your_trello_key
TRELLO_API_SECRET=your_trello_secret
HUGGINGFACE_API_KEY=your_huggingface_token
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ai-dev-team.git
cd ai-dev-team
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Development

Run the development server:
```bash
./scripts/dev.sh
```

Run tests:
```bash
./scripts/test.sh
```

Run locally with Docker:
```bash
./scripts/docker-local.sh
```

## Deployment

The project uses GitHub Actions for CI/CD and deploys to Google Cloud Run. See `.github/workflows/deploy-prod.yml` for details.

## Architecture

The system consists of several microservices:
- Master Service: Orchestrates communication between agents
- Project Manager: Handles project planning and management
- Developer: Generates and reviews code
- UX Designer: Creates design specifications and mockups
- Tester: Generates and runs test suites

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Code of Conduct

Please read our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for details on our code of conduct.

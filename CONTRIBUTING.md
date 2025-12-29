# Contributing to PMOVES-DoX

Thank you for your interest in contributing to PMOVES-DoX! This document provides guidelines for contributing to the project.

## Code of Conduct

Please read and follow our community guidelines. Be respectful, inclusive, and constructive in all interactions.

## Prerequisites

Before contributing, ensure you have:

- **Docker** and Docker Compose
- **Git** with submodule support
- **Python 3.10+** with pip
- **Node.js 18+** with npm
- **Make** (optional, for convenience commands)

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/PMOVES-DoX.git
   cd PMOVES-DoX
   ```
3. Set up the development environment:
   ```bash
   # Backend
   cd backend
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt

   # Frontend
   cd ../frontend
   npm install
   ```

## Project Structure

```
PMOVES-DoX/
├── backend/          # FastAPI Python backend
├── frontend/         # Next.js React frontend
├── docs/             # Documentation
├── samples/          # Sample data files
├── tools/            # Utility scripts
└── supabase/         # Supabase configuration
```

## Contribution Process

### Reporting Issues

1. Search existing issues to avoid duplicates
2. Use issue templates when available
3. Provide clear reproduction steps
4. Include environment details

### Pull Requests

1. Create a feature branch from `main` or `PMOVES.AI-Edition-Hardened`:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. Follow conventional commit format:
   ```
   type(scope): description

   Types: feat, fix, docs, style, refactor, test, chore, ci
   ```

3. Ensure all tests pass:
   ```bash
   # Backend tests
   cd backend && pytest

   # Frontend build
   cd frontend && npm run build
   ```

4. Submit PR targeting the appropriate branch

## Technical Standards

### Backend (Python/FastAPI)

- Follow PEP 8 style guidelines
- Use type hints
- Add docstrings for public functions
- Maintain test coverage

### Frontend (Next.js/TypeScript)

- Follow ESLint configuration
- Use TypeScript strictly
- Keep components modular
- Follow React best practices

### Docker

- Services should expose `/health` endpoint
- Use non-root users in containers
- Document environment variables in `.env.example`

## Testing

Before submitting:

1. Run backend tests:
   ```bash
   cd backend && pytest
   ```

2. Verify frontend builds:
   ```bash
   cd frontend && npm run build
   ```

3. Test Docker deployment:
   ```bash
   docker-compose up --build
   ```

## Documentation

When adding features:

- Update relevant documentation in `docs/`
- Add inline code comments where helpful
- Update API documentation if endpoints change

## Operational Modes

PMOVES-DoX supports two modes:

- **Standalone**: Independent operation with SQLite
- **Docked**: Integration with PMOVES.AI ecosystem

Ensure changes work in both modes when applicable.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

- Open a GitHub issue for questions
- Check existing documentation in `docs/`

Thank you for contributing to PMOVES-DoX!

# Contributing to NetOpsHub

Thank you for your interest in contributing to NetOpsHub! This document provides
guidelines and information for contributors.

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (optional, for full-stack testing)

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# Backend tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=netopshub --cov-report=term-missing

# Frontend type checking
cd frontend && npx tsc --noEmit
```

## Code Style

- **Python**: We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting
- **TypeScript**: Standard TypeScript strict mode
- **Commits**: Use conventional commit messages (`feat:`, `fix:`, `docs:`, etc.)

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Write tests for new functionality
4. Ensure all tests pass (`pytest tests/`)
5. Submit a pull request with a clear description

## Areas for Contribution

- **Collection engines**: Support for additional protocols (gNMI, NETCONF)
- **Vendor support**: Additional vendor parsers and compliance rules
- **Agent capabilities**: Enhanced diagnosis patterns, ML models
- **Frontend**: Interactive topology visualization, metric charts
- **Documentation**: Tutorials, API reference, deployment guides
- **Testing**: Additional test coverage, integration tests

## Architecture Overview

See the [README](README.md) for the high-level architecture diagram.

### Key Principles

1. **Demo mode first**: All components work in demo mode without external dependencies
2. **Unified models**: All data flows through `netopshub.models` Pydantic schemas
3. **Agent pattern**: Each AI agent is independent and communicates through the coordinator
4. **HITL safety**: All remediation actions require human approval

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

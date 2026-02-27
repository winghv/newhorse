# Contributing to Newhorse

Thank you for your interest in contributing to Newhorse! This guide will help you get started.

## Prerequisites

- **Node.js** 18+ and npm 9+
- **Python** 3.10+
- A **Claude API key** (from [Anthropic Console](https://console.anthropic.com/))

## Development Setup

```bash
# Clone the repository
git clone https://github.com/winghv/newhorse.git
cd newhorse

# Install dependencies (sets up both frontend and backend)
npm install

# Copy environment template and configure your API key
cp .env.example .env

# Start the development servers (API + Web)
npm run dev
```

This launches the FastAPI backend and Next.js frontend concurrently.

## Project Structure

```
apps/api/           FastAPI backend (SQLAlchemy + SQLite)
apps/web/           Next.js 14 frontend (App Router + Tailwind CSS)
extensions/skills/  Agent skill extensions
scripts/            Development scripts
docs/               Documentation
```

## How to Contribute

### Reporting Bugs

Open a [Bug Report](../../issues/new?template=bug_report.md) issue. Include steps to reproduce, expected behavior, and your environment details.

### Suggesting Features

Open a [Feature Request](../../issues/new?template=feature_request.md) issue. Describe the problem, your proposed solution, and alternatives you've considered.

### Submitting Code

1. Fork the repository and create a feature branch from `master`.
2. Make your changes, following the code style guidelines below.
3. Test your changes locally with `npm run dev`.
4. Submit a pull request using the provided PR template.

## Code Style

- **Python**: Formatted and linted with [Ruff](https://docs.astral.sh/ruff/)
- **TypeScript/JavaScript**: Linted with ESLint (Next.js config)
- Keep code simple and focused -- avoid over-engineering.

## Commit Convention

We use the format: `type: description`

| Type       | Usage                                     |
|------------|-------------------------------------------|
| `feat`     | New feature                               |
| `fix`      | Bug fix                                   |
| `refactor` | Code restructuring without behavior change|
| `chore`    | Maintenance, dependencies, tooling        |

- Write commit messages in **English**.
- One commit per logical change.

**Examples:**
```
feat: add agent export functionality
fix: resolve WebSocket reconnection on timeout
refactor: extract shared validation logic
chore: update Python dependencies
```

## Need Help?

If you have questions or run into issues, feel free to open a [discussion](../../discussions) or reach out via an issue. We're happy to help!

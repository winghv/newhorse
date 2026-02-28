# Getting Started

This guide will help you get Newhorse up and running quickly.

## Prerequisites

Before you begin, ensure you have:

- **Node.js 18+** - [Download](https://nodejs.org/)
- **Python 3.10+** - [Download](https://www.python.org/)
- **Claude Code CLI** - Installed and configured with API access

## Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url> newhorse
cd newhorse
```

### 2. Install Dependencies

```bash
npm install
```

This installs:
- Node.js dependencies for the monorepo
- Frontend dependencies in `apps/web`

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` as needed. The defaults work for local development.

### 4. Start Development Server

```bash
npm run dev
```

This command will:
1. Check and create `.env` if needed
2. Create Python virtual environment
3. Install Python dependencies
4. Start the FastAPI backend on port 8999
5. Start the Next.js frontend on port 3999

## First Steps

### 1. Open the Web Interface

Navigate to http://localhost:3999

### 2. Create a Project

Click "New Project" and enter a name.

### 3. Start Chatting

Click on your project to open the chat interface. Start typing to interact with the Hello Agent.

## Next Steps

- [Create your own Agent](./agent-development.md)
- [Create custom Skills](./skill-development.md)
- [Deploy to production](./deployment.md)

## Troubleshooting

### Python virtual environment issues

```bash
cd apps/api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### WebSocket connection fails

Make sure the backend is running on port 8999. Check the terminal for errors.

### Claude API errors

Ensure Claude Code CLI is properly configured with valid API credentials.

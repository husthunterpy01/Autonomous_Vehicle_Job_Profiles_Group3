# Autonomous Vehicle Job Finder Frontend

Frontend application for the Autonomous Vehicle Job Profiles project.

## Technology

- Next.js
- React
- TypeScript
- Tailwind CSS
- ESLint
- Prettier

## Requirements

- Node.js 20.9 or later
- npm

## Installation

From the repository root:

```bash
cd frontend
npm install
```

## Environment variables

Copy `.env.example` to `.env.local`.

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Run locally

```bash
npm run dev
```

Open the following pages:

- http://localhost:3000
- http://localhost:3000/search
- http://localhost:3000/signup
- http://localhost:3000/login

The signup and login forms call the backend authentication API with
`credentials: "include"`. The JWT is kept in an HTTP-only cookie and is never
written to `localStorage` or `sessionStorage`. After authentication, the navbar
loads `/api/v1/auth/me` and displays the signed-in profile menu.

## Code checks

```bash
npm run format
npm run lint
npm run build
```

## Project structure

```text
app/              Next.js routes and pages
components/       Reusable React components
lib/services/     API configuration and service functions
styles/           Shared styles and documentation
public/           Static assets
```

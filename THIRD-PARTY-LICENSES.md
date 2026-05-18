# Third-Party Licenses

NousViz includes third-party open-source software. Below is a summary of licenses used.

## Frontend (apps/web/)

| License | Package Count |
|---------|--------------|
| MIT | ~310 |
| ISC | ~21 |
| Apache-2.0 | ~9 |
| BSD-3-Clause | ~5 |
| CC-BY-4.0 | 1 |
| 0BSD | 1 |

Key dependencies: React (MIT), Vite (MIT), Tailwind CSS (MIT), Lucide React (ISC), Recharts (MIT).

## Backend (apps/api/)

| License | Package |
|---------|---------|
| MIT | FastAPI, Uvicorn, python-dotenv |
| BSD-3-Clause | psycopg2 |
| Apache-2.0 | bcrypt, cryptography |
| PSF | Python standard library |

## Full Dependency Lists

- **Frontend:** Run `npx license-checker --summary` in `apps/web/`
- **Backend:** Run `pip-licenses` with the virtualenv active

All third-party software is used under its original license terms. No modifications to third-party source code are included in this repository.

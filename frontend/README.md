# Cathode Frontend

This is the React + TypeScript + Vite frontend for Cathode.

Use the repo-root launcher to run the full web stack:

```bash
./start.sh --react
```

Manual frontend-only run:

```bash
npm run dev -- --host 127.0.0.1 --port 9322
```

The frontend expects the FastAPI server on `127.0.0.1:9321` unless Vite proxy settings are changed.

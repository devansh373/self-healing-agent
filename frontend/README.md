# Self-Healing Infrastructure Agent — Frontend

This is the real-time telemetry dashboard for the Self-Healing Infrastructure Agent. Built with **Next.js 16 (App Router)**, **TypeScript**, and **Vanilla CSS**, it provides live observability into infrastructure failures, autonomous AI remediation attempts, and sandbox validation telemetry.

## Features

- **Live WebSocket Streaming**: Connects natively to `ws://localhost:8000/ws/deployments` to display live state transitions (`FAILED` → `HEALING` → `HEALED` / `FAILED_TO_HEAL`) without page refreshes.
- **Interactive Triggering**: A "Run Demo Pipeline" button initiates the simulated Terraform breakage.
- **Diagnostic Telemetry Panels**: Displays monospace `<pre>` blocks containing broken HCL code, stderr error logs, AI root-cause analysis with synthesized HCL patches, and verification outputs.
- **Rich Dark Mode Aesthetics**: Glassmorphism cards, glowing status badges, and smooth CSS micro-animations.

## Prerequisites

- Node.js 20+ and npm
- Running local backend server on port 8000 (see `../backend/README.md`)

## Getting Started

1. **Environment Configuration**  
Ensure `.env.local` exists in the `frontend` directory:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/deployments
```

2. **Install Dependencies**  
```bash
npm install
```

3. **Run Development Server**  
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser to interact with the dashboard.

## Production Build Verification

To verify TypeScript compliance and production asset compilation:
```bash
npm run build
```

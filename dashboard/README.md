# Pyqual Dashboard

A serverless dashboard for visualizing pyqual quality metrics across multiple repositories.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   CI/CD Pipeline│────▶│  JSON Artifacts │────▶│  Static Dashboard│
│  (GitHub/GitLab)│     │  (summary.json) │     │   (React SPA)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │  Optional API   │
                       │  (FastAPI)      │
                       │  for local dev  │
                       └─────────────────┘
```

## Features

- 📊 Real-time quality metrics visualization
- 📈 Historical trends and regressions
- 🔍 Multi-repository overview
- 🚀 Serverless deployment (GitHub Pages, Cloudflare Pages)
- 📱 Responsive design
- 🔐 No backend required for production

## Quick Start

### Production (Serverless)

1. **Configure CI to upload artifacts**:
   - GitHub Actions: Use the provided `.github/workflows/pyqual-enhanced.yml`
   - GitLab CI: Use the provided `.gitlab-ci.yml`

2. **Deploy to GitHub Pages**:
   ```bash
   # Clone this dashboard
   git clone https://github.com/your-org/pyqual-dashboard
   cd pyqual-dashboard
   
   # Configure your repositories
   cp config/repos.example.json config/repos.json
   # Edit repos.json with your repository URLs
   
   # Deploy
   npm install
   npm run build
   npm run deploy
   ```

### Local Development

1. **Start the development server**:
   ```bash
   cd dashboard
   npm install
   npm run dev
   ```

2. **Start the optional API server**:
   ```bash
   cd api
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

3. **Open http://localhost:3000**

## Configuration

### Repository Configuration

Create `config/repos.json`:

```json
{
  "repositories": [
    {
      "id": "pyqual",
      "name": "Pyqual",
      "url": "https://github.com/semcod/pyqual",
      "branch": "main",
      "ciUrl": "https://github.com/semcod/pyqual/actions"
    },
    {
      "id": "my-project",
      "name": "My Project",
      "url": "https://github.com/myorg/my-project",
      "branch": "main",
      "ciUrl": "https://github.com/myorg/my-project/actions"
    }
  ]
}
```

### Data Sources

The dashboard can fetch data from:

1. **Direct GitHub Releases** (recommended):
   - CI creates a GitHub Release with artifacts
   - Dashboard fetches `summary.json` from release assets

2. **Raw Git LFS**:
   - Push `.pyqual/` directory to LFS
   - Dashboard fetches from Git LFS

3. **S3/Cloud Storage**:
   - CI uploads to S3 bucket
   - Dashboard fetches from storage

4. **Local API**:
   - FastAPI server serves local `.pyqual/` data
   - Useful for testing and on-premises

## Data Format

The dashboard expects `summary.json` in this format:

```json
{
  "timestamp": "2026-03-31T20:00:00Z",
  "commit": "abc123...",
  "branch": "main",
  "status": "passed|failed",
  "duration_s": 62.114,
  "iterations": 1,
  "metrics": {
    "coverage": 85.5,
    "maintainability": 75.2,
    "security": 100.0
  },
  "gates": [
    {
      "metric": "coverage",
      "value": 85.5,
      "threshold": 80.0,
      "passed": true
    }
  ],
  "stages": [
    {
      "name": "test",
      "duration_s": 10.5,
      "passed": true,
      "skipped": false
    }
  ]
}
```

## Deployment Options

### GitHub Pages

```yaml
# .github/workflows/deploy-dashboard.yml
name: Deploy Dashboard
on:
  push:
    branches: [main]
    paths: ['dashboard/**']
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: |
          cd dashboard
          npm install
          npm run build
          npm run deploy
```

### Cloudflare Pages

1. Connect your GitHub repo
2. Build command: `cd dashboard && npm run build`
3. Output directory: `dashboard/dist`

### Vercel

```bash
vercel --prod
```

## Customization

### Adding New Metrics

1. Update `src/types/metrics.ts`
2. Add visualization in `src/components/MetricsPanel.tsx`
3. Update color schemes in `src/theme/colors.ts`

### Theming

Edit `src/theme/index.ts`:

```typescript
export const theme = {
  colors: {
    primary: '#your-color',
    success: '#your-green',
    warning: '#your-yellow',
    error: '#your-red'
  }
}
```

## API Reference (Optional)

If using the FastAPI backend:

- `GET /api/projects` - List all repositories
- `GET /api/projects/{id}/runs` - Get recent runs
- `GET /api/projects/{id}/metrics` - Get metrics history
- `GET /api/projects/{id}/runs/{run_id}` - Get specific run details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

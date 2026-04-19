## Overview

This guide explains how to integrate Pyqual into your CI/CD pipelines and set up a dashboard for visualizing quality metrics across multiple repositories.

## Table of Contents

1. [CI/CD Integration](#cicd-integration)
   - [GitHub Actions](#github-actions)
   - [GitLab CI](#gitlab-ci)
2. [Dashboard Setup](#dashboard-setup)
   - [Prerequisites](#prerequisites)
   - [Installation](#installation)
   - [Configuration](#configuration)
   - [Deployment](#deployment)
3. [Data Sources](#data-sources)
4. [Troubleshooting](#troubleshooting)

### GitHub Actions

1. Copy the enhanced workflow file to your repository:
   ```bash
   cp .github/workflows/pyqual-enhanced.yml .github/workflows/pyqual.yml
   ```

2. Configure repository secrets:
   - `ANTHROPIC_API_KEY`: For Claude Code integration
   - `OPENROUTER_API_KEY`: For alternative LLM models
   - `OPENAI_API_KEY`: For GPT models
   - `LLM_MODEL`: Default model to use
   - `COVERAGE_THRESHOLD`: Minimum coverage percentage
   - `PYQUAL_ENABLE_FIX`: Enable/disable automatic fixes
   - `PYQUAL_MAX_ITERATIONS`: Maximum fix iterations
   - `DASHBOARD_TOKEN`: Token for dashboard updates (optional)
   - `DASHBOARD_REPO`: Repository for dashboard data (optional)

3. The workflow will:
   - Test against Python 3.9-3.12
   - Run quality gates
   - Generate summary reports
   - Upload artifacts
   - Comment on PRs with results
   - Update dashboard (if configured)

### GitLab CI

1. Copy the GitLab CI configuration:
   ```bash
   cp .gitlab-ci.yml .gitlab-ci.yml
   ```

2. Configure CI/CD variables:
   - `ANTHROPIC_API_KEY`
   - `OPENROUTER_API_KEY`
   - `OPENAI_API_KEY`
   - `LLM_MODEL`
   - `COVERAGE_THRESHOLD`
   - `PYQUAL_ENABLE_FIX`
   - `PYQUAL_MAX_ITERATIONS`

3. Features:
   - Parallel execution across Python versions
   - Combined reporting
   - Review apps for merge requests
   - Scheduled nightly runs

### Prerequisites

- Node.js 18+ and npm
- (Optional) Python 3.9+ for API server

### Installation

1. Clone or copy the dashboard:
   ```bash
   cd dashboard
   npm install
   ```

2. Create configuration:
   ```bash
   cp config/repos.example.json config/repos.json
   ```

3. Edit `config/repos.json`:
   ```json
   {
     "repositories": [
       {
         "id": "my-project",
         "name": "My Project",
         "url": "https://github.com/myorg/my-project",
         "branch": "main",
         "ciUrl": "https://github.com/myorg/my-project/actions"
       }
     ],
     "refreshInterval": 60,
     "theme": "light"
   }
   ```

#### Repository Configuration

Each repository requires:
- `id`: Unique identifier
- `name`: Display name
- `url`: Repository URL
- `branch`: Default branch
- `ciUrl`: Link to CI/CD pipeline

#### Environment Variables

- `VITE_API_URL`: Backend API URL (default: http://localhost:8000)
- `VITE_GITHUB_TOKEN`: GitHub token for higher rate limits

#### Development

1. Start the frontend:
   ```bash
   npm run dev
   ```

2. (Optional) Start the API server:
   ```bash
   cd api
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

3. Open http://localhost:3000

##### GitHub Pages

1. Build and deploy:
   ```bash
   npm run build
   npm run deploy
   ```

2. Configure GitHub Pages in repository settings to deploy from `gh-pages` branch

##### Cloudflare Pages

1. Connect your repository to Cloudflare Pages
2. Build command: `npm run build`
3. Output directory: `dist`
4. Environment variables: `VITE_API_URL`, `VITE_GITHUB_TOKEN`

##### Vercel

```bash
npm install -g vercel
vercel --prod
```

## Data Sources

The dashboard can fetch data from multiple sources:

### 1. GitHub Releases (Recommended)

CI creates releases with artifacts:
```yaml
- name: Create Release
  uses: actions/create-release@v1
  with:
    tag_name: pyqual-${{ github.run_number }}
    release_name: Pyqual Report #${{ github.run_number }}
    draft: false
    prerelease: false
```

### 2. Direct Git LFS

Store `.pyqual/` directory in Git LFS:
```bash
git lfs track ".pyqual/*.json"
git lfs track ".pyqual/*.db"
git add .gitattributes
```

### 3. S3/Cloud Storage

Upload artifacts to S3:
```bash
aws s3 sync .pyqual/ s3://my-bucket/pyqual/${REPO_NAME}/${COMMIT_SHA}/
```

### 4. Local API Server

For on-premises or development:
- API reads from local `.pyqual/` directories
- Supports ingestion endpoint for CI uploads

### Summary JSON Structure

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
  "stages": [
    {
      "name": "test",
      "duration_s": 10.5,
      "passed": true,
      "skipped": false
    }
  ],
  "gates": [
    {
      "metric": "coverage",
      "value": 85.5,
      "threshold": 80.0,
      "passed": true
    }
  ]
}
```

### Charts Not Displaying

1. **Check browser console** for JavaScript errors
2. **Verify Recharts installation**:
   ```bash
   npm list recharts
   ```
3. **Check data format** - ensure metrics are numbers, not strings
4. **Verify Tailwind CSS** is properly configured

### API Connection Issues

1. **Check CORS settings** in FastAPI
2. **Verify API URL** in environment variables
3. **Check authentication** for protected endpoints

### Data Not Loading

1. **Verify GitHub token** has repository access
2. **Check rate limits** - use authenticated requests
3. **Verify repository URLs** are correct
4. **Check CI artifacts** are being uploaded

#### Issue: "No runs" displayed
- Solution: Ensure CI is running and uploading artifacts
- Check if `summary.json` exists in artifacts

#### Issue: Charts show no data
- Solution: Verify metrics are numeric values
- Check browser console for data parsing errors

#### Issue: Dashboard not updating
- Solution: Verify refresh interval settings
- Check if data source is accessible

### Custom Metrics

Add custom metrics by extending the summary JSON:
```json
{
  "metrics": {
    "custom_metric": 95.0,
    "performance_score": 88.5
  }
}
```

### Custom Themes

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

### Adding New Chart Types

1. Create new component in `src/components/`
2. Import in `RepositoryDetail.tsx`
3. Add data fetching logic in `api/index.ts`

## Security Considerations

1. **API Authentication**: Use bearer tokens for ingestion
2. **CORS**: Restrict to allowed origins
3. **Rate Limiting**: Implement for public dashboards
4. **Data Privacy**: Avoid storing sensitive data in artifacts

## Performance Optimization

1. **Caching**: Implement API response caching
2. **Lazy Loading**: Load charts on demand
3. **Data Aggregation**: Pre-compute historical data
4. **CDN**: Use CDN for static assets

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Add tests
5. Submit pull request

## Support

- Issues: [GitHub Issues](https://github.com/semcod/pyqual/issues)
- Documentation: [Pyqual Docs](https://pyqual.readthedocs.io)
- Community: [Discussions](https://github.com/semcod/pyqual/discussions)

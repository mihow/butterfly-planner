# Branch Preview Options

Guide to setting up automatic preview deployments for pull requests.

## Current Implementation ✅

**GitHub Actions Artifacts** (Already configured!)

- Uploads `site/` folder as downloadable artifact for all `claude/*` branches
- Retention: 7 days
- Access: Go to Actions → Workflow Run → Download artifact
- Cost: Free (included in GitHub Actions)

**How to use:**
1. Push to branch → GitHub Actions runs
2. Navigate to workflow run
3. Download `site-preview-<sha>.zip`
4. Unzip and open `index.html` locally

---

## Option 1: Netlify Deploy Previews (Recommended)

**Best for:** Automatic preview URLs, zero config, free tier

### Setup (5 minutes)

1. **Sign up at Netlify**
   - Link GitHub account
   - Import `mihow/butterfly-planner` repository

2. **Configure build settings**
   - Build command: `make install-dev && butterfly-planner refresh`
   - Publish directory: `site/`
   - Python version: 3.12

3. **Add netlify.toml**
   ```toml
   [build]
     command = "pip install -e . && python -m butterfly_planner.flows.fetch && python -m butterfly_planner.flows.build"
     publish = "site/"

   [build.environment]
     PYTHON_VERSION = "3.12"

   [[redirects]]
     from = "/*"
     to = "/index.html"
     status = 200
   ```

4. **Enable Deploy Previews**
   - Go to Site Settings → Build & Deploy → Deploy Previews
   - Enable "Any pull request against your production branch"

### Result

Every PR gets:
- Preview URL: `https://deploy-preview-123--butterfly-planner.netlify.app`
- Automatic updates on each push
- Comment on PR with preview link
- SSL certificate (HTTPS)
- Fast CDN delivery

### Pros
✅ Automatic preview URLs
✅ Comments on PRs with link
✅ Free for open source
✅ Zero maintenance
✅ Fast deploys (~2 min)
✅ Custom domains supported

### Cons
❌ Requires third-party service
❌ Free tier: 300 build minutes/month
❌ Preview URLs are public (no auth)

---

## Option 2: Vercel Deploy Previews

**Best for:** Next.js/React apps (overkill for static sites, but works)

### Setup

1. Sign up at https://vercel.com
2. Import GitHub repo
3. Add `vercel.json`:
   ```json
   {
     "buildCommand": "pip install -e . && butterfly-planner refresh",
     "outputDirectory": "site",
     "installCommand": "pip install uv && uv sync"
   }
   ```

### Result

Similar to Netlify:
- Preview URL: `https://butterfly-planner-abc123.vercel.app`
- Auto-updates on push
- PR comments

### Pros/Cons
Similar to Netlify, slightly faster builds but more complex config for Python apps.

---

## Option 3: GitHub Pages Branch Previews

**Best for:** No third-party dependencies, uses GitHub infrastructure

### Setup

Add to `.github/workflows/pr-preview.yml`:

```yaml
name: PR Preview

on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: write
  pull-requests: write

jobs:
  deploy-preview:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install and build
        run: |
          pip install -e .
          butterfly-planner refresh

      - name: Deploy to gh-pages branch
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./site
          destination_dir: pr-${{ github.event.pull_request.number }}

      - name: Comment PR
        uses: actions/github-script@v7
        with:
          script: |
            const previewUrl = `https://${context.repo.owner}.github.io/${context.repo.repo}/pr-${{ github.event.pull_request.number }}/`;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## 🦋 Preview Deployed!\n\n${previewUrl}`
            });
```

### Result

- Preview URL: `https://mihow.github.io/butterfly-planner/pr-123/`
- Deploys to `gh-pages` branch in subdirectories
- Free, no third-party services

### Pros
✅ No third-party service
✅ Completely free
✅ Uses existing GitHub infrastructure

### Cons
❌ Requires manual cleanup (old PR previews remain)
❌ Slower than Netlify/Vercel
❌ Need to enable GitHub Pages
❌ More complex workflow management

---

## Option 4: Cloudflare Pages

**Best for:** Edge performance, international users

### Setup

1. Sign up at https://pages.cloudflare.com
2. Connect GitHub repo
3. Build settings:
   - Build command: `pip install -e . && butterfly-planner refresh`
   - Output directory: `site`

### Result

- Preview URL: `https://abc123.butterfly-planner.pages.dev`
- Automatic PR comments
- Global CDN (very fast)

### Pros
✅ Fast global CDN
✅ Unlimited bandwidth
✅ Great free tier
✅ DDoS protection

### Cons
❌ Build times can be slow
❌ Less Python-friendly than Netlify

---

## Option 5: Local Preview Server

**Best for:** Quick local testing without deployment

Already working! Just run:

```bash
git checkout <branch>
butterfly-planner refresh
butterfly-planner serve
```

Then share via:
- **ngrok:** `ngrok http 8000` → Get public URL
- **localtunnel:** `lt --port 8000` → Get public URL
- **serveo:** `ssh -R 80:localhost:8000 serveo.net`

### Pros
✅ Instant (no deploy wait)
✅ Full control
✅ Works offline

### Cons
❌ Requires local machine running
❌ Not automatic
❌ Temporary URLs

---

## Comparison Matrix

| Feature                  | GitHub Artifact | Netlify | Vercel | GH Pages | Cloudflare |
|--------------------------|----------------|---------|--------|----------|------------|
| Auto preview URL         | ❌              | ✅       | ✅      | ✅        | ✅          |
| PR comments              | ❌              | ✅       | ✅      | ⚠️       | ✅          |
| Setup time               | ✅ (done)       | 5 min   | 5 min  | 10 min   | 5 min      |
| Free tier                | ✅              | ✅       | ✅      | ✅        | ✅          |
| Third-party service      | ❌              | ✅       | ✅      | ❌        | ✅          |
| Build speed              | N/A            | ⚡⚡     | ⚡⚡    | ⚡        | ⚡          |
| Custom domains           | ❌              | ✅       | ✅      | ⚠️       | ✅          |
| HTTPS                    | N/A            | ✅       | ✅      | ✅        | ✅          |
| Zero config              | ✅              | ❌       | ❌      | ❌        | ❌          |

---

## Recommendation

**For this project:**

1. **Keep GitHub Artifacts** (current) for now
   - Already working
   - Zero config
   - Good for quick checks

2. **Add Netlify** when you want shareable URLs
   - Takes 5 minutes
   - Best UX for reviewers
   - Free and reliable

3. **Skip Vercel/Cloudflare** unless you need their specific features

---

## Implementation: Add Netlify

### Step 1: Create netlify.toml

```bash
cat > netlify.toml << 'EOF'
[build]
  command = "pip install -e . && python -m butterfly_planner.flows.fetch && python -m butterfly_planner.flows.build"
  publish = "site/"

[build.environment]
  PYTHON_VERSION = "3.12"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[context.deploy-preview]
  command = "pip install -e . && python -m butterfly_planner.flows.fetch && python -m butterfly_planner.flows.build"

[context.production]
  command = "pip install -e . && python -m butterfly_planner.flows.fetch && python -m butterfly_planner.flows.build"
EOF
```

### Step 2: Push to repo

```bash
git add netlify.toml
git commit -m "Add Netlify configuration for deploy previews"
git push
```

### Step 3: Connect to Netlify

1. Go to https://app.netlify.com/
2. Click "Add new site" → "Import an existing project"
3. Choose GitHub → Select `butterfly-planner`
4. Netlify auto-detects settings from `netlify.toml`
5. Click "Deploy"

### Step 4: Enable PR previews

- Go to Site Settings → Build & Deploy → Deploy Previews
- Select "Any pull request against your production branch"
- Save

Done! Next PR will have a preview URL automatically.

---

## Testing Preview Deployments

Create a test PR:

```bash
git checkout -b test-preview
echo "<!-- Test -->" >> site/index.html
git add site/index.html
git commit -m "Test preview deployment"
git push -u origin test-preview
gh pr create --title "Test: Preview deployment" --body "Testing automatic previews"
```

Check:
- ✅ GitHub Actions artifact appears
- ✅ Netlify preview URL posted as comment (if configured)
- ✅ Site loads correctly
- ✅ Data is fresh (check timestamp)

---

## Troubleshooting

**Build fails on Netlify:**
- Check build logs for Python errors
- Verify `PYTHON_VERSION = "3.12"` is set
- Check if all dependencies are in `pyproject.toml`

**Preview URL shows 404:**
- Check `publish = "site/"` directory is correct
- Verify build command actually creates `site/index.html`
- Check Netlify build logs

**Data is stale:**
- API may be rate-limited
- Check Open-Meteo API status
- Verify fetch command ran successfully

**Preview takes too long:**
- Netlify free tier queues builds
- Consider caching dependencies
- Use `requirements.txt` instead of full install

---

## Future Enhancements

1. **Preview screenshots** - Auto-capture preview and post to PR
2. **Visual regression testing** - Compare preview to main
3. **Lighthouse scores** - Performance metrics on each PR
4. **A/B testing** - Deploy multiple variants
5. **Password protection** - Secure previews for private testing

---

## Cost Estimates (Monthly)

All options below assume ~20 PRs/month, 5 pushes per PR:

| Service         | Free Tier            | After Free Tier |
|-----------------|----------------------|-----------------|
| GitHub Artifact | Unlimited            | N/A             |
| Netlify         | 300 build min/month  | $19/mo          |
| Vercel          | 100 deploys/day      | $20/mo          |
| GH Pages        | Unlimited            | N/A             |
| Cloudflare      | Unlimited            | N/A             |

This project (1 location, static site) stays well within all free tiers.

---

## References

- Netlify: https://docs.netlify.com/site-deploys/deploy-previews/
- Vercel: https://vercel.com/docs/deployments/preview-deployments
- Cloudflare Pages: https://developers.cloudflare.com/pages/
- GitHub Pages: https://docs.github.com/en/pages
- ngrok: https://ngrok.com/docs

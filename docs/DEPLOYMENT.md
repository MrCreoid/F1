# Deployment

## Hugging Face backend

1. Create a public **Docker** Space named `weather-whiplash-api`.
2. Authenticate Git with a Hugging Face write token:

   ```bash
   export HF_TOKEN=hf_your_write_token
   hf auth login --token "$HF_TOKEN" --add-to-git-credential
   ```

3. Push the current branch:

   ```bash
   git push huggingface main
   ```

4. In Space **Settings → Variables**, set `WW_CORS_ORIGINS` to
   `https://mrcreoid.github.io` (no repository path or trailing slash).
5. Confirm `https://mrcreoid-weather-whiplash-api.hf.space/api/health` returns JSON.

The `Dockerfile` exposes FastAPI on port 7860. Free Space storage is temporary, so
uploads and SQLite sessions are cleared whenever the Space restarts.

## GitHub Pages frontend

1. Create the GitHub repository `mrcreoid/F1`, then update the deleted remote:

   ```bash
   git remote set-url origin https://github.com/mrcreoid/F1.git
   git push -u origin main
   ```

2. In **Settings → Pages**, choose **GitHub Actions**.
3. In **Settings → Secrets and variables → Actions → Variables**, add:

   ```text
   HF_API_URL=https://mrcreoid-weather-whiplash-api.hf.space
   ```

4. Push to `main` or manually run **Deploy frontend to GitHub Pages**. The workflow
   publishes the static `frontend/out` build.

`HF_API_URL` is public configuration, not a secret. Never put `HF_TOKEN` in GitHub
variables, source files, or commits.

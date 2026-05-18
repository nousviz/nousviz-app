# Installing Plugins from Private Repositories

NousViz supports installing plugins from private Git repositories via SSH deploy keys or HTTPS personal access tokens.

---

## Option 1: SSH Deploy Keys (Recommended)

SSH deploy keys are the most secure option — each key is scoped to a single repository.

### Step 1: Generate a key in NousViz

1. Go to **Settings → Security → Deploy Keys**
2. Click **Generate Key**
3. Give it a name (e.g. "GitHub - My Plugin")
4. Select the host (github.com, gitlab.com, or bitbucket.org)
5. Click **Generate** — a public key will be displayed

### Step 2: Add the key to your repository

**GitHub:**
1. Go to your repository → Settings → Deploy keys
2. Click "Add deploy key"
3. Paste the public key from Step 1
4. Title it "NousViz Deploy"
5. Leave "Allow write access" unchecked (read-only is sufficient)

**GitLab:**
1. Go to your project → Settings → Repository → Deploy keys
2. Click "Add new key"
3. Paste the public key

**Bitbucket:**
1. Go to your repository → Repository settings → Access keys
2. Click "Add key"
3. Paste the public key

### Step 3: Install the plugin

1. Go to **Marketplace → Install from URL**
2. Enter the SSH URL: `git@github.com:your-org/your-plugin.git`
3. Enter the plugin ID (the `name` field from the plugin's `plugin.yaml`)
4. Click **Install**

### Multiple repositories

Generate a separate deploy key for each repository that hosts a plugin. Each key is independent — revoking one doesn't affect others.

---

## Option 2: GitHub Personal Access Token (HTTPS)

If you prefer HTTPS or need access to multiple repositories under one org, use a GitHub Personal Access Token.

### Step 1: Generate a token on GitHub

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Click "Generate new token"
3. Select the repositories you need access to
4. Grant **Contents: Read-only** permission
5. Copy the token

### Step 2: Configure in NousViz

1. Go to **Settings → Security → Git Access Token**
2. Paste the token
3. Click **Save**

The token is stored encrypted and automatically used when cloning from HTTPS URLs.

### Step 3: Install

1. Go to **Marketplace → Install from URL**
2. Enter the HTTPS URL: `https://github.com/your-org/your-plugin.git`
3. Enter the plugin ID
4. Click **Install**

---

## Troubleshooting

### "Plugin not found at tag 'vX.Y.Z'"

The plugin repository must have a Git tag matching the version in `plugin.yaml`. If the manifest says `version: 1.0.0`, the repo needs a `v1.0.0` tag.

### "Permission denied (publickey)"

- Verify the deploy key is added to the correct repository
- Test the key using the **Test** button in Settings → Security → Deploy Keys
- Ensure the key wasn't generated for a different host

### "repository_url must use https:// or git@"

Only HTTPS and SSH URLs are supported. `file://` and `ssh://` protocol URLs are blocked for security.

### Clone timeout

If the server can't reach the Git host, check:
- Firewall rules allow outbound SSH (port 22) or HTTPS (port 443)
- DNS resolution works on the server

# GitHub Sync & GPG Authentication Guide

This guide outlines the steps to set up GPG signing for your commits and sync a new local project with a GitHub repository.

## Part 1: Setting up GPG Signing

Since `gpg` is not currently installed on your system, follow these steps to set it up.

### 1. Install GPG
Use Homebrew to install the GPG tools:
```bash
brew install gnupg
```

### 2. Generate a GPG Key
Run the following command to generate a new key pair:
```bash
gpg --full-generate-key
```
- Select **(1) RSA and RSA** (default).
- Select **4096** bits for key size.
- Set the expiration (e.g., **0** for no expiration).
- Enter your name and the **email address** associated with your GitHub account.
- Set a secure passphrase.

### 3. Get Your Key ID
List your keys to find the ID of the key you just created:
```bash
gpg --list-secret-keys --keyid-format LONG
```
Output example:
```
sec   rsa4096/3AA5C34371567BD2 2025-11-21 [SC]
      ...
uid                 [ultimate] Your Name <your.email@example.com>
```
In this example, the Key ID is `3AA5C34371567BD2` (the part after `rsa4096/`).

### 4. Export Public Key for GitHub
Run this command using your Key ID:
```bash
gpg --armor --export <YOUR_KEY_ID>
```
Copy the entire output (starting with `-----BEGIN PGP PUBLIC KEY BLOCK-----`).

### 5. Add Key to GitHub
1. Go to [GitHub Settings > SSH and GPG keys](https://github.com/settings/keys).
2. Click **New GPG key**.
3. Paste the key block you copied.
4. Click **Add GPG key**.

### 6. Configure Git to Use the Key
Run these commands in your terminal (replace `<YOUR_KEY_ID>` with your actual ID):
```bash
git config --global user.signingkey <YOUR_KEY_ID>
git config --global commit.gpgsign true
```

### 7. Configure GPG Agent (Optional but Recommended)
To prevent GPG from failing in VS Code or other GUIs, add this to your `~/.zshrc` or `~/.bash_profile`:
```bash
export GPG_TTY=$(tty)
```

---

## Part 2: Syncing a New Project with GitHub

Follow these steps when you have a local folder that you want to push to a new GitHub repository.

### 1. Initialize Git
Navigate to your project folder and run:
```bash
git init
```

### 2. Stage and Commit Files
```bash
git add .
git commit -m "Initial commit"
# If GPG is set up, it will ask for your passphrase here to sign the commit.
```

### 3. Create Repository on GitHub
1. Go to [github.com/new](https://github.com/new).
2. Enter a **Repository name**.
3. **Important:** Do NOT check "Initialize with README", ".gitignore", or "License" (since you have local files).
4. Click **Create repository**.

### 4. Link and Push
Copy the repository URL (e.g., `https://github.com/username/repo.git` or `git@github.com:username/repo.git`) and run:

```bash
# Rename branch to main
git branch -M main

# Add remote
git remote add origin <REMOTE_URL>

# Push to GitHub
git push -u origin main
```

## Troubleshooting

- **Permission Denied (publickey):** Ensure your SSH key is added to the agent:
  ```bash
  ssh-add ~/.ssh/id_ed25519_ganimedes
  ```
- **Unrelated Histories:** If you accidentally initialized the repo on GitHub with a README, use:
  ```bash
  git pull origin main --allow-unrelated-histories --no-rebase
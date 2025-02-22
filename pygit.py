import os
import zipfile
import boto3
import tempfile
from github import Github

# GitHub credentials
ACCESS_TOKEN = "your-github-personal-access-token"  # Use AWS Secrets Manager for security
GITHUB_OWNER = "your-username-or-org"
GITHUB_REPO = "your-repository-name"
BRANCH = "main"

# Amazon Bedrock details
BEDROCK_MODEL_ID = "anthropic.claude-v2"  # Change as needed
bedrock_client = boto3.client("bedrock-runtime")

def download_github_repo():
    """Download all files from a GitHub repository and return the local directory."""
    g = Github(ACCESS_TOKEN)
    repo = g.get_repo(f"{GITHUB_OWNER}/{GITHUB_REPO}")
    
    temp_dir = tempfile.mkdtemp()  # Temporary directory for Lambda storage
    contents = repo.get_contents("", ref=BRANCH)
    queue = contents

    while queue:
        file_content = queue.pop(0)

        if file_content.type == "dir":  # Fetch subdirectories
            queue.extend(repo.get_contents(file_content.path, ref=BRANCH))
        else:  # Download file
            file_path = os.path.join(temp_dir, file_content.path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as file:
                file.write(file_content.decoded_content)
    
    return temp_dir

def zip_directory(directory):
    """Zip all files in a directory and return the ZIP file path."""
    zip_path = os.path.join(tempfile.gettempdir(), "repo.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, directory))
    return zip_path

def send_to_bedrock(file_path):
    """Send the zipped repository code to Amazon Bedrock for code review."""
    with open(file_path, "rb") as file:
        code_content = file.read()

    payload = {
        "prompt": "Review this Python code for optimization and performance improvements.",
        "inputText": code_content.decode("utf-8", errors="ignore"),  # Convert to text
        "temperature": 0.5
    }

    response = bedrock_client.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=str(payload)
    )

    return response["body"].read().decode("utf-8")

def lambda_handler(event, context):
    """AWS Lambda handler to download a GitHub repo, zip it, and send it to Bedrock."""
    try:
        repo_dir = download_github_repo()
        zip_path = zip_directory(repo_dir)
        review_result = send_to_bedrock(zip_path)

        return {
            "statusCode": 200,
            "body": review_result
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": str(e)
        }

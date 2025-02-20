import json
import boto3
from github import Github

def get_github_repo_files(repo_name, github_token):
    """Fetch specific files (.py, .js, requirements.txt, package.json) and their contents from a GitHub repository."""
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    files_data = {}
    allowed_extensions = {".py", ".js", "requirements.txt", "package.json"}
    
    contents = repo.get_contents("")
    while contents:
        file_content = contents.pop(0)
        if file_content.type == "file":
            if any(file_content.path.endswith(ext) for ext in allowed_extensions):
                files_data[file_content.path] = file_content.decoded_content.decode('utf-8')
        elif file_content.type == "dir":
            contents.extend(repo.get_contents(file_content.path))
    
    return files_data

def invoke_bedrock_agent(payload, agent_id, agent_alias_id, region="us-east-1"):
    """Invoke AWS Bedrock Agent with the provided payload."""
    client = boto3.client("bedrock-agent-runtime", region_name=region)
    
    response = client.invoke_agent(
        agentId=agent_id,
        agentAliasId=agent_alias_id,
        sessionId="session-12345",
        inputText=json.dumps(payload)
    )
    
    return response["completion"]

def lambda_handler(event, context):
    """AWS Lambda handler function."""
    repo_name = event.get("repo_name")  # e.g., "owner/repo"
    github_token = event.get("github_token")
    agent_id = event.get("agent_id")
    agent_alias_id = event.get("agent_alias_id")
    
    if not (repo_name and github_token and agent_id and agent_alias_id):
        return {"statusCode": 400, "body": "Missing required parameters"}
    
    try:
        files_data = get_github_repo_files(repo_name, github_token)
        
        # Send file data to Bedrock Agent for dependency analysis
        response = invoke_bedrock_agent(files_data, agent_id, agent_alias_id)
        
        return {
            "statusCode": 200,
            "body": json.loads(response)
        }
    except Exception as e:
        return {"statusCode": 500, "body": str(e)}

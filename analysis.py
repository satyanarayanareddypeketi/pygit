import boto3
import json
import time
import math

# Initialize Lambda client
lambda_client = boto3.client('lambda')
pricing_client = boto3.client('pricing')

def lambda_handler(event, context):
 try:
 # Extracting action and memory details
 action = event['action']
 memory = event['memory'] # Memory setting (e.g., 128MB, 256MB, 512MB)
 function_name = 'YourLambdaFunctionName'
 alias_name = f"memory_{memory}_alias"
 requests = event['requests'] # Number of requests for testing
 region = "us-east-1" # AWS region, modify as needed

 # AWS Pricing Data for Lambda
 pricing_data = get_lambda_pricing(region)

 if action == 'check_alias_version':
 # Check if the version exists for the given memory setting
 version_name = f"v{memory}"

 try:
 # Check if the alias already exists
 response = lambda_client.get_alias(
 FunctionName=function_name,
 Name=alias_name
 )
 print(f"Alias {alias_name} already exists.")
 except lambda_client.exceptions.ResourceNotFoundException:
 print(f"Alias {alias_name} does not exist. Creating...")
 lambda_client.create_alias(
 FunctionName=function_name,
 Name=alias_name,
 FunctionVersion=version_name
 )
 print(f"Alias {alias_name} created successfully.")
 
 return {
 "status": "Alias Checked and Created if necessary"
 }

 elif action == 'run_test':
 # Run Lambda test with specific memory setting and request count
 print(f"Starting test for {memory}MB memory with {requests} requests.")
 
 # Create a new version of the Lambda function for the specified memory
 version_response = lambda_client.publish_version(
 FunctionName=function_name,
 Description=f"Lambda version for {memory}MB"
 )
 version_name = version_response['Version']
 print(f"Published version {version_name} for {memory}MB.")

 # Set the alias to point to the newly published version
 lambda_client.update_alias(
 FunctionName=function_name,
 Name=alias_name,
 FunctionVersion=version_name
 )

 # Invoke the Lambda function for each request and measure execution time
 start_time = time.time()
 for _ in range(requests):
 response = lambda_client.invoke(
 FunctionName=function_name,
 Payload=json.dumps({"memory": memory}),
 )
 response_payload = json.loads(response['Payload'].read().decode('utf-8'))
 print(f"Lambda invoked. Response: {response_payload}")
 
 execution_time = time.time() - start_time
 print(f"Completed {requests} requests in {execution_time} seconds.")
 
 # Calculate execution cost based on the number of requests and memory
 cost = calculate_execution_cost(memory, execution_time, requests, pricing_data)
 print(f"Estimated cost for {memory}MB memory and {requests} requests: ${cost:.4f}")

 return {
 "status": "Test Completed",
 "execution_time": execution_time,
 "cost": cost
 }

 elif action == 'cleanup':
 # Cleanup: Remove alias and version after testing
 try:
 lambda_client.delete_alias(
 FunctionName=function_name,
 Name=alias_name
 )
 print(f"Alias {alias_name} deleted successfully.")
 except lambda_client.exceptions.ResourceNotFoundException:
 print(f"Alias {alias_name} not found for cleanup.")
 
 return {
 "status": "Cleanup Completed"
 }

 else:
 return {
 "error": "Unknown action"
 }

 except Exception as e:
 print(f"Error: {str(e)}")
 return {
 "error": str(e)
 }


def get_lambda_pricing(region):
 """
 Retrieves the Lambda pricing data for the specified region.
 The pricing data is fetched from AWS pricing API.
 """
 try:
 # Fetch Lambda pricing for the given region
 pricing_response = pricing_client.get_products(
 ServiceCode='AWSLambda',
 Filters=[
 {
 'Type': 'TERM_MATCH',
 'Field': 'location',
 'Value': f"AWS Lambda – Compute Charges ({region})"
 }
 ]
 )
 
 # Extract pricing information from the response
 price_list = pricing_response['PriceList']
 price_data = json.loads(price_list[0])
 price_dimensions = price_data['terms']['OnDemand']
 
 lambda_pricing = {}
 
 for price_key, price_value in price_dimensions.items():
 memory_size = int(price_key.split('.')[1].replace('MB', ''))
 price = float(price_value['priceDimensions'][list(price_value['priceDimensions'].keys())[0]]['pricePerUnit']['USD'])
 lambda_pricing[memory_size] = price
 
 return lambda_pricing

 except Exception as e:
 print(f"Error retrieving pricing: {str(e)}")
 return {}


def calculate_execution_cost(memory, execution_time, requests, pricing_data):
 """
 Calculate the cost of executing the Lambda function based on the memory, time, and request count.
 """
 memory_cost = pricing_data.get(memory, 0)
 
 # Lambda pricing is based on GB-seconds (memory * time in seconds)
 execution_in_gb_seconds = (memory / 1024) * execution_time # Memory in GB * time in seconds
 
 # The pricing is charged per GB-second, so multiply by the number of requests
 total_cost = memory_cost * execution_in_gb_seconds * requests

 return total_cost

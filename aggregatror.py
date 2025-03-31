import json

def lambda_handler(event, context):
try:
results = event['results']

# Initialize variables for tracking the best result
best_result = None
best_cost = float('inf')

for result in results:
memory = result['memory']
avg_execution_time = result['avg_execution_time']
estimated_cost = result['estimated_cost']

# Update the best result based on the lowest cost
if estimated_cost < best_cost:
best_cost = estimated_cost
best_result = {
"memory": memory,
"avg_execution_time": avg_execution_time,
"estimated_cost": best_cost
}

return {
"best_memory_setting": best_result
}

except Exception as e:
print(f"Error in Aggregator Lambda: {str(e)}")
return {"error": str(e)}

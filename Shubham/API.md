# Targets API Documentation

A RESTful API for managing the list of websites the WebHealth crawler monitors. Built with Amazon API Gateway, AWS Lambda, and DynamoDB.

## Base URL

Each environment has its own API endpoint, shown as a CloudFormation output after deployment:

Find your deployed URL:
```bash
aws cloudformation describe-stacks --stack-name Prod-ShubhamStack --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='TargetsApiEndpoint'].OutputValue" --output text
```

## Data model

| Field | Type | Description |
|-------|------|--------------|
| `name` | string | Unique identifier for the target (partition key) |
| `url`  | string | The website URL to monitor |

## Endpoints

### Create a target

POST /targets

**Request body:**
```json
{ "name": "ExampleSite", "url": "https://example.com" }
```

**Response:** `201 Created`
```json
{ "name": "ExampleSite", "url": "https://example.com" }
```

**Errors:** `400 Bad Request` if `name` or `url` is missing.

---

### List all targets

GET /targets

**Response:** `200 OK`
```json
[
  { "name": "ExampleSite", "url": "https://example.com" },
  { "name": "AnotherSite", "url": "https://another.example" }
]
```

---

### Update a target

PUT /targets/{name}

**Request body:**
```json
{ "url": "https://new-url.example" }
```

**Response:** `200 OK`
```json
{ "name": "ExampleSite", "url": "https://new-url.example" }
```

**Errors:** `400 Bad Request` if `url` is missing.

---

### Delete a target

DELETE /targets/{name}

**Response:** `204 No Content`

## Example usage (curl)

```bash
API_URL="https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/targets"

# Create
curl -X POST "$API_URL" -H "Content-Type: application/json" \
  -d '{"name": "ExampleSite", "url": "https://example.com"}'

# List
curl "$API_URL"

# Update
curl -X PUT "$API_URL/ExampleSite" -H "Content-Type: application/json" \
  -d '{"url": "https://updated.example"}'

# Delete
curl -X DELETE "$API_URL/ExampleSite"
```

## Architecture

Client → API Gateway → Lambda (Create/List/Update/Delete) → DynamoDB (TargetsTable)

Each CRUD operation is handled by its own Lambda function (`CreateTargetFn`, `ListTargetsFn`, `UpdateTargetFn`, `DeleteTargetFn`), defined in `lambda/targets_api.py`. Each function has least-privilege IAM access, scoped to read/write only the `TargetsTable`.

## Testing

- **Unit tests** (`tests/unit/test_targets_api.py`) — test each Lambda handler's logic with mocked DynamoDB calls
- **Functional tests** (`tests/functional/test_shubham_stack.py`) — confirm the API Gateway and DynamoDB table are defined correctly in the CDK stack
- **Integration test** (`tests/integration/test_deployed_monitor.py`) — calls the real, deployed API in Beta to confirm create and read work end to end
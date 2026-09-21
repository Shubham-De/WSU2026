# Website Monitor with AWS CDK and Lambda

A small serverless project that checks whether a website is up and how fast it responds. It is built with the AWS CDK (Python) and runs as an AWS Lambda function.

## What it does

The `WebMonitor` Lambda function visits a website and reports:

- **is_up**: whether the site responded successfully
- **status_code**: the HTTP status code (200 means OK)
- **response_time_ms**: how long the request took, in milliseconds

The monitored site is `https://www.westernsydney.edu.au/`.

## Project structure

| Path | Purpose |
|------|---------|
| `app.py` | Entry point for the CDK app |
| `shubham/shubham_stack.py` | Defines the AWS resources (two Lambda functions) |
| `lambda/hello.py` | Hello Lambda warm-up function |
| `lambda/monitor.py` | Website monitor function |

## Prerequisites

- Python 3
- Node.js
- AWS CLI, configured with `aws configure`
- AWS CDK: `npm install -g aws-cdk`

## Setup and deploy

```bash
cd Shubham
python -m venv .venv          # only if .venv doesn't exist yet
.venv\Scripts\activate        # Windows
python -m pip install -r requirements.txt
cdk bootstrap                 # once per account and region
cdk deploy
```

The stack is deployed to **us-east-1 (N. Virginia)**.

## Testing

1. Open the AWS Console and go to **Lambda**, then open the function whose name starts with `ShubhamStack-WebMonitor`.
2. Open the **Test** tab and run it with the default `{}` event.

### Sample output

```json
{
  "url": "https://www.westernsydney.edu.au/",
  "is_up": true,
  "status_code": 200,
  "response_time_ms": 791
}
```

## Clean up

To remove everything from AWS:

```bash
cdk destroy
```

## What I learned

- Infrastructure as Code: defining AWS resources in Python instead of clicking in the console
- How Lambda functions, handlers and IAM execution roles fit together
- Using Git and GitHub to version the project
# Website Monitor with AWS CDK and Lambda

A small serverless project that checks whether websites are up and how fast they respond. It is built with the AWS CDK (Python), runs as an AWS Lambda function every 5 minutes, and sends its results to CloudWatch, where they appear on a dashboard and trigger alarms.

## What it does

The `WebMonitor` Lambda function reads a list of websites from `lambda/websites.json`, visits each one, and records two metrics in CloudWatch:

- **Availability**: 1 if the site responded successfully, 0 if not
- **Latency**: response time in milliseconds

An EventBridge rule runs the function **every 5 minutes**.

## Project structure

| Path | Purpose |
|------|---------|
| `app.py` | Entry point for the CDK app |
| `shubham/shubham_stack.py` | Defines the AWS resources (Lambdas, schedule, dashboard, alarms) |
| `lambda/hello.py` | Hello Lambda warm-up function |
| `lambda/monitor.py` | Website monitor function |
| `lambda/websites.json` | List of websites to check |
| `RUNBOOK.md` | What to do when an alarm fires |

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

## Monitoring

| Component | Details |
|-----------|---------|
| Metrics namespace | `WebHealth` |
| Dashboard | `WebHealth` (availability and latency graphs for each site) |
| Availability alarm | Triggers when availability drops below 1 |
| Latency alarm | Triggers when latency is above 3000 ms for 2 checks in a row |

### Adding a website

Add an entry to `lambda/websites.json`, then run `cdk deploy`:

```json
{ "name": "Example", "url": "https://example.com/" }
```

The dashboard and alarms are created for the new site automatically.

## Testing

1. Open the AWS Console and go to **Lambda**, then open the function whose name starts with `ShubhamStack-WebMonitor`.
2. Open the **Test** tab and run it with the default `{}` event.

### Sample output

```json
[
  { "website": "WesternSydney", "is_up": true, "latency_ms": 414 },
  { "website": "GitHub", "is_up": true, "latency_ms": 40 },
  { "website": "Wikipedia", "is_up": true, "latency_ms": 80 }
]
```

## Progress

- [x] CDK and AWS account setup
- [x] Hello Lambda
- [x] Website monitor Lambda
- [x] Check a list of websites from JSON
- [x] Run automatically every 5 minutes
- [x] Send metrics to CloudWatch with boto3
- [x] CloudWatch dashboard
- [x] Availability and latency alarms
- [ ] Alarm notifications (email through SNS)

## Runbook

See [RUNBOOK.md](RUNBOOK.md) for how to respond to alarms.

## Clean up

To remove everything from AWS:

```bash
cdk destroy
```

## What I learned

- Infrastructure as Code: defining AWS resources in Python instead of clicking in the console
- How Lambda functions, handlers and IAM execution roles fit together
- Writing custom metrics to CloudWatch with boto3
- Scheduling with EventBridge, and building dashboards and alarms in CDK
- Using Git and GitHub to version the project
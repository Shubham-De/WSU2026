# Website Monitor with AWS CDK, Lambda and CI/CD

A small serverless project that checks whether websites are up and how fast they respond. It is built with the AWS CDK (Python), runs as an AWS Lambda function every 5 minutes, and sends its results to CloudWatch, where they appear on a dashboard and trigger alarms. Changes are deployed through a CI/CD pipeline with separate **Beta** and **Prod** environments, gated by an automated test suite and protected by automatic rollback.

## What it does

The `WebMonitor` Lambda function reads a list of websites from `lambda/websites.json`, visits each one, and records two metrics in CloudWatch:

- **Availability**: 1 if the site responded successfully, 0 if not
- **Latency**: response time in milliseconds

An EventBridge rule runs the function **every 5 minutes**.

## CI/CD pipeline

Code pushed to the `main` branch on GitHub triggers an AWS CodePipeline (`WebHealthPipeline`) that:

1. **Source** — pulls the latest commit from GitHub
2. **Build** — installs dependencies, **runs the unit and functional test suite**, then runs `cdk synth`
3. **UpdatePipeline** — lets the pipeline update its own definition if it changed
4. **Beta** — deploys a full, independent copy of the stack for testing
5. **IntegrationTests** — runs integration tests against the real, deployed Beta environment
6. **PromoteToProd** — pauses for manual approval in the AWS Console
7. **Prod** — deploys the same stack to production, once approved

If any test fails, the pipeline stops — broken code cannot reach Beta or Prod.

```
GitHub push → Source → Build (tests + Synth) → Beta → Integration tests → Manual approval → Prod
```

To set this up from scratch, see [Pipeline setup](#pipeline-setup) below.

## Automated testing

| Type | Count | What it checks | Runs |
|------|-------|-----------------|------|
| Unit | 12 | Individual functions in `monitor.py` and `alarm_logger.py`, with AWS calls mocked | Before Beta deploys |
| Functional | 8 | The CDK stack synthesizes the correct resources (Lambda count, alarm thresholds, DynamoDB keys, etc.) using `aws_cdk.assertions` | Before Beta deploys |
| Integration | 2 | The real, deployed Beta Lambda runs successfully and sends real metrics to CloudWatch | After Beta deploys, before Prod |

Run locally:
```bash
python -m pip install -r requirements-dev.txt
python -m pip install boto3
python -m pytest tests/unit tests/functional -v   # fast, no AWS needed
python -m pytest tests/integration -v              # needs Beta deployed + AWS credentials
```

## Operational health and automated rollback

In addition to monitoring the *websites being checked*, the stack monitors the **WebMonitor Lambda itself**:

| Alarm | Triggers when |
|-------|---------------|
| Duration | Average run time exceeds 50 seconds (2 checks in a row) |
| Errors | The function throws an error |
| Throttles | The function is throttled by Lambda's concurrency limits |
| No invocations | The function hasn't run in 10 minutes (the schedule may be broken) |

`WebMonitor` is deployed through a **Lambda alias** (`live`), managed by **AWS CodeDeploy**. Every pipeline deployment publishes a new Lambda version and shifts the alias to it. CodeDeploy watches the Duration, Errors and Throttles alarms during the deployment — if any of them trip, **the alias automatically rolls back to the previous working version**, with no manual action needed.

The "No invocations" alarm is alert-only (not a rollback trigger), since a missed schedule isn't something a code rollback fixes.

Lambda memory usage is visible per-invocation in the Lambda console's **Monitor** tab and in CloudWatch Logs, though it isn't exposed as a standard alarmable metric the way duration and errors are.

## Project structure

| Path | Purpose |
|------|---------|
| `app.py` | Entry point for the CDK app — defines the pipeline stack |
| `shubham/pipeline_stack.py` | Defines the CodePipeline: source, build, test gates, Beta and Prod stages |
| `shubham/app_stage.py` | Wraps `ShubhamStack` so it can be deployed once per environment (Beta, Prod) |
| `shubham/shubham_stack.py` | Defines the AWS resources (Lambdas, alias, CodeDeploy, schedule, dashboard, alarms, SNS, DynamoDB) |
| `lambda/hello.py` | Hello Lambda warm-up function |
| `lambda/monitor.py` | Website monitor function |
| `lambda/alarm_logger.py` | Saves alarm events into DynamoDB |
| `lambda/websites.json` | List of websites to check |
| `tests/unit/` | Unit tests (12) |
| `tests/functional/` | Functional/infrastructure tests (8) |
| `tests/integration/` | Integration tests against the deployed Beta environment (2) |
| `RUNBOOK.md` | What to do when an alarm fires |

## Prerequisites

- Python 3
- Node.js
- AWS CLI, configured with `aws configure`
- AWS CDK: `npm install -g aws-cdk`
- A GitHub personal access token with `repo` scope, stored in AWS Secrets Manager under the name `github-token`:
```bash
aws secretsmanager create-secret --name github-token --secret-string "<your token>"
```

## Pipeline setup

The pipeline itself only needs to be deployed once, by hand. After that, every push to `main` deploys automatically.

```bash
cd Shubham
python -m venv .venv          # only if .venv doesn't exist yet
.venv\Scripts\activate        # Windows
python -m pip install -r requirements.txt
cdk bootstrap                 # once per account and region
cdk deploy WebHealthPipelineStack
```

The pipeline and both environments (Beta, Prod) are deployed to **us-east-1 (N. Virginia)**.

After the first deploy, push to `main` to trigger the pipeline's first real run:

```bash
git add .
git commit -m "Trigger pipeline"
git push
```

Watch it run in the AWS Console under **CodePipeline → Pipelines → WebHealthPipeline**. When it reaches **PromoteToProd**, click **Review → Approve** to let it continue to Prod.

## Monitoring

| Component | Details |
|-----------|---------|
| Metrics namespace | `WebHealth` |
| Dashboard | `WebHealth-<stack name>` (availability and latency graphs for each site) — a separate dashboard per environment |
| Availability alarm | Triggers when availability drops below 1 |
| Latency alarm | Triggers when latency is above 3000 ms for 2 checks in a row |

### Notifications and alarm history

When an alarm changes state, it publishes to an **SNS topic**, which:

1. Sends an **email** to the address set as `alert_email` in `shubham/shubham_stack.py`
2. Triggers the `AlarmLogger` Lambda, which saves the event in a **DynamoDB** table

Each environment (Beta, Prod) has its own topic and table.

| Field | Meaning |
| ----------- | ----------- |
| `alarm_name` | Which alarm changed |
| `timestamp` | When it changed |
| `new_state` | `ALARM` or `OK` |
| `old_state` | The previous state |
| `reason` | Why CloudWatch changed the state |

To view the history, open DynamoDB in the AWS Console, then Tables, then the relevant `AlarmLogTable`, then Explore table items.

### Testing notifications

Force an alarm into the ALARM state (replace with the full alarm name, e.g. one prefixed `Prod-ShubhamStack-...`):

```bash
aws cloudwatch set-alarm-state --alarm-name "<alarm name>" --state-value ALARM --state-reason "Testing notifications"
```

### Adding a website

Add an entry to `lambda/websites.json`, commit and push:

```json
{ "name": "Example", "url": "https://example.com/" }
```

The pipeline deploys the change to Beta, then Prod (after approval), and the dashboard and alarms are created for the new site automatically in both.

## Testing the monitor

1. Open the AWS Console and go to **Lambda**.
2. Open the function whose name starts with `Prod-ShubhamStack-WebMonitor` (or `Beta-ShubhamStack-WebMonitor` to test the staging copy).
3. Open the **Test** tab and run it with the default `{}` event.

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
- [x] Alarm notifications (email through SNS)
- [x] Alarm history logged in DynamoDB
- [x] CI/CD pipeline with Beta and Prod stages
- [x] Automated test suite (12 unit, 8 functional, 2 integration), enforced as pipeline blockers
- [x] Operational Lambda health alarms (duration, errors, throttles, invocations)
- [x] Automated rollback via Lambda alias + CodeDeploy
- [ ] CRUD API Gateway for the website target list

## Runbook

See [RUNBOOK.md](RUNBOOK.md) for how to respond to alarms.

## Clean up

To remove an environment, delete its stack directly (the pipeline will redeploy it on the next push):

```bash
aws cloudformation delete-stack --stack-name Beta-ShubhamStack --region us-east-1
aws cloudformation delete-stack --stack-name Prod-ShubhamStack --region us-east-1
```

To remove the pipeline itself:

```bash
cdk destroy WebHealthPipelineStack
```

## What I learned

- Infrastructure as Code: defining AWS resources in Python instead of clicking in the console
- How Lambda functions, handlers and IAM execution roles fit together
- Writing custom metrics to CloudWatch with boto3
- Scheduling with EventBridge, and building dashboards and alarms in CDK
- Publishing alarm events through SNS, and logging them to DynamoDB
- Building a multi-stage CI/CD pipeline with AWS CDK Pipelines, including Beta, manual approval, and Prod
- Writing unit, functional and integration tests with pytest and `aws_cdk.assertions`, and wiring them as blocking gates in a pipeline
- Granting a CodeBuild step specific IAM permissions (`role_policy_statements`) to call AWS services it needs for integration testing
- Deploying Lambda through a versioned alias with CodeDeploy, and using CloudWatch alarms to trigger automatic rollback
- Why CloudFormation resources with fixed names (like a dashboard name) collide across stacks, and how changing a construct's logical ID forces a clean replacement
- Using Git and GitHub to version the project
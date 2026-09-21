# Runbook: WebHealth Monitor

A runbook is a checklist for what to do when something goes wrong. It lets anyone on the team respond, not just the person who built the system.

## Alarm: `<Site>AvailabilityAlarm` is IN ALARM

The monitor could not reach the site.

1. **Check the site yourself** by opening its URL in a browser.
2. **Check the Lambda logs.** Go to Lambda, open `ShubhamStack-WebMonitor`, then Monitor, then View CloudWatch logs. Look for a line like `<url> failed: <reason>`.
3. **Decide what happened:**
   - **The site is really down:** nothing to fix on our side. Wait for it to recover.
   - **The site works in the browser but the monitor fails:** the site may be blocking our requests (for example `HTTP Error 403`). Check the `User-Agent` in `lambda/monitor.py`.
   - **The Lambda itself errors:** read the logs for a Python error and fix the code.
4. **Confirm recovery.** The alarm returns to OK after the next successful runs (5 to 10 minutes).

## Alarm: `<Site>LatencyAlarm` is IN ALARM

The site responded, but slower than 3000 ms for two checks in a row.

1. Open the **WebHealth** dashboard and look at the latency graph.
2. Check whether it is a short spike or a lasting trend.
3. Open the site in a browser to see if it feels slow.
4. If it stays slow, note the time and record it as an incident.

## The dashboard shows no data

1. Check that the EventBridge rule `MonitorSchedule` is enabled.
2. Check that the Lambda ran recently (Lambda, then Monitor tab, then Invocations).
3. Look in the logs for an `AccessDenied` error, which means the Lambda is missing the CloudWatch permission.
4. Check that `lambda/websites.json` is valid JSON. A missing comma or bracket will break the function.

## Redeploying

```bash
cd Shubham
.venv\Scripts\activate
cdk deploy
```

## Adding or removing a website

1. Edit `lambda/websites.json`.
2. Run `cdk deploy`. The dashboard and alarms update automatically.
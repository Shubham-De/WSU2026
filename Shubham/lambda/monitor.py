import time
import urllib.request
import json


import boto3



#URL = "https://www.westernsydney.edu.au/"

cloudwatch = boto3.client("cloudwatch")


def check_website(url):   #Visit one website. Returns is_up, response_time_in_ms
    
    start = time.time()
    try:
        response = urllib.request.urlopen(url, timeout=10)
        is_up = response.status == 200
    except Exception:
        is_up = False   
    latency_ms = round((time.time() - start) * 1000)
    return is_up, latency_ms

"""
def handler(event, context):
    # time before we visit the site
    start = time.time()

    try:
        # vvisit the website
        response = urllib.request.urlopen(URL, timeout=10)
        status_code = response.status      
        is_up = True
    except Exception:
        # If anything goes wrong, the site counts as down
        status_code = None
        is_up = False

    # Time taken - time now minus time before and then converted to milliseconds
    latency_ms = round((time.time() - start) * 1000)


    return {
        "url": URL,
        "is_up": is_up,
        "status_code": status_code,
        "response_time_ms": latency_ms,
    }
"""

def handler(event, context):
    # open list of websites from the json  file
    with open("websites.json") as f:
        websites = json.load(f)

    results = []

    # check websites one at a time
    for site in websites:
        is_up, latency_ms = check_website(site["url"])


    
        cloudwatch.put_metric_data(
            Namespace="WebHealth",   # the name of our logbook
            MetricData=[
                {
                    "MetricName": "Availability",
                    "Dimensions": [{"Name": "Website", "Value": site["name"]}],
                    "Value": 1 if is_up else 0,   # 1 = up, 0 = down
                },
                {
                    "MetricName": "Latency",
                    "Dimensions": [{"Name": "Website", "Value": site["name"]}],
                    "Value": latency_ms,
                    "Unit": "Milliseconds",
                },
            ],
        )

        results.append({"website": site["name"], "is_up": is_up, "latency_ms": latency_ms})

    return results
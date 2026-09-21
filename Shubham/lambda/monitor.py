import time
import urllib.request



URL = "https://www.westernsydney.edu.au/"



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
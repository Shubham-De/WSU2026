
#Unit tests for lambda/monitor.py


import sys
import os
from unittest.mock import patch, MagicMock

# So this test file can import lambda / monitor.py directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lambda"))

import monitor


def test_check_website_success():
    #A 200 response should count as up.
    fake_response = MagicMock()
    fake_response.status = 200
    fake_response.__enter__.return_value = fake_response

    with patch("urllib.request.urlopen", return_value=fake_response):
        is_up, latency_ms = monitor.check_website("https://example.com")

    assert is_up is True


def test_check_website_timeout():
    #A timeout should count as down, not crash.
    with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
        is_up, latency_ms = monitor.check_website("https://example.com")

    assert is_up is False


def test_check_website_connection_error():
    #here any connection failure should count as down.
    with patch("urllib.request.urlopen", side_effect=ConnectionError("refused")):
        is_up, latency_ms = monitor.check_website("https://example.com")

    assert is_up is False


def test_check_website_non_200_status():
    #A non-200 status eg 500 should not count as up.
    fake_response = MagicMock()
    fake_response.status = 500
    fake_response.__enter__.return_value = fake_response

    with patch("urllib.request.urlopen", return_value=fake_response):
        is_up, _ = monitor.check_website("https://example.com")

    assert is_up is False


def test_check_website_returns_latency_as_number():
    #latency_ms should always be a number. never none or a string.
    fake_response = MagicMock()
    fake_response.status = 200
    fake_response.__enter__.return_value = fake_response

    with patch("urllib.request.urlopen", return_value=fake_response):
        _, latency_ms = monitor.check_website("https://example.com")

    assert isinstance(latency_ms, (int, float))
    assert latency_ms >= 0


def test_check_website_latency_on_failure_is_still_a_number():
    #Even when the site is down, we should still get a latency number back.
    with patch("urllib.request.urlopen", side_effect=TimeoutError()):
        _, latency_ms = monitor.check_website("https://example.com")

    assert isinstance(latency_ms, (int, float))


def test_check_website_sends_user_agent_header():

    #The request should identify itself, so sites don't block it (Wikipedia bug fix).
    captured = {}

    def fake_urlopen(request, timeout=10):
        captured["request"] = request
        fake_response = MagicMock()
        fake_response.status = 200
        fake_response.__enter__.return_value = fake_response
        return fake_response

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        monitor.check_website("https://example.com")

    sent_request = captured["request"]
    assert "User-agent" in sent_request.headers


def test_check_website_uses_the_given_url():
    """The function should request the exact URL it was given."""
    captured = {}

    def fake_urlopen(request, timeout=10):
        captured["request"] = request
        fake_response = MagicMock()
        fake_response.status = 200
        fake_response.__enter__.return_value = fake_response
        return fake_response

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        monitor.check_website("https://my-test-site.example/")

    assert captured["request"].full_url == "https://my-test-site.example/"


@patch("monitor.cloudwatch")
@patch("monitor.load_websites")
def test_handler_sends_metrics_for_every_site(mock_load, mock_cloudwatch):
    """handler() should send CloudWatch metrics for each website in the list."""
    mock_load.return_value = [
        {"name": "SiteA", "url": "https://a.example"},
        {"name": "SiteB", "url": "https://b.example"},
    ]
    fake_response = MagicMock()
    fake_response.status = 200
    fake_response.__enter__.return_value = fake_response

    with patch("urllib.request.urlopen", return_value=fake_response):
        monitor.handler({}, None)

    # put_metric_data is called once per website (2 sites = 2 calls),
    # each call sending 2 metrics (Availability, Latency) = 4 metric entries total
    
    assert mock_cloudwatch.put_metric_data.call_count == 2

    all_metric_data = []
    for call in mock_cloudwatch.put_metric_data.call_args_list:
        all_metric_data.extend(call.kwargs["MetricData"])

    assert len(all_metric_data) == 4

@patch("monitor.cloudwatch")
@patch("monitor.load_websites")
def test_handler_returns_a_result_per_site(mock_load, mock_cloudwatch):
    #handler() should return one result dict per website checked.
    mock_load.return_value = [{"name": "SiteA", "url": "https://a.example"}]
    fake_response = MagicMock()
    fake_response.status = 200
    fake_response.__enter__.return_value = fake_response

    with patch("urllib.request.urlopen", return_value=fake_response):
        results = monitor.handler({}, None)

    assert len(results) == 1
    assert results[0]["website"] == "SiteA"
    assert results[0]["is_up"] is True

#Unit tests for lambda/alarm_logger.py

import sys
import os
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lambda"))

# alarm_logger.py reads TABLE_NAME from the env at import tiem

os.environ["TABLE_NAME"] = "FakeTableForTests"

import alarm_logger


def _fake_sns_event(alarm_name="TestAlarm", new_state="ALARM", old_state="OK", reason="Threshold crossed"):

    #Builds a fake SNS event shaped like the real one CloudWatch sends.
    message = {
        "AlarmName": alarm_name,
        "NewStateValue": new_state,
        "OldStateValue": old_state,
        "NewStateReason": reason,
        "StateChangeTime": "2026-01-01T00:00:00.000+0000",
    }
    return {"Records": [{"Sns": {"Message": json.dumps(message)}}]}


@patch("alarm_logger.table")
def test_handler_writes_one_item_per_record(mock_table):
    event = _fake_sns_event()
    alarm_logger.handler(event, None)

    assert mock_table.put_item.call_count == 1


@patch("alarm_logger.table")
def test_handler_saves_the_correct_alarm_name(mock_table):
    event = _fake_sns_event(alarm_name="WesternSydneyAvailabilityAlarm")
    alarm_logger.handler(event, None)

    saved_item = mock_table.put_item.call_args.kwargs["Item"]
    assert saved_item["alarm_name"] == "WesternSydneyAvailabilityAlarm"
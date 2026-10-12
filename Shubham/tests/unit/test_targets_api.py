
#Unit tests for lambda/targets_api.py

import sys
import os
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lambda"))

os.environ["TARGETS_TABLE_NAME"] = "FakeTargetsTableForTests"

import targets_api


@patch("targets_api.table")
def test_create_target_saves_name_and_url(mock_table):
    event = {"body": json.dumps({"name": "TestSite", "url": "https://test.example"})}

    response = targets_api.create_target(event, None)

    assert response["statusCode"] == 201
    mock_table.put_item.assert_called_once_with(
        Item={"name": "TestSite", "url": "https://test.example"}
    )


@patch("targets_api.table")
def test_create_target_rejects_missing_fields(mock_table):
    event = {"body": json.dumps({"name": "TestSite"})}  # no url

    response = targets_api.create_target(event, None)

    assert response["statusCode"] == 400
    mock_table.put_item.assert_not_called()
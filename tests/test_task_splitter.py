"""Tests for the task splitter."""

from __future__ import annotations

import pytest

from openharness.coordinator.task_splitter import TaskSplitter, SubTask


class TestParseResponse:
    """Test the JSON parsing logic of TaskSplitter."""

    def _make_splitter(self):
        """Create a TaskSplitter with a mock client (not used for parsing tests)."""
        return TaskSplitter(api_client=None, model="test")  # type: ignore[arg-type]

    def test_valid_json(self):
        splitter = self._make_splitter()
        response = '{"subtasks": [{"description": "task A", "complexity": "simple"}]}'
        result = splitter._parse_split_response(response)
        assert len(result) == 1
        assert result[0].description == "task A"
        assert result[0].estimated_complexity == "simple"

    def test_empty_subtasks(self):
        splitter = self._make_splitter()
        response = '{"subtasks": []}'
        result = splitter._parse_split_response(response)
        assert result == []

    def test_invalid_json(self):
        splitter = self._make_splitter()
        result = splitter._parse_split_response("not json at all")
        assert result == []

    def test_json_in_code_block(self):
        splitter = self._make_splitter()
        response = '```json\n{"subtasks": [{"description": "task B"}]}\n```'
        result = splitter._parse_split_response(response)
        assert len(result) == 1
        assert result[0].description == "task B"

    def test_max_five_subtasks(self):
        splitter = self._make_splitter()
        items = [{"description": f"task {i}"} for i in range(10)]
        response = f'{{"subtasks": {items}}}'.replace("'", '"')
        result = splitter._parse_split_response(response)
        assert len(result) <= 5

    def test_missing_description_skipped(self):
        splitter = self._make_splitter()
        response = '{"subtasks": [{"complexity": "simple"}, {"description": "valid"}]}'
        result = splitter._parse_split_response(response)
        assert len(result) == 1
        assert result[0].description == "valid"


class TestSubTask:
    def test_to_dict(self):
        st = SubTask(task_id="t1", description="do X", estimated_complexity="simple")
        data = st.to_dict()
        assert data["task_id"] == "t1"
        assert data["description"] == "do X"

import pytest
from datetime import datetime, timezone
from unittest.mock import patch
from gt_transform import transform


class TestTransform:

    def test_returns_empty_list_when_no_data(self):
        result = transform([])

        assert result == []

    def test_returns_empty_list_when_none(self):
        result = transform(None)

        assert result == []

    def test_lowercases_keyword_value(self):
        raw_data = [{'keyword_value': 'MATCHA', 'search_volume': 75}]

        result = transform(raw_data)

        assert result[0]['keyword_value'] == 'matcha'

    def test_strips_whitespace_from_keyword(self):
        raw_data = [{'keyword_value': '  coffee  ', 'search_volume': 90}]

        result = transform(raw_data)

        assert result[0]['keyword_value'] == 'coffee'

    def test_preserves_search_volume(self):
        raw_data = [{'keyword_value': 'matcha', 'search_volume': 75}]

        result = transform(raw_data)

        assert result[0]['search_volume'] == 75

    def test_adds_trend_date(self):
        raw_data = [{'keyword_value': 'matcha', 'search_volume': 75}]

        result = transform(raw_data)

        assert 'trend_date' in result[0]
        assert isinstance(result[0]['trend_date'], datetime)

    def test_trend_date_is_utc(self):
        raw_data = [{'keyword_value': 'matcha', 'search_volume': 75}]

        result = transform(raw_data)

        assert result[0]['trend_date'].tzinfo == timezone.utc

    def test_transforms_multiple_records(self):
        raw_data = [
            {'keyword_value': 'Matcha', 'search_volume': 75},
            {'keyword_value': 'Coffee', 'search_volume': 90},
            {'keyword_value': 'Tea', 'search_volume': 60}
        ]

        result = transform(raw_data)

        assert len(result) == 3
        assert result[0]['keyword_value'] == 'matcha'
        assert result[1]['keyword_value'] == 'coffee'
        assert result[2]['keyword_value'] == 'tea'

    def test_all_records_have_same_timestamp(self):
        raw_data = [
            {'keyword_value': 'matcha', 'search_volume': 75},
            {'keyword_value': 'coffee', 'search_volume': 90}
        ]

        result = transform(raw_data)

        assert result[0]['trend_date'] == result[1]['trend_date']

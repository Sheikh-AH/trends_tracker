# pylint: skip-file
import pytest
from unittest.mock import patch, MagicMock
from alert_send import get_users_for_keyword, already_alerted_today, mark_as_alerted, send_email, send_alerts, alerts_sent_today


class TestGetUsersForKeyword:

    @patch('alert_send.get_db_connection')
    def test_returns_users(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (1, 'user1@test.com'), (2, 'user2@test.com')]
        mock_conn.return_value.cursor.return_value = mock_cursor

        result = get_users_for_keyword('matcha')

        assert len(result) == 2
        assert result[0] == {'user_id': 1, 'email': 'user1@test.com'}
        assert result[1] == {'user_id': 2, 'email': 'user2@test.com'}

    @patch('alert_send.get_db_connection')
    def test_returns_empty_list_when_no_users(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.return_value.cursor.return_value = mock_cursor

        result = get_users_for_keyword('matcha')

        assert result == []

    @patch('alert_send.get_db_connection')
    def test_closes_connection(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.return_value.cursor.return_value = mock_cursor

        get_users_for_keyword('matcha')

        mock_cursor.close.assert_called_once()
        mock_conn.return_value.close.assert_called_once()


class TestAlreadyAlertedToday:

    def test_returns_false_when_not_alerted(self):
        alerts_sent_today.clear()

        result = already_alerted_today(1, 'matcha')

        assert result is False

    def test_returns_true_when_already_alerted(self):
        alerts_sent_today.clear()
        alerts_sent_today['1:matcha'] = True

        result = already_alerted_today(1, 'matcha')

        assert result is True


class TestMarkAsAlerted:

    def test_marks_user_keyword_as_alerted(self):
        alerts_sent_today.clear()

        mark_as_alerted(1, 'matcha')

        assert alerts_sent_today.get('1:matcha') is True

    def test_different_users_tracked_separately(self):
        alerts_sent_today.clear()

        mark_as_alerted(1, 'matcha')
        mark_as_alerted(2, 'matcha')

        assert alerts_sent_today.get('1:matcha') is True
        assert alerts_sent_today.get('2:matcha') is True

    def test_different_keywords_tracked_separately(self):
        alerts_sent_today.clear()

        mark_as_alerted(1, 'matcha')
        mark_as_alerted(1, 'coffee')

        assert alerts_sent_today.get('1:matcha') is True
        assert alerts_sent_today.get('1:coffee') is True


class TestSendEmail:

    @patch('alert_send.boto3.client')
    def test_sends_email_successfully(self, mock_boto):
        mock_ses = MagicMock()
        mock_boto.return_value = mock_ses

        with patch.dict('os.environ', {'AWS_REGION': 'eu-west-2', 'SENDER_EMAIL': 'noreply@test.com'}):
            result = send_email('user@test.com', 'matcha', 15)

        assert result is True
        mock_ses.send_email.assert_called_once()

    @patch('alert_send.boto3.client')
    def test_returns_false_on_failure(self, mock_boto):
        mock_ses = MagicMock()
        mock_ses.send_email.side_effect = Exception("SES Error")
        mock_boto.return_value = mock_ses

        with patch.dict('os.environ', {'AWS_REGION': 'eu-west-2', 'SENDER_EMAIL': 'noreply@test.com'}):
            result = send_email('user@test.com', 'matcha', 15)

        assert result is False

    @patch('alert_send.boto3.client')
    def test_email_contains_keyword(self, mock_boto):
        mock_ses = MagicMock()
        mock_boto.return_value = mock_ses

        with patch.dict('os.environ', {'AWS_REGION': 'eu-west-2', 'SENDER_EMAIL': 'noreply@test.com'}):
            send_email('user@test.com', 'matcha', 15)

        call_args = mock_ses.send_email.call_args
        body = call_args[1]['Message']['Body']['Text']['Data']
        subject = call_args[1]['Message']['Subject']['Data']

        assert 'matcha' in body
        assert 'matcha' in subject


class TestSendAlerts:

    def test_does_nothing_when_no_spikes(self):
        alerts_sent_today.clear()

        send_alerts([])

        assert len(alerts_sent_today) == 0

    @patch('alert_send.send_email')
    @patch('alert_send.get_users_for_keyword')
    def test_sends_alerts_to_users(self, mock_get_users, mock_send):
        alerts_sent_today.clear()
        mock_get_users.return_value = [
            {'user_id': 1, 'email': 'user@test.com'}]
        mock_send.return_value = True

        spikes = [{'keyword': 'matcha', 'current_count': 15, 'average_count': 5}]
        send_alerts(spikes)

        mock_send.assert_called_once_with('user@test.com', 'matcha', 15)

    @patch('alert_send.send_email')
    @patch('alert_send.get_users_for_keyword')
    def test_skips_already_alerted_users(self, mock_get_users, mock_send):
        alerts_sent_today.clear()
        alerts_sent_today['1:matcha'] = True
        mock_get_users.return_value = [
            {'user_id': 1, 'email': 'user@test.com'}]

        spikes = [{'keyword': 'matcha', 'current_count': 15, 'average_count': 5}]
        send_alerts(spikes)

        mock_send.assert_not_called()

    @patch('alert_send.send_email')
    @patch('alert_send.get_users_for_keyword')
    def test_marks_user_as_alerted_after_send(self, mock_get_users, mock_send):
        alerts_sent_today.clear()
        mock_get_users.return_value = [
            {'user_id': 1, 'email': 'user@test.com'}]
        mock_send.return_value = True

        spikes = [{'keyword': 'matcha', 'current_count': 15, 'average_count': 5}]
        send_alerts(spikes)

        assert alerts_sent_today.get('1:matcha') is True

    @patch('alert_send.send_email')
    @patch('alert_send.get_users_for_keyword')
    def test_does_not_mark_as_alerted_if_send_fails(self, mock_get_users, mock_send):
        alerts_sent_today.clear()
        mock_get_users.return_value = [
            {'user_id': 1, 'email': 'user@test.com'}]
        mock_send.return_value = False

        spikes = [{'keyword': 'matcha', 'current_count': 15, 'average_count': 5}]
        send_alerts(spikes)

        assert alerts_sent_today.get('1:matcha') is None

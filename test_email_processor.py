import unittest
from unittest.mock import Mock, patch
from email_processor import get_emails_by_label

class TestEmailProcessor(unittest.TestCase):

    @patch('email_processor.build')
    def test_get_emails_by_label(self, mock_build):
        # Mock the Gmail service and messages
        mock_service = Mock()
        mock_messages = Mock()
        mock_messages.list.return_value.execute.return_value = {'messages': [{'id': '123'}]}
        mock_service.users.return_value.messages = mock_messages
        mock_build.return_value = mock_service

        # Call the function with a test label
        get_emails_by_label(mock_service, "Test Label")

        # Assert that the correct query was used
        mock_messages.list.assert_called_with(userId='me', q='label:"Test Label" is:unread')

if __name__ == '__main__':
    unittest.main()

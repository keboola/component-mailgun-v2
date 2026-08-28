import os
import sys
import unittest
from unittest import mock

from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import JSONDecodeError, ReadTimeout, RetryError

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from keboola.component.exceptions import UserException  # noqa: E402
from mailgun.client import AuthenticationError, MailgunClient  # noqa: E402

DUMMY_TOKEN = 'dummy-token'
DUMMY_DOMAIN = 'example.com'


def _response(status_code, json_value=None, json_exc=None, text=''):
    """Build a stand-in for a requests.Response returned by HttpClient.get_raw."""
    response = mock.Mock()
    response.status_code = status_code
    response.text = text
    if json_exc is not None:
        response.json.side_effect = json_exc
    else:
        response.json.return_value = json_value
    return response


def _build_client(get_raw_mock, param_from_name=None, param_from_email='postmaster'):
    with mock.patch.object(MailgunClient, 'get_raw', get_raw_mock):
        return MailgunClient(param_token=DUMMY_TOKEN, param_domain=DUMMY_DOMAIN,
                             param_from_name=param_from_name, param_region='EU',
                             param_from_email=param_from_email)


class TestValidateAuthenticationTransientFailures(unittest.TestCase):
    """Regression tests for the defensive handling added to _validate_authentication.

    The underlying HttpClient already retries the credential-check request with an
    exponential backoff. When that retry window is exhausted, requests raises a
    RequestException, which previously escaped the component uncaught and made the job
    end with an opaque internal error (exit code 2). It must now fail as a UserException
    (exit code 1) carrying an actionable message.
    """

    def test_retry_error_is_raised_as_user_exception(self):
        get_raw = mock.Mock(side_effect=RetryError('too many 500 error responses'))

        with self.assertRaises(UserException) as ctx:
            _build_client(get_raw)

        self.assertIn('Could not reach the Mailgun API', str(ctx.exception))
        self.assertIn('try running the configuration again later', str(ctx.exception))
        self.assertEqual(1, get_raw.call_count)

    def test_connection_error_is_raised_as_user_exception(self):
        get_raw = mock.Mock(side_effect=RequestsConnectionError('connection reset by peer'))

        with self.assertRaises(UserException):
            _build_client(get_raw)

    def test_read_timeout_is_raised_as_user_exception(self):
        get_raw = mock.Mock(side_effect=ReadTimeout('read timed out'))

        with self.assertRaises(UserException):
            _build_client(get_raw)

    def test_original_error_is_chained_not_hidden(self):
        """The job must still fail, and the original error stays available for debugging."""
        original = RetryError('too many 500 error responses')
        get_raw = mock.Mock(side_effect=original)

        with self.assertRaises(UserException) as ctx:
            _build_client(get_raw)

        self.assertIs(original, ctx.exception.__cause__)


class TestValidateAuthenticationUnchangedBehaviour(unittest.TestCase):
    """Pins the pre-existing behaviour that the defensive change must not alter."""

    def test_successful_authentication_builds_client(self):
        get_raw = mock.Mock(return_value=_response(200, json_value={'items': []}))

        client = _build_client(get_raw)

        self.assertEqual(f'postmaster@{DUMMY_DOMAIN}', client.param_from_id)
        self.assertEqual(1, get_raw.call_count)

    def test_successful_authentication_with_from_name(self):
        get_raw = mock.Mock(return_value=_response(200, json_value={'items': []}))

        client = _build_client(get_raw, param_from_name='Sender')

        self.assertEqual(f'Sender <postmaster@{DUMMY_DOMAIN}>', client.param_from_id)

    def test_rejected_credentials_still_raise_user_exception(self):
        get_raw = mock.Mock(return_value=_response(401, json_value={'message': 'Forbidden'}))

        with self.assertRaises(UserException) as ctx:
            _build_client(get_raw)

        self.assertIn('Authentication was not successful', str(ctx.exception))

    def test_non_json_response_still_raises_authentication_error(self):
        get_raw = mock.Mock(return_value=_response(
            200, json_exc=JSONDecodeError('Expecting value', '<html>error</html>', 0),
            text='<html>error</html>'))

        with self.assertRaises(AuthenticationError):
            _build_client(get_raw)


if __name__ == '__main__':
    unittest.main()

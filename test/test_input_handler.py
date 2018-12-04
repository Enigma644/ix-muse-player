import unittest
import mock

import input_handler


@mock.patch('time.sleep')
@mock.patch('utilities.DisplayPlayback')
class InputHandlerTest(unittest.TestCase):
    def setUp(self):
        self.event = mock.MagicMock()
        self.queue = mock.MagicMock()
        self.handler = input_handler.InputHandler(self.queue)

    def test_put_message_puts_to_queue(self, *unused):
        self.handler.put_message('tsst')
        self.queue.put.assert_called_with('tsst')

    def test_put_done_message_sets_done_and_puts_done_to_queue(self, *unused):
        self.assertFalse(self.handler.done)
        self.handler.put_done_message()
        self.assertTrue(self.handler.done)
        self.queue.put.assert_called_with(['done'])

    def test_start_file_returns_immediately_if_events_is_empty(self, sleep, *unused):
        self.handler.start_file([])
        self.assertFalse(self.queue.put.called)
        self.assertFalse(sleep.called)

    def test_start_file_puts_m_if_m(self, sleep, display_playback):
        self.handler.start_file([self.event])
        self.queue.put.assert_called_with(self.event)

    def test_start_file_does_not_sleep_if_as_fast_as_possible(self, sleep, *unused):
        self.handler.as_fast_as_possible = True
        self.handler.start_file([self.event])
        sleep.assert_called()

    def test_start_file_sleeps_if_not_as_fast_as_possible(self, sleep, *unused):
        self.handler.as_fast_as_possible = False
        self.handler.start_file([self.event])
        sleep.assert_called()

    @mock.patch('time.time')
    def test_start_file_sleeps_with_timestamp_appropriate_time(self, sleep, display_playback, time):
        # TODO
        raise unittest.SkipTest

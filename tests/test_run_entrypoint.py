import socket
import unittest

from run_spec2code import pick_listen_port


class PickListenPortTests(unittest.TestCase):
    def test_returns_preferred_port_when_free(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            free_port = probe.getsockname()[1]
        self.assertEqual(pick_listen_port("127.0.0.1", free_port), free_port)

    def test_skips_to_next_port_when_preferred_is_busy(self) -> None:
        # Hold a port open the way a stale Spec2Code instance would.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy:
            busy.bind(("127.0.0.1", 0))
            busy.listen(1)
            busy_port = busy.getsockname()[1]

            chosen = pick_listen_port("127.0.0.1", busy_port)

            self.assertNotEqual(chosen, busy_port)
            self.assertGreater(chosen, busy_port)
            self.assertLessEqual(chosen, busy_port + 30)

    def test_gives_up_and_returns_preferred_after_attempts(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy:
            busy.bind(("127.0.0.1", 0))
            busy.listen(1)
            busy_port = busy.getsockname()[1]

            self.assertEqual(pick_listen_port("127.0.0.1", busy_port, attempts=1), busy_port)


if __name__ == "__main__":
    unittest.main()

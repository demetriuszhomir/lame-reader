import unittest

from app import parse_speak_request, synthesize


class TextReaderTests(unittest.TestCase):
    def test_request_validation(self) -> None:
        self.assertEqual(
            parse_speak_request(b'{"text":" Hello. ","speed":1.2}'),
            ("Hello.", 1.2),
        )
        self.assertEqual(parse_speak_request(b'{"text":"Slow","speed":0.2}'), ("Slow", 0.2))
        self.assertEqual(parse_speak_request(b'{"text":"Fast","speed":2}'), ("Fast", 2.0))
        for body in (
            b'{"text":""}',
            b'{"text":"Hello","speed":0.19}',
            b'{"text":"Hello","speed":2.01}',
        ):
            with self.assertRaises(ValueError):
                parse_speak_request(body)

    def test_synthesis_returns_wav(self) -> None:
        audio = synthesize("Hello from Lame Reader.", 1.0)
        self.assertEqual(audio[:4], b"RIFF")
        self.assertGreater(len(audio), 1_000)


if __name__ == "__main__":
    unittest.main()

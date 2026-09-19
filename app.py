from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
import threading
import wave
import webbrowser
from functools import lru_cache
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from piper import PiperVoice, SynthesisConfig


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
VOICE_NAME = "en_US-kusal-medium"
VOICE_DIR = ROOT / "voice"
VOICE_PATH = VOICE_DIR / f"{VOICE_NAME}.onnx"
VOICE_CONFIG_PATH = VOICE_DIR / f"{VOICE_NAME}.onnx.json"
MAX_REQUEST_BYTES = 16_384
MAX_PHRASE_LENGTH = 1_000
_voice: PiperVoice | None = None
_voice_lock = threading.Lock()


def get_voice() -> PiperVoice:
    global _voice
    if _voice is None:
        if not VOICE_PATH.exists() or not VOICE_CONFIG_PATH.exists():
            print(f"Downloading Piper voice: {VOICE_NAME}")
            VOICE_DIR.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "piper.download_voices",
                    "--data-dir",
                    str(VOICE_DIR),
                    VOICE_NAME,
                ],
                check=True,
            )
        if not VOICE_PATH.exists() or not VOICE_CONFIG_PATH.exists():
            raise FileNotFoundError(f"Voice download failed: {VOICE_PATH}")
        _voice = PiperVoice.load(VOICE_PATH)
    return _voice


@lru_cache(maxsize=32)
def synthesize(text: str, speed: float) -> bytes:
    output = io.BytesIO()
    config = SynthesisConfig(
        length_scale=0.8 / speed,
        noise_scale=0.667,
        noise_w_scale=0.8,
        normalize_audio=True,
        volume=1.0,
    )
    with _voice_lock, wave.open(output, "wb") as wav_file:
        get_voice().synthesize_wav(text, wav_file, syn_config=config)
    return output.getvalue()


def parse_speak_request(body: bytes) -> tuple[str, float]:
    try:
        payload = json.loads(body)
        text = payload["text"].strip()
        speed = float(payload.get("speed", 1.0))
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise ValueError("Expected JSON with text and optional speed") from error

    if not text:
        raise ValueError("Text is empty")
    if len(text) > MAX_PHRASE_LENGTH:
        raise ValueError(f"Phrase is longer than {MAX_PHRASE_LENGTH} characters")
    if not 0.2 <= speed <= 2.0:
        raise ValueError("Speed must be between 0.2 and 2.0")
    return text, round(speed, 2)


class ReaderHandler(BaseHTTPRequestHandler):
    server_version = "LameReader/1.0"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            self.send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return
        if path == "/health":
            self.send_json({"status": "ok", "voice": VOICE_PATH.stem})
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/speak":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_REQUEST_BYTES:
                raise ValueError("Invalid request size")
            text, speed = parse_speak_request(self.rfile.read(length))
            audio = synthesize(text, speed)
        except ValueError as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        except Exception as error:
            print(f"Synthesis failed: {error}")
            self.send_json({"error": "Speech synthesis failed"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(audio)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(audio)

    def send_file(self, path: Path, content_type: str) -> None:
        content = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, payload: dict[str, str], status: HTTPStatus = HTTPStatus.OK) -> None:
        content = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Lame Reader with local Piper TTS")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), ReaderHandler)
    local_url = f"http://127.0.0.1:{args.port}"
    print(f"Lame Reader: {local_url}")
    print("Press Ctrl+C to stop")
    if not args.no_open:
        threading.Timer(0.6, webbrowser.open, args=(local_url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

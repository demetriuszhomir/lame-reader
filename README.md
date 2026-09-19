# Lame Reader

A local, mobile-first text reader powered by Piper TTS.

## Run on Windows

```powershell
.\start.ps1
```

Open `http://127.0.0.1:8765`. The first run installs Piper; the first playback downloads the voice automatically.

For access from another device on your local network:

```powershell
.\start.ps1 -BindAddress 0.0.0.0
```

Text and preferences stay in the browser. Voice models and the Python environment stay local and are excluded from Git.

The server has no authentication. Keep it on trusted networks or behind an authenticated tunnel.

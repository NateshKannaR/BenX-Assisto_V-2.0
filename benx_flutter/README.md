# BenX Android companion

Pair with your desktop to check its battery, list saved Hyprland layouts, and restore a named layout. Restore waits for approval on the phone.

## Build and install

Use Flutter 3.24.5, Java 17, and the Android SDK.

```bash
cd benx_flutter
flutter pub get
flutter analyze
flutter build apk --release
```

The APK is written to `build/app/outputs/flutter-apk/app-release.apk`. The GitHub Actions build also uploads it as `benx-companion-apk`. The included Gradle configuration uses a debug signing key for sideloading. Configure your own release signing before distributing it.

## Pair with the desktop

On your desktop, activate the BenX Python environment and generate a pairing token in a private terminal.

```bash
source benx_venv/bin/activate
export BENX_PAIRING_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
printf '%s\n' "$BENX_PAIRING_TOKEN"
python -m uvicorn jarvis_ai.companion:app --host 127.0.0.1 --port 8001
```

Expose only the companion port through an HTTPS reverse proxy reachable by your phone. Forward WebSocket upgrades at `/ws` to `127.0.0.1:8001` and use a TLS certificate trusted by Android. The desktop web UI stays on its separate loopback port.

Open BenX on your phone, enter `wss://<your-desktop-hostname>/ws`, and paste the token. The app clears the token field after pairing. Generate a new token and restart the companion server to revoke the old token and end existing sessions.

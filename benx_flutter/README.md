# BenX Mobile — Flutter App

Remote control your BenX AI assistant from your phone.

## Features
- 💬 Real-time chat via WebSocket
- 📊 Live system metrics (CPU, RAM, Battery)
- ⚡ Quick command chips
- 🤖 Agent mode toggle
- 📋 Copy responses to clipboard
- 🌙 Dark cyberpunk UI matching desktop

## Setup

### 1. Install Flutter
```bash
# Arch
yay -S flutter

# Ubuntu
sudo snap install flutter --classic
```

### 2. Install dependencies
```bash
cd benx_flutter
flutter pub get
```

### 3. Run on device/emulator
```bash
flutter run
```

### 4. Build APK
```bash
flutter build apk --release
# APK at: build/app/outputs/flutter-apk/app-release.apk
```

## Connect to BenX Server

1. Make sure BenX web server is running:
   ```bash
   bash run_web.sh
   ```
2. Open the app → enter your server IP:
   ```
   ws://YOUR_PC_IP:8000/ws
   ```
   Find your IP: `ip addr | grep 192.168`

3. Both phone and PC must be on the **same WiFi network**

## For Vercel deployment
Use your Vercel URL:
```
wss://your-app.vercel.app/ws
```
> Note: Vercel has limited WS support — use Railway for full WebSocket

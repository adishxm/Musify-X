# Contributing to Musify-X 🌐

Thank you for your interest in contributing to **Musify-X**! We welcome bug reports, feature suggestions, documentation enhancements, and pull requests.

---

## 🧭 Code of Conduct

Musify-X is an inclusive, privacy-first community. We expect all contributors and participants to treat everyone with kindness, constructive communication, and mutual respect.

---

## 📌 Project Overview

**Musify-X** is an independent, Chromium/Brave-powered privacy browser for Android featuring:
- **Dynamic Day/Night Adaptive Icons**: Adaptive vectors switching seamlessly between light and dark system modes.
- **Custom Liquid 'M' Design System**: Bespoke brand identity across launcher, URL bar shields, splash screen, and in-app dialogs.
- **Built-in Privacy Shields**: Engine-level ad and tracker blocking, anti-fingerprinting, and script control.
- **Zero Telemetry**: No behavioral analytics, no telemetry beacons, and zero tracking pings.

> [!IMPORTANT]
> **Musify-X** is an independent browser and is **NOT** the same as the legacy Musify project. All contributions should focus on the Musify-X browser architecture and its build tooling.

---

## 🛠️ Development & Build Setup

### Prerequisites
- **Operating System**: Windows 10/11, macOS, or Linux.
- **Python**: 3.10 or newer (with `opencv-python`, `numpy`, and `Pillow`).
- **Android SDK**: Build-Tools (34.0.0+) and Android Platform SDK (`android-36` or compatible).
- **Android Debug Keystore**: Automatically located at `~/.android/debug.keystore`.

### Quick Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/adishxm/Musify-X.git
   cd Musify-X
   ```

2. **Install Python dependencies:**
   ```bash
   pip install pillow opencv-python numpy
   ```

3. **Build Musify-X APK:**
   ```bash
   python build.py
   ```

4. **Test on Android Emulator:**
   - Double click `test-on-emulator.bat` or run:
   ```cmd
   test-on-emulator.bat
   ```

---

## 🐛 Submitting Issues

When submitting bug reports or site compatibility issues:
1. **Device & OS**: Android version, device model / emulator AVD.
2. **App Version**: Musify-X build date / commit SHA.
3. **Steps to Reproduce**: Detailed reproduction steps with URLs.
4. **Observed vs Expected**: Clear description with screenshots if applicable.

---

## 🚀 Pull Request Guidelines

1. Create a feature branch: `git checkout -b feature/your-feature-name`.
2. Ensure `python build.py` completes with zero errors and generates a signed APK.
3. Verify on the Android emulator with `test-on-emulator.bat`.
4. Submit your pull request with a detailed description of changes.

---

*Engineered with ❤️ by [adishxm](https://github.com/adishxm)*

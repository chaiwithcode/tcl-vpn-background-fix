# Prompt for Codex or Claude Code without installation

Download this project and open Codex or Claude Code in its root folder. Copy the prompt below. It loads the same shared skill directly from the local files, without installing it into your personal skills directory.

```text
Read skills/tcl-vpn-fix/SKILL.md and follow that skill to diagnose my TCL TV VPN disconnecting in the background. Resolve its guide and helper relative to that skill folder.

TV model: <MODEL>
Android / firmware version, if known: <VERSION>
TV ADB address: <LOCAL_IP:PORT>
VPN app: <VPN_APP_NAME>
VPN package name, if known: <VPN_PACKAGE_OR_DISCOVER_IT>

You may inspect my selected TV and prepare a targeted fix. Show me the exact backed-up configuration change before applying it, and ask before rebooting or making broader changes. Preserve unrelated settings and report what you actually verified.
```

The files must be available locally, and your tool needs terminal access to ADB on the same network as the TV. Do not paste account credentials or pairing secrets into public issues. For normal installation and direct skill invocation, see [README.md](README.md).

# TCL VPN Background Fix

A shared skill for **Codex and Claude Code** to diagnose VPN apps killed by TCL Safety Guard and prepare targeted saved exclusions.

Tested with Surfshark on a **TCL 55C7K-UK running Android 12**: both exclusions survived a full reboot, and the VPN reconnected automatically. Other VPN apps and firmware are not yet verified. Firmware or remote configuration updates may overwrite the settings.

## What it does

- Guides you through Developer options, USB debugging, and ADB authorization.
- Identifies your chosen VPN app and checks for `tguard-kill` in its exit history.
- Preserves the TV's settings and prepares exclusions for just that package.
- Checks the saved and running configuration, then verifies after an authorized reboot.
- Keeps backups locally and prepares a guarded rollback.

The single Python helper only prepares local files, compares configurations, and prints commands. It never connects to or modifies the TV itself. Codex or Claude Code runs the reviewed ADB commands within your authorization.

## Requirements

- Codex or Claude Code **running locally with terminal access**.
- ADB from Google's [SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools).
- Python 3.9 or newer. No Python packages or API keys are required.
- TV and computer on the same network, with debugging enabled and the computer authorized.

The examples use a macOS/Linux shell. A cloud-only chat or remote agent environment generally cannot reach your TV's private network without an appropriate local connection.

## Install the skill

Download this project and open a terminal in its root folder. Install the **same skill folder** into the discovery location for your chosen tool. These examples refuse to overwrite an existing installation.

### Codex

```sh
mkdir -p "$HOME/.agents/skills"
if test ! -e "$HOME/.agents/skills/tcl-vpn-fix"; then
  cp -R skills/tcl-vpn-fix "$HOME/.agents/skills/"
else
  echo "Skill already exists; review it before replacing."
fi
```

Invoke it in Codex:

```text
Use $tcl-vpn-fix to diagnose my TCL TV VPN disconnecting in the background.
My TV model is <MODEL>, its ADB address is <LOCAL_IP:PORT>, and my VPN app is <APP>.
```

### Claude Code

```sh
mkdir -p "$HOME/.claude/skills"
if test ! -e "$HOME/.claude/skills/tcl-vpn-fix"; then
  cp -R skills/tcl-vpn-fix "$HOME/.claude/skills/"
else
  echo "Skill already exists; review it before replacing."
fi
```

Invoke it in Claude Code:

```text
/tcl-vpn-fix
Diagnose my TCL TV VPN disconnecting in the background.
My TV model is <MODEL>, its ADB address is <LOCAL_IP:PORT>, and my VPN app is <APP>.
```

If the skill does not appear, start a new session and check the installation path. Both copies contain the same instructions, reference, and helper; they require no product-specific hooks or MCP server. These install locations and invocation forms follow the [Codex skills documentation](https://learn.chatgpt.com/docs/build-skills) and [Claude Code skills documentation](https://code.claude.com/docs/en/skills).

A skill's instructions do not grant terminal or device permissions. Accept the TV's ADB authorization prompt yourself, and approve any host permission prompts required by your environment.

## Guide and fallback prompt

- [Developer mode, USB debugging, and manual ADB guide](skills/tcl-vpn-fix/references/guide.md)
- [Skill instructions](skills/tcl-vpn-fix/SKILL.md)
- [Short prompt without installation](AGENT-PROMPT.md)

For the manual route, use the same helper with `python3 skills/tcl-vpn-fix/scripts/vpn_config.py --help`. The guide explains preparation, verification, and rollback; there are no embedded Python programs to copy.

## Scope and known limits

This method applies when the VPN app's exit history shows **`tguard-kill`** and the matching TCL configuration provider is accessible. It does not fix every VPN disconnect or Wi-Fi problem.

The saved-exclusion method keeps Safety Guard enabled. On the tested TV, disabling its cleaner component was denied, and disabling the entire app was undone during boot. Live-only exclusions also disappeared after reboot; saved exclusions were required.

Long-term streaming stability is not yet verified. A connected VPN does not prove all apps use it when split tunneling is enabled.

## Development and compatibility reports

Run the offline helper tests:

```sh
python3 -m unittest discover -s tests -v
```

The tests require no TV or ADB connection. Installing and exercising the skill inside each product is a separate check from validating its portable files.

When reporting compatibility, include your TV model, Android/firmware version, VPN app/package, whether `tguard-kill` was present, and whether saved/live exclusions survived reboot. Redact IP/MAC addresses, Wi-Fi names, pairing codes, account details, and raw logs. Keep generated configurations and command files in `vpn-fix-local/`, which is ignored by Git.

## License

[MIT](LICENSE). Independent community project; not an official TCL or VPN-provider fix.

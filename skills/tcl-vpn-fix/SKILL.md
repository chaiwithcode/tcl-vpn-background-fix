---
name: tcl-vpn-fix
description: Diagnose VPN apps killed in the background by TCL Safety Guard over ADB, and prepare targeted saved cleaner exclusions with backups, rollback, and reboot verification. Use for TCL Google TV or Android TV VPN background disconnects.
---

# TCL VPN background fix

Use local terminal access, ADB, and Python 3. This skill works without Codex- or Claude-specific tools, substitutions, hooks, or plugins. Resolve `scripts/` and `references/` relative to this skill directory, not the user's working directory.

Read [references/guide.md](references/guide.md) for TV-side debugging setup, exact commands, helper usage, tested evidence, and firmware limitations. Read it before changing cleaner settings.

## Diagnose and choose the scope

- Discover the selected TV and authorize ADB. Use `adb -s <serial>` for every device command; `adb connect`/`disconnect` take the selected address. If debugging is unavailable, explain the TV-side action from the guide. Do not scan unrelated devices.
- Identify the user's chosen VPN app and verify its installed package. Never default to Surfshark. Inspect its exit history, version, battery exemption, TCL auto-start operations, and VPN service/network state.
- Classify the actual process-exit reason before choosing a fix. Repeated exits with `description=tguard-kill` support the TCL cleaner diagnosis. If `tguard-kill` is absent or has already been resolved, inspect other exit reasons rather than repeating whitelist changes. In particular, `reason=6 (ANR)` with Android diagnostics reporting `Context.startForegroundService() did not then call Service.startForeground()` indicates a foreground-service startup timeout. This was observed with Surfshark's `WireguardVpnService` on Android 12. App-update exits, network interruptions, and other crashes require separate investigation.
- The saved method requires `content://com.tcl.providers.config/TGuardMemoryManager` and unique `KillWhiteList` / `OneKeyCleanWhiteList` entries with string-array values. Stop this approach if the schema is missing, differs, or access is denied. Do not root, remove packages, or work around access controls.

## Prepare, apply, and verify

1. Save a fresh selected-TV query locally. Use `scripts/vpn_config.py prepare` to validate the data, create a new backup directory, and generate the quoted apply command. The helper performs local file operations only; it never invokes ADB.
2. Review `before.json` versus `after.json`: only the selected package may be added to the two lists. Preserve existing entries and all other settings. Backups and command files stay private and outside tracked source.
3. Immediately before applying, read the TV config again and run the helper's `verify` against `before.json`. If it differs, prepare again from the new state in a fresh directory. This is a freshness check, not an atomic lock against simultaneous firmware updates.
4. Use existing user authorization for the targeted fix. If it covers diagnosis only, request approval of the concrete diff before running the generated command. A skill does not grant new permissions. Never suppress command failures.
5. Read back saved JSON and `verify` against `after.json`; separately inspect the live TGuard service dump for the selected package in both lists. A silent update or live-only `dumpsys --ma` change does not prove persistence. If the save succeeded but live state did not reload, report that distinction and verify after an authorized reboot.
6. Offer the VPN's own auto-connect feature if available, preserving location and split tunneling. Reboot only with authorization covering the playback interruption. Reconnect after boot and check `sys.boot_completed`, both saved/live lists, and the VPN service/network. Give startup time before judging auto-connect. Test in the background and report the observation duration; a VPN network alone does not prove every app is tunneled with split tunneling.

If Surfshark continues disconnecting after `tguard-kill` has been eliminated, inspect the new process-exit history and relevant Android ANR diagnostics. For the tested Surfshark 3.37.1 / Android 12 foreground-service timeout affecting WireGuard, changing the protocol through the Surfshark TV app's **Settings → Protocol → OpenVPN/ UDP** prevented new ANRs during the observed test window. Treat this as a separate, user-approved in-app workaround. Preserve auto-connect, location, and split-tunneling preferences. Do not apply protocol changes to other VPN providers without evidence.

## Rollback and claims

- Use the helper's `rollback` with fresh current data and the original before/after pair. It prints a full restore command only if the pair is exactly the package-only change and the TV still matches the applied state. Re-read immediately before executing any generated command.
- If current settings have changed, merge only additions recorded in the original pair, preserving later settings and package entries that predated this fix. Preview and verify that merged rollback; do not force a full old configuration.
- The saved exclusions survived reboot with Surfshark on a TCL 55C7K-UK running Android 12. Other VPN apps and firmware are unverified; remote configuration or firmware updates may overwrite settings. Do not promise a universal or permanent cure.
- On the tested TCL 55C7K-UK with Surfshark 3.37.1, OpenVPN (UDP) established a foreground VPN service, survived the tested background and standby/wake scenarios, and automatically reconnected after one full reboot. No new ANRs occurred during approximately 20 minutes of sustained observation. Longer-term reliability remains unverified. Do not present this as a universal or permanent fix.
- Component disabling was denied on that TV; whole Safety Guard package disabling was restored by firmware during boot. Keep the fix targeted; do not disable Safety Guard as the default solution.
- Report actual changes, saved/live/reboot checks, and limitations. Redact network identifiers and never publish raw logs, pairing secrets, account details, or device backups.

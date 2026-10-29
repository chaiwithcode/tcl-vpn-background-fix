# Manual ADB reference

For Codex and Claude Code, use the shared skill described in the project's README. This reference preserves the manual setup and device-specific findings. The commands below assume a macOS/Linux shell, with the working directory at the downloaded project root.

The saved exclusions were reboot-verified with Surfshark on a TCL 55C7K-UK running Android 12. Other apps and firmware remain unverified.

## What causes this particular problem?

The TV's process-exit history repeatedly recorded:

```text
process=com.surfshark.vpnclient.android
reason=2 (SIGNALED)
status=9
description=tguard-kill
```

Android battery optimization was already disabled for Surfshark. TCL auto-start and associated-start permissions were already allowed. The VPN was still being killed by TCL's separate memory cleaner.

This fix applies to that cause. It does not diagnose every VPN disconnect, Wi-Fi interruption, server problem, or app crash.

## Requirements

- ADB available on your computer; see Google's [SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools).
- Python 3 for the configuration preparation step.
- TV and computer on the same local network.
- Developer options and debugging enabled on the TV, with this computer authorized.
- The matching TCL configuration provider and list names, checked below. If they are absent or access is denied, stop; these instructions are not a match for that firmware.

No root, APK installation, package removal, or Safety Guard disabling is needed for the saved-exclusion method.

## 1. Connect to the TV

### Enable Developer options

1. On the TV, open **Settings → System → About**. Some Android TV versions use **Settings → Device Preferences → About** instead.
2. Scroll to **Android TV OS build** (sometimes called **Build** or **Build number**).
3. With that row selected, press **OK** on the remote seven times, or until the TV says **You are now a developer**. If it says you are already a developer, continue to the next section.
4. Go back to **Settings → System** (or **Device Preferences**) and open **Developer options**.

### Enable USB debugging for ADB

1. In **Developer options**, turn on the main Developer options switch if one is shown.
2. Scroll to the **Debugging** section and enable **USB debugging**.
3. Accept the TV's confirmation dialog.

On the tested TCL C7K, enabling **USB debugging** also made ADB available over the network on port **5555**, despite there being no separate Network debugging toggle. A USB cable was not required for that TV.

That behavior varies by firmware. If the connection is refused, check the TV's available debugging options rather than assuming port 5555 must be open. Wireless debugging, when available, can require pairing and a different port.

### Find the TV's IP address and connect

Open **Settings → Network & Internet**, select the connected Wi-Fi or Ethernet network, and look for **IP address** or **Status information**. Menu names vary by firmware. Keep the computer and TV on the same local network.

These commands use a macOS/Linux shell. Replace `TV_IP` with your TV's local IP address:

```sh
export TV_ADB='TV_IP:5555'
adb connect "$TV_ADB"
adb devices -l
```

Watch the TV for an **Allow USB debugging?** prompt after running `adb connect`. Select **Always allow from this computer** if you trust this computer, then choose **Allow** or **OK**. This authorization prompt can appear even though the connection uses Wi-Fi.

Run `adb devices -l` again. Continue only when ADB reports the selected TV as `device`, rather than `unauthorized` or `offline`.

- **`unauthorized` / failed to authenticate:** accept the authorization prompt on the TV. If it does not appear, toggle USB debugging off and on, then retry the connection.
- **Connection refused:** confirm debugging is enabled and the IP address is still correct. If your firmware offers **Network debugging** or **Wireless debugging**, use the address, port, and pairing procedure it provides. USB debugging alone does not enable network ADB on every TV.
- **`offline`:** disconnect and reconnect the selected TV with `adb disconnect "$TV_ADB"` followed by `adb connect "$TV_ADB"`.

## 2. Confirm the cause

Find your VPN app's exact Android package name. List installed packages and identify the one belonging to your VPN; do not guess from the app's display name:

```sh
adb -s "$TV_ADB" shell pm list packages
export VPN_PACKAGE='YOUR_VPN_PACKAGE'
```

Replace `YOUR_VPN_PACKAGE` before continuing. For the tested Surfshark app, the package was `com.surfshark.vpnclient.android`; use that only if Surfshark is your chosen app.

```sh
adb -s "$TV_ADB" shell getprop ro.product.model
adb -s "$TV_ADB" shell getprop ro.build.version.release
adb -s "$TV_ADB" shell pm list packages "$VPN_PACKAGE"
adb -s "$TV_ADB" shell dumpsys activity exit-info "$VPN_PACKAGE"
adb -s "$TV_ADB" shell dumpsys deviceidle whitelist
adb -s "$TV_ADB" shell cmd appops get "$VPN_PACKAGE"
```

Look for repeated exits of your VPN app with `description=tguard-kill`. An exit due to an app update, user action, crash, or ordinary low-memory handling is different evidence. If `tguard-kill` is absent, investigate the actual disconnect before applying this fix.

Check whether your VPN app already has an Android battery exemption and whether TCL's `APP_AUTO_START` and `APP_ASSOC_START` operations are allowed. Their availability and names may vary by firmware.

## 3. Back up the TV's own cleaner configuration

```sh
mkdir -p vpn-fix-local
adb -s "$TV_ADB" shell content query \
  --uri content://com.tcl.providers.config/TGuardMemoryManager \
  > vpn-fix-local/original-query.txt
cat vpn-fix-local/original-query.txt
```

The tested firmware returned one row with `project_id=TGuardMemoryManager` and a JSON `config_content` array. That array contained `KillWhiteList` and `OneKeyCleanWhiteList`, each with a list of package names.

**Use the configuration read from your own TV.** Do not replace it with another model's complete list. Keep backups local; they are not needed in a public issue.

## 4. Prepare and review the smallest change

Use the single shared helper instead of copying Python code. Set `SKILL_DIR` to the skill folder. From the downloaded project root:

```sh
export SKILL_DIR="$PWD/skills/tcl-vpn-fix"
python3 "$SKILL_DIR/scripts/vpn_config.py" prepare \
  --query vpn-fix-local/original-query.txt \
  --package "$VPN_PACKAGE" --serial "$TV_ADB" \
  --output vpn-fix-local/run-1
```

If using an installed skill, use that skill's actual directory instead. The helper never runs ADB. It validates the input and creates a fresh output directory containing `before.json`, `after.json`, and, when a change is needed, `apply-command.txt`. It refuses to overwrite an existing directory.

Review the JSON files. Only your selected VPN package should be added to `KillWhiteList` and `OneKeyCleanWhiteList`; all other values must stay the same. If both lists already contain it, the helper reports no change and creates no apply command.

Immediately before applying, read the saved config again and check it against the original:

```sh
adb -s "$TV_ADB" shell content query \
  --uri content://com.tcl.providers.config/TGuardMemoryManager \
  > vpn-fix-local/pre-apply-query.txt
python3 "$SKILL_DIR/scripts/vpn_config.py" verify \
  --query vpn-fix-local/pre-apply-query.txt \
  --expected vpn-fix-local/run-1/before.json
```

If verification fails, stop and prepare again from the new config in a fresh output directory. This check does not lock out concurrent firmware updates.

If a change is needed, review the generated command and run it only after the check succeeds and the change is authorized:

```sh
cat vpn-fix-local/run-1/apply-command.txt
sh vpn-fix-local/run-1/apply-command.txt
```

The helper targets the selected ADB serial and handles the two shell-quoting layers. A successful TV update may print nothing; read it back next.

### Why the escaping matters

This TV's `content` command splits `--bind` values on unescaped colons. JSON also contains colons. Without escaping them, it rejects the update with **Binding not well formed**.

The shared helper doubles JSON backslashes first, then escapes colons inside the JSON value, then quotes the remote command and local command separately. The `config_content:s:` prefix stays unescaped. This behavior was checked against the command tool on the tested TV; other firmware may differ.

## 5. Read back and test after a full reboot

Read the saved configuration again and confirm the only changes are the intended additions:

```sh
adb -s "$TV_ADB" shell content query \
  --uri content://com.tcl.providers.config/TGuardMemoryManager
adb -s "$TV_ADB" shell dumpsys activity service \
  com.tcl.guard/.memorymanager.TGuardService
```

For an exact saved-config comparison, capture the query into a new local file and run:

```sh
adb -s "$TV_ADB" shell content query \
  --uri content://com.tcl.providers.config/TGuardMemoryManager \
  > vpn-fix-local/saved-query.txt
python3 "$SKILL_DIR/scripts/vpn_config.py" verify \
  --query vpn-fix-local/saved-query.txt \
  --expected vpn-fix-local/run-1/after.json
```

The live service dump should include your VPN app's package under both `KillWhiteList` and `OneKeyCleanWhiteList`. Saved configuration and live configuration are separate checks.

In your VPN app, enable its auto-connect setting, if available, if you want reconnection when the TV goes online. Surfshark calls this **Settings → Auto connect**. Keep your intended location and any split-tunneling configuration (called Bypasser in Surfshark). Then reboot when it is convenient; this interrupts playback:

```sh
adb -s "$TV_ADB" reboot
```

Once the TV is back, reconnect. If ADB has retained an offline connection, disconnect that TV and reconnect it:

```sh
adb disconnect "$TV_ADB"
adb connect "$TV_ADB"
adb -s "$TV_ADB" shell getprop sys.boot_completed
```

When boot is complete (`1`), repeat both configuration checks. Confirm your VPN reconnects and remains connected while you use your usual streaming app. These read-only diagnostics can help:

```sh
adb -s "$TV_ADB" shell dumpsys activity services "$VPN_PACKAGE"
adb -s "$TV_ADB" shell dumpsys connectivity
```

Look for your VPN app's service and a connected VPN network. Split tunneling can intentionally route only selected apps through the VPN; a connected tunnel does not prove that every app uses it. Raw connectivity dumps can contain personal network details, so redact them before sharing.

On the tested TV, both exclusions loaded automatically after reboot, and Surfshark's VPN was connected and validated approximately 71 seconds after boot. That is an observation, not a startup-time guarantee.

## Rollback

Read a fresh current query, then ask the same helper to prepare a rollback:

```sh
adb -s "$TV_ADB" shell content query \
  --uri content://com.tcl.providers.config/TGuardMemoryManager \
  > vpn-fix-local/current-query.txt
python3 "$SKILL_DIR/scripts/vpn_config.py" rollback \
  --query vpn-fix-local/current-query.txt \
  --before vpn-fix-local/run-1/before.json \
  --after vpn-fix-local/run-1/after.json \
  --package "$VPN_PACKAGE" --serial "$TV_ADB"
```

It prints a restore command only if the original pair represents exactly the selected package's additions and the current config still equals `after.json`. Review the command and ensure the query is still fresh before executing it separately.

If firmware or another change altered the current config, the helper refuses a full rollback. Merge only the VPN entries added by the original operation and preserve all newer settings. Never remove a package from a list where it was already present before this fix. Preview and verify a merged rollback as carefully as the original change.

After restoring the saved configuration, reboot when authorized to reload it and verify the result. The separate auto-connect setting can be turned off inside your VPN app.

## Findings from approaches that did not persist

- Android's battery exemption alone was insufficient on the tested TV.
- Adding entries through `dumpsys ... --ma mKillWhiteList ...` changed only the running cleaner's list; it did not survive a reboot by itself.
- Disabling only `com.tcl.guard/.memorymanager.TGuardService` was rejected with a `SecurityException`.
- Disabling the entire `com.tcl.guard` package reported success, but the firmware re-enabled it during boot. Package disabling was not a permanent solution on this TV.

The saved-exclusion method keeps Safety Guard enabled. It was verified with Surfshark; compatibility with other VPN apps still needs testing.

## Report compatibility

Reports from other TV models and VPN apps are welcome. Include the TV model, Android version, firmware version, VPN app and package name, whether `tguard-kill` was present, whether the two saved lists were available, and whether they survived reboot. Distinguish observations from assumptions.

Do not post account details, pairing codes, ADB keys, IP/MAC addresses, Wi-Fi names, or unredacted logs. No personal network details or original TV configuration backups are included in this project.

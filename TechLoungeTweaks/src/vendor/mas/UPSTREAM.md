# Microsoft Activation Scripts (MAS)

Source: https://github.com/massgravel/Microsoft-Activation-Scripts
Commit: 6401d2f36975dc07bcb6d22ea823a8498a75ec01
Version: 3.12
Retrieved: 2026-09-10
License: GPL-3.0, included as LICENSE.

These files are unmodified upstream source:
- HWID_Activation.cmd: MAS/Separate-Files-Version/Activators/HWID_Activation.cmd
- Change_Windows_Edition.cmd: MAS/Separate-Files-Version/Change_Windows_Edition.cmd

Tech Lounge Tweaks launches them as separate interactive processes. The scripts
are bundled with the application; the launcher does not download or execute a
remote bootstrap script. Activation itself requires an internet connection.
SHA-256 checksums are pinned in windows_setup.py. To update, replace the scripts
from a reviewed upstream commit and update both the hashes and this notice.

AL15 Quick-Setup-Tool
Version V1.7 (19.11.2026)
created by: M.Wingert - Solution Architect - ifm electronic vertrieb Deutschland GmbH
Source code: https://github.com/isofruit89/al15-quick-setup-tool
License: Apache License 2.0 (see LICENSE.txt)

Disclaimer:
This software is not an official ifm product.
The AL15 Quick-Setup Tool is provided for demonstration and evaluation purposes only. It has been developed as an internal/prototype tool to simplify configuration workflows and showcase possible approaches for device setup.

Important Notes:
This software is not released, supported, or maintained by ifm.
It is not tested according to official product quality or security standards.
The application is not digitally signed, which means your operating system or antivirus software may display a warning when starting it.
Use of this tool is entirely at your own risk.

Usage
The application runs locally on your machine and does not require installation.
- Start with start.bat: the tool starts and the browser opens automatically.
- Or start AL15-Quick-Setup-Tool.exe and open http://127.0.0.1:5010 in a browser.
The tool runs in the background without a window. To stop it, end "AL15-Quick-Setup-Tool.exe" in the Task Manager.

Folders
profiles  saved parameter sets (JSON, not encrypted)
exports   generated request lists and assets per parameter set
palettes  Node-RED palettes created with the palette packager

Requirements
Windows 10/11, AL159x with firmware 1.7 or later.

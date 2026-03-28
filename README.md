# WinOps Remote Management Agent

A comprehensive Windows remote endpoint management application designed to monitor, enforce, and log deep system configurations and policies across multiple machines. 

## Features

### Core Functionality
*   **Remote System Configuration:** Interfere with and manage a wide array of system settings (Power profiles, UAC, Network configs, Startup apps, and UI Themes) from a centralized console.
*   **Policy Persistence Engine:** Enforces your selected configurations by continuously monitoring and aggressively resetting modified registry values and system files.
*   **Advanced Telemetry & Logging:** Centralized SQLite-based logging system that records system state changes, the specific processes triggering them, and network enforcement events.
*   **Headless Client & Tray Integration:** Runs silently in the background as a lightweight service with an optional system tray icon for local user awareness.
*   **Remote Command Execution:** Secure API endpoints to push configuration payloads or trigger local scripts on the fly.

### Modern UI (Admin Console)
*   **PySide6-based Interface:** A highly responsive, modern GUI for the centralized management dashboard.
*   **Fleet Dashboard Tab:** View live status, connectivity, and compliance states of all remote nodes.
*   **Policy Editor Tab:** Granular controls to build and push configuration payloads (e.g., lock wallpaper, disable USB ports, enforce dark mode).
*   **Telemetry Tab:** Sortable, filterable view of network-wide system changes and security events.

### Technical Features
*   **Deep Registry & WMI Monitoring:** Efficiently monitors and hooks into core Windows subsystems without degrading host performance.
*   **Client-Server Architecture:** Secure local agent that communicates with a remote management server via encrypted WebSockets or REST API.
*   **Portable Executable:** Single-file agent executable compiled via PyInstaller for instant deployment.
*   **Privilege Escalation Ready:** Capable of running as a standard user for basic settings, or as SYSTEM/Admin for deep registry and policy enforcement.

## Installation

### Option 1: Run Admin Console from Source
1. Ensure Python 3.11+ is installed on the management machine.
2. Run `install.bat` to install dependencies.
3. Execute: `python admin_console.py`

### Option 2: Build Remote Agent Executable
1. Install dependencies: `pip install -r requirements.txt`
2. Install PyInstaller: `pip install pyinstaller`
3. Build the silent agent: `pyinstaller --onefile --noconsole --icon=assets/agent_icon.ico agent.py`
4. Deploy the executable from the `dist/` folder to your target Windows machines.

## Usage

### Admin Dashboard
*   **Node Management:** View all connected remote clients and their current system state.
*   **Policy Push:** Select a target (or group of targets) and push a new configuration profile.
*   **Real-time Overrides:** Manually flip system settings on a remote machine with a single click.

### Policy Persistence Mode
When enabled via the admin console, the remote agent enters Persistence Mode:
*   Actively monitors targeted registry keys and system APIs every 500ms.
*   Automatically reverts any unauthorized changes made by local users, third-party software, or Windows Updates.
*   Logs all enforcement actions and broadcasts them back to the admin server.
*   Effectively "locks" the remote machine to your exact specifications.

### Powerful Use Cases
*   **Fleet Management:** Maintain absolute consistency across all workstations in an environment.
*   **Kiosk Lockdown:** Prevent end-users from altering system behaviors, network settings, or visual themes.
*   **Security Enforcement:** Override local Group Policy to enforce stricter customized security baselines.
*   **Update Blocking:** Block unwanted configuration changes triggered by background Windows system updates.

## Technical Details

### Monitored Subsystems (Expandable)
*   **System UI:** `Personalize\Themes`, Desktop Wallpaper, Taskbar behavior.
*   **Security:** UAC settings (`EnableLUA`), Windows Defender toggles.
*   **System Policies:** `Software\Policies\Microsoft\Windows`
*   **Network/Power:** Active network adapters, sleep/hibernate timeouts.

### Database Schema
The SQLite database (local cache and server-side) stores:
*   Timestamp of configuration change
*   Target machine ID / IP Address
*   Before/After state of the setting
*   Source process name that attempted the change
*   Enforcement action taken (Allowed/Reverted)

### Performance
*   Minimal CPU usage (< 1% on modern systems) even during deep registry polling.
*   Small memory footprint (< 50MB RAM).
*   Asynchronous network I/O to ensure non-blocking UI and agent operations.

## Troubleshooting

### Common Issues
*   **Access Denied Logs:** Ensure the agent is deployed with Administrator/SYSTEM privileges if managing core OS settings like UAC or network adapters.
*   **Agent Offline:** Verify firewall rules allow outbound connections from the agent to your management server's IP/Port.
*   **Persistence Fights:** If the agent is stuck in an infinite loop of reverting a setting, check if a domain-level Group Policy object is actively fighting the agent.

## Development

### Project Structure

```text
WinOps/
├── server/
│   ├── admin_console.py       # PySide6 main management window
│   ├── api_server.py          # Listener for remote agents
│   └── database.py            # Central telemetry storage
├── agent/
│   ├── agent.py               # Remote client entry point
│   ├── system_monitor.py      # Core monitoring logic (Registry/WMI)
│   └── enforcer_service.py    # Background persistence wrapper
├── assets/                    # Icons and resources
├── requirements.txt           # Python dependencies
└── build_agent.bat            # Windows agent compiler
```

### Project Structure
* This is a rapidly evolving tool. Upcoming features include:

* Enhanced process detection utilizing ETW (Event Tracing for Windows) for kernel-level visibility.

* Remote terminal/shell access integration.

* Automated MSI installer generation for massive domain deployments.

* Active Directory / LDAP integration for role-based admin access.

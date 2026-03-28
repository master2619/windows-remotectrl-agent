#!/usr/bin/env python3
"""
WinOps Agent - Headless Entry Point
Runs silently in the background, enforcing policies.
"""

import sys
import os
import time
import winreg
import traceback
from pathlib import Path
import logging
import asyncio
from comm_layer import AgentCommLink
import psutil
import subprocess
import win32serviceutil
import win32service
import win32event
import servicemanager
import json

if getattr(sys, 'frozen', False):
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, application_path)

from service import ThemeService

class AgentConfig:
    """Pulls deployment settings injected by the MSI Installer"""
    
    REG_PATH = r"SOFTWARE\WinOpsAgent"
    
    @classmethod
    def load(cls):
        """Read all critical parameters from the registry"""
        logger = logging.getLogger(__name__)
        config = {}
        
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, cls.REG_PATH, 0, winreg.KEY_READ) as key:
                config['server_url'] = winreg.QueryValueEx(key, "ServerURL")[0]
                config['session_key'] = winreg.QueryValueEx(key, "SessionKey")[0]
                
                try:
                    config['agent_id'] = winreg.QueryValueEx(key, "AgentID")[0]
                except FileNotFoundError:
                    import socket
                    config['agent_id'] = socket.gethostname()
                    
            logger.info(f"Loaded config from Registry. Target: {config['server_url']}")
            return config
            
        except FileNotFoundError:
            logger.critical("FATAL: WinOps Registry keys missing! Was the MSI installer run?")
            return None
        except Exception as e:
            logger.critical(f"FATAL: Failed to read registry config: {e}")
            return None

class WinOpsAgent:
    """Headless agent handling background service coordination"""

    def ensure_explorer_is_alive():
        """Checks if the Windows shell is running and revives it if it's dead."""
            try:

                explorer_running = any(
                p.info['name'].lower() == 'explorer.exe' 
                for p in psutil.process_iter(['name']) 
                if p.info['name']
                                )
        
                if not explorer_running:
                print("explorer.exe is not running; Restarting shell...")
                subprocess.Popen(["explorer.exe"], shell=True)
                time.sleep(2) 
                print("Shell successfully resurrected.")
            except Exception as e:
                print(f"Failed to check or restart explorer: {e}")

    
    
    def __init__(self):
        self.setup_logging()
        self.theme_service = None

ensure_explorer_is_alive()

    def setup_logging(self):
        """Setup application logging"""
        log_dir = Path.home() / "AppData" / "Roaming" / "WinOpsAgent"
        log_dir.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "agent.log"),
                logging.StreamHandler()
                        ]
                                )
        self.logger = logging.getLogger(__name__)
        self.logger.info("WinOps Headless Agent initializing... 🚀")

    def start_services(self):
        """Setup background monitoring service"""
        try:
            initial_payload = [
            {
                "id": "theme_apps_dark",
                "name": "Enforce Dark Mode",
                "hive": "HKEY_CURRENT_USER",
            "path": "Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
            "key": "AppsUseLightTheme",
            "type": "REG_DWORD",
            "value": 0
            }
                                ]
            self.policy_enforcer = PolicyEnforcer()
            self.policy_enforcer.load_policies(initial_payload)
            self.policy_enforcer.start_enforcement()
            
            self.logger.info("Core enforcement services started. Running in shadows... 🥷")
        except Exception as e:
            self.logger.error(f"Failed to start services: {e}")
            self.logger.error(traceback.format_exc())

    def run(self):
        """Keep the agent alive without a GUI event loop"""
        self.start_services()
        
        try:
            self.logger.info("Agent is fully operational. Press Ctrl+C to exit.")
            
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Agent shutdown signaled by user.")
            return 0
        except Exception as e:
            self.logger.error(f"Fatal agent error: {e}")
            self.logger.error(traceback.format_exc())
            return 1
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup application resources"""
        self.logger.info("Wiping traces and shutting down... 🧹")
        if self.theme_service:
            self.theme_service.stop()

class WinOpsService(win32serviceutil.ServiceFramework):
    _svc_name_ = "WinOpsAgent"
    _svc_display_name_ = "WinOps System Management"
    _svc_description_ = "Enforces enterprise system configurations."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.logger = logging.getLogger(__name__)

    def SvcStop(self):
        """THE TRAP: Intercept the Stop signal and ignore it."""
        self.logger.warning("🚨 ALERT: User attempted to stop the WinOps service!")
        
        self.trigger_tamper_alert()

        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        

    def trigger_tamper_alert(self):
        """Creates a local flag that the CommLink will read and send"""
        try:
            with open("tamper_flag.dat", "w") as f:
                f.write("SERVICE_STOP_ATTEMPTED")
        except Exception:
            pass

    def SvcDoRun(self):
        """The entry point for the Windows Service"""
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        
        self.logger.info("Service Wrapper engaged. Starting main loop...")
        self.main_agent_loop()

def main():
    logger = logging.getLogger(__name__)
    logger.info("Starting WinOps Agent...")
    

    config = AgentConfig.load()
    
    if not config:
        logger.error("Agent cannot start without valid Registry Configuration.")
        logger.info("Going to sleep to prevent system instability. 💤")
        while True:
            time.sleep(3600) 
            
    comm_link = AgentCommLink(config)
    
    try:
        asyncio.run(comm_link.connect_to_mothership())
    except KeyboardInterrupt:
        logger.info("Agent shutting down...")
    except Exception as e:
        logger.error(f"Fatal crash: {e}")

    if "--service" in sys.argv:
        logger.info("Waking up as SYSTEM Service...")
        win32serviceutil.HandleCommandLine(WinOpsService)
        
    elif "--shell" in sys.argv:
        logger.info("Waking up as User Shell. Providing UI and watching...")
        ensure_explorer_is_alive()        
        while True:
            time.sleep(3600) 
            
    else:
        logger.error("Agent launched without context flags. Shutting down.")
        sys.exit(1)

if __name__ == "__main__":
    main()
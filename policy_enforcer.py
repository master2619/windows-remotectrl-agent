"""
WinOps Agent - Core Policy Enforcer
Dynamically monitors and enforces system configurations via Registry and WMI.
"""

import winreg
import sqlite3
import time
import logging
import threading
from datetime import datetime
from pathlib import Path
import json
import psutil

class PolicyEnforcer:
    """Core engine for dynamic registry monitoring and state persistence"""

    HIVE_MAP = {
        "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
        "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
        "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
        "HKEY_USERS": winreg.HKEY_USERS,
    }

    TYPE_MAP = {
        "REG_DWORD": winreg.REG_DWORD,
        "REG_SZ": winreg.REG_SZ,
        "REG_EXPAND_SZ": winreg.REG_EXPAND_SZ,
        "REG_BINARY": winreg.REG_BINARY,
    }

    def __init__(self, db_path=None):
        self.setup_database()
        self.logger = logging.getLogger(__name__)
        
        if db_path is None:
            app_data = Path.home() / "AppData" / "Roaming" / "WinOpsAgent"
            app_data.mkdir(parents=True, exist_ok=True)
            db_path = app_data / "telemetry.db"
            
        self.db_path = str(db_path)
        self.setup_database()

        self.policies = [] 
        self.is_enforcing = False
        self.enforcement_thread = None
        self.stop_event = threading.Event()

def setup_database(self):
        """Upgraded schema: Added source_process and synced flag"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS policy_telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    policy_id TEXT NOT NULL,
                    source_process TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT NOT NULL,
                    action_taken TEXT NOT NULL,
                    synced INTEGER DEFAULT 0 
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Failed to setup database: {e}")

    def detect_source_process(self):
        """Scan for the likely culprit that triggered the change"""
        try:
            for proc in psutil.process_iter(['name']):
                name = proc.info['name']
                if name and name.lower() in ['systemsettings.exe', 'regedit.exe', 'msiexec.exe', 'cmd.exe', 'powershell.exe']:
                    return name
            return "Unknown/Background Process"
        except Exception:
            return "Unknown"

    def log_telemetry(self, policy_id, old_val, new_val, action):
        """Record the violation locally"""
        source_process = self.detect_source_process()
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO policy_telemetry (timestamp, policy_id, source_process, old_value, new_value, action_taken)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (timestamp, policy_id, source_process, str(old_val), str(new_val), action))
            conn.commit()
            conn.close()
            self.logger.warning(f"🚨 Violation Detected: {policy_id} altered by {source_process}. Action: {action}")
        except Exception as e:
            self.logger.error(f"Telemetry logging failed: {e}")

    def get_unsynced_telemetry(self):
        """Fetch all logs that haven't been sent to the Mothership yet"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row 
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM policy_telemetry WHERE synced = 0")
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            self.logger.error(f"Failed to fetch unsynced logs: {e}")
            return []

    def mark_telemetry_synced(self, log_ids):
        """Flag logs as successfully transmitted"""
        if not log_ids: return
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            placeholders = ','.join('?' * len(log_ids))
            cursor.execute(f"UPDATE policy_telemetry SET synced = 1 WHERE id IN ({placeholders})", log_ids)
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Failed to mark logs synced: {e}")

    def load_policies(self, policy_payload):
        """Load a list of policy dictionaries (can be passed from a server later)"""
        if isinstance(policy_payload, str):
            self.policies = json.loads(policy_payload)
        else:
            self.policies = policy_payload
            
        self.logger.info(f"Loaded {len(self.policies)} system policies for enforcement.")

    def _read_registry_value(self, hive_str, path, key):
        """Safely read a value from the Windows Registry"""
        hive = self.HIVE_MAP.get(hive_str)
        if not hive:
            return None
            
        try:
            with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as reg_key:
                value, _ = winreg.QueryValueEx(reg_key, key)
                return value
        except FileNotFoundError:
            return None 
        except Exception as e:
            self.logger.error(f"Registry read error ({path}\\{key}): {e}")
            return None

    def _write_registry_value(self, hive_str, path, key, value, type_str):
        """Forcefully write a value to the Windows Registry"""
        hive = self.HIVE_MAP.get(hive_str)
        reg_type = self.TYPE_MAP.get(type_str, winreg.REG_DWORD)
        
        try:
            with winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_CREATE_SUB_KEY) as reg_key:
                winreg.SetValueEx(reg_key, key, 0, reg_type, value)
            return True
        except PermissionError:
            self.logger.warning(f"ACCESS DENIED! Run agent as Admin to modify {hive_str}\\{path}")
            return False
        except Exception as e:
            self.logger.error(f"Registry write error: {e}")
            return False

    def log_telemetry(self, policy_id, old_val, new_val, action):
        """Record enforcement actions"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO policy_telemetry (timestamp, policy_id, old_value, new_value, action_taken)
                VALUES (?, ?, ?, ?, ?)
            """, (timestamp, policy_id, str(old_val), str(new_val), action))
            conn.commit()
            conn.close()
            self.logger.info(f"⚡ Policy Enforced: {policy_id} | Set to {new_val}")
        except Exception as e:
            self.logger.error(f"Telemetry logging failed: {e}")

    def start_enforcement(self):
        """Kick off the relentless background loop"""
        if self.is_enforcing or not self.policies:
            return

        self.is_enforcing = True
        self.stop_event.clear()
        self.enforcement_thread = threading.Thread(target=self._enforcement_loop, daemon=True)
        self.enforcement_thread.start()
        self.logger.info("Enforcement engine activated. System lockdown initiated. 🛡️")

    def stop_enforcement(self):
        self.is_enforcing = False
        self.stop_event.set()
        if self.enforcement_thread:
            self.enforcement_thread.join(timeout=3)

    def _enforcement_loop(self):
        """The heart of the agent. Iterates through all policies continuously."""
        while self.is_enforcing and not self.stop_event.is_set():
            for policy in self.policies:
                try:
                    current_value = self._read_registry_value(
                        policy['hive'], policy['path'], policy['key']
                    )
                    
                    expected_value = policy['value']

                    if current_value != expected_value:
                        success = self._write_registry_value(
                            policy['hive'], policy['path'], policy['key'], 
                            expected_value, policy['type']
                        )
                        
                        if success:
                            self.log_telemetry(
                                policy['id'], current_value, expected_value, "REVERTED_UNAUTHORIZED_CHANGE"
                            )
                except Exception as e:
                    self.logger.error(f"Error evaluating policy {policy.get('id')}: {e}")

            time.sleep(1)
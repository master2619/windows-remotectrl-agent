"""
WinOps Agent - Telemetry & Comm Layer
Dials out to the Management Server and listens for dynamic policy payloads.
"""

import asyncio
import os
import websockets
import json
import logging
from policy_enforcer import PolicyEnforcer

logger = logging.getLogger(__name__)

class AgentCommLink:
    def __init__(self, config):
        self.server_url = config['server_url']
        self.agent_id = config['agent_id']
        self.session_key = config['session_key'] 
        self.enforcer = PolicyEnforcer()
        
    async def connect_to_mothership(self):
            logger.info(f"Initiating outbound WSS tunnel to {self.server_url}...")

            while True:
                try:
                    async with websockets.connect(self.server_url) as ws:
                    logger.info("Uplink established! Sending Session Key...")
                    
                    auth_packet = {
                        "type": "auth",
                        "agent_id": self.agent_id,
                        "session_key": self.session_key, 
                        "os": "Windows"
                    }
                    await ws.send(json.dumps(auth_packet))
                    
                    auth_response = json.loads(await ws.recv())
                    if auth_response.get("status") != "accepted":
                        logger.error("Server rejected our Session Key! Retrying later...")
                        await asyncio.sleep(60)
                        continue

                    logger.info("Authentication successful. Awaiting orders...")
                    
                    async for message in ws:
                        await self.handle_incoming_command(message, ws)

                    async def monitor_tampering(self, ws):
                        while True:
                            if os.path.exists("tamper_flag.dat"):
                            logger.info("Transmitting Tamper Alert to Mothership!")
                            alert_packet = {
                                "type": "telemetry",
                                "event": "tampering_detected",
                                "details": "User attempted to stop the Windows Service via services.msc"
                                            }
                            await ws.send(json.dumps(alert_packet))
                            os.remove("tamper_flag.dat") 
            
                            await asyncio.sleep(2) 
                        
                except Exception as e:
                    logger.error(f"Network/Auth failure: {e}")
                    await asyncio.sleep(5) 


    async def handle_incoming_command(self, message, ws):
        """Parse the JSON pushed down from the server"""
        try:
            packet = json.loads(message)
            command_type = packet.get("type")
            
            if command_type == "update_policies":
                logger.info("Received new policy payload from mothership!")
                
                new_policies = packet.get("payload", [])
                
                self.enforcer.stop_enforcement()
                self.enforcer.load_policies(new_policies)
                self.enforcer.start_enforcement()
                
                await ws.send(json.dumps({
                    "type": "ack",
                    "status": "policies_applied",
                    "count": len(new_policies)
                }))
                
            elif command_type == "ping":
                await ws.send(json.dumps({"type": "pong"}))
                
        except json.JSONDecodeError:
            logger.error("Received malformed garbage from server.")
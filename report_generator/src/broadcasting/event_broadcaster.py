from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import json
from enum import Enum

class EventType(Enum):
    # Coordinator events
    COORDINATOR_ANALYZING = "coordinator_analyzing"
    COORDINATOR_DECISION = "coordinator_decision"
    COORDINATOR_REASONING = "coordinator_reasoning"
    COORDINATOR_KEYWORDS = "coordinator_keywords"
    COORDINATOR_CONTINUING = "coordinator_continuing"
    
    # Expert events
    EXPERT_STARTING = "expert_starting"
    EXPERT_INITIALIZED = "expert_initialized"
    EXPERT_LOBE_RESPONSE = "expert_lobe_response"
    EXPERT_COMPLETED = "expert_completed"
    
    # Team events
    TEAM_STATUS = "team_status"
    APPROVED_EXPERTS = "approved_experts"
    
    # HTTP events
    HTTP_REQUEST = "http_request"
    
    # System events
    STATUS_CHANGE = "status_change"
    LOG_MESSAGE = "log_message"
    ERROR = "error"

class EventBroadcaster:
    def __init__(self):
        self.listeners: List[asyncio.Queue] = []
        
    def add_listener(self, queue: asyncio.Queue):
        self.listeners.append(queue)
        
    def remove_listener(self, queue: asyncio.Queue):
        if queue in self.listeners:
            self.listeners.remove(queue)
    
    async def broadcast(self, event_type: EventType, data: Dict[str, Any], job_id: Optional[str] = None):
        """Broadcast structured event to all listeners"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type.value,
            "job_id": job_id,
            "data": data
        }
        
        # Send to all listeners
        dead_queues = []
        for queue in self.listeners:
            try:
                await queue.put(event)
            except:
                dead_queues.append(queue)
        
        # Clean up dead queues
        for q in dead_queues:
            self.remove_listener(q)

# Global broadcaster instance
event_broadcaster = EventBroadcaster()

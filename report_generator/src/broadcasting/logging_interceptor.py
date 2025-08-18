import re
from src.broadcasting.event_broadcaster import event_broadcaster, EventType
import asyncio

class StructuredLogInterceptor:
    """Intercepts and parses log messages into structured events"""
    
    # Patterns to match different log types
    PATTERNS = {
        'coordinator_analyzing': re.compile(r'🎯 Coordinator analyzing conversation \(Message (\d+)/(\d+)\)'),
        'coordinator_decision': re.compile(r'🧠 Coordinator Decision: (.+)'),
        'coordinator_reasoning': re.compile(r'💭 Reasoning: (.+)'),
        'coordinator_keywords': re.compile(r'🔑 Updated Keywords: \[(.+)\]'),
        'expert_starting': re.compile(r'🔄 (.+) starting deliberation\.\.\.'),
        'expert_response': re.compile(r'(🎨 Creative Lobe|🧠 Reasoning Lobe) \((.+)\): (.+)'),
        'http_request': re.compile(r'HTTP Request: (\w+) (.+) "(.+)"'),
        'team_status': re.compile(r'(🚀|✅|📊|👥|⏱️|📋) (.+)'),
        'coordinator_continuing': re.compile(r'🔄 Coordinator continuing with tools'),
    }
    
    def __init__(self, job_id: str):
        self.job_id = job_id
    
    async def process_message(self, message: str, level: str = "INFO"):
        """Process a log message and emit structured events"""
        
        # Check coordinator analyzing
        match = self.PATTERNS['coordinator_analyzing'].match(message)
        if match:
            await event_broadcaster.broadcast(
                EventType.COORDINATOR_ANALYZING,
                {
                    "current_message": int(match.group(1)),
                    "max_messages": int(match.group(2)),
                    "progress_percentage": (int(match.group(1)) / int(match.group(2))) * 100
                },
                self.job_id
            )
            return
        
        # Check coordinator decision
        match = self.PATTERNS['coordinator_decision'].match(message)
        if match:
            await event_broadcaster.broadcast(
                EventType.COORDINATOR_DECISION,
                {"decision": match.group(1)},
                self.job_id
            )
            return
        
        # Check coordinator reasoning
        match = self.PATTERNS['coordinator_reasoning'].match(message)
        if match:
            await event_broadcaster.broadcast(
                EventType.COORDINATOR_REASONING,
                {"reasoning": match.group(1)},
                self.job_id
            )
            return
        
        # Check coordinator keywords
        match = self.PATTERNS['coordinator_keywords'].match(message)
        if match:
            keywords = [k.strip().strip("'\"") for k in match.group(1).split(',')]
            await event_broadcaster.broadcast(
                EventType.COORDINATOR_KEYWORDS,
                {"keywords": keywords},
                self.job_id
            )
            return
        
        # Check expert starting
        match = self.PATTERNS['expert_starting'].match(message)
        if match:
            await event_broadcaster.broadcast(
                EventType.EXPERT_STARTING,
                {"expert_name": match.group(1)},
                self.job_id
            )
            return
        
        # Check expert lobe response
        match = self.PATTERNS['expert_response'].match(message)
        if match:
            lobe_type = "creative" if "Creative" in match.group(1) else "reasoning"
            await event_broadcaster.broadcast(
                EventType.EXPERT_LOBE_RESPONSE,
                {
                    "lobe_type": lobe_type,
                    "expert_name": match.group(2),
                    "response_preview": match.group(3)[:200] + "..." if len(match.group(3)) > 200 else match.group(3)
                },
                self.job_id
            )
            return
        
        # Check HTTP requests
        match = self.PATTERNS['http_request'].match(message)
        if match:
            await event_broadcaster.broadcast(
                EventType.HTTP_REQUEST,
                {
                    "method": match.group(1),
                    "url": match.group(2),
                    "status": match.group(3)
                },
                self.job_id
            )
            return
        
        # Check team status
        match = self.PATTERNS['team_status'].match(message)
        if match:
            await event_broadcaster.broadcast(
                EventType.TEAM_STATUS,
                {
                    "icon": match.group(1),
                    "message": match.group(2)
                },
                self.job_id
            )
            return

        if "continue_coordinator" in message:
            await event_broadcaster.broadcast(
                EventType.COORDINATOR_CONTINUING,
                {"message": "Coordinator performing additional analysis"},
                self.job_id
            )
            return
        
        # Default: send as generic log
        await event_broadcaster.broadcast(
            EventType.LOG_MESSAGE,
            {
                "level": level,
                "message": message
            },
            self.job_id
        )

# Custom print interceptor
class PrintInterceptor:
    def __init__(self, job_id: str, original_print):
        self.job_id = job_id
        self.original_print = original_print
        self.interceptor = StructuredLogInterceptor(job_id)
        
    def __call__(self, *args, **kwargs):
        # Call original print
        self.original_print(*args, **kwargs)
        
        # Process the message
        message = ' '.join(str(arg) for arg in args)
        asyncio.create_task(self.interceptor.process_message(message))

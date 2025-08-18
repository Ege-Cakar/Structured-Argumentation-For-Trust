import asyncio
import aiohttp
import json
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout

console = Console()

class RiskAssessmentMonitor:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.experts = []
        self.current_expert = None
        self.messages_processed = 0
        self.max_messages = 30
        
    def display_experts(self):
        """Display expert team in a table"""
        if not self.experts:
            return
            
        table = Table(title="Expert Team")
        table.add_column("Expert", style="cyan")
        table.add_column("Keywords", style="green")
        
        for expert in self.experts[:5]:  # Show first 5
            keywords = ", ".join(expert.get("keywords", [])[:3]) + "..."
            table.add_row(expert["name"], keywords)
        
        if len(self.experts) > 5:
            table.add_row("...", f"and {len(self.experts) - 5} more")
            
        console.print(table)
    
    def process_event(self, event: dict):
        """Process and display structured events"""
        event_type = event.get("type")
        data = event.get("data", {})
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if event_type == "approved_experts":
            self.experts = data.get("experts", [])
            console.print(f"\n[bold blue]📚 Loaded {data.get('count')} experts[/bold blue]")
            self.display_experts()
            
        elif event_type == "coordinator_analyzing":
            self.messages_processed = data.get("current_message", 0)
            self.max_messages = data.get("max_messages", 30)
            progress = data.get("progress_percentage", 0)
            console.print(f"[{timestamp}] 🎯 Coordinator analyzing: Message {self.messages_processed}/{self.max_messages} ({progress:.1f}%)")
            
        elif event_type == "coordinator_decision":
            decision = data.get("decision")
            console.print(f"[{timestamp}] [bold green]🧠 Decision: {decision}[/bold green]")
            
        elif event_type == "coordinator_reasoning":
            reasoning = data.get("reasoning")
            console.print(f"[{timestamp}] [dim]💭 {reasoning}[/dim]")
            
        elif event_type == "coordinator_keywords":
            keywords = data.get("keywords", [])
            console.print(f"[{timestamp}] 🔑 Keywords: [cyan]{', '.join(keywords)}[/cyan]")
            
        elif event_type == "expert_starting":
            self.current_expert = data.get("expert_name")
            console.print(f"\n[{timestamp}] [bold yellow]🔄 {self.current_expert} starting deliberation...[/bold yellow]")
            
        elif event_type == "expert_lobe_response":
            lobe = data.get("lobe_type")
            expert = data.get("expert_name")
            response = data.get("response_preview")
            icon = "🎨" if lobe == "creative" else "🧠"
            console.print(f"[{timestamp}] {icon} {lobe.title()} Lobe: [dim]{response}[/dim]")
            
        elif event_type == "http_request":
            method = data.get("method")
            url = data.get("url")
            status = data.get("status")
            if "200 OK" in status:
                console.print(f"[{timestamp}] [dim green]📡 {method} {url} → {status}[/dim green]")
                
        elif event_type == "team_status":
            icon = data.get("icon")
            message = data.get("message")
            console.print(f"[{timestamp}] {icon} {message}")
            
        elif event_type == "status_change":
            status = data.get("status")
            message = data.get("message")
            if status == "completed":
                console.print(f"\n[bold green]✅ {message}[/bold green]")
            elif status == "failed":
                console.print(f"\n[bold red]❌ {message}[/bold red]")
            else:
                console.print(f"\n[bold blue]🔄 {message}[/bold blue]")

async def monitor_assessment(base_url: str, job_id: str):
    """Monitor assessment with pretty display"""
    monitor = RiskAssessmentMonitor(job_id)
    
    async with aiohttp.ClientSession() as session:
        # Connect to job-specific WebSocket
        ws_url = f"ws://localhost:8000/ws/progress/{job_id}"
        
        async with session.ws_connect(ws_url) as ws:
            console.print(Panel.fit(
                f"[bold]Monitoring Risk Assessment[/bold]\nJob ID: {job_id}",
                border_style="blue"
            ))
            
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    event = json.loads(msg.data)
                    monitor.process_event(event)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    console.print(f'[red]WebSocket error: {ws.exception()}[/red]')

async def submit_and_monitor(query: str):
    """Submit assessment and monitor with enhanced display"""
    base_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        # Submit assessment
        console.print("[bold blue]📤 Submitting assessment...[/bold blue]")
        
        async with session.post(
            f"{base_url}/api/assessments",
            json={
                "query": query,
                "generate_experts": False,
                "max_messages": 20
            }
        ) as resp:
            result = await resp.json()
            job_id = result["job_id"]
            
        # Monitor the assessment
        await monitor_assessment(base_url, job_id)

if __name__ == "__main__":
    # Install rich for pretty display: pip install rich
    
    query = """
    Perform a comprehensive SWIFT risk assessment for our e-commerce platform's 
    authentication system, focusing on multi-factor authentication vulnerabilities.
    """
    
    asyncio.run(submit_and_monitor(query))

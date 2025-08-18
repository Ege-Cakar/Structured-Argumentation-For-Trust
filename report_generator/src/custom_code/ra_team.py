"""
Hub-and-spoke architecture where Coordinator controls all expert interactions:
- Coordinator decides which expert speaks next
- Expert does internal deliberation, returns to Coordinator  
- Coordinator updates keywords and manages conversation flow, sends to another expert
- Summary Agent synthesizes final report when needed
"""

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
import logging
from src.utils.schemas import TeamState
from src.custom_code.summarizer import SummaryAgent
from src.custom_code.coordinator import Coordinator
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
import os
from pathlib import Path
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class ExpertTeam:
    """
    Main team orchestrator using LangGraph for state management.
    Implements hub-and-spoke architecture with coordinator control.
    """
    
    def __init__(
        self,
        coordinator: Coordinator,
        experts: Dict[str, Any],  # Expert instances
        summary_agent: SummaryAgent,
        max_messages: int = 40,
        recursion_limit: int = 125,
        debug: bool = False,
        conversation_path: str = "conversation.json",
        resume_checkpoint: str | None = None,
    ):
        self.coordinator = coordinator
        self.experts = experts
        self.summary_agent = summary_agent
        self.max_messages = max_messages
        self.debug = debug
        self.recursion_limit = recursion_limit
        self.conversation_path = conversation_path

        Path(self.conversation_path).mkdir(parents=True, exist_ok=True)
        
        # Generate unique conversation ID (overridden if resuming)
        self.conversation_id = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # If resuming, load checkpoint immediately
        self._checkpoint_state: TeamState | None = None
        if resume_checkpoint is not None and Path(resume_checkpoint).exists():
            self._checkpoint_state = self._load_checkpoint_state(resume_checkpoint)
            # Use the same conversation id so future files append correctly
            self.conversation_id = self._checkpoint_state.get("conversation_id", self.conversation_id)

        # Build the team graph
        self.team_graph = self._build_team_graph()
    
    def _build_team_graph(self) -> StateGraph:
        """Build the LangGraph state machine for team coordination"""

        workflow = StateGraph(TeamState)

        # Add core nodes
        workflow.add_node("coordinator", self._coordinator_decide)
        workflow.add_node("generate_summary", self._generate_summary)
        workflow.add_node("finalize", self._finalize)

        # One node per expert
        for expert_name in self.experts:
            workflow.add_node(expert_name, self._expert_deliberate)
            # Each expert returns to coordinator after speaking
            workflow.add_edge(expert_name, "coordinator")

        # Entry point
        workflow.add_edge(START, "coordinator")

        # Build routing map dynamically: each expert name maps to itself
        route_map = {name: name for name in self.experts}
        route_map["summarize"] = "generate_summary"
        route_map["continue_coordinator"] = "coordinator"

        workflow.add_conditional_edges(
            "coordinator",
            self._route_after_coordinator,
            route_map,
        )

        # Summary → finalize → END
        workflow.add_edge("generate_summary", "finalize")
        workflow.add_edge("finalize", END)
    
        return workflow.compile()

    def _load_checkpoint_state(self, checkpoint_file: str) -> TeamState:
        """Load a previously saved conversation state JSON file"""
        with open(checkpoint_file, "r") as f:
            data = json.load(f)
        return data  # type: ignore

    def _sanitize_for_filename(self, name: str) -> str:
        """Create a filesystem-safe identifier from an arbitrary step or expert name.
        - Lowercase
        - Replace spaces, dashes, and slashes with underscores
        - Replace '&' with 'and'
        - Replace remaining non-alphanumeric characters with underscores
        - Collapse duplicate underscores and trim
        """
        safe = name.lower()
        for ch in (" ", "-", "/", "\\"):
            safe = safe.replace(ch, "_")
        safe = safe.replace("&", "and")
        safe = "".join(c if (c.isalnum() or c == "_") else "_" for c in safe)
        while "__" in safe:
            safe = safe.replace("__", "_")
        return safe.strip("_")

    def _save_conversation_state(self, state: TeamState, step_name: str):
        """Save current conversation state to JSON"""
        # Create a serializable version of the state
        serializable_state = {
            "conversation_id": self.conversation_id,
            "timestamp": datetime.now().isoformat(),
            "step": step_name,
            "query": state.get("query", ""),
            "message_count": state.get("message_count", 0),
            "max_messages": state.get("max_messages", 0),
            "current_speaker": state.get("current_speaker", ""),
            "coordinator_decision": state.get("coordinator_decision", ""),
            "coordinator_instructions": state.get("coordinator_instructions", ""),
            "conversation_keywords": state.get("conversation_keywords", []),
            "messages": state.get("messages", []),
            "expert_responses": state.get("expert_responses", {}),
            "final_report": state.get("final_report", ""),
            "concluded": state.get("concluded", False)
        }
        
        # Save to timestamped file
        safe_step = self._sanitize_for_filename(step_name)
        filename = f"{self.conversation_id}_{state.get('message_count', 0):03d}_{safe_step}.json"
        filepath = os.path.join(self.conversation_path, filename)
        
        with open(filepath, "w") as f:
            json.dump(serializable_state, f, indent=2)
        
        # Also save a "latest" version that always has the current state
        latest_filepath = os.path.join(self.conversation_path, f"{self.conversation_id}_latest.json")
        with open(latest_filepath, "w") as f:
            json.dump(serializable_state, f, indent=2)
        
        # Save a human-readable conversation log
        self._save_conversation_log(state)

    def _save_conversation_log(self, state: TeamState):
        """Save human-readable conversation log"""
        log_filepath = os.path.join(self.conversation_path, f"{self.conversation_id}_log.md")
        
        with open(log_filepath, "w") as f:
            f.write(f"# Conversation Log: {self.conversation_id}\n\n")
            f.write(f"**Query**: {state.get('query', '')}\n\n")
            f.write(f"**Started**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            
            for msg in state.get("messages", []):
                speaker = msg.get("speaker", "Unknown")
                content = msg.get("content", "")
                
                f.write(f"## {speaker}\n\n")
                f.write(f"{content}\n\n")
                f.write("---\n\n")
            
            if state.get("final_report"):
                f.write("## Final Report\n\n")
                f.write(state.get("final_report", ""))
                f.write("\n\n")
    
    async def _coordinator_decide(self, state: TeamState) -> TeamState:
        """Coordinator decides next action"""
        decision_data = await self.coordinator.decide_next_action(state)
        
        # Only require instructions when handing off to an expert
        instructions = ""
        if decision_data["decision"] not in ["continue_coordinator", "summarize", "end"]:
            instructions = decision_data.get("instructions", "Please analyze the query based on your expertise")
        elif decision_data["decision"] == "summarize":
            instructions = decision_data.get("instructions", "Create final comprehensive summary")
        
        new_state = {
            **state,
            "coordinator_decision": decision_data["decision"],
            "coordinator_instructions": instructions,  # Use the conditional instructions
            "conversation_keywords": decision_data.get("keywords", state.get("conversation_keywords", [])),
            "messages": state["messages"] + [{
                "speaker": "Coordinator",
                "content": f"Decision: {decision_data['decision']} | Reasoning: {decision_data['reasoning']}"
            }]
        }

        self._save_conversation_state(new_state, "coordinator_decide")

        return new_state
    
    async def _expert_deliberate(self, state: TeamState) -> TeamState:
        """Run expert deliberation and return to coordinator"""
        expert_name = state["coordinator_decision"]
        expert = self.experts[expert_name]
        
        # Update expert keywords if provided
        if state.get("conversation_keywords"):
            await expert.update_keywords(
                lobe1_keywords=state["conversation_keywords"],
                lobe2_keywords=state["conversation_keywords"]
            )
        
        if self.debug:
            print(f"\n🔄 {expert_name} starting deliberation...")
        
        # Build team conversation context (without internal deliberations)
        team_context = f"User Query: {state['query']}\n\n"
        
        for msg in state["messages"]:
            speaker = msg["speaker"]
            content = msg["content"]
            
            if speaker == "Coordinator":
                # Clean up coordinator messages
                if "Decision:" in content and "Reasoning:" in content:
                    reasoning_part = content.split("Reasoning:")[1].strip()
                    team_context += f"Coordinator: {reasoning_part}\n\n"
                else:
                    team_context += f"Coordinator: {content}\n\n"
            else:
                # Expert final responses only
                team_context += f"{speaker}: {content}\n\n"
        
        # Get the current instruction from coordinator
        current_instruction = ""
        for msg in reversed(state["messages"]):
            if msg["speaker"] == "Coordinator" and "Reasoning:" in msg["content"]:
                current_instruction = msg["content"].split("Reasoning:")[1].strip()
                break
        
        # Get expert response with team context
        expert_response = await expert.process_message(current_instruction, team_context)
        
        new_state = {
            **state,
            "expert_responses": {**state["expert_responses"], expert_name: expert_response},
            "message_count": state["message_count"] + 1,
            "messages": state["messages"] + [{
                "speaker": expert_name,
                "content": expert_response
            }],
            "current_speaker": "Coordinator"
        }

        self._save_conversation_state(new_state, f"expert_{expert_name}")

        return new_state

        
    async def _generate_summary(self, state: TeamState) -> TeamState:
        """Generate final summary"""
        final_report = await self.summary_agent.generate_summary(state)
        
        new_state = {
            **state,
            "final_report": final_report,
            "concluded": True,
            "messages": state["messages"] + [{
                "speaker": "SummaryAgent", 
                "content": final_report
            }]
        }

        self._save_conversation_state(new_state, "summary")

        return new_state
    
    async def _finalize(self, state: TeamState) -> TeamState:
        """Finalize the conversation"""
        if self.debug:
            print(f"\n🏁 Team consultation completed!")
            print(f"📊 Total messages: {state['message_count']}")
            print(f"👥 Experts consulted: {list(state['expert_responses'].keys())}")
        
        final_state = {**state, "concluded": True}
        
        # Save final state
        self._save_conversation_state(final_state, "finalize")
        
        # Create a summary file
        summary_filepath = os.path.join(self.conversation_path, f"{self.conversation_id}_summary.json")
        with open(summary_filepath, "w") as f:
            json.dump({
                "conversation_id": self.conversation_id,
                "completed_at": datetime.now().isoformat(),
                "query": state.get("query", ""),
                "total_messages": state.get("message_count", 0),
                "experts_consulted": list(state.get("expert_responses", {}).keys()),
                "final_report_preview": state.get("final_report", "")[:500] + "..."
            }, f, indent=2)
        
        return final_state
    
    def _route_after_coordinator(self, state: TeamState) -> str:
        """Return the next node key based on coordinator decision"""
        decision = state["coordinator_decision"]
        
        # Handle continuation
        if decision == "continue_coordinator":
            return "continue_coordinator"
        elif decision == "summarize":
            return "summarize"
        elif decision == "end":
            return "finalize"  # triggers END via finalize node
        else:
            # coordinator returns the expert name directly; fallback to first expert
            return decision if decision in self.experts else next(iter(self.experts))
    
    async def consult(self, query: str, resume: bool = False) -> str:
        """Main method to run team consultation"""
        
        if self.debug:
            print(f"\n{'='*80}")
            print(f"🖋️ SWIFT RISK ASSESSMENT STARTING")
            print(f"{'='*80}")
            print(f"📋 Query: {query}")
            print(f"👥 Available Experts: {list(self.experts.keys())}")
            print(f"⏱️  Max Messages: {self.max_messages}")
        
        if resume and self._checkpoint_state is not None:
            initial_state = self._checkpoint_state  # type: ignore
            # Ensure debug and max_messages stay current
            initial_state["debug"] = self.debug
            initial_state["max_messages"] = self.max_messages
            if self.debug:
                print(f"\n🔄 Resuming consultation from checkpoint: {self.conversation_id}\n")
        else:
            # Initialize fresh team state
            initial_state: TeamState = {
                "messages": [],
                "query": query,
                "current_speaker": "Coordinator",
                "conversation_keywords": [],
                "expert_responses": {},
                "message_count": 0,
                "max_messages": self.max_messages,
                "concluded": False,
                "coordinator_decision": "",
                "final_report": "",
                "debug": self.debug
            }
        
        try:
            # Run the team consultation
            final_state = await self.team_graph.ainvoke(initial_state, {"recursion_limit": self.recursion_limit})
            
            # Return final report or last expert response
            result = final_state.get("final_report", "No summary generated")
            
            if self.debug:
                print(f"\n{'='*80}")
                print(f"📋 FINAL TEAM RESPONSE:")
                print(f"{'='*80}")
            
            return result
            
        except Exception as e:
            logger.error(f"Team consultation error: {e}", exc_info=True)
            error_msg = f"Team consultation encountered an error: {str(e)}"
            if self.debug:
                print(f"\n❌ {error_msg}")
            return error_msg
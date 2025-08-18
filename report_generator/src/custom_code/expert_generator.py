from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from typing import TypedDict, List, Literal, Annotated, Sequence
import json
import os
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from src.utils.schemas import ExpertGenTeamState
from src.utils.system_prompts import ORGANIZER_PROMPT, CRITIC_PROMPT
import logging
load_dotenv()
logger = logging.getLogger(__name__)

@tool 
def create_expert_response(
    thoughts: Annotated[str, "Your reasoning about the expert"],
    expert_name: Annotated[str, "Name of the expert"],
    expert_system_prompt: Annotated[str, "Detailed system prompt for the expert"],
    expert_keywords: Annotated[List[str], "List of keywords relevant to the expert"]
) -> dict:
    """Create a structured expert response"""
    return {
        "thoughts": thoughts,
        "response": {
            "name": expert_name,
            "system_prompt": expert_system_prompt,
            "keywords": expert_keywords
        }
    }
    
@tool
def func_save_expert(
    expert_name: Annotated[str, "Name of the expert"],
    expert_system_prompt: Annotated[str, "Detailed system prompt for the expert"],
    expert_keywords: Annotated[List[str], "List of keywords relevant to the expert"]
) -> dict:
    """Save an expert to the structured document"""
    output_file = "data/text_files/approved_experts.json"
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Load existing experts or create new list
    existing_experts = []
    if os.path.exists(output_file):
        try:
            with open(output_file, "r") as f:
                existing_experts = json.load(f)
                # Handle case where file contains single expert dict instead of list
                if isinstance(existing_experts, dict):
                    existing_experts = [existing_experts]
        except (json.JSONDecodeError, FileNotFoundError):
            existing_experts = []
    
    # Check for duplicates
    existing_names = [exp.get("name") for exp in existing_experts if isinstance(exp, dict)]
    if expert_name in existing_names:
        print(f"Expert {expert_name} already exists, skipping...")
        return {"status": "duplicate", "name": expert_name}

    # Add new expert
    new_expert = {
        "name": expert_name,
        "system_prompt": expert_system_prompt,
        "keywords": expert_keywords
    }
    
    existing_experts.append(new_expert)
    
    # Write back to file
    with open(output_file, "w") as f:
        json.dump(existing_experts, f, indent=4)
    
    print(f"Saved expert {expert_name} to {output_file}")
    return {"status": "approved", "expert": new_expert}

class ExpertGenerator:
    def __init__(self, model: str = "gpt-5", provider: str = "openai", min_experts: int = 5, max_experts: int = 8):
        """
        Initialize the SWIFT Risk Assessment Team
        
        Args:
            model: Model to use for LLM calls
            provider: LLM provider (openai or anthropic)
            min_experts: Minimum number of experts to generate
            max_experts: Maximum number of experts to generate
        """
        self.model = model
        self.min_experts = min_experts
        self.max_experts = max_experts
        
        # System prompts
        self.organizer_prompt = ORGANIZER_PROMPT
        self.critic_prompt = CRITIC_PROMPT

        organizer_tools_list = [create_expert_response]
        critic_tools_list = [func_save_expert]

        # Create LLM instances with tools bound
        if provider == "openai":
            self.organizer_llm = ChatOpenAI(
                model=model,
            ).bind_tools(organizer_tools_list)
            
            self.critic_llm = ChatOpenAI(
                model=model,
            ).bind_tools(critic_tools_list)
        elif provider == "anthropic":
            self.organizer_llm = ChatAnthropic(
                model=model,
                temperature=0.7
            ).bind_tools(organizer_tools_list)
            
            self.critic_llm = ChatAnthropic(
                model=model,
                temperature=0.3
            ).bind_tools(critic_tools_list)
        
        # Create tool nodes
        self.organizer_tools = ToolNode(organizer_tools_list)
        self.critic_tools = ToolNode(critic_tools_list)

        self.team_graph = self.create_graph()

    def organizer_agent(self, state: ExpertGenTeamState) -> dict:
        """The Organizer agent creates expert specifications"""
        print("🔨 Organizer Agent Working...")
        
        messages = state["messages"]
        task = state["task_description"]
        expert_count = state["expert_count"]
        
        # Build the conversation
        conversation_messages = []
        
        # Always start with system message and task
        conversation_messages.append(SystemMessage(content=self.organizer_prompt))
        conversation_messages.append(HumanMessage(content=f"TASK: {task}"))
        
        # Extract list of already created experts
        created_experts = []
        for msg in messages:
            if isinstance(msg, ToolMessage):
                try:
                    content = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                    if isinstance(content, dict) and content.get("status") == "approved":
                        expert_name = content.get("expert", {}).get("name", "Unknown")
                        created_experts.append(expert_name)
                except:
                    pass
        
        # Check if we just had an approval
        just_approved = False
        if len(messages) >= 2:
            for msg in messages[-3:]:
                if isinstance(msg, ToolMessage):
                    try:
                        content = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                        if isinstance(content, dict) and content.get("status") == "approved":
                            just_approved = True
                            break
                    except:
                        pass
        
        # Provide context about existing experts and next steps
        if created_experts:
            expert_list = "\n".join([f"- {name}" for name in created_experts])
            context_msg = f"""EXPERTS ALREADY CREATED ({len(created_experts)}):
    {expert_list}

    """
            if just_approved:
                context_msg += f"Expert '{created_experts[-1]}' was just approved! Now CREATE expert #{expert_count + 1} using create_expert_response tool. Make it DIFFERENT from the above experts."
            else:
                context_msg += f"Please CREATE expert #{expert_count + 1} using create_expert_response tool. Make it DIFFERENT from the above experts."
            
            conversation_messages.append(HumanMessage(content=context_msg))
        else:
            conversation_messages.append(HumanMessage(
                content="No experts created yet. Please CREATE the first expert using create_expert_response tool."
            ))
        
        # Check if we should finish
        if expert_count >= self.min_experts:
            conversation_messages.append(HumanMessage(
                content=f"You have created {expert_count} experts (minimum was {self.min_experts}). If the team has good coverage of all risk areas, say 'EXPERT GENERATION DONE'. Otherwise, create more specialized experts."
            ))
        
        # Call LLM
        response = self.organizer_llm.invoke(conversation_messages)
        
        print(f"📝 Organizer response: {response.content[:150] if response.content else 'Tool call only'}...")
        
        return {
            "messages": [response],
            "current_agent": "organizer"
        }



    def critic_agent(self, state: ExpertGenTeamState) -> dict:
        """The Critic agent evaluates expert specifications"""
        print("👾 Critic Agent Evaluating...")
        
        messages = state["messages"]
        
        # Build conversation - only include messages that don't cause conflicts
        conversation_messages = [SystemMessage(content=self.critic_prompt)]
        
        # Find the most recent expert proposal
        expert_data = None
        organizer_thoughts = None
        
        # Only look at recent messages, avoiding tool result conflicts
        for msg in reversed(messages[-10:]):
            # Skip tool messages to avoid conflicts
            if isinstance(msg, ToolMessage):
                try:
                    content = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                    if "response" in content and "name" in content["response"]:
                        expert_data = content["response"]
                        # Extract thoughts from the previous message
                        idx = messages.index(msg)
                        if idx > 0:
                            prev_msg = messages[idx - 1]
                            if hasattr(prev_msg, 'tool_calls') and prev_msg.tool_calls:
                                for tc in prev_msg.tool_calls:
                                    if tc['name'] == 'create_expert_response':
                                        organizer_thoughts = tc['args'].get('thoughts', '')
                                        break
                        break
                except:
                    continue
        
        if expert_data:
            # Create a clean conversation without tool messages
            eval_message = f"""
            Please evaluate the proposed expert:

            Expert Name: {expert_data['name']}
            Organizer's Thoughts: {organizer_thoughts or 'Not provided'}
            System Prompt: {expert_data['system_prompt']}
            Keywords: {', '.join(expert_data['keywords'])}

            You can either:
            1. Approve it by using the func_save_expert tool if it meets all criteria
            2. Provide constructive feedback on what needs improvement
            3. Ask clarifying questions about the expert's role or capabilities
            """
            conversation_messages.append(HumanMessage(content=eval_message))
        else:
            # No recent expert to evaluate
            conversation_messages.append(
                HumanMessage(content="I'm ready to evaluate the next expert proposal. Please have the organizer create one.")
            )
        
        # Call LLM
        response = self.critic_llm.invoke(conversation_messages)
        
        print(f"🎯 Critic response: {response.content[:150] if response.content else 'Tool call only'}...")
        
        return {
            "messages": [response],
            "current_agent": "critic"
        }



    def update_expert_count(self, state: ExpertGenTeamState) -> dict:
        """Check if expert was approved and update count"""
        messages = state["messages"]
        expert_count = state["expert_count"]
        
        # Check the last tool message for approval
        for msg in reversed(messages[-3:]):  # Check last few messages
            if isinstance(msg, ToolMessage):
                try:
                    content = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                    if content.get("status") == "approved":
                        expert_count += 1
                        print(f"✅ Expert approved! Total experts: {expert_count}")
                        break
                except:
                    continue
        
        return {
            "expert_count": expert_count,
            "current_agent": "organizer"
        }

    def should_continue(self, state: ExpertGenTeamState) -> str:
        """Routing logic after organizer"""
        messages = state["messages"]
        last_message = messages[-1] if messages else None
        
        # Check for completion
        if last_message and hasattr(last_message, 'content') and last_message.content:
            if "EXPERT GENERATION DONE" in last_message.content and state["expert_count"] >= self.min_experts:
                print(f"🎉 Expert generation completed with {state['expert_count']} experts!")
                return END
        
        elif state["expert_count"] >= self.max_experts:
            print(f"🎉 Expert generation completed with {state['expert_count']} (maximum amount) experts!")
            return END
        
        return "critic"

    def create_graph(self):
        """Creates the LangGraph workflow"""
        
        # Initialize the graph
        workflow = StateGraph(ExpertGenTeamState)
        
        # Add agent nodes
        workflow.add_node("organizer", self.organizer_agent)
        workflow.add_node("critic", self.critic_agent)
        workflow.add_node("update_count", self.update_expert_count)
        
        # Add tool nodes
        
        workflow.add_node("organizer_tools", self.organizer_tools)
        workflow.add_node("critic_tools", self.critic_tools)
        
        # Set entry point
        workflow.set_entry_point("organizer")
        
        # Organizer routing
        def route_organizer(state):
            messages = state["messages"]
            last_message = messages[-1] if messages else None
            
            # First check if we should end
            if last_message and hasattr(last_message, 'content') and last_message.content:
                if "EXPERT GENERATION DONE" in last_message.content and state["expert_count"] >= self.min_experts:
                    return END
            
            # Then check for tool calls
            if last_message and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"
            
            return "continue"
        
        workflow.add_conditional_edges(
            "organizer",
            route_organizer,
            {
                "tools": "organizer_tools",
                "continue": "critic",
                END: END
            }
        )

        
        # After organizer tools, check if we should continue
        workflow.add_conditional_edges(
            "organizer_tools",
            self.should_continue,
            {
                "critic": "critic",
                END: END
            }
        )
        
        # Critic routing
        def route_critic(state):
            messages = state["messages"]
            last_message = messages[-1] if messages else None
            
            if last_message and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"
            
            # If no tool call, go back to organizer for natural conversation
            return "continue"
        
        workflow.add_conditional_edges(
            "critic",
            route_critic,
            {
                "tools": "critic_tools",
                "continue": "organizer"  # Allow natural back-and-forth
            }
        )
            
        # After critic tools, update count and go back to organizer
        workflow.add_edge("critic_tools", "update_count")
        workflow.add_edge("update_count", "organizer")
        
        # Compile with memory
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)

    def run_expert_generator(self, user_request: str, swift_details: str, database_info: str):
        """Run the SWIFT risk assessment team creation process"""
        # Create the compiled graph
        app = self.create_graph()
        
        # Create task description
        expert_gen_task = f"""Generate a team of experts for risk assessment based on the following:

User Request: {user_request}

Information on SWIFT steps: {swift_details}

Database Information: {database_info}

Create diverse experts with different perspectives and specializations."""
        
        # Initial state
        initial_state = {
            "messages": [],
            "current_agent": "organizer", 
            "expert_count": 0,
            "task_description": expert_gen_task
        }
        # that's how langgraph operates
        
        print("🚀 Starting SWIFT Risk Assessment Team Creation...")
        print(f"📋 Task: {expert_gen_task[:100]}...")
        print("-" * 50)
        
        # Run the workflow
        config = {"configurable": {"thread_id": "swift_team_creation"},
        "recursion_limit": 100}
        
        try:
            final_state = None
            step_count = 0
            
            for state in app.stream(initial_state, config):
                step_count += 1
                final_state = state
                
                # Get the node that just executed
                node_name = list(state.keys())[0]
                current_state = state[node_name]
                
                print(f"\n🔄 Step {step_count}: {node_name}")
                
                # Show the latest message if it exists
                if "messages" in current_state and current_state["messages"]:
                    latest_msg = current_state["messages"][-1]
                    if hasattr(latest_msg, 'content') and latest_msg.content:
                        print(f"💬 {latest_msg.content[:200]}...")
                    elif hasattr(latest_msg, 'tool_calls') and latest_msg.tool_calls:
                        print(f"🔧 Tool call: {latest_msg.tool_calls[0]['name']}")
                
                if "expert_count" in current_state:
                    print(f"👥 Experts approved: {current_state['expert_count']}")
                print("-" * 30)
                
                # Safety break
                if step_count > 100:
                    print("⚠️ Maximum steps reached")
                    break
            
            if final_state:
                # Get the final expert count
                final_expert_count = 0
                for node_state in final_state.values():
                    if "expert_count" in node_state:
                        final_expert_count = node_state["expert_count"]
                
                print("\n" + "="*50)
                print("🎉 TEAM CREATION COMPLETE!")
                print(f"📊 Total Experts Generated: {final_expert_count}")
                print(f"🔄 Total Steps: {step_count}")
                
                # Check saved experts file
                try:
                    with open("src/text_files/approved_experts.json", "r") as f:
                        saved_experts = json.load(f)
                        print(f"\n👥 Saved Expert Team ({len(saved_experts)} experts):")
                        for i, expert in enumerate(saved_experts, 1):
                            print(f"  {i}. {expert.get('name', 'Unknown')}")
                            keywords = expert.get('keywords', [])
                            print(f"     Keywords: {', '.join(keywords[:5])}{'...' if len(keywords) > 5 else ''}")
                        
                        return saved_experts
                        
                except FileNotFoundError:
                    print("📁 No experts file found")
                    return []
            
        except Exception as e:
            print(f"❌ Error during execution: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

# Example usage
if __name__ == "__main__":
    # Initialize the team
    # expert_generator = ExpertGenerator(
    #     model="claude-sonnet-4-20250514",
    #     provider="anthropic",
    #     min_experts=5
    # )
    expert_generator = ExpertGenerator(
        model="gpt-5",
        provider="openai",
        min_experts=5
    )

    png = expert_generator.team_graph.get_graph().draw_mermaid_png()
    with open("expert_gen_graph.png", "wb") as f:
        f.write(png)
    
    # with open("data/text_files/approved_experts.json", "w") as f:
    #     f.write("[]")
    
    with open("data/text_files/dummy_req.txt", "r", encoding="utf-8") as file:
        risk_assessment_request = file.read()
        logger.info("Risk assessment request file loaded successfully")

    # Read the risk assessment request file
    with open("data/text_files/swift_info.txt", "r", encoding="utf-8") as file:
        swift_info = file.read()
        logger.info("Swift info file loaded successfully")

    # Create task request
    dummy_req = risk_assessment_request
    swift_info = swift_info
    database_info = "The database contains information about a wide range of relevant expertise."
    
    # Run the assessment
    # experts = expert_generator.run_expert_generator(
    #     user_request=dummy_req,
    #     swift_details=swift_info, 
    #     database_info=database_info
    # )
    
    print(f"\n📁 Expert team saved to: src/text_files/approved_experts.json")
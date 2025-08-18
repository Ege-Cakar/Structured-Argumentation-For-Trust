from typing import Dict, Any
from langchain_openai import ChatOpenAI
from src.utils.schemas import TeamState
from src.utils.system_prompts import SUMMARIZER_PROMPT
from src.utils.report import read_current_document, create_section, merge_section
from langchain_google_genai import ChatGoogleGenerativeAI
import logging

logger = logging.getLogger(__name__)

class SummaryAgent:
    """
    Specialized agent that synthesizes all expert contributions into a final report.
    """
    
    def __init__(self, model_client: ChatGoogleGenerativeAI or ChatOpenAI, debug: bool = False):
        self.model_client = model_client.bind_tools([create_section, read_current_document])
        self.debug = debug
        
        self.system_message = SUMMARIZER_PROMPT
    
    async def generate_summary(self, state: TeamState) -> str:
        """Generate final summary report"""
        
        if self.debug:
            logger.info(f"\n📊 Summary Agent generating final report...")
        
        # Collect all expert responses
        expert_contributions = ""
        for expert_name, response in state["expert_responses"].items():
            expert_contributions += f"\n=== {expert_name} Analysis ===\n{response}\n"
        
        conversation_log = ""
        for msg in state["messages"]:
            conversation_log += f"{msg['speaker']}: {msg['content']}\n"
        
        prompt = f"""Original Query: {state['query']}

Expert Contributions:
{expert_contributions}

Full Conversation Log:
{conversation_log}

Create the comprehensive final section that synthesizes all expert input and their arguments.

Make sure all details and arguments are preserved. Be comprehensive. Be specific. And be clear in your arguments.

I want you to have arguments clearly laid out. I want you to be thorough. 
"""
        
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self.model_client.ainvoke(messages)
            summary = response.content.strip()
            
            if self.debug:
                logger.info(f"✅ Summary Agent completed report ({len(summary)} chars)")
            
            return summary
            
        except Exception as e:
            logger.error(f"Summary generation error: {e}")
            return f"Error generating summary: {str(e)}"

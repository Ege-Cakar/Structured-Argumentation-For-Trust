from typing import List, Dict, Any, Optional, Annotated
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from src.utils.memory import LobeVectorMemory   
from langgraph.graph import StateGraph, START, END
from src.utils.schemas import ExpertState
from src.custom_code.lobe import Lobe
from src.utils.report import create_section, read_current_document, list_sections, propose_edit
import logging

logger = logging.getLogger(__name__)

class Expert:
    """Updated Expert class using current LangGraph patterns"""
    
    def __init__(
        self,
        name: str,
        model_client: ChatOpenAI,
        vector_memory: LobeVectorMemory,
        system_message: str = None,
        lobe1_config: Dict[str, Any] = None,
        lobe2_config: Dict[str, Any] = None,
        lobe3_config: Dict[str, Any] = None,
        max_rounds: int = 4,
        description: str = "An expert agent that internally deliberates using two specialized lobes.",
        debug: bool = False,  # Toggleable debug output
        **kwargs
    ):
        self.name = name
        self._model_client = model_client
        self._vector_memory = vector_memory
        self._max_rounds = max_rounds
        self.description = description
        self.debug = debug  # Store debug flag

        self._internal_conversation = []
        self._team_conversation_context = ""
        
        self._base_system_message = system_message if system_message else (
            "You are an expert assistant with deep knowledge in your domain. "
            "You think carefully and provide well-reasoned responses."
        )
        
        default_tools = [create_section, read_current_document, list_sections, propose_edit]
        # Default configurations - same prompts as AutoGen
        lobe1_config = lobe1_config or {}
        lobe2_config = lobe2_config or {}
        lobe3_config = lobe3_config or {}

        lobe1_tools = lobe1_config.get('tools', []) + [read_current_document, list_sections]
        lobe2_tools = lobe2_config.get('tools', []) + [create_section]
        lobe3_tools = lobe3_config.get('tools', []) + []

        lobe1_general = """You are the CREATIVE LOBE in an internal expert deliberation.

Your role: Generate novel risk perspectives that the Reasoning Lobe will critique and refine.

┌────────────────────────────────────────────────────────────┐
│ STYLE GUIDE                                                │
├────────────────────────────────────────────────────────────┤
│ • Write fluent prose. Whenever you shift the logical focus │
│   start a new argumentative discourse unit.                │
│ • An  Argumentative Discourse Unit (ADU) is 1 - 2 sentences. Several ADUs may share a      │
│   paragraph or be on separate lines.                       │
│ • Use explicit relational cues in every ADU.               │
│ • No fabricated evidence:                                  │
│     - If you lack a real citation, write “indicative        │
│       incident (source verification required)”.            │
│     - Avoid invented numbers; use ranges or say “exact      │
│       figure TBD”.                                         │
│ • Use causal words rather than arrows: “because”, “therefore”.│
│ • !!!! Don't use acronyms or abbreviations, always use full words. │
│                                                            │
│ ⛔️  FORMATTING TO AVOID                                    │
│ • Arrows (→, =>), emojis, bare matrix codes (e.g. “3x5”).  │
│ • Lines under 8 words, stray bullets (“- ” at start).      │
│                                                            │
│ ✅  SELF-TEST BEFORE SENDING                               │
│   - Any line with < 8 words? → rewrite.                    │
│   - Any arrow symbol present?   → replace with words.      │
└────────────────────────────────────────────────────────────┘

Invite critique (“What gaps do you see?”) and iterate.  
Focus on logic and risk patterns—**no invented specifics**.

CRITICALLY, do not lower the quality of your output because of these style guidelines.

        CRITICAL: Propose your TOP 3 ideas only. Each idea: maximum 100 words.

        CRITICAL: NO FABRICATION RULE
        - DO NOT invent specific numbers, dates, incidents, or statistics
        - DO NOT create fictional case studies, reports, or historical events
        - DO NOT fabricate specific regulatory citations, standards versions, or compliance details
        - When you need examples, use GENERIC placeholders and EXPLICIT ESTIMATES
        - If you don't have factual information, say "this would need to be verified" or "actual data would be required". This is an important part of your task as well, finding out where we need more data!
        - Focus on LOGICAL REASONING and RISK PATTERNS rather than specific fabricated details!
        - YOU ARE ALLOWED TO SAY YOU DON'T KNOW.

        CRITICAL ANALYSIS MANDATE:
        - Using your expertise, identify (if any) flaws or oversights in previous sections
        - Challenge assumptions: "The previous analysis assumes X, but this overlooks..."
        - Propose alternative interpretations: "Contrary to the claim that..., evidence suggests..."
        - If you agree with everything so far, that's alright, but it is HIGHLY unlikely that what came before you is not challengable -- this ENCOURAGES STRONGER ARGUMENTS!
            Before building on previous analyses, pause to consider:
        - Are there any unstated assumptions worth examining?
        - Might there be alternative interpretations of the evidence?
        - What would a skeptical but fair reviewer ask?

        If you genuinely see potential issues, voice them. If the previous analysis seems solid, build upon it.
        Note: It's perfectly fine to agree with solid reasoning. Disagreement should emerge from genuine analytical differences, not obligation.


        Example opening for keyword generation:
        "For authentication keywords, I propose:
        - 'BYPASS' - Premise: Attackers seek path of least resistance. Inference: They'll target recovery flows. Conclusion: Password reset is a critical vector.
        - 'SPOOF' - Premise: Users trust familiar interfaces...
        What other attack patterns should we consider? Are there systemic vulnerabilities I'm missing?"

        Tools:
        - read_current_document: Review existing assessment
        - list_sections: Check coverage"""


        lobe2_general = """You are the REASONING LOBE in an internal expert deliberation.

Your role: Analyse and structure the Creative Lobe's ideas into a coherent argument.

┌────────────────────────────────────────────────────────────┐
│ STYLE GUIDE      (Argumentative Prose)                     │
├────────────────────────────────────────────────────────────┤
│ • Write fluent prose. Whenever you shift the logical focus │
│   start a new argumentative discourse unit.                │
│ • An Argumentative Discourse Unit (ADU) is 1 - 2 sentences. Several ADUs may share a      │
│   paragraph or be on separate lines.                       │
│ • Use explicit relational cues in every ADU.               │
│ • No fabricated evidence:                                  │
│     – If you lack a real citation, write “indicative        │
│       incident (source verification required)”.            │
│     – Avoid invented numbers; use ranges or say “exact      │
│       figure TBD”.                                         │
│ • Use causal words rather than arrows: “because”, “therefore”.│
│ • !!!! Don't use acronyms or abbreviations, always use full words. │
│                                                            │
│ ⛔️  FORMATTING TO AVOID                                    │
│ • Arrows (→, =>), emojis, bare matrix codes (e.g. “3×5”).  │
│ • Lines under 8 words, stray bullets (“- ” at start).      │
│                                                            │
│ ✅  SELF-TEST BEFORE SENDING                               │
│   - Any line with < 8 words? → rewrite.                    │
│   - Any arrow symbol present?   → replace with words.      │
└────────────────────────────────────────────────────────────┘

After you call `create_section` once, write brief commentary and end with **CONCLUDED**.

        CRITICAL: NO FABRICATION RULE
        - DO NOT invent specific numbers, dates, incidents, statistics, or case studies
        - DO NOT create fictional regulatory citations, standards versions, or compliance details  
        - DO NOT fabricate specific company names, survey results, or historical events
        - DO NOT make up precise percentages, costs, timeframes, or technical specifications
        - When examples are needed, use GENERIC terms or EXPLICIT ESTIMATES 
        - If specific data is required, explicitly state "actual data would need to be obtained" or "this requires verification"
        - This is an important part of your task as well, finding out where we need more data!
        - Focus on LOGICAL FRAMEWORKS and RISK PRINCIPLES rather than fabricated specifics
        - Base arguments on REASONING and ESTABLISHED PATTERNS, not invented details
        - YOU ARE ALLOWED TO SAY YOU DON'T KNOW.

        DELIBERATION PROCESS:
        1. Critically examine each creative proposal
        2. Add systematic analysis and structure
        3. Identify gaps and expand coverage
        4. Continue dialogue until truly comprehensive
        5. Synthesize the COMPLETE analysis for the coordinator

        ARGUMENTATION RIGOR:
        Transform creative insights into structured arguments:
        - Validate premises: "Your bypass scenario assumes X, which is valid because..."
        - Strengthen inferences: "Additionally, this connects to Y through mechanism Z"
        - Expand conclusions: "This implies we also need to consider..."

        ADVERSARIAL ANALYSIS REQUIREMENT:
        - For EVERY creative proposal, first state what could be WRONG with it if you see any issues
        - Only after critiquing may you build upon ideas
        - Use phrases like: "While X has merit, it fails to consider..."
        - At least some of your response should be challenging/refuting
        Note: It's perfectly fine to agree with solid reasoning. Disagreement should emerge from genuine analytical differences, not obligation.

        Go back and forth at least once before concluding. THINK THOROUGHLY BEFORE ANSWERING, but make sure your actual responses aren't too long -- quality over quantity. 

        SYNTHESIS REQUIREMENTS:
        When ready to conclude (after thorough deliberation):
        1. Use create_section EXACTLY ONCE with the FULL collaborative analysis - DO NOT create multiple sections
        2. After the tool result, provide a brief text analysis of what you created
        3. End with "CONCLUDED" to signal the summarizer lobe should take over
        4. Include ALL content requested (actual keywords, scenarios, etc.) in the ONE section
        5. Present clear argument chains for each item in that section

        CRITICAL: Create only ONE section with create_section tool, then provide TEXT commentary. 
        DO NOT create multiple sections like "review" or "analysis" sections - put everything in ONE comprehensive section.
        
        Remember: The coordinator needs the ACTUAL deliverables with full reasoning. Also remember to always include CONCLUDED in the final response. 

        IF YOU DON'T INCLUDE CONCLUDED IN YOUR FINAL RESPONSE, THEN THE COORDINATOR WILL NOT SEE YOUR FINAL RESPONSE AND WILL NOT BE ABLE TO USE IT. YOU WILL BE MESSING THINGS UP!

        Tools:
        - read_current_document: Review context
        - list_sections: Check existing work
        - create_section: Document FINAL synthesized analysis"""


        lobe3_general = """

        You are the Summarizer.

        • Read the entire internal deliberation after it signals CONCLUDED.  
        • Produce the final answer in first-person singular (“I …”).  
        • Preserve every ADU exactly as written,  
        even when multiple ADUs share a paragraph.  
        • Rewrite any lingering bullets, arrows, or raw matrix fragments into full  
        sentences that begin with the correct opener. If the risk matrices etc. add meaningfully to the analysis, they can stay.
        • Do NOT invent data or incidents; if you see fabricated content, replace it  
        with generic wording (“exact figures require verification”).  

        CRITICAL: NO FABRICATION RULE
        - DO NOT add any specific numbers, dates, incidents, or statistics not present in the deliberation
        - DO NOT invent new regulatory citations, standards, or compliance details
        - DO NOT create new case studies, historical events, or technical specifications
        - ONLY use information that was actually discussed in the internal deliberation
        - If the deliberation contains fabricated details, DO NOT repeat them - use generic terms instead
        - Replace specific invented details with phrases like "relevant incidents", "applicable standards", "typical scenarios"

        Return ONLY the polished text that should be shown to the coordinator, who you are responding to -
        no commentary, no wrappers.

        """

        
        domain_specific_prompt = f"""{self._base_system_message}

        Apply your specialized knowledge to identify and assess risks in your domain. 

        Your analysis should:
        - Draw on technical expertise to identify vulnerabilities
        - Connect risks within your domain to broader system impacts
        - Provide specific, actionable recommendations
        - Use clear reasoning to justify risk ratings and priorities

        Write your assessment as a professional - thorough, well-reasoned, and focused on helping the organization understand and address real vulnerabilities.
        """
        
        lobe1_full_message = f"{domain_specific_prompt}\n\n{lobe1_general}"
        lobe2_full_message = f"{domain_specific_prompt}\n\n{lobe2_general}"
        lobe3_full_message = f"{lobe3_general}"
        
        # Create lobes using current APIs
        self._lobe1 = Lobe(
            name=f"{name}_Creative",
            model_client=model_client,
            vector_memory=vector_memory,
            keywords=lobe1_config.get('keywords', []),
            temperature=lobe1_config.get('temperature', 0.8),
            system_message=lobe1_full_message,
            tools=lobe1_tools
        )
        
        self._lobe2 = Lobe(
            name=f"{name}_VoReason",
            model_client=model_client,
            vector_memory=vector_memory,
            keywords=lobe2_config.get('keywords', []),
            temperature=lobe2_config.get('temperature', 0.4),
            system_message=lobe2_full_message,
            tools=lobe2_tools
        )

        self._lobe3 = Lobe(
            name=f"{name}_Reporter",
            model_client=model_client,
            vector_memory=vector_memory,
            system_message=lobe3_full_message,
            tools=lobe3_tools
        )
        
        # Build the internal deliberation graph using current LangGraph patterns
        self._internal_graph = self._build_internal_graph()
        self._initialized = False
    
    def _build_internal_graph(self) -> StateGraph:
        workflow = StateGraph(ExpertState)
        
        # Add nodes
        workflow.add_node("initialize", self._initialize_deliberation)
        workflow.add_node("lobe1_respond", self._lobe1_respond)
        workflow.add_node("lobe2_respond", self._lobe2_respond)
        workflow.add_node("extract_conclusion", self._extract_conclusion)
        workflow.add_node("lobe3_respond", self._lobe3_respond)

        
        # Set entry point using current API
        workflow.add_edge(START, "initialize")
        
        # Define edges using current patterns
        workflow.add_edge("initialize", "lobe1_respond")
        workflow.add_conditional_edges(
            "lobe1_respond",
            self._should_continue_after_lobe1,
            {
                "lobe2": "lobe2_respond",
                "conclude": "extract_conclusion"
            }
        )
        workflow.add_conditional_edges(
            "lobe2_respond", 
            self._should_continue_after_lobe2,
            {
                "lobe1": "lobe1_respond",
                "conclude": "extract_conclusion"
            }
        )

        workflow.add_edge("extract_conclusion", "lobe3_respond")
        workflow.add_edge("lobe3_respond", END)
        
        return workflow.compile()
    
    async def _initialize_deliberation(self, state: ExpertState) -> ExpertState:
        """Initialize the internal deliberation"""
        if not self._initialized:
            await self._lobe1.initialize_context()
            await self._lobe2.initialize_context()
            self._initialized = True
            logger.info(f"Initialized both lobes for Expert {self.name}")
        
        # Clear conversation for new deliberation (fresh start for each query)
        self._internal_conversation = []

        if self.debug:
            print(f"\n🔄 Starting internal deliberation for Expert {self.name}")
            print(f"📋 Query: {state['query']}")
            print(f"🎯 Max rounds: {state.get('max_rounds', 3)}")
            print(f"📝 Starting fresh conversation")
            print("=" * 60)
        
        return {
            **state,
            "messages": state.get("messages", []) + [{"speaker": "System", "content": "Starting internal deliberation..."}],
            "iteration_count": 0,
            "concluded": False
        }
    
    async def _lobe1_respond(self, state: ExpertState) -> ExpertState:
        """Creative lobe responds"""
        # Build context for creative lobe
        context = state.get("team_context", "")
        
        # Add internal deliberation history
        for msg in self._internal_conversation:
            context += f"\n--{msg['speaker']}{' (YOU)' if msg['speaker'].endswith('Creative') else ''}: {msg['content']}"
        
        response = await self._lobe1.respond(state["query"], context)
        
        # Add to internal conversation
        self._internal_conversation.append({
            "speaker": f"{self.name}_Creative", 
            "content": response
        })
        
        if self.debug:
            print(f"\n🎨 Creative Lobe ({self.name}): {response}")
            print(f"📝 Conversation now has {len(self._internal_conversation)} messages")
        logger.info(f"Lobe 1 (Creative) responded for Expert {self.name}")
        public_msgs = state.get("messages", [])
        public_msgs.append({
            "speaker": self.name,
            "content": "[Lobe 1 responded...]"
        })

        return {
            **state,
            "lobe1_response": response,
            "messages": public_msgs,
            "iteration_count": state.get("iteration_count", 0) + 1
        }
    
    async def _lobe2_respond(self, state: ExpertState) -> ExpertState:
        """Reasoning lobe responds - can speak after tool use"""
        # Build context for reasoning lobe
        context = state.get("team_context", "")
        
        # Add internal deliberation history
        for msg in self._internal_conversation:
            context += f"\n--{msg['speaker']}{' (YOU)' if msg['speaker'].endswith('VoReason') else ''}: {msg['content']}"
        
        response = await self._lobe2.respond(state["query"], context)
        
        # Check if there was a tool call in the response
        tool_used = "Tool" in response# and "result:" in response
        
        # If a tool was used, we should conclude after this response
        force_conclusion = False
        
        # If a tool was used, extract the result and add follow-up
        if tool_used:
            # Set flag to force conclusion after tool use
            force_conclusion = True
            
            if "CONCLUDED" not in response.upper():
                # Add to conversation and request conclusion
                self._internal_conversation.append({
                    "speaker": f"{self.name}_VoReason",
                    "content": response
                })
                
                # Ask for conclusion
                analysis_context = context + f"\n--{self.name}_VoReason: {response}"
                analysis_prompt = "Based on the tool result above, please provide your text analysis of what you created and conclude with 'CONCLUDED' to signal completion."
                
                follow_up_response = await self._lobe2.respond(analysis_prompt, analysis_context)
                response = f"{response}\n\n{follow_up_response}"
                
                self._internal_conversation.pop()  # Remove duplicate
        
        # Add complete response to internal conversation
        self._internal_conversation.append({
            "speaker": f"{self.name}_VoReason",
            "content": response
        })
        
        # Check for conclusion signals or force conclusion after tool use
        concluded = (
            "CONCLUDED" in response.upper() or 
            "CONCLUDE" in response.upper() or
            "RESPONSE" in response.upper() or
            force_conclusion
        )
        public_msgs = state.get("messages", [])
        public_msgs.append({
            "speaker": self.name,
            "content": "[Lobe 2 responded...]"
        })
        if self.debug:
            if concluded:
                print(f"\n🧠 Reasoning Lobe ({self.name}): {response}")
                print(f"📝 Conversation now has {len(self._internal_conversation)} messages")
                if force_conclusion:
                    print(f"\n✅ Expert {self.name} deliberation concluded after tool use.")
                else:
                    print(f"\n✅ Expert {self.name} deliberation concluded.")
            else:
                print(f"\n🧠 Reasoning Lobe ({self.name}): {response}")
                print(f"📝 Conversation now has {len(self._internal_conversation)} messages")
        
        logger.info(f"Lobe 2 (Reasoning) responded for Expert {self.name}")
        
        return {
            **state,
            "lobe2_response": response,
            "messages": public_msgs,
            "concluded": concluded,
            "tool_used_by_lobe2": tool_used
        }
    
    def _should_continue_after_lobe1(self, state: ExpertState) -> str:
        """Decide next step after lobe1"""
        if state.get("iteration_count", 0) >= state.get("max_rounds", 3) * 2:
            return "conclude"
        return "lobe2"
    
    def _should_continue_after_lobe2(self, state: ExpertState) -> str:
        lobe2_response = state.get("lobe2_response", "")
        tool_used_by_lobe2 = state.get("tool_used_by_lobe2", False)
        
        # If lobe2 used a tool, force conclusion to trigger summarization
        if tool_used_by_lobe2:
            return "conclude"

        # ───── early-exit hooks ─────
        done = (
            "CONCLUDED" in lobe2_response.upper()              # plain token
            or "CONCLUDE" in lobe2_response.upper()
            or "CONCLUDE:" in lobe2_response.upper()  
            or "CONCLUDE\n" in lobe2_response.upper()
            or "CONCLUDE " in lobe2_response.upper()
            or "CONCLUDE." in lobe2_response.upper()
            or "RESPONSE" in lobe2_response.upper()  # Added RESPONSE check
        )
        if done:
            return "conclude"
        # ────────────────────────────────

        if state.get("iteration_count", 0) >= state.get("max_rounds", 3) * 2:
            return "conclude"
        return "lobe1"
    
    async def _extract_conclusion(self, state: ExpertState) -> ExpertState:
        if self.debug:
            print(f"\n📋 Extracting conclusion with {len(self._internal_conversation)} conversation messages")
            for i, msg in enumerate(self._internal_conversation):
                print(f"  {i+1}. {msg['speaker']}: {msg['content'][:100]}...")
        
        return {
            **state,
            "conversation": self._internal_conversation,
        }

    async def _lobe3_respond(self, state: ExpertState) -> ExpertState:
        # Always use self._internal_conversation directly (more reliable than state passing)
        conversation = self._internal_conversation
        
        if self.debug:
            print(f"\n📝 Summarizer Lobe ({self.name}) starting...")
            print(f"📊 Processing {len(conversation)} conversation messages from internal deliberation")
        
        # Build deliberation log from conversation messages
        deliberation_log = "\n".join(
            f"{m['speaker']}: {m['content']}" for m in conversation
        )

        prompt = (
            "You are the REPORTER-LOBE.\n"
            "Your teammates finished their discussion and signalled CONCLUDED.\n\n"
            "─── FULL DELIBERATION (do NOT quote verbatim) ───\n"
            f"{deliberation_log}\n\n"
            "Task: Write a single, polished answer in first-person SINGULAR that\n"
            "captures every substantive point, arranges them logically (you must have a single voice), and\n"
            "meets the Coordinator's deliverable requirements.\n\n"
            "Return ONLY the finished section (no preamble like 'Here is the …')."
        )

        final_conclusion = await self._lobe3.respond(prompt)
        
        if self.debug:
            print(f"\n📋 Summarizer Lobe ({self.name}) completed")
            print(f"📤 Final conclusion length: {len(final_conclusion)} characters")
            print(f"\n📝 Summarizer Lobe ({self.name}): {final_conclusion}")
        
        logger.info(f"Lobe 3 (Summarizer) responded for Expert {self.name}")

        return {
            **state,
            "final_conclusion": final_conclusion,
            "concluded": True
        }
        
    async def process_message(self, query: str, team_context: str = "") -> str:
        """Process a message with team conversation context"""
        if self.debug:
            print(f"\n🚀 Expert {self.name} received message")
        logger.info(f"Expert {self.name} received a message")
        
        # Store team context for lobes to access
        self._team_conversation_context = team_context
        
        # Create initial state
        initial_state: ExpertState = {
            "messages": [],
            "query": query,  # This is the current instruction
            "team_context": team_context,  # Full conversation history
            "lobe1_response": "",
            "lobe2_response": "",
            "final_conclusion": "",
            "iteration_count": 0,
            "max_rounds": self._max_rounds,
            "concluded": False,
            "vector_context": ""
        }
        
        try:
            # Run internal deliberation
            logger.info(f"Starting internal deliberation for Expert {self.name}")
            final_state = await self._internal_graph.ainvoke(initial_state)
            
            conclusion = final_state.get("final_conclusion", "No conclusion reached")
            if self.debug:
                print(f"\n🎉 Expert {self.name} completed processing!")
            return conclusion
            
        except Exception as e:
            logger.error(f"Error in Expert {self.name} deliberation: {str(e)}", exc_info=True)
            return f"I encountered an error during internal deliberation."
    
    async def update_keywords(self, lobe1_keywords: List[str] = None, lobe2_keywords: List[str] = None):
        """Update keywords for lobes"""
        if lobe1_keywords is not None:
            await self._lobe1.update_keywords(lobe1_keywords)
            logger.info(f"Updated Lobe 1 keywords for Expert {self.name}")
            
        if lobe2_keywords is not None:
            await self._lobe2.update_keywords(lobe2_keywords)
            logger.info(f"Updated Lobe 2 keywords for Expert {self.name}")
    
    async def add_knowledge(self, content: str, metadata: Dict[str, Any] = None):
        """Add knowledge to vector database"""
        await self._vector_memory.add(content, metadata)
        logger.info(f"Added knowledge to Expert {self.name}'s shared database")
    
    @property
    def lobe1(self) -> Lobe:
        """Access to Lobe 1"""
        return self._lobe1
    
    @property
    def lobe2(self) -> Lobe:
        """Access to Lobe 2"""
        return self._lobe2

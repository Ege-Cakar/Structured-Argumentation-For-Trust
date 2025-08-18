from typing import List, Dict, Any, Optional, Annotated  
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langgraph.graph import StateGraph, START, END
import json
import logging
import asyncio
import signal
import os 
import re 
 
from dotenv import load_dotenv
from src.custom_code.expert import Expert
from src.custom_code.lobe import LobeVectorMemory   
from src.custom_code.coordinator import Coordinator
from src.custom_code.summarizer import SummaryAgent
from src.custom_code.ra_team import ExpertTeam
from src.custom_code.expert_generator import ExpertGenerator
from src.utils.memory import initialize_database
from pathlib import Path
from langchain_google_genai import ChatGoogleGenerativeAI
import inquirer
from src.utils.system_prompts import EXPERT_EXTRAS
from src.utils.report import get_doc_manager
from datetime import datetime
from src.custom_code.section_transformer import AsyncSectionTransformer
from src.utils.system_prompts import ARGUMENT_TRANSLATOR_PROMPT


load_dotenv()

logger = logging.getLogger(__name__)

# Debug flag - Set to True to see internal deliberation, False for quiet mode
DEBUG_INTERNAL_DELIBERATION = True

# Maximum messages for expert team deliberation
MAX_EXPERT_MESSAGES = 100  # Default for normal runs

generate_from_scratch = False

def select_checkpoint(conversations_dir: str) -> Optional[str]:
    """
    Scan for available checkpoints and let user select one.
    Returns the selected checkpoint path or None if no checkpoints found.
    """
    if not os.path.isdir(conversations_dir):
        print("⚠️  Conversations directory not found.")
        return None
    
    # Find all latest checkpoints
    latest_checkpoints = []
    fl_checkpoints = []
    
    for f in os.listdir(conversations_dir):
        f_lower = f.lower()
        filepath = os.path.join(conversations_dir, f)
        
        # Check for feedback loop files (case insensitive, various patterns)
        if ('_fl.json' in f_lower or '_fl_' in f_lower) and f.endswith('.json'):
            mtime = os.path.getmtime(filepath)
            fl_checkpoints.append((filepath, mtime, f))
        # Check for latest files (but exclude FL files already captured)
        elif f.endswith("_latest.json") and '_fl' not in f_lower:
            mtime = os.path.getmtime(filepath)
            latest_checkpoints.append((filepath, mtime, f))
        # Also check for other FL patterns that might not have "latest" in them
        elif f_lower.endswith("_fl.json"):
            mtime = os.path.getmtime(filepath)
            if (filepath, mtime, f) not in fl_checkpoints:  # Avoid duplicates
                fl_checkpoints.append((filepath, mtime, f))
    
    # Sort by modification time (newest first)
    latest_checkpoints.sort(key=lambda x: x[1], reverse=True)
    fl_checkpoints.sort(key=lambda x: x[1], reverse=True)
    
    if not latest_checkpoints and not fl_checkpoints:
        print("⚠️  No checkpoints found in data/conversations.")
        return None
    
    # Build selection menu
    print("\n" + "="*60)
    print("SELECT CHECKPOINT TO RESUME FROM:")
    print("="*60)
    
    options = []
    
    # Add latest checkpoints
    if latest_checkpoints:
        print("\n📁 Latest Checkpoints:")
        for i, (path, mtime, filename) in enumerate(latest_checkpoints[:5]):  # Show max 5 latest
            dt = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            print(f"  {i+1}) {filename} - Modified: {dt}")
            options.append(("latest", i, path, filename, dt))
    
    # Add feedback loop checkpoints
    if fl_checkpoints:
        print("\n🔄 Feedback Loop Checkpoints (for v2 documents):")
        start_idx = len(latest_checkpoints[:5]) + 1
        for i, (path, mtime, filename) in enumerate(fl_checkpoints[:5]):  # Show max 5 FL
            dt = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            idx = start_idx + i
            print(f"  {idx}) {filename} - Modified: {dt}")
            options.append(("fl", i, path, filename, dt))
    
    print(f"\n  0) Cancel and start fresh")
    print("="*60)
    
    # Get user selection
    while True:
        try:
            choice = input("\nEnter your choice (0 to cancel): ").strip()
            choice_num = int(choice)
            
            if choice_num == 0:
                print("Cancelled. Starting fresh.")
                return None
            elif 1 <= choice_num <= len(options):
                selected = options[choice_num - 1]
                checkpoint_type, _, path, filename, dt = selected
                print(f"\n✅ Selected {'feedback loop' if checkpoint_type == 'fl' else 'latest'} checkpoint:")
                print(f"   File: {filename}")
                print(f"   Modified: {dt}")
                return path
            else:
                print(f"Invalid choice. Please enter a number between 0 and {len(options)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except Exception as e:
            print(f"Error: {e}")
            return None

async def main():
    # Setup logging
    logging.basicConfig(level=logging.INFO)

    Path("data/report").mkdir(parents=True, exist_ok=True)
    Path("data/conversations").mkdir(parents=True, exist_ok=True)
    
    # ----------------------------------------------------------------------------
    # Interactive Operation Mode Selection
    # ----------------------------------------------------------------------------
    print("\n" + "="*60)
    print("SWIFT RISK ASSESSMENT SYSTEM")
    print("="*60)
    print("\nSelect operation mode:")
    print("1) Generate from scratch with NEW experts")
    print("2) Generate from scratch with SAVED experts")
    print("3) Generate summary from saved sections.json")
    print("4) Continue from a checkpoint")  # Changed text here
    print("="*60)
    
    while True:
        choice = input("\nEnter your choice (1-4): ").strip()
        if choice in ['1', '2', '3', '4']:
            break
        print("Invalid choice. Please enter 1, 2, 3, or 4.")
    
    # Process choice flags
    generate_new_experts: bool = (choice == '1')
    continue_previous: bool = (choice == '4')
    run_full_assessment: bool = (choice in ['1', '2', '4'])
    summary_only: bool = (choice == '3')
    
    print(f"\nSelected: Option {choice}")
    print("="*60 + "\n")
    
    # ----------------------------------------------------------------------------
    # Reset data IF REQUIRED
    # ----------------------------------------------------------------------------
    if not continue_previous and not summary_only:
        print("Resetting data files...")
        
        # Remove any previous team state file
        state_path = "data/text_files/team_state.pkl"
        if os.path.exists(state_path):
            try:
                os.remove(state_path)
            except OSError:
                pass
        
        # Delete previous generated markdown/text files
        import glob
        protected = {"data/text_files/swift_info.md"}
        for path in glob.glob("data/text_files/*.md"):
            if path in protected:
                continue
            try:
                os.remove(path)
            except OSError:
                pass
        
        # Reset JSON files to empty objects
        json_files = [
            "data/report/current_document.json",
            "data/report/history.json",
            "data/report/sections.json",
        ]

        for json_file in json_files:
            with open(json_file, "w") as f:
                f.write("{}")
        
        # Reset report.md to empty
        with open("data/report/report.md", "w") as f:
            f.write("")
        
        print("Data files reset complete.\n")
    else:
        print("Continuing with existing data files. No reset performed.\n")
    
    report = "data/text_files/report.md"
    
    # -----------------------------------------------------------------------------
    # Clear report if not continuing or in summary mode
    if not continue_previous and not summary_only:
        with open(report, "w") as f:
            f.write("")

    translator_task = None
    translator = None

    if run_full_assessment:
        # Read the risk assessment request file
        with open("data/text_files/dummy_req.txt", "r", encoding="utf-8") as file:
            risk_assessment_request = file.read()
            logger.info("Risk assessment request file loaded successfully")

        translator = AsyncSectionTransformer(
            sections_path="data/report/sections.json",
            output_path="data/report/sections_transformed.json",
            system_prompt_template=ARGUMENT_TRANSLATOR_PROMPT,
            original_query=risk_assessment_request,
            poll_interval=3.0,  # Check every 3 seconds
            debug=DEBUG_INTERNAL_DELIBERATION
        )
        translator_task = asyncio.create_task(translator.run())
        print("✅ Argument transformer started in background")

        # Read the risk assessment request file
        with open("data/text_files/swift_info.md", "r", encoding="utf-8") as file:
            swift_info = file.read()
            logger.info("Swift info file loaded successfully")

        # Read the database info file
        with open("data/text_files/database_info.txt", "r", encoding="utf-8") as file:
            database_info = file.read()
            logger.info("Database info file loaded successfully")

        # Setup vector memory using current API
        vector_memory = await initialize_database()
        
        # Create model client using current API
        model_client = ChatOpenAI(
            model="gpt-5",
            use_responses_api=True,
            reasoning={"effort": "high"},
            text={"verbosity": "low"},
            output_version="responses/v1",
        )

        thinking_client = ChatOpenAI(
            model="gpt-5",
            use_responses_api=True,
            reasoning={"effort": "high"},
            text={"verbosity": "low"},
            output_version="responses/v1",
        )
    
    if generate_new_experts:
        print("🔄 Generating new expert team...")
        with open("data/text_files/approved_experts.json", "w") as f:
            f.write("[]")
        
        # Create the task request string
        expert_gen_task = f"""Generate a team of experts for risk assessment based on the following:

        User Request: {risk_assessment_request}

        Information on SWIFT steps: {swift_info}

        You will have access to relevant data to help with keyword generation and expert identification. 
        """

        expert_generator = ExpertGenerator(
            model="gpt-5",
            provider="openai",
            min_experts=5,
            max_experts=8
        )

        _ = expert_generator.run_expert_generator(
            user_request=risk_assessment_request,
            swift_details=swift_info, 
            database_info=database_info
        )
        print("✅ New expert team generated!")
    
    # main.py - UPDATED OPTION 3 SECTION ONLY

    # ADDED: Option 3 - Summary only from saved sections
    if summary_only:
        print("📊 Generating summary from saved sections...")

        swift_info = ""

        with open("data/text_files/swift_info.md", "r", encoding="utf-8") as file:
            swift_info = file.read()
        
        # Re-use the shared DocumentManager singleton so we see the same sections that the
        # tool functions created during normal runs.
        doc_manager = get_doc_manager()
        
        if not doc_manager.sections:
            print("❌ No saved sections found in data/report/sections.json")
            print("Please run option 1 or 2 first to generate sections.")
            return
        
        # Create model client without tools binding for direct summary
        model_client = ChatOpenAI(
            model="gpt-5",
            use_responses_api=True,
            reasoning={"effort": "high"},
            text={"verbosity": "low"},
            output_version="responses/v1",
        )
        
        # Build content from saved sections
        messages = []
        expert_responses = {}
        all_sections_content = []
        
        # Process each section
        print("\n📄 Found sections:")
        for section_id, section in doc_manager.sections.items():
            print(f"  - {section.domain} by {section.author} (status: {section.status.value})")
            if section.status.value == "draft":
                expert_name = section.author
                expert_responses[expert_name] = section.content
                messages.append({
                    "speaker": expert_name,
                    "content": section.content
                })
                all_sections_content.append(f"=== {section.domain} (by {expert_name}) ===\n{section.content}")
        
        if not expert_responses:
            print("❌ No merged sections found. Please complete a full assessment first.")
            return
        
        print(all_sections_content)
        
        # Create a direct summary prompt
        summary_prompt = f"""You are the SWIFT Risk Assessment Summary Agent. Based on the expert analyses provided below, as well as information on SWIFT, generate a comprehensive final report.

        Expert Contributions:

        {chr(10).join(all_sections_content)}

        Information on SWIFT:
        {swift_info}
        
        Make sure all details and arguments are preserved. Be comprehensive. Be specific. And be clear in your arguments.

        I want you to have arguments clearly laid out. I want you to be thorough. 

        What you are saying must be logically and argumentatively complete with premises, inferences and conclusions. EVERYTHING YOU SAY MUST BE WELL SUPPORTED, EITHER THROUGH ARGUMENTATION OR EVIDENCE.

        """

        # Generate summary directly
        print("\n🔄 Generating comprehensive summary...")
        
        try:
            response = model_client.invoke([
                {"role": "system", "content": "You are a professional risk assessment summarizer. Create clear, actionable reports."},
                {"role": "user", "content": summary_prompt}
            ])
            
            final_report = response.content
            
            if final_report:
                print("\n" + "="*80)
                print("📋 FINAL SUMMARY REPORT:")
                print("="*80)
                print(final_report)
                
                # Save the summary
                with open("data/text_files/summary_report.md", "w") as f:
                    f.write(final_report)
                print(f"\n✅ Summary saved to data/text_files/summary_report.md")
                
                # Also update the main report
                with open("data/text_files/report.md", "w") as f:
                    f.write(final_report)
                print(f"✅ Main report updated at data/text_files/report.md")
            else:
                print("❌ Failed to generate summary")
                
        except Exception as e:
            print(f"❌ Error generating summary: {e}")
            logger.error(f"Summary generation error: {e}", exc_info=True)
        
        return  # Exit early for summary-only mode
    
    if run_full_assessment:
        with open("data/text_files/approved_experts.json", "r") as f:
            approved_experts = json.load(f)

        if not approved_experts:
            print("❌ No approved experts found. Please run option 1 first.")
            return

        print(f"✅ Loaded {len(approved_experts)} experts")

        # Create experts
        experts = {}
        for expert in approved_experts:
            keywords = expert["keywords"]
            lobe1_config = {
                "keywords": keywords,
                "temperature": 1
            }
            lobe2_config = {
                "keywords": keywords,
                "temperature": 1
            }
            expert_agent = Expert(
                name=expert["name"].lower().replace(" ", "_").replace("-","_"),
                model_client=model_client,
                vector_memory=vector_memory,
                system_message=expert["system_prompt"]+"\n\n"+EXPERT_EXTRAS,
                lobe1_config=lobe1_config,
                lobe2_config=lobe2_config,
                debug=DEBUG_INTERNAL_DELIBERATION  # Let team handle debug output
            )
            experts[expert["name"]] = expert_agent
        
        coordinator_client = ChatOpenAI(
            model="gpt-5",
            use_responses_api=True,
            reasoning={"effort": "high"},
            text={"verbosity": "medium"},
            output_version="responses/v1",
        )

        # Create team components
        coordinator = Coordinator(coordinator_client, experts, debug=DEBUG_INTERNAL_DELIBERATION, swift_info=swift_info)
        summary_agent = SummaryAgent(model_client, debug=DEBUG_INTERNAL_DELIBERATION)
        
        # Determine resume checkpoint if continuing
        resume_checkpoint: Optional[str] = None
        is_feedback_loop: bool = False
        revision_number: int = 1
        if continue_previous:
            conversations_dir = "data/conversations"
            
            # Use the new checkpoint selection function
            resume_checkpoint = select_checkpoint(conversations_dir)
            
            if resume_checkpoint:
                # Check if it's a feedback loop checkpoint and extract revision number
                filename_lower = os.path.basename(resume_checkpoint).lower()
                is_feedback_loop = '_fl' in filename_lower
                
                if is_feedback_loop:
                    # Extract revision number if present (e.g., _FL_2 -> 2)
                    import re
                    match = re.search(r'_fl_?(\d+)', filename_lower)
                    if match:
                        revision_number = int(match.group(1))
                    else:
                        revision_number = 1  # Default to 1 if no number after _FL
                
                checkpoint_type = f"feedback loop (revision {revision_number})" if is_feedback_loop else "latest"
                print(f"✅ Resuming from {checkpoint_type} checkpoint: {os.path.basename(resume_checkpoint)}")
            else:
                print("⚠️  No checkpoint selected. Starting a new team.")

        # Determine message limit based on checkpoint type and revision
        if is_feedback_loop:
            message_limit = MAX_EXPERT_MESSAGES + (30 * revision_number)
            print(f"📈 Using scaled message limit for feedback loop revision {revision_number}: {message_limit} messages")
        else:
            message_limit = MAX_EXPERT_MESSAGES

        # Create team (optionally with resume checkpoint)
        team = ExpertTeam(
            coordinator=coordinator,
            experts=experts,
            summary_agent=summary_agent,
            max_messages=message_limit,  # Dynamically set based on checkpoint type
            debug=DEBUG_INTERNAL_DELIBERATION,
            conversation_path="data/conversations",
            resume_checkpoint=resume_checkpoint,
        )

        # Register Ctrl+C handler to report latest checkpoint location
        def _interrupt_handler(signum, frame):
            try:
                latest_path = os.path.join("data/conversations", f"{team.conversation_id}_latest.json")
                print(f"\n💾 Progress is checkpointed to: {latest_path}")
                print("   You can continue later using option 4 (Continue from a checkpoint).")
            except Exception as e:
                print(f"\n⚠️  Interrupt received but failed to compute checkpoint path: {e}")
            raise KeyboardInterrupt

        signal.signal(signal.SIGINT, _interrupt_handler)
        try:
            signal.signal(signal.SIGTERM, _interrupt_handler)
        except Exception:
            pass

        png = team.team_graph.get_graph().draw_mermaid_png()
        
        with open("team_graph.png", "wb") as f:
            f.write(png)
        
        if DEBUG_INTERNAL_DELIBERATION:
            print("✅ Expert system initialized!")
            print("\n" + "="*80)
        
        # Process a query
        query = risk_assessment_request 
        response = await team.consult(query, resume=resume_checkpoint is not None)

        if translator and translator_task:
            # Do final transformation pass
            await translator.transform_all_final()
            
            # Stop the transformer
            translator.stop()
            await asyncio.sleep(0.1)  # Let it clean up
            translator_task.cancel()
            
            try:
                await translator_task
            except asyncio.CancelledError:
                pass
            
            if DEBUG_INTERNAL_DELIBERATION:
                print("✅ Translator stopped and final pass complete")
                
                # Show stats
                if os.path.exists("data/report/sections_transformed.json"):
                    with open("data/report/sections_transformed.json", 'r') as f:
                        transformed = json.load(f)
                    print(f"📊 Total transformed sections: {len(transformed)}")
        
        if DEBUG_INTERNAL_DELIBERATION:
            print("\n" + "="*80)
            print(f"📋 FINAL EXPERT RESPONSE:")
            print("="*80)
        
        print(f"{response}")
        
        # ============================================================================
        # MARKDOWN EXPORT AND VERIFICATION
        # ============================================================================
        
        if DEBUG_INTERNAL_DELIBERATION:
            print("\n" + "="*80)
            print(f"💾 SAVING DOCUMENT AS MARKDOWN")
            print("="*80)
        
        try:
            # Get the document manager and export to markdown
            doc_manager = get_doc_manager()
            markdown_content = doc_manager.get_current_document_markdown()
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            markdown_filename = f"data/report/risk_assessment_report_{timestamp}.md"
            
            # Save markdown file
            with open(markdown_filename, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            if DEBUG_INTERNAL_DELIBERATION:
                print(f"✅ Markdown report saved to: {markdown_filename}")
                print(f"📄 Document length: {len(markdown_content)} characters")
                
                # Verify summarizer received content by checking if final response contains summary
                if len(response) > 100:  # Reasonable length check
                    print(f"✅ Summarizer appears to be working - Final response length: {len(response)} characters")
                else:
                    print(f"⚠️  Warning: Final response seems short ({len(response)} chars) - Check if summarizer is receiving content properly")
                
                # Show preview of markdown content
                preview_lines = markdown_content.split('\n')[:10]
                print(f"\n📋 MARKDOWN PREVIEW (first 10 lines):")
                print("-" * 40)
                for line in preview_lines:
                    print(line)
                if len(markdown_content.split('\n')) > 10:
                    print("... (truncated)")
                print("-" * 40)
                
        except Exception as e:
            print(f"❌ Error saving markdown: {e}")
            if DEBUG_INTERNAL_DELIBERATION:
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
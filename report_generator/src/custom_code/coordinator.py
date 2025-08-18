from __future__ import annotations

import json, regex as re  
import logging
from typing import Dict, Any, List

from langchain_openai import ChatOpenAI
from src.utils.schemas import TeamState
from src.utils.report import (
    read_current_document,
    list_sections,
    merge_section,
)
from src.utils.system_prompts import SWIFT_COORDINATOR_PROMPT

logger = logging.getLogger(__name__)


class Coordinator:
    """
    Central coordinator that manages expert selection and conversation flow.
    """

    def __init__(
        self,
        model_client: ChatOpenAI,
        experts: Dict[str, Any],
        debug: bool = False,
        tools: List[Any] | None = None,
        swift_info: str = "",
    ):
        self.experts = experts
        self.debug = debug
        self.swift_info = swift_info

        self.tools = tools or [read_current_document, list_sections, merge_section]
        # A tool-bound model for direct calls
        self.model_client = model_client.bind_tools(self.tools)

        # running counters
        self.turn_counter: int = 0          # every call to decide_next_action increments
        self.last_merge_turn: int = -1      # turn# when we last performed QC

        # store the raw system prompt (template)
        self._system_template = SWIFT_COORDINATOR_PROMPT

    # --------------------------------------------------------------------- #
    #  Main public API
    # --------------------------------------------------------------------- #
    async def decide_next_action(self, state: TeamState) -> Dict[str, Any]:
        """
        Main driver called by ExpertTeam.
        Returns a JSON-serialisable dict with keys:
          reasoning · decision · keywords · instructions
        """
        self.turn_counter += 1
        if self.debug:
            print(
                f"\n🎯 Coordinator analysing (turn {self.turn_counter} | "
                f"msg {state['message_count']}/{state['max_messages']})"
            )

        # ------------------------------------------------------------------
        #  0. Hard stop on message limit
        # ------------------------------------------------------------------
        if state["message_count"] >= state["max_messages"]:
            if self.debug:
                print("⏰ Message cap hit – forcing summarise")
            return {
                "reasoning": "Message cap reached – handing off for summary.",
                "decision": "summarize",
                "keywords": ["summary"],
                "instructions": "Create the final comprehensive report.",
            }

        # ------------------------------------------------------------------
        #  1. Every other coordinator turn → QC / merge draft sections
        # ------------------------------------------------------------------
        if (
            self.turn_counter % 2 == 0
            and self.last_merge_turn != self.turn_counter
        ):
            merge_reasoning = await self._perform_qc_merge()
            self.last_merge_turn = self.turn_counter
            # Stay in coordinator after merging
            return {
                "reasoning": merge_reasoning,
                "decision": "continue_coordinator",
            }

        # ------------------------------------------------------------------
        #  2. Normal “figure out who speaks next” flow
        # ------------------------------------------------------------------
        decision_dict = await self._ask_model_for_next_step(state)

        if self.debug:
            print(f"🧠 Decision: {decision_dict['decision']}")
            print(f"💭 Reasoning: {decision_dict['reasoning']}")
            if decision_dict.get("keywords"):
                print(f"🔑 Keywords: {decision_dict['keywords']}")

        return decision_dict

    # ===================================================================== #
    #  Internal helpers
    # ===================================================================== #
    async def _perform_qc_merge(self) -> str:
        """
        List all sections and automatically merge any still in *draft* status.
        Returns a multi-line reasoning string.
        """
        reasoning_lines: List[str] = []
        try:
            raw = await list_sections.ainvoke({})
            sections = json.loads(raw) if raw else []
        except Exception as exc:
            return f"Attempted QC but list_sections failed: {exc}"

        drafts = [s for s in sections if s.get("status") == "draft"]

        if not drafts:
            return "QC pass: no draft sections to merge."

        for sec in drafts:
            sid = sec["section_id"]
            try:
                merge_result = await merge_section.ainvoke(
                    {"section_id": sid, "notes": f"Auto-merge on turn {self.turn_counter}"}
                )
                reasoning_lines.append(f"Merged {sid}: {merge_result}")
            except Exception as exc:
                reasoning_lines.append(f"⚠️ Merge {sid} failed: {exc}")

        return "QC/merge completed:\n" + "\n".join(reasoning_lines)

    # ------------------------------------------------------------------ #
    async def _ask_model_for_next_step(self, state: TeamState) -> Dict[str, Any]:
        """
        Builds the conversation context, calls the LLM (with tools),
        then parses / validates the returned JSON.
        """
        # ---- build conversation summary -------------------------------------------------
        recent_conv = "\n".join(
            f"{m['speaker']}: {m['content']}" for m in state["messages"][-20:]
        )
        expert_status = "\n".join(
            f"- {name}: "
            + ("Contributed" if name in state["expert_responses"] else "Not consulted")
            for name in self.experts
        )

        user_prompt = f"""Original Query: {state['query']}

Current Keywords: {state.get('conversation_keywords', [])}

Expert Status:
{expert_status}

Recent Conversation:
{recent_conv}

Available Experts: {list(self.experts.keys())}

You may use the tools (read_current_document, list_sections, merge_section) for QC.
Remember: **You CANNOT create content** – only direct experts to create it.

What content is needed next, and who should create it?

Respond with valid JSON only.
"""

        system_msg = self._system_template.format(
            expert_list=", ".join(self.experts.keys()),
            swift_info=self.swift_info,
        )

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_prompt},
        ]

        # ---- first LLM call -------------------------------------------------------------
        assistant = await self.model_client.ainvoke(messages)


        # If the assistant invoked tools, execute them and get a follow-up
        content = None
        if isinstance(assistant.content, str):
            content = assistant.content
        elif isinstance(assistant.content, list):
            # GPT-5 responses API returns content as list
            # Look for text content in the list
            for item in assistant.content:
                if isinstance(item, dict) and item.get('type') == 'text':
                    content = item.get('text', '')
                    break

        # If the assistant invoked tools, execute them and get a follow-up
        if getattr(assistant, "tool_calls", None):
            follow_json = await self._handle_tool_phase(
                messages, assistant, system_msg
            )
        elif content:
            follow_json = self._safe_json_from_text(content)
        else:
            # No text content but no tools either - shouldn't happen normally
            logger.warning(f"No text content or tools in response")
            follow_json = {
                "reasoning": "Processing coordinator decision",
                "decision": "continue_coordinator",
                "keywords": state.get("conversation_keywords", []),
            }


        # ---- sanity-fill missing fields -------------------------------------------------
        follow_json.setdefault("keywords", state.get("conversation_keywords", []))
        if follow_json["decision"] not in ("continue_coordinator", "summarize", "end"):
            follow_json.setdefault(
                "instructions",
                "Please produce the requested content with clear argument chains.",
            )

        return follow_json

    # ------------------------------------------------------------------ #
    async def _handle_tool_phase(
        self, base_msgs: List[dict], assistant_msg, system_msg: str
    ) -> Dict[str, Any]:
        """
        Execute each tool call and then ask the model for its JSON decision.
        Uses **all-dict** messages to stay homogeneous.
        """
        tool_msgs: List[dict] = base_msgs[:]
        content = ""
        if isinstance(assistant_msg.content, str):
            content = assistant_msg.content
        elif isinstance(assistant_msg.content, list):
            for item in assistant_msg.content:
                if isinstance(item, dict) and item.get('type') == 'text':
                    content = item.get('text', '')
                    break

        # Append assistant call as dict
        tool_msgs.append(
            {
                "role": "assistant",
                "content": content,  # This might be empty for tool calls
                "tool_calls": assistant_msg.tool_calls,
            }
        )


        # Execute each tool
        for tc in assistant_msg.tool_calls:
            tool_fn = next((t for t in self.tools if t.name == tc["name"]), None)
            if not tool_fn:
                tool_msgs.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": f"Error: tool {tc['name']} not found",
                    }
                )
                continue
            try:
                result = await tool_fn.ainvoke(tc["args"])
            except Exception as exc:
                result = f"Error executing tool: {exc}"
            tool_msgs.append(
                {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": str(result),
                }
            )

        # Ask for final JSON decision – allow successive tool calls
        follow_prompt = (
            "Based on the tool results above, provide your decision in **JSON only** "
            "with keys: reasoning · decision · keywords · instructions."
        )
        tool_msgs.append({"role": "user", "content": follow_prompt})

        # Loop to support multiple assistant→tool rounds until we finally get JSON text
        max_tool_rounds = 5  # safety guard to avoid infinite loops
        rounds = 0
        while rounds < max_tool_rounds:
            rounds += 1
            follow = await self.model_client.ainvoke(tool_msgs)
            follow_content = ""
            if isinstance(follow.content, str):
                follow_content = follow.content
            elif isinstance(follow.content, list):
                for item in follow.content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        follow_content = item.get('text', '')
                        break

            # Record assistant reply
            tool_msgs.append(
                {
                    "role": "assistant",
                    "content": follow_content,
                    "tool_calls": getattr(follow, "tool_calls", None),
                }
            )


            if getattr(follow, "tool_calls", None):
                # Execute each subsequent tool call
                for tc in follow.tool_calls:
                    tool_fn = next((t for t in self.tools if t.name == tc["name"]), None)
                    if not tool_fn:
                        tool_msgs.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": f"Error: tool {tc['name']} not found",
                            }
                        )
                        continue
                    try:
                        result = await tool_fn.ainvoke(tc["args"])
                    except Exception as exc:
                        result = f"Error executing tool: {exc}"
                    tool_msgs.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": str(result),
                        }
                    )
                # After executing tools, continue loop to ask again for JSON decision
                tool_msgs.append({"role": "user", "content": follow_prompt})
                continue
            # Assistant returned no tool calls – expect JSON content
            if follow_content:
                return self._safe_json_from_text(follow_content)
            else:
                # No content, return a default
                logger.warning("No text content in tool follow-up response")
                return {
                    "reasoning": "Proceeding with assessment",
                    "decision": "continue_coordinator",
                    "keywords": [],
                }


        # If we exit loop without return, raise descriptive error
        raise RuntimeError("Exceeded maximum successive tool rounds without JSON response")

    # ------------------------------------------------------------------ #
    @staticmethod
    def _safe_json_from_text(txt: str):
        """
        Return the first JSON object found in txt.
        Raises ValueError if none can be parsed.
        """
        match = re.search(r"\{(?:[^{}]|(?R))*\}", txt, re.S)
        if not match:
            raise ValueError(f"No JSON object found\n---RAW---\n{txt}\n---")
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Could not parse JSON: {exc}\n---RAW---\n{txt}\n---") from exc
from langchain_openai import ChatOpenAI
from typing import List, Any
from src.utils.memory import LobeVectorMemory
import json
import logging

logger = logging.getLogger(__name__) # Do I need this?

class Lobe:
    """Updated Lobe class using current LangChain APIs"""
    
    def __init__(
        self,
        name: str,
        model_client: ChatOpenAI,
        vector_memory: LobeVectorMemory,
        keywords: List[str] = None,
        temperature: float = 0.7,
        system_message: str = None,
        tools: List[Any] = None
    ):
        self.name = name
        
        # Create a new model client with specified temperature
        # self.model_client = ChatOpenAI(
        #     model=model_client.model_name,
        #     temperature=temperature,
        #     api_key=model_client.openai_api_key if hasattr(model_client, 'openai_api_key') else None
        # )
        self.model_client = model_client
        
        self.vector_memory = vector_memory
        self.keywords = keywords or []
        self.tools = tools or []
        self._base_system_message = system_message or "You are a helpful AI assistant."
        self._system_message = self._base_system_message
        self._initialized = False
    
    async def initialize_context(self):
        """Initialize context from keywords using current API"""
        if not self.keywords or self._initialized:
            return
            
        results = await self.vector_memory.search_by_keywords(self.keywords)
        if not results:
            context = f"Initial keywords: {', '.join(self.keywords)}"
        else:
            context_parts = [f"Relevant context for keywords [{', '.join(self.keywords)}]:"]
            
            # Take top 6 results and enumerate starting from 1
            for i, result in enumerate(results[:6], 1):
                context_parts.append(f"{i}. {result['content']}")
                
                # Optionally include relevance score
                if 'score' in result:
                    context_parts[-1] += f" (relevance: {result['score']:.2f})"
            
            context = "\n".join(context_parts)
        
        self._system_message = f"{self._base_system_message}\n\n{context}"
        self._initialized = True

    
    async def query_common_db(self, keywords: List[str], top_k: int = 5) -> str:
        """Query the vector database using current API"""
        try:
            original_k = self.vector_memory.config.k
            self.vector_memory.config.k = top_k
            
            results = await self.vector_memory.search_by_keywords(keywords)
            
            self.vector_memory.config.k = original_k
            
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "content": result["content"],
                    "score": result["metadata"].get('score', 0),
                    "metadata": {k: v for k, v in result["metadata"].items() if k not in ['score', 'id']}
                })
            
            return json.dumps({
                "query": keywords,
                "results": formatted_results,
                "count": len(formatted_results)
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Error querying database: {e}")
            return json.dumps({
                "error": str(e),
                "query": keywords,
                "results": []
            })
    
    async def respond(self, query: str, context: str = "") -> str:
        """Generate response using current LangChain API"""
        await self.initialize_context()
        
        # Create messages in the format expected by current ChatOpenAI
        messages = [
            {"role": "system", "content": self._system_message},
            {"role": "user", "content": f"Context: {context}\n\nQuery: {query}"}
        ]
        
        try:
            # If tools are available, bind them to the model
            if self.tools:
                model_with_tools = self.model_client.bind_tools(self.tools)
                response = await model_with_tools.ainvoke(messages)
                
                # Handle tool calls if present
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    # Execute tool calls
                    tool_results = []
                    for tool_call in response.tool_calls:
                        # Find the tool by name
                        tool_func = None
                        for tool in self.tools:
                            if tool.name == tool_call['name']:
                                tool_func = tool
                                break
                        
                        if tool_func:
                            try:
                                result = await tool_func.ainvoke(tool_call['args'])
                                tool_results.append(f"Tool {tool_call['name']} called with args {tool_call['args']}\nResult: {result}")
                            except Exception as e:
                                tool_results.append(f"Tool {tool_call['name']} error: {str(e)}")
                    
                    # Return both the response and tool results
                    combined_response = "\n\n".join(tool_results)
                    if response.content: # add the text
                        combined_response += f"\n\n{response.content}"
                    
                    return combined_response
                else:
                    return response.content
            else:
                # No tools, use regular invoke
                response = await self.model_client.ainvoke(messages)
                return response.content
        except Exception as e:
            logger.error(f"Error in lobe response: {e}")
            return f"Error generating response: {str(e)}"
    
    async def update_keywords(self, keywords: List[str]):
        """Update keywords and refresh context"""
        self.keywords = keywords
        self._initialized = False
        await self.initialize_context()
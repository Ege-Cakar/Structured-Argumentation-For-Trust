import asyncio
import json
import os
from typing import Dict, Any, Set, Optional
from datetime import datetime
from pathlib import Path
import logging
from langchain_openai import ChatOpenAI
import hashlib

logger = logging.getLogger(__name__)

class AsyncSectionTransformer:
    """
    Asynchronously monitors sections.json and transforms content
    using the translator prompt, saving to sections_transformed.json
    """
    
    def __init__(
        self,
        sections_path: str = "data/report/sections.json",
        output_path: str = "data/report/sections_transformed.json",
        system_prompt_template: str = None,
        original_query: str = "",
        poll_interval: float = 2.0,  # Check every 2 seconds
        model_name: str = "gpt-5",
        debug: bool = False
    ):
        self.sections_path = sections_path
        self.output_path = output_path
        self.system_prompt_template = system_prompt_template
        self.original_query = original_query
        self.poll_interval = poll_interval
        self.debug = debug
        self._running = False
        self._processed_hashes: Set[str] = set()
        
        # Ensure output file exists and is clean for this run
        try:
            output_dir = Path(self.output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            with open(self.output_path, 'w') as f:
                json.dump({}, f, indent=2)
            if self.debug:
                print(f"🆕 Initialized clean output at {self.output_path}")
        except Exception as e:
            logger.warning(f"Could not initialize output file {self.output_path}: {e}")
        
        # Initialize transformer model with conservative settings
        self.transformer = ChatOpenAI(
            model=model_name,
            use_responses_api=True,
            reasoning={"effort": "high"},
            text={"verbosity": "low"},
            output_version="responses/v1",
        )
        
        # Load existing transformed sections if they exist
        self._load_existing_transformed()
    
    def _load_existing_transformed(self):
        """Load already transformed sections to avoid reprocessing"""
        if os.path.exists(self.output_path):
            try:
                with open(self.output_path, 'r') as f:
                    existing = json.load(f)
                    # Track which sections we've already processed
                    for section_id, section in existing.items():
                        if 'content_hash' in section:
                            self._processed_hashes.add(section['content_hash'])
            except Exception as e:
                logger.warning(f"Could not load existing transformed sections: {e}")
    
    def _get_content_hash(self, content: str) -> str:
        """Generate hash of content to detect changes"""
        return hashlib.md5(content.encode()).hexdigest()
    
    async def transform_section(self, section_id: str, section: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single section's content"""
        try:
            content = section.get('content', '')
            content_hash = self._get_content_hash(content)
            
            # Skip if already processed
            if content_hash in self._processed_hashes:
                return None
            
            # Prepare the system prompt with filled variables
            system_prompt = self.system_prompt_template.format(
                original_query=self.original_query,
                source_expert_name=section.get('author', 'Unknown Expert'),
                content_to_transform=content
            )
            
            if self.debug:
                print(f"\n🔄 Transforming section: {section_id}")
                print(f"   Author: {section.get('author', 'Unknown')}")
                print(f"   Domain: {section.get('domain', 'Unknown')}")
            
            # Call the transformer
            response = await self.transformer.ainvoke([
                {"role": "system", "content": system_prompt}
            ])
            
            transformed_content = response.content
            
            # Create transformed section with same structure but new content
            transformed_section = {
                **section,  # Keep all original metadata
                'content': transformed_content,
                'content_hash': content_hash,
                'original_content_length': len(content),
                'transformed_content_length': len(transformed_content),
                'transformed_at': datetime.now().isoformat()
            }
            
            # Mark as processed
            self._processed_hashes.add(content_hash)
            
            if self.debug:
                print(f"   ✅ Transformed: {len(content)} → {len(transformed_content)} chars")
            
            return transformed_section
            
        except Exception as e:
            logger.error(f"Error transforming section {section_id}: {e}")
            if self.debug:
                print(f"   ❌ Transform failed: {e}")
            return None
    
    async def check_and_transform(self):
        """Check for new/updated sections and transform them"""
        if not os.path.exists(self.sections_path):
            return
        
        try:
            # Load current sections
            with open(self.sections_path, 'r') as f:
                sections = json.load(f)
            
            if not sections:
                return
            
            # Load existing transformed sections
            transformed_sections = {}
            if os.path.exists(self.output_path):
                with open(self.output_path, 'r') as f:
                    transformed_sections = json.load(f)
            
            # Process each section
            updates_made = False
            for section_id, section in sections.items():
                # Only process merged sections (not draft/empty)
                if section.get('status') != 'merged':
                    continue
                
                # Transform if needed
                transformed = await self.transform_section(section_id, section)
                
                if transformed:
                    transformed_sections[section_id] = transformed
                    updates_made = True
            
            # Save updated transformations
            if updates_made:
                with open(self.output_path, 'w') as f:
                    json.dump(transformed_sections, f, indent=2)
                
                if self.debug:
                    print(f"💾 Saved {len(transformed_sections)} transformed sections")
                    
        except Exception as e:
            logger.error(f"Error in check_and_transform: {e}")
    
    async def run(self):
        """Main async loop to monitor and transform sections"""
        self._running = True
        
        if self.debug:
            print(f"\n🚀 Section Transformer Started")
            print(f"   Monitoring: {self.sections_path}")
            print(f"   Output: {self.output_path}")
            print(f"   Poll interval: {self.poll_interval}s")
            print("="*60)
        
        while self._running:
            try:
                await self.check_and_transform()
                await asyncio.sleep(self.poll_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Transformer loop error: {e}")
                await asyncio.sleep(self.poll_interval)
        
        if self.debug:
            print("\n🛑 Section Transformer Stopped")
    
    def stop(self):
        """Stop the transformer"""
        self._running = False
    
    async def transform_all_final(self):
        """
        Do a final transformation pass on all sections.
        Useful after team completes to ensure everything is transformed.
        """
        if self.debug:
            print("\n🏁 Running final transformation pass...")
        
        # Clear processed hashes to force reprocess
        original_hashes = self._processed_hashes.copy()
        self._processed_hashes.clear()
        
        await self.check_and_transform()
        
        # Restore hashes
        self._processed_hashes = original_hashes
        
        if self.debug:
            print("✅ Final transformation complete")
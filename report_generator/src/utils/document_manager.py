from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
import json
import uuid
from enum import Enum
import os 
from pathlib import Path 

class SectionStatus(Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    MERGED = "merged"

@dataclass
class Section:
    section_id: str
    domain: str
    author: str
    content: str
    version: int = 1
    status: SectionStatus = SectionStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    parent_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DocumentChange:
    change_id: str
    section_id: str
    author: str
    change_type: Literal["create", "edit", "merge", "approve"]
    content_before: Optional[str] = None
    content_after: Optional[str] = None
    rationale: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

class DocumentManager:
    def __init__(self, base_path: str = "data/report"):
        self.base_path = base_path
        self.sections: Dict[str, Section] = {}
        self.history: List[DocumentChange] = []
        self.current_document: List[Tuple[str, str, int]] = []  


        # Create directory if it doesn't exist
        Path(self.base_path).mkdir(parents=True, exist_ok=True)
        
        # Load existing data if available
        self._load_from_disk()
        
    def create_section(self, domain: str, author: str, content: str) -> str:
        """Create a new draft section"""
        content = content.rstrip() + "\n"
        section_id = f"{domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        section = Section(
            section_id=section_id,
            domain=domain,
            author=author,
            content=content
        )
        self.sections[section_id] = section
        
        change = DocumentChange(
            change_id=uuid.uuid4().hex,
            section_id=section_id,
            author=author,
            change_type="create",
            content_after=content
        )
        self.history.append(change)

        self.save_to_disk()
        
        return section_id
    
    def propose_edit(self, section_id: str, author: str, new_content: str, rationale: str) -> str:
        """Propose an edit to existing section (creates new version)"""
        if section_id not in self.sections:
            raise ValueError(f"Section {section_id} not found")
        new_content = new_content.rstrip() + "\n"
            
        original = self.sections[section_id]
        new_version_id = f"{original.domain}_v{original.version + 1}_{datetime.now().strftime('%H%M%S')}"
        
        new_section = Section(
            section_id=new_version_id,
            domain=original.domain,
            author=author,
            content=new_content,
            version=original.version + 1,
            parent_version=section_id,
            metadata={"rationale": rationale}
        )
        self.sections[new_version_id] = new_section
        
        change = DocumentChange(
            change_id=uuid.uuid4().hex,
            section_id=new_version_id,
            author=author,
            change_type="edit",
            content_before=original.content,
            content_after=new_content,
            rationale=rationale
        )
        self.history.append(change)
        self.save_to_disk()        
        return new_version_id
    
    def merge_to_document(self, section_id: str, coordinator_notes: str = "") -> bool:
        """Merge approved section into main document"""
        if section_id not in self.sections:
            return False
            
        section = self.sections[section_id]

        if section.version <= self._latest_version(section.domain):
            raise ValueError(f"Cannot merge older version {section.version} "
                             f"after v{self._latest_version(section.domain)}")  

        section.status = SectionStatus.MERGED
        section.updated_at = datetime.now()
        
        self.current_document.append((section.domain, section_id, section.version))
        
        change = DocumentChange(
            change_id=uuid.uuid4().hex,
            section_id=section_id,
            author="coordinator",
            change_type="merge",
            rationale=coordinator_notes
        )
        self.history.append(change)

        self.save_to_disk()
        
        return True
    
    def get_current_document_markdown(self) -> str:
        parts = [
            "# Risk Assessment Report\n",
            f"_Generated {datetime.now():%Y-%m-%d %H:%M:%S}_\n\n"
        ]

        # Fallback: if current_document is empty, derive order from all MERGED sections
        entries = self.current_document
        if len(entries) == 0:
            # sort by updated_at to maintain logical flow
            merged_sections = [s for s in self.sections.values() if s.status == SectionStatus.MERGED]
            merged_sections.sort(key=lambda s: s.updated_at)
            entries = [(s.domain, s.section_id, s.version) for s in merged_sections]

        for domain, sid, ver in entries:
            sec = self.sections[sid]
            parts.extend([
                f"## {domain.replace('_', ' ').title()}  \n",
                f"*Version {ver} • Author: {sec.author} • Section ID: {sid}*\n\n",
                sec.content.rstrip(),  # strip dangling whitespace
                "\n\n",
            ])
        return "".join(parts)

    def _latest_version(self, domain: str) -> int:
        for dom, _, ver in reversed(self.current_document):
            if dom == domain:
                return ver
        return 0
    
    def _section_to_dict(self, section: Section) -> Dict[str, Any]:
        """Convert Section to dictionary for JSON serialization"""
        return {
            "section_id": section.section_id,
            "domain": section.domain,
            "author": section.author,
            "content": section.content,
            "version": section.version,
            "status": section.status.value,
            "created_at": section.created_at.isoformat(),
            "updated_at": section.updated_at.isoformat(),
            "parent_version": section.parent_version,
            "metadata": section.metadata
        }
    
    def _dict_to_section(self, data: Dict[str, Any]) -> Section:
        """Convert dictionary to Section object"""
        return Section(
            section_id=data["section_id"],
            domain=data["domain"],
            author=data["author"],
            content=data["content"],
            version=data["version"],
            status=SectionStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            parent_version=data.get("parent_version"),
            metadata=data.get("metadata", {})
        )
    
    def _change_to_dict(self, change: DocumentChange) -> Dict[str, Any]:
        """Convert DocumentChange to dictionary for JSON serialization"""
        return {
            "change_id": change.change_id,
            "section_id": change.section_id,
            "author": change.author,
            "change_type": change.change_type,
            "content_before": change.content_before,
            "content_after": change.content_after,
            "rationale": change.rationale,
            "timestamp": change.timestamp.isoformat()
        }
    
    def _dict_to_change(self, data: Dict[str, Any]) -> DocumentChange:
        """Convert dictionary to DocumentChange object"""
        return DocumentChange(
            change_id=data["change_id"],
            section_id=data["section_id"],
            author=data["author"],
            change_type=data["change_type"],
            content_before=data.get("content_before"),
            content_after=data.get("content_after"),
            rationale=data.get("rationale"),
            timestamp=datetime.fromisoformat(data["timestamp"])
        )
    
    def save_to_disk(self):
        """Save current state to JSON files"""
        # Save sections
        sections_data = {
            sid: self._section_to_dict(section) 
            for sid, section in self.sections.items()
        }
        with open(os.path.join(self.base_path, "sections.json"), "w") as f:
            json.dump(sections_data, f, indent=2)
        
        # Save history
        history_data = [self._change_to_dict(change) for change in self.history]
        with open(os.path.join(self.base_path, "history.json"), "w") as f:
            json.dump(history_data, f, indent=2)
        
        # Save current document
        with open(os.path.join(self.base_path, "current_document.json"), "w") as f:
            json.dump(self.current_document, f, indent=2)
        
        # Also save markdown version
        with open(os.path.join(self.base_path, "report.md"), "w") as f:
            f.write(self.get_current_document_markdown())
    
    def _load_from_disk(self):
        """Load state from JSON files if they exist"""
        # Load sections
        sections_file = os.path.join(self.base_path, "sections.json")
        if os.path.exists(sections_file):
            with open(sections_file, "r") as f:
                sections_data = json.load(f)
                self.sections = {
                    sid: self._dict_to_section(data) 
                    for sid, data in sections_data.items()
                }
        
        # Load history
        history_file = os.path.join(self.base_path, "history.json")
        if os.path.exists(history_file):
            with open(history_file, "r") as f:
                history_data = json.load(f)
                self.history = [self._dict_to_change(data) for data in history_data]
        
        # Load current document
        current_doc_file = os.path.join(self.base_path, "current_document.json")
        if os.path.exists(current_doc_file):
            with open(current_doc_file, "r") as f:
                self.current_document = json.load(f)

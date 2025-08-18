from langchain_core.tools import tool
from typing import Annotated, Optional
from src.utils.document_manager import DocumentManager, SectionStatus
import json

# Global document manager instance
_doc_manager = None

def get_doc_manager() -> DocumentManager:
    global _doc_manager
    if _doc_manager is None:
        _doc_manager = DocumentManager()
    return _doc_manager

@tool
def create_section(
    domain: Annotated[str, "Domain/topic of this section (e.g., 'authentication_risks')"],
    content: Annotated[str, "Markdown content for this section"],
    author: Annotated[str, "Name of the expert authoring this section"]
) -> str:
    """Create a new draft section for the risk assessment"""
    manager = get_doc_manager()
    section_id = manager.create_section(domain, author, content)
    return f"Created draft section {section_id} for {domain}"

@tool
def propose_edit(
    section_id: Annotated[str, "ID of section to edit"],
    new_content: Annotated[str, "Proposed new content"],
    rationale: Annotated[str, "Reason for the edit"],
    author: Annotated[str, "Name of the expert proposing edit"]
) -> str:
    """Propose an edit to an existing section"""
    manager = get_doc_manager()
    new_version_id = manager.propose_edit(section_id, author, new_content, rationale)
    return f"Created edit proposal {new_version_id} for section {section_id}"

@tool
def read_section(
    section_id: Annotated[str, "ID of specific section to read"]
) -> str:
    """Read a specific section by ID"""
    manager = get_doc_manager()
    if section_id in manager.sections:
        section = manager.sections[section_id]
        return json.dumps({
            "section_id": section_id,
            "domain": section.domain,
            "author": section.author,
            "content": section.content,
            "status": section.status.value,
            "version": section.version
        }, indent=2)
    return f"Section {section_id} not found"

@tool
def list_sections(
    domain: Optional[Annotated[str, "Filter by domain"]] = None,
    status: Optional[Annotated[str, "Filter by status"]] = None
) -> str:
    """List all sections, optionally filtered"""
    manager = get_doc_manager()
    sections = []
    
    for section in manager.sections.values():
        if domain and section.domain != domain:
            continue
        if status and section.status.value != status:
            continue
            
        sections.append({
            "section_id": section.section_id,
            "domain": section.domain,
            "author": section.author,
            "status": section.status.value,
            "version": section.version,
            "created_at": section.created_at.isoformat()
        })
    
    return json.dumps(sections, indent=2)

@tool
def read_current_document() -> str:
    """Read the current merged document"""
    manager = get_doc_manager()
    return manager.get_current_document_markdown()

@tool
def merge_section(
    section_id: Annotated[str, "Section ID to merge"],
    notes: Annotated[str, "Coordinator notes about the merge"] = ""
) -> str:
    """Merge an approved section into the main document (Coordinator only)"""
    manager = get_doc_manager()
    try:
        if manager.merge_to_document(section_id, notes):
            return f"Successfully merged section {section_id} into main document"
        return f"Failed to merge section {section_id}"
    except Exception as exc:
        return f"Failed to merge section {section_id}: {exc}"

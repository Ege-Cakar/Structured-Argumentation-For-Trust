from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from typing import List, Dict, Any, Optional, Set
import os
import hashlib
from pathlib import Path
import logging
from datetime import datetime
import json

# PDF support
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("PyPDF2 not available. Install with: pip install PyPDF2")

logger = logging.getLogger(__name__)

class TextChunker:
    """Simple text chunker for large documents"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str, base_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks"""
        if not text or len(text.strip()) == 0:
            return []
        
        # If text is small, return as single chunk
        if len(text) <= self.chunk_size:
            return [{
                "content": text,
                "metadata": {
                    **(base_metadata or {}),
                    "chunk_index": 0,
                    "total_chunks": 1
                }
            }]
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            # Find end position
            end = min(start + self.chunk_size, len(text))
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end
                for i in range(end - 1, max(start + self.chunk_size - 200, start), -1):
                    if text[i] in '.!?' and i + 1 < len(text) and text[i + 1].isspace():
                        end = i + 1
                        break
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    "content": chunk_text,
                    "metadata": {
                        **(base_metadata or {}),
                        "chunk_index": chunk_index,
                        "chunk_start": start,
                        "chunk_end": end
                    }
                })
                chunk_index += 1
            
            # Move start with overlap
            start = max(start + 1, end - self.chunk_overlap)
        
        # Update total chunks
        for chunk in chunks:
            chunk["metadata"]["total_chunks"] = len(chunks)
        
        return chunks

class LobeVectorMemory:
    """Vector memory with chunking and deduplication"""
    
    def __init__(self, embeddings=None, persist_directory="./data/vectordb", 
                 chunk_size=1000, chunk_overlap=200, enable_chunking=True):
        self.embeddings = embeddings or OpenAIEmbeddings(model="text-embedding-3-large")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.enable_chunking = enable_chunking
        
        # Initialize chunker
        self.chunker = TextChunker(chunk_size, chunk_overlap)
        
        # Use current Chroma API
        self.vectorstore = Chroma(
            collection_name="lobe_memory",
            embedding_function=self.embeddings,
            persist_directory=persist_directory
        )
        self.retriever = self.vectorstore.as_retriever()
        self.config = type('Config', (), {'k': 5})()
    
    async def search_by_keywords(self, keywords: List[str], deduplicate=True) -> List[Dict[str, Any]]:
        """Search by keywords with optional source deduplication"""
        query = " ".join(keywords)
        
        # Get more results than k to account for deduplication
        search_k = self.config.k * 3 if deduplicate else self.config.k
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": search_k})
        
        # Use invoke instead of deprecated get_relevant_documents
        docs = await self.retriever.ainvoke(query) if hasattr(self.retriever, 'ainvoke') else self.retriever.invoke(query)
        
        results = []
        seen_sources = set()
        
        for doc in docs:
            # If deduplicating, check if we've seen this source
            if deduplicate:
                source = doc.metadata.get('source', doc.metadata.get('filename', ''))
                if source in seen_sources:
                    continue
                seen_sources.add(source)
            
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": doc.metadata.get('score', 1.0)
            })
            
            # Stop when we have enough unique results
            if len(results) >= self.config.k:
                break
        
        return results
    
    async def add(self, content: str, metadata: Dict[str, Any] = None):
        """Add content with optional chunking"""
        metadata = metadata or {}
        
        # If chunking is enabled and content is large
        if self.enable_chunking and len(content) > self.chunk_size:
            chunks = self.chunker.chunk_text(content, metadata)
            
            # Add all chunks
            docs = []
            for chunk in chunks:
                doc = Document(
                    page_content=chunk["content"],
                    metadata=chunk["metadata"]
                )
                docs.append(doc)
            
            if docs:
                self.vectorstore.add_documents(docs)
                logger.info(f"Added {len(docs)} chunks from source: {metadata.get('source', 'unknown')}")
        else:
            # Add as single document
            doc = Document(page_content=content, metadata=metadata)
            self.vectorstore.add_documents([doc])
    
    def _generate_file_hash(self, filepath: str) -> str:
        """Generate hash of file content"""
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    async def file_exists(self, file_hash: str) -> bool:
        """Check if file with this hash exists"""
        # Search for the file hash
        results = self.vectorstore.similarity_search(
            query="",  # Empty query
            k=1,
            filter={"file_hash": file_hash}
        )
        return len(results) > 0
    
    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF"""
        if not PDF_AVAILABLE:
            logger.warning(f"Cannot process PDF {file_path} - PyPDF2 not installed")
            return ""
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                # Check if encrypted
                if pdf_reader.is_encrypted:
                    try:
                        pdf_reader.decrypt("")
                    except:
                        logger.warning(f"Cannot decrypt PDF: {file_path}")
                        return ""
                
                # Extract text from all pages
                for page_num in range(len(pdf_reader.pages)):
                    try:
                        page = pdf_reader.pages[page_num]
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as e:
                        logger.error(f"Error extracting page {page_num}: {e}")
                        continue
                
                return text.strip()
                
        except Exception as e:
            logger.error(f"Error reading PDF {file_path}: {e}")
            return ""
    
    async def add_folder(self, folder_path: str, file_extensions: List[str] = None,
                        force_reprocess: bool = False) -> Dict[str, Any]:
        """Add all files from folder with deduplication"""
        if file_extensions is None:
            file_extensions = ['.txt', '.md', '.pdf']
        
        folder = Path(folder_path)
        if not folder.exists():
            raise ValueError(f"Folder {folder_path} does not exist")
        
        stats = {
            "processed": 0,
            "added": 0,
            "skipped": 0,
            "errors": 0,
            "already_processed": 0,
            "files": []
        }
        
        # Get already processed files
        processed_hashes = set()
        if not force_reprocess:
            # Query to get all file hashes
            all_docs = self.vectorstore.similarity_search("", k=10000)  # Get many
            for doc in all_docs:
                if 'file_hash' in doc.metadata:
                    processed_hashes.add(doc.metadata['file_hash'])
            logger.info(f"Found {len(processed_hashes)} already processed files")
        
        for file_path in folder.rglob('*'):  # Recursive glob
            if file_path.is_file() and file_path.suffix in file_extensions:
                stats["processed"] += 1
                
                try:
                    # Generate hash
                    file_hash = self._generate_file_hash(str(file_path))
                    
                    # Check if already processed
                    if file_hash in processed_hashes and not force_reprocess:
                        logger.info(f"Skipping already processed: {file_path.name}")
                        stats["already_processed"] += 1
                        continue
                    
                    # Read content based on file type
                    content = ""
                    if file_path.suffix.lower() == '.pdf':
                        content = self._extract_pdf_text(str(file_path))
                    else:
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                        except UnicodeDecodeError:
                            with open(file_path, 'r', encoding='latin-1') as f:
                                content = f.read()
                    
                    if not content or not content.strip():
                        logger.warning(f"Empty file: {file_path.name}")
                        stats["skipped"] += 1
                        continue
                    
                    # Prepare metadata
                    metadata = {
                        "source": str(file_path),
                        "filename": file_path.name,
                        "file_hash": file_hash,
                        "file_type": file_path.suffix,
                        "file_size": file_path.stat().st_size,
                        "added_date": datetime.now().isoformat()
                    }
                    
                    # Add to vector store
                    await self.add(content, metadata)
                    logger.info(f"Added: {file_path.name}")
                    stats["added"] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing {file_path.name}: {e}")
                    stats["errors"] += 1
        
        logger.info(
            f"Processing complete: "
            f"Added {stats['added']}, "
            f"Already processed {stats['already_processed']}, "
            f"Skipped {stats['skipped']}, "
            f"Errors {stats['errors']}"
        )
        
        return stats

async def initialize_database():
    vector_memory = LobeVectorMemory(persist_directory="./data/vectordb")
    
    # Add files from a folder
    stats = await vector_memory.add_folder(
        folder_path="data/database",
        file_extensions=['.txt', '.md', '.pdf']
    )
    
    print(f"Database initialized: {stats['added']} files added, {stats['skipped']} skipped")

    return vector_memory
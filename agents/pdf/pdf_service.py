from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import base64
import io
from pdfminer.high_level import extract_text
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from common.security import verify_token
from common.logging import logger
from common.models import PDFUploadRequest, PDFAnalysisResponse
from model.courtlistener_client import courtlistener_client
from model.issue_extractor import extract_issues
from agents.citation.citation_service import citation_extractor
from typing import Dict, Any, List
import re
import os
from datetime import datetime

app = FastAPI(title="PDF Analysis Service")

class PDFProcessor:
    """Enhanced PDF processing for legal documents"""
    
    def __init__(self):
        self.max_file_size = 10 * 1024 * 1024  # 10MB limit
        self.supported_formats = ['.pdf']
    
    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF content"""
        try:
            # Method 1: Using pdfminer.high_level (faster for simple PDFs)
            try:
                text = extract_text(io.BytesIO(pdf_content))
                if text and len(text.strip()) > 100:
                    return self._clean_text(text)
            except Exception as e:
                logger.warning(f"High-level extraction failed: {e}")
            
            # Method 2: Using pdfminer with more control (for complex PDFs)
            try:
                text = self._extract_text_detailed(pdf_content)
                if text and len(text.strip()) > 100:
                    return self._clean_text(text)
            except Exception as e:
                logger.error(f"Detailed extraction failed: {e}")
            
            return ""
            
        except Exception as e:
            logger.error(f"PDF text extraction error: {e}")
            return ""
    
    def _extract_text_detailed(self, pdf_content: bytes) -> str:
        """Extract text using detailed pdfminer approach"""
        resource_manager = PDFResourceManager()
        fake_file_handle = io.StringIO()
        converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
        page_interpreter = PDFPageInterpreter(resource_manager, converter)
        
        pages = PDFPage.get_pages(io.BytesIO(pdf_content), caching=True, check_extractable=True)
        
        text = ""
        for page in pages:
            page_interpreter.process_page(page)
            text += fake_file_handle.getvalue()
        
        converter.close()
        fake_file_handle.close()
        
        return text
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers and headers/footers
        text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
        
        # Remove excessive punctuation
        text = re.sub(r'[.]{3,}', '...', text)
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        return text.strip()
    
    def analyze_legal_document(self, text: str) -> Dict[str, Any]:
        """Analyze legal document and extract key information"""
        if not text or len(text.strip()) < 100:
            return {
                "success": False,
                "error": "Insufficient text content"
            }
        
        try:
            # Extract case information
            case_info = self._extract_case_info(text)
            
            # Extract legal issues
            issues = extract_issues(text)
            
            # Extract citations
            citations = citation_extractor.extract_citations_from_text(text)
            
            # Extract key legal terms
            legal_terms = self._extract_legal_terms(text)
            
            # Extract parties
            parties = self._extract_parties(text)
            
            # Extract court information
            court_info = self._extract_court_info(text)
            
            # Extract dates
            dates = self._extract_dates(text)
            
            return {
                "success": True,
                "case_info": case_info,
                "issues": issues,
                "citations": citations,
                "legal_terms": legal_terms,
                "parties": parties,
                "court_info": court_info,
                "dates": dates,
                "text_length": len(text),
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing legal document: {e}")
            return {
                "success": False,
                "error": f"Analysis failed: {str(e)}"
            }
    
    def _extract_case_info(self, text: str) -> Dict[str, Any]:
        """Extract case information from text"""
        case_info = {}
        
        # Extract case name (look for "v." pattern)
        case_pattern = r'([A-Z][a-zA-Z\s,&\']+)\s+v\.\s+([A-Z][a-zA-Z\s,&\']+)'
        case_match = re.search(case_pattern, text[:1000])
        if case_match:
            case_info["case_name"] = f"{case_match.group(1)} v. {case_match.group(2)}"
        
        # Extract docket number
        docket_pattern = r'(?:Docket|Case)\s+(?:No\.|Number)\s*:?\s*([A-Z0-9\-\.]+)'
        docket_match = re.search(docket_pattern, text, re.IGNORECASE)
        if docket_match:
            case_info["docket_number"] = docket_match.group(1)
        
        return case_info
    
    def _extract_legal_terms(self, text: str) -> List[str]:
        """Extract key legal terms"""
        legal_terms = []
        
        # Common legal terms
        term_patterns = [
            r'\b(?:plaintiff|defendant|appellant|appellee)\b',
            r'\b(?:motion|petition|complaint|answer)\b',
            r'\b(?:judgment|ruling|decision|opinion)\b',
            r'\b(?:appeal|reversal|affirmance)\b',
            r'\b(?:injunction|restraining order)\b',
            r'\b(?:damages|compensation|remedy)\b',
            r'\b(?:liability|negligence|breach)\b',
            r'\b(?:constitutional|statutory|regulatory)\b'
        ]
        
        for pattern in term_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            legal_terms.extend(matches)
        
        return list(set(legal_terms))
    
    def _extract_parties(self, text: str) -> List[str]:
        """Extract party names"""
        parties = []
        
        # Look for party patterns
        party_patterns = [
            r'(?:Plaintiff|Petitioner|Appellant)\s*:?\s*([A-Z][a-zA-Z\s,&\']+)',
            r'(?:Defendant|Respondent|Appellee)\s*:?\s*([A-Z][a-zA-Z\s,&\']+)'
        ]
        
        for pattern in party_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            parties.extend(matches)
        
        return list(set(parties))
    
    def _extract_court_info(self, text: str) -> Dict[str, str]:
        """Extract court information"""
        court_info = {}
        
        # Court patterns
        court_patterns = [
            r'([A-Z][a-zA-Z\s]+(?:Court|Circuit|District))\s+of\s+([A-Z][a-zA-Z\s]+)',
            r'(?:United States|U\.S\.)\s+([A-Z][a-zA-Z\s]+(?:Court|Circuit|District))',
            r'([A-Z][a-zA-Z\s]+(?:Supreme Court|Court of Appeals))'
        ]
        
        for pattern in court_patterns:
            match = re.search(pattern, text)
            if match:
                court_info["court"] = match.group(1).strip()
                if len(match.groups()) > 1:
                    court_info["jurisdiction"] = match.group(2).strip()
                break
        
        return court_info
    
    def _extract_dates(self, text: str) -> List[str]:
        """Extract important dates"""
        dates = []
        
        # Date patterns
        date_patterns = [
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{1,2}/\d{1,2}/\d{4}\b',
            r'\b\d{4}-\d{2}-\d{2}\b'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            dates.extend(matches)
        
        return list(set(dates))

# Global processor instance
pdf_processor = PDFProcessor()

@app.post("/upload_pdf", response_model=PDFAnalysisResponse)
async def upload_pdf(file: UploadFile = File(...), _token: str = Depends(verify_token)):
    """Upload and analyze a PDF legal document"""
    logger.info(f"Received PDF upload request: {file.filename}")
    
    try:
        # Validate file
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Read file content
        content = await file.read()
        
        if len(content) > pdf_processor.max_file_size:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")
        
        # Extract text
        text = pdf_processor.extract_text_from_pdf(content)
        
        if not text:
            return PDFAnalysisResponse(
                success=False,
                error="Could not extract text from PDF"
            )
        
        # Analyze document
        analysis = pdf_processor.analyze_legal_document(text)
        
        if analysis["success"]:
            return PDFAnalysisResponse(
                success=True,
                case_text=text,
                extracted_data=analysis
            )
        else:
            return PDFAnalysisResponse(
                success=False,
                error=analysis.get("error", "Analysis failed")
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PDF upload: {e}")
        return PDFAnalysisResponse(
            success=False,
            error=f"Processing failed: {str(e)}"
        )

@app.post("/analyze_pdf_text")
async def analyze_pdf_text(request: PDFUploadRequest, _token: str = Depends(verify_token)):
    """Analyze PDF text content (base64 encoded)"""
    logger.info("Received PDF text analysis request")
    
    try:
        # Decode base64 content
        pdf_content = base64.b64decode(request.content)
        
        # Extract text
        text = pdf_processor.extract_text_from_pdf(pdf_content)
        
        if not text:
            return PDFAnalysisResponse(
                success=False,
                error="Could not extract text from PDF"
            )
        
        # Analyze document
        analysis = pdf_processor.analyze_legal_document(text)
        
        if analysis["success"]:
            return PDFAnalysisResponse(
                success=True,
                case_text=text,
                extracted_data=analysis
            )
        else:
            return PDFAnalysisResponse(
                success=False,
                error=analysis.get("error", "Analysis failed")
            )
    
    except Exception as e:
        logger.error(f"Error analyzing PDF text: {e}")
        return PDFAnalysisResponse(
            success=False,
            error=f"Analysis failed: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "PDF Analysis Service",
        "max_file_size": pdf_processor.max_file_size,
        "supported_formats": pdf_processor.supported_formats
    }

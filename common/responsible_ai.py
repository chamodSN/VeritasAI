"""
Responsible AI Framework Implementation for VeritasAI Legal Research System
Based on IBM's Responsible AI Framework with legal-specific adaptations
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from common.logging import logger
from common.models import ResponsibleAICheck
import re
import statistics
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

@dataclass
class RAIMetrics:
    """Responsible AI metrics for legal research"""
    explainability_score: float
    fairness_score: float
    robustness_score: float
    transparency_score: float
    privacy_score: float
    overall_score: float

class ResponsibleAIFramework:
    """
    Responsible AI implementation based on IBM's framework:
    - Explainability: Can users understand how AI derives conclusions?
    - Fairness: Are results unbiased and representative?
    - Robustness: Does the system handle edge cases and errors gracefully?
    - Transparency: Are processes and data sources clear?
    - Privacy: Is user data protected appropriately?
    """
    
    def __init__(self):
        self.legal_bias_indicators = [
            'gender', 'race', 'ethnicity', 'religion', 'age', 'disability',
            'sexual orientation', 'national origin', 'socioeconomic status'
        ]
        
        self.court_hierarchy = {
            'Supreme Court': 1.0,
            'Court of Appeals': 0.8,
            'District Court': 0.6,
            'State Supreme Court': 0.7,
            'State Court of Appeals': 0.5,
            'State District Court': 0.4
        }
        
        self.precedential_weight = {
            'precedential': 1.0,
            'non-precedential': 0.3,
            'unpublished': 0.2
        }
    
    def run_comprehensive_checks(self, 
                                query: str, 
                                results: Dict[str, Any], 
                                case_data: List[Dict[str, Any]] = None) -> List[ResponsibleAICheck]:
        """Run all responsible AI checks"""
        checks = []
        
        # Explainability checks
        checks.extend(self._check_explainability(query, results, case_data))
        
        # Fairness checks
        checks.extend(self._check_fairness(query, results, case_data))
        
        # Robustness checks
        checks.extend(self._check_robustness(query, results, case_data))
        
        # Transparency checks
        checks.extend(self._check_transparency(query, results, case_data))
        
        # Privacy checks
        checks.extend(self._check_privacy(query, results, case_data))
        
        return checks
    
    def _check_explainability(self, query: str, results: Dict[str, Any], case_data: List[Dict[str, Any]]) -> List[ResponsibleAICheck]:
        """Check explainability - can users understand AI conclusions?"""
        checks = []
        
        # Check if results provide clear reasoning
        if 'summary' in results and results['summary']:
            summary_length = len(str(results['summary']))
            if summary_length < 100:
                checks.append(ResponsibleAICheck(
                    check_type="explainability",
                    status="warning",
                    message="Summary is too brief to provide adequate explanation",
                    details={"summary_length": summary_length}
                ))
            elif summary_length > 2000:
                checks.append(ResponsibleAICheck(
                    check_type="explainability",
                    status="warning",
                    message="Summary may be too verbose for clear understanding",
                    details={"summary_length": summary_length}
                ))
            else:
                checks.append(ResponsibleAICheck(
                    check_type="explainability",
                    status="passed",
                    message="Summary provides adequate explanation",
                    details={"summary_length": summary_length}
                ))
        
        # Check citation quality
        if 'citations' in results and results['citations']:
            citation_count = len(results['citations'])
            if citation_count == 0:
                checks.append(ResponsibleAICheck(
                    check_type="explainability",
                    status="warning",
                    message="No citations provided to support conclusions",
                    details={"citation_count": citation_count}
                ))
            elif citation_count < 3:
                checks.append(ResponsibleAICheck(
                    check_type="explainability",
                    status="warning",
                    message="Limited citations may reduce explainability",
                    details={"citation_count": citation_count}
                ))
            else:
                checks.append(ResponsibleAICheck(
                    check_type="explainability",
                    status="passed",
                    message="Adequate citations provided for explanation",
                    details={"citation_count": citation_count}
                ))
        
        # Check confidence score transparency
        if 'confidence' in results:
            confidence = results['confidence']
            if confidence < 0.3:
                checks.append(ResponsibleAICheck(
                    check_type="explainability",
                    status="warning",
                    message="Low confidence score indicates uncertain conclusions",
                    details={"confidence": confidence}
                ))
            elif confidence > 0.8:
                checks.append(ResponsibleAICheck(
                    check_type="explainability",
                    status="passed",
                    message="High confidence score indicates reliable conclusions",
                    details={"confidence": confidence}
                ))
        
        return checks
    
    def _check_fairness(self, query: str, results: Dict[str, Any], case_data: List[Dict[str, Any]]) -> List[ResponsibleAICheck]:
        """Check fairness - are results unbiased and representative?"""
        checks = []
        
        if not case_data:
            return checks
        
        # Check court representation diversity
        courts = [case.get('court', '') for case in case_data if case.get('court')]
        if courts:
            unique_courts = set(courts)
            if len(unique_courts) == 1:
                checks.append(ResponsibleAICheck(
                    check_type="fairness",
                    status="warning",
                    message="Results from single court may lack diversity",
                    details={"courts": list(unique_courts), "count": len(courts)}
                ))
            elif len(unique_courts) >= 3:
                checks.append(ResponsibleAICheck(
                    check_type="fairness",
                    status="passed",
                    message="Good court diversity in results",
                    details={"courts": list(unique_courts), "count": len(courts)}
                ))
        
        # Check temporal diversity
        dates = [case.get('date_filed', '') for case in case_data if case.get('date_filed')]
        if dates:
            years = [date[:4] for date in dates if len(date) >= 4]
            if years:
                year_range = max(years) - min(years) if years else 0
                if year_range < 2:
                    checks.append(ResponsibleAICheck(
                        check_type="fairness",
                        status="warning",
                        message="Limited temporal diversity in case dates",
                        details={"year_range": year_range, "years": sorted(set(years))}
                    ))
                else:
                    checks.append(ResponsibleAICheck(
                        check_type="fairness",
                        status="passed",
                        message="Good temporal diversity in case dates",
                        details={"year_range": year_range, "years": sorted(set(years))}
                    ))
        
        # Check precedential balance
        precedential_cases = [case for case in case_data if case.get('precedential')]
        if precedential_cases and len(case_data) > 0:
            precedential_ratio = len(precedential_cases) / len(case_data)
            if precedential_ratio < 0.3:
                checks.append(ResponsibleAICheck(
                    check_type="fairness",
                    status="warning",
                    message="Low proportion of precedential cases may affect reliability",
                    details={"precedential_ratio": precedential_ratio}
                ))
            elif precedential_ratio > 0.7:
                checks.append(ResponsibleAICheck(
                    check_type="fairness",
                    status="passed",
                    message="Good proportion of precedential cases",
                    details={"precedential_ratio": precedential_ratio}
                ))
        
        # Check for potential bias indicators in query
        query_lower = query.lower()
        bias_indicators_found = [indicator for indicator in self.legal_bias_indicators 
                               if indicator in query_lower]
        if bias_indicators_found:
            checks.append(ResponsibleAICheck(
                check_type="fairness",
                status="warning",
                message="Query contains potential bias indicators",
                details={"bias_indicators": bias_indicators_found}
            ))
        
        return checks
    
    def _check_robustness(self, query: str, results: Dict[str, Any], case_data: List[Dict[str, Any]]) -> List[ResponsibleAICheck]:
        """Check robustness - does system handle edge cases gracefully?"""
        checks = []
        
        # Check for empty or insufficient results
        if not results or len(results) == 0:
            checks.append(ResponsibleAICheck(
                check_type="robustness",
                status="failed",
                message="System failed to produce any results",
                details={"result_count": 0}
            ))
            return checks
        
        # Check case count robustness
        case_count = results.get('case_count', 0)
        if case_count == 0:
            checks.append(ResponsibleAICheck(
                check_type="robustness",
                status="failed",
                message="No cases found for query",
                details={"case_count": case_count}
            ))
        elif case_count < 3:
            checks.append(ResponsibleAICheck(
                check_type="robustness",
                status="warning",
                message="Limited case count may affect robustness",
                details={"case_count": case_count}
            ))
        else:
            checks.append(ResponsibleAICheck(
                check_type="robustness",
                status="passed",
                message="Adequate case count for robust analysis",
                details={"case_count": case_count}
            ))
        
        # Check error handling
        if 'error' in results and results['error']:
            checks.append(ResponsibleAICheck(
                check_type="robustness",
                status="failed",
                message="System error detected in results",
                details={"error": results['error']}
            ))
        
        # Check data quality
        if case_data:
            text_lengths = [len(str(case.get('case_text', ''))) for case in case_data]
            if text_lengths:
                avg_length = statistics.mean(text_lengths)
                if avg_length < 500:
                    checks.append(ResponsibleAICheck(
                        check_type="robustness",
                        status="warning",
                        message="Cases have insufficient text content",
                        details={"avg_text_length": avg_length}
                    ))
                else:
                    checks.append(ResponsibleAICheck(
                        check_type="robustness",
                        status="passed",
                        message="Cases have adequate text content",
                        details={"avg_text_length": avg_length}
                    ))
        
        return checks
    
    def _check_transparency(self, query: str, results: Dict[str, Any], case_data: List[Dict[str, Any]]) -> List[ResponsibleAICheck]:
        """Check transparency - are processes and sources clear?"""
        checks = []
        
        # Check data source transparency
        source = results.get('source', '')
        if source:
            checks.append(ResponsibleAICheck(
                check_type="transparency",
                status="passed",
                message="Data source is clearly identified",
                details={"source": source}
            ))
        else:
            checks.append(ResponsibleAICheck(
                check_type="transparency",
                status="warning",
                message="Data source not clearly identified",
                details={}
            ))
        
        # Check methodology transparency
        if 'case_count' in results and 'confidence' in results:
            checks.append(ResponsibleAICheck(
                check_type="transparency",
                status="passed",
                message="Analysis methodology metrics provided",
                details={
                    "case_count": results['case_count'],
                    "confidence": results['confidence']
                }
            ))
        
        # Check timestamp transparency
        timestamp = datetime.utcnow().isoformat()
        checks.append(ResponsibleAICheck(
            check_type="transparency",
            status="passed",
            message="Analysis timestamp provided",
            details={"timestamp": timestamp}
        ))
        
        return checks
    
    def _check_privacy(self, query: str, results: Dict[str, Any], case_data: List[Dict[str, Any]]) -> List[ResponsibleAICheck]:
        """Check privacy - is user data protected appropriately?"""
        checks = []
        
        # Check for PII in query
        pii_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b',  # Credit card
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{3}-\d{3}-\d{4}\b'  # Phone
        ]
        
        pii_found = []
        for pattern in pii_patterns:
            if re.search(pattern, query):
                pii_found.append(pattern)
        
        if pii_found:
            checks.append(ResponsibleAICheck(
                check_type="privacy",
                status="failed",
                message="Potential PII detected in query",
                details={"pii_patterns": pii_found}
            ))
        else:
            checks.append(ResponsibleAICheck(
                check_type="privacy",
                status="passed",
                message="No PII detected in query",
                details={}
            ))
        
        # Check data retention transparency
        checks.append(ResponsibleAICheck(
            check_type="privacy",
            status="passed",
            message="Data retention policies should be clearly communicated",
            details={"retention_policy": "User data retained according to privacy policy"}
        ))
        
        return checks
    
    def calculate_overall_score(self, checks: List[ResponsibleAICheck]) -> RAIMetrics:
        """Calculate overall responsible AI metrics"""
        if not checks:
            return RAIMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        
        # Group checks by type
        check_groups = {}
        for check in checks:
            check_type = check.check_type
            if check_type not in check_groups:
                check_groups[check_type] = []
            check_groups[check_type].append(check)
        
        # Calculate scores for each pillar
        scores = {}
        for check_type, type_checks in check_groups.items():
            passed = len([c for c in type_checks if c.status == "passed"])
            warnings = len([c for c in type_checks if c.status == "warning"])
            failed = len([c for c in type_checks if c.status == "failed"])
            
            total = len(type_checks)
            if total > 0:
                # Score calculation: passed=1.0, warning=0.5, failed=0.0
                score = (passed * 1.0 + warnings * 0.5 + failed * 0.0) / total
                scores[check_type] = score
            else:
                scores[check_type] = 0.0
        
        # Calculate overall score
        overall_score = statistics.mean(list(scores.values())) if scores else 0.0
        
        return RAIMetrics(
            explainability_score=scores.get('explainability', 0.0),
            fairness_score=scores.get('fairness', 0.0),
            robustness_score=scores.get('robustness', 0.0),
            transparency_score=scores.get('transparency', 0.0),
            privacy_score=scores.get('privacy', 0.0),
            overall_score=overall_score
        )

# Global framework instance
rai_framework = ResponsibleAIFramework()

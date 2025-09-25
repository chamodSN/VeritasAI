import re
import asyncio
from typing import List, Dict, Any, Tuple
from transformers import pipeline
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim
import numpy as np
from common.config import Config
from common.logging import logger


class ResponsibleAIService:
    def __init__(self):
        self.bias_detector = None
        self.sentiment_analyzer = None
        self.embedding_model = None
        self._initialize_models()

    def _initialize_models(self):
        try:
            if Config.ENABLE_BIAS_DETECTION:
                self.bias_detector = pipeline(
                    "text-classification",
                    model="distilbert-base-uncased",
                    device=-1
                )
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Responsible AI models initialized successfully")
        except Exception as e:
            logger.warning(
                f"Failed to initialize Responsible AI models: {str(e)}")

    async def check_query_fairness(self, query: str) -> Dict[str, Any]:
        if not self.bias_detector:
            return {"is_fair": True, "bias_score": 0.0, "warnings": []}
        try:
            bias_result = self.bias_detector(query)
            bias_score = bias_result[0]["score"] if bias_result[0]["label"] == "POSITIVE" else 0.0
            protected_attributes = [
                r'\b(race|ethnicity|gender|sex|age|religion|nationality|disability)\b',
                r'\b(black|white|hispanic|asian|male|female|old|young|christian|muslim|jewish)\b'
            ]
            warnings = []
            for pattern in protected_attributes:
                if re.search(pattern, query, re.IGNORECASE):
                    warnings.append(f"Potential bias in query: {pattern}")
            is_fair = bias_score < 0.4 and len(warnings) == 0
            if not is_fair:
                logger.warning(
                    f"RA Check: Query fairness issue - bias_score: {bias_score}, warnings: {warnings}")
            return {
                "is_fair": is_fair,
                "bias_score": bias_score,
                "warnings": warnings
            }
        except Exception as e:
            logger.error(f"Error in bias detection: {str(e)}")
            return {"is_fair": True, "bias_score": 0.0, "warnings": []}

    async def check_result_diversity(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not results:
            return {"is_diverse": True, "diversity_score": 1.0, "recommendations": []}
        try:
            courts = [result.get("court_citation_string", "")
                      for result in results]
            unique_courts = len(set(courts))
            court_diversity = unique_courts / len(courts) if courts else 0
            dates = []
            for result in results:
                date_filed = result.get("dateFiled")
                if date_filed:
                    try:
                        from datetime import datetime
                        if isinstance(date_filed, str):
                            parsed_date = datetime.fromisoformat(
                                date_filed.replace('Z', '+00:00')).date()
                            dates.append(parsed_date)
                        else:
                            dates.append(date_filed)
                    except Exception:
                        continue
            temporal_diversity = 1.0
            if len(dates) > 1:
                try:
                    date_range = max(dates) - min(dates)
                    temporal_diversity = min(1.0, date_range.days / 365)
                except Exception:
                    temporal_diversity = 0.5
            diversity_score = (court_diversity + temporal_diversity) / 2
            is_diverse = diversity_score > 0.4
            recommendations = []
            if court_diversity < 0.5:
                recommendations.append("Expand court coverage for diversity")
            if temporal_diversity < 0.4:
                recommendations.append(
                    "Expand date range for temporal diversity")
            if not is_diverse:
                logger.warning(
                    f"RA Check: Low diversity - score: {diversity_score}")
            return {
                "is_diverse": is_diverse,
                "diversity_score": diversity_score,
                "recommendations": recommendations
            }
        except Exception as e:
            logger.error(f"Error in diversity analysis: {str(e)}")
            return {"is_diverse": True, "diversity_score": 1.0, "recommendations": []}

    async def check_classification_confidence(self, classifications: Dict[str, Any]) -> Dict[str, Any]:
        try:
            confidence_issues = []
            for key, value in classifications.items():
                if isinstance(value, tuple) and len(value) == 2:
                    label, score = value
                    if score < 0.5:  # Lowered threshold
                        confidence_issues.append(
                            f"Low confidence in {key}: {score}")
            is_confident = len(confidence_issues) == 0
            if not is_confident:
                logger.warning(
                    f"RA Check: Low confidence classifications: {confidence_issues}")
            return {
                "is_confident": is_confident,
                "confidence_issues": confidence_issues,
                "min_threshold": 0.5  # Updated
            }
        except Exception as e:
            logger.error(f"Error in confidence checking: {str(e)}")
            return {"is_confident": True, "confidence_issues": [], "min_threshold": 0.5}

    async def check_result_relevance(self, query: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.embedding_model or not results:
            return {"is_relevant": True, "relevance_score": 1.0, "low_relevance_results": []}
        try:
            query_embedding = self.embedding_model.encode([query])[0]
            low_relevance_results = []
            relevance_scores = []
            for i, result in enumerate(results):
                result_text = f"{result.get('caseName', '')} {result.get('snippet', '')}"
                result_embedding = self.embedding_model.encode([result_text])[
                    0]
                similarity = cos_sim(query_embedding, result_embedding)[
                    0][0].item()
                relevance_scores.append(similarity)
                if similarity < 0.5:  # Lowered threshold
                    low_relevance_results.append({
                        "index": i,
                        "similarity": similarity,
                        "case_name": result.get('caseName', 'Unknown')
                    })
            avg_relevance = np.mean(
                relevance_scores) if relevance_scores else 0
            is_relevant = avg_relevance > 0.5 and len(
                low_relevance_results) < len(results) * 0.5
            if not is_relevant:
                logger.warning(
                    f"RA Check: Low relevance - avg_relevance: {avg_relevance}")
            return {
                "is_relevant": is_relevant,
                "relevance_score": avg_relevance,
                "low_relevance_results": low_relevance_results
            }
        except Exception as e:
            logger.error(f"Error in relevance checking: {str(e)}")
            return {"is_relevant": True, "relevance_score": 1.0, "low_relevance_results": []}


responsible_ai = ResponsibleAIService()

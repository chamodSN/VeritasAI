"""
Advanced CourtListener API Features
Includes alerts, dockets, opinions, and case tracking
"""

import requests
# import json  # Not used in current implementation
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from common.config import Config
from common.logging import setup_logging
from model.courtlistener_client import courtlistener_client

logger = setup_logging()


@dataclass
class Alert:
    """Data structure for CourtListener alerts"""
    name: str
    query: str
    rate: str
    resource_uri: str
    date_created: str
    is_active: bool


@dataclass
class DocketEntry:
    """Data structure for docket entries"""
    entry_number: int
    description: str
    date_filed: str
    document_number: Optional[str] = None
    attachment_number: Optional[int] = None


@dataclass
class Opinion:
    """Data structure for opinions"""
    absolute_url: str
    cluster: str
    date_created: str
    date_modified: str
    html: Optional[str] = None
    html_lawbox: Optional[str] = None
    html_columbia: Optional[str] = None
    html_anon_2020: Optional[str] = None
    plain_text: Optional[str] = None
    xml: Optional[str] = None
    author: Optional[str] = None
    joined_by: Optional[List[str]] = None
    type: Optional[str] = None


class CourtListenerAdvancedFeatures:
    """Advanced features for CourtListener API integration"""

    def __init__(self):
        self.api_key = Config.COURTLISTENER_API_KEY
        self.base_url = "https://www.courtlistener.com/api/rest/v4"
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }

    def create_search_alert(self, query: str, name: str, rate: str = "dly") -> Optional[str]:
        """Create a search alert for new cases"""
        url = f"{self.base_url}/alerts/"
        data = {
            "name": name,
            "query": query,
            "rate": rate  # dly, wly, mly
        }

        try:
            response = requests.post(
                url, headers=self.headers, json=data, timeout=30)
            response.raise_for_status()

            alert_data = response.json()
            logger.info("Created alert: %s", name)
            return alert_data.get("resource_uri")

        except requests.exceptions.RequestException as e:
            logger.error("Error creating alert: %s", e)
            return None

    def get_user_alerts(self) -> List[Alert]:
        """Get all alerts for the authenticated user"""
        url = f"{self.base_url}/alerts/"

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            alerts = []

            for alert_data in data.get("results", []):
                alert = Alert(
                    name=alert_data.get("name", ""),
                    query=alert_data.get("query", ""),
                    rate=alert_data.get("rate", ""),
                    resource_uri=alert_data.get("resource_uri", ""),
                    date_created=alert_data.get("date_created", ""),
                    is_active=alert_data.get("is_active", True)
                )
                alerts.append(alert)

            return alerts

        except requests.exceptions.RequestException as e:
            logger.error("Error getting alerts: %s", e)
            return []

    def delete_alert(self, alert_uri: str) -> bool:
        """Delete an alert"""
        try:
            response = requests.delete(
                alert_uri, headers=self.headers, timeout=30)
            response.raise_for_status()
            logger.info("Deleted alert: %s", alert_uri)
            return True

        except requests.exceptions.RequestException as e:
            logger.error("Error deleting alert: %s", e)
            return False

    def get_docket_entries(self, docket_id: str) -> List[DocketEntry]:
        """Get docket entries for a case"""
        url = f"{self.base_url}/docket-entries/"
        params = {
            "docket": docket_id,
            "format": "json"
        }

        try:
            response = requests.get(
                url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            entries = []

            for entry_data in data.get("results", []):
                entry = DocketEntry(
                    entry_number=entry_data.get("entry_number", 0),
                    description=entry_data.get("description", ""),
                    date_filed=entry_data.get("date_filed", ""),
                    document_number=entry_data.get("document_number"),
                    attachment_number=entry_data.get("attachment_number")
                )
                entries.append(entry)

            return entries

        except requests.exceptions.RequestException as e:
            logger.error("Error getting docket entries: %s", e)
            return []

    def get_case_opinions(self, case_id: str) -> List[Opinion]:
        """Get opinions for a specific case"""
        url = f"{self.base_url}/opinions/"
        params = {
            "cluster": case_id,
            "format": "json"
        }

        try:
            response = requests.get(
                url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            opinions = []

            for opinion_data in data.get("results", []):
                opinion = Opinion(
                    absolute_url=opinion_data.get("absolute_url", ""),
                    cluster=opinion_data.get("cluster", ""),
                    date_created=opinion_data.get("date_created", ""),
                    date_modified=opinion_data.get("date_modified", ""),
                    html=opinion_data.get("html"),
                    html_lawbox=opinion_data.get("html_lawbox"),
                    html_columbia=opinion_data.get("html_columbia"),
                    html_anon_2020=opinion_data.get("html_anon_2020"),
                    plain_text=opinion_data.get("plain_text"),
                    xml=opinion_data.get("xml"),
                    author=opinion_data.get("author"),
                    joined_by=opinion_data.get("joined_by"),
                    type=opinion_data.get("type")
                )
                opinions.append(opinion)

            return opinions

        except requests.exceptions.RequestException as e:
            logger.error("Error getting opinions: %s", e)
            return []

    def get_court_statistics(self) -> Dict[str, Any]:
        """Get statistics about courts and cases"""
        url = f"{self.base_url}/courts/"
        params = {
            "format": "json",
            "page_size": 100
        }

        try:
            response = requests.get(
                url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Calculate basic statistics
            total_courts = data.get("count", 0)
            courts = data.get("results", [])

            # Group by jurisdiction
            jurisdictions = {}
            for court in courts:
                jurisdiction = court.get("jurisdiction", "Unknown")
                if jurisdiction not in jurisdictions:
                    jurisdictions[jurisdiction] = 0
                jurisdictions[jurisdiction] += 1

            return {
                "total_courts": total_courts,
                "jurisdictions": jurisdictions,
                "courts_sample": courts[:10]  # First 10 courts as sample
            }

        except requests.exceptions.RequestException as e:
            logger.error("Error getting court statistics: %s", e)
            return {}

    def search_by_court(self, court_id: str, query: str = "", limit: int = 20) -> List[Dict[str, Any]]:
        """Search cases within a specific court"""
        url = f"{self.base_url}/search/"
        params = {
            "court": court_id,
            "q": query,
            "stat_Precedential": "on",
            "order_by": "score desc",
            "format": "json"
        }

        try:
            response = requests.get(
                url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            return data.get("results", [])[:limit]

        except requests.exceptions.RequestException as e:
            logger.error("Error searching by court: %s", e)
            return []

    def get_case_citations(self, case_id: str) -> Dict[str, Any]:
        """Get citations for a specific case"""
        url = f"{self.base_url}/citations/"
        params = {
            "cited_opinion": case_id,
            "format": "json"
        }

        try:
            response = requests.get(
                url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Get citing cases
            citing_cases = []
            for citation in data.get("results", []):
                citing_cases.append({
                    "case_name": citation.get("citing_opinion", {}).get("caseName", ""),
                    "court": citation.get("citing_opinion", {}).get("court", ""),
                    "date_filed": citation.get("citing_opinion", {}).get("dateFiled", ""),
                    "citation_text": citation.get("citation_text", "")
                })

            return {
                "total_citations": data.get("count", 0),
                "citing_cases": citing_cases
            }

        except requests.exceptions.RequestException as e:
            logger.error("Error getting case citations: %s", e)
            return {"total_citations": 0, "citing_cases": []}

    def track_case_updates(self, case_id: str) -> Dict[str, Any]:
        """Track updates for a specific case"""
        # This would typically involve checking for new docket entries
        # and opinion updates over time
        docket_entries = self.get_docket_entries(case_id)
        opinions = self.get_case_opinions(case_id)

        return {
            "case_id": case_id,
            "docket_entries_count": len(docket_entries),
            "opinions_count": len(opinions),
            "latest_docket_entry": docket_entries[-1] if docket_entries else None,
            "latest_opinion": opinions[-1] if opinions else None
        }

    def bulk_case_analysis(self, case_ids: List[str]) -> Dict[str, Any]:
        """Perform bulk analysis on multiple cases"""
        results = {
            "total_cases": len(case_ids),
            "cases_analyzed": 0,
            "common_courts": {},
            "date_range": {"earliest": None, "latest": None},
            "precedential_count": 0,
            "total_citations": 0
        }

        for case_id in case_ids:
            try:
                # Get case details
                case_details = courtlistener_client.get_case_details(case_id)
                if case_details:
                    results["cases_analyzed"] += 1

                    # Track courts
                    court = case_details.get("court", "Unknown")
                    if court not in results["common_courts"]:
                        results["common_courts"][court] = 0
                    results["common_courts"][court] += 1

                    # Track dates
                    date_filed = case_details.get("dateFiled")
                    if date_filed:
                        if not results["date_range"]["earliest"] or date_filed < results["date_range"]["earliest"]:
                            results["date_range"]["earliest"] = date_filed
                        if not results["date_range"]["latest"] or date_filed > results["date_range"]["latest"]:
                            results["date_range"]["latest"] = date_filed

                    # Track precedential status
                    if case_details.get("precedential"):
                        results["precedential_count"] += 1

                    # Get citation count
                    citations = self.get_case_citations(case_id)
                    results["total_citations"] += citations.get(
                        "total_citations", 0)

            except Exception as e:
                logger.warning("Error analyzing case %s: %s", case_id, e)

        return results


# Global instance
courtlistener_advanced = CourtListenerAdvancedFeatures()

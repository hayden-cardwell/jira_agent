from jira import JIRA
from pprint import pprint
from typing import Dict, Any


class Client:
    def __init__(self, server: str, email: str, token: str, testing_mode: bool = False):
        self.server = server
        self.email = email
        self.token = token
        self.testing_mode = testing_mode
        self.jira: JIRA = JIRA(server=self.server, basic_auth=(self.email, self.token))

    def test_connection(self):
        try:
            # Example: Get current user info
            user_id = self.jira.current_user()
            pprint(f"Logged in as: {user_id}")
            user_info = self.jira.user(user_id)
            pprint(f"User info: {user_info}")

        except Exception as e:
            print(f"Failed to connect to JIRA: {e}")

    def fetch_recently_resolved(self, project_key: str, lookback_minutes: int = 5):
        jql = f"project = {project_key} AND resolutiondate >= -{lookback_minutes}m"
        issues = self.jira.search_issues(
            jql_str=jql,
            maxResults=100,
            fields="key,summary,status,resolution,resolutiondate",
        )
        return issues

    def get_ticket(self, ticket_id: str):
        """Simple method to get basic JIRA issue object."""
        return self.jira.issue(ticket_id)

    def get_full_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """
        Get the full JIRA issue with all data expanded.

        Args:
            ticket_id: The JIRA ticket key (e.g., 'PROJ-123')

        Returns:
            Dict of the full JIRA Issue (all fields, comments, attachments, history)
        """
        # return self.jira.issue(ticket_id, expand="changelog,renderedFields")
        return self.jira.issue(ticket_id, expand="all").raw

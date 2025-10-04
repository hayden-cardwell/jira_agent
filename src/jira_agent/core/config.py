"""Configuration management for the JIRA agent."""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class ServiceConfig:
    """Configuration for all external services."""

    # JIRA settings
    jira_server: Optional[str] = None
    jira_email: Optional[str] = None
    jira_token: Optional[str] = None
    jira_testing_mode: bool = False
    jira_project_key: Optional[str] = None

    # Confluence settings
    confluence_server: Optional[str] = None
    confluence_email: Optional[str] = None
    confluence_token: Optional[str] = None
    confluence_space: Optional[str] = None
    confluence_auto_submit: bool = False

    # LLM settings
    llm_provider: str = "openai"
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: Optional[str] = None

    # AWS Bedrock settings
    aws_region: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    bedrock_inference_profile: Optional[str] = None

    # Runtime settings
    use_static_tickets: bool = False
    poll_interval_seconds: int = 30
    lookback_minutes: int = 300

    @classmethod
    def from_env(cls) -> "ServiceConfig":
        """Load configuration from environment variables."""
        return cls(
            jira_server=os.getenv("JIRA_SERVER"),
            jira_email=os.getenv("JIRA_EMAIL"),
            jira_token=os.getenv("JIRA_API_TOKEN"),
            jira_testing_mode=os.getenv("TESTING_MODE", "").lower() == "true",
            jira_project_key=os.getenv("JIRA_PROJECT_KEY"),
            confluence_server=os.getenv("CONFLUENCE_SERVER"),
            confluence_email=os.getenv("CONFLUENCE_EMAIL"),
            confluence_token=os.getenv("CONFLUENCE_API_TOKEN"),
            confluence_space=os.getenv("CONFLUENCE_SPACE_KEY"),
            confluence_auto_submit=os.getenv("CONFLUENCE_AUTO_SUBMIT", "false").lower()
            == "true",
            llm_provider=os.getenv("LLM_PROVIDER", "openai").lower(),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_base_url=os.getenv("OPENAI_BASE_URL"),
            openai_model=os.getenv("OPENAI_MODEL"),
            aws_region=os.getenv("AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            bedrock_inference_profile=os.getenv("BEDROCK_INFERENCE_PROFILE"),
            use_static_tickets=os.getenv("USE_STATIC_TICKETS", "false").lower()
            == "true",
            poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "30")),
            lookback_minutes=int(os.getenv("LOOKBACK_MINUTES", "300")),
        )

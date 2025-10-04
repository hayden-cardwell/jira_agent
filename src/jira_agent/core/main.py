"""
Alternative main application logic for the JIRA agent.
Demonstrates improved structure, logging, and error handling.
"""

import time
import logging
from typing import Optional, List, Dict, Any, Set, Tuple
from dotenv import load_dotenv
from pprint import pprint
from ..atlassian import jira, confluence
from ..agent import llm
from ..prompts import PromptTemplate, load_prompt_values
from .config import ServiceConfig
from .confluence_handler import ConfluenceHandler


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class JiraAgent:
    """Main agent for processing JIRA tickets with LLM analysis."""

    def __init__(self, config: ServiceConfig):
        self.config = config
        self.llm_service: Optional[llm.LLM] = None
        self.jira_service: Optional[jira.Client] = None
        self.confluence_service: Optional[confluence.Client] = None
        self.confluence_handler: Optional[ConfluenceHandler] = None
        self.template: Optional[PromptTemplate] = None
        self.ticket_analyzer_examples: Optional[List[Dict[str, str]]] = None

    def initialize(self) -> bool:
        """
        Initialize all services based on configuration.

        Returns:
            bool: True if core services initialized successfully, False otherwise.
        """
        try:
            # Initialize LLM service (required)
            self._initialize_llm()

            # Initialize template (required)
            self._initialize_template()

            # Initialize Confluence service (optional)
            self._initialize_confluence()

            # Initialize JIRA service (only needed for live mode)
            if not self.config.use_static_tickets:
                if not self._initialize_jira():
                    return False

            logger.info("Agent initialization complete")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}", exc_info=True)
            return False

    def _initialize_llm(self) -> None:
        """Initialize the LLM service."""
        if self.config.llm_provider == "bedrock":
            # Initialize AWS Bedrock provider
            if not self.config.aws_region:
                raise ValueError(
                    "AWS_REGION is required for Bedrock provider. "
                    "Set it in your .env file."
                )
            if not self.config.bedrock_inference_profile:
                raise ValueError(
                    "BEDROCK_INFERENCE_PROFILE is required for Bedrock provider. "
                    "Example: us.anthropic.claude-3-5-haiku-20241022-v1:0"
                )

            llm_provider = llm.BedrockProvider(
                region=self.config.aws_region,
                inference_profile=self.config.bedrock_inference_profile,
                access_key_id=self.config.aws_access_key_id,
                secret_access_key=self.config.aws_secret_access_key,
            )
            logger.info(
                f"LLM service initialized (Bedrock: {self.config.bedrock_inference_profile})"
            )
        else:
            # Default to OpenAI provider
            if not self.config.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required")

            llm_provider = llm.OpenAIProvider(
                api_key=self.config.openai_api_key,
                base_url=self.config.openai_base_url,
                model=self.config.openai_model or "gpt-4.1-2025-04-14",
            )
            logger.info("LLM service initialized (OpenAI)")

        self.llm_service = llm.LLM(provider=llm_provider)

    def _initialize_template(self) -> None:
        """Initialize the prompt template."""
        system_prompt, instruction_text, examples = load_prompt_values(
            env_var="PROMPT_TICKET_ANALYZER", default_filename="ticket_analyzer.prompt"
        )
        self.template = PromptTemplate(
            system_prompt=system_prompt,
            instruction_template=instruction_text,
        )
        self.ticket_analyzer_examples = examples
        logger.debug("Prompt template initialized")

    def _initialize_confluence(self) -> None:
        """Initialize Confluence service if credentials are available."""
        if not all(
            [
                self.config.confluence_server,
                self.config.confluence_email,
                self.config.confluence_token,
            ]
        ):
            logger.info("Confluence credentials not configured, skipping integration")
            return

        try:
            self.confluence_service = confluence.Client(
                self.config.confluence_server,
                self.config.confluence_email,
                self.config.confluence_token,
                self.config.confluence_space,
            )

            if self.confluence_service.test_connection():
                logger.info("Confluence service initialized successfully")
                # Initialize the Confluence handler with both services
                if self.llm_service:
                    self.confluence_handler = ConfluenceHandler(
                        self.confluence_service,
                        self.llm_service,
                    )
            else:
                logger.warning(
                    "Confluence connection test failed, disabling integration"
                )
                self.confluence_service = None

        except Exception as e:
            logger.warning(f"Could not initialize Confluence: {e}")
            self.confluence_service = None

    def _initialize_jira(self) -> bool:
        """
        Initialize JIRA service for live mode.

        Returns:
            bool: True if successful, False otherwise.
        """
        if not all(
            [
                self.config.jira_server,
                self.config.jira_email,
                self.config.jira_token,
            ]
        ):
            logger.error("JIRA credentials not configured. See env.example for setup.")
            return False

        if not self.config.jira_project_key:
            logger.error(
                "JIRA_PROJECT_KEY is not configured. Set it in your environment."
            )
            return False

        try:
            self.jira_service = jira.Client(
                self.config.jira_server,
                self.config.jira_email,
                self.config.jira_token,
                testing_mode=self.config.jira_testing_mode,
            )
            self.jira_service.test_connection()
            logger.info("JIRA service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to JIRA: {e}", exc_info=True)
            return False

    def search_confluence_for_ticket(
        self, ticket_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate search queries and find relevant Confluence articles.

        Args:
            ticket_data: The ticket data dictionary

        Returns:
            List of relevant Confluence articles (deduplicated)
        """
        if not self.confluence_handler:
            logger.debug("Confluence handler not available, skipping search")
            return []

        return self.confluence_handler.search_for_ticket(ticket_data)

    def process_ticket(
        self,
        ticket_data: Dict[str, Any],
        ticket_key: str = "Unknown",
        submit_to_confluence: Optional[bool] = None,
    ) -> Optional[str]:
        """
        Process a single ticket through the analysis pipeline.

        Args:
            ticket_data: The ticket data dictionary
            ticket_key: The ticket key for logging purposes
            submit_to_confluence: Whether to submit draft changes to Confluence
                                 (None = use config default)

        Returns:
            The LLM analysis response, or None if processing failed
        """
        try:
            logger.info(f"Processing ticket: {ticket_key}")

            # Search Confluence for relevant articles
            confluence_results = self.search_confluence_for_ticket(ticket_data)

            if confluence_results:
                logger.info(
                    f"Found {len(confluence_results)} relevant Confluence articles"
                )
                for article in confluence_results:
                    logger.debug(f"  - {article.get('title')} ({article.get('url')})")
            else:
                logger.debug("No relevant Confluence articles found")

            # Generate analysis using LLM
            formatted_messages = self.template.format_messages(
                ticket_data=ticket_data,
                examples=self.ticket_analyzer_examples,
                confluence_results=confluence_results,
            )

            response = self.llm_service.generate_response(prompt=formatted_messages)
            logger.info(f"Analysis complete for {ticket_key}")

            # Submit to Confluence if requested and service is available
            # Use config setting if submit_to_confluence is not explicitly set
            should_submit = (
                submit_to_confluence
                if submit_to_confluence is not None
                else self.config.confluence_auto_submit
            )

            if should_submit and self.confluence_handler:
                self.confluence_handler.submit_analysis(response, ticket_key)

            return response

        except Exception as e:
            logger.error(f"Error processing ticket {ticket_key}: {e}", exc_info=True)
            return None

    def run_static_mode(self) -> None:
        """Process static tickets from files."""
        logger.info("Running in static ticket mode")

        try:
            from ..data.static_tickets.tls_inspection import ticket_data

            static_tickets = [ticket_data]  # Add more tickets as needed
            logger.info(f"Found {len(static_tickets)} static tickets to process")

            for ticket in static_tickets:
                ticket_key = ticket.get("key", "Unknown")
                response = self.process_ticket(ticket, ticket_key)

                if response:
                    pprint(response)
                    print("-" * 80)

        except ImportError as e:
            logger.error(f"Failed to load static tickets: {e}")
        except Exception as e:
            logger.error(f"Error in static mode: {e}", exc_info=True)

    def run_live_mode(self) -> None:
        """Poll JIRA for recently resolved tickets and process them."""
        if not self.jira_service:
            logger.error("JIRA service not initialized, cannot run live mode")
            return

        logger.info("Starting JIRA polling loop...")
        logger.info(
            f"Polling every {self.config.poll_interval_seconds}s, "
            f"looking back {self.config.lookback_minutes} minutes"
        )

        processed_tickets: Set[Tuple[str, str]] = set()

        while True:
            try:
                project_key = self.config.jira_project_key
                issues = self.jira_service.fetch_recently_resolved(
                    project_key=project_key,
                    lookback_minutes=self.config.lookback_minutes,
                )

                for issue in issues:
                    ticket_id = (issue.key, issue.fields.resolutiondate)

                    # Skip if already processed (unless in testing mode)
                    if (
                        not self.config.jira_testing_mode
                        and ticket_id in processed_tickets
                    ):
                        continue

                    if not self.config.jira_testing_mode:
                        processed_tickets.add(ticket_id)

                    # Get full ticket data and process
                    full_ticket = self.jira_service.get_full_ticket(issue.key)
                    response = self.process_ticket(full_ticket, issue.key)

                    if response:
                        print(response)

                time.sleep(self.config.poll_interval_seconds)

            except KeyboardInterrupt:
                logger.info("Shutting down gracefully...")
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}", exc_info=True)
                logger.info("Continuing after error...")
                time.sleep(self.config.poll_interval_seconds)

    def run(self) -> None:
        """Run the agent in the appropriate mode."""
        if not self.initialize():
            logger.error("Failed to initialize agent, exiting")
            return

        if self.config.use_static_tickets:
            self.run_static_mode()
        else:
            self.run_live_mode()


def main():
    """Main entry point for the JIRA agent."""
    load_dotenv()

    config = ServiceConfig.from_env()
    agent = JiraAgent(config)
    agent.run()


if __name__ == "__main__":
    main()

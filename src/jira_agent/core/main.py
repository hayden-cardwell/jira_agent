"""
Alternative main application logic for the JIRA agent.
Demonstrates improved structure, logging, and error handling.
"""

import os
import time
import json
import logging
from typing import Optional, List, Dict, Any, Set, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv
from pprint import pprint
from ..atlassian import jira, confluence
from ..agent import llm
from ..prompts import TicketAnalyzerPrompts, PromptTemplate, ConfluenceSearchPrompts


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: Optional[str] = None

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
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_base_url=os.getenv("OPENAI_BASE_URL"),
            openai_model=os.getenv("OPENAI_MODEL"),
            use_static_tickets=os.getenv("USE_STATIC_TICKETS", "false").lower()
            == "true",
            poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "30")),
            lookback_minutes=int(os.getenv("LOOKBACK_MINUTES", "300")),
        )


class JiraAgent:
    """Main agent for processing JIRA tickets with LLM analysis."""

    def __init__(self, config: ServiceConfig):
        self.config = config
        self.llm_service: Optional[llm.LLM] = None
        self.jira_service: Optional[jira.Client] = None
        self.confluence_service: Optional[confluence.Client] = None
        self.template: Optional[PromptTemplate] = None

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
        if not self.config.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")

        llm_provider = llm.OpenAIProvider(
            api_key=self.config.openai_api_key,
            base_url=self.config.openai_base_url,
            model=self.config.openai_model or "gpt-4.1-2025-04-14",
        )
        self.llm_service = llm.LLM(provider=llm_provider)
        logger.info("LLM service initialized")

    def _initialize_template(self) -> None:
        """Initialize the prompt template."""
        analyzer = TicketAnalyzerPrompts()
        self.template = PromptTemplate(
            system_prompt=analyzer.SYSTEM_PROMPT,
            instruction_template=analyzer.ANALYSIS_INSTRUCTION,
        )
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
        if not self.confluence_service:
            logger.debug("Confluence service not available, skipping search")
            return []

        try:
            logger.info("Generating Confluence search queries...")

            # Generate search queries using LLM
            search_queries = self._generate_search_queries(ticket_data)
            if not search_queries:
                return []

            logger.info(f"Generated {len(search_queries)} search queries")
            for i, query in enumerate(search_queries, 1):
                logger.info(f"  Query {i}: {query}")

            # Execute searches and deduplicate results
            return self._execute_confluence_searches(search_queries)

        except Exception as e:
            logger.error(f"Error searching Confluence: {e}", exc_info=True)
            return []

    def _generate_search_queries(self, ticket_data: Dict[str, Any]) -> List[str]:
        """Generate search queries using LLM."""
        search_prompts = ConfluenceSearchPrompts()
        search_template = PromptTemplate(
            system_prompt=search_prompts.SYSTEM_PROMPT,
            instruction_template=search_prompts.QUERY_GENERATION_INSTRUCTION,
        )

        formatted_messages = search_template.format_messages(
            ticket_data=ticket_data,
            examples=search_prompts.FEW_SHOT_EXAMPLES,
        )

        response = self.llm_service.generate_response(prompt=formatted_messages)

        try:
            search_queries = json.loads(response)
            if not isinstance(search_queries, list):
                logger.warning(f"Expected list of queries, got {type(search_queries)}")
                return []
            return search_queries

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse search queries JSON: {e}")
            logger.debug(f"Raw LLM response: {response}")
            return []

    def _execute_confluence_searches(
        self, search_queries: List[str]
    ) -> List[Dict[str, Any]]:
        """Execute Confluence searches and deduplicate results."""
        all_results = []
        seen_ids: Set[str] = set()

        for query in search_queries:
            logger.debug(f"Searching Confluence: {query}")
            results = self.confluence_service.search_articles(query, limit=5)

            for article in results:
                article_id = article.get("id")
                if article_id and article_id not in seen_ids:
                    seen_ids.add(article_id)
                    # Fetch full content for each article
                    page_content = self.confluence_service.get_page_content(article_id)
                    if page_content:
                        article["content"] = page_content.get("content", "")
                    all_results.append(article)

        logger.info(f"Found {len(all_results)} unique Confluence articles")
        return all_results

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
                examples=TicketAnalyzerPrompts.CORRECT_FEW_SHOT_EXAMPLES,
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

            if should_submit and self.confluence_service:
                self.submit_to_confluence(response, ticket_key)

            return response

        except Exception as e:
            logger.error(f"Error processing ticket {ticket_key}: {e}", exc_info=True)
            return None

    def submit_to_confluence(
        self, llm_response: str, ticket_key: str = "Unknown"
    ) -> None:
        """
        Parse LLM response and submit draft changes to Confluence.

        Args:
            llm_response: The JSON response from the LLM
            ticket_key: The ticket key for logging purposes
        """
        try:
            # Parse the LLM response
            analysis = json.loads(llm_response)

            logger.info(f"Processing Confluence submissions for {ticket_key}")
            logger.debug(
                f"Analysis: {analysis.get('reasoning', 'No reasoning provided')}"
            )

            # Handle new article creation
            if analysis.get("needsNewArticle") and analysis.get("proposedTitle"):
                self._create_new_confluence_article(
                    title=analysis.get("proposedTitle"),
                    sections=analysis.get("sections", []),
                    ticket_key=ticket_key,
                )

            # Handle existing article updates
            existing_updates = analysis.get("existingArticleUpdates", [])
            if existing_updates:
                for update in existing_updates:
                    self._update_existing_confluence_article(
                        article_title=update.get("articleTitle"),
                        suggested_changes=update.get("suggestedChanges"),
                        redrafted_content=update.get("redraftedContent"),
                        ticket_key=ticket_key,
                    )

            # Log if no action was needed
            if not analysis.get("needsNewArticle") and not existing_updates:
                logger.info(
                    f"No Confluence changes needed for {ticket_key}: "
                    f"{analysis.get('reasoning', 'Already covered')}"
                )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Raw response: {llm_response}")
        except Exception as e:
            logger.error(f"Error submitting to Confluence: {e}", exc_info=True)

    def _create_new_confluence_article(
        self, title: str, sections: List[str], ticket_key: str
    ) -> None:
        """
        Create a new Confluence article with the proposed title and sections.

        Args:
            title: Proposed article title
            sections: List of section names for the article
            ticket_key: The ticket key for logging and reference
        """
        try:
            logger.info(f"Creating new Confluence article: '{title}'")

            # Generate basic HTML structure with sections
            content_parts = [
                f"<p><em>This draft was automatically generated from ticket {ticket_key}</em></p>",
                "<p><strong>Note:</strong> This is a draft. Please review and complete the content.</p>",
                "<hr />",
            ]

            for section in sections:
                content_parts.append(f"<h2>{section}</h2>")
                content_parts.append("<p>[Content needed]</p>")

            content = "\n".join(content_parts)

            # Create the page
            result = self.confluence_service.create_page(
                title=f"[DRAFT] {title}",
                content=content,
            )

            if result:
                logger.info(
                    f"Successfully created Confluence page: {result.get('url')}"
                )
            else:
                logger.warning(f"Failed to create Confluence page for {ticket_key}")

        except Exception as e:
            logger.error(f"Error creating Confluence article: {e}", exc_info=True)

    def _update_existing_confluence_article(
        self,
        article_title: str,
        suggested_changes: str,
        redrafted_content: Optional[str],
        ticket_key: str,
    ) -> None:
        """
        Update an existing Confluence article with suggested changes.

        Args:
            article_title: Title of the article to update
            suggested_changes: Description of what changes are needed
            redrafted_content: Optional complete redrafted content (HTML)
            ticket_key: The ticket key for logging and reference
        """
        try:
            logger.info(f"Updating Confluence article: '{article_title}'")

            # Find the page by title
            page = self.confluence_service.find_page_by_title(article_title)

            if not page:
                logger.warning(
                    f"Could not find Confluence page '{article_title}'. "
                    "Creating as new page instead."
                )
                # Create a new page with the suggested changes
                content = f"<p><em>Original article '{article_title}' not found. "
                content += f"Created from ticket {ticket_key}</em></p>"
                content += f"<h2>Suggested Changes</h2><p>{suggested_changes}</p>"

                if redrafted_content:
                    content += f"<h2>Content</h2>{redrafted_content}"

                self.confluence_service.create_page(
                    title=f"[DRAFT] {article_title}",
                    content=content,
                )
                return

            # If we have redrafted content, use it; otherwise add a comment section
            if redrafted_content:
                # Update with the complete redrafted content
                version_comment = (
                    f"Updated based on ticket {ticket_key}: {suggested_changes}"
                )
                result = self.confluence_service.update_page(
                    page_id=page["id"],
                    title=page["title"],
                    content=redrafted_content,
                    version_comment=version_comment,
                )
            else:
                # Get current content and append suggestions
                current_page = self.confluence_service.get_page_content(page["id"])
                if not current_page:
                    logger.warning(f"Could not retrieve content for page {page['id']}")
                    return

                current_content = current_page.get("content", "")

                # Append suggested changes as a new section
                updated_content = current_content
                updated_content += "\n<hr />\n"
                updated_content += f"<h2>Suggested Updates (from {ticket_key})</h2>"
                updated_content += f"<p>{suggested_changes}</p>"
                updated_content += f"<p><em>Added automatically on {time.strftime('%Y-%m-%d')}</em></p>"

                version_comment = f"Added suggestions from ticket {ticket_key}"
                result = self.confluence_service.update_page(
                    page_id=page["id"],
                    title=page["title"],
                    content=updated_content,
                    version_comment=version_comment,
                )

            if result:
                logger.info(
                    f"Successfully updated Confluence page: {result.get('url')}"
                )
            else:
                logger.warning(f"Failed to update Confluence page '{article_title}'")

        except Exception as e:
            logger.error(f"Error updating Confluence article: {e}", exc_info=True)

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

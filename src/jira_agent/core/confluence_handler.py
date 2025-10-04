"""Confluence integration handler for JIRA agent."""

import json
import time
import logging
from typing import Optional, List, Dict, Any, Set
from ..atlassian import confluence
from ..agent import llm
from ..prompts import PromptTemplate, load_prompt_values


logger = logging.getLogger(__name__)


class ConfluenceHandler:
    """Handles Confluence integration for ticket analysis and documentation."""

    def __init__(
        self,
        confluence_service: confluence.Client,
        llm_service: llm.LLM,
    ):
        """
        Initialize the Confluence handler.

        Args:
            confluence_service: Confluence API client
            llm_service: LLM service for generating queries and analysis
        """
        self.confluence_service = confluence_service
        self.llm_service = llm_service

    def search_for_ticket(self, ticket_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate search queries and find relevant Confluence articles.

        Args:
            ticket_data: The ticket data dictionary

        Returns:
            List of relevant Confluence articles (deduplicated)
        """
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
            return self._execute_searches(search_queries)

        except Exception as e:
            logger.error(f"Error searching Confluence: {e}", exc_info=True)
            return []

    def _generate_search_queries(self, ticket_data: Dict[str, Any]) -> List[str]:
        """Generate search queries using LLM."""
        system_prompt, instruction_text, examples = load_prompt_values(
            env_var="PROMPT_CONFLUENCE_SEARCH",
            default_filename="confluence_search.prompt",
        )
        search_template = PromptTemplate(
            system_prompt=system_prompt,
            instruction_template=instruction_text,
        )

        formatted_messages = search_template.format_messages(
            ticket_data=ticket_data,
            examples=examples,
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

    def _execute_searches(self, search_queries: List[str]) -> List[Dict[str, Any]]:
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

    def submit_analysis(self, llm_response: str, ticket_key: str = "Unknown") -> None:
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
                self._create_new_article(
                    title=analysis.get("proposedTitle"),
                    sections=analysis.get("sections", []),
                    ticket_key=ticket_key,
                )

            # Handle existing article updates
            existing_updates = analysis.get("existingArticleUpdates", [])
            if existing_updates:
                for update in existing_updates:
                    self._update_existing_article(
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

    def _create_new_article(
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

    def _update_existing_article(
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

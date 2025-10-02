from atlassian import Confluence
from pprint import pprint
from typing import List, Dict, Any, Optional


class Client:
    def __init__(
        self, server: str, email: str, token: str, space_key: Optional[str] = None
    ):
        """
        Initialize Confluence client.

        Args:
            server: Confluence server URL (e.g., 'https://your-domain.atlassian.net')
            email: User email for authentication
            token: API token for authentication
            space_key: Optional default space key to search within
        """
        self.server = server
        self.email = email
        self.token = token
        self.space_key = space_key
        self.confluence = Confluence(
            url=self.server,
            username=self.email,
            password=self.token,
            cloud=True,  # Set to True for Atlassian Cloud, False for Server
        )

    def test_connection(self):
        """Test the Confluence connection by getting current user info."""
        try:
            # Some versions of atlassian-python-api lack get_current_user on Confluence.
            # Use a lightweight CQL query as a connectivity check instead.
            _ = self.confluence.cql("type=page", limit=1)
            return True
        except Exception as e:
            print(f"Failed to connect to Confluence: {e}")
            return False

    def search_articles(
        self, query: str, space_key: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for articles using CQL (Confluence Query Language).

        Args:
            query: Search query text
            space_key: Space to search in (uses default if not provided)
            limit: Maximum number of results to return

        Returns:
            List of search results with page information
        """
        try:
            search_space = space_key or self.space_key

            # Build CQL query
            # Search both title and text to improve match rate
            cql_parts = [f'(title ~ "{query}" OR text ~ "{query}")', "type=page"]
            if search_space:
                cql_parts.append(f'space="{search_space}"')

            cql = " AND ".join(cql_parts)

            results = self.confluence.cql(cql, limit=limit)

            # Extract relevant information from results
            articles = []
            for result in results.get("results", []):
                content = result.get("content", {})
                articles.append(
                    {
                        "id": content.get("id"),
                        "title": content.get("title"),
                        "type": content.get("type"),
                        "space": content.get("space", {}).get("key"),
                        "url": f"{self.server}/wiki{content.get('_links', {}).get('webui', '')}",
                    }
                )

            return articles

        except Exception as e:
            print(f"Error searching Confluence: {e}")
            return []

    def get_page_content(
        self, page_id: str, expand: str = "body.storage,version"
    ) -> Optional[Dict[str, Any]]:
        """
        Get full content of a specific Confluence page.

        Args:
            page_id: The Confluence page ID
            expand: Fields to expand in the response

        Returns:
            Dictionary containing page information and content
        """
        try:
            page = self.confluence.get_page_by_id(page_id=page_id, expand=expand)

            return {
                "id": page.get("id"),
                "title": page.get("title"),
                "space": page.get("space", {}).get("key"),
                "content": page.get("body", {}).get("storage", {}).get("value", ""),
                "version": page.get("version", {}).get("number"),
                "url": f"{self.server}/wiki{page.get('_links', {}).get('webui', '')}",
            }

        except Exception as e:
            print(f"Error getting page content: {e}")
            return None

    def search_by_label(
        self, label: str, space_key: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for articles by label.

        Args:
            label: Label to search for
            space_key: Space to search in (uses default if not provided)
            limit: Maximum number of results to return

        Returns:
            List of pages with the specified label
        """
        try:
            search_space = space_key or self.space_key

            cql_parts = [f'label="{label}"', "type=page"]
            if search_space:
                cql_parts.append(f'space="{search_space}"')

            cql = " AND ".join(cql_parts)

            results = self.confluence.cql(cql, limit=limit)

            articles = []
            for result in results.get("results", []):
                content = result.get("content", {})
                articles.append(
                    {
                        "id": content.get("id"),
                        "title": content.get("title"),
                        "type": content.get("type"),
                        "space": content.get("space", {}).get("key"),
                        "url": f"{self.server}/wiki{content.get('_links', {}).get('webui', '')}",
                    }
                )

            return articles

        except Exception as e:
            print(f"Error searching by label: {e}")
            return []

    def create_page(
        self,
        title: str,
        content: str,
        space_key: Optional[str] = None,
        parent_id: Optional[str] = None,
        status: str = "draft",
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new Confluence page (draft or published).

        Args:
            title: Page title
            content: Page content in Confluence storage format (HTML)
            space_key: Space to create the page in (uses default if not provided)
            parent_id: Optional parent page ID
            status: Page status - "draft" or "current" (default: "draft")

        Returns:
            Dictionary with page information (id, title, url) or None if failed
        """
        try:
            target_space = space_key or self.space_key
            if not target_space:
                print("Error: No space key provided or configured")
                return None

            # Create the page using the atlassian-python-api library
            # Note: The library may not support draft status directly, so we create as current
            page = self.confluence.create_page(
                space=target_space,
                title=title,
                body=content,
                parent_id=parent_id,
                type="page",
                representation="storage",
            )

            return {
                "id": page.get("id"),
                "title": page.get("title"),
                "space": page.get("space", {}).get("key"),
                "url": f"{self.server}/wiki{page.get('_links', {}).get('webui', '')}",
                "version": page.get("version", {}).get("number"),
            }

        except Exception as e:
            print(f"Error creating Confluence page: {e}")
            return None

    def update_page(
        self,
        page_id: str,
        title: str,
        content: str,
        version_comment: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing Confluence page.

        Args:
            page_id: The ID of the page to update
            title: Page title (must match existing or be updated)
            content: New page content in Confluence storage format (HTML)
            version_comment: Optional comment describing the changes

        Returns:
            Dictionary with updated page information or None if failed
        """
        try:
            # Get current page to get version number
            current_page = self.confluence.get_page_by_id(
                page_id=page_id, expand="version"
            )
            if not current_page:
                print(f"Error: Could not find page with ID {page_id}")
                return None

            current_version = current_page.get("version", {}).get("number", 1)

            # Update the page
            updated_page = self.confluence.update_page(
                page_id=page_id,
                title=title,
                body=content,
                parent_id=(
                    current_page.get("ancestors", [{}])[-1].get("id")
                    if current_page.get("ancestors")
                    else None
                ),
                type="page",
                representation="storage",
                minor_edit=False,
                version_comment=version_comment or "Updated by JIRA Agent",
            )

            return {
                "id": updated_page.get("id"),
                "title": updated_page.get("title"),
                "space": updated_page.get("space", {}).get("key"),
                "url": f"{self.server}/wiki{updated_page.get('_links', {}).get('webui', '')}",
                "version": updated_page.get("version", {}).get("number"),
            }

        except Exception as e:
            print(f"Error updating Confluence page: {e}")
            return None

    def find_page_by_title(
        self, title: str, space_key: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find a page by its exact title.

        Args:
            title: Exact page title to search for
            space_key: Space to search in (uses default if not provided)

        Returns:
            Dictionary with page information or None if not found
        """
        try:
            target_space = space_key or self.space_key

            cql_parts = [f'title="{title}"', "type=page"]
            if target_space:
                cql_parts.append(f'space="{target_space}"')

            cql = " AND ".join(cql_parts)
            results = self.confluence.cql(cql, limit=1)

            if results.get("results"):
                content = results["results"][0].get("content", {})
                return {
                    "id": content.get("id"),
                    "title": content.get("title"),
                    "type": content.get("type"),
                    "space": content.get("space", {}).get("key"),
                    "url": f"{self.server}/wiki{content.get('_links', {}).get('webui', '')}",
                }

            return None

        except Exception as e:
            print(f"Error finding page by title: {e}")
            return None

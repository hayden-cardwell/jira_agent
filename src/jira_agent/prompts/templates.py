from typing import Any, Dict, List, Tuple
import os
from pathlib import Path


class PromptTemplate:
    """Base class for managing prompt templates with ticket-data separation."""

    def __init__(self, system_prompt: str, instruction_template: str):
        self.system_prompt = system_prompt.strip()
        self.instruction_template = instruction_template.strip()

    def _format_ticket_context(self, ticket_data: Dict[str, Any]) -> str:
        """Render a comprehensive ticket summary from raw dict data."""
        key = ticket_data.get("key", "")
        fields = (
            ticket_data.get("fields", {}) if "fields" in ticket_data else ticket_data
        )

        summary = fields.get("summary", "")
        description = fields.get("description", "") or ""

        # Get resolution details
        resolution = fields.get("resolution", {}) or {}
        resolution_name = (
            resolution.get("name") if isinstance(resolution, dict) else str(resolution)
        )
        resolution_description = (
            resolution.get("description", "") if isinstance(resolution, dict) else ""
        )

        # Get status details
        status = fields.get("status", {}) or {}
        status_name = status.get("name") if isinstance(status, dict) else str(status)

        # Get assignee and reporter
        assignee = fields.get("assignee", {}) or {}
        assignee_name = (
            assignee.get("displayName", "") if isinstance(assignee, dict) else ""
        )
        reporter = fields.get("reporter", {}) or {}
        reporter_name = (
            reporter.get("displayName", "") if isinstance(reporter, dict) else ""
        )

        # Get priority and issue type
        priority = fields.get("priority", {}) or {}
        priority_name = priority.get("name", "") if isinstance(priority, dict) else ""
        issuetype = fields.get("issuetype", {}) or {}
        issuetype_name = (
            issuetype.get("name", "") if isinstance(issuetype, dict) else ""
        )

        # Get labels and components
        labels = fields.get("labels", []) or []
        components = fields.get("components", []) or []
        component_names = [
            comp.get("name", "") for comp in components if isinstance(comp, dict)
        ]

        # Get timestamps
        created = fields.get("created", "")
        updated = fields.get("updated", "")
        resolved = fields.get("resolutiondate", "")

        # Get comments with full content
        comments_container = fields.get("comment", {}) or {}
        comments = (
            comments_container.get("comments", [])
            if isinstance(comments_container, dict)
            else []
        )
        comment_summaries = []
        for c in comments:
            author = (
                (c.get("author", {}) or {}).get("displayName")
                if isinstance(c, dict)
                else None
            )
            body = c.get("body") if isinstance(c, dict) else None
            created_date = c.get("created", "") if isinstance(c, dict) else ""
            if body and isinstance(body, str):
                # Include full comment content, not just first line
                body_content = body.strip()
                # Truncate very long comments but keep more content
                if len(body_content) > 1000:
                    body_content = body_content[:1000] + "..."
            else:
                body_content = ""
            comment_summaries.append(
                f"- {author or 'Unknown'} ({created_date}): {body_content}"
            )

        # Get attachment metadata only (not full content)
        attachments = fields.get("attachment", []) or []
        attachment_info = []
        for att in attachments:
            if isinstance(att, dict):
                filename = att.get("filename", "")
                size = att.get("size", "")
                mimetype = att.get("mimeType", "")
                created_date = att.get("created", "")
                author = (att.get("author", {}) or {}).get("displayName", "")

                info_parts = [filename]
                if size:
                    # Convert bytes to human readable format
                    if isinstance(size, (int, str)) and str(size).isdigit():
                        size_int = int(size)
                        if size_int < 1024:
                            size_str = f"{size_int}B"
                        elif size_int < 1024 * 1024:
                            size_str = f"{size_int // 1024}KB"
                        else:
                            size_str = f"{size_int // (1024 * 1024)}MB"
                        info_parts.append(size_str)
                if mimetype:
                    info_parts.append(mimetype)
                if author:
                    info_parts.append(f"by {author}")
                if created_date:
                    info_parts.append(created_date)

                attachment_info.append(" - ".join(info_parts))

        # Build comprehensive ticket context
        lines = [
            f"Key: {key}",
            f"Summary: {summary}",
            f"Issue Type: {issuetype_name}",
            f"Status: {status_name}",
            f"Resolution: {resolution_name}",
        ]

        if resolution_description:
            lines.append(f"Resolution Description: {resolution_description}")

        lines.extend(
            [
                f"Priority: {priority_name}",
                f"Reporter: {reporter_name}",
                f"Assignee: {assignee_name}",
                f"Created: {created}",
                f"Updated: {updated}",
                f"Resolved: {resolved}",
            ]
        )

        if labels:
            lines.append(f"Labels: {', '.join(labels)}")

        if component_names:
            lines.append(f"Components: {', '.join(component_names)}")

        if attachment_info:
            lines.append(f"Attachments ({len(attachment_info)}):")
            lines.extend([f"- {info}" for info in attachment_info])

        lines.append("Description:")
        if isinstance(description, str) and description:
            # Keep more of the description content
            if len(description) > 5000:
                lines.append(description[:5000] + "...")
            else:
                lines.append(description)
        else:
            lines.append("No description provided")

        if comment_summaries:
            lines.append(f"Comments ({len(comment_summaries)}):")
            lines.extend(comment_summaries)

        return "\n".join(lines)

    def format_messages(
        self,
        ticket_data: Dict[str, Any],
        examples: List[Dict[str, Any]] = None,
        confluence_results: List[Dict[str, Any]] = None,
        **kwargs,
    ) -> List[Dict[str, str]]:
        """Format as messages array for multi-shot prompting with prompt caching optimization."""
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add few-shot examples if provided - these are static and cacheable
        if examples:
            for example in examples:
                # Only handle standard message format: {"role": "user/assistant", "content": "..."}
                if "role" in example and "content" in example:
                    messages.append(
                        {"role": example["role"], "content": example["content"]}
                    )
                else:
                    raise ValueError(
                        f"Invalid example format. Expected 'role' and 'content' keys, got: {list(example.keys())}"
                    )

        # Add instructions first (static and cacheable)
        instructions = (
            self.instruction_template.format(**kwargs)
            if kwargs
            else self.instruction_template
        )

        # For prompt caching optimization, put ticket-specific context at the very end
        ticket_context = self._format_ticket_context(ticket_data)
        # print(ticket_context)

        # Format Confluence results if provided
        confluence_context = ""
        if confluence_results:
            confluence_context = "\n\n## Existing Confluence Articles\n"
            confluence_context += (
                f"Found {len(confluence_results)} potentially relevant articles:\n"
            )
            for i, article in enumerate(confluence_results, 1):
                confluence_context += f"\n{i}. {article.get('title', 'Unknown')}\n"
                confluence_context += f"   Space: {article.get('space', 'Unknown')}\n"
                confluence_context += f"   URL: {article.get('url', 'N/A')}\n"
                if article.get("content"):
                    confluence_context += f"   Content: {article.get('content')}\n"

        # Final user message with all context
        messages.append(
            {
                "role": "user",
                "content": f"## Instructions\n{instructions}\n\n## Ticket Context\n{ticket_context}{confluence_context}",
            }
        )

        return messages


def _parse_prompt_file(path: Path) -> Tuple[Dict[str, List[str]], List[Dict[str, str]]]:
    """Parse a .prompt file into sections and few-shot messages.

    The .prompt file format uses headings:
      - "# system"
      - "# instructions"
      - "# few-shot" with message blocks introduced by lines starting with "> ROLE".
    """
    sections: Dict[str, List[str]] = {"system": [], "instructions": []}
    messages: List[Dict[str, str]] = []
    current_section: str | None = None
    current_message: Dict[str, Any] | None = None

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            if current_section == "few-shot" and current_message:
                messages.append(
                    {
                        "role": current_message["role"],
                        "content": "\n".join(current_message["lines"]).strip(),
                    }
                )
                current_message = None
            current_section = line[2:].strip().lower()
            continue

        if current_section == "few-shot":
            if line.startswith("> "):
                if current_message:
                    messages.append(
                        {
                            "role": current_message["role"],
                            "content": "\n".join(current_message["lines"]).strip(),
                        }
                    )
                current_message = {"role": line[2:].strip(), "lines": []}
            elif current_message is not None:
                current_message["lines"].append(line)
            continue

        if current_section in sections:
            sections[current_section].append(line)

    if current_section == "few-shot" and current_message:
        messages.append(
            {
                "role": current_message["role"],
                "content": "\n".join(current_message["lines"]).strip(),
            }
        )

    return sections, messages


def load_prompt_values(
    env_var: str, default_filename: str
) -> Tuple[str, str, List[Dict[str, str]]]:
    """Load system prompt, instruction text, and few-shot examples for a prompt.

    Args:
        env_var: Environment variable name that can override the prompt file path.
        default_filename: File name under the repository-level "prompts/" directory.

    Returns:
        Tuple of (system_text, instruction_text, few_shot_messages)
    """
    default_path = Path(__file__).resolve().parents[3] / "prompts" / default_filename
    prompt_path = Path(os.environ.get(env_var) or default_path)

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    sections, messages = _parse_prompt_file(prompt_path)

    system_text = "\n".join(sections.get("system", [])).strip()
    instruction_text = "\n".join(sections.get("instructions", [])).strip()

    if not system_text:
        raise ValueError(f"System section is empty in prompt file: {prompt_path}")

    if not instruction_text:
        raise ValueError(f"Instructions section is empty in prompt file: {prompt_path}")

    return system_text, instruction_text, messages

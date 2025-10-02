"""
Prompts for analyzing tickets and drafting docs.
"""


class TicketAnalyzerPrompts:
    """Prompt strings for analyzing tickets and drafting docs."""

    SYSTEM_PROMPT = (
        "You are a technical documentation assistant that analyzes resolved support tickets "
        "to determine if they require troubleshooting articles or updates to existing documentation. "
        "Be concise, accurate, and actionable."
    )

    ANALYSIS_INSTRUCTION = (
        "Analyze this resolved ticket and determine:\n"
        "1. Does this represent a recurring issue worth documenting?\n"
        "2. Review any existing Confluence articles provided. Do any already cover this issue adequately?\n"
        "3. If an existing article should be updated, specify which article and what changes are needed.\n"
        "4. If a new article is needed, propose a title and key sections.\n"
        "5. For existing article updates, optionally provide the complete redrafted content with improvements incorporated.\n\n"
        "Return a JSON object with:\n"
        '- "needsNewArticle": bool (true if a completely new article is needed)\n'
        '- "existingArticleUpdates": [{"articleTitle": string, "suggestedChanges": string, "redraftedContent": string|null}] (what to add/modify in existing articles)\n'
        '- "proposedTitle": string|null (for new article, if needed)\n'
        '- "sections": [string] (sections for new article, if needed)\n'
        '- "reasoning": string (brief explanation of your decision)'
    )

    ARTICLE_REDRAFT_INSTRUCTION = (
        "When updating an existing article, redraft it by incorporating the specified improvements:\n\n"
        "Original article:\n"
        "{original_content}\n\n"
        "Improvements needed:\n"
        "{suggested_changes}\n\n"
        "Guidelines:\n"
        "- Preserve the article's existing structure and headings\n"
        "- Add new content in appropriate sections\n"
        "- Update or clarify existing instructions\n"
        "- Maintain consistent tone and formatting\n"
        "- Include specific details from the ticket resolution\n\n"
        "Return the complete redrafted article."
    )

    ARTICLE_DRAFT_INSTRUCTION = (
        "Draft a troubleshooting article using this structure:\n"
        "- Title\n"
        "- Problem Description\n"
        "- Symptoms\n"
        "- Root Cause\n"
        "- Solution Steps\n"
        "- Prevention / Best Practices\n\n"
        "Title: {article_title}\n"
        "Focus: {focus_areas}"
    )

    CORRECT_FEW_SHOT_EXAMPLES = [
        # Example 1
        {
            "role": "user",
            "content": """Key: CSOPS-1234
Summary: CrowdStrike is failing to install. 
Issue Type: Troubleshooting
Status: Done
Resolution: Done
Priority: Medium
Reporter: Hayden Cardwell
Assignee: Hayden Cardwell
Created: 2025-09-27T10:21:02.620-0500
Updated: 2025-09-29T05:50:23.386-0500
Resolved: 2025-09-29T05:44:08.191-0500
Labels: security, endpoint-protection
Description:
CrowdStrike is failing to install on my Windows system, please help. 
Comments (1):
- Hayden Cardwell (2025-09-29T05:50:23.386-0500): Issue was TLS inspection blocking the connection. Added firewall exception.""",
        },
        {
            "role": "assistant",
            "content": """{"needsNewArticle": true, "existingArticleUpdates": [], "proposedTitle": "CrowdStrike Installation Fails Due to TLS Inspection", "sections": ["Problem Description", "Symptoms", "Root Cause", "Solution Steps", "Prevention"], "reasoning": "No existing articles found. This is a specific technical issue with TLS inspection that warrants its own troubleshooting guide."}""",
        },
        # Example 2
        {
            "role": "user",
            "content": """Key: CSOPS-5678
Summary: User unable to access dashboard after password reset
Issue Type: Bug
Status: Done
Resolution: Fixed
Priority: High
Reporter: Jane Smith
Assignee: Support Team
Created: 2025-09-28T14:30:15.123-0500
Updated: 2025-09-28T16:45:30.456-0500
Resolved: 2025-09-28T16:30:22.789-0500
Labels: authentication, dashboard-access
Description:
Customer reported they couldn't log in after resetting their password. Browser was caching old credentials.
Comments (2):
- Support Agent (2025-09-28T15:15:20.234-0500): Cleared browser cache and cookies, issue resolved
- Jane Smith (2025-09-28T16:45:30.456-0500): Thank you, that worked!

## Existing Confluence Articles
Found 1 potentially relevant articles:

1. Login Troubleshooting Guide
   Space: SUPPORT
   URL: https://example.atlassian.net/wiki/spaces/SUPPORT/pages/123/Login+Troubleshooting
   Content: <h1>Login Troubleshooting Guide</h1><h2>Common Issues</h2><ul><li>Incorrect password</li><li>Account locked</li><li>Session expired</li></ul><h2>Solutions</h2><p>If you cannot log in, try resetting your password or contact support.</p>""",
        },
        {
            "role": "assistant",
            "content": """{"needsNewArticle": false, "existingArticleUpdates": [{"articleTitle": "Login Troubleshooting Guide", "suggestedChanges": "Add a new section under 'Common Issues' for 'Login fails after password reset' with specific browser cache clearing steps for Chrome, Firefox, and Edge.", "redraftedContent": "<h1>Login Troubleshooting Guide</h1><h2>Common Issues</h2><ul><li>Incorrect password</li><li>Account locked</li><li>Session expired</li><li>Login fails after password reset (browser cache issue)</li></ul><h2>Solutions</h2><p><strong>For browser cache issues after password reset:</strong></p><ol><li>Clear your browser cache and cookies:<ul><li><strong>Chrome:</strong> Settings → Privacy and security → Clear browsing data → Select 'Cookies and other site data' and 'Cached images and files'</li><li><strong>Firefox:</strong> Settings → Privacy & Security → Cookies and Site Data → Clear Data</li><li><strong>Edge:</strong> Settings → Privacy, search, and services → Clear browsing data → Choose what to clear</li></ul></li><li>Try logging in with an incognito/private browsing window</li><li>If issue persists, try a different browser</li></ol><p><strong>For other login issues:</strong> Try resetting your password or contact support.</p>"}], "proposedTitle": null, "sections": [], "reasoning": "Existing Login Troubleshooting Guide covers this topic area but lacks information about browser cache issues after password reset. Updating the existing article is better than creating a new one."}""",
        },
        # Example 3: Already covered adequately
        {
            "role": "user",
            "content": """Key: CSOPS-9999
Summary: VPN connection drops intermittently
Issue Type: Support
Status: Done
Resolution: Resolved
Priority: Low
Reporter: User Name
Assignee: Support Team
Created: 2025-09-28T09:00:00.000-0500
Updated: 2025-09-28T09:30:00.000-0500
Resolved: 2025-09-28T09:30:00.000-0500
Labels: vpn, network
Description:
User experiencing intermittent VPN disconnections. Advised to restart router and VPN client. Issue resolved.
Comments (1):
- Support Agent (2025-09-28T09:30:00.000-0500): Standard troubleshooting resolved the issue.

## Existing Confluence Articles
Found 1 potentially relevant articles:

1. VPN Connection Issues Troubleshooting
   Space: SUPPORT
   URL: https://example.atlassian.net/wiki/spaces/SUPPORT/pages/456/VPN+Troubleshooting
   Content: <h1>VPN Connection Issues</h1><h2>Intermittent Disconnections</h2><p>If your VPN connection drops intermittently:</p><ol><li>Restart your router</li><li>Restart the VPN client</li><li>Check for network interference</li><li>Update VPN client to latest version</li></ol><h2>Cannot Connect</h2><p>If you cannot establish a VPN connection, verify your credentials and network settings.</p>""",
        },
        {
            "role": "assistant",
            "content": """{"needsNewArticle": false, "existingArticleUpdates": [], "proposedTitle": null, "sections": [], "reasoning": "The existing 'VPN Connection Issues Troubleshooting' article already covers this exact scenario with appropriate troubleshooting steps. No new article or updates needed."}""",
        },
    ]

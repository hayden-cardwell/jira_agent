"""
Prompts for generating Confluence search queries from ticket data.
"""


class ConfluenceSearchPrompts:
    """Prompt strings for generating optimal Confluence search queries."""

    SYSTEM_PROMPT = (
        "You are a search query optimization assistant. Your job is to analyze support tickets "
        "and generate optimal search queries to find relevant troubleshooting articles in a knowledge base. "
        "Generate SHORT, SIMPLE queries using only 2-4 key terms. Avoid long complex phrases. "
        "Focus on the most important technical keywords that would appear in documentation. "
        "Return output as raw JSON only — no markdown, no code fences, no prose."
    )

    QUERY_GENERATION_INSTRUCTION = (
        "Analyze this ticket and generate 3-4 SHORT search queries (2-4 words each) that would find relevant help articles. "
        "IMPORTANT: Keep queries simple and focused. Use only the most essential keywords.\n\n"
        "Focus on:\n"
        "- Product names and key technical terms\n"
        "- Specific error types or symptoms (simplified)\n"
        "- Problem category (1-2 words)\n\n"
        "BAD examples (too long/complex):\n"
        '- "CrowdStrike Falcon Sensor installation TLS SSL inspection"\n'
        '- "certificate pinning proxy HTTPS interception"\n\n'
        "GOOD examples (short/focused):\n"
        '- "CrowdStrike installation"\n'
        '- "Falcon connectivity"\n'
        '- "TLS proxy"\n\n'
        "Output format requirements:\n"
        "- Return ONLY a JSON array of strings\n"
        "- Each query should be 2-4 words maximum\n"
        "- Do NOT include markdown, backticks, explanations, or any extra text\n\n"
        'Example of valid output: ["query1", "query2", "query3", "query4"]'
    )

    FEW_SHOT_EXAMPLES = [
        # Example 1: TLS/SSL inspection blocking CrowdStrike
        {
            "role": "user",
            "content": """Key: CSOPS-9284
Summary: CrowdStrike install failing — can't reach cloud
Description: Trying to deploy the Falcon Sensor on a few Windows 11 servers. The installer fails with an error saying it can't connect to the cloud. I ran `Test-NetConnection falcon.us-2.crowdstrike.com -Port 443` and DNS resolution works. No firewall rules appear to be blocking it.
Resolution: TLS/SSL inspection was intercepting and modifying the Falcon Sensor's outbound HTTPS requests, breaking certificate-pinned communication during install. Customer's network team created an exception to bypass TLS inspection and allow outbound HTTPS traffic to CrowdStrike's required cloud domains.
Labels: crowdstrike, install, tls-inspection""",
        },
        {
            "role": "assistant",
            "content": """["CrowdStrike installation", "Falcon connectivity", "TLS proxy", "cloud firewall"]""",
        },
        # Example 2: Browser cache causing login issues
        {
            "role": "user",
            "content": """Key: CSOPS-5678
Summary: User unable to access dashboard after password reset
Description: Customer reported they couldn't log in after resetting their password. Browser was caching old credentials.
Resolution: Cleared browser cache and cookies, issue resolved
Labels: authentication, dashboard-access""",
        },
        {
            "role": "assistant",
            "content": """["login password reset", "authentication cache", "browser credentials", "dashboard access"]""",
        },
        # Example 3: Database connection timeout
        {
            "role": "user",
            "content": """Key: CSOPS-3456
Summary: Application timing out connecting to database
Description: Production app is getting connection timeout errors when trying to reach the PostgreSQL database. Error: "connection timeout after 30 seconds". Network team confirms no packet loss between app and DB servers.
Resolution: Connection pool was exhausted. Increased max_connections in postgresql.conf from 100 to 300 and adjusted application pool size.
Labels: database, postgresql, performance""",
        },
        {
            "role": "assistant",
            "content": """["PostgreSQL timeout", "connection pool", "database performance", "max connections"]""",
        },
        # Example 4: Memory leak in microservice
        {
            "role": "user",
            "content": """Key: CSOPS-7890
Summary: API service crashing with OOM errors
Description: Our user-service microservice keeps crashing every 6-8 hours with Out of Memory errors. Heap dumps show memory usage growing continuously. Running on Kubernetes with 4GB memory limit.
Resolution: Found memory leak in event listener that wasn't being properly garbage collected. Updated code to remove listeners on cleanup and increased memory limit to 6GB as temporary buffer.
Labels: kubernetes, memory-leak, microservices""",
        },
        {
            "role": "assistant",
            "content": """["microservice memory leak", "Kubernetes OOM", "memory troubleshooting", "heap crash"]""",
        },
    ]

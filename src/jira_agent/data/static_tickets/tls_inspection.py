ticket_data = {
    "key": "CSOPS-9284",
    "fields": {
        "summary": "CrowdStrike install failing — can’t reach cloud",
        "description": (
            "Trying to deploy the Falcon Sensor on a few Windows 11 servers. "
            "The installer fails with an error saying it can’t connect to the cloud. "
            "I ran `Test-NetConnection falcon.us-2.crowdstrike.com -Port 443` and DNS resolution works. "
            "No firewall rules appear to be blocking it."
        ),
        "status": {"name": "Resolved"},
        "resolution": {
            "name": "Fixed",
            "description": (
                "TLS/SSL inspection was intercepting and modifying the Falcon Sensor's outbound HTTPS requests, "
                "breaking certificate-pinned communication during install.\n\n"
                "Customer’s network team created an exception to bypass TLS inspection and allow outbound HTTPS traffic "
                "to CrowdStrike’s required cloud domains. After the changes, installation succeeded and the host "
                "registered with the console.\n\n"
                "Sensor installed successfully and appeared in the Falcon UI. No further errors."
            ),
        },
        "assignee": {"displayName": "CrowdStrike Support"},
        "reporter": {"displayName": "Server Admin"},
        "priority": {"name": "Medium"},
        "issuetype": {"name": "Bug"},
        "labels": ["crowdstrike", "install", "tls-inspection"],
        "components": [{"name": "Sensor Deployment"}],
        "created": "2025-09-28T13:42:00.000-0500",
        "updated": "2025-09-29T08:01:00.000-0500",
        "resolutiondate": "2025-09-29T07:55:00.000-0500",
        "comment": {
            "comments": [
                {
                    "author": {"displayName": "CrowdStrike Support"},
                    "body": (
                        "Thanks for the info. Let's check if the device is able to complete a proper TLS handshake. "
                        "Can you run the following command on one of the affected servers and paste the full output?\n\n"
                        "```\ncurl -v https://falcon.us-2.crowdstrike.com\n```"
                    ),
                    "created": "2025-09-28T14:00:00.000-0500",
                },
                {
                    "author": {"displayName": "Server Admin"},
                    "body": (
                        "Here’s the output. Looks like the certificate is signed by our internal CA, not CrowdStrike."
                    ),
                    "created": "2025-09-28T14:08:00.000-0500",
                },
                {
                    "author": {"displayName": "CrowdStrike Support"},
                    "body": (
                        "That helps. Based on the output, your environment is likely doing TLS/SSL inspection through a DPI device or proxy. "
                        "The Falcon Sensor uses certificate pinning during install and can’t communicate properly if the TLS connection is intercepted or re-signed.\n\n"
                        "You’ll need to ask your network team to **bypass TLS inspection** and allow outbound HTTPS (port 443) to CrowdStrike’s cloud domains. "
                        "For US-2 customers, that includes:\n\n"
                        "- `falcon.us-2.crowdstrike.com`\n"
                        "- `assets.falcon.us-2.crowdstrike.com`\n"
                        "- `assets-public.falcon.us-2.crowdstrike.com`\n"
                        "- `api.us-2.crowdstrike.com`\n"
                        "- `firehose.us-2.crowdstrike.com`\n"
                        "- All subdomains of `*.cloudsink.net`\n\n"
                        "They should also ensure any proxy or PAC file used returns `DIRECT` for these domains."
                    ),
                    "created": "2025-09-28T14:12:00.000-0500",
                },
                {
                    "author": {"displayName": "Server Admin"},
                    "body": (
                        "Got it. I sent that list to our network admin. They made the changes to bypass TLS inspection and allow those domains."
                    ),
                    "created": "2025-09-28T15:02:00.000-0500",
                },
                {
                    "author": {"displayName": "Server Admin"},
                    "body": (
                        "Just retried the install and it worked—host showed up in the Falcon console within a minute. Looks like that was it."
                    ),
                    "created": "2025-09-28T15:15:00.000-0500",
                },
                {
                    "author": {"displayName": "CrowdStrike Support"},
                    "body": (
                        "Awesome, glad to hear it. Just make sure the bypass stays in place for those domains on all networks where Falcon will be installed or needs to communicate. "
                        "This avoids future issues with registration, updates, and event reporting."
                    ),
                    "created": "2025-09-28T15:20:00.000-0500",
                },
            ]
        },
    },
}

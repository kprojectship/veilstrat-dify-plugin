# VeilStrat Dify plugin privacy

This plugin sends user-selected research queries, country codes, slice filters, company UUIDs and the user's bearer API key to the VeilStrat API at app.veilstrat.com. Returned company research is passed to Dify. No other external service is contacted by plugin code.

The plugin does not collect analytics, write logs, persist credentials, or store research results. Dify manages provider credentials and may retain workflow inputs, outputs and execution history according to the workspace settings. VeilStrat processes API requests, account usage and operational data under its [privacy policy](https://www.veilstrat.com/privacy-policy). These platform retention practices are separate from the plugin's lack of local storage.

Only documented HTTPS API routes are used. Redirects and user-provided destination URLs are not supported. Each API call has a 20-second timeout, and the plugin performs no automatic retries or pagination. Exceptions omit raw response bodies and credentials.

For privacy or security questions, contact support@veilstrat.com. Do not include API keys or private company research in public issues.

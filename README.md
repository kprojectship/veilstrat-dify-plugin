# VeilStrat for Dify

Research company funding, AI hiring and technology-adoption signals with [VeilStrat](https://www.veilstrat.com/) in Dify agents and workflows.

Source repository: https://github.com/kprojectship/veilstrat-dify-plugin

## Setup

Install the VeilStrat plugin, then add your own team API key in its provider settings. Create the key in [VeilStrat Settings > API](https://app.veilstrat.com/). API access requires VeilStrat Pro with the API Access add-on. The plugin is MIT-licensed; VeilStrat service fees and quotas apply separately. Credential validation calls health and usage, which are exempt from the API request budget.

Read the [API overview](https://www.veilstrat.com/developers), [authentication guide](https://app.veilstrat.com/docs/api), [endpoint reference](https://app.veilstrat.com/docs/api/endpoints) and [usage limits](https://app.veilstrat.com/docs/api/rate-limits).

## Tools

| Tool | Purpose |
| --- | --- |
| Search Companies | Request one page using a signal query and optional country codes |
| Get Company Dossier | Retrieve details for a company UUID |
| Search Signal Slices | Filter a catalog-backed slice by minimum score and optional countries |
| Get Filter Catalog | Discover supported queries, technologies and slices |
| Get Account Usage | Inspect API quotas and reset times |
| Check API Connection | Check API connectivity |

## Example

Start with Get Filter Catalog and Get Account Usage. Use Search Companies with `signal:hiring:30d`, countries `US`, page 1 and page size 10. Inspect the response and use Get Company Dossier only for relevant company UUIDs. Use a slice identifier returned by the catalog with Search Signal Slices. The plugin returns the original JSON response so that pagination and evidence remain available. It does not traverse every page or retry requests automatically.

Hiring-derived technology signals indicate hiring demand, not confirmed production deployment. Funding is a financing event, not proof of purchasing budget. Scores prioritize account research; they are not purchase probabilities.

## Network and privacy

Requests go exclusively to `https://app.veilstrat.com/api/v1`; redirects are refused. The plugin sends the API key as a bearer header along with the requested queries, country codes, slice filters and company UUIDs. It has no analytics, persistent storage, arbitrary URL fetching, filesystem operations or code-execution tools. Dify and VeilStrat retain service data according to their own settings and policies. See [PRIVACY.md](PRIVACY.md) and [VeilStrat's privacy policy](https://www.veilstrat.com/privacy-policy).

401 means the key was rejected; 403 means API eligibility is missing; 404 means an identifier was not found; 422 means query validation failed; and 429 means a quota was reached. Stop and inspect account usage and reset times after a quota error. Errors never include raw upstream bodies or bearer credentials.

## Development and validation

Use Python 3.12 and `pip install -r requirements.txt`. Run `python -m unittest discover -s tests -v` for local SDK and transport tests. Package with the official Dify CLI and run the Dify Marketplace Toolkit validator. These local tests do not replace an authenticated installation test in Dify Cloud or Community Edition.

## Support

Contact [support@veilstrat.com](mailto:support@veilstrat.com) with the plugin version and reproducible steps. Never send API keys in an issue or pull request.


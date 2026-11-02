"""Fixed-destination, read-only VeilStrat API transport."""
import math
import re
from typing import Any
from uuid import UUID
import httpx

BASE_URL = "https://app.veilstrat.com/api/v1"

class VeilStratError(ValueError):
    pass

def countries(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if not isinstance(value, str):
        raise VeilStratError("Countries must be comma-separated two-letter codes.")
    result = [code.strip().upper() for code in value.split(",")]
    if any(not re.fullmatch(r"[A-Z]{2}", code) for code in result):
        raise VeilStratError("Countries must be comma-separated two-letter codes.")
    return list(dict.fromkeys(result))

def integer(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        raise VeilStratError(f"{name} must be an integer from {minimum} to {maximum}.")
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise VeilStratError(f"{name} must be an integer from {minimum} to {maximum}.") from None
    if not math.isfinite(number) or not number.is_integer() or not minimum <= number <= maximum:
        raise VeilStratError(f"{name} must be an integer from {minimum} to {maximum}.")
    return int(number)

class VeilStratClient:
    def __init__(self, key: str):
        if not isinstance(key, str) or not key.strip() or any(c.isspace() for c in key):
            raise VeilStratError("Configure a valid VeilStrat team API key.")
        self.key = key

    def request(self, method: str, path: str, *, body=None, params=None) -> dict:
        allowed = {("GET", "/health"), ("GET", "/stats"), ("GET", "/filters"), ("GET", "/slices"), ("POST", "/companies")}
        dossier = method == "GET" and re.fullmatch(r"/companies/[0-9a-fA-F-]{36}", path)
        if (method, path) not in allowed and not dossier:
            raise VeilStratError("Unsupported API operation.")
        try:
            with httpx.Client(timeout=20.0, follow_redirects=False, trust_env=False) as client:
                response = client.request(method, BASE_URL + path, headers={"Authorization": "Bearer " + self.key, "Accept": "application/json"}, json=body, params=params)
        except httpx.HTTPError:
            raise VeilStratError("VeilStrat could not be reached. No automatic retry was attempted.") from None
        if response.status_code != 200:
            messages = {401: "API key rejected. Check VeilStrat Settings > API.", 403: "API access requires an eligible Pro account and the API Access add-on.", 404: "Company or slice not found. Use an identifier returned by search or the filter catalog.", 422: "The query or filters were rejected. Check the current filter catalog.", 429: "API quota reached. Stop and check usage and reset times before trying again."}
            message = messages.get(response.status_code, "VeilStrat returned HTTP " + str(response.status_code) + ". No automatic retry was attempted.")
            retry = response.headers.get("Retry-After", "")
            if response.status_code == 429 and retry.isdigit():
                message += " Retry after " + retry + " seconds."
            raise VeilStratError(message)
        try:
            payload = response.json()
        except ValueError:
            raise VeilStratError("VeilStrat returned an invalid JSON response.") from None
        if not isinstance(payload, dict):
            raise VeilStratError("VeilStrat returned an unexpected response format.")
        return payload

    def invoke(self, operation: str, values: dict) -> dict:
        simple = {"get_health": "/health", "get_usage": "/stats", "get_filters": "/filters"}
        if operation in simple:
            return self.request("GET", simple[operation])
        if operation == "get_company":
            try:
                company_id = str(UUID(str(values.get("company_id", "")).strip()))
            except (ValueError, TypeError, AttributeError):
                raise VeilStratError("Provide a company UUID from search or a VeilStrat webhook.") from None
            return self.request("GET", "/companies/" + company_id)
        if operation == "search_companies":
            query = values.get("signal_query", "")
            if not isinstance(query, str) or not query.strip():
                raise VeilStratError("Provide a signal query from the current filter catalog.")
            page_size = integer(values.get("page_size", 10), "Page size", 1, 50)
            page = integer(values.get("page", 1), "Page", 1, 500)
            if (page - 1) * page_size >= 500:
                raise VeilStratError("Company-search offset must be below 500 records.")
            body = {"signal_query": query.strip(), "page": page, "pageSize": page_size}
            selected_countries = countries(values.get("countries", ""))
            if selected_countries:
                body["countries"] = selected_countries
            return self.request("POST", "/companies", body=body)
        if operation == "search_slices":
            name = values.get("slice", "")
            if not isinstance(name, str) or not name.strip():
                raise VeilStratError("Provide a slice identifier from the filter catalog.")
            params = {"slice": name.strip(), "scoreMin": integer(values.get("score_min", 70), "Minimum score", 0, 100)}
            selected_countries = countries(values.get("countries", ""))
            if selected_countries:
                params["countries"] = ",".join(selected_countries)
            return self.request("GET", "/slices", params=params)
        raise VeilStratError("Unsupported API operation.")

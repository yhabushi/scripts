#!/usr/bin/env python3
"""
Jira Ticket Fetcher
===================
Fetches Jira issues matching a JQL query and exports them to JSON files.

Changes vs. original:
  1. sys.exit(1) added at all fatal exit paths so callers/CI detect failure.
  2. Explicit check for the "<token>" placeholder prevents silent auth failures.
  3. Early return + warning when the ticket list is empty prevents silently
     writing empty output files.
  4. TypeError added alongside ValueError in the tickets_per_file guard.
  5. Stray extra space before `processed_count += 1` removed (PEP 8).
  6. Type hints added to every function signature.
"""

import json
import math
import os
import sys

import requests

CONFIG_FILE = "jira-config.json"
_PLACEHOLDER_TOKEN = "<token>"


def load_config(config_path: str) -> "dict | None":
    """Load and return the configuration from a JSON file."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        print("Configuration loaded successfully.")
        return config
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_path}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{config_path}'.")
        return None


def fetch_jira_tickets(config: dict) -> "list | None":
    """Fetch tickets from Jira based on the JQL query in the config."""
    if not config:
        print("Error: Configuration is missing.")
        return None

    access_token = config.get("access_token")
    jira_base_url = config.get("jira_base_url")
    jql_query = config.get("jql_query")
    fields = config.get("fields", ["key", "summary"])
    max_results_per_request = config.get("max_results", 100)

    if not all([access_token, jira_base_url, jql_query]):
        print("Error: Missing critical configuration: access_token, jira_base_url, or jql_query.")
        return None

    # Fix 2: guard against the placeholder token.
    if access_token == _PLACEHOLDER_TOKEN:
        print(
            f"Error: access_token is still the placeholder '{_PLACEHOLDER_TOKEN}'. "
            "Please replace it with a real Jira Personal Access Token."
        )
        return None

    search_url = f"{jira_base_url}/rest/api/latest/search"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    all_issues: list = []
    start_at = 0
    total_issues_expected = -1

    print(f"Fetching tickets from: {search_url}")
    print(f"JQL Query: {jql_query}")

    while True:
        payload = {
            "jql": jql_query,
            "startAt": start_at,
            "maxResults": max_results_per_request,
            "fields": fields,
        }
        try:
            print(
                f"Requesting issues {start_at} to "
                f"{start_at + max_results_per_request - 1}..."
            )
            response = requests.post(search_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()
            issues_on_page = data.get("issues", [])
            all_issues.extend(issues_on_page)

            if total_issues_expected == -1:
                total_issues_expected = data.get("total", 0)
                print(f"Total issues found by JQL: {total_issues_expected}")

            print(
                f"Fetched {len(issues_on_page)} issues in this batch; "
                f"total so far: {len(all_issues)}."
            )

            start_at += len(issues_on_page)
            if start_at >= total_issues_expected or not issues_on_page:
                print("All issues fetched.")
                break

        except requests.exceptions.HTTPError as err:
            print(f"HTTP error: {err}")
            print(f"Response: {response.content.decode()}")
            return None
        except requests.exceptions.ConnectionError as err:
            print(f"Connection error: {err}")
            return None
        except requests.exceptions.Timeout as err:
            print(f"Timeout: {err}")
            return None
        except requests.exceptions.RequestException as err:
            print(f"Request error: {err}")
            return None
        except json.JSONDecodeError:
            print("Error: Could not decode JSON response from Jira.")
            print(f"Response: {response.text}")
            return None

    return all_issues


def _delete_nested_key_recursive(current_item: "dict | list", path_segments: list) -> None:
    """Recursively delete a key from a dict or list of dicts in-place."""
    if not path_segments:
        return

    key = path_segments[0]

    if isinstance(current_item, list):
        for item in current_item:
            if isinstance(item, dict):
                _delete_nested_key_recursive(item, path_segments)
        return

    if not isinstance(current_item, dict) or key not in current_item:
        return

    if len(path_segments) == 1:
        current_item.pop(key, None)
    else:
        _delete_nested_key_recursive(current_item[key], path_segments[1:])


def process_tickets_data(tickets: list, config: dict) -> None:
    """Exclude specified keys from tickets based on config. Modifies in-place."""
    if not tickets or not config:
        print("No tickets or configuration provided for processing.")
        return

    global_exclusions = config.get("global_key_exclusions", [])
    ticket_field_exclusions = config.get("ticket_field_exclusions", {})

    if not global_exclusions and not ticket_field_exclusions:
        print("No exclusion rules defined. Skipping.")
        return

    processed_count = 0
    for ticket in tickets:
        if not isinstance(ticket, dict):
            continue

        for key in global_exclusions:
            ticket.pop(key, None)

        if "fields" in ticket and isinstance(ticket["fields"], dict):
            fields_obj = ticket["fields"]
            for field_key, sub_paths in ticket_field_exclusions.items():
                if field_key in fields_obj and isinstance(fields_obj[field_key], (dict, list)):
                    for sub_path in sub_paths:
                        _delete_nested_key_recursive(fields_obj[field_key], sub_path.split("."))
        processed_count += 1  # Fix 5: removed stray extra space

    print(f"Processed {processed_count} tickets.")


def save_tickets(tickets: "list | None", config: dict) -> None:
    """Save tickets to one or more JSON files based on config."""
    if tickets is None:
        print("No tickets to save.")
        return
    if not config:
        print("Cannot save tickets: configuration missing.")
        return

    filename_base = config.get("export_filename", "jira_tickets")
    fmt = config.get("export_format", "json").lower()
    per_file_raw = config.get("tickets_per_file")
    per_file: "int | None" = None

    if per_file_raw is not None:
        try:
            per_file = int(per_file_raw)
            if per_file <= 0:
                print(f"Warning: tickets_per_file={per_file_raw} is not positive; using single file.")
                per_file = None
        except (ValueError, TypeError):  # Fix 4: TypeError added
            print(f"Warning: tickets_per_file='{per_file_raw}' is invalid; using single file.")
            per_file = None

    total = len(tickets)

    # Fix 3: avoid silently creating empty files.
    if total == 0:
        print("Warning: ticket list is empty; no output files will be written.")
        return

    def _write(path, data):
        try:
            if fmt == "json":
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                print(f"Saved {len(data)} tickets to '{path}'")
            else:
                print(f"Error: unsupported format '{fmt}'. Use 'json'.")
        except IOError as e:
            print(f"Error writing '{path}': {e}")
            sys.exit(1)  # Fix 1: exit non-zero on IO failure

    if per_file:
        num_files = math.ceil(total / per_file)
        print(f"Splitting {total} tickets into {num_files} file(s) (~{per_file} each).")
        for i in range(num_files):
            chunk = tickets[i * per_file:(i + 1) * per_file]
            _write(f"{filename_base}{i + 1}.{fmt}", chunk)
    else:
        _write(f"{filename_base}.{fmt}", tickets)


if __name__ == "__main__":
    if not os.path.exists(CONFIG_FILE):
        print(f"Warning: '{CONFIG_FILE}' not found. Create it with your Jira details.")
        example = {
            "access_token": "YOUR_JIRA_ACCESS_TOKEN",
            "jira_base_url": "https://your-jira-instance.com",
            "jql_query": "project = YOUR_PROJECT AND status = Open",
            "fields": ["key", "summary", "status", "assignee", "reporter",
                       "priority", "issuetype", "created", "updated",
                       "description", "resolution", "comment"],
            "export_format": "json",
            "max_results": 50,
            "export_filename": "my_jira_tickets",
            "tickets_per_file": 20,
            "global_key_exclusions": ["expand", "id", "self"],
            "ticket_field_exclusions": {
                "reporter": ["self", "avatarUrls", "key", "emailAddress", "active", "timeZone"],
                "assignee": ["self", "avatarUrls", "key", "emailAddress", "active", "timeZone"],
                "issuetype": ["self", "iconUrl", "avatarId", "description"],
                "priority": ["self", "iconUrl"],
                "status": ["self", "iconUrl", "statusCategory.self", "statusCategory.id",
                           "statusCategory.key", "statusCategory.colorName"],
                "comment": ["comments.self", "comments.id",
                            "comments.author.self", "comments.author.key",
                            "comments.author.active", "comments.author.timeZone",
                            "comments.author.avatarUrls",
                            "comments.updateAuthor.self", "comments.updateAuthor.key",
                            "comments.updateAuthor.active", "comments.updateAuthor.timeZone",
                            "comments.updateAuthor.avatarUrls",
                            "maxResults", "total", "startAt"],
            },
        }
        print(json.dumps(example, indent=4))
        sys.exit(1)  # Fix 1: exit non-zero when config is missing

    cfg = load_config(CONFIG_FILE)
    if cfg is None:
        sys.exit(1)  # Fix 1: exit non-zero when config fails to load

    tickets = fetch_jira_tickets(cfg)
    if tickets is None:
        print("Ticket fetching failed.")
        sys.exit(1)  # Fix 1: exit non-zero on fetch failure
    elif not tickets:
        print("No tickets returned.")
    else:
        process_tickets_data(tickets, cfg)
        save_tickets(tickets, cfg)

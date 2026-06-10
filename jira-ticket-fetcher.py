import json
import requests
import os
import math

CONFIG_FILE = 'jira-config.json'

def load_config(config_path):
    """Loads the configuration from a JSON file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print("Configuration loaded successfully.")
        return config
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_path}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{config_path}'.")
        return None

def fetch_jira_tickets(config):
    """Fetches tickets from Jira based on the JQL query in the config."""
    if not config:
        print("Error: Configuration is missing.")
        return None

    access_token = config.get("access_token")
    jira_base_url = config.get("jira_base_url")
    search_url = f"{jira_base_url}/rest/api/latest/search"

    jql_query = config.get("jql_query")
    fields = config.get("fields", ["key", "summary"])
    max_results_per_request = config.get("max_results", 100)

    if not all([access_token, jira_base_url, jql_query]):
        print("Error: Missing critical configuration: access_token, jira_base_url, or jql_query.")
        return None

    # Check that access_token is not the placeholder value
    if access_token == "<token>":
        print("Error: access_token is set to the placeholder '<token>'. Please set a real token.")
        return None

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    all_issues = []
    start_at = 0
    total_issues_expected = -1

    print(f"Fetching tickets from: {search_url}")
    print(f"JQL Query: {jql_query}")

    while True:
        payload = {
            "jql": jql_query,
            "startAt": start_at,
            "maxResults": max_results_per_request,
            "fields": fields
        }

        try:
            print(f"Requesting issues from {start_at} to {start_at + max_results_per_request - 1}...")
            response = requests.post(search_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()
            issues_on_page = data.get("issues", [])
            all_issues.extend(issues_on_page)

            if total_issues_expected == -1:
                total_issues_expected = data.get("total", 0)
                print(f"Total issues found by JQL: {total_issues_expected}")

            print(f"Fetched {len(issues_on_page)} issues in this batch. Total fetched so far: {len(all_issues)}.")

            start_at += len(issues_on_page)
            if start_at >= total_issues_expected or not issues_on_page:
                print("All issues fetched or no more issues to fetch.")
                break

        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            print(f"Response content: {response.content.decode()}")
            return None
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Connection error occurred: {conn_err}")
            return None
        except requests.exceptions.Timeout as timeout_err:
            print(f"Timeout error occurred: {timeout_err}")
            return None
        except requests.exceptions.RequestException as req_err:
            print(f"An error occurred during the request: {req_err}")
            return None
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON response from Jira.")
            print(f"Response content: {response.text}")
            return None
    return all_issues

def _delete_nested_key_recursive(current_item, path_segments):
    """
    Recursively navigates and deletes a key from a dictionary or list of dictionaries.
    Modifies current_item in place.
    """
    if not path_segments:
        return

    key_to_process = path_segments[0]

    if isinstance(current_item, list):
        for item_in_list in current_item:
            if isinstance(item_in_list, dict):
                _delete_nested_key_recursive(item_in_list, path_segments)
        return

    if not isinstance(current_item, dict) or key_to_process not in current_item:
        return

    if len(path_segments) == 1:
        try:
            del current_item[key_to_process]
        except KeyError:
            pass
    else:
        _delete_nested_key_recursive(current_item[key_to_process], path_segments[1:])


def process_tickets_data(tickets, config):
    """
    Processes fetched tickets to exclude specified keys based on config.
    Modifies the tickets list in-place.
    """
    if not tickets or not config:
        print("No tickets or configuration provided for processing.")
        return

    global_exclusions = config.get("global_key_exclusions", [])
    ticket_field_exclusions = config.get("ticket_field_exclusions", {})

    if not global_exclusions and not ticket_field_exclusions:
        print("No exclusion rules defined in configuration. Skipping data processing.")
        return

    processed_count = 0
    for ticket in tickets:
        if not isinstance(ticket, dict):
            continue

        for key_to_del in global_exclusions:
            if key_to_del in ticket:
                try:
                    del ticket[key_to_del]
                except KeyError:
                    pass

        if "fields" in ticket and isinstance(ticket["fields"], dict):
            ticket_fields_obj = ticket["fields"]
            for main_field_key, sub_key_paths_to_exclude in ticket_field_exclusions.items():
                if main_field_key in ticket_fields_obj and isinstance(ticket_fields_obj[main_field_key], (dict, list)):
                    target_item_for_sub_keys = ticket_fields_obj[main_field_key]
                    for sub_key_path_str in sub_key_paths_to_exclude:
                        path_segments = sub_key_path_str.split('.')
                        _delete_nested_key_recursive(target_item_for_sub_keys, path_segments)
        processed_count += 1

    print(f"Processed {processed_count} tickets for data exclusion.")


def save_tickets(tickets, config):
    """Saves the fetched tickets to one or more files based on config."""
    if tickets is None:
        print("No tickets to save.")
        return

    if not config:
        print("Cannot save tickets without configuration.")
        return

    export_filename_base = config.get("export_filename", "jira_tickets")
    export_format = config.get("export_format", "json").lower()
    tickets_per_file_str = config.get("tickets_per_file")
    tickets_per_file = None

    if tickets_per_file_str is not None:
        try:
            tickets_per_file = int(tickets_per_file_str)
            if tickets_per_file <= 0:
                print(f"Warning: 'tickets_per_file' ({tickets_per_file_str}) is not a positive integer. Saving all tickets to a single file.")
                tickets_per_file = None
        except ValueError:
            print(f"Warning: 'tickets_per_file' ('{tickets_per_file_str}') is not a valid integer. Saving all tickets to a single file.")
            tickets_per_file = None

    total_tickets = len(tickets)

    if tickets_per_file and total_tickets > 0:
        num_files = math.ceil(total_tickets / tickets_per_file)
        print(f"Splitting {total_tickets} tickets into {num_files} file(s) with approximately {tickets_per_file} tickets per file.")

        for i in range(num_files):
            start_index = i * tickets_per_file
            end_index = start_index + tickets_per_file
            ticket_chunk = tickets[start_index:end_index]

            output_file = f"{export_filename_base}{i + 1}.{export_format}"

            try:
                if export_format == "json":
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(ticket_chunk, f, indent=4, ensure_ascii=False)
                    print(f"Successfully saved {len(ticket_chunk)} tickets to '{output_file}'")
                else:
                    print(f"Error: Unsupported export format '{export_format}' for chunked saving. Please use 'json'.")
                    return
            except IOError as e:
                print(f"Error writing to file '{output_file}': {e}")
            except Exception as e:
                print(f"An unexpected error occurred during saving chunk to '{output_file}': {e}")
    else:
        output_file = f"{export_filename_base}.{export_format}"
        try:
            if export_format == "json":
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(tickets, f, indent=4, ensure_ascii=False)
                print(f"Successfully saved {total_tickets} tickets to '{output_file}'")
            else:
                print(f"Error: Unsupported export format '{export_format}'. Please use 'json'.")
                return
        except IOError as e:
            print(f"Error writing to file '{output_file}': {e}")
        except Exception as e:
            print(f"An unexpected error occurred during saving: {e}")


if __name__ == "__main__":
    if not os.path.exists(CONFIG_FILE):
        print(f"Warning: '{CONFIG_FILE}' not found. You should create it with your Jira details.")
        example_config_content = {
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
                            "maxResults", "total", "startAt"]
            }
        }
        print(json.dumps(example_config_content, indent=4))
    else:
        configuration = load_config(CONFIG_FILE)
        if configuration:
            fetched_tickets = fetch_jira_tickets(configuration)
            if fetched_tickets:
                process_tickets_data(fetched_tickets, configuration)
                save_tickets(fetched_tickets, configuration)
            else:
                print("Ticket fetching failed or returned no tickets.")

import json
import requests
import os

CONFIG_FILE = 'jira-config.json'

def load_config(config_path):
    """Loads the configuration from a JSON file."""
    try:
        with open(config_path, 'r') as f:
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
        return None

    access_token = config.get("access_token")
    jira_base_url = config.get("jira_base_url")
    # Using 'latest' as per your curl, but you can adapt to use jira_api_version if needed
    # jira_api_version = config.get("jira_api_version", "latest")
    # search_url = f"{jira_base_url}/rest/api/{jira_api_version}/search"
    search_url = f"{jira_base_url}/rest/api/latest/search" # Matching your cURL

    jql_query = config.get("jql_query")
    fields = config.get("fields", ["key", "summary"]) # Default to key and summary if not specified
    max_results_per_request = config.get("max_results", 100) # Max results per API call

    if not all([access_token, jira_base_url, jql_query]):
        print("Error: Missing critical configuration: access_token, jira_base_url, or jql_query.")
        return None

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json" # Good practice to specify accept header
    }

    all_issues = []
    start_at = 0
    total_issues_expected = -1 # Initialize to an unknown state

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
            print(f"Requesting issues from {start_at} to {start_at + max_results_per_request -1}...")
            response = requests.post(search_url, headers=headers, json=payload, timeout=30) # Added timeout
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)

            data = response.json()
            issues_on_page = data.get("issues", [])
            all_issues.extend(issues_on_page)

            if total_issues_expected == -1: # First request
                total_issues_expected = data.get("total", 0)
                print(f"Total issues found by JQL: {total_issues_expected}")

            print(f"Fetched {len(issues_on_page)} issues in this batch. Total fetched so far: {len(all_issues)}.")

            # Check if we've fetched all issues
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
            print(f"Response content: {response.text}") # Show raw response
            return None

    return all_issues

def save_tickets(tickets, config):
    """Saves the fetched tickets to a file based on config."""
    if tickets is None:
        print("No tickets to save.")
        return

    if not config:
        print("Cannot save tickets without configuration.")
        return

    export_filename = config.get("export_filename", "jira_tickets")
    export_format = config.get("export_format", "json").lower()
    output_file = f"{export_filename}.{export_format}"

    try:
        if export_format == "json":
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(tickets, f, indent=4, ensure_ascii=False)
            print(f"Successfully saved {len(tickets)} tickets to '{output_file}'")
        # Add other formats like CSV if needed
        # elif export_format == "csv":
        #     # Implementation for CSV
        #     print(f"CSV export not yet implemented in this script version.")
        else:
            print(f"Error: Unsupported export format '{export_format}'. Please use 'json'.")
            return

    except IOError as e:
        print(f"Error writing to file '{output_file}': {e}")
    except Exception as e:
        print(f"An unexpected error occurred during saving: {e}")


if __name__ == "__main__":
    # Create a dummy config file if it doesn't exist for testing
    if not os.path.exists(CONFIG_FILE):
        print(f"Warning: '{CONFIG_FILE}' not found. You should create it with your Jira details.")
        print("Example config.json:")
        example_config_content = {
            "access_token": "YOUR_JIRA_ACCESS_TOKEN",
            "jira_base_url": "https://your-jira-instance.com",
            "jira_api_version": "3", # Or use "latest" in the URL construction
            "jql_query": "project = YOUR_PROJECT AND status = Open",
            "fields": [
                "key", "summary", "status", "assignee", "reporter",
                "priority", "issuetype", "created", "updated",
                "description", "resolution"
            ],
            "export_format": "json",
            "max_results": 50, # Results per API call for pagination
            "export_filename": "my_jira_tickets"
        }
        print(json.dumps(example_config_content, indent=4))
        # For actual use, create config.json with your real details.
    else:
        configuration = load_config(CONFIG_FILE)
        if configuration:
            fetched_tickets = fetch_jira_tickets(configuration)
            if fetched_tickets:
                save_tickets(fetched_tickets, configuration)
            else:
                print("Ticket fetching failed or returned no tickets.")

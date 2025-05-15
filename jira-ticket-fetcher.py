import json
import requests
import os
import math

CONFIG_FILE = 'jira-config.json'

def load_config(config_path):
    """Loads the configuration from a JSON file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f: # Added encoding
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
    # Construct the search URL for the Jira API
    search_url = f"{jira_base_url}/rest/api/latest/search"

    jql_query = config.get("jql_query")
    # Default to fetching 'key' and 'summary' if 'fields' is not specified in config
    fields = config.get("fields", ["key", "summary"]) 
    # Default to fetching 100 results per API call if 'max_results' is not specified
    max_results_per_request = config.get("max_results", 100) 

    # Check for essential configuration parameters
    if not all([access_token, jira_base_url, jql_query]):
        print("Error: Missing critical configuration: access_token, jira_base_url, or jql_query.")
        return None

    # Set up headers for the API request
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json" # Specify that we expect a JSON response
    }

    all_issues = [] # List to store all fetched issues
    start_at = 0 # Pagination: starting index for results
    total_issues_expected = -1 # Initialize to an unknown state, will be updated by the first API response

    print(f"Fetching tickets from: {search_url}")
    print(f"JQL Query: {jql_query}")

    # Loop to handle pagination if there are more results than max_results_per_request
    while True:
        # Payload for the POST request to Jira API
        payload = {
            "jql": jql_query,
            "startAt": start_at,
            "maxResults": max_results_per_request,
            "fields": fields
        }

        try:
            print(f"Requesting issues from {start_at} to {start_at + max_results_per_request -1}...")
            # Make the POST request to Jira
            response = requests.post(search_url, headers=headers, json=payload, timeout=30) # Added timeout
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)

            data = response.json() # Parse the JSON response
            issues_on_page = data.get("issues", []) # Get the list of issues from the response
            all_issues.extend(issues_on_page) # Add fetched issues to our main list

            if total_issues_expected == -1: # If this is the first request
                total_issues_expected = data.get("total", 0) # Get the total number of issues matching the JQL
                print(f"Total issues found by JQL: {total_issues_expected}")

            print(f"Fetched {len(issues_on_page)} issues in this batch. Total fetched so far: {len(all_issues)}.")

            # Check if we've fetched all issues
            start_at += len(issues_on_page) # Increment the starting point for the next request
            if start_at >= total_issues_expected or not issues_on_page:
                print("All issues fetched or no more issues to fetch.")
                break # Exit the loop
        
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

def _delete_nested_key_recursive(current_item, path_segments):
    """
    Recursively navigates and deletes a key from a dictionary or list of dictionaries.
    Modifies current_item in place.
    
    Args:
        current_item: The dictionary or list of dictionaries to process.
        path_segments: A list of strings representing the path to the key to delete 
                       (e.g., ['statusCategory', 'self']).
    """
    if not path_segments: # Base case: no more path segments to process
        return

    key_to_process = path_segments[0] # Current key/index in the path

    if isinstance(current_item, list):
        # If current_item is a list, apply the deletion to each dictionary element in it
        for item_in_list in current_item:
            if isinstance(item_in_list, dict):
                 _delete_nested_key_recursive(item_in_list, path_segments) # Recurse on each item
        return


    # If current_item is not a dictionary, or the key is not found, stop
    if not isinstance(current_item, dict) or key_to_process not in current_item:
        return

    if len(path_segments) == 1:  # This is the final key in the path to delete
        try:
            del current_item[key_to_process]
        except KeyError:
            # Should not happen due to 'key_to_process not in current_item' check above, but good for safety
            pass 
    else:  # Navigate deeper into the structure
        _delete_nested_key_recursive(current_item[key_to_process], path_segments[1:])


def process_tickets_data(tickets, config):
    """
    Processes fetched tickets to exclude specified keys based on config.
    Modifies the tickets list in-place.
    
    Args:
        tickets: A list of ticket dictionaries.
        config: The configuration dictionary.
    """
    if not tickets or not config:
        print("No tickets or configuration provided for processing.")
        return

    # Get exclusion rules from config, defaulting to empty lists/dicts if not found
    global_exclusions = config.get("global_key_exclusions", [])
    ticket_field_exclusions = config.get("ticket_field_exclusions", {})

    if not global_exclusions and not ticket_field_exclusions:
        print("No exclusion rules defined in configuration. Skipping data processing.")
        return

    processed_count = 0
    for ticket in tickets: # Iterate over each ticket
        if not isinstance(ticket, dict): # Skip if a ticket is not a dictionary
            continue

        # Apply global exclusions (top-level keys in each ticket object)
        for key_to_del in global_exclusions:
            if key_to_del in ticket:
                try:
                    del ticket[key_to_del]
                except KeyError:
                    pass # Key already gone or was never there

        # Apply ticket_field_exclusions (keys within ticket['fields'] object)
        if "fields" in ticket and isinstance(ticket["fields"], dict):
            ticket_fields_obj = ticket["fields"] # The 'fields' sub-dictionary
            for main_field_key, sub_key_paths_to_exclude in ticket_field_exclusions.items():
                # main_field_key is e.g., "reporter", "assignee"
                # sub_key_paths_to_exclude is a list like ["self", "avatarUrls"]
                if main_field_key in ticket_fields_obj and isinstance(ticket_fields_obj[main_field_key], (dict, list)):
                    # target_item_for_sub_keys is the actual object like ticket_fields_obj['reporter']
                    target_item_for_sub_keys = ticket_fields_obj[main_field_key] 
                    for sub_key_path_str in sub_key_paths_to_exclude:
                        # sub_key_path_str can be "self" or "statusCategory.key"
                        path_segments = sub_key_path_str.split('.') # Split for nested paths
                        _delete_nested_key_recursive(target_item_for_sub_keys, path_segments)
        processed_count +=1
    
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
    tickets_per_file = None # Initialize


    # Validate tickets_per_file from config
    if tickets_per_file_str is not None:
        try:
            tickets_per_file = int(tickets_per_file_str)
            if tickets_per_file <= 0:
                print(f"Warning: 'tickets_per_file' ({tickets_per_file_str}) is not a positive integer. Saving all tickets to a single file.")
                tickets_per_file = None # Revert to single file behavior if invalid
        except ValueError:
            print(f"Warning: 'tickets_per_file' ('{tickets_per_file_str}') is not a valid integer. Saving all tickets to a single file.")
            tickets_per_file = None # Revert to single file behavior if not an integer
    
    total_tickets = len(tickets)

    if tickets_per_file and total_tickets > 0 :
        # Calculate number of files needed
        num_files = math.ceil(total_tickets / tickets_per_file)
        print(f"Splitting {total_tickets} tickets into {num_files} file(s) with approximately {tickets_per_file} tickets per file.")

        for i in range(num_files): # Loop to create each file
            start_index = i * tickets_per_file
            end_index = start_index + tickets_per_file
            ticket_chunk = tickets[start_index:end_index] # Get a slice of tickets for the current file
            
            # Construct filename with number (e.g., redhat-genie-tickets1.json)
            output_file = f"{export_filename_base}{i+1}.{export_format}"
            
            try:
                if export_format == "json":
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(ticket_chunk, f, indent=4, ensure_ascii=False)
                    print(f"Successfully saved {len(ticket_chunk)} tickets to '{output_file}'")
                # Placeholder for other formats like CSV if needed in the future
                # elif export_format == "csv":
                #     print(f"CSV export not yet implemented in this script version for multiple files.")
                else:
                    print(f"Error: Unsupported export format '{export_format}' for chunked saving. Please use 'json'.")
                    return # Stop if format is unsupported for chunked saving
            except IOError as e:
                print(f"Error writing to file '{output_file}': {e}")
            except Exception as e:
                print(f"An unexpected error occurred during saving chunk to '{output_file}': {e}")
    else:
        # Original behavior: save all to one file if tickets_per_file is not set or invalid
        output_file = f"{export_filename_base}.{export_format}"
        try:
            if export_format == "json":
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(tickets, f, indent=4, ensure_ascii=False)
                print(f"Successfully saved {total_tickets} tickets to '{output_file}'")
            # Placeholder for other formats
            # elif export_format == "csv":
            #     print(f"CSV export not yet implemented in this script version.")
            else:
                print(f"Error: Unsupported export format '{export_format}'. Please use 'json'.")
                return
        except IOError as e:
            print(f"Error writing to file '{output_file}': {e}")
        except Exception as e:
            print(f"An unexpected error occurred during saving: {e}")


if __name__ == "__main__":
    # Check if the configuration file exists
    if not os.path.exists(CONFIG_FILE):
        print(f"Warning: '{CONFIG_FILE}' not found. You should create it with your Jira details.")
        print("Example config.json content including exclusion rules:")
        # Provide an example configuration to guide the user
        example_config_content = {
            "access_token": "YOUR_JIRA_ACCESS_TOKEN",
            "jira_base_url": "https://your-jira-instance.com",
            "jql_query": "project = YOUR_PROJECT AND status = Open",
            "fields": [ # Fields to fetch from Jira API
                "key", "summary", "status", "assignee", "reporter",
                "priority", "issuetype", "created", "updated",
                "description", "resolution", "comment" 
            ],
            "export_format": "json",
            "max_results": 50, # Results per API call for pagination
            "export_filename": "my_jira_tickets",
            "tickets_per_file": 20, # Example: New configuration for splitting files
            "global_key_exclusions": ["expand", "id", "self"], # Remove these top-level keys from each ticket
            "ticket_field_exclusions": { # Remove specific sub-keys from objects within ticket.fields
                "reporter": ["self", "avatarUrls", "key", "emailAddress", "active", "timeZone"],
                "assignee": ["self", "avatarUrls", "key", "emailAddress", "active", "timeZone"],
                "issuetype": ["self", "iconUrl", "avatarId", "description"],
                "priority": ["self", "iconUrl"],
                "status": ["self", "iconUrl", "statusCategory.self", "statusCategory.id", "statusCategory.key", "statusCategory.colorName"],
                "comment": [ # Example for comment field, including nested keys within the 'comments' list
                    "comments.self", "comments.id", 
                    "comments.author.self", "comments.author.key", "comments.author.active", "comments.author.timeZone", "comments.author.avatarUrls",
                    "comments.updateAuthor.self", "comments.updateAuthor.key", "comments.updateAuthor.active", "comments.updateAuthor.timeZone", "comments.updateAuthor.avatarUrls",
                    "maxResults", "total", "startAt"
                ]
            }
        }
        print(json.dumps(example_config_content, indent=4))
    else:
        # Load configuration if the file exists
        configuration = load_config(CONFIG_FILE)
        if configuration:
            # Fetch tickets from Jira
            fetched_tickets = fetch_jira_tickets(configuration)
            if fetched_tickets:
                # Process tickets to remove unwanted keys before saving
                process_tickets_data(fetched_tickets, configuration)
                # Save the processed tickets to file(s)
                save_tickets(fetched_tickets, configuration)
            else:
                print("Ticket fetching failed or returned no tickets.")

import json
import os
import csv
import re
from datetime import datetime, timezone

# Define paths directly in the code for JSON input and CSV output
jsondir = "data"  # Root folder containing subfolders with JSON message files
userjson = "data/users.json"  # Path to Slack users JSON file
outcsv_file = "slack_messages.csv"  # Path to the output CSV file

def handle_annotated_mention(matchobj):
    """Handles annotated mentions, formatting them to @username."""
    return "@{}".format((matchobj.group(0)[2:-1]).split("|")[1])

def handle_mention(matchobj, user_dict):
    """Handles standard mentions by converting user IDs to usernames."""
    user_id = matchobj.group(0)[2:-1]
    return "@{}".format(user_dict.get(user_id, ["Unknown User"])[0])

def transform_text(text, user_dict):
    """Transforms message text, replacing mentions and special characters."""
    text = text.replace("<!channel>", "@channel")  # Replace channel mention
    text = text.replace("&gt;",  ">")              # Replace HTML entity for ">"
    text = text.replace("&amp;", "&")              # Replace HTML entity for "&"
    text = re.compile(r"<@U\w+\|[A-Za-z0-9.-_]+>").sub(handle_annotated_mention, text)
    text = re.compile(r"<@U\w+>").sub(lambda match: handle_mention(match, user_dict), text)
    return text

def load_user_data(userjson_path):
    """Loads user data from a JSON file, storing it in a dictionary."""
    users = {}
    with open(userjson_path, encoding='utf-8') as user_data:
        userlist = json.load(user_data)
        for userdata in userlist:
            userid = userdata["id"]
            realname = userdata.get("real_name") or userdata["name"]  # Use real name or fallback to username
            if not re.match(r'.*[a-zA-Z].*', realname):
                realname = userdata["name"]
            users[userid] = [realname]
    return users

def extract_attachment_title(item):
    """Extracts the title of the first attachment if present in the message item."""
    if "files" in item and item["files"]:
        return item["files"][0].get("title", "")
    return ""

def process_json_files(jsondir, users, csvwriter):
    """Processes JSON files across all subfolders and writes data to a CSV."""
    for root, dirs, files in os.walk(jsondir):  # Traverse all folders in jsondir
        channel_name = os.path.basename(root)  # Use folder name as channel name
        
        for content in files:
            if content.endswith(".json"):
                with open(os.path.join(root, content), encoding='utf-8') as data_file:
                    try:
                        data = json.load(data_file)
                        # Ensure that data is a list of dictionaries
                        if isinstance(data, list):
                            for item in data:
                                # Process only message-type items with text
                                if isinstance(item, dict) and item.get("type") == "message" and "text" in item:
                                    user_cur = users.get(item.get("user", "Unknown User"), ["Unknown User"])
                                    ts = datetime.fromtimestamp(float(item['ts']), tz=timezone.utc)
                                    date, time = ts.strftime("%Y-%m-%d"), ts.strftime("%H:%M:%S")
                                    message_text = transform_text(item["text"], users)
                                    attachment_title = extract_attachment_title(item)
                                    
                                    # Write row with specified column order
                                    csvwriter.writerow([channel_name, date, time, message_text, attachment_title, user_cur[0]])
                    except json.JSONDecodeError:
                        print(f"Error decoding JSON file: {content}")

def main():
    """Main function controlling data flow and creating the CSV file."""
    users = load_user_data(userjson)  # Load user data from JSON file
    
    with open(outcsv_file, 'w', newline='', encoding='utf-8') as f:
        csvwriter = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csvwriter.writerow(['canal', 'fecha', 'hora', 'mensaje', 'adjunto', 'autor'])
        
        process_json_files(jsondir, users, csvwriter)  # Process JSON files and write to CSV

if __name__ == "__main__":
    main()

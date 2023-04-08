from pathlib import Path
import json
import os
import re

#################### Constants ######################
directory_in_str = "outputs\m3u\m3u_2023-04-08"
exclude = set(['backups'])
#####################################################

def handleUserInput() -> str:
    search_text = None
    while search_text == None:
        try:
            search_text = input(f"What would you like to search?\n-> ")
        except:
            print(input_error_message)

    # Stop Script
    if(search_text == ""): exit()
    return search_text

# Capture user input
user_query = handleUserInput()

# Print empty line for visiblity
print()

matched_hosts = []

# Walk over directory
for root, dirs, files in os.walk(directory_in_str, topdown=True):
    # Skip Top directory
    if (root == directory_in_str): continue

    # Exclude Backups folder
    dirs[:] = [d for d in dirs if d not in exclude]

    if (len(files) > 0):
        # Extension is ususally m3u or m3u_plus
        file_extension = root.split(sep="&")[-1]
        file_path = os.path.join(root, f"programming.{file_extension}")

        with open(file_path, "r", encoding="utf-8") as reader:
            hostname = root.split(sep="&")[0].split(sep="\\")[-1]
            lines = reader.readlines()
            # print(hostname)

            for row in lines:
                # if row.find(user_query) != -1:
                if re.search(user_query, row, re.IGNORECASE):
                    try:
                        result = matched_hosts.index(hostname)
                    except:
                        matched_hosts.append(hostname)
                    
                    # print('string exists in file: ', root)
                    # print('line Number:', lines.index(row))
                    # print(f"{lines.index(row)} - {row}")


# Print empty line for visiblity
print()
print(matched_hosts)
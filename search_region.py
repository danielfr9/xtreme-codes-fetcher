from pathlib import Path
import json
import os
import argparse
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--dir', type=str, default='')
args = parser.parse_args()

#################### Constants ######################
m3u_directory = f'outputs/m3u/{args.dir}'

if (not os.path.exists(f'./{m3u_directory}')):
    sys.exit("Provided folder doesn't exist in the outputs folder")

exclude = set(['backups'])
input_error_message = """
####################################
      Invalid input, try again     
####################################
"""
#####################################################


def handleUserInput() -> str:
    user_region = None
    while user_region not in [0, 1, 2, 3, 4]:
        try:
            user_region = int(
                input(f"What region do you need? 1-America 2-Europe 3-Asia 4-UTC 0-Exit\n-> "))
        except:
            print(input_error_message)

    # Stop Script
    if (user_region == 0):
        exit()

    region = "America"
    if (user_region == 2):
        region = "Europe"
    if (user_region == 3):
        region = "Asia"
    if (user_region == 4):
        region = "UTC"
    return region


# Capture user input
continent_or_UTC = handleUserInput()

# Print empty line for visiblity
print()

# Walk over directory
for root, dirs, files in os.walk(m3u_directory, topdown=True):
    # Skip Top directory
    if (root == m3u_directory):
        continue

    # Exclude Backups folder
    dirs[:] = [d for d in dirs if d not in exclude]

    if (len(files) > 0):
        file_path = os.path.join(root, "info.json")
        # print(file_path)
        with open(file_path, "r") as reader:
            data: dict = json.load(reader)
            info: dict = data.get("info")
            user_info: dict = info.get("user_info")
            server_info: dict = info.get("server_info")

            # Check for invalid Accounts
            if (user_info != None):
                status = user_info.get("status")
                if (status == "Disabled" or status == "Banned"):
                    continue

            # Check that the server_info is actually in the info property
            if (server_info != None):
                timezone: str = server_info.get("timezone")

                # America/*, Europe/*, UTC
                t = timezone.split("/")

                if (t[0] == continent_or_UTC):
                    print(f"{timezone} - {data['url']}")

# Print empty line for visiblity
print()

# pathlist = Path(directory_in_str).glob('**/info.json')
# for path in pathlist:
#      # because path is object not string
#     path_in_str = str(path)
#     with open(path_in_str, "r") as reader:
#         data = json.load(reader)
#         print(data["url"])

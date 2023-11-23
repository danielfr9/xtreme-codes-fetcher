import requests
from requests.exceptions import HTTPError
from urllib import parse
from urllib.parse import SplitResult
import re
from pathlib import Path
from typing import Dict, AnyStr, Union

import json
from datetime import datetime
import argparse
import os.path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--filename', type=str, required=True)
args = parser.parse_args()

# Create directories if they don't exist
Path("inputs").mkdir(parents=True, exist_ok=True)
Path("outputs").mkdir(parents=True, exist_ok=True)

# Constants
codes_file = f'inputs/{args.filename}.txt'

if (not os.path.isfile(f'./{codes_file}')):
    sys.exit("Provided file doesn't exist in input folder")

# formatted_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# File storage locations
SUCCESS_FOLDER = f"outputs/m3u/{args.filename}"
FAIL_FILE = f"outputs/failures/failures_{args.filename}.txt"
RETRY_FILE = f"outputs/retries/retry_{args.filename}.txt"

#####################################################
retry_list = []


# Result: Response, Status_Code, Reason
def fetchUrl(URL: str, queries: dict = {}):
    # NOTE: Status Code can be None to account for Exception
    try:
        response = requests.get(URL, params=queries)
        # If the response was successful, no Exception will be raised
        response.raise_for_status()
    except HTTPError as http_err:
        return None, response.status_code, response.reason
    except Exception as err:
        return None, None, None
    else:
        if (response.status_code == 200):
            return response, None, None
        else:
            return None, response.status_code, response.reason


def netlocToFormattedDomain(netloc: str):
    # Remove (.) from the netloc (replace with a underscore) and remove port number.
    # lemon.catchmeifyo.com:8000  => lemon_catchmeifyo_com
    domain = re.sub(":[0-9]+$", "", parsed_url.netloc).replace(".", "_")
    return domain


def saveSuccess(account_info: dict, netloc: str, m3u: str, extension: str, filename: str):
    domain = netlocToFormattedDomain(netloc)

    parentFolder = f"{SUCCESS_FOLDER}/{domain}/{filename}"
    Path(parentFolder).mkdir(exist_ok=True, parents=True)

    with open(f"{parentFolder}/info.json", "w+", encoding="utf-8") as outfile:
        json.dump(account_info, outfile)

    with open(f"{parentFolder}/programming.{extension}", "w+", encoding="utf-8", newline="\n") as outfile2:
        outfile2.write(m3u)


def saveBackup(backup: dict, netloc: str, filename: str):
    domain = netlocToFormattedDomain(netloc)

    parentFolder = f"{SUCCESS_FOLDER}/{domain}/backups/{filename}"

    Path(parentFolder).mkdir(exist_ok=True, parents=True)
    with open(f"{parentFolder}/info.json", "w+", encoding="utf-8") as outfile:
        json.dump(backup, outfile)


def saveRetry(retry_list: list):
    with open(RETRY_FILE, "w+", encoding="utf-8") as outfile:
        outfile.writelines(retry_list)


def saveFailure(url: str, status_code: Union[int, None] = None, reason: Union[str, None] = None, errorType: Union[str, None] = None):
    rsn = "Unknown Reason" if reason is None else reason
    errT = "USER_INFO" if errorType is None else errorType
    
    with open(FAIL_FILE, "a+", encoding="utf-8") as outfile2:
        outfile2.write(f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} - ")

        if (status_code != None):
            outfile2.write(f"{status_code} ")
            
        outfile2.write(f"{rsn} - {errT} - {url}")

def handleFailure(url: str, status_code: Union[int, None] = None, reason: Union[str, None] = None, errorType: Union[str, None] = None):
    retry_list.append(url)
    print(f"❌ {reason}: {url}", end="")
    saveFailure(url,status_code,reason, errorType)

def createFilename(queries: Dict, netloc: str):
    netlocDomain = netlocToFormattedDomain(netloc)

    # Extract username and check for special case of login instead of username
    username = "no_username"
    if (queries.get("username")):
        # TODO: Validate for all the invalid characters in a file name
        # https://sh1708063.b.had.su/ParsXML/Edem-m3u.php?key=MA59DDN4XFDNXM
        username = queries.get("username").replace(":", "_")
    elif (queries.get("login")):
        username = queries.get("login")

    result_filename = f"{netlocDomain}&{username}&{queries.get('type')}"
    return result_filename


def getQueryDict(query_string) -> Dict[AnyStr, AnyStr]:
    queries = parse.parse_qs(query_string)
    extractedQueries: Dict[AnyStr, AnyStr] = dict()

    # Extract each query from the dict value list
    # {'username': ['valueForUsername']} => {'username': 'valueForUsername'}
    for k, v in queries.items():
        extractedQueries[k] = v[0]

    return extractedQueries


def verifyXtremeUrl(parsed_url: SplitResult):
    # Check if it contains the usual get.php path
    if (parsed_url.path != "/get.php"):
        # TODO
        # # Check the url uses a username and password
        # if (not (queries.get("username") and queries.get("password"))):
        #     # Return False and None, signaling that it doesn't follow the usual Xtream Codes format
        #     return False, None

        # # Return True and the path, signaling that it only changes the path (ex. /get.php?username=?&password=?)
        # return True, parsed_url.path
        return False

    # Return True and None, signaling that it is a valid Xtreme Code url
    return True

with open(codes_file, "r", encoding="utf-8") as reader:
    counter = 0
    visited_list = set()

    for m3u_link in reader:
        counter += 1
        print(f"{counter}- Checking: {m3u_link}", end="")

        # Parse the file to get the parts of the url | Scheme=http, netloc=(domain and port), path=(route), query=(username,password and type in a single string), fragment
        parsed_url = parse.urlsplit(m3u_link)

        # Verify the URL, check for Xtream Code format
        isValidUrl = verifyXtremeUrl(parsed_url)

        # Save as failed if not valid
        if (not isValidUrl):
            handleFailure(m3u_link,None,"Invalid Format")
            continue

        # Transform string into dict
        queries = getQueryDict(parsed_url.query)

        # Generate filename from the url
        filename = createFilename(queries, parsed_url.netloc)

        # Create url to fetch user information
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        info_url = f"{base_url}/player_api.php"
        m3u_url = f"{base_url}/get.php"

        # Fetch User Info
        response_user_info = fetchUrl(info_url, queries=queries)

        # Save as failed if it couldn't fetch user info
        if (response_user_info[0] == None):
            _, status_code, error = response_user_info
            handleFailure(m3u_link,status_code,error)
            continue

        user_info = None
        try:
            user_info = response_user_info[0].json()
        except Exception as ex:
            # Save as failed if the user info isn't in JSON format
            handleFailure(m3u_link,None,"Invalid User Info")
            continue

        # Check if the domain and port has been visited
        if (parsed_url.netloc in visited_list):
            # Create backup dict
            backup = dict({
                "created": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                "authority": parsed_url.netloc,
                "url": m3u_link.strip(),
                "info": user_info
            })
            saveBackup(backup, parsed_url.netloc, filename)
            print(f"💾 Saved as backup: {m3u_link}", end="")
            continue

        # Fetch M3U list
        response_m3u = fetchUrl(m3u_url, queries=queries)

        # Save as failed if no m3u data was fetched
        if (response_m3u[0] == None):
            _, status_code, error = response_m3u
            handleFailure(m3u_link,status_code,error)
            continue

        m3u_text = response_m3u[0].text

        # Create result dict
        result = dict({
            "created": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            "authority": parsed_url.netloc,
            "url": m3u_link.strip(),
            "info": user_info,
        })

        saveSuccess(result, parsed_url.netloc, m3u_text,
                   queries.get("type"), filename)
        visited_list.add(parsed_url.netloc)
        print(f"✅ Success: {m3u_link}", end="")

    saveRetry(retry_list)

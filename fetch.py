import requests
from requests.exceptions import HTTPError
from urllib import parse
from urllib.parse import SplitResult
import json 
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, AnyStr, List, TypedDict, Any, Union

# BUG: Sometimes USER_INFO can return with an error message from the database instead of the actual data
# "info": { "error": "MySQL: Cannot assign requested address" }

# FIXME: Special Case for Xtreme Codes
# https://s.topiptv.in/list.php?login=termit52&password=Keklol228&type=m3u

# Create directories if they don't exist
Path("inputs").mkdir(parents=True, exist_ok=True)
Path("outputs").mkdir(parents=True, exist_ok=True)

# Constants
codes_file = "inputs/m3u-8-4-2023.txt"

# TODO: Check if directory/file exist, and create if not
SUCCESS_FOLDER = f"outputs/m3u/m3u_{datetime.today().strftime('%Y-%m-%d')}"
FAIL_FILE = f"outputs/failures/failures_{datetime.today().strftime('%Y-%m-%d')}.txt"
RETRY_FILE = f"outputs/retries/retry_{datetime.today().strftime('%Y-%m-%d')}.txt"

#####################################################
def fetchUrl(URL: str, queries: dict = {}):
    # NOTE: Status Code can be None to account for Exception
    try:
        response = requests.get(URL, params=queries)
        # If the response was successful, no Exception will be raised
        response.raise_for_status()
    except HTTPError as http_err:
        return None, response.status_code, response.reason  
    except Exception as err:
        return  None, None, "Undefined"
    else:
        if (response.status_code == 200): 
            return response, None, None
        else:
            return None, response.status_code, response.reason

def netlocToFilename(netloc: str):
    # Remove (.) from the netloc (replace with a underscore) and remove port number.
    domain = re.sub(":[0-9]+$","",parsed_url.netloc).replace(".", "_")
    return domain

def saveSucces(account_info: dict, netloc: str, m3u: str, extension: str, filename: str):
    domain = netlocToFilename(netloc)

    parentFolder = f"{SUCCESS_FOLDER}/{domain}/{filename}"
    Path(parentFolder).mkdir(exist_ok=True, parents=True)

    with open(f"{parentFolder}/info.json", "w+", encoding="utf-8") as outfile:
        json.dump(account_info, outfile)

    with open(f"{parentFolder}/programming.{extension}", "w+", encoding="utf-8", newline="\n") as outfile2:
        outfile2.write(m3u)

def saveBackup(backup: dict, netloc: str, filename: str):
    domain = netlocToFilename(netloc)

    parentFolder = f"{SUCCESS_FOLDER}/{domain}/backups/{filename}"

    Path(parentFolder).mkdir(exist_ok=True, parents=True)
    with open(f"{parentFolder}/info.json", "w+", encoding="utf-8") as outfile:
            json.dump(backup, outfile)

def saveRetry(retry_list):
    with open(RETRY_FILE, "w+", encoding="utf-8") as outfile:
        outfile.writelines(retry_list)

def saveFailure(url: str , reason, status_code=None ,type="USER_INFO"):
    with open(FAIL_FILE, "a+", encoding="utf-8") as outfile2:
        outfile2.write(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
        outfile2.write(" - ")

        # Note: STATUS_CODE or REASON can be None, but not both
        # Check for status code; Leave space on the right for a posible reason
        if(status_code != None):
            outfile2.write(f"{status_code} ")

        # Check for reason
        if(reason != None):
            outfile2.write(reason)
            outfile2.write(" - ")
        else:
            # Add dash while accounting for status code right space
            outfile2.write("- ")

        outfile2.write(type)
        outfile2.write(" - ")
        outfile2.write(url)

def createFilename(parsed_url):
    queries = getQueries(parsed_url.query)
    netlocFilename = netlocToFilename(parsed_url.netloc) 

    # Extract username and check for special case of login instead of username
    username = "no_username"
    if (queries.get("username")):
        # TODO: Validate for all the invalid characters in a file name
        # https://sh1708063.b.had.su/ParsXML/Edem-m3u.php?key=MA59DDN4XFDNXM
        username = queries.get("username").replace(":", "_")
    elif (queries.get("login")):
        username = queries.get("login")

    result_filename = f"{netlocFilename}&{username}&{queries.get('type')}"
    return result_filename

def getQueries(query_string) -> Dict[AnyStr, AnyStr]:
    # Extract each query from the dict value list
    # {'username': ['valueForUsername']} => {'username': 'valueForUsername'} 
    queries = parse.parse_qs(query_string)
    extractedQueries: Dict[AnyStr, AnyStr] = dict()

    for k,v in queries.items():
        extractedQueries[k] = v[0]
    
    return extractedQueries

def verifyXtremeUrl(parsed_url: SplitResult):
    # Check if it contains the usual get.php path
    if (parsed_url.path != "/get.php"):
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
    retry_list = []
    visited_list = set()
    
    for m3u_link in reader:
        counter += 1
        print(f"{counter}- Checking: {m3u_link}", end="")

        # Parse the file to get the parts of the url | Scheme=http, netloc=(domain and port), path=(route), query=(username,password and type in a single string), fragment
        parsed_url = parse.urlsplit(m3u_link)
        
        # Verify the URL, check for Xtream Code format
        isValid = verifyXtremeUrl(parsed_url)

        # Save as failed if not valid
        if (not isValid):
            print(f"Wrong Format: {m3u_link}", end="") 
            retry_list.append(m3u_link)
            saveFailure(m3u_link, "Invalid Format", None)
            continue

        # Transform string into dict
        queries = getQueries(parsed_url.query)

        # Generate filename from the url
        filename = createFilename(parsed_url)

        # Create url to fetch user information
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        info_url = f"{base_url}/player_api.php"
        m3u_url = f"{base_url}/get.php"

        # Fetch User Info
        response_user_info = fetchUrl(info_url, queries=queries)

        # Save as failed if it couldn't fetch user info
        if (response_user_info[0] == None): 
            _, status_code, error = response_user_info
            print(f"Failed: {m3u_link}", end="")
            retry_list.append(m3u_link)
            saveFailure(m3u_link, error, status_code)
            continue

        user_info = None
        try:
            user_info = response_user_info[0].json()
        except Exception as ex:
            # Save as failed if the user info isn't in JSON format
            print(f"Failed parsing: {m3u_link}", end="")
            retry_list.append(m3u_link)
            saveFailure(m3u_link, "FAILED PARSING", None)
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
            print(f"Saved as backup: {m3u_link}", end="")
            continue

        # Fetch M3U list
        response_m3u = fetchUrl(m3u_url, queries=queries)

        # Save as failed if no m3u data was fetched
        if (response_m3u[0] == None): 
            _, status_code, error = response_m3u
            print(f"Failed: {m3u_link}", end="")
            retry_list.append(m3u_link)
            saveFailure(m3u_link, error, status_code)
            continue

        m3u_text = response_m3u[0].text

        # Create result dict
        result = dict({
            "created": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            "authority": parsed_url.netloc,
            "url": m3u_link.strip(),
            "info": user_info,
        })

        saveSucces(result, parsed_url.netloc, m3u_text, queries.get("type"), filename)
        visited_list.add(parsed_url.netloc)
        print(f"Success: {m3u_link}", end="")

    saveRetry(retry_list)
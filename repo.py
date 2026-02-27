import database
import requests
import time
import urllib3
import os
from config import API_BASE_URL

# Deaktiver SSL advarsler
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def send_results(bws_path, last_mtime, club_id, section_id):
    try:
        current_mtime = os.path.getmtime(bws_path)

        if current_mtime > last_mtime:
            results = database.fetch_results(bws_path)
            if results:
                payload = {
                    "ClubId": int(club_id),
                    "SectionId": int(section_id),
                    "Results": results
                }
                response = requests.post(f"{API_BASE_URL}/Results", json=payload, timeout=5, verify=False)
                if response.status_code in [200, 201]:
                    print(f"[{time.strftime('%H:%M:%S')}] Sync succesfuld! {len(results)} rækker sendt.")
                    return current_mtime 
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] Server svarede med fejl: {response.status_code}")
        
        return last_mtime

    except requests.RequestException as e:
        print(f"Fejl ved API-kald: {e}")
        return last_mtime
    except Exception as e:
        print(f"Fejl under datahentning eller API-kald: {e}")
        return last_mtime


def insert_players(bws_path, club_id):
    try:
        response = requests.get(f"{API_BASE_URL}/ClubsDb/ClubMembersShort/{club_id}", timeout=5, verify=False)
        if response.status_code == 200:
            players = response.json()
            database.insert_main_players(bws_path, players)
        else:
            print(f"Fejl ved hentning af spillere: {response.status_code}")
    except requests.RequestException as e:
        print(f"Fejl ved API-kald: {e}")

def get_session_info(section_id):
    try:
        response = requests.get(f"{API_BASE_URL}/ClubTournamentsDb/session/{section_id}", timeout=5, verify=False)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Fejl ved hentning af session info: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"Fejl ved API-kald: {e}")
        return None

def get_section_info(section_id):
    try:
        response = requests.get(f"{API_BASE_URL}/ClubTournamentsDb/section/{section_id}", timeout=5, verify=False)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Fejl ved hentning af sektion info: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"Fejl ved API-kald: {e}")
        return None
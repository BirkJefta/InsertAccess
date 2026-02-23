import urllib3
import repo
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import database
import requests
import time
from config import API_BASE_URL, POLL_MS
from setup import get_club_settings
import os


def run_sync():
    
    settings = get_club_settings()
    last_mtime = 0
    club_id = settings["ClubId"]
    section_id = settings["SectionId"]
    bws_path = settings["path"]

    print(f"Klub: {club_id} | Sektion: {section_id}")
    print(f"Overvåger fil: {bws_path}")
    repo.insert_players(bws_path, club_id)

    while True:
        last_mtime = repo.send_results(bws_path, last_mtime, club_id, section_id)
        time.sleep(POLL_MS / 1000.0)
        
if __name__ == "__main__":
    run_sync()


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
    #sæt client info i databasen
    client_id = database.insert_client_info(bws_path)
    if client_id:
        print(f"PC registreret med Client ID: {client_id}")
    else:
        print("Kunne ikke registrere PC – Bridgemate kan have problemer med at starte.")
    #Hent session info og opdater i databasen
    session_info = repo.get_session_info(section_id)
    if session_info:
        database.insert_session_info(bws_path, session_info)
    else:
        print("Kunne ikke hente session info – session data vil ikke blive opdateret.")
    

    print(f"Klub: {club_id} | Sektion: {section_id}")
    print(f"Overvåger fil: {bws_path}")
    #indsæt spillere i databasen så bridgemate kan vise dem.
    repo.insert_players(bws_path, club_id)

    while True:
        last_mtime = repo.send_results(bws_path, last_mtime, club_id, section_id)
        time.sleep(POLL_MS / 1000.0)
        
if __name__ == "__main__":
    run_sync()


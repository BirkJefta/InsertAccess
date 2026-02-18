import urllib3
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

    while True:
        try:
            current_mtime = os.path.getmtime(bws_path)

            if current_mtime > last_mtime:
                #hvis filen er ændret siden sidste tjek, så hent data og send til API
                results = database.fetch_results(bws_path)
                if results:
                    payload = {
                        "ClubId": int(club_id),
                        "SectionId": int(section_id),
                        "Results": results
                    }
                    response = requests.post(f"{API_BASE_URL}/Results", json=payload, timeout=5,verify=False)
                    if response.status_code in [200, 201]:
                        print(f"[{time.strftime('%H:%M:%S')}] Sync succesfuld! {len(results)} rækker sendt.")
                        last_mtime = current_mtime
                    else:
                        print(f"[{time.strftime('%H:%M:%S')}] Server svarede med fejl: {response.status_code}")

        except requests.RequestException as e:
            print(f"Fejl ved API-kald: {e}")
        except Exception as e:
            print(f"Fejl under datahentning eller API-kald: {e}")



        time.sleep(POLL_MS / 1000.0)
if __name__ == "__main__":
    run_sync()


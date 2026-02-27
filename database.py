#fil til at håndtere databaseforbindelsen og dataudtræk fra BWS--filen.
#Åbner access filen direkte, eller laver en kopi hvis den er låst, og åbner kopien i stedet.
#Metoder til at hente eller indsætte data i access filen, og mappe det til et format som kan sendes til API'et i json format.




#Driver til access database
import pyodbc
#til at håndtere låste filer og lave midlertidige kopier
import shutil
#adgang til operativsystemets funktioner
import os
#spørger hvert 5 sekund om der er ændringer i bws filen
import time
from datetime import datetime
from config import TEMP_DIR
import socket


#get tournament data from the database

def get_connection(bws_path):
    #spørg hvilken driver de har
    all_drivers = [d for d in pyodbc.drivers() if 'Access' in d and '(*.mdb' in d]
    if not all_drivers:
        raise Exception("Ingen Access-drivere fundet. Er Microsoft Access Database Engine installeret?")
    driver = all_drivers[0]
    try:
        conn_str = f"DRIVER={{{driver}}};DBQ={bws_path};"
        return pyodbc.connect(conn_str, timeout=2),None
    except Exception:
         #lav kopi hvis filen ikke kan åbnes 
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR)
        #kopi med samme endelse som originalen (bws eller mdb)
        ext = os.path.splitext(bws_path)[1]
        copy_path = os.path.join(TEMP_DIR, f"live_copy{ext}")
        shutil.copy2(bws_path, copy_path)
        #prøv at åbne kopien
        try:
            conn_str = f"DRIVER={{{driver}}};DBQ={copy_path};"
            return pyodbc.connect(conn_str, timeout=2), copy_path
        except Exception as e:
            #hvis det stadig ikke virker, så giv en fejl
            raise Exception(f"Kunne ikke åbne data {e}")

#Client tabel i access
def insert_client_info(bws_path):
    pc_name = socket.gethostname()
    all_drivers = [d for d in pyodbc.drivers() if 'Access' in d and '(*.mdb' in d]
    if not all_drivers:
        print("Ingen driver fundet")
        return None
    
    conn_str = f"DRIVER={{{all_drivers[0]}}};DBQ={bws_path};"
    try:
        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()

        #Tjek om pc'en allerede er registreret, hvis den er gemmer vi dens ID, ellers opretter vi en ny client
        cursor.execute("SELECT ID FROM Clients WHERE Computer = ?", (pc_name,))
        row = cursor.fetchone()

        if row:
            client_id = row[0]
        else:
            cursor.execute("INSERT INTO Clients (Computer) VALUES (?)", (pc_name,))
            cursor.execute("SELECT @@IDENTITY")
            client_id = int(cursor.fetchone()[0])
            conn.commit()
        return client_id
    except Exception as e:
        print(f"Fejl ved indsættelse af client info: {e}")
        return None
    finally:
        if 'conn' in locals(): conn.close()
        


def fetch_results(bws_path):
    #hent data og map dem. Send i Json format.
    conn, copy_path = get_connection(bws_path)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM RoundData")
        #hent coloumns så man ved hvad dataen repræsenterer i access
        columns = [column[0] for column in cursor.description]
        #da der bruges forskellig navne i forskellige versioner af access, så lav en masse gæt

        def pick(candidates):
            for c in candidates:
                for col in columns:
                    #lower for at gøre det case-insensitive
                    if col.lower() == c.lower(): return col
            #kan den ikke finde nogen, giver den op
            return None
        
        #mapper de forskellige navne til et navn som bruges i json outputtet
        mapping = {
            'Section': pick(['Section', 'SectionID', 'SectionNr']) or 'Section',
            'Round': pick(['Round', 'RoundNr', 'RoundNo', 'Rnd']),
            'Table': pick(['Table', 'TableNr', 'TableNo', 'TableID']),
            'NS': pick(['NSPair', 'PairNS', 'NS']),
            'EW': pick(['EWPair', 'PairEW', 'EW']),
            'Low': pick(['LowBoard', 'Low', 'LowBrd']),
            'High': pick(['HighBoard', 'High', 'HighBrd']),
            'Custom': pick(['CustomBoards', 'Custom'])
        }

        results = []
        #gem i en dictionary, zip så kolonnenavne (key) samles med værdierne i rækken (values)
        for row in cursor.fetchall():
            row_dict = dict(zip(columns, row))
            results.append({
                'Section': row_dict.get(mapping['Section'], 1),
                'Round': row_dict.get(mapping['Round']),
                'Table': row_dict.get(mapping['Table']),
                'NS': row_dict.get(mapping['NS']),
                'EW': row_dict.get(mapping['EW']),
                'Low': row_dict.get(mapping['Low']),
                'High': row_dict.get(mapping['High']),
                'Custom': row_dict.get(mapping['Custom'])
            })
        return results
    finally:
        cursor.close()
        conn.close()
        #slet kopien for at undgå rod i temp mappen
        if copy_path and os.path.exists(copy_path):
            os.remove(copy_path)



def insert_main_players(bws_path, players):
    all_drivers = [d for d in pyodbc.drivers() if 'Access' in d and '(*.mdb' in d]
    if not all_drivers: return
    
    conn_str = f"DRIVER={{{all_drivers[0]}}};DBQ={bws_path};"
    try:
        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM PlayerNames") # Rydder tabellen før indsættelse
        sql = "INSERT INTO PlayerNames (ID, Name, strID) VALUES (?, ?, ?)"
        data_to_insert = [(p['ID'], p['Name'], p['strID']) for p in players]
        cursor.executemany(sql, data_to_insert)
        conn.commit()
        print(f"Indsatte {len(players)} spillere i PlayerNames tabellen.")
    except Exception as e:
        print(f"Fejl ved indsættelse af spillere: {e}")
        conn.rollback()
    finally:
        cursor.close()
        if 'conn' in locals(): conn.close()

#indsæt session info i access hvis den er tom, eller opdater den hvis noget er ændret.
def insert_session_info(bws_path,session_info):
    all_drivers = [d for d in pyodbc.drivers() if 'Access' in d and '(*.mdb' in d]
    if not all_drivers: return
    
    conn_str = f"DRIVER={{{all_drivers[0]}}};DBQ={bws_path};"

    #da date og time er opdelt i access, men samlet fra api, skal det splittes.
    name = session_info.get("Name", "")
    raw_dt = session_info.get("StartDateTime", "1970-01-01T00:00:00").replace('Z', '')
    dt_obj = datetime.fromisoformat(raw_dt)
    date = dt_obj.date()
    time = dt_obj.time()


    try:
        #opdaterer session info i access, hvis den allerede findes, ellers indsætter den
        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT ID, GUID FROM Session")
        row = cursor.fetchone()
        #hvis der allerede er en session, opdater den, ellers indsæt en ny
        if row:
            current_id = row[0]
            sql = "UPDATE Session SET Name = ?, [Date] = ?, [Time] = ? WHERE ID = ?"
            cursor.execute(sql, (name, date, time, current_id))
        else:
            sql = "INSERT INTO Session (ID, Name, [Date], [Time], GUID, Status, ShowInApp, PairsMoveAcrossField, EWReturnHome) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
            cursor.execute(sql, (1, name, date, time, None, 0, 0, 0, 0))
        conn.commit()
        return current_id
        
    except Exception as e:
        print(f"Fejl ved indsættelse eller opdatering af session info: {e}")

    finally:
        cursor.close()
        if 'conn' in locals(): conn.close()

def insert_section_info(bws_path,section_info, session_id):
    all_drivers = [d for d in pyodbc.drivers() if 'Access' in d and '(*.mdb' in d]
    if not all_drivers: return
    
    conn_str = f"DRIVER={{{all_drivers[0]}}};DBQ={bws_path};"
    letter = section_info.get("AccessLetter", "")
    missing_pair = section_info.get("MissingPair", 0)
    tables = section_info.get("NoOfTables", 0)
    session = session_id
    scoring_type = 1 #1 for matchpoint, 2 for IMPs, 3 for Board-a-Match 4 for team. TODO: find ud af hvordan man finder korrekte
    is_mitchell = section_info.get("IsMitchell",0)
    winners = 1 #antal vindere. Hvis det er mitchell, så er der 2 vindere, ellers 1.

    if is_mitchell == 1:
        winners = 2
    
    try:
        with pyodbc.connect(conn_str, timeout=5) as conn:
            cursor = conn.cursor()
            access_id = 1

            cursor.execute("SELECT COUNT(*) FROM Section WHERE ID = ?", (access_id,))
            exists = cursor.fetchone()[0] > 0
            if exists:
                sql = "UPDATE Section SET Letter = ?, [Tables] = ?, MissingPair = ?, EWMoveBeforePlay = ?, [Session] = ?, ScoringType = ?, Winners = ? WHERE ID = ?"
                params = (letter, tables, missing_pair, 0, session, scoring_type, winners, access_id)
            else:
                sql = "INSERT INTO Section (ID, Letter, [Tables], MissingPair, EWMoveBeforePlay, [Session], ScoringType, Winners) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                params = (access_id, letter, tables, missing_pair, 0, session, scoring_type, winners)
            
            cursor.execute(sql, params)
            conn.commit()
    except Exception as e:
        print(f"Fejl ved indsættelse af section info: {e}")






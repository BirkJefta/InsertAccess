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


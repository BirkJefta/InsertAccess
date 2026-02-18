#kode til at bruger kan vælge fil til at læse fra og indtaste klub, så frontend ved hvem den skal vise resultater fra

import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox # simpledialog bruges til tekst
import json
import os
import re

def suggest_section_id(file_path):
    filename = os.path.basename(file_path)
    #find tallet i filnavnet.
    numbers = re.findall(r'\d+', filename)
    return numbers[0] if numbers else ""


def get_club_settings():
    settings_file = "settings.json"
    settings = {}
    
    # 1. Tjek om vi allerede har gemt indstillingerne
    if os.path.exists(settings_file):
        with open(settings_file, "r") as f:
            settings = json.load(f)

    # 2. Hvis ikke, så opret et lille vindue til indtastning
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    # Spørg efter Klub ID
    #TODO: valider at det er et gyldigt klub ID, og at det ikke er tomt, evt. med en dropdown.
    #hvis klub id er gemt, spørg om de vil bruge det, eller indtaste et nyt

    # 2. Hvis der allerede er gemt en klub, spørg om de vil fortsætte med den eller indtaste en ny
    if settings.get("ClubId"):
        # Spørg om de vil fortsætte som den gemte klub
        svar = messagebox.askyesno("Log ind", f"Vil du logge ind som '{settings['ClubId']}'?\n(Vælg 'Nej' for at skifte klub)")
        
        if not svar:
            # Hvis de svarer nej, spørg om nyt ID
            nyt_id = simpledialog.askstring("Log ind", "Indtast nyt Klub ID:")
            if nyt_id:
                settings["ClubId"] = nyt_id.upper().strip()
            else:
                messagebox.showerror("Fejl", "Klub ID skal udfyldes.")
                exit()
    else:
        # Hvis der slet ikke findes gemte indstillinger
        club_id = simpledialog.askstring("Førstegangs opsætning", "Indtast dit Klub ID:")
        if not club_id:
            exit()
        settings["ClubId"] = club_id.upper().strip()

    #samme mappe som sidst.
    last_dir = os.path.dirname(settings.get("path", ""))

    # Spørg efter Filstien
    file_path = filedialog.askopenfilename(
        title=f"Velkommen {settings['ClubId']} - Vælg din BridgeMate fil",
        initialdir=last_dir,
        filetypes=[("BridgeMate filer", "*.bws *.mdb")]
    )

    if not file_path:
        if settings.get("path") and messagebox.askyesno("Fortsæt?", f"Ingen ny fil valgt. Vil du bruge den gamle?:\n{settings['path']}"):
            file_path = settings["path"]
        else:
            messagebox.showwarning("Afbrudt", "Ingen fil valgt. Lukker.")
            exit()

    suggestion = suggest_section_id(file_path)
    section_id = simpledialog.askstring(
        "Bekræft Sektion", 
        f"Hvilken sektion er dette?\nFil: {os.path.basename(file_path)}",
        initialvalue=suggestion
        )
    
    if not section_id or not section_id.isdigit():
        messagebox.showerror("Fejl", "Sektion ID skal være et tal.")
        exit()

    settings["path"] = file_path
    settings["SectionId"] = section_id
    
    with open(settings_file, "w") as f:
        json.dump(settings, f)
        
    return settings
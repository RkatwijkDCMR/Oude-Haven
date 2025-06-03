# -*- coding: utf-8 -*-
"""
Created on Tue Jun  3 10:21:49 2025

@author: rkk
"""

# -*- coding: utf-8 -*-
"""
Created on Wed Feb 12 11:43:37 2025
Aangepast door: jouw naam
Beschrijving: Scrape alleen de punten voor opgegeven datums en uren.
"""

import time
import os
import math
import datetime
import pyautogui
import pandas as pd  # Voor het opslaan van de metadata
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import StaleElementReferenceException

# ---------------------------
# Stap 0: Definieer hier de gewenste datums en uren (pas dit aan)
# Formaat: "YYYY-MM-DD": [u1, u2, ...]  (uren in 24-uurs notatie, bijv. 0..23)
desired_datetimes = {
    "2024-10-14": [10, 11],    # scrape 14 okt 2024 om 10:00 en 11:00
    "2024-10-15": [12, 13, 14] # scrape 15 okt 2024 om 12:00, 13:00 en 14:00
}
# ---------------------------

# Mapping dict voor Franse naar Nederlandse dagen/maanden (ongewijzigd)
french_to_dutch_days = {
    'lundi': 'maandag',
    'mardi': 'dinsdag',
    'mercredi': 'woensdag',
    'jeudi': 'donderdag',
    'vendredi': 'vrijdag',
    'samedi': 'zaterdag',
    'dimanche': 'zondag'
}

french_to_dutch_months = {
    'janvier': 'januari',
    'janv.': 'januari',
    'févr.': 'februari',
    'mars': 'maart',
    'avril': 'april',
    'avr.': 'april',
    'mai': 'mei',
    'juin': 'juni',
    'juil.': 'juli',
    'août': 'augustus',
    'sept.': 'september',
    'oct.': 'oktober',
    'nov.': 'november',
    'déc.': 'december'
}

french_month_to_number = {
    'janvier': 1,
    'janv.': 1,
    'févr.': 2,
    'mars': 3,
    'avril': 4,
    'avr.':4,
    'mai': 5,
    'juin': 6,
    'juil.': 7,
    'août': 8,
    'sept.': 9,
    'oct.': 10,
    'nov.': 11,
    'déc.': 12
}

# Om van Nederlandse maandnaam direct een getal te maken
dutch_month_to_number = {
    'januari': 1, 'februari': 2, 'maart': 3, 'april': 4,
    'mei': 5, 'juni': 6, 'juli': 7, 'augustus': 8,
    'september': 9, 'oktober': 10, 'november': 11, 'december': 12
}

# ---------------------------
# Stap 1: Selenium WebDriver instellen
options = webdriver.ChromeOptions()
options.binary_location = "C:/Program Files/Google/Chrome/Application/chrome.exe"
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# Stap 2: Open de website en laat gebruiker handmatig inloggen/alles klaarzetten
search_url = "https://mesure.bruitparif.fr/priv/rotterdam/immersive"
driver.get(search_url)
input("Druk op Enter nadat de pagina volledig is ingeladen en je bent ingelogd (indien nodig)...")

# Stap 3: Basisfolder waarin alle foto's en metadata komen (pas dit pad aan)
base_folder = r"C:\Users\rkk\.spyder-py3\scrippies\Oude haven\Foto's"
os.makedirs(base_folder, exist_ok=True)

# Wachtobject voor Selenium
wait = WebDriverWait(driver, 10)  # Maximaal 10 sec wachten op elementen

# ---------------------------
# PARSEN VAN DE EERSTE WEEK OM STARTDATUM TE BEPALEN
try:
    display_period_elem = driver.find_element(
        By.CSS_SELECTOR, "date-display span[data-bind='text: DisplayPeriod']"
    )
    display_text_init = display_period_elem.text.strip()
    # Verwijder "du " en split op " au "
    if not display_text_init.startswith("du "):
        raise Exception("Onverwacht formaat display period: " + display_text_init)
    content_init = display_text_init[3:].strip()
    parts_init = content_init.split(" au ")
    if len(parts_init) != 2:
        raise Exception("Onverwacht formaat display period: " + display_text_init)

    tokens1_init = parts_init[0].strip().split()
    tokens2_init = parts_init[1].strip().split()

    # Bepaal startdag, startmaand en jaar
    if len(tokens1_init) == 1:
        start_day_init = int(tokens1_init[0])
        start_month_fr_init = tokens2_init[1]
        year_init = int(tokens2_init[2])
    else:
        start_day_init = int(tokens1_init[0])
        start_month_fr_init = tokens1_init[1]
        if len(tokens1_init) >= 3:
            try:
                year_init = int(tokens1_init[2])
            except ValueError:
                year_init = int(tokens2_init[-1])
        else:
            year_init = int(tokens2_init[-1])

    month_num_init = french_month_to_number.get(start_month_fr_init, None)
    if month_num_init is None:
        raise Exception("Onbekende Franse maand: " + start_month_fr_init)
    initial_start_date = datetime.date(year_init, month_num_init, start_day_init)

except Exception as e:
    print("Fout bij het parsen van de initiële display period:", e)
    driver.quit()
    raise SystemExit(1)

# Converteer de gewenste datums (strings) naar date-objecten
desired_date_objects = {}
for date_str, hours in desired_datetimes.items():
    try:
        yyyy, mm, dd = date_str.split("-")
        date_obj = datetime.date(int(yyyy), int(mm), int(dd))
        desired_date_objects[date_obj] = hours
    except Exception as e:
        print(f"Fout in gewenste datum formaat '{date_str}': {e}")
        driver.quit()
        raise SystemExit(1)

# Bepaal voor elke gewenste datum in welke week (offset vanaf initial_start_date) die valt
week_to_dates = {}
for date_obj, hours in desired_date_objects.items():
    diff_days = (date_obj - initial_start_date).days
    if diff_days < 0:
        print(f"Waarschuwing: gewenste datum {date_obj} ligt vóór de initiële week ({initial_start_date}). Wordt overgeslagen.")
        continue
    week_idx = diff_days // 7  # weekindex ten opzichte van week 0 = initiële week
    week_to_dates.setdefault(week_idx, []).append(date_obj)

if not week_to_dates:
    print("Er zijn (na filtering) geen datums binnen of na de initiële week. Script stopt.")
    driver.quit()
    raise SystemExit(0)

# Bepaal de maximale weekindex die we moeten bezoeken
max_week_idx = max(week_to_dates.keys())

# ---------------------------
# LOOP OVER ALLE NODIGE WEKEN
current_week_idx = 0  # de huidige positionering (0 = initiële week)
for target_week_idx in sorted(week_to_dates.keys()):
    # Eerst: klik zo nodig (target_week_idx - current_week_idx) keer op "Volgende week"
    shifts = target_week_idx - current_week_idx
    for _ in range(shifts):
        try:
            next_week_button = driver.find_element(
                By.CSS_SELECTOR, "button[title='Décaler de la même durée vers le futur']"
            )
            next_week_button.click()
            time.sleep(5)  # even wachten tot de nieuwe week geladen is
        except Exception as e:
            print(f"Kon niet naar week {current_week_idx+1}→{current_week_idx+2} navigeren: {e}")
            driver.quit()
            raise SystemExit(1)
    current_week_idx = target_week_idx

    # NU STAAN WE IN DE JUISTE WEEK. Haal de display_period opnieuw op (optioneel, voor naamgeving)
    try:
        display_period_elem = driver.find_element(
            By.CSS_SELECTOR, "date-display span[data-bind='text: DisplayPeriod']"
        )
        display_text = display_period_elem.text.strip()
    except Exception as e:
        print(f"Fout bij ophalen display_period in week {current_week_idx}: {e}")
        driver.quit()
        raise SystemExit(1)

    # Analyseer opnieuw de startdatum van deze week (voor folder-structuur)
    try:
        content = display_text[3:].strip()
        parts = content.split(" au ")
        tokens1 = parts[0].strip().split()
        tokens2 = parts[1].strip().split()
        if len(tokens1) == 1:
            start_day = int(tokens1[0])
            start_month_fr = tokens2[1]
            year = int(tokens2[2])
        else:
            start_day = int(tokens1[0])
            start_month_fr = tokens1[1]
            if len(tokens1) >= 3:
                try:
                    year = int(tokens1[2])
                except ValueError:
                    year = int(tokens2[-1])
            else:
                year = int(tokens2[-1])
        month_num = french_month_to_number.get(start_month_fr, None)
        if month_num is None:
            month_num = 0
        # Bepaal Nederlandse maandnaam
        dutch_month = french_to_dutch_months.get(start_month_fr, start_month_fr)
        # Bereken het weeknummer voor folder (optioneel, behoud jouw methode)
        first_day = datetime.date(year, month_num, 1)
        week_number = math.ceil((start_day + first_day.weekday()) / 7)
    except Exception as e:
        print("Fout bij het parsen van de display period (folder-structuur):", e)
        driver.quit()
        raise SystemExit(1)

    # Maak folder-structuur: maand en week
    month_folder = os.path.join(base_folder, dutch_month)
    os.makedirs(month_folder, exist_ok=True)
    week_folder = os.path.join(month_folder, f"Week {week_number}")
    os.makedirs(week_folder, exist_ok=True)

    # Metadata-lijst voor deze week
    week_metadata = []

    # Haal alle highcharts-point elementen op
    original_paths = driver.find_elements(By.CSS_SELECTOR, "path.highcharts-point")
    if not original_paths:
        print(f"Geen data-punten gevonden in week {current_week_idx}.")
        continue

    # Sorteer de punten op x en y voor voorspelbare volgorde
    sorted_points = sorted(original_paths, key=lambda e: (e.location['x'], e.location['y']))

    # We willen alleen de datums die in deze week thuishoren:
    dates_in_this_week = week_to_dates.get(current_week_idx, [])

    # Tel de opgeslagen afbeeldingen in deze week (voor oplopende nummering)
    saved_counter = 1

    for p in sorted_points:
        for attempt in range(3):  # MAX_RETRIES = 3
            try:
                if not p.is_displayed():
                    # Probeer p opnieuw te vinden op vergelijkbare coordinaten
                    nieuwe_punten = driver.find_elements(By.CSS_SELECTOR, "path.highcharts-point")
                    for np in nieuwe_punten:
                        if abs(np.location['x'] - p.location['x']) < 5 and abs(np.location['y'] - p.location['y']) < 5:
                            p = np
                            break
                    else:
                        raise Exception("Element niet zichtbaar en niet opnieuw gevonden.")

                # Klik op het datapunt om info te tonen
                ActionChains(driver).move_to_element_with_offset(
                    p, p.size['width'] / 2, p.size['height'] / 2
                ).click().perform()
                time.sleep(2)  # wacht tot tooltip/overlay verschijnt

                # Scrape de overlayinformatie
                try:
                    leq_element = driver.find_element(
                        By.CSS_SELECTOR, "div.dba > div.number[data-bind='text: $component.ServiceInfoLeq']"
                    )
                    leq_value = leq_element.text
                except Exception:
                    leq_value = None

                try:
                    time_element = driver.find_element(
                        By.CSS_SELECTOR, "div.time > span[data-bind='text: $component.ServiceInfoFromTo']"
                    )
                    time_text = time_element.text
                    # Vertaal Franse dagen/maanden naar Nederlands
                    for fr_day, nl_day in french_to_dutch_days.items():
                        time_text = time_text.replace(fr_day, nl_day)
                    for fr_month, nl_month in french_to_dutch_months.items():
                        time_text = time_text.replace(fr_month, nl_month)
                except Exception:
                    time_text = None

                # Als we time_text hebben, parse de datum en het uur
                if time_text:
                    # Verwacht tokens zoals ["maandag","14","oktober","2024","10:00","-","11:00"]
                    tokens = time_text.split()
                    if len(tokens) >= 5:
                        try:
                            dag_num = int(tokens[1])
                            maand_nl = tokens[2]
                            jaar = int(tokens[3])
                            uur_str = tokens[4]  # bv "10:00"
                            uur_int = int(uur_str.split(":")[0])
                            # Maak date-object
                            maand_num = dutch_month_to_number.get(maand_nl, None)
                            if maand_num is not None:
                                punt_date = datetime.date(jaar, maand_num, dag_num)
                            else:
                                raise Exception(f"Onbekende maandnaam: {maand_nl}")
                        except Exception as e_parse:
                            punt_date = None
                            uur_int = None
                            print("Parsing time_text mislukt:", e_parse)
                    else:
                        punt_date = None
                        uur_int = None
                else:
                    punt_date = None
                    uur_int = None

                # Controleren of deze punt voldoet aan gewenste datum en uur
                to_save = False
                if punt_date and uur_int is not None:
                    if punt_date in dates_in_this_week:
                        gewenste_uren = desired_date_objects.get(punt_date, [])
                        if uur_int in gewenste_uren:
                            to_save = True

                if to_save:
                    # Sla de afbeelding op via context-click op canvas
                    canvas = wait.until(EC.presence_of_element_located((By.TAG_NAME, "canvas")))
                    ActionChains(driver).context_click(canvas).perform()
                    time.sleep(1)
                    pyautogui.press("down", presses=1, interval=0.2)
                    pyautogui.press("enter")
                    time.sleep(1)

                    # Geef bestandsnaam gebaseerd op datum en uur
                    date_str_fmt = punt_date.strftime("%Y%m%d")
                    image_filename = f"{date_str_fmt}_{uur_int:02d}.png"
                    image_save_path = os.path.join(week_folder, image_filename)
                    pyautogui.write(image_save_path)
                    time.sleep(1)
                    pyautogui.press("enter")
                    time.sleep(1)

                    # Voeg metadata toe
                    week_metadata.append({
                        "image_filename": image_filename,
                        "leq": leq_value,
                        "time_info": time_text,
                        "display_period": display_text
                    })
                    saved_counter += 1

                else:
                    # Sluit tooltip met Escape als we niet opslaan
                    pyautogui.press("esc")
                    time.sleep(0.5)

                break  # stop retry-loop als gelukt

            except StaleElementReferenceException:
                time.sleep(1)
            except Exception as e:
                print(f"Fout bij verwerken punt (poging {attempt+1}): {e}")
                # Probeer niet eindeloos, ga naar volgende punt
                break

    # Sla de metadata voor deze week op (in week-folder)
    if week_metadata:
        metadata_file = os.path.join(week_folder, "metadata.pkl")
        pd.DataFrame(week_metadata).to_pickle(metadata_file)
        print(f"Week {current_week_idx} (start {initial_start_date + datetime.timedelta(weeks=current_week_idx)}) – "
              f"{len(week_metadata)} afbeeldingen bewaard in {week_folder}.")
    else:
        print(f"Week {current_week_idx}: geen punten die voldeden aan de filter. Geen metadata weggeschreven.")

# Sluit de browser
driver.quit()
print("Proces voltooid!")

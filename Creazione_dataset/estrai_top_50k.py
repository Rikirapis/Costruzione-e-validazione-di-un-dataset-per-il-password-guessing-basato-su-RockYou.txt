# tronca in base allo score il dataset a 50000 password

import json
import os

INPUT_FILE = 'password_scored_progress.jsonl'
OUTPUT_FILE = 'top_50k_passwords.txt'
TARGET_COUNT = 50000

def estrai_top_50k_testo():
    # controlli sul file
    if not os.path.exists(INPUT_FILE):
        print(f"Errore: Il file {INPUT_FILE} non esiste.")
        return

    dati = []
    print(f"Lettura del file {INPUT_FILE} in corso...")

    # Legge tutte le righe valide
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            try:
                record = json.loads(linea)
                if 'password' in record and 'score' in record:
                    dati.append(record)
            except json.JSONDecodeError:
                pass

    if len(dati) == 0:
        print("Nessun dato da elaborare.")
        return

    # Ordina per score in ordine decrescente 
    dati_ordinati = sorted(dati, key=lambda x: x['score'], reverse=True)

    # Prende le prime 50.000 (o il massimo che può ricavare)
    top_50k = dati_ordinati[:TARGET_COUNT]
    
    print(f"Salvataggio di {len(top_50k)} password nel file {OUTPUT_FILE}...")
    
    # Salvataggio in formato TXT (solo password e \n)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for record in top_50k:
            f.write(record['password'] + '\n')
            
    print(f"\n[V] Estrazione completata! Il tuo dizionario è pronto in: {OUTPUT_FILE}")

if __name__ == '__main__':
    estrai_top_50k_testo()
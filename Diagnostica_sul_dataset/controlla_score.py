# controllo diagnostico sui record a cui è già stato assegnato il dataset per decidere
# se interrompere la computazione di "associa_score.py"

import json
from collections import Counter
import os

# Nome del file che sta venendo popolato da Claude
INPUT_FILE = 'password_scored_progress.jsonl'

def analizza_distribuzione():
    # controlli sul file 
    if not os.path.exists(INPUT_FILE):
        print(f"Errore: Il file {INPUT_FILE} non esiste ancora.")
        return

    punteggi = []
    totale_password = 0

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        # per ogni riga inserisce gli score nel vettore punteggi
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            try:
                dati = json.loads(linea)
                if 'score' in dati:
                    punteggi.append(dati['score'])
                    totale_password += 1
            except json.JSONDecodeError:
                # Ignora righe nel formato errato
                pass 

    if totale_password == 0:
        print("Il file è ancora vuoto o non contiene dati validi.")
        return

    # Conta le frequenze di ogni score (da 0 a 5)
    conteggi = Counter(punteggi)
    
    # Stampa i risultati ordinati in forma di tabella
    print("=" * 45)
    print(f"TOTALE PASSWORD ANALIZZATE FINORA: {totale_password}")
    print("=" * 45)
    print(f"{'PUNTEGGIO':<12} | {'QUANTITÀ':<12} | {'PERCENTUALE'}")
    print("-" * 45)
    
    for score in range(6): 
        quantita = conteggi.get(score,0)
        percentuale = (quantita / totale_password) * 100
        print(f"Score {score:<6} | {quantita:<12} | {percentuale:.2f}%")

    
    print("=" * 45)
    
    print(f"\nSomma delle quantità a score > 0: {conteggi.get(1,0) + conteggi.get(2,0) + conteggi.get(3,0)}")
    

if __name__ == '__main__':
    analizza_distribuzione()

# Diagnostica: verifica se le righe vuote nel dataset sono RAGGRUPPATE (blocchi falliti) o
# SPARSE (password singole saltate)

# Misura le 'run' di righe vuote consecutive e ne mostra la distribuzione.
# Molte run lunghe ~30, sono blocchi interi falliti.
# Molte run da 1-2, sono le vuote sparse.

import json
from collections import Counter

INPUT_DATASET = 'dataset_pii_finale.jsonl'


def e_vuota(rec):
    # true se non ci sono elementi all'interno del record oltre alla password
    return not any([rec.get('n'), rec.get('c'), rec.get('dt'),
                    rec.get('az'), rec.get('ab')])



def main():
    stato = []  
    with open(INPUT_DATASET, encoding='utf-8') as f:

        for linea in f:
            linea = linea.strip() 

            if not linea:
                continue 
            try:
                rec = json.loads(linea)
            except json.JSONDecodeError: 
                continue
    #si inserisce nel vettore di booleani lo stato associato al record della pass True=vuota, False=piena
            stato.append(e_vuota(rec))

    # per calcolare le run di vuote consecutive (vale anche per valori singoli)
    run_vuote = [] 
    corrente = 0
    for v in stato:
        if v:
            corrente += 1 
        else:
            if corrente > 0:
                run_vuote.append(corrente) 
            corrente = 0 
    if corrente > 0:
        run_vuote.append(corrente) 

    tot = len(stato)
    tot_vuote = sum(stato) 

    #stampa prima diagnosi
    print(f"Righe totali: {tot} | vuote: {tot_vuote} ({100*tot_vuote/tot:.1f}%)") 
    print(f"Numero di 'run' di vuote consecutive (vale anche per singoli elementi): {len(run_vuote)}") 
    print(f"Run più lunga: {max(run_vuote)} righe consecutive vuote\n")

    #calcolo del numero di run per fascia (in una buona distribuzione prevarrebbero le singole/le minori di 4)
    fasce = Counter()
    for r in run_vuote:
        if r == 1:
            fasce['1 (isolata)'] += 1
        elif r <= 3:
            fasce['2-3'] += 1
        elif r <= 10:
            fasce['4-10'] += 1
        elif r <= 25:
            fasce['11-25'] += 1
        elif r <= 35:
            fasce['26-35 (~1 blocco)'] += 1
        else:
            fasce['36+ (blocchi multipli)'] += 1

    # diagnosi finale
    righe_in_run_lunghe = sum(r for r in run_vuote if r >= 11)
    print(f"ANALISI FINALE: Righe vuote in run lunghe (11+): {righe_in_run_lunghe} "f"({100*righe_in_run_lunghe/tot_vuote:.0f}% delle vuote)")
    if righe_in_run_lunghe > tot_vuote * 0.5:
        print("=> Prevalgono i BLOCCHI FALLITI: serve riprocessare i blocchi")
    else:
        print("=> Prevalgono le vuote SPARSE: password singole saltate, distribuzione più valida.")


if __name__ == '__main__':
    main()

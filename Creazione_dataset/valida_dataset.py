# Validazione del dataset PII estratto.
# Controlla l'output del modello con regole deterministiche
# e marca i record sospetti con un motivo, per una possibile revisione manuale a campione.

    # è possibile decommentare le righe tra """ ... """ per scrivere un report csv per la revisione manuale 


import json
import re
import os
"""
import csv
"""
from verifica_leet import is_substring_leet   # verifica substring leet-aware

INPUT_FILE = 'dataset_pii_finale.jsonl'
"""
REPORT_FILE = 'validazione_report.csv'
"""
# Intervallo di anni di nascita considerato plausibile
ANNO_MIN, ANNO_MAX = 1940, 2012

_non_alnum = re.compile(r'[^a-z0-9]')


def norm(s: str) -> str:
    # Normalizzazione della stringa per poter fare i check
    return _non_alnum.sub('', s.lower())


def alpha_tokens(pwd: str):
    # Estrazione dalla stringa di tutte le sequenze di caratteri maggiori di 2
    return [t for t in re.split(r'[^a-zA-Z]+', pwd) if len(t) >= 3]


def digit_runs(pwd: str):
    # Estrazione di tutte le sequenze di numeri in una lista di stringhe
    return re.findall(r'\d+', pwd)

#check dell'intervallo
def gruppo_ok(x, minv, maxv, cifre):
    if x == '--':
        return True
    return x.isdigit() and len(x) == cifre and minv <= int(x) <= maxv

def valida_data(dt: str, p_norm: str):
    # Controlla il campo dt in formato gg/mm/aaaa (con -- ammesso). Ritorna motiv
    motivi = []
    if not dt:
        return motivi

    #controlla che effettivamente ci sia una data nel campo data
    if (len(dt) != 10 or 
        dt[2] != '/' or 
        dt[5] != '/' or 
        not all(c.isdigit() or c == '-' for c in dt.replace('/', ''))):
        
        motivi.append(f"altro_campo_in_data:'{dt}'")
        return motivi

    # Suddivide la stringa data in gg, mm, aaaa e verifica se il formato è corretto
    parti = dt.split('/')
    if len(parti) != 3:
        motivi.append(f"data_formato_errato:'{dt}'")
        return motivi
    gg, mm, aaaa = parti

    if not gruppo_ok(gg, 1, 31, 2):
        motivi.append(f"giorno_non_valido:'{gg}'")
    if not gruppo_ok(mm, 1, 12, 2):
        motivi.append(f"mese_non_valido:'{mm}'")
    if not gruppo_ok(aaaa, ANNO_MIN, ANNO_MAX, 4):
        motivi.append(f"anno_non_valido:'{aaaa}'")

    # Verifica se nella password sono presenti giorno, mese e anno
    if aaaa != '--' and aaaa.isdigit() and aaaa[2:] not in p_norm and aaaa not in p_norm:
        motivi.append(f"anno_non_nella_password:'{aaaa}'")
    if gg != '--' and gg not in p_norm:
        motivi.append(f"giorno_non_nella_password:'{gg}'")
    if mm != '--' and mm not in p_norm:
        motivi.append(f"mese_non_nella_password:'{mm}'")

    return motivi


def valida_record(rec: dict):
    # Ritorna la lista dei motivi di segnalazione per ogni record
    motivi = []
    p = rec.get('p', '')
    p_norm = norm(p)
    campi_testo = {'n': rec.get('n', ''), 'c': rec.get('c', ''),
                   'az': rec.get('az', ''), 'ab': rec.get('ab', '')}
    dt = rec.get('dt', '')

    # Verifica substring dopo la pulizia dal leetspeak 
    for campo, val in campi_testo.items():
        if val and not is_substring_leet(val, p):
            motivi.append(f"INVENTATO:{campo}='{val}'")

    # Controlli sulla data 
    motivi.extend(valida_data(dt, p_norm))

    # Anno a 4 cifre plausibile presente nella password ma campo dt vuoto
    if not dt:
        for run in digit_runs(p):
            for i in range(len(run) - 3):
                sub = run[i:i + 4]
                if ANNO_MIN <= int(sub) <= ANNO_MAX:
                    motivi.append(f"data_potenzialmente_mancante:'{sub}'")
                    break
            else:
                continue
            break

    # Stesso valore in due categorie diverse
    valori = [(k, norm(v)) for k, v in campi_testo.items() if v]
    visti = {}
    for k, vn in valori:
        if vn in visti:
            motivi.append(f"duplicato:'{vn}' in {visti[vn]} e {k}")
        else:
            visti[vn] = k

    # Molti token nominali, potrebbe essere stato inferito male qualche dato nominale come abitudine
    n_tok = len(alpha_tokens(p))
    if n_tok >= 4:
        motivi.append(f"molti_token({n_tok})_rivedere")

    # Record completamente vuoto su password con token nominali
    tutto_vuoto = not any(campi_testo.values()) and not dt
    if tutto_vuoto and n_tok >= 1:
        motivi.append("possibile_estrazione_mancata")

    # Verifica se sono ancora presenti maiuscole nei campi 
    for campo, val in campi_testo.items():
        if val and val != val.lower():
            motivi.append(f"non_minuscolo:{campo}")

    return motivi


def main():
    # controllo sul file
    if not os.path.exists(INPUT_FILE):
        print(f"Errore: {INPUT_FILE} non trovato.")
        return

    totale = 0
    segnalati = 0
    conteggio_tipi = {}
    righe_report = []

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for linea in f:
            #per ogni riga valida il record con i controlli precedenti
            linea = linea.strip()
            if not linea:
                continue
            try:
                rec = json.loads(linea)
            except json.JSONDecodeError:
                # riga JSON malformata, va segnalata tra i motivi
                """
                righe_report.append({'p': linea[:60], 'motivi': 'JSON_MALFORMATO',
                                      'n': '', 'c': '', 'dt': '', 'az': '', 'ab': ''})
                """
                segnalati += 1
                conteggio_tipi['JSON_MALFORMATO'] = conteggio_tipi.get('JSON_MALFORMATO', 0) + 1
                totale += 1
                continue

            totale += 1
            motivi = valida_record(rec)
            if motivi:
                segnalati += 1
                for m in motivi:
                    tipo = m.split(':')[0].split('(')[0]
                    conteggio_tipi[tipo] = conteggio_tipi.get(tipo, 0) + 1


                """
                righe_report.append({
                    'p': rec.get('p', ''),
                    'motivi': ' | '.join(motivi),
                    'n': rec.get('n', ''), 'c': rec.get('c', ''),
                    'dt': rec.get('dt', ''), 'az': rec.get('az', ''),
                    'ab': rec.get('ab', '')
                })
                """

    # Scrittura dei motivi nella lista all'interno del file
    """
    with open(REPORT_FILE, 'w', encoding='utf-8', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=['p', 'motivi', 'n', 'c', 'dt', 'az', 'ab'])
        writer.writeheader()
        writer.writerows(righe_report)
    """
        
    # Riepilogo 
    print(f"Record totali analizzati : {totale}")
    print(f"Record segnalati         : {segnalati} ({100*segnalati/max(totale,1):.1f}%)")
    print(f"Record puliti            : {totale - segnalati}")
    print(f"\nSegnalazioni per tipo (una segnalazione conta il record piu' volte):")

    for tipo, n in sorted(conteggio_tipi.items(), key=lambda x: -x[1]):
        # in base al conteggio per ogni tipologia stampa in output i punteggi in ordine
        print(f"  {n:5d}  {tipo}")


if __name__ == '__main__':
    main()

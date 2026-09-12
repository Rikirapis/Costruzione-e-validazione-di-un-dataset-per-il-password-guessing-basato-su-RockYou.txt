
import anthropic
import time
import os
import json

from prompt_condiviso import SYSTEM_PROMPT  
from verifica_leet import marca_invenzioni  

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

INPUT_FILE = 'top_50k_passwords.txt'
OUTPUT_FILE = 'dataset_pii_finale.jsonl'
INVENZIONI_FILE = 'invenzioni_da_rivedere.jsonl'   # valori non validi 
CHUNK_SIZE = 30

MODEL = "claude-sonnet-4-6"   
MAX_TENTATIVI = 3             # massimo di errori API (+ retry vuoti) 
MAX_TOKENS = 4000         

def parse_risposta(testo_risposta):
    testo_risposta = testo_risposta.strip()
    # pulizia di sicurezza da eventuali blocchi markdown inseriti dal LLM
    if "```" in testo_risposta:
        for p in testo_risposta.split("```"):
            if "|" in p:
                testo_risposta = p.strip()
                if testo_risposta.startswith("text"):
                    testo_risposta = testo_risposta[4:].strip()
                break
    # elaborazione linea per linea dell'output atteso
    risultati = {}
    for linea in testo_risposta.split('\n'):
        linea = linea.strip()
        # salta righe vuote o righe di ragionamento che iniziano per #
        if not linea or linea.startswith('#'):
            continue
        # estrae campi delimitati da |
        parti = linea.split('|')
        if len(parti) == 6 and parti[0].strip().isdigit():
            pwd_id = parti[0].strip()
            # popola la lista con dati puliti
            risultati[pwd_id] = {
                "n": parti[1].strip().lower(),
                "c": parti[2].strip().lower(),
                "dt": parti[3].strip(),          
                "az": parti[4].strip().lower(),
                "ab": parti[5].strip().lower(),
            }
    return risultati


def estrai_chunk_pii(chunk_dict, numero_blocco, totale_blocchi):
    # preparazione della stringa di input da inviare al LLM
    lista_testo = "\n".join([f"{k}: {v}" for k, v in chunk_dict.items()])
    attesi = set(chunk_dict.keys())
    ultimo_risultato = {}
    retry_vuoto_usato = False   # la soglia-retry si attiva UNA sola volta

    tentativo = 0
    # ciclo dei tentativi per singola chiamata api
    while tentativo < MAX_TENTATIVI:
        # Chiamata API 
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {"role": "user",
                     "content": f"Estrai PII da queste password:\n{lista_testo}"}
                ],
            )
        except Exception as e:
            # ad ogni errore si attende più tempo per evitare di avere problemi di firewall
            attesa = min(5 * (2 ** tentativo), 60)
            print(f"   [!] [Blocco {numero_blocco}/{totale_blocchi}] Errore API: {e}. "
                  f"Tentativo {tentativo + 1}/{MAX_TENTATIVI}, riprovo in {attesa}s...")
            time.sleep(attesa)
            tentativo += 1
            continue

        # diagnostica utilizzo cache 
        u = response.usage
        print(f"   [cache] write={u.cache_creation_input_tokens} "
              f"read={u.cache_read_input_tokens} input={u.input_tokens} "
              f"output={u.output_tokens}")

        if response.stop_reason == "max_tokens":
            print(f"   [i] [Blocco {numero_blocco}/{totale_blocchi}] Risposta al limite "
                  f"di max_tokens: alcune righe potrebbero mancare (salvate vuote).")

        # parsing e controllo esiti della risposta 
        testo_risposta = response.content[0].text
        risultati = parse_risposta(testo_risposta)
        ultimo_risultato = risultati
        mancanti = attesi - set(risultati.keys())
        frazione_vuota = len(mancanti) / len(attesi) if attesi else 0.0

        # SOGLIA-RETRY si verifica se ha senso recuperare le stringhe (> 50% vuote)
        if frazione_vuota >= 0.5 and not retry_vuoto_usato:
            retry_vuoto_usato = True
            print(f"   [!] [Blocco {numero_blocco}/{totale_blocchi}] quasi vuoto "
                  f"({len(mancanti)}/{len(attesi)}). Output grezzo del modello "
                  f"(primi 500 char) per diagnosi:")
            # stampa estratto grezzo dell'output ottenuto
            estratto = testo_risposta.strip()[:500].replace("\n", "\n       | ")
            print("       | " + estratto)
            print("   -> ritento UNA volta.")
            time.sleep(3)
            tentativo += 1
            continue

        # Caso in cui il blocco è accettato
        if mancanti:
            print(f"   [i] [Blocco {numero_blocco}/{totale_blocchi}] "
                  f"{len(mancanti)}/{len(attesi)} righe non estratte "
                  f"(salvate vuote, si correggono in validazione).")
        return risultati

    # esauriti i tentativi: restituisce l'ultimo risultato ottenuto 
    print(f"   [X] [Blocco {numero_blocco}/{totale_blocchi}] Non recuperato dopo "
          f"{MAX_TENTATIVI} tentativi. Salvo quello che c'e' "
          f"({len(ultimo_risultato)}/{len(attesi)}).")
    return ultimo_risultato


def crea_dataset_finale():
    # controlli sul file
    if not os.path.exists(INPUT_FILE):
        print(f"Errore: {INPUT_FILE} non trovato.")
        return

    # lettura di tutto il file target
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        tutte_le_password = [line.strip() for line in f if line.strip()]

    # logica di reripresa automatica in caso di stop e riavvio
    linee_gia_fatte = 0
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as out_f:
            linee_gia_fatte = sum(1 for _ in out_f)
        print(f"Riprendo estrazione: {linee_gia_fatte} password già completate...")

    chunks = []
    chunk_corrente = {}
    # scomposizione in chunks sulla base di quanto è già stato elaborato
    for i, pwd in enumerate(tutte_le_password):
        if i < linee_gia_fatte:
            continue

        chunk_corrente[str(i)] = pwd
        if len(chunk_corrente) == CHUNK_SIZE:
            chunks.append(chunk_corrente)
            chunk_corrente = {}
    # inserisce eventuale scarto
    if chunk_corrente:
        chunks.append(chunk_corrente)

    totale_chunks = len(chunks)
    if totale_chunks == 0:
        print("Tutte le estrazioni sono state completate!")
        return

    print(f"Avvio estrazione PII ({totale_chunks} blocchi rimanenti)...")

    # ciclo principale per la scrittura del file
    tot_invenzioni = 0
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as out_f, \
         open(INVENZIONI_FILE, 'a', encoding='utf-8') as inv_f:
        completati = 0
        for chunk in chunks:
            numero_attuale = completati + 1
            estratti = estrai_chunk_pii(chunk, numero_attuale, totale_chunks)

            # Riassemblaggio del JSON per salvare i record
            for pwd_id, original_pwd in chunk.items():
                dati_pii = estratti.get(
                    pwd_id, {"n": "", "c": "", "dt": "", "az": "", "ab": ""}
                )

                record_finale = {
                    "p": original_pwd,
                    "n": dati_pii["n"],
                    "c": dati_pii["c"],
                    "dt": dati_pii["dt"],
                    "az": dati_pii["az"],
                    "ab": dati_pii["ab"]
                }

                # marcatura dei file errato con lo script di validazione 
                for sospetto in marca_invenzioni(record_finale):
                    inv_f.write(json.dumps(sospetto) + "\n")
                    tot_invenzioni += 1

                out_f.write(json.dumps(record_finale) + "\n")

            # scrittura su disco ad ogni chunk
            out_f.flush()
            inv_f.flush()
            completati += 1
            print(f"Progresso: {numero_attuale}/{totale_chunks} blocchi completati.")
            time.sleep(0.3)

    # log finale delle anomalie rilevate
    if tot_invenzioni:
        print(f"\n[i] {tot_invenzioni} valori non-substring marcati in {INVENZIONI_FILE} "
              f"(NON scartati: restano nel dataset, da rivedere).")


if __name__ == '__main__':
    crea_dataset_finale()
# script che richiama il LLM opportunamente al fine di assegnare uno score alla password in base
# al contenuto di informazioni personali della password stessa

import anthropic
import time
import os
import json

# Inizializzazione il client Anthropic con la chiave API (tramite variabile d'ambiente)
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

INPUT_FILE = 'rockyou_random_500k_bilanciato.txt'
OUTPUT_FILE = 'password_scored_progress.jsonl'
CHUNK_SIZE = 120  

SYSTEM_PROMPT = """Sei un analista esperto di cybersecurity e profiling dati (PII).
Analizza ogni password e CONTA quante categorie DISTINTE tra le 5 target sono identificabili in modo inequivocabile:

1. [nome]: Nomi propri di persona (es. mario, alex, giulia, john).
2. [cognome]: Cognomi (es. rossi, smith, bianchi, mueller).
3. [anno_nascita]: Anno verosimile a 4 cifre (1930-2025) o 2 cifre finali coerenti (es. 90, 99, 04).
4. [azienda]: Brand noti, aziende, datori di lavoro o sigle aziendali (es. ferrari, ibm, google, unibo).
5. [abitudine]: Passioni esplicite, squadre sportive, generi/artisti musicali, hobby (es. juventus, inter, rock, anime, tennis).

Regole di rigore:
- Sequenze casuali, parole del dizionario generiche o pattern da tastiera (es. 'qwerty', 'drago', 'stella', 'sole', 'ciao', '123456') NON appartengono a nessuna categoria -> Punteggio 0.
- Assegna 1 punto per ogni categoria PRESENTE E DISTINTA (punteggio finale da 0 a 5).

Formatta l'output ESCLUSIVAMENTE come ID e punteggio separati da virgola, uno per riga. 
NON inserire blocchi di codice markdown (come ```), commenti o testo introduttivo. Restituisci solo i dati grezzi.
Esempio:
0,2
1,0
2,3"""

def analizza_chunk_claude_sonnet(chunk_dict, numero_blocco, totale_blocchi):
    # formattazione della lista di password in un'unica stringa
    lista_testo = "\n".join([f"{k}: {v}" for k, v in chunk_dict.items()])
    
    while True:
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                # Il system prompt viene utilizzato attraverso cache per ridurre i costi
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"}
                    }
                ],
                messages=[
                    {
                        "role": "user", 
                        "content": f"Lista password:\n{lista_testo}"
                    }
                ]
            )
            
            risultati = {}
            testo_risposta = response.content[0].text.strip()
            
            # Pulisce eventuali tag markdown indesiderati
            if "```" in testo_risposta:
                parti_md = testo_risposta.split("```")
                for p in parti_md:
                    p_pulito = p.strip()
                    if p_pulito.startswith("csv") or p_pulito.startswith("text"):
                        p_pulito = p_pulito[3:].strip()
                    if "," in p_pulito and "\n" in p_pulito:
                        testo_risposta = p_pulito
                        break

            # estrazione dei risultati e inserimento dello score
            for linea in testo_risposta.split('\n'):
                linea = linea.strip()
                if ',' in linea:
                    parti = linea.split(',')
                    if len(parti) == 2 and parti[0].strip().isdigit() and parti[1].strip().isdigit():
                        risultati[parti[0].strip()] = int(parti[1].strip())
                        
            return risultati
            
        except Exception as e:
            # ritenta dopo 5 secondi se si verificano errori
            print(f"   [!] [Blocco {numero_blocco}/{totale_blocchi}] Errore di rete con Claude: {e}. Riprovo tra 5s...")
            time.sleep(5)

def elabora_dataset():
    # controlli sul file di input

    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            tutte_le_password = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Errore: File {INPUT_FILE} non trovato.")
        return

    # sezione dedicata alla ripresa dell'elaborazione dal punto in cui si era fermato se si dovessero verificare problemi
    linee_gia_fatte = 0
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as out_f:
            linee_gia_fatte = sum(1 for _ in out_f)
        print(f"Trovate {linee_gia_fatte} password già elaborate. Riprendo dal punto di interruzione...")

    chunks = []
    chunk_corrente = {}

    # divisione delle password in chunks
    for i, pwd in enumerate(tutte_le_password):
        # Salta le password già elaborate
        if i < linee_gia_fatte:
            continue
            
        chunk_corrente[str(i)] = pwd
        if len(chunk_corrente) == CHUNK_SIZE:
            chunks.append(chunk_corrente)
            chunk_corrente = {}
    # per inserire l'ultimo blocco
    if chunk_corrente:
        chunks.append(chunk_corrente)

    # nel caso in cui sono state mandate tutte le richieste, non c'è bisogno di continuare
    totale_chunks = len(chunks)
    if totale_chunks == 0:
         print("Tutte le password sono state già elaborate!")
         return

    print(f"Avvio elaborazione con Claude 4.6 Sonnet ({totale_chunks} blocchi rimanenti)...")
    
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as out_f:
        completati = 0
        for chunk in chunks:
            # calcolo del numero di blocco reale basato sulle password fatte
            numero_attuale = completati + 1
            punteggi = analizza_chunk_claude_sonnet(chunk, numero_attuale, totale_chunks)

            # salvataggio in formato JSONL
            for pwd_id, score in punteggi.items():
                pwd_reale = chunk.get(pwd_id, "")
                record = {"password": pwd_reale, "score": score}
                out_f.write(json.dumps(record) + "\n")
            
            # Forza la scrittura immediata
            out_f.flush()
                
            completati += 1
            print(f"Progresso: {numero_attuale}/{totale_chunks} blocchi completati.")
            # time sleep per non fare sembrare sospetto il numero elevato di richieste
            time.sleep(0.3) 

if __name__ == '__main__':
    elabora_dataset()
    print("\n[V] Valutazione completata con successo!")
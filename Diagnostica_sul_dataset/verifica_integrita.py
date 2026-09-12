# Verifica di integrità finale del dataset PII.

# Tiene conto del fatto che la lista è ordinata in modo DECRESCENTE per ricchezza
# informativa: quindi molte vuote in CODA sono normali, mentre una run lunga di
# vuote in TESTA è sospetta


import json
import sys

DATASET = 'dataset_pii_finale.jsonl'
FASCIA = 5000

def e_vuota(rec):
    #true se non ci sono campi riempiti nel record
    return not any([rec.get('n'), rec.get('c'), rec.get('dt'),
                    rec.get('az'), rec.get('ab')])


def main():
    # inserimento di tutte le stringhe senza \n e spazi in una lista
    righe = []
    with open(DATASET, encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if l:
                righe.append(json.loads(l))
    n = len(righe)

    # Verifica quante righe vuote totali sono presente
    stato = [e_vuota(r) for r in righe]
    tot_vuote = sum(stato)
    print(f"Righe vuote totali: {tot_vuote} ({100*tot_vuote/n:.1f}%)")

    # Output "grafico" della densità per fasce
    print(f"\nDensità informativa per fasce di {FASCIA} (% righe popolate):")
    for start in range(0, n, FASCIA):
        fetta = stato[start:start + FASCIA]
        popolate = sum(1 for v in fetta if not v)
        pct = 100 * popolate / len(fetta)
        barra = '#' * int(pct / 2.5)
        print(f"  {start+1:>6}-{start+len(fetta):<6}: {pct:5.1f}% {barra}")


if __name__ == '__main__':
    main()

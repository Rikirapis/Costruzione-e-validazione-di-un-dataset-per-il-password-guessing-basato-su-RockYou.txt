
# Verifica se un valore estratto è una substring della password, tollerando il
# leetspeak (es. "corey" da "C0rey", "mario" da "M4r1o", "beb" da "8e8").

# Nella LEET MAP sono presenti solo leet comuni e ragionevolmente sicure.
# Il "1" è mappato a "i" e le cifre non presenti in mappa (es. 6, 9) restano invariate
# così da non creare falsi accoppiamenti.

import re

# Mappa leet conservativa: cifra/simbolo -> lettera canonica
_LEET_MAP = {
    '0': 'o',
    '1': 'i',
    '3': 'e',
    '4': 'a',
    '5': 's',
    '7': 't',
    '8': 'b',
    '@': 'a',
    '$': 's',
}

_non_alnum = re.compile(r'[^a-z0-9@$]')
# espressione regolare per informazioni che non contengono lettere minuscole, numeri, @ e $


def _canonicalizza(s: str) -> str:
    # trasforma la stringa dall'originale a una versione tutta in minuscolo
    s = s.lower()
    s = _non_alnum.sub('', s)                 
    return ''.join(_LEET_MAP.get(ch, ch) for ch in s)


def is_substring_leet(valore: str, password: str) -> bool:
    # True se `valore` è substring di `password`, confrontando le forme senza leet di entrambe.
    if not valore:
        return True
    return _canonicalizza(valore) in _canonicalizza(password)


def marca_invenzioni(record: dict, campi=('n', 'c', 'az', 'ab')) -> list: 
    # Controlla se i campi testuali di un record sono nella sua password `p` marcando il record se possiede campi sospetti.
    p = record.get('p', '') 
    sospetti = []
    for k in campi:
        v = record.get(k, '')
        if v and not is_substring_leet(v, p):
            sospetti.append({'p': p, 'campo': k, 'valore': v})
    return sospetti
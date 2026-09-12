# CAMPIONAMENTO DI 500000 PASS: di ogni genere suddivise in pass
# 0 < pass < 16 e 15 < pass < 50 campionate poi in maniera random dalle liste
# in cui si trovavano momentaneamente
import random

# si selezionano i file di input e output (rockyou è stato prima mescolato)
input_file = 'rockyou_shuffled.txt'
output_file = 'rockyou_random_500k_bilanciato.txt'
target_total = 500000
passwords_short = []  
passwords_long = []   

def divide_archive():
    # apertura file e suddivisione in corte e lunghe
    with open(input_file, 'r', encoding='latin-1') as f:
        for line in f:
            pwd = line.strip()
            length = len(pwd)
            if 6 <= length <= 15:
                passwords_short.append(pwd)
            elif 16 <= length <= 50:
                passwords_long.append(pwd)

    # Estrazione casuale per il gruppo "corto"
    if len(passwords_short) < (target_total/2):
        #si salverebbe una parte delle password se non bastassero per il dataset scelto
        print(f"Password corte insufficienti")
        selected_short = passwords_short 
    else:
        selected_short = random.sample(passwords_short, (target_total/2))

    # Estrazione casuale per il gruppo "lungo"
    if len(passwords_long) < (target_total/2):
        print(f"Password lunghe insufficienti")
        selected_long = passwords_long
    else:
        selected_long = random.sample(passwords_long, (target_total/2))

    # Unione dei due campioni
    final_dataset = selected_short + selected_long

    # shuffle per evitare che l'LLM legga prima tutte le corte e poi tutte le lunghe per assegmare lo score
    random.shuffle(final_dataset)

    with open(output_file, 'w', encoding='utf-8') as out_f:
        for pwd in final_dataset:
            out_f.write(f"{pwd}\n") 

    print(f"Salvato con successo in {output_file}! Totale estratte: {len(final_dataset)}")

if __name__ == '__main__':
    divide_archive()
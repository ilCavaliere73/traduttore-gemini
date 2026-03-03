import os
import time
import google.generativeai as genai
from flask import Flask, render_template, request, send_file
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
if not os.path.exists('uploads'):
    os.makedirs('uploads')


# --- INIZIO CONFIGURAZIONE ROBUSTA ---
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Lista di priorità: proviamo i modelli standard, poi quelli "strani" che hai trovato
modelli_da_provare = [
    'gemini-1.5-flash',             # Il migliore standard oggi
    'gemini-1.5-pro',               # L'alternativa potente
    'gemini-pro',                   # Il vecchio standard (molto compatibile)
    'gemini-3.1-flash-lite-preview' # Quello della tua lista
]

model = None

print("--- Tentativo connessione ai modelli ---")
for nome_modello in modelli_da_provare:
    try:
        print(f"Provo a caricare: {nome_modello}...")
        test_model = genai.GenerativeModel(nome_modello)
        # Testiamo se risponde davvero
        test_model.generate_content("test")
        
        # Se siamo qui, funziona!
        model = test_model
        print(f"✅ SUCCESSO! Usiamo il modello: {nome_modello}")
        break 
    except Exception as e:
        print(f"❌ {nome_modello} non disponibile. Errore: {e}")
        continue

# Se nessuno funziona, solleviamo un errore chiaro
if model is None:
    raise ValueError("Nessun modello funzionante trovato. Controlla la tua API Key su Google AI Studio.")
# -
# -- FINE CONFIGURAZIONE ---

def dividi_testo(testo, max_chars=15000):
    """Divide il testo in blocchi ampi per Gemini"""
    pezzi = []
    while len(testo) > max_chars:
        punto_taglio = testo.rfind('.', 0, max_chars)
        if punto_taglio == -1: punto_taglio = max_chars
        pezzi.append(testo[:punto_taglio+1])
        testo = testo[punto_taglio+1:]
    pezzi.append(testo)
    return pezzi

@app.route('/', methods=['GET', 'POST'])
def index():
    traduzione_totale = ""
    testo_originale = ""
    errore = None
    pronto_per_download = False

    if request.method == 'POST':
        file = request.files.get('file_testo')
        testo_manuale = request.form.get('testo')
        lingua = request.form.get('lingua', 'italiano')
        
        if file and file.filename != '':
            testo_originale = file.read().decode('utf-8')
        else:
            testo_originale = testo_manuale

        if testo_originale:
            pezzi = dividi_testo(testo_originale)
            traduzioni_parziali = []
            
            try:
                for i, pezzo in enumerate(pezzi):
                    print(f"Traduco blocco {i+1} di {len(pezzi)}...")
                    prompt = (
                        f"Sei un traduttore accademico esperto in filologia. "
                        f"Traduci questo testo dall'INGLESE ANTICO/ARCAICO in {lingua} moderno. "
                        "Mantieni lo stile solenne e la precisione dei termini originali, "
                        "ma rendilo leggibile oggi. Testo da tradurre:\n\n" + pezzo
                    )
                    
                    response = model.generate_content(prompt)
                    traduzioni_parziali.append(response.text)
                    
                    if len(pezzi) > 1:
                        time.sleep(3) # Pausa di sicurezza per il piano free
                
                traduzione_totale = "\n\n".join(traduzioni_parziali)
                pronto_per_download = True
                
                # Salva il file per il download
                with open("uploads/traduzione.txt", "w", encoding="utf-8") as f:
                    f.write(traduzione_totale)
                    
            except Exception as e:
                traduzione_totale = "\n\n".join(traduzioni_parziali)
                errore = f"Interrotto al blocco {len(traduzioni_parziali)+1}: {str(e)}"

    return render_template('index.html', 
                           traduzione=traduzione_totale, 
                           originale=testo_originale, 
                           errore=errore, 
                           pronto_per_download=pronto_per_download)

@app.route('/download')
def download():
    return send_file("uploads/traduzione.txt", as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
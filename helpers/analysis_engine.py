import spacy
import librosa
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Carregar el model de spaCy per a català
try:
    nlp = spacy.load("ca_core_news_md")
except OSError:
    print("Model spaCy 'ca' no trobat.")
    nlp = spacy.blank("ca")

try:
    semantic_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
except Exception as e:
    print(f"⚠️ Error cargando SentenceTransformer: {e}")
    semantic_model = None

def analyze_audio_signal(file_path):
    """
    Analiza la física del audio (Independiente del idioma).
    """
    y, sr = librosa.load(file_path, sr=None)
    duration = librosa.get_duration(y=y, sr=sr)
    
    # Detectar silencios (top_db=20 es umbral de voz estándar)
    non_silent_intervals = librosa.effects.split(y, top_db=20)
    
    active_time = sum([end - start for start, end in non_silent_intervals]) / sr
    pause_time = duration - active_time
    
    phonation_ratio = active_time / duration if duration > 0 else 0
    
    return {
        "duration_total": round(duration, 2),
        "active_speech_time": round(active_time, 2),
        "pause_time": round(pause_time, 2),
        "phonation_ratio": round(phonation_ratio, 2)
    }

def analyze_linguistics(text):
    """
    Analiza la estructura gramatical en CATALÁN.
    """
    doc = nlp(text)
    
    noun_count = 0
    pronoun_count = 0
    verb_count = 0
    total_words = len(doc)
    
    sentences = list(doc.sents)
    avg_sentence_length = sum(len(s) for s in sentences) / len(sentences) if sentences else 0

    for token in doc:
        # Los códigos POS (Part Of Speech) son universales en spaCy
        if token.pos_ == "NOUN": noun_count += 1
        if token.pos_ == "PRON": pronoun_count += 1
        if token.pos_ == "VERB": verb_count += 1
        
    # Ratio Pronom/Nom (Anomia)
    p_n_ratio = pronoun_count / noun_count if noun_count > 0 else 0
    
    # Densidad de Ideas (Verbos / Total)
    idea_density = verb_count / total_words if total_words > 0 else 0

    return {
        "pronoun_noun_ratio": round(p_n_ratio, 2),
        "idea_density": round(idea_density, 2),
        "avg_sentence_length": round(avg_sentence_length, 2),
        "noun_count": noun_count,
        "pronoun_count": pronoun_count
    }

def analyze_executive_functions(full_text):
    """
    Analiza la planificación y coherencia del discurso completo.
    """
    if not semantic_model or not full_text.strip():
        return {
            "global_coherence": 0,
            "semantic_drift": 0,
            "sentence_count": 0
        }

    # 1. Separar frases usando spaCy
    doc = nlp(full_text)
    sentences = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 5]

    if len(sentences) < 2:
        return {
            "global_coherence": 1.0, # Si solo hay una frase, es 100% coherente consigo misma
            "semantic_drift": 1.0,
            "sentence_count": len(sentences)
        }

    # 2. Convertir frases a Vectores (Embeddings)
    embeddings = semantic_model.encode(sentences)

    # 3. Métrica A: COHERENCIA GLOBAL (Inicio vs Fin)
    # ¿Termina hablando de lo mismo que empezó? (Planificación a largo plazo)
    # Compara el vector de la primera frase con el de la última.
    start_end_sim = cosine_similarity([embeddings[0]], [embeddings[-1]])[0][0]

    # 4. Métrica B: DERIVA SEMÁNTICA (Semantic Drift / Local Coherence)
    # ¿Mantiene el hilo paso a paso? Calcula similitud entre frase N y N+1
    # Un valor bajo indica saltos bruscos de tema ("Fuga de ideas").
    step_similarities = []
    for i in range(len(embeddings) - 1):
        sim = cosine_similarity([embeddings[i]], [embeddings[i+1]])[0][0]
        step_similarities.append(sim)
    
    avg_local_coherence = np.mean(step_similarities) if step_similarities else 0

    return {
        "global_coherence": round(float(start_end_sim), 2),  # 1.0 = Estructura circular perfecta
        "semantic_drift": round(float(avg_local_coherence), 2), # 1.0 = Hilo conductor muy rígido, <0.3 = Caos
        "sentence_count": len(sentences)
    }
import spacy
import librosa
import numpy as np
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Versión 2.0

# Cargar modelos (Gestión de errores robusta)
try:
    nlp = spacy.load("ca_core_news_md")
except OSError:
    print("⚠️ Model spaCy 'ca' no trobat. Usant blank.")
    nlp = spacy.blank("ca")

try:
    semantic_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
except Exception as e:
    print(f"⚠️ Error cargando SentenceTransformer: {e}")
    semantic_model = None

def smart_segmentation(text, max_words=20):
    """
    Divide el flujo de consciencia en unidades de pensamiento coherentes.
    """
    if not text: return []
    
    # 1. Segmentación base por spaCy
    doc = nlp(text)
    base_sentences = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 0]
    
    final_segments = []
    
    for sent in base_sentences:
        words = sent.split()
        # Si es una frase "normal" (corta), la guardamos
        if len(words) <= max_words:
            final_segments.append(sent)
        else:
            # Si es muy larga (Whisper no puso puntos), cortamos por conectores
            # Cortamos por: puntuación, 'i', 'que', 'però', 'mentre', 'doncs'
            sub_segments = re.split(r'[,:;]|\s+(?:i|que|però|mentre|doncs|per)\s+', sent)
            
            current_chunk = []
            for sub in sub_segments:
                current_chunk.append(sub)
                # Acumulamos hasta tener una "minifrase" de al menos 8 palabras para dar contexto
                if len(" ".join(current_chunk).split()) > 8:
                    final_segments.append(" ".join(current_chunk).strip())
                    current_chunk = []
            
            if current_chunk:
                final_segments.append(" ".join(current_chunk).strip())

    # Filtro final: eliminamos fragmentos residuales muy cortos (<3 palabras)
    return [s for s in final_segments if len(s.split()) > 3]

def analyze_audio_signal(file_path):
    """Análisis físico (DSP)."""
    y, sr = librosa.load(file_path, sr=None)
    duration = librosa.get_duration(y=y, sr=sr)
    
    # Detectar silencios (top_db=25)
    non_silent_intervals = librosa.effects.split(y, top_db=25)
    
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
    """Análisis gramatical unificado con smart_segmentation."""
    doc = nlp(text)
    
    noun_count = 0
    pronoun_count = 0
    content_words_count = 0 
    
    # Totales
    total_words = len(doc)
    
    # Usamos la misma segmentación para calcular la longitud
    segments = smart_segmentation(text)
    avg_sentence_length = np.mean([len(s.split()) for s in segments]) if segments else 0

    for token in doc:
        if token.pos_ == "NOUN": noun_count += 1
        if token.pos_ == "PRON": pronoun_count += 1
        
        # Densidad Léxica Estándar (Sustantivos + Verbos + Adj + Adv)
        if token.pos_ in ["NOUN", "VERB", "ADJ", "ADV"] and not token.is_stop: 
            content_words_count += 1
        
    p_n_ratio = pronoun_count / noun_count if noun_count > 0 else 0
    
    # Densidad Léxica (Rango sano esperable: 0.40 - 0.60)
    lexical_density = content_words_count / total_words if total_words > 0 else 0

    return {
        "pronoun_noun_ratio": round(p_n_ratio, 2),
        "idea_density": round(lexical_density, 2),
        "avg_sentence_length": round(avg_sentence_length, 2),
        "noun_count": noun_count,
        "pronoun_count": pronoun_count
    }

def analyze_executive_functions(full_text):
    """Análisis semántico con Ventana Deslizante (Smoothing)."""
    if not semantic_model or not full_text.strip():
        return {"global_coherence": 0, "semantic_drift": 0, "sentence_count": 0}

    sentences = smart_segmentation(full_text, max_words=20)

    if len(sentences) < 2:
        return {"global_coherence": 1.0, "semantic_drift": 1.0, "sentence_count": len(sentences)}

    embeddings = semantic_model.encode(sentences)

    # 1. Coherencia Global (Principio vs Final)
    # Usamos promedio de las primeras/últimas 2 frases para reducir ruido
    head_n = min(2, len(embeddings))
    start_vec = np.mean(embeddings[:head_n], axis=0)
    end_vec = np.mean(embeddings[-head_n:], axis=0)
    
    start_end_sim = cosine_similarity([start_vec], [end_vec])[0][0]

    # 2. Deriva Semántica con VENTANA DESLIZANTE (Sliding Window)
    # En lugar de comparar frase 1 vs 2, comparamos el "flujo":
    # Vector A = Promedio(Frase i, Frase i+1)
    # Vector B = Promedio(Frase i+1, Frase i+2)
    # Esto suaviza los saltos bruscos por mala segmentación.
    
    if len(embeddings) > 2:
        rolling_sims = []
        for i in range(len(embeddings) - 2):
            # Ventana actual vs Ventana siguiente
            window_a = np.mean(embeddings[i : i+2], axis=0)
            window_b = np.mean(embeddings[i+1 : i+3], axis=0)
            
            sim = cosine_similarity([window_a], [window_b])[0][0]
            rolling_sims.append(sim)
        
        avg_local_coherence = np.mean(rolling_sims)
    else:
        # Fallback si hay muy pocas frases
        sim = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        avg_local_coherence = sim

    return {
        "global_coherence": round(float(start_end_sim), 2),
        "semantic_drift": round(float(avg_local_coherence), 2),
        "sentence_count": len(sentences)
    }
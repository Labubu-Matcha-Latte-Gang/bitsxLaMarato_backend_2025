import spacy
import librosa
import numpy as np
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Versio 4.0

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

def smart_segmentation(text, max_words=25):
    """
    Segmentación optimizada para Catalán conversacional.
    """
    if not text: return []
    
    doc = nlp(text)
    base_sentences = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 0]
    
    final_segments = []
    
    for sent in base_sentences:
        words = sent.split()
        if len(words) <= max_words:
            final_segments.append(sent)
        else:
            # Eliminamos 'que' y 'per' para no romper subordinadas.
            sub_segments = re.split(r'[,:;]|\s+(?:però|mentre|doncs|tampoc|encara|així)\s+', sent)
            
            current_chunk = []
            for sub in sub_segments:
                current_chunk.append(sub)
                if len(" ".join(current_chunk).split()) > 6:
                    final_segments.append(" ".join(current_chunk).strip())
                    current_chunk = []
            
            if current_chunk:
                final_segments.append(" ".join(current_chunk).strip())

    return [s for s in final_segments if len(s.split()) > 3]

def analyze_audio_signal(file_path):
    """Análisis físico (DSP)."""
    y, sr = librosa.load(file_path, sr=None)
    duration = librosa.get_duration(y=y, sr=sr)
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
    """Análisis gramatical."""
    doc = nlp(text)
    noun_count = 0
    pronoun_count = 0
    content_words_count = 0 
    total_words = len(doc)
    
    segments = smart_segmentation(text)
    avg_sentence_length = np.mean([len(s.split()) for s in segments]) if segments else 0

    for token in doc:
        if token.pos_ == "NOUN": noun_count += 1
        if token.pos_ == "PRON": pronoun_count += 1
        if token.pos_ in ["NOUN", "VERB", "ADJ", "ADV", "PROPN"] and not token.is_stop: 
            content_words_count += 1
        
    p_n_ratio = pronoun_count / noun_count if noun_count > 0 else 0
    lexical_density = content_words_count / total_words if total_words > 0 else 0

    return {
        "pronoun_noun_ratio": round(p_n_ratio, 2),
        "idea_density": round(lexical_density, 2),
        "avg_sentence_length": round(avg_sentence_length, 2),
        "noun_count": noun_count,
        "pronoun_count": pronoun_count
    }

def analyze_executive_functions(full_text):
    """
    Análisis semántico estricto para detectar incoherencias.
    """
    if not semantic_model or not full_text.strip():
        return {"global_coherence": 0, "semantic_drift": 0, "topic_adherence": 0, "sentence_count": 0}

    sentences = smart_segmentation(full_text, max_words=30) # Aumentamos un poco el contexto por frase

    if len(sentences) < 2:
        return {
            "global_coherence": 1.0, 
            "semantic_drift": 1.0, 
            "topic_adherence": 1.0,
            "sentence_count": len(sentences)
        }

    embeddings = semantic_model.encode(sentences)

    # 1. Coherencia Global (Start vs End)
    head_n = min(2, len(embeddings))
    start_vec = np.mean(embeddings[:head_n], axis=0)
    end_vec = np.mean(embeddings[-head_n:], axis=0)
    start_end_sim = cosine_similarity([start_vec], [end_vec])[0][0]

    # 2. Deriva Semántica ESTRICTA (Neighbour similarity)
    # Quitamos el suavizado. Si saltas de "Horno" a "Coche", esto debe dar bajo.
    step_similarities = []
    for i in range(len(embeddings) - 1):
        sim = cosine_similarity([embeddings[i]], [embeddings[i+1]])[0][0]
        step_similarities.append(sim)
    
    avg_local_coherence = np.mean(step_similarities) if step_similarities else 0

    # 3. Adherencia al Tópico (Topic Adherence)
    # Calculamos el "Tema Central" (promedio de todo el texto)
    topic_centroid = np.mean(embeddings, axis=0)
    
    # Medimos la distancia de cada frase al centro
    adherence_scores = cosine_similarity(embeddings, [topic_centroid])
    avg_topic_adherence = np.mean(adherence_scores)

    return {
        "global_coherence": round(float(start_end_sim), 2),
        "semantic_drift": round(float(avg_local_coherence), 2),
        "topic_adherence": round(float(avg_topic_adherence), 2), # <--- ESTA es clave para "Fuga de ideas"
        "sentence_count": len(sentences)
    }
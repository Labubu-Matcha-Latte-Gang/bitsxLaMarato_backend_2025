import os
import subprocess
import tempfile
import spacy
import librosa
import numpy as np
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from helpers.debugger.logger import AbstractLogger

# Version 6.0
logger = AbstractLogger.get_instance()

# 1. Cargar Modelos
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

def load_audio_mono_16k(file_path: str, target_sr: int = 16000):
    """
    Intenta cargar el audio de forma robusta:

    1) Primero con librosa.load(file_path, sr=target_sr, mono=True).
    2) Si falla (formato raro, contenedor corrupto, etc.), intenta
       convertir con ffmpeg a WAV mono 16 kHz en un fichero temporal
       y cargar ese fichero.
    3) Si todo falla, lanza excepción.

    Devuelve: (y, sr)
    - y: np.ndarray 1D con la señal mono
    - sr: int frecuencia de muestreo (target_sr)
    """
    # Primer intento: carga directa con librosa
    try:
        y, sr = librosa.load(file_path, sr=target_sr, mono=True)
        return y, sr
    except Exception as e:
        warn_msg = (
            f"⚠️ librosa.load ha fallat amb {file_path}: {e}. "
            f"Intentant ffmpeg -> WAV {target_sr} Hz mono."
        )
        logger.warning(warn_msg)

    # Segundo intento: ffmpeg -> WAV mono 16 kHz
    temp_wav = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            temp_wav = tmp.name

        # ffmpeg -y -i input -ac 1 -ar 16000 output.wav
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            file_path,
            "-ac",
            "1",
            "-ar",
            str(target_sr),
            temp_wav,
        ]

        completed = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        if completed.returncode != 0:
            err_msg = (
                f"⚠️ No s'ha pogut convertir/cargar l'àudio amb ffmpeg "
                f"(exit={completed.returncode}): {completed.stderr.decode(errors='ignore')}"
            )
            logger.error(err_msg)
            raise RuntimeError(err_msg)

        # Intentar de nuevo con librosa sobre el WAV temporal
        y, sr = librosa.load(temp_wav, sr=target_sr, mono=True)
        return y, sr

    finally:
        # Limpieza del WAV temporal si existe
        if temp_wav and os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
            except OSError:
                pass

def load_audio_with_fallback(file_path:str):
    """
    Intenta cargar el audio con librosa. Si falla (formato raro, webm, etc.),
    intenta convertir a WAV con ffmpeg y volver a cargar.
    """
    try:
        # Primer intento: directamente (soundfile + audioread)
        y, sr = librosa.load(file_path, sr=None)
        return y, sr
    except Exception as e:
        logger.warning(f"⚠️ librosa.load ha fallat amb {file_path}: {e}. Intentant ffmpeg -> WAV.")
    
    # Segundo intento: convertir a WAV con ffmpeg
    tmp_wav = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_wav = tmp.name

        # Conversió a mono i, per exemple, 16kHz per alleugerir càlculs
        cmd = [
            "ffmpeg",
            "-y",               # sobreescriure si existeix
            "-i", file_path,
            "-ac", "1",         # 1 canal (mono)
            "-ar", "16000",     # 16 kHz
            tmp_wav,
        ]
        # Silenciar la sortida de ffmpeg
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        y, sr = librosa.load(tmp_wav, sr=None)
        return y, sr
    except Exception as e:
        logger.error(f"⚠️ No s'ha pogut convertir/cargar l'àudio amb ffmpeg: {e}", error=e)
        # Últim recurs: llançar l'error perquè el capturi el nivell superior
        raise
    finally:
        if tmp_wav and os.path.exists(tmp_wav):
            os.remove(tmp_wav)

# 2. Segmentación Optimizada (Evita romper subordinadas con 'que')
def smart_segmentation(text, max_words=25):
    if not text:
        return []
    doc = nlp(text)
    base_sentences = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 0]
    final_segments = []

    for sent in base_sentences:
        words = sent.split()
        if len(words) <= max_words:
            final_segments.append(sent)
        else:
            # Cortamos solo en pausas fuertes, ignorando 'que'/'per'
            sub_segments = re.split(
                r"[,:;]|\s+(?:però|mentre|doncs|tampoc|encara|així|i)\s+",
                sent,
            )
            current_chunk = []
            for sub in sub_segments:
                current_chunk.append(sub)
                if len(" ".join(current_chunk).split()) > 6:
                    final_segments.append(" ".join(current_chunk).strip())
                    current_chunk = []
            if current_chunk:
                final_segments.append(" ".join(current_chunk).strip())

    return [s for s in final_segments if len(s.split()) > 3]

# 3. Análisis de Señal (DSP)
def analyze_audio_signal(file_path: str):
    """
    Calculates basic acoustic metrics:
      - total duration
      - active speech time
      - pause time
      - phonation ratio

    If audio loading fails, logs the error and returns
    a dictionary with all metrics set to 0, to avoid breaking
    the transcription request.
    """
    try:
        y, sr = load_audio_mono_16k(file_path, target_sr=16000)
        # Seguridad extra: si por lo que sea y está vacío:
        if y is None or len(y) == 0:
            raise ValueError("Señal de audio vacía tras la carga")

        duration = librosa.get_duration(y=y, sr=sr)
        non_silent_intervals = librosa.effects.split(y, top_db=25)
        active_time = sum((end - start) for start, end in non_silent_intervals) / sr
        pause_time = duration - active_time
        phonation_ratio = active_time / duration if duration > 0 else 0.0

        return {
            "duration_total": round(float(duration), 2),
            "active_speech_time": round(float(active_time), 2),
            "pause_time": round(float(pause_time), 2),
            "phonation_ratio": round(float(phonation_ratio), 2),
        }

    except Exception as e:
        msg = f"Error analitzant el senyal d'àudio ({file_path}): {e}"
        print(msg)
        logger.error(msg)
        # Devolvemos métricas neutras para no trencar la transcripció
        return {
            "duration_total": 0.0,
            "active_speech_time": 0.0,
            "pause_time": 0.0,
            "phonation_ratio": 0.0,
        }

# 4. Análisis Lingüístico (Gramática + Nombres Propios)
def analyze_linguistics(text):
    doc = nlp(text)
    noun_count = 0
    pronoun_count = 0
    content_words_count = 0
    total_words = len(doc)

    segments = smart_segmentation(text)
    avg_sentence_length = np.mean([len(s.split()) for s in segments]) if segments else 0

    for token in doc:
        if token.pos_ == "NOUN":
            noun_count += 1
        if token.pos_ == "PRON":
            pronoun_count += 1
        if token.pos_ in ["NOUN", "VERB", "ADJ", "ADV", "PROPN"] and not token.is_stop:
            content_words_count += 1

    p_n_ratio = pronoun_count / noun_count if noun_count > 0 else 0
    lexical_density = content_words_count / total_words if total_words > 0 else 0

    return {
        "pronoun_noun_ratio": round(float(p_n_ratio), 2),
        "idea_density": round(float(lexical_density), 2),
        "avg_sentence_length": round(float(avg_sentence_length), 2),
        "noun_count": int(noun_count),
        "pronoun_count": int(pronoun_count),
    }

# 5. Análisis Ejecutivo (Semántica con Suavizado)
def analyze_executive_functions(full_text):
    if not semantic_model or not full_text or not full_text.strip():
        return {
            "global_coherence": 0.0,
            "semantic_drift": 0.0,
            "topic_adherence": 0.0,
            "sentence_count": 0,
        }

    sentences = smart_segmentation(full_text, max_words=30)
    if len(sentences) < 2:
        # Texto demasiado corto como para medir deriva coherentemente
        return {
            "global_coherence": 1.0,
            "semantic_drift": 1.0,
            "topic_adherence": 1.0,
            "sentence_count": len(sentences),
        }

    embeddings = semantic_model.encode(sentences)

    # A. Coherencia Global (Principio vs Final)
    head_n = min(2, len(embeddings))
    start_vec = np.mean(embeddings[:head_n], axis=0)
    end_vec = np.mean(embeddings[-head_n:], axis=0)
    start_end_sim = cosine_similarity([start_vec], [end_vec])[0][0]

    # B. Deriva Semántica SUAVIZADA (Ventana Deslizante)
    rolling_sims = []
    if len(embeddings) > 2:
        for i in range(len(embeddings) - 2):
            vec_a = np.mean(embeddings[i : i + 2], axis=0)
            vec_b = np.mean(embeddings[i + 1 : i + 3], axis=0)
            sim = cosine_similarity([vec_a], [vec_b])[0][0]
            rolling_sims.append(sim)
        avg_drift = np.mean(rolling_sims)
    else:
        avg_drift = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]

    # C. Adherencia al Tópico (Distancia al Centroide)
    topic_centroid = np.mean(embeddings, axis=0)
    adherence_scores = cosine_similarity(embeddings, [topic_centroid])
    avg_topic_adherence = np.mean(adherence_scores)

    return {
        "global_coherence": round(float(start_end_sim), 2),
        "semantic_drift": round(float(avg_drift), 2),
        "topic_adherence": round(float(avg_topic_adherence), 2),
        "sentence_count": len(sentences),
    }
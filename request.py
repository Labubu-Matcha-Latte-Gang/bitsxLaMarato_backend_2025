import requests
import uuid
import os
import json

# --- CONFIGURACIÓN ---
BASE_URL = "http://localhost:5000/api/v1"  # Ajusta si tu prefijo no es /api
EMAIL = "admin@admin.com"                # Un usuario que ya exista en tu DB
PASSWORD = "0vhsQ80'Is[d"                 # Contraseña válida
AUDIO_FILE = "test_audio.mp3"             # ARCHIVO QUE DEBES TENER EN LA CARPETA
# ---------------------

def main():
    print(f"--- Probando API en: {BASE_URL} ---")

    # 1. LOGIN (Para obtener el Token)
    print("\n1. Iniciando sesión...")
    login_url = f"{BASE_URL}/user/login"
    try:
        response = requests.post(login_url, json={"email": EMAIL, "password": PASSWORD})
        
        if response.status_code != 200:
            print(f"❌ Error Login: {response.text}")
            return
            
        token = response.json().get("access_token")
        print("✅ Login correcto. Token recibido.")
        
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return

    # Preparar cabeceras con el token
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Generar un ID de sesión único (simulando una nueva grabación)
    session_id = str(uuid.uuid4())
    print(f"\n--- Sesión de grabación: {session_id} ---")

    # 2. ENVIAR UN CHUNK (FRAGMENTO)
    # En un caso real, esto estaría en un bucle enviando trozos cada 30s.
    # Aquí enviamos el archivo entero como el "chunk 0" para probar.
    print(f"\n2. Enviando fragmento de audio (Chunk 0)...")
    
    if not os.path.exists(AUDIO_FILE):
        print(f"❌ Error: No encuentro el archivo '{AUDIO_FILE}' para la prueba.")
        return

    chunk_url = f"{BASE_URL}/transcription/chunk"
    
    # Multipart/form-data: enviamos datos y archivo
    with open(AUDIO_FILE, 'rb') as f:
        files = {
            'audio_blob': (os.path.basename(AUDIO_FILE), f, 'audio/mpeg') # Ajusta MIME si usas wav/webm
        }
        data = {
            'session_id': session_id,
            'chunk_index': 0
        }
        
        response = requests.post(chunk_url, headers=auth_headers, files=files, data=data)
        
        if response.status_code == 200:
            print(f"✅ Chunk procesado. Transcripción parcial: {response.json().get('partial_text')}")
        else:
            print(f"❌ Error subiendo chunk: {response.text}")
            return

    # 3. FINALIZAR (COMPLETE)
    # Esto une todos los trozos y nos da el resultado final
    print("\n3. Finalizando sesión...")
    complete_url = f"{BASE_URL}/transcription/complete"
    
    json_data = {"session_id": session_id}
    
    response = requests.post(complete_url, headers=auth_headers, json=json_data)
    
    if response.status_code == 200:
        result = response.json()
        print("\n🎉 ¡ÉXITO! Transcripción completa:")
        print("------------------------------------------------")
        print(result.get("transcription"))
        print("------------------------------------------------")
    else:
        print(f"❌ Error finalizando: {response.text}")

if __name__ == "__main__":
    main()
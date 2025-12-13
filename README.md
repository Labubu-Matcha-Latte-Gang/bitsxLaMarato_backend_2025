<div align="center">
  <img src="assets/logo-text-blau.png" alt="logo" width="200" height="auto" />
  <h1>bitsxLaMarató 2025 - Backend</h1>
  
  <p>
    Backend de l'aplicació per a la gestió de pacients i activitats, desenvolupat per a l'esdeveniment BitsxLaMarató 2025.
  </p>
  
  <h4>
    <a href="https://github.com/Labubu-Matcha-Latte-Gang/bitsxLaMarato_backend_2025/issues/">Informar d'un error</a>
    <span> · </span>
    <a href="https://github.com/Labubu-Matcha-Latte-Gang/bitsxLaMarato_backend_2025/issues/">Sol·licitar una funcionalitat</a>
    <span> · </span>
    <a href="https://github.com/Labubu-Matcha-Latte-Gang/bitsxLaMarato_backend_2025/pulls">Contribuir</a>
  </h4>
</div>

<br />

## Sobre el Projecte

Aquest repositori conté el codi font del servei de backend per a l'aplicació de **bitsxLaMarató 2025**. L'objectiu principal és proporcionar una API REST per gestionar les dades de pacients, metges, activitats, recomanacions i altres funcionalitats relacionades amb el seguiment de la salut en el context de La Marató de TV3.

L'arquitectura del projecte segueix principis de disseny net (Clean Architecture) per garantir una alta mantenibilitat, escalabilitat i testeabilitat.

### Tecnologies principals

*   **Python 3.11+**
*   **Flask**: Framework principal per a la construcció de l'API REST.
*   **SQLAlchemy**: ORM per a la interacció amb la base de dades.
*   **Alembic**: Eina per a la gestió de migracions de la base de dades.
*   **Pytest**: Framework per a la realització de tests unitaris i d'integració.
*   **Docker**: Per a la containerització de l'aplicació i els seus serveis.

## Com començar

Per poder executar el projecte en un entorn de desenvolupament local, segueix els passos següents.

### Prerequisits

Assegura't de tenir instal·lat el següent programari:
*   Python 3.11 o superior
*   Docker i Docker Compose

### Instal·lació

1.  **Clona el repositori**
    ```bash
    git clone https://github.com/Labubu-Matcha-Latte-Gang/bitsxLaMarato_backend_2025.git
    cd bitsxLaMarato_backend_2025
    ```

2.  **Crea i activa un entorn virtual**
    ```bash
    python -m venv venv
    # A Windows
    .\venv\Scripts\activate
    # A macOS/Linux
    source venv/bin/activate
    ```

3.  **Instal·la les dependències**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuració de l'entorn**
    Crea un fitxer `.env` a l'arrel del projecte copiant `.env.example` i ajusta les variables d'entorn segons les teves necessitats (configuració de la base de dades, claus secretes, etc.).

## Ús

### Execució amb Docker (Recomanat)

La manera més senzilla d'executar l'aplicació i tots els serveis necessaris (com la base de dades) és a través de Docker Compose.

```bash
docker-compose up --build
```

L'API estarà disponible a `http://localhost:5000`.

### Execució local

Si prefereixes executar l'aplicació directament a la teva màquina:

1.  Assegura't que tens una instància de PostgreSQL en funcionament i que les credencials coincideixen amb les del teu fitxer `.env`.

2.  Aplica les migracions de la base de dades:
    ```bash
    alembic upgrade head
    ```

3.  Executa l'aplicació Flask:
    ```bash
    flask run
    ```

## Tests

Per executar la suite de tests, utilitza `pytest`:

```bash
pytest
```

Això executarà tots els tests definits al directori `tests/`.

## Documentació de l'API

Un cop l'aplicació estigui en marxa, pots accedir a la documentació interactiva de l'API (Swagger UI) a través de l'endpoint `/api/docs`:

[http://localhost:5000/api/docs](http://localhost:5000/api/docs)

## Llicència

Distribuït sota la Llicència MIT. Consulta el fitxer `LICENSE` per a més informació.

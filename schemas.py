from marshmallow import Schema, fields, validate
from helpers.enums.gender import Gender
from helpers.enums.question_types import QuestionType

GENDER_VALUES = [gender.value for gender in Gender]
GENDER_DESCRIPTION = f"Gènere del pacient. Valors acceptats: {', '.join(GENDER_VALUES)}."
QUESTION_TYPE_VALUES = [question_type.value for question_type in QuestionType]
QUESTION_TYPE_DESCRIPTION = f"Tipus de pregunta. Valors acceptats: {', '.join(QUESTION_TYPE_VALUES)}."
ACTIVITY_TYPE_DESCRIPTION = f"Tipus d'activitat. Valors acceptats: {', '.join(QUESTION_TYPE_VALUES)}."

password_complexity = validate.Regexp(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$",
    error="La contrasenya ha de contenir almenys una lletra majúscula, una minúscula, un número i tenir un mínim de 8 caràcters.",
)


class SwaggerDocQuerySchema(Schema):
    """
    Paràmetres per descarregar la documentació de l'API.
    """

    class Meta:
        description = "Selecciona el format de descàrrega de la documentació."
        example = {"format": "pdf"}

    format = fields.String(
        load_default="html",
        validate=validate.OneOf(["html", "pdf"]),
        metadata={
            "description": "Format del document a descarregar (html o pdf).",
            "example": "html",
        },
    )


class PatientEmailPathSchema(Schema):
    """
    Esquema per recuperar dades d'un pacient a partir del correu a la ruta.
    """

    class Meta:
        description = "Paràmetres de ruta per consultar un pacient pel seu correu electrònic."
        example = {"email": "pacient@example.com"}

    email = fields.Email(
        required=True,
        metadata={
            "description": "Correu electrònic del pacient per recuperar les seves dades.",
            "example": "pacient@example.com",
        },
    )


class UserResponseSchema(Schema):
    """
    Esquema de resposta d'usuari (inclou dades específiques del rol quan existeixen).
    """

    class Meta:
        description = "Payload retornat per operacions d'usuari amb informació del rol."
        example = {
            "email": "jane.doe@example.com",
            "name": "Jane",
            "surname": "Doe",
            "role": {
                "ailments": "Hipertensió lleu",
                "gender": "female",
                "age": 42,
                "treatments": "Control dietètic",
                "height_cm": 168.5,
                "weight_kg": 64.3,
                "doctors": ["dr.house@example.com"],
            },
        }

    email = fields.Email(
        required=True,
        metadata={
            "description": "Correu electrònic de l'usuari.",
            "example": "jane.doe@example.com",
        },
    )
    name = fields.String(
        required=True,
        metadata={
            "description": "Nom de l'usuari.",
            "example": "Jane",
        },
    )
    surname = fields.String(
        required=True,
        metadata={
            "description": "Cognoms de l'usuari.",
            "example": "Doe",
        },
    )
    role = fields.Dict(
        required=False,
        metadata={
            "description": (
                "Dades específiques del rol. Per als pacients: ailments, gender, age, treatments, "
                "height_cm, weight_kg, doctors (correus). Per als metges: patients (correus). "
                "Per als administradors: objecte buit."
            ),
            "example": {
                "ailments": "Hipertensió lleu",
                "gender": "female",
                "age": 42,
                "treatments": "Control dietètic",
                "height_cm": 168.5,
                "weight_kg": 64.3,
                "doctors": ["dr.house@example.com"],
            },
        },
    )


class ScoreSummarySchema(Schema):
    """
    Resum de puntuacions d'activitats d'un pacient.
    """

    class Meta:
        description = "Puntuacions realitzades pel pacient amb informació de l'activitat."
        example = {
            "activity_id": "6f37f5b4-1c2d-4f3e-9a0b-123456789abc",
            "activity_title": "Memòria curta",
            "activity_type": "memory",
            "completed_at": "2024-01-15T10:30:00",
            "score": 8.5,
            "seconds_to_finish": 120.0,
        }

    activity_id = fields.String(
        required=True,
        metadata={
            "description": "Identificador de l'activitat.",
            "example": "6f37f5b4-1c2d-4f3e-9a0b-123456789abc",
        },
    )
    activity_title = fields.String(
        required=True,
        metadata={
            "description": "Títol de l'activitat realitzada.",
            "example": "Memòria curta",
        },
    )
    activity_type = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "description": "Tipus d'activitat (valor enum) o null si no hi ha tipus.",
            "example": "memory",
        },
    )
    completed_at = fields.String(
        required=True,
        metadata={
            "description": "Data de finalització en format ISO 8601.",
            "example": "2024-01-15T10:30:00",
        },
    )
    score = fields.Float(
        required=True,
        metadata={
            "description": "Puntuació obtinguda.",
            "example": 8.5,
        },
    )
    seconds_to_finish = fields.Float(
        required=True,
        metadata={
            "description": "Segons necessaris per completar l'activitat.",
            "example": 120.0,
        },
    )


class QuestionAnswerWithAnalysisSchema(Schema):
    """
    Pregunta contestada amb metadades d'anàlisi.
    """

    class Meta:
        description = "Resposta a preguntes amb mètriques analitzades sobre el text."
        example = {
            "question": {
                "id": "7e9c5a2c-1234-4b1f-9a77-111122223333",
                "text": "Quants dies té una setmana?",
                "question_type": "concentration",
                "difficulty": 1.0,
            },
            "answered_at": "2024-01-20T09:15:00",
            "analysis": {
                "pronoun_noun_ratio": 0.4,
                "idea_density": 0.6,
            },
        }

    question = fields.Nested(
        "QuestionResponseSchema",
        required=True,
        metadata={
            "description": "Pregunta contestada amb les seves dades bàsiques.",
        },
    )
    answered_at = fields.String(
        required=True,
        metadata={
            "description": "Data en què es va contestar la pregunta.",
            "example": "2024-01-20T09:15:00",
        },
    )
    analysis = fields.Dict(
        keys=fields.String(),
        values=fields.Float(),
        required=True,
        metadata={
            "description": "Mètriques derivades del text (coherència, densitat lèxica, etc.).",
            "example": {"pronoun_noun_ratio": 0.4, "idea_density": 0.6},
        },
    )


class GraphFileSchema(Schema):
    """
    Fitxer de gràfic generat per al pacient.
    """

    class Meta:
        description = "Fitxers HTML dels gràfics codificats en base64."
        example = {
            "filename": "scores_memory.html",
            "content_type": "text/html",
            "content": "PGh0bWw+PC9odG1sPg==",
        }

    filename = fields.String(
        required=True,
        metadata={
            "description": "Nom del fitxer generat (per exemple, un id de gràfic).",
            "example": "scores_memory.html",
        },
    )
    content_type = fields.String(
        required=True,
        metadata={
            "description": "Tipus MIME del fitxer (sempre text/html).",
            "example": "text/html",
        },
    )
    content = fields.String(
        required=True,
        metadata={
            "description": "Fragment HTML (div + script Plotly) codificat en base64, pensat per injectar-se en un iframe via `srcdoc` o en un contenidor que executi scripts.",
            "description": "Fragment HTML (div + script Plotly) codificat en base64; en Flutter es pot decodificar i passar a una WebView (p. ex. `controller.loadHtmlString(fragment)`).",
            "example": "PGRpdiBpZD0icGxvdF9leGFtcGxlIj48L2Rpdj48c2NyaXB0Pi8qIHBsb3QgKi88L3NjcmlwdD4=",
        },
    )


class PatientDataResponseSchema(Schema):
    """
    Resposta completa amb dades del pacient, puntuacions, preguntes i gràfics.
    """

    class Meta:
        description = "Dades enriquides del pacient amb les puntuacions, preguntes i fitxers de gràfics."
        example = {
            "patient": UserResponseSchema.Meta.example,
            "scores": [ScoreSummarySchema.Meta.example],
            "questions": [QuestionAnswerWithAnalysisSchema.Meta.example],
            "graph_files": [GraphFileSchema.Meta.example],
        }

    patient = fields.Nested(
        UserResponseSchema,
        required=True,
        metadata={
            "description": "Informació bàsica del pacient amb el seu rol.",
        },
    )
    scores = fields.List(
        fields.Nested(ScoreSummarySchema),
        required=True,
        metadata={
            "description": "Puntuacions d'activitats del pacient (pot ser una llista buida).",
        },
    )
    questions = fields.List(
        fields.Nested(QuestionAnswerWithAnalysisSchema),
        required=True,
        metadata={
            "description": "Preguntes contestades amb mètriques d'anàlisi (pot ser buit).",
        },
    )
    graph_files = fields.List(
        fields.Nested(GraphFileSchema),
        required=True,
        metadata={
            "description": "Fragments HTML (div + script) dels gràfics codificats en base64 (pot ser buit).",
        },
    )


class UserUpdateSchema(Schema):
    """
    Esquema per a actualitzacions completes de l'usuari (PUT).
    """

    class Meta:
        description = "Cos complet per reemplaçar les dades de l'usuari autenticat."
        example = {
            "name": "Laura",
            "surname": "Serra",
            "password": "Segura123",
            "ailments": "Diabetis tipus 2",
            "gender": "female",
            "age": 36,
            "treatments": "Dieta baixa en sucre",
            "height_cm": 170.2,
            "weight_kg": 65.5,
            "doctors": ["metge1@example.com", "metge2@example.com"],
            "patients": ["pacient@example.com"],
        }

    name = fields.String(
        required=True,
        validate=validate.Length(max=80),
        metadata={
            "description": "Nom actualitzat de l'usuari.",
            "example": "Laura",
        },
    )
    surname = fields.String(
        required=True,
        validate=validate.Length(max=80),
        metadata={
            "description": "Cognoms actualitzats de l'usuari.",
            "example": "Serra",
        },
    )
    password = fields.String(
        required=False,
        load_only=True,
        validate=password_complexity,
        metadata={
            "description": "Nova contrasenya per a l'usuari.",
            "example": "Segura123",
        },
    )
    ailments = fields.String(
        required=False,
        allow_none=True,
        validate=lambda s: len(s) <= 2048,
        metadata={
            "description": "Patologies o malalties del pacient.",
            "example": "Diabetis tipus 2",
        },
    )
    gender = fields.Enum(
        Gender,
        required=False,
        by_value=True,
        metadata={
            "description": GENDER_DESCRIPTION,
            "enum": GENDER_VALUES,
            "example": "female",
        },
    )
    age = fields.Integer(
        required=False,
        allow_none=False,
        metadata={
            "description": "Edat del pacient.",
            "example": 36,
        },
    )
    treatments = fields.String(
        required=False,
        allow_none=True,
        validate=lambda s: len(s) <= 2048,
        metadata={
            "description": "Tractaments del pacient.",
            "example": "Dieta baixa en sucre",
        },
    )
    height_cm = fields.Float(
        required=False,
        allow_none=False,
        metadata={
            "description": "Alçada del pacient en centímetres.",
            "example": 170.2,
        },
    )
    weight_kg = fields.Float(
        required=False,
        allow_none=False,
        metadata={
            "description": "Pes del pacient en quilograms.",
            "example": 65.5,
        },
    )
    doctors = fields.List(
        fields.Email(),
        required=False,
        metadata={
            "description": "Llista de correus dels metges associats al pacient.",
            "example": ["metge1@example.com", "metge2@example.com"],
        },
    )
    patients = fields.List(
        fields.Email(),
        required=False,
        metadata={
            "description": "Llista de correus dels pacients associats al metge.",
            "example": ["pacient@example.com"],
        },
    )


class UserPartialUpdateSchema(Schema):
    """
    Esquema per a actualitzacions parcials de l'usuari (PATCH).
    """

    class Meta:
        description = "Cos parcial per modificar camps concrets de l'usuari autenticat."
        example = {
            "surname": "Ribas",
            "treatments": "Fisioteràpia setmanal",
            "height_cm": 172.0,
        }

    name = fields.String(
        required=False,
        validate=validate.Length(max=80),
        metadata={
            "description": "Nom actualitzat de l'usuari.",
            "example": "Marc",
        },
    )
    surname = fields.String(
        required=False,
        validate=validate.Length(max=80),
        metadata={
            "description": "Cognoms actualitzats de l'usuari.",
            "example": "Ribas",
        },
    )
    password = fields.String(
        required=False,
        load_only=True,
        validate=password_complexity,
        metadata={
            "description": "Nova contrasenya per a l'usuari.",
            "example": "ContrasenyaNova1",
        },
    )
    ailments = fields.String(
        required=False,
        allow_none=True,
        validate=lambda s: len(s) <= 2048,
        metadata={
            "description": "Patologies o malalties del pacient.",
            "example": "Migranya crònica",
        },
    )
    gender = fields.Enum(
        Gender,
        required=False,
        by_value=True,
        metadata={
            "description": GENDER_DESCRIPTION,
            "enum": GENDER_VALUES,
            "example": "male",
        },
    )
    age = fields.Integer(
        required=False,
        allow_none=False,
        metadata={
            "description": "Edat del pacient.",
            "example": 48,
        },
    )
    treatments = fields.String(
        required=False,
        allow_none=True,
        validate=lambda s: len(s) <= 2048,
        metadata={
            "description": "Tractaments del pacient.",
            "example": "Fisioteràpia setmanal",
        },
    )
    height_cm = fields.Float(
        required=False,
        allow_none=False,
        metadata={
            "description": "Alçada del pacient en centímetres.",
            "example": 172.0,
        },
    )
    weight_kg = fields.Float(
        required=False,
        allow_none=False,
        metadata={
            "description": "Pes del pacient en quilograms.",
            "example": 72.4,
        },
    )
    doctors = fields.List(
        fields.Email(),
        required=False,
        metadata={
            "description": "Llista de correus dels metges associats al pacient.",
            "example": ["metge3@example.com"],
        },
    )
    patients = fields.List(
        fields.Email(),
        required=False,
        metadata={
            "description": "Llista de correus dels pacients associats al metge.",
            "example": ["pacient1@example.com", "pacient2@example.com"],
        },
    )


class UserRegisterSchema(Schema):
    """
    Esquema per a les dades de registre d'un usuari.
    """

    class Meta:
        description = "Cos base per registrar un usuari amb credencials i dades personals."
        example = {
            "name": "Clara",
            "surname": "Puig",
            "email": "clara.puig@example.com",
            "password": "ClaraSegura1",
        }

    name = fields.String(
        required=True,
        validate=validate.Length(max=80),
        metadata={
            "description": "Nom de l'usuari.",
            "example": "Clara",
        },
    )
    surname = fields.String(
        required=True,
        validate=validate.Length(max=80),
        metadata={
            "description": "Cognoms de l'usuari.",
            "example": "Puig",
        },
    )
    email = fields.Email(
        required=True,
        metadata={
            "description": "Adreça de correu de l'usuari.",
            "example": "clara.puig@example.com",
        },
    )
    password = fields.String(
        required=True,
        load_only=True,
        validate=password_complexity,
        metadata={
            "description": "Contrasenya de l'usuari.",
            "example": "ClaraSegura1",
        },
    )


class PatientRegisterSchema(UserRegisterSchema):
    """
    Esquema per al registre de pacients.
    """

    class Meta:
        description = "Cos complet per registrar un pacient amb metadades mèdiques i associacions."
        example = {
            "name": "Pau",
            "surname": "Casals",
            "email": "pau.casals@example.com",
            "password": "PauSalut1",
            "ailments": "Asma",
            "gender": "male",
            "age": 28,
            "treatments": "Inhalador diari",
            "height_cm": 180.0,
            "weight_kg": 78.2,
            "doctors": ["doctor@example.com"],
        }

    ailments = fields.String(
        required=False,
        allow_none=True,
        validate=lambda s: len(s) <= 2048,
        metadata={
            "description": "Malalties o afeccions del pacient.",
            "example": "Asma",
        },
    )
    gender = fields.Enum(
        Gender,
        required=True,
        by_value=True,
        metadata={
            "description": f"Gènere del pacient. Valors acceptats: {', '.join(GENDER_VALUES)}.",
            "enum": GENDER_VALUES,
            "example": "male",
        },
    )
    age = fields.Integer(
        required=True,
        allow_none=False,
        metadata={
            "description": "Edat del pacient.",
            "example": 28,
        },
    )
    treatments = fields.String(
        required=False,
        allow_none=True,
        validate=lambda s: len(s) <= 2048,
        metadata={
            "description": "Tractaments actuals del pacient.",
            "example": "Inhalador diari",
        },
    )
    height_cm = fields.Float(
        required=True,
        allow_none=False,
        metadata={
            "description": "Alçada del pacient en centímetres.",
            "example": 180.0,
        },
    )
    weight_kg = fields.Float(
        required=True,
        allow_none=False,
        metadata={
            "description": "Pes del pacient en quilograms.",
            "example": 78.2,
        },
    )
    doctors = fields.List(
        fields.Email(),
        required=False,
        metadata={
            "description": "Llista de correus de metges associats al pacient.",
            "example": ["doctor@example.com"],
        },
    )


class DoctorRegisterSchema(UserRegisterSchema):
    """
    Esquema per al registre de metges.
    """

    class Meta:
        description = "Cos complet per registrar un metge i associar-hi pacients."
        example = {
            "name": "Anna",
            "surname": "Font",
            "email": "anna.font@example.com",
            "password": "AnnaMetge1",
            "patients": ["pacient1@example.com", "pacient2@example.com"],
        }

    patients = fields.List(
        fields.Email(),
        required=False,
        metadata={
            "description": "Llista de correus dels pacients associats al metge.",
            "example": ["pacient1@example.com", "pacient2@example.com"],
        },
    )


class UserLoginSchema(Schema):
    """
    Esquema per a les credencials d'inici de sessió.
    """

    class Meta:
        description = "Cos per autenticar un usuari amb correu i contrasenya."
        example = {
            "email": "clara.puig@example.com",
            "password": "ClaraSegura1",
        }

    email = fields.Email(
        required=True,
        metadata={
            "description": "Correu electrònic de l'usuari.",
            "example": "clara.puig@example.com",
        },
    )
    password = fields.String(
        required=True,
        load_only=True,
        metadata={
            "description": "Contrasenya de l'usuari.",
            "example": "ClaraSegura1",
        },
    )


class UserLoginResponseSchema(Schema):
    """
    Esquema per a la resposta d'inici de sessió.
    """

    class Meta:
        description = "Resposta d'autenticació amb el token JWT."
        example = {"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}

    access_token = fields.String(
        required=True,
        metadata={
            "description": "Token d'autenticació per a l'usuari.",
            "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        },
    )


class UserRegisterResponseSchema(UserResponseSchema):
    """
    Esquema de resposta per al registre d'usuaris amb token d'accés.
    """

    class Meta:
        description = "Usuari creat correctament amb el token JWT per iniciar sessió."
        example = {
            "email": "jane.doe@example.com",
            "name": "Jane",
            "surname": "Doe",
            "role": {
                "ailments": "Hipertensió lleu",
                "gender": "female",
                "age": 42,
                "treatments": "Control dietètic",
                "height_cm": 168.5,
                "weight_kg": 64.3,
                "doctors": ["dr.house@example.com"],
            },
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        }

    access_token = fields.String(
        required=True,
        metadata={
            "description": "Token JWT que permet autenticar les peticions del nou usuari.",
            "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        },
    )


class UserForgotPasswordSchema(Schema):
    """
    Esquema per a la sol·licitud de recuperar contrasenya.
    """

    class Meta:
        description = "Cos per demanar l'enviament del codi de restabliment de contrasenya."
        example = {"email": "clara.puig@example.com"}

    email = fields.Email(
        required=True,
        metadata={
            "description": "Correu electrònic de l'usuari que demana restablir la contrasenya.",
            "example": "clara.puig@example.com",
        },
    )


class UserForgotPasswordResponseSchema(Schema):
    """
    Esquema per a la resposta de sol·licitud de restabliment.
    """

    class Meta:
        description = "Resposta que indica l'estat de l'enviament del codi i la seva validesa."
        example = {
            "message": "El correu de restabliment s'ha enviat correctament.",
            "validity": 5,
        }

    message = fields.String(
        required=True,
        metadata={
            "description": "Missatge de resposta que indica el resultat de la sol·licitud.",
            "example": "El correu de restabliment s'ha enviat correctament.",
        },
    )
    validity = fields.Float(
        required=True,
        metadata={
            "description": "Durada de validesa del codi de restabliment en minuts.",
            "example": 5,
        },
    )


class UserResetPasswordSchema(Schema):
    """
    Esquema per al restabliment de contrasenya.
    """

    class Meta:
        description = "Cos per validar el codi de restabliment i establir una nova contrasenya."
        example = {
            "email": "clara.puig@example.com",
            "reset_code": "AB12CD34",
            "new_password": "NovaContrasenya1",
        }

    email = fields.Email(
        required=True,
        metadata={
            "description": "Correu electrònic de l'usuari que restableix la contrasenya.",
            "example": "clara.puig@example.com",
        },
    )
    reset_code = fields.String(
        required=True,
        metadata={
            "description": "Codi de restabliment proporcionat a l'usuari.",
            "example": "AB12CD34",
        },
    )
    new_password = fields.String(
        required=True,
        load_only=True,
        validate=password_complexity,
        metadata={
            "description": "Nova contrasenya per a l'usuari.",
            "example": "NovaContrasenya1",
        },
    )


class UserResetPasswordResponseSchema(Schema):
    """
    Esquema per a la resposta de restabliment de contrasenya.
    """

    class Meta:
        description = "Resposta que confirma que la contrasenya s'ha restablert."
        example = {"message": "Contrasenya restablerta correctament."}

    message = fields.String(
        required=True,
        metadata={
            "description": "Missatge de resultat de l'operació de restabliment.",
            "example": "Contrasenya restablerta correctament.",
        },
    )


class TranscriptionChunkSchema(Schema):
    """
    Esquema per pujar un fragment d'àudio.
    """

    class Meta:
        description = "Paràmetres per enviar un fragment d'àudio d'una sessió de transcripció."
        example = {"session_id": "sessio-123", "chunk_index": 1}

    session_id = fields.String(
        required=True,
        metadata={
            "description": "Identificador únic de la sessió d'enregistrament.",
            "example": "sessio-123",
        },
    )
    chunk_index = fields.Integer(
        required=True,
        metadata={
            "description": "Índex seqüencial del fragment.",
            "example": 1,
        },
    )


class TranscriptionCompleteSchema(Schema):
    """
    Esquema per finalitzar la sessió de transcripció.
    """

    class Meta:
        description = "Paràmetres per tancar una sessió i combinar tots els fragments."
        example = {"session_id": "sessio-123"}

    session_id = fields.String(
        required=True,
        metadata={
            "description": "Identificador únic de la sessió d'enregistrament a finalitzar.",
            "example": "sessio-123",
        },
    )


class TranscriptionResponseSchema(Schema):
    """
    Esquema per a la resposta final de transcripció.
    """

    class Meta:
        description = "Resposta amb l'estat i el text transcrit complet."
        example = {
            "status": "completed",
            "transcription": "Bon dia, aquesta és la transcripció completa de la sessió.",
        }

    status = fields.String(
        required=True,
        metadata={
            "description": "Estat de l'operació.",
            "example": "completed",
        },
    )
    transcription = fields.String(
        required=True,
        metadata={
            "description": "Text combinat complet de la transcripció.",
            "example": "Bon dia, aquesta és la transcripció completa de la sessió.",
        },
    )


class QuestionBaseSchema(Schema):
    """
    Esquema base per als camps de pregunta.
    """

    class Meta:
        description = "Camps comuns per definir una pregunta."
        example = {
            "text": "Quin nombre ve després del 7?",
            "question_type": "concentration",
            "difficulty": 2.5,
        }

    text = fields.String(
        required=True,
        validate=validate.Length(min=1),
        metadata={
            "description": "Enunciat o text de la pregunta.",
            "example": "Quin nombre ve després del 7?",
        },
    )
    question_type = fields.Enum(
        QuestionType,
        required=True,
        by_value=True,
        metadata={
            "description": QUESTION_TYPE_DESCRIPTION,
            "enum": QUESTION_TYPE_VALUES,
            "example": "concentration",
        },
    )
    difficulty = fields.Float(
        required=True,
        validate=validate.Range(min=0, max=5),
        metadata={
            "description": "Puntuació de dificultat entre 0 (mínim) i 5 (màxim).",
            "example": 2.5,
        },
    )


class QuestionCreateSchema(QuestionBaseSchema):
    """
    Esquema per crear una única pregunta.
    """

    class Meta(QuestionBaseSchema.Meta):
        description = "Cos per crear una nova pregunta."
        example = QuestionBaseSchema.Meta.example


class QuestionBulkCreateSchema(Schema):
    """
    Esquema per a la creació massiva de preguntes.
    """

    class Meta:
        description = "Cos per crear diverses preguntes en una sola sol·licitud."
        example = {
            "questions": [
                {
                    "text": "Quants dies té una setmana?",
                    "question_type": "concentration",
                    "difficulty": 1.0,
                },
                {
                    "text": "Ordena de menor a major: 3, 1, 2.",
                    "question_type": "sorting",
                    "difficulty": 2.0,
                },
            ]
        }

    questions = fields.List(
        fields.Nested(QuestionCreateSchema),
        required=True,
        validate=validate.Length(min=1),
        metadata={
            "description": "Llista de preguntes a crear.",
            "example": [
                {
                    "text": "Quants dies té una setmana?",
                    "question_type": "concentration",
                    "difficulty": 1.0,
                }
            ],
        },
    )


class QuestionResponseSchema(QuestionBaseSchema):
    """
    Esquema per retornar dades de pregunta.
    """

    class Meta(QuestionBaseSchema.Meta):
        description = "Resposta amb la informació d'una pregunta existent."
        example = {
            "id": "7e9c5a2c-1234-4b1f-9a77-111122223333",
            **QuestionBaseSchema.Meta.example,
        }

    id = fields.UUID(
        required=True,
        dump_only=True,
        metadata={
            "description": "Identificador únic de la pregunta.",
            "example": "7e9c5a2c-1234-4b1f-9a77-111122223333",
        },
    )


class QuestionUpdateSchema(QuestionBaseSchema):
    """
    Esquema per reemplaçar completament una pregunta (PUT).
    """

    class Meta(QuestionBaseSchema.Meta):
        description = "Cos complet per actualitzar tots els camps d'una pregunta existent."
        example = QuestionBaseSchema.Meta.example


class QuestionPartialUpdateSchema(Schema):
    """
    Esquema per actualitzar parcialment una pregunta (PATCH).
    """

    class Meta:
        description = "Cos parcial per modificar només alguns camps d'una pregunta."
        example = {"difficulty": 3.0}

    text = fields.String(
        required=False,
        validate=validate.Length(min=1),
        metadata={
            "description": "Enunciat o text de la pregunta.",
            "example": "Canvia l'ordre dels números: 4, 2, 3.",
        },
    )
    question_type = fields.Enum(
        QuestionType,
        required=False,
        by_value=True,
        metadata={
            "description": QUESTION_TYPE_DESCRIPTION,
            "enum": QUESTION_TYPE_VALUES,
            "example": "sorting",
        },
    )
    difficulty = fields.Float(
        required=False,
        validate=validate.Range(min=0, max=5),
        metadata={
            "description": "Puntuació de dificultat entre 0 (mínim) i 5 (màxim).",
            "example": 3.0,
        },
    )


class QuestionQuerySchema(Schema):
    """
    Esquema per filtrar preguntes mitjançant paràmetres de consulta.
    """

    class Meta:
        description = "Filtres disponibles per consultar les preguntes."
        example = {
            "id": "7e9c5a2c-1234-4b1f-9a77-111122223333",
            "question_type": "speed",
            "difficulty_min": 1.0,
            "difficulty_max": 3.0,
        }

    id = fields.UUID(
        required=False,
        metadata={
            "description": "Filtra per ID de la pregunta.",
            "example": "7e9c5a2c-1234-4b1f-9a77-111122223333",
        },
    )
    question_type = fields.Enum(
        QuestionType,
        required=False,
        by_value=True,
        metadata={
            "description": QUESTION_TYPE_DESCRIPTION,
            "enum": QUESTION_TYPE_VALUES,
            "example": "speed",
        },
    )
    difficulty = fields.Float(
        required=False,
        validate=validate.Range(min=0, max=5),
        metadata={
            "description": "Filtra per dificultat exacta entre 0 i 5.",
            "example": 2.0,
        },
    )
    difficulty_min = fields.Float(
        required=False,
        validate=validate.Range(min=0, max=5),
        metadata={
            "description": "Filtra preguntes amb dificultat superior o igual al valor indicat.",
            "example": 1.0,
        },
    )
    difficulty_max = fields.Float(
        required=False,
        validate=validate.Range(min=0, max=5),
        metadata={
            "description": "Filtra preguntes amb dificultat inferior o igual al valor indicat.",
            "example": 3.0,
        },
    )


class QuestionIdSchema(Schema):
    """
    Esquema per a operacions que requereixen l'identificador d'una pregunta.
    """

    class Meta:
        description = "Paràmetre per indicar l'ID de la pregunta."
        example = {"id": "7e9c5a2c-1234-4b1f-9a77-111122223333"}

    id = fields.UUID(
        required=True,
        metadata={
            "description": "Identificador de la pregunta sobre la qual operar.",
            "example": "7e9c5a2c-1234-4b1f-9a77-111122223333",
        },
    )


class ActivityBaseSchema(Schema):
    """
    Esquema base per als camps d'activitat.
    """

    class Meta:
        description = "Camps comuns per definir una activitat."
        example = {
            "title": "Memoritzar seqüències",
            "description": "Recorda l'ordre de colors que apareixen a la pantalla.",
            "activity_type": "concentration",
            "difficulty": 2.0,
        }

    title = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255),
        metadata={
            "description": "Títol de l'activitat.",
            "example": "Memoritzar seqüències",
        },
    )
    description = fields.String(
        required=True,
        validate=validate.Length(min=1),
        metadata={
            "description": "Descripció de l'activitat.",
            "example": "Recorda l'ordre de colors que apareixen a la pantalla.",
        },
    )
    activity_type = fields.Enum(
        QuestionType,
        required=True,
        by_value=True,
        metadata={
            "description": ACTIVITY_TYPE_DESCRIPTION,
            "enum": QUESTION_TYPE_VALUES,
            "example": "concentration",
        },
    )
    difficulty = fields.Float(
        required=True,
        validate=validate.Range(min=0, max=5),
        metadata={
            "description": "Puntuació de dificultat entre 0 (mínim) i 5 (màxim).",
            "example": 2.0,
        },
    )


class ActivityCreateSchema(ActivityBaseSchema):
    """
    Esquema per crear una única activitat.
    """

    class Meta(ActivityBaseSchema.Meta):
        description = "Cos per crear una nova activitat."
        example = ActivityBaseSchema.Meta.example


class ActivityBulkCreateSchema(Schema):
    """
    Esquema per a la creació massiva d'activitats.
    """

    class Meta:
        description = "Cos per crear diverses activitats en una sola sol·licitud."
        example = {
            "activities": [
                {
                    "title": "Suma ràpida",
                    "description": "Respon sumes senzilles en menys de 5 segons.",
                    "activity_type": "speed",
                    "difficulty": 1.5,
                }
            ]
        }

    activities = fields.List(
        fields.Nested(ActivityCreateSchema),
        required=True,
        validate=validate.Length(min=1),
        metadata={
            "description": "Llista d'activitats a crear.",
            "example": [
                {
                    "title": "Suma ràpida",
                    "description": "Respon sumes senzilles en menys de 5 segons.",
                    "activity_type": "speed",
                    "difficulty": 1.5,
                }
            ],
        },
    )


class ActivityResponseSchema(ActivityBaseSchema):
    """
    Esquema per retornar dades d'activitat.
    """

    class Meta(ActivityBaseSchema.Meta):
        description = "Resposta amb la informació d'una activitat existent."
        example = {
            "id": "8f0d1a2b-5678-4cde-9abc-444455556666",
            **ActivityBaseSchema.Meta.example,
        }

    id = fields.UUID(
        required=True,
        dump_only=True,
        metadata={
            "description": "Identificador únic de l'activitat.",
            "example": "8f0d1a2b-5678-4cde-9abc-444455556666",
        },
    )


class ActivityUpdateSchema(ActivityBaseSchema):
    """
    Esquema per reemplaçar completament una activitat (PUT).
    """

    class Meta(ActivityBaseSchema.Meta):
        description = "Cos complet per actualitzar tots els camps d'una activitat existent."
        example = ActivityBaseSchema.Meta.example


class ActivityPartialUpdateSchema(Schema):
    """
    Esquema per actualitzar parcialment una activitat (PATCH).
    """

    class Meta:
        description = "Cos parcial per modificar només alguns camps d'una activitat."
        example = {"title": "Nou títol d'activitat"}

    title = fields.String(
        required=False,
        validate=validate.Length(min=1, max=255),
        metadata={
            "description": "Títol de l'activitat.",
            "example": "Repetició de patrons",
        },
    )
    description = fields.String(
        required=False,
        validate=validate.Length(min=1),
        metadata={
            "description": "Descripció de l'activitat.",
            "example": "Segueix el patró visual que apareix a la pantalla.",
        },
    )
    activity_type = fields.Enum(
        QuestionType,
        required=False,
        by_value=True,
        metadata={
            "description": ACTIVITY_TYPE_DESCRIPTION,
            "enum": QUESTION_TYPE_VALUES,
            "example": "multitasking",
        },
    )
    difficulty = fields.Float(
        required=False,
        validate=validate.Range(min=0, max=5),
        metadata={
            "description": "Puntuació de dificultat entre 0 (mínim) i 5 (màxim).",
            "example": 3.5,
        },
    )


class ActivityQuerySchema(Schema):
    """
    Esquema per filtrar activitats mitjançant paràmetres de consulta.
    """

    class Meta:
        description = "Filtres disponibles per consultar les activitats."
        example = {
            "search": "memoritzar",
            "title": "Memoritzar seqüències",
            "activity_type": "concentration",
            "difficulty_min": 1.0,
            "difficulty_max": 4.0,
        }

    id = fields.UUID(
        required=False,
        metadata={
            "description": "Filtra per ID de l'activitat.",
            "example": "8f0d1a2b-5678-4cde-9abc-444455556666",
        },
    )
    title = fields.String(
        required=False,
        validate=validate.Length(min=1),
        metadata={
            "description": "Filtra per títol exacte de l'activitat (per cerques parcials, utilitza `search`).",
            "example": "Memoritzar seqüències",
        },
    )
    search = fields.String(
        required=False,
        validate=validate.Length(min=1),
        metadata={
            "description": "Text parcial per cercar coincidències en el títol, sense diferenciar majúscules/minúscules.",
            "example": "contar",
        },
    )
    activity_type = fields.Enum(
        QuestionType,
        required=False,
        by_value=True,
        metadata={
            "description": ACTIVITY_TYPE_DESCRIPTION,
            "enum": QUESTION_TYPE_VALUES,
            "example": "concentration",
        },
    )
    difficulty = fields.Float(
        required=False,
        validate=validate.Range(min=0, max=5),
        metadata={
            "description": "Filtra per dificultat exacta entre 0 i 5.",
            "example": 2.0,
        },
    )
    difficulty_min = fields.Float(
        required=False,
        validate=validate.Range(min=0, max=5),
        metadata={
            "description": "Filtra activitats amb dificultat superior o igual al valor indicat.",
            "example": 1.0,
        },
    )
    difficulty_max = fields.Float(
        required=False,
        validate=validate.Range(min=0, max=5),
        metadata={
            "description": "Filtra activitats amb dificultat inferior o igual al valor indicat.",
            "example": 4.0,
        },
    )


class ActivityIdSchema(Schema):
    """
    Esquema per a operacions que requereixen l'identificador d'una activitat.
    """

    class Meta:
        description = "Paràmetre per indicar l'ID de l'activitat."
        example = {"id": "8f0d1a2b-5678-4cde-9abc-444455556666"}

    id = fields.UUID(
        required=True,
        metadata={
            "description": "Identificador de l'activitat sobre la qual operar.",
            "example": "8f0d1a2b-5678-4cde-9abc-444455556666",
        },
    )

class ActivityCompleteSchema(Schema):
    """
    Esquema per marcar una activitat com a completada.
    """

    class Meta:
        description = "Paràmetres per indicar l'activitat completada i les dades associades."
        example = {
            "activity_id": "8f0d1a2b-5678-4cde-9abc-444455556666",
            "score": 8.5,
            "seconds_to_finish": 120.3,
        }

    id = fields.UUID(
        required=True,
        metadata={
            "description": "Identificador de l'activitat que s'ha completat.",
            "example": "8f0d1a2b-5678-4cde-9abc-444455556666",
        },
    )

    score = fields.Float(
        required=True,
        metadata={
            "description": "Puntuació obtinguda en completar l'activitat.",
            "example": 8.5,
        },
    )

    seconds_to_finish = fields.Float(
        required=True,
        metadata={
            "description": "Temps en segons que ha trigat l'usuari a completar l'activitat.",
            "example": 120.3,
        },
    )

class ActivityCompleteResponseSchema(Schema):
    """
    Esquema per a la resposta de l'activitat completada.
    """

    class Meta:
        description = "Resposta amb les dades de puntuació en completar una activitat."
        example = {
            "patient": {
                "email": "pacient@example.com",
                "name": "John",
                "surname": "Doe",
                "role": {"gender": "male", "age": 30, "height_cm": 180.0, "weight_kg": 75.0, "doctors": []},
            },
            "activity": {
                "id": "8f0d1a2b-5678-4cde-9abc-444455556666",
                "title": "Suma ràpida",
                "description": "Respon sumes senzilles en menys de 5 segons.",
                "activity_type": "speed",
                "difficulty": 1.5,
            },
            "completed_at": "2024-05-01T12:34:56.789Z",
            "score": 8.5,
            "seconds_to_finish": 120.3,
        }

    patient = fields.Nested(
        UserResponseSchema,
        required=True,
        dump_only=True,
        metadata={
            "description": "Dades del pacient que ha completat l'activitat.",
        },
    )
    activity = fields.Nested(
        ActivityResponseSchema,
        required=True,
        dump_only=True,
        metadata={
            "description": "Activitat que s'ha completat.",
        },
    )
    completed_at = fields.DateTime(
        required=True,
        dump_only=True,
        metadata={
            "description": "Moment en què s'ha registrat la finalització.",
            "example": "2024-05-01T12:34:56.789Z",
        },
    )
    score = fields.Float(
        required=True,
        dump_only=True,
        metadata={
            "description": "Puntuació obtinguda en completar l'activitat.",
            "example": 8.5,
        },
    )
    seconds_to_finish = fields.Float(
        required=True,
        dump_only=True,
        metadata={
            "description": "Temps en segons que ha trigat el pacient a completar l'activitat.",
            "example": 120.3,
        },
    )

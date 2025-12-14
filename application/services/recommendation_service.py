import random
import concurrent.futures
from application.services.user_service import PatientData
from helpers.factories.adapter_factories import AbstractAdapterFactory

class RecommendationService:
    """
    Service to handle recommendations for patients using LLMs.
    """
    __adapter_factory: AbstractAdapterFactory

    FALLBACK_RECOMMENDATIONS = [
    {
        "recommendation": "Surt a fer un passeig curt i fixa't en tres coses de color vermell que trobis pel camí.",
        "reason": "Caminar activa la circulació i buscar objectes específics estimula l'atenció selectiva sense generar estrès.",
        "areas": [
        { "area": "attention", "percentage": 70 },
        { "area": "speed", "percentage": 30 }
        ]
    },
    {
        "recommendation": "Prepara't una infusió o un cafè calent, centrant-te en l'aroma i en cada pas del procés.",
        "reason": "Seguir una seqüència de passos familiars ajuda a l'organització mental i proporciona un moment de calma sensorial.",
        "areas": [
        { "area": "alternating_fluency", "percentage": 60 },
        { "area": "speed", "percentage": 40 }
        ]
    },
    {
        "recommendation": "Truca a un amic o familiar proper per xerrar cinc minuts sobre com ha anat el dia.",
        "reason": "La conversa espontània requereix processar informació ràpidament i formular respostes, activant la fluïdesa verbal.",
        "areas": [
        { "area": "alternating_fluency", "percentage": 50 },
        { "area": "memory", "percentage": 30 },
        { "area": "speed", "percentage": 20 }
        ]
    },
    {
        "recommendation": "Seu còmodament prop d'una finestra i observa el moviment del carrer o la natura durant uns minuts.",
        "reason": "L'observació passiva permet treballar l'atenció sostinguda amb una càrrega cognitiva molt baixa, ideal per moments de fatiga.",
        "areas": [
        { "area": "attention", "percentage": 100 }
        ]
    },
    {
        "recommendation": "Escolta una cançó que t'agradi molt i intenta identificar tots els instruments que hi sonen.",
        "reason": "La música millora l'estat d'ànim, i l'exercici d'identificació treballa la memòria auditiva i la concentració.",
        "areas": [
        { "area": "attention", "percentage": 60 },
        { "area": "memory", "percentage": 40 }
        ]
    },
    {
        "recommendation": "Fes una llista breu de quatre coses que necessitis comprar o fer demà.",
        "reason": "Planificar i escriure ítems concrets ajuda a estructurar el pensament i exercita la recuperació de la informació.",
        "areas": [
        { "area": "alternating_fluency", "percentage": 50 },
        { "area": "memory", "percentage": 50 }
        ]
    },
    {
        "recommendation": "Rega les plantes de casa i treu-ne les fulles seques amb suavitat.",
        "reason": "La cura de les plantes connecta amb l'entorn i requereix coordinació i atenció al detall en un context relaxat.",
        "areas": [
        { "area": "speed", "percentage": 50 },
        { "area": "attention", "percentage": 50 }
        ]
    },
    {
        "recommendation": "Tria la roba que et posaràs demà i deixa-la preparada sobre una cadira.",
        "reason": "Prendre decisions senzilles sobre seqüències lògiques ajuda a la planificació i redueix la fatiga mental del dia següent.",
        "areas": [
        { "area": "alternating_fluency", "percentage": 70 },
        { "area": "memory", "percentage": 30 }
        ]
    },
    {
        "recommendation": "Mira un àlbum de fotos antic o imatges al mòbil i recorda on es van fer.",
        "reason": "Evocar records personals reforça la memòria episòdica i sol tenir un efecte positiu en l'estat emocional.",
        "areas": [
        { "area": "memory", "percentage": 80 },
        { "area": "attention", "percentage": 20 }
        ]
    },
    {
        "recommendation": "Llegeix un parell de pàgines d'un llibre o una revista que tinguis a mà.",
        "reason": "La lectura breu ajuda a mantenir el focus i la comprensió lectora sense esgotar les reserves d'energia.",
        "areas": [
        { "area": "attention", "percentage": 60 },
        { "area": "memory", "percentage": 40 }
        ]
    },
    {
        "recommendation": "Prepara una macedònia o talla una peça de fruita per berenar.",
        "reason": "Manipular aliments i utilitzar estris de cuina de forma segura implica coordinació i seguiment d'una tasca seqüencial.",
        "areas": [
        { "area": "speed", "percentage": 40 },
        { "area": "attention", "percentage": 60 }
        ]
    },
    {
        "recommendation": "Organitza les teves medicines o vitamines per als propers dies utilitzant el pastiller.",
        "reason": "Aquesta tasca és funcional i requereix classificar i verificar informació important, exercitant la memòria de treball.",
        "areas": [
        { "area": "memory", "percentage": 50 },
        { "area": "attention", "percentage": 50 }
        ]
    },
    {
        "recommendation": "Envia una nota de veu a algú explicant una cosa curiosa que has vist avui.",
        "reason": "Narrar una petita història obliga a estructurar el discurs i mantenir el fil, treballant la fluïdesa verbal.",
        "areas": [
        { "area": "alternating_fluency", "percentage": 40 },
        { "area": "speed", "percentage": 60 }
        ]
    },
    {
        "recommendation": "Dibuixa o gargoteja lliurement en un paper mentre escoltes la ràdio.",
        "reason": "La multitasca suau (dibuixar i escoltar) estimula la capacitat de canviar el focus d'atenció de manera relaxada.",
        "areas": [
        { "area": "attention", "percentage": 40 },
        { "area": "alternating_fluency", "percentage": 60 }
        ]
    },
    {
        "recommendation": "Plega la roba neta que tinguis seca, separant-la per tipus de peça.",
        "reason": "Una activitat repetitiva i motora que permet classificar ítems mentalment amb un ritme pausat i constant.",
        "areas": [
        { "area": "speed", "percentage": 70 },
        { "area": "attention", "percentage": 30 }
        ]
    },
    {
        "recommendation": "Obre el pot de les espècies o herbes aromàtiques i intenta endevinar quina és cadascuna només per l'olor.",
        "reason": "L'estimulació olfactiva connecta directament amb la memòria i requereix atenció focalitzada sense esforç visual.",
        "areas": [
        { "area": "memory", "percentage": 50 },
        { "area": "attention", "percentage": 50 }
        ]
    },
    {
        "recommendation": "Tanca els ulls un moment i visualitza amb tot el detall possible un paisatge que t'agradi molt.",
        "reason": "La visualització mental exercita la capacitat de mantenir imatges actives al cervell, una forma suau de memòria.",
        "areas": [
        { "area": "memory", "percentage": 60 },
        { "area": "attention", "percentage": 40 }
        ]
    },
    {
        "recommendation": "Fes estiraments suaus de coll i espatlles mentre comptes lentament les respiracions.",
        "reason": "Coordinar el moviment amb el recompte de la respiració ajuda a connectar cos i ment, reduint l'ansietat.",
        "areas": [
        { "area": "attention", "percentage": 70 },
        { "area": "speed", "percentage": 30 }
        ]
    },
    {
        "recommendation": "Fes un cop d'ull als titulars d'una revista o diari i llegeix només la notícia més positiva que trobis.",
        "reason": "Cercar informació específica (escaneig visual) millora la velocitat de processament i filtra estímuls negatius.",
        "areas": [
        { "area": "speed", "percentage": 60 },
        { "area": "attention", "percentage": 40 }
        ]
    },
    {
        "recommendation": "Taral·leja una melodia que coneguis bé mentre fas alguna tasca senzilla com recollir la taula.",
        "reason": "La doble tasca (taral·lejar i moure's) estimula la fluïdesa i la coordinació sense suposar una càrrega excessiva.",
        "areas": [
        { "area": "alternating_fluency", "percentage": 40 },
        { "area": "memory", "percentage": 60 }
        ]
    },
    {
        "recommendation": "Escriu en una llibreta una cosa bona, per petita que sigui, que t'hagi passat aquesta setmana.",
        "reason": "L'escriptura de gratitud requereix recuperar informació recent i estructurar-la en una frase coherent.",
        "areas": [
        { "area": "alternating_fluency", "percentage": 50 },
        { "area": "memory", "percentage": 50 }
        ]
    },
    {
        "recommendation": "Mira el cel per la finestra i intenta trobar formes conegudes als núvols durant uns minuts.",
        "reason": "Aquest joc visual clàssic estimula la creativitat i la velocitat de processament visual en un entorn relaxant.",
        "areas": [
        { "area": "attention", "percentage": 50 },
        { "area": "speed", "percentage": 50 }
        ]
    },
    {
        "recommendation": "Agafa una fruita o un objecte petit i descriu-ne mentalment la textura, el pes i el color.",
        "reason": "Generar adjectius i descriptors per a un objecte físic activa l'accés al lèxic i l'atenció sensorial.",
        "areas": [
        { "area": "alternating_fluency", "percentage": 70 },
        { "area": "attention", "percentage": 30 }
        ]
    },
    {
        "recommendation": "Ordena tres o quatre llibres o revistes que tinguis a prop segons la seva mida o color.",
        "reason": "Categoritzar objectes físics aplicant una norma senzilla (mida/color) manté la ment ordenada i activa.",
        "areas": [
        { "area": "memory", "percentage": 40 },
        { "area": "speed", "percentage": 60 }
        ]
    },
    {
        "recommendation": "Posa't crema hidratant a les mans fent un massatge lent i concentrant-te només en el tacte.",
        "reason": "L'atenció plena en una sensació física (tacte) ajuda a reduir el soroll mental i millora la concentració.",
        "areas": [
        { "area": "attention", "percentage": 100 }
        ]
    },
    {
        "recommendation": "Mira un programa de televisió tranquil i intenta resumir l'argument en una sola frase quan acabi.",
        "reason": "Sintetitzar informació complexa en una idea simple és un excel·lent exercici de comprensió i fluïdesa.",
        "areas": [
        { "area": "memory", "percentage": 50 },
        { "area": "alternating_fluency", "percentage": 50 }
        ]
    },
    {
        "recommendation": "Practica tres respiracions profundes, comptant fins a quatre quan agafis l'aire i quan el treguis.",
        "reason": "El comptatge rítmic manté la memòria de treball activa mentre l'oxigenació ajuda a claredat mental.",
        "areas": [
        { "area": "attention", "percentage": 60 },
        { "area": "memory", "percentage": 40 }
        ]
    },
    {
        "recommendation": "Juga una partida ràpida de solitari amb cartes o fes un passatemps molt senzill.",
        "reason": "Els jocs estructurats amb regles conegudes ajuden a la velocitat de processament i a la presa de decisions.",
        "areas": [
        { "area": "speed", "percentage": 50 },
        { "area": "memory", "percentage": 50 }
        ]
    },
    {
        "recommendation": "Beu un got d'aigua a glops petits, sentint la temperatura i el recorregut del líquid.",
        "reason": "Centrar-se exclusivament en l'acte de beure elimina distraccions i focalitza l'atenció en el present.",
        "areas": [
        { "area": "attention", "percentage": 100 }
        ]
    },
    {
        "recommendation": "Surt un moment al balcó o jardí i intenta identificar tres sons diferents que sentis al carrer.",
        "reason": "Discriminar estímuls auditius en un entorn obert treballa l'atenció selectiva i la velocitat de percepció.",
        "areas": [
        { "area": "attention", "percentage": 70 },
        { "area": "speed", "percentage": 30 }
        ]
    }
    ]

    SYSTEM_PROMPT = """Ets un assistent clínic de suport (no substitueixes cap professional sanitari) especialitzat en recomanacions d’activitats per a persones amb càncer que poden presentar dificultats cognitives derivades del tractament i/o de la malaltia.

La query de l’usuari consisteix exclusivament en les dades del/la pacient (estat actual, símptomes, nivell de fatiga, estat emocional, limitacions físiques, preferències, entorn, suport disponible i qualsevol altra informació rellevant). No rebràs cap pregunta ni cap ordre explícita: has d’interpretar aquestes dades com el context complet sobre el qual basar la teva resposta.

Tasca principal:
- Analitza les dades del/la pacient i el seu estat més recent.
- Genera una única recomanació d’activitat, concreta, segura i executable avui o en els pròxims dies.
- La recomanació ha de ser una activitat quotidiana i natural del dia a dia (per exemple: sortir a caminar, preparar una beguda calenta, escoltar música, regar plantes, parlar amb algú, observar l’entorn), evitant exercicis artificials o de tipus “test cognitiu”.

Objectiu cognitiu:
- L’activitat ha d’estimular una o diverses de les següents funcions cognitives, que són les únicament permeses:
  - atenció
  - memòria de treball
  - fluència alternant
  - velocitat de processament
- L’estimulació cognitiva ha de ser implícita i integrada en l’activitat, no explícita ni forçada.
- Ajusta la càrrega cognitiva segons la fatiga i la claredat mental descrites.

Creativitat i varietat:
- Evita recomanar repetidament la mateixa activitat entre respostes.
- No prioritzis activitats domèstiques repetitives com ordenar calaixos, armaris o papers.
- Fomenta recomanacions variades vinculades al moviment suau, el contacte amb l’entorn, la comunicació, la música, la creativitat, la rutina personal o el benestar emocional.
- Si diverses opcions són possibles segons les dades, escull la més diferent de les habituals i la més alineada amb les preferències del/la pacient.

Seguretat i límits:
- No facis diagnòstics ni donis consells mèdics.
- No suggereixis canvis de medicació ni de tractament.
- Si les dades indiquen signes d’alarma (confusió sobtada o greu, empitjorament ràpid, dolor intens no controlat, febre, mareig important, dificultat respiratòria, ideació autolesiva o risc elevat de caiguda), no prioritzis una activitat i indica de manera empàtica la necessitat de contactar amb l’equip sanitari o un cuidador.
- Evita activitats amb risc físic si hi ha inestabilitat, neuropatia o mareig.

To i estil:
- Escriu sempre en català.
- Mantén un to proper, empàtic, tranquil i respectuós, sense infantilitzar.
- Utilitza frases curtes i llenguatge senzill.
- Els camps recommendation i reason han de ser breus (aproximadament 2–3 línies cadascun).

Structured output (obligatori):
- Has de respondre exclusivament utilitzant l’structured output que ja se t’ha proporcionat.
- No afegeixis cap camp extra ni cap text fora de l’estructura definida.
- El camp areas només pot contenir aquestes funcions cognitives:
  - atenció
  - memòria de treball
  - fluència alternant
  - velocitat de processament

Regla crítica dels percentatges:
- La suma de tots els valors percentage dins areas ha de ser exactament 100.0.
- No utilitzis aproximacions.
- Fes servir decimals si cal.
- Verifica la suma abans de generar la resposta i corregeix-la internament si no és exacta.

Gestió de manca de dades:
- Si les dades del/la pacient són incompletes o ambiguës, assumeix sempre l’opció més segura i conservadora.
- No facis preguntes a l’usuari.
- Justifica breument l’elecció dins del camp reason.

Recordatori final:
- La query són només dades, no una pregunta.
- Has d’interpretar-les i actuar en conseqüència.
- Una sola recomanació clara, quotidiana i executable.
- Sortida exclusivament estructurada.
- Percentatges que sumin 100.0 exactes.
"""

    def __init__(self, adapter_factory: AbstractAdapterFactory | None = None) -> None:
        self.__adapter_factory = adapter_factory or AbstractAdapterFactory.get_instance()

    def get_recommendation_for_patient(self, patient_data: PatientData) -> dict:
        """
        Get a recommendation for the specified patient using an LLM.
        If the LLM fails or times out, return a fallback recommendation.
        Args:
            patient_data (PatientData): Data of the patient to get recommendations for.
        Returns:
            dict: The generated recommendation.
        """
        llm_adapter = self.__adapter_factory.get_llm_adapter()

        def _call_llm():
            return llm_adapter.generate_recommendation(
                patient_data, self.SYSTEM_PROMPT
            )

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_call_llm)
                return future.result(timeout=5)
        except (concurrent.futures.TimeoutError, Exception):
            return random.choice(self.FALLBACK_RECOMMENDATIONS)
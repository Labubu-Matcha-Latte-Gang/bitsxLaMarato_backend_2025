from enum import Enum

class QuestionType(Enum):
    CONCENTRATION = "concentration"
    SPEED = "speed"
    WORDS = "words"
    SORTING = "sorting"
    MULTITASKING = "multitasking"
    DIARY = "diary"

class CognitiveArea(Enum):
    ATTENTION = "attention"
    MEMORY = "memory"
    ALTERNATING_FLUENCY = "alternating_fluency"
    SPEED = "speed"
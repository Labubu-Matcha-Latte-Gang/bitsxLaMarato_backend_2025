from __future__ import annotations
from abc import ABC, abstractmethod
import json
from time import time
from typing import TYPE_CHECKING

from openai import AzureOpenAI

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from helpers.debugger.logger import AbstractLogger
from helpers.enums.question_types import CognitiveArea

if TYPE_CHECKING:
    from application.services.user_service import PatientData

class AbstractLlmAdapter(ABC):
    """Abstract adapter for LLM services."""

    logger = AbstractLogger.get_instance()

    @classmethod
    def _patient_data_to_markdown(cls, patient_data: PatientData) -> str:
        """
        Convert patient data to a markdown-formatted string optimized for LLM context.
        FILTERED: Excludes PII (Name, Email), administrative data (Doctors), and raw files (Graphs).
        """
        
        p_info = patient_data.get("patient", {})
        role_data = p_info.get("role", {})
        
        lines = []
        
        lines.append("# Perfil Clínic del Pacient")
        lines.append("> **Nota:** Les dades personals i administratives han estat anonimitzades per privacitat.")
        lines.append("")
        
        lines.append("## Dades Demogràfiques i Condicions")
        lines.append(f"- **Edat:** {role_data.get('age', 'N/A')}")
        lines.append(f"- **Gènere:** {role_data.get('gender', 'N/A')}")
        lines.append(f"- **Alçada:** {role_data.get('height_cm', 'N/A')} cm")
        lines.append(f"- **Pes:** {role_data.get('weight_kg', 'N/A')} kg")
        
        ailments = role_data.get("ailments")
        treatments = role_data.get("treatments")
        
        lines.append(f"- **Malalties/Afeccions:** {ailments if ailments else 'Cap registrada'}")
        lines.append(f"- **Tractaments:** {treatments if treatments else 'Cap actiu'}")
        lines.append("")

        scores = patient_data.get("scores", [])
        if scores:
            lines.append("## Puntuacions d'Activitat")
            lines.append("| Data | Activitat | Tipus | Puntuació | Durada (s) |")
            lines.append("|---|---|---|---|---|")
            for score in scores:
                row = (
                    f"| {score.get('completed_at', 'N/A')} "
                    f"| {score.get('activity_title', 'N/A')} "
                    f"| {score.get('activity_type', 'N/A')} "
                    f"| **{score.get('score', 0)}** "
                    f"| {score.get('seconds_to_finish', 0)} |"
                )
                lines.append(row)
            lines.append("")
        
        return "\n".join(lines)
    
    @classmethod
    def _normalize_percentages(cls, areas: dict) -> dict:
        """
        Adjusts the percentages so they sum exactly to 100.0 by modifying only the area with the highest weight.
        """
        if not areas:
            return areas

        total = sum(a["percentage"] for a in areas)
        delta = 100.0 - total

        if abs(delta) < 1e-6:
            return areas

        target = max(areas, key=lambda a: a["percentage"])

        target["percentage"] += delta

        target["percentage"] = max(
            0.0,
            min(100.0, target["percentage"])
        )

        return areas

    
    @abstractmethod
    def generate_summary(self, patient_data: PatientData, system_prompt: str) -> str:
        """Generate a summary for the given patient data.
        
        Args:
            patient_data (PatientData): Data of the patient to summarize.
            system_prompt (str): The system instruction to guide the LLM.
        Returns:
            str: The generated summary.
        """
        raise NotImplementedError
    
    @abstractmethod
    def generate_recommendation(self, patient_data: PatientData, system_prompt: str) -> dict:
        """Generate a recommendation for the given patient data.
        
        Args:
            patient_data (PatientData): Data of the patient to recommend for.
            system_prompt (str): The system instruction to guide the LLM.
        Returns:
            dict: The generated recommendation.
        """
    
class AzureOpenaiAdapter(AbstractLlmAdapter):
    """Concrete adapter for Azure OpenAI LLM services."""
    __client: AzureOpenAI = None
    __model: str = None

    def __init__(self, api_key: str = None, endpoint: str = None, api_version: str = None, model: str = None) -> None:
        from flask import current_app

        api_key = api_key or current_app.config['AZURE_OPENAI_API_KEY']
        endpoint = endpoint or current_app.config['AZURE_OPENAI_ENDPOINT']
        api_version = api_version or current_app.config['AZURE_OPENAI_API_VERSION']

        self.__client = AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=endpoint)
        self.__model = model or current_app.config.get('AZURE_OPENAI_LLM_MODEL', 'gpt-5-mini') or 'gpt-5-mini'
    
    def generate_summary(self, patient_data: PatientData, system_prompt: str) -> str:
        context_data = self._patient_data_to_markdown(patient_data)

        try:
            response = self.__client.chat.completions.create(
                model=self.__model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Dades del pacient:\n{context_data}"}
                ],
                reasoning_effort="low", 
                
                extra_body={"verbosity": "low"},
                max_completion_tokens=300
            )

            final_summary = response.choices[0].message.content

            if not final_summary:
                self.logger.error("Empty summary received from AzureOpenAI", module="AzureOpenaiAdapter")
                return "No s'ha pogut generar un resum del pacient."
            
            return final_summary

        except Exception as e:
            self.logger.error(f"Error generating summary in AzureOpenaiAdapter: {str(e)}", module="AzureOpenaiAdapter", error=e)
            return "Hi ha hagut un error en generar el resum del pacient."
        
    def generate_recommendation(self, patient_data: PatientData, system_prompt: str) -> dict:
        raise NotImplementedError("AzureOpenaiAdapter does not implement generate_recommendation yet.")
        
class GeminiAdapter(AbstractLlmAdapter):
    """Concrete adapter for Google Gemini LLM services."""
    __model_name: str = None
    
    def __init__(self, api_key: str = None, model_name: str = None) -> None:
        """
        Initialize the Gemini client.
        Uses GOOGLE_API_KEY from Flask config by default.
        Args:
            api_key (str, optional): API key for Google Gemini. Defaults to None.
            model_name (str, optional): Model name to use. Defaults to `gemini-2.5-flash`.
        """
        from flask import current_app

        self.api_key = api_key or current_app.config.get('GOOGLE_API_KEY')
        
        if not self.api_key:
            current_app.logger.warning("GOOGLE_API_KEY not found in configuration.")
        else:
            genai.configure(api_key=self.api_key)
            self.__model_name = model_name or current_app.config.get('GEMINI_MODEL_NAME', 'gemini-2.5-flash')

    def generate_summary(self, patient_data: PatientData, system_prompt: str) -> str:
        context_data = self._patient_data_to_markdown(patient_data)
        self.logger.debug("Context data prepared for Gemini", module="GeminiAdapter", metadata={"context_data": context_data})
        
        try:

            init_time = time()
            gen_config = GenerationConfig(
                temperature=0,
                max_output_tokens=6000,
                candidate_count=1,
                top_p=0.6,
                top_k=25
            )

            model = genai.GenerativeModel(
                model_name=self.__model_name,
                system_instruction=system_prompt
            )

            response = model.generate_content(
                contents=context_data,
                generation_config=gen_config
            )

            final_summary = response.text

            if not final_summary:
                self.logger.error("Empty summary received from Gemini", module="GeminiAdapter")
                return "No s'ha pogut generar un resum del pacient."
            
            final_time = time() - init_time
            # Do not log the full summary at info level to avoid exposing sensitive patient data
            self.logger.info(f"Gemini summary generated in {final_time:.2f} seconds", module="GeminiAdapter", metadata={"duration_seconds": final_time})
            # If needed for debugging, log the summary at debug level (ensure this is disabled in production)
            # self.logger.debug("Gemini summary content", module="GeminiAdapter", metadata={"summary": final_summary})
            
            return final_summary

        except Exception as e:
            self.logger.error(f"Error generating summary in GeminiAdapter: {str(e)}", module="GeminiAdapter", error=e)
            return "No s'ha pogut generar el resum (Error del servei Gemini)."

    def generate_recommendation(self, patient_data: PatientData, system_prompt: str) -> dict:
        context_data = self._patient_data_to_markdown(patient_data)
        self.logger.debug("Context data prepared for Gemini", module="GeminiAdapter", metadata={"context_data": context_data})

        try:
            enum_array = [area.value for area in CognitiveArea]
            schema = {
                "type": "object",
                "required": ["recommendation", "reason", "areas"],
                "properties": {
                    "recommendation": {"type": "string"},
                    "reason": {"type": "string"},
                    "areas": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["area", "percentage"],
                            "properties": {
                                "area": {
                                    "type": "string",
                                    "enum": enum_array
                                },
                                "percentage": {
                                    "type": "number"
                                }
                            }
                        }
                    }
                },
            }
            gen_config = GenerationConfig(
                temperature=0.8,
                candidate_count=1,
                response_mime_type="application/json",
                response_schema=schema
            )

            model = genai.GenerativeModel(
                "gemini-2.5-flash",
                system_instruction=system_prompt
            )

            response = model.generate_content(context_data, generation_config=gen_config)

            output = json.loads(response.text)

            output["areas"] = self._normalize_percentages(output["areas"])

            self.logger.info("Gemini recommendation generated successfully", module="GeminiAdapter", metadata={"recommendation": output})
            return output
        except Exception as e:
            self.logger.error(f"Error generating recommendation in GeminiAdapter: {str(e)}", module="GeminiAdapter", error=e)
            return {"error": "No s'ha pogut generar la recomanació (Error del servei Gemini)."}
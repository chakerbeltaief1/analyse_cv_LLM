import os
import re
import json
import time
import logging
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import fitz  # PyMuPDF
import ollama
from tqdm import tqdm


# Configuration du logging
def setup_logging(log_file: str = "cv_analyzer.log") -> logging.Logger:
    """Configure et retourne un logger pour l'application."""
    logger = logging.getLogger("cv_analyzer")
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # Handler pour fichier
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Handler pour console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger


warnings.filterwarnings("ignore", category=FutureWarning)


@dataclass
class CVAnalyzerConfig:
    """Configuration pour l'analyseur de CV."""
    
    folder_path: Path = Path(r"C:\analyse_cv_LLM\Backend\data\cv_brut")
    output_folder: Path = Path(r"C:\analyse_cv_LLM\Backend\data\dossier_feature")
    model_name: str = "llama3.2:3b"
    max_workers: int = 2  # Reduced for stability
    timeout_seconds: int = 60  # Increased timeout
    retry_count: int = 3
    max_text_length: int = 150000 # Reduced for better processing
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'CVAnalyzerConfig':
        """Crée une instance de configuration à partir d'un dictionnaire."""
        config_dict = config_dict.copy()
        if "folder_path" in config_dict:
            config_dict["folder_path"] = Path(config_dict["folder_path"])
        if "output_folder" in config_dict:
            config_dict["output_folder"] = Path(config_dict["output_folder"])
        
        return cls(**config_dict)


class PDFTextExtractor:
    """Classe pour extraire le texte des fichiers PDF."""
    
    @staticmethod
    def extract(file_path: Union[str, Path]) -> str:
        """Extrait le texte d'un fichier PDF."""
        logger = logging.getLogger("cv_analyzer")
        text = ""
        
        try:
            with fitz.open(file_path) as doc:
                for page in doc:
                    page_text = page.get_text()
                    if page_text.strip():  # Only add non-empty pages
                        text += page_text + "\n"
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du PDF {file_path}: {e}")
            raise
        
        # Nettoyage du texte
        text = PDFTextExtractor.clean_text(text)
        return text
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Nettoie le texte extrait."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might cause issues
        text = re.sub(r'[^\w\s@.\+\-:,;()/\n]', ' ', text)
        # Clean up multiple spaces again
        text = re.sub(r' +', ' ', text)
        return text.strip()


class CVPromptGenerator:
    """Classe pour générer des prompts d'analyse de CV."""
    
    @staticmethod
    def create_prompt(text: str, max_length: int = 8000) -> str:
        """Génère un prompt pour l'analyse de CV."""
        # Truncate text if too long
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return f"""Tu es un assistant spécialisé dans l'analyse de CV. Analyse le CV suivant et extrais les informations dans le format JSON exact suivant. IMPORTANT: Réponds UNIQUEMENT avec le JSON, sans texte supplémentaire.

{{
  "informations_personnelles": {{
    "nom_prenom": "",
    "email": "",
    "telephone": "",
    "adresse": "",
    "github": "",
    "linkedin": "",
    "portfolio": ""
  }},
  "profil": "",
  "experiences_professionnelles": [
    {{
      "type": "",
      "poste": "",
      "entreprise": "",
      "date_debut": "",
      "date_fin": "",
      "description": "",
      "competences_utilisees": []
    }}
  ],
  "formation": [
    {{
      "niveau": "",
      "diplome": "",
      "etablissement": "",
      "specialite": "",
      "date_debut": "",
      "date_fin": "",
      "description": ""
    }}
  ],
  "projets": [
    {{
      "titre": "",
      "description": "",
      "technologies": [],
      "responsabilites": [],
      "date_debut": "",
      "date_fin": ""
    }}
  ],
  "competences": {{
    "langages_programmation": [],
    "frameworks_bibliotheques": [],
    "outils_developpement": [],
    "bases_donnees": [],
    "methodologies": [],
    "cloud_devops": [],
    "autres": []
  }},
  "langues": [
    {{
      "langue": "",
      "niveau": ""
    }}
  ],
  "vie_associative": [
    {{
      "organisation": "",
      "role": "",
      "date_debut": "",
      "date_fin": "",
      "description": ""
    }}
  ],
  "certifications": [
    {{
      "titre": "",
      "organisme": "",
      "date": "",
      "details": ""
    }}
  ],
  "soft_skills": [],
  "centres_interet": []
}}

CV à analyser:
{text}"""


class JSONProcessor:
    """Classe pour traiter les réponses JSON du modèle LLM."""
    
    @staticmethod
    def extract_json_from_response(content: str) -> str:
        """Extrait le JSON de la réponse du modèle."""
        # Remove code blocks
        content = re.sub(r'```(?:json)?\s*', '', content)
        content = re.sub(r'\s*```', '', content)
        
        # Find JSON content between braces
        json_match = re.search(r'(\{.*\})', content, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        return content.strip()
    
    @staticmethod
    def clean_and_validate(json_str: str) -> Optional[Dict[str, Any]]:
        """Nettoie et valide une chaîne JSON."""
        logger = logging.getLogger("cv_analyzer")
        
        if not json_str.strip():
            logger.warning("Réponse vide du modèle")
            return None
        
        try:
            # First attempt: direct parsing
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"Première tentative JSON échouée: {e}")
            
            try:
                # Clean common JSON issues
                cleaned = json_str
                
                # Fix trailing commas
                cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
                
                # Fix quotes
                cleaned = cleaned.replace('\\"', '"')
                cleaned = re.sub(r'([^\\])"([^"]*)"([^",}\]:\s])', r'\1"\2"\3', cleaned)
                
                # Remove any non-JSON content before and after
                start = cleaned.find('{')
                end = cleaned.rfind('}') + 1
                if start >= 0 and end > start:
                    cleaned = cleaned[start:end]
                
                return json.loads(cleaned)
                
            except json.JSONDecodeError as e2:
                logger.error(f"Impossible de corriger le JSON: {e2}")
                logger.debug(f"JSON problématique: {json_str[:500]}...")
                return None


class LLMClient:
    """Client pour interagir avec le modèle LLM."""
    
    def __init__(self, model_name: str, timeout: int = 120, retries: int = 3):
        """Initialise le client LLM."""
        self.model_name = model_name
        self.timeout = timeout
        self.retries = retries
        self.logger = logging.getLogger("cv_analyzer")
    
    def get_structured_info(self, text: str) -> Optional[Dict[str, Any]]:
        """Obtient des informations structurées à partir du texte."""
        prompt = CVPromptGenerator.create_prompt(text)
        
        for attempt in range(self.retries + 1):
            try:
                self.logger.debug(f"Tentative {attempt + 1}/{self.retries + 1} d'appel au modèle {self.model_name}")
                
                response = ollama.chat(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    options={
                        "temperature": 0.1,  # Lower temperature for more consistent output
                        "top_p": 0.9,
                        "num_predict": 2048,  # Limit response length
                    }
                )
                
                content = response['message']['content']
                self.logger.debug(f"Réponse brute (premiers 200 chars): {content[:200]}...")
                
                if not content or content.strip() == "":
                    self.logger.warning(f"Tentative {attempt + 1}: Réponse vide du modèle")
                    continue
                
                json_content = JSONProcessor.extract_json_from_response(content)
                result = JSONProcessor.clean_and_validate(json_content)
                
                if result:
                    self.logger.debug("JSON valide obtenu")
                    return result
                
                self.logger.warning(f"Tentative {attempt + 1}/{self.retries + 1}: JSON invalide")
                if attempt < self.retries:
                    time.sleep(2 ** attempt)  # Exponential backoff
                
            except Exception as e:
                self.logger.warning(f"Tentative {attempt + 1}/{self.retries + 1}: Erreur Ollama: {e}")
                if attempt < self.retries:
                    time.sleep(2 ** attempt)
        
        self.logger.error(f"Échec après {self.retries + 1} tentatives")
        return None


class CVProcessor:
    """Classe principale pour le traitement des CV."""
    
    def __init__(self, config: CVAnalyzerConfig):
        """Initialise le processeur de CV."""
        self.config = config
        self.logger = logging.getLogger("cv_analyzer")
        self.llm_client = LLMClient(
            model_name=config.model_name,
            timeout=config.timeout_seconds,
            retries=config.retry_count
        )
    
    def process_file(self, file_name: str) -> Optional[Path]:
        """Traite un fichier CV."""
        file_path = self.config.folder_path / file_name
        
        try:
            self.logger.info(f"Traitement de : {file_name}")
            
            # Check if output file already exists
            name_without_ext = Path(file_name).stem
            output_file = self.config.output_folder / f"{name_without_ext}.json"
            if output_file.exists():
                self.logger.info(f"Fichier {file_name} déjà traité, passage au suivant")
                return output_file
            
            # Extraction du texte
            text = PDFTextExtractor.extract(file_path)
            
            if len(text.strip()) < 100:
                self.logger.warning(f"Texte trop court pour {file_name} ({len(text)} caractères).")
                return None
            
            self.logger.debug(f"Texte extrait pour {file_name}: {len(text)} caractères")
            
            # Obtenir les informations structurées
            info = self.llm_client.get_structured_info(text)
            
            if not info:
                self.logger.error(f"Échec de l'extraction des informations structurées de {file_name}")
                return None
            
            # Ajouter des métadonnées
            info["metadata"] = {
                "fichier_source": file_name,
                "taille_texte": len(text),
                "date_traitement": time.strftime("%Y-%m-%d %H:%M:%S"),
                "modele_utilise": self.config.model_name
            }
            
            # Sauvegarder le résultat
            return self.save_result(file_name, info)
            
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de {file_name}: {e}", exc_info=True)
            return None
    
    def save_result(self, file_name: str, data: Dict[str, Any]) -> Path:
        """Sauvegarde les résultats dans un fichier JSON."""
        # Créer le dossier de sortie s'il n'existe pas
        self.config.output_folder.mkdir(parents=True, exist_ok=True)
        
        # Déterminer le nom du fichier de sortie
        name_without_ext = Path(file_name).stem
        output_file = self.config.output_folder / f"{name_without_ext}.json"
        
        # Écrire les données
        with open(output_file, 'w', encoding='utf-8') as f_out:
            json.dump(data, f_out, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Résultat sauvegardé dans {output_file}")
        return output_file
    
    def get_file_list(self, extension: str = '.pdf') -> List[str]:
        """Obtient la liste des fichiers à traiter."""
        if not self.config.folder_path.exists():
            self.logger.error(f"Le dossier {self.config.folder_path} n'existe pas.")
            return []
        
        return [f for f in os.listdir(self.config.folder_path) if f.lower().endswith(extension)]
    
    def process_all_files(self) -> List[Path]:
        """Traite tous les fichiers CV."""
        files = self.get_file_list()
        
        if not files:
            self.logger.info("Aucun fichier PDF trouvé.")
            return []
        
        self.logger.info(f"{len(files)} fichiers trouvés. Lancement du traitement...")
        
        # Process files sequentially for better debugging
        results = []
        for file_name in tqdm(files, desc="Traitement des CV"):
            result = self.process_file(file_name)
            results.append(result)
            # Small delay between files to avoid overwhelming the LLM
            time.sleep(1)
        
        # Filtrer les résultats None
        processed_files = [res for res in results if res is not None]
        
        self.logger.info(f"{len(processed_files)} fichiers traités avec succès sur {len(files)}.")
        return processed_files


def main():
    """Fonction principale."""
    # Configuration par défaut
    DEFAULT_CONFIG = {
        "folder_path": Path(r"C:\analyse_cv_LLM\Backend\data\cv_brut"),
        "output_folder": Path(r"C:\analyse_cv_LLM\Backend\data\dossier_feature"),
        "model_name": "llama3.2:3b",
        "max_workers": 2,
        "timeout_seconds": 120,
        "retry_count": 3,
        "max_text_length": 8000
    }
    
    # Configuration du logging
    logger = setup_logging()
    
    try:
        # Charger la configuration
        config = CVAnalyzerConfig.from_dict(DEFAULT_CONFIG)
        
        # Vérifier que le modèle est disponible
        try:
            ollama.show(config.model_name)
            logger.info(f"Modèle {config.model_name} disponible")
        except Exception as e:
            logger.error(f"Modèle {config.model_name} non disponible: {e}")
            return
        
        # Créer et exécuter le processeur
        processor = CVProcessor(config)
        processor.process_all_files()
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution: {e}", exc_info=True)


if __name__ == "__main__":
    main()
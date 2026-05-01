from flask import Flask, request, jsonify
from flask_cors import CORS
import fitz  # PyMuPDF
import ollama
import json
import re
import tempfile
import os
import logging
import time
import concurrent.futures
from typing import Dict, Optional, Any, Tuple, List
from pathlib import Path
from werkzeug.utils import secure_filename
from datetime import datetime
import traceback
import sys

# Fix encoding issues on Windows
if sys.platform.startswith('win'):
    import locale
    # Force UTF-8 encoding for logging on Windows
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

# Initialize Flask application
app = Flask(__name__)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
app.config['UPLOAD_EXTENSIONS'] = ['.pdf']
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Enable CORS for all routes with proper configuration
CORS(app, 
     origins=['*'], 
     allow_headers=['Content-Type', 'Authorization'], 
     methods=['GET', 'POST', 'OPTIONS'],
     supports_credentials=False)

# Configure logging with UTF-8 encoding
class UTF8StreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            # Replace problematic Unicode characters for Windows compatibility
            if sys.platform.startswith('win'):
                msg = msg.replace('✓', '[OK]').replace('⚠', '[WARNING]').replace('❌', '[ERROR]')
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        UTF8StreamHandler(),
        logging.FileHandler('cv_analyzer.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# LLM Configuration
LLM_CONFIG = {
    "model_name": "llama3.2:3b",
    "timeout_seconds": 600,
    "retry_count": 3,
    "max_text_length": 131072
}

# Catégories pour la classification des CV
CV_CATEGORIES = [
    "Développement Web",
    "Développement Mobile",
    "Data Science",
    "Intelligence Artificielle",
    "DevOps",
    "Cybersécurité",
    "Réseaux",
    "Administration Système",
    "Design UI/UX",
    "Marketing Digital",
    "Gestion de Projet",
    "Blockchain & Crypto",
    "IoT & Systèmes Embarqués",
    "Réalité Virtuelle/Augmentée",
    "Robotique & Automatisation",
    "Cloud Computing",
    "Big Data & Analytics",
    "Création de Contenu",
    "Photographie & Vidéo",
    "Animation & Motion Design",
    "Sound Design & Audio",
    "Community Management",
    "Ressources Humaines",
    "Formation & E-learning",
    "Consulting IT",
    "Business Development",
    "Operations & Supply Chain",
    "Qualité & Conformité",
    "Legal Tech & Juridique",
    "FinTech & Services Financiers",
    "HealthTech & Médical",
    "EdTech & Formation",
    "E-commerce & Retail",
    "Gaming & Divertissement",
    "Architecture d'Entreprise",
    "Innovation & R&D",
    "Transformation Digitale",
    "Freelance Multi-compétences",
    "Startup & Entrepreneuriat",
    "International & Export"
]

# Error handlers
@app.errorhandler(413)
def too_large(e):
    return jsonify({
        "error": "File too large",
        "message": "File size exceeds 50MB limit",
        "max_size": "50MB"
    }), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": ["/", "/analyze", "/match", "/health"]
    }), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({
        "error": "Internal server error",
        "message": "Something went wrong on our end"
    }), 500

@app.route('/')
def home():
    """Home endpoint with API documentation"""
    return jsonify({
        "status": "running",
        "service": "CV Analyzer API Enhanced",
        "version": "2.1.3",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "/analyze": {
                "method": "POST",
                "description": "Analyze a PDF CV/resume using LLM for extraction and classification",
                "content-type": "multipart/form-data",
                "parameters": {
                    "file": "PDF file (required, max 50MB)"
                },
                "example_curl": "curl -X POST -F 'file=@path/to/your/cv.pdf' http://localhost:5000/analyze"
            },
            "/match": {
                "method": "POST",
                "description": "Analyze CV against specific job offer and calculate compatibility score",
                "content-type": "multipart/form-data",
                "parameters": {
                    "file": "PDF file (required, max 50MB)",
                    "job_offer": "JSON object with job details (required)"
                },
                "example_curl": "curl -X POST -F 'file=@cv.pdf' -F 'job_offer={\"title\":\"Développeur Full Stack\", \"description\":\"...\"}' http://localhost:5000/match"
            },
            "/health": {
                "method": "GET",
                "description": "Check service health and component status"
            }
        },
        "configuration": {
            "llm_model": LLM_CONFIG["model_name"],
            "max_file_size": "50MB",
            "supported_formats": [".pdf"],
            "available_categories": CV_CATEGORIES
        }
    })

def extract_text_from_pdf(file_path: str) -> str:
    """Extract and clean text from a PDF file"""
    try:
        text = ""
        with fitz.open(file_path) as doc:
            logger.info(f"Processing PDF with {len(doc)} pages")
            
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                if page_text.strip():
                    text += f"\n--- Page {page_num + 1} ---\n{page_text}"
        
        if not text.strip():
            raise ValueError("PDF appears to be empty or contains only images")

        # Clean and normalize text
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s@.+\-:,;()\/\n]', ' ', text)
        text = text.strip()
        
        logger.info(f"Extracted {len(text)} characters from PDF")
        return text
        
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")

def create_cv_prompt(text: str) -> str:
    """Create a comprehensive prompt for the LLM to extract structured CV data"""
    truncated_text = text[:LLM_CONFIG['max_text_length']]
 
    return f"""
Tu es un assistant expert en analyse de CV. Analyse ce CV et extrais TOUTES les informations disponibles dans la structure JSON exacte suivante.


STRUCTURE JSON OBLIGATOIRE:
{{
  "score_total": {{
    "score": 0,
    "details_evaluation": {{
      "completude_informations": 0,
      "qualite_experiences": 0,
      "pertinence_competences": 0,
      "formation_adequation": 0,
      "presentation_structure": 0
    }},
    "commentaire_general": "",
    "points_forts": [],
    "points_amelioration": []
  }},
  "informations_personnelles": {{
    "nom_prenom": "",
    "email": "",
    "telephone": "",
    "adresse": "",
    "github": "",
    "linkedin": "",
    "portfolio": "",
    "site_web": ""
  }},
  "profil": "",
  "experiences_professionnelles": [
    {{
      "type": "",
      "poste": "",
      "entreprise": "",
      "date_debut": "",
      "date_fin": "",
      "duree": "",
      "lieu": "",
      "description": "",
      "competences_utilisees": [],
      "realisations": []
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
      "lieu": "",
      "mention": "",
      "description": "",
      "notes": ""
    }}
  ],
  "projets": [
    {{
      "titre": "",
      "type": "",
      "description": "",
      "technologies_utilisees": [],
      "date_debut": "",
      "date_fin": "",
      "lien": "",
      "github": "",
      "statut": ""
    }}
  ],
  "competences": {{
    "langages_programmation": [],
    "frameworks_bibliotheques": [],
    "outils_developpement": [],
    "bases_donnees": [],
    "methodologies": [],
    "cloud_devops": [],
    "systemes_exploitation": [],
    "design_multimedia": [],
    "gestion_projet": [],
    "autres": []
  }},
  "langues": [
    {{
      "langue": "",
      "niveau": "",
      "certification": ""
    }}
  ],
  "vie_associative": [
    {{
      "organisation": "",
      "role": "",
      "date_debut": "",
      "date_fin": "",
      "description": "",
      "competences_developpees": []
    }}
  ],
  "certifications": [
    {{
      "titre": "",
      "organisme": "",
      "date": "",
      "validite": "",
      "details": "",
      "lien": ""
    }}
  ],
  "soft_skills": [],
  "centres_interet": [],
  "publications": [
    {{
      "titre": "",
      "type": "",
      "date": "",
      "description": "",
      "lien": ""
    }}
  ],
  "prix_distinctions": [
    {{
      "titre": "",
      "organisme": "",
      "date": "",
      "description": ""
    }}
  ]
}}

CRITÈRES D'ÉVALUATION POUR LE SCORE (sur 100):
- Complétude des informations (20 points): Présence des informations essentielles
- Qualité des expériences (25 points): Pertinence, détail, progression
- Pertinence des compétences (20 points): Adéquation avec le profil, diversité
- Formation et qualifications (15 points): Niveau, pertinence, certifications
- Présentation et structure (20 points): Clarté, organisation, professionnalisme

TEXTE DU CV À ANALYSER:
{truncated_text}

Réponds UNIQUEMENT avec le JSON, sans texte supplémentaire:"""

def create_job_matching_prompt(cv_text: str, job_offer: Dict[str, Any]) -> str:
    """Create a prompt for matching CV against job offer"""
    truncated_text = cv_text[:LLM_CONFIG['max_text_length']]

    
    return f"""
Tu es un expert en recrutement. Analyse ce CV par rapport à l'offre d'emploi fournie et calcule un score de compatibilité détaillé.

OFFRE D'EMPLOI:
Titre: {job_offer.get('title', 'Non spécifié')}
Entreprise: {job_offer.get('company', 'Non spécifiée')}
Localisation: {job_offer.get('location', 'Non spécifiée')}
Type de contrat: {job_offer.get('contract_type', 'Non spécifié')}
Niveau d'expérience: {job_offer.get('experience_level', 'Non spécifié')}
Salaire: {job_offer.get('salary', 'Non spécifié')}

Description du poste:
{job_offer.get('description', 'Non fournie')}

Compétences requises:
{', '.join(job_offer.get('required_skills', []))}

Compétences souhaitées:
{', '.join(job_offer.get('preferred_skills', []))}

Qualifications requises:
{job_offer.get('qualifications', 'Non spécifiées')}

IMPORTANT: Réponds UNIQUEMENT avec un JSON dans cette structure exacte:
{{
  "score_compatibilite": {{
    "score_global": 0,
    "scores_detailles": {{
      "competences_techniques": {{
        "score": 0,
        "details": "",
        "competences_correspondantes": [],
        "competences_manquantes": []
      }},
      "experience_professionnelle": {{
        "score": 0,
        "details": "",
        "experiences_pertinentes": [],
        "niveau_adequation": ""
      }},
      "formation_qualifications": {{
        "score": 0,
        "details": "",
        "formations_pertinentes": [],
        "certifications_pertinentes": []
      }},
      "soft_skills": {{
        "score": 0,
        "details": "",
        "soft_skills_identifiees": []
      }},
      "localisation_mobilite": {{
        "score": 0,
        "details": "",
        "compatibilite_geographique": ""
      }}
    }}
  }},
  "analyse_detaillee": {{
    "points_forts_candidature": [],
    "points_faibles_candidature": [],
    "recommandations_candidat": [],
    "recommandations_recruteur": []
  }},
  "decision_recommandee": {{
    "recommandation": "",
    "confiance": 0.0,
    "prochaines_etapes": []
  }},
  "questions_entretien_suggerees": []
}}

CRITÈRES DE NOTATION (sur 100):
- Compétences techniques (30 points): Correspondance avec les compétences requises/souhaitées
- Expérience professionnelle (25 points): Pertinence et niveau d'expérience
- Formation et qualifications (20 points): Adéquation du niveau d'études et certifications
- Soft skills (15 points): Compétences transversales identifiées
- Localisation et mobilité (10 points): Compatibilité géographique

RECOMMANDATIONS POSSIBLES:
- "Candidat excellent - Recommandé fortement"
- "Candidat très bon - Recommandé"
- "Candidat moyen - À évaluer"
- "Candidat faible - Non recommandé"
- "Candidat inadéquat - Rejeté"

TEXTE DU CV À ANALYSER:
{truncated_text}

Réponds UNIQUEMENT avec le JSON demandé, sans texte supplémentaire:"""

def create_classification_prompt(text: str) -> str:
    """Create a prompt for the LLM to classify the CV into a category"""
    truncated_text = text[:LLM_CONFIG['max_text_length']]
    categories = ", ".join(CV_CATEGORIES)
    
    return f"""
Tu es un expert en recrutement et en analyse de CV. Analyse ce CV et classe-le dans UNE SEULE des catégories suivantes:
{categories}

Réponds UNIQUEMENT avec un objet JSON contenant:
1. La catégorie choisie (exactement comme écrite dans la liste)
2. Un niveau de confiance entre 0 et 1
3. Une justification brève de ton choix

Format JSON attendu:
{{
  "categorie": "Nom de la catégorie",
  "confiance": 0.XX,
  "justification": "Brève explication de ton choix"
}}

TEXTE DU CV À ANALYSER:
{truncated_text}

Réponds UNIQUEMENT avec le JSON demandé, sans texte supplémentaire:"""

def analyze_with_llm(text: str) -> Optional[Dict[str, Any]]:
    """Send CV text to LLM for analysis with comprehensive error handling"""
    prompt = create_cv_prompt(text)
    
    for attempt in range(LLM_CONFIG["retry_count"]):
        try:
            logger.info(f"LLM analysis attempt {attempt + 1}/{LLM_CONFIG['retry_count']}")
            
            start_time = time.time()
            
            response = ollama.chat(
                model=LLM_CONFIG["model_name"],
                messages=[{"role": "user", "content": prompt}],
                options={
                    "num_predict":  131072,
                    "temperature": 0.1,
                    "top_p": 0.9
                }
            )
            
            processing_time = time.time() - start_time
            logger.info(f"LLM response received in {processing_time:.2f} seconds")
            
            content = response.get("message", {}).get("content", "")
            
            if not content:
                raise ValueError("Empty response from LLM")
            
            # Clean the response - remove markdown code blocks if present
            content = re.sub(r'^```json\s*', '', content.strip())
            content = re.sub(r'\s*```$', '', content.strip())
            
            # Try to find and extract JSON if the response isn't pure JSON
            if not content.strip().startswith('{'):
                json_match = re.search(r'(\{[\s\S]*\})', content)
                if json_match:
                    content = json_match.group(1)
                else:
                    raise ValueError("No valid JSON found in LLM response")
            
            # Parse and validate JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed: {e}")
                logger.error(f"Content: {content[:500]}...")
                raise
            
            # Validate structure
            if not isinstance(data, dict):
                raise ValueError("Response is not a JSON object")
                
            required_keys = ["informations_personnelles", "competences", "formation", "score_total"]
            missing_keys = [key for key in required_keys if key not in data]
            if missing_keys:
                logger.warning(f"Missing keys in response: {missing_keys}")
            
            # Validate score structure
            if "score_total" in data:
                score_data = data["score_total"]
                if not isinstance(score_data.get("score"), (int, float)) or not (0 <= score_data.get("score", 0) <= 100):
                    logger.warning(f"Invalid score value: {score_data.get('score')}")
                    if "score_total" not in data:
                        data["score_total"] = {}
                    data["score_total"]["score"] = 50  # Default score
            
            logger.info("LLM analysis completed successfully")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error on attempt {attempt + 1}: {e}")
            if attempt < LLM_CONFIG["retry_count"] - 1:
                time.sleep(2)
            
        except Exception as e:
            logger.error(f"LLM error on attempt {attempt + 1}: {e}")
            if attempt < LLM_CONFIG["retry_count"] - 1:
                time.sleep(2)
    
    logger.error("All LLM attempts failed")
    return None

def match_with_llm(cv_text: str, job_offer: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Match CV against job offer using LLM"""
    prompt = create_job_matching_prompt(cv_text, job_offer)
    
    for attempt in range(LLM_CONFIG["retry_count"]):
        try:
            logger.info(f"LLM job matching attempt {attempt + 1}/{LLM_CONFIG['retry_count']}")
            
            start_time = time.time()
            
            response = ollama.chat(
                model=LLM_CONFIG["model_name"],
                messages=[{"role": "user", "content": prompt}],
                options={
                    "num_predict":  131072,
                    "temperature": 0.1,
                    "top_p": 0.9
                }
            )
            
            processing_time = time.time() - start_time
            logger.info(f"LLM job matching response received in {processing_time:.2f} seconds")
            
            content = response.get("message", {}).get("content", "")
            
            if not content:
                raise ValueError("Empty response from LLM")
            
            # Clean the response
            content = re.sub(r'^```json\s*', '', content.strip())
            content = re.sub(r'\s*```$', '', content.strip())
            
            # Try to find and extract JSON
            if not content.strip().startswith('{'):
                json_match = re.search(r'(\{[\s\S]*\})', content)
                if json_match:
                    content = json_match.group(1)
                else:
                    raise ValueError("No valid JSON found in LLM job matching response")
            
            # Parse and validate JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed for job matching: {e}")
                logger.error(f"Content: {content[:500]}...")
                raise
            
            # Validate structure
            if not isinstance(data, dict) or "score_compatibilite" not in data:
                raise ValueError("Invalid job matching response structure")
            
            # Validate score
            score = data.get("score_compatibilite", {}).get("score_global", 0)
            if not isinstance(score, (int, float)) or not (0 <= score <= 100):
                logger.warning(f"Invalid compatibility score: {score}")
                data["score_compatibilite"]["score_global"] = 50  # Default score
            
            logger.info(f"Job matching completed successfully with score: {data.get('score_compatibilite', {}).get('score_global', 'N/A')}")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error on job matching attempt {attempt + 1}: {e}")
            if attempt < LLM_CONFIG["retry_count"] - 1:
                time.sleep(2)
            
        except Exception as e:
            logger.error(f"LLM job matching error on attempt {attempt + 1}: {e}")
            if attempt < LLM_CONFIG["retry_count"] - 1:
                time.sleep(2)
    
    logger.error("All LLM job matching attempts failed")
    return None

def classify_with_llm(text: str) -> Optional[Dict[str, Any]]:
    """Classify CV text using the LLM"""
    prompt = create_classification_prompt(text)
    
    for attempt in range(LLM_CONFIG["retry_count"]):
        try:
            logger.info(f"LLM classification attempt {attempt + 1}/{LLM_CONFIG['retry_count']}")
            
            start_time = time.time()
            
            response = ollama.chat(
                model=LLM_CONFIG["model_name"],
                messages=[{"role": "user", "content": prompt}],
                options={
                    "num_predict":  131072,
                    "temperature": 0.2,
                    "top_p": 0.9
                }
            )
            
            processing_time = time.time() - start_time
            logger.info(f"LLM classification response received in {processing_time:.2f} seconds")
            
            content = response.get("message", {}).get("content", "")
            
            if not content:
                raise ValueError("Empty response from LLM")
            
            # Clean the response
            content = re.sub(r'^```json\s*', '', content.strip())
            content = re.sub(r'\s*```$', '', content.strip())
            
            # Try to find and extract JSON
            if not content.strip().startswith('{'):
                json_match = re.search(r'(\{[\s\S]*\})', content)
                if json_match:
                    content = json_match.group(1)
                else:
                    raise ValueError("No valid JSON found in LLM classification response")
            
            # Parse and validate JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed for classification: {e}")
                logger.error(f"Content: {content[:500]}...")
                raise
            
            # Validate structure
            if not isinstance(data, dict) or "categorie" not in data:
                raise ValueError("Invalid classification response structure")
            
            # Ensure the category is one of the predefined categories
            if data.get("categorie") not in CV_CATEGORIES:
                closest_match = min(CV_CATEGORIES, key=lambda x: abs(len(x) - len(data.get("categorie", ""))))
                logger.warning(f"Category '{data.get('categorie')}' not in predefined list, using closest match: '{closest_match}'")
                data["categorie"] = closest_match
            
            logger.info(f"Classification completed: {data.get('categorie')} (confidence: {data.get('confiance', 'N/A')})")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error on classification attempt {attempt + 1}: {e}")
            if attempt < LLM_CONFIG["retry_count"] - 1:
                time.sleep(2)
            
        except Exception as e:
            logger.error(f"LLM classification error on attempt {attempt + 1}: {e}")
            if attempt < LLM_CONFIG["retry_count"] - 1:
                time.sleep(2)
    
    logger.error("All LLM classification attempts failed")
    return None

def validate_pdf_file(file) -> Tuple[bool, str]:
    """Validate uploaded PDF file with enhanced checks and debugging"""
    logger.info("Starting file validation...")
    
    # Check if file exists
    if not file:
        logger.error("No file object provided")
        return False, "No file provided in request"
    
    # Log file object attributes for debugging
    logger.info(f"File object type: {type(file)}")
    logger.info(f"File object attributes: {dir(file)}")
    
    # Check if filename exists
    if not hasattr(file, 'filename'):
        logger.error("File object has no filename attribute")
        return False, "Invalid file object - no filename attribute"
    
    if file.filename is None:
        logger.error("Filename is None")
        return False, "No filename provided"
    
    if not file.filename or not file.filename.strip():
        logger.error(f"Empty filename: '{file.filename}'")
        return False, "Empty filename provided"
    
    logger.info(f"Filename: {file.filename}")
    
    # Check file extension
    file_ext = os.path.splitext(file.filename.lower())[1]
    logger.info(f"File extension: '{file_ext}'")
    
    if file_ext not in app.config['UPLOAD_EXTENSIONS']:
        logger.error(f"Invalid file extension: {file_ext}")
        return False, f"Invalid file type. Only PDF files are accepted, got: {file_ext or 'no extension'}"
    
    # Check if file has content
    try:
        # Save current position
        current_pos = file.tell() if hasattr(file, 'tell') else 0
        
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(current_pos)  # Reset file pointer to original position
        
        logger.info(f"File size: {file_size} bytes")
        
        if file_size == 0:
            logger.error("File is empty")
            return False, "File is empty"
        
        max_size = app.config['MAX_CONTENT_LENGTH']
        if file_size > max_size:
            logger.error(f"File too large: {file_size} > {max_size}")
            return False, f"File too large. Maximum size: {max_size/1024/1024:.1f}MB, got: {file_size/1024/1024:.1f}MB"
            
    except Exception as e:
        logger.error(f"Error checking file size: {str(e)}")
        return False, f"Error checking file size: {str(e)}"
    
    logger.info("File validation successful")
    return True, "Valid file"

def validate_job_offer(job_offer_str: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate and parse job offer JSON"""
    try:
        job_offer = json.loads(job_offer_str)
        
        if not isinstance(job_offer, dict):
            return False, "Job offer must be a JSON object", {}
        
        # Check required fields
        required_fields = ['title', 'description']
        missing_fields = [field for field in required_fields if not job_offer.get(field, '').strip()]
        
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}", {}
        
        # Set default values for optional fields
        defaults = {
            'company': '',
            'location': '',
            'contract_type': '',
            'experience_level': '',
            'salary': '',
            'required_skills': [],
            'preferred_skills': [],
            'qualifications': ''
        }
        
        for key, default_value in defaults.items():
            if key not in job_offer:
                job_offer[key] = default_value
        
        # Ensure skills are lists
        if not isinstance(job_offer.get('required_skills'), list):
            job_offer['required_skills'] = []
        if not isinstance(job_offer.get('preferred_skills'), list):
            job_offer['preferred_skills'] = []
        
        return True, "Valid job offer", job_offer
        
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON format: {str(e)}", {}
    except Exception as e:
        return False, f"Error validating job offer: {str(e)}", {}

@app.route('/analyze', methods=['POST', 'OPTIONS'])
def analyze_cv():
    """Analyze a CV/resume PDF file using LLM with comprehensive error handling"""
    
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response
    
    start_time = time.time()
    temp_file_path = None
    
    try:
        logger.info("Starting CV analysis request")
        
        # Check if file is in request
        if 'file' not in request.files:
            logger.error("No file part in request")
            return jsonify({
                "error": "No file provided",
                "message": "Please provide a PDF file in the 'file' field",
                "status": "error"
            }), 400
        
        file = request.files['file']
        logger.info(f"Received file: {getattr(file, 'filename', 'unknown')}")
        
        # Validate file
        is_valid, validation_message = validate_pdf_file(file)
        if not is_valid:
            logger.error(f"File validation failed: {validation_message}")
            return jsonify({
                "error": "Invalid file",
                "message": validation_message,
                "status": "error"
            }), 400
        
        # Create temporary file with secure filename
        secure_name = secure_filename(file.filename)
        temp_file_path = os.path.join(tempfile.gettempdir(), f"cv_temp_{int(time.time())}_{secure_name}")
        
        try:
            file.save(temp_file_path)
            logger.info(f"File saved temporarily to: {temp_file_path}")
        except Exception as e:
            logger.error(f"Failed to save temporary file: {e}")
            return jsonify({
                "error": "File processing error",
                "message": f"Failed to process uploaded file: {str(e)}",
                "status": "error"
            }), 500
        
        # Extract text from PDF
        try:
            text = extract_text_from_pdf(temp_file_path)
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            return jsonify({
                "error": "PDF processing error",
                "message": f"Failed to extract text from PDF: {str(e)}",
                "status": "error"
            }), 422
        
        # Analyze with LLM and classify simultaneously
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_analysis = executor.submit(analyze_with_llm, text)
            future_classification = executor.submit(classify_with_llm, text)
            
            # Get analysis results
            analysis_result = future_analysis.result()
            classification_result = future_classification.result()
        
        # Check if analysis failed
        if analysis_result is None:
            logger.error("LLM analysis failed completely")
            return jsonify({
                "error": "Analysis failed",
                "message": "Failed to analyze CV with AI. Please try again or contact support.",
                "status": "error",
                "suggestions": [
                    "Ensure the PDF contains readable text (not just images)",
                    "Try with a different PDF file",
                    "Check if the PDF is not corrupted"
                ]
            }), 500
        
        # Add classification to result if successful
        if classification_result:
            analysis_result['classification'] = classification_result
        else:
            logger.warning("Classification failed, using default")
            analysis_result['classification'] = {
                "categorie": "Freelance Multi-compétences",
                "confiance": 0.3,
                "justification": "Classification automatique échouée"
            }
        
        # Add metadata
        analysis_result['metadata'] = {
            "filename": file.filename,
            "processing_time_seconds": round(time.time() - start_time, 2),
            "text_length": len(text),
            "analysis_timestamp": datetime.now().isoformat(),
            "model_used": LLM_CONFIG["model_name"],
            "version": "2.1.3"
        }
        
        # Add status
        analysis_result['status'] = 'success'
        
        logger.info(f"CV analysis completed successfully in {time.time() - start_time:.2f} seconds")
        
        return jsonify(analysis_result)
        
    except Exception as e:
        logger.error(f"Unexpected error in analyze_cv: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Internal server error",
            "message": f"An unexpected error occurred: {str(e)}",
            "status": "error"
        }), 500
        
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"Temporary file cleaned up: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file: {e}")

@app.route('/match', methods=['POST', 'OPTIONS'])
def match_cv():
    """Match a CV against a specific job offer with detailed compatibility analysis"""
    
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response
    
    start_time = time.time()
    temp_file_path = None
    
    try:
        logger.info("Starting CV-Job matching request")
        
        # Check if file is in request
        if 'file' not in request.files:
            logger.error("No file part in request")
            return jsonify({
                "error": "No file provided",
                "message": "Please provide a PDF file in the 'file' field",
                "status": "error"
            }), 400
        
        # Check if job offer is in request
        if 'job_offer' not in request.form:
            logger.error("No job offer in request")
            return jsonify({
                "error": "No job offer provided",
                "message": "Please provide job offer details in the 'job_offer' field as JSON",
                "status": "error"
            }), 400
        
        file = request.files['file']
        job_offer_str = request.form['job_offer']
        
        logger.info(f"Received file: {getattr(file, 'filename', 'unknown')}")
        
        # Validate file
        is_valid, validation_message = validate_pdf_file(file)
        if not is_valid:
            logger.error(f"File validation failed: {validation_message}")
            return jsonify({
                "error": "Invalid file",
                "message": validation_message,
                "status": "error"
            }), 400
        
        # Validate job offer
        is_valid_job, job_validation_message, job_offer = validate_job_offer(job_offer_str)
        if not is_valid_job:
            logger.error(f"Job offer validation failed: {job_validation_message}")
            return jsonify({
                "error": "Invalid job offer",
                "message": job_validation_message,
                "status": "error"
            }), 400
        
        # Create temporary file
        secure_name = secure_filename(file.filename)
        temp_file_path = os.path.join(tempfile.gettempdir(), f"cv_match_{int(time.time())}_{secure_name}")
        
        try:
            file.save(temp_file_path)
            logger.info(f"File saved temporarily to: {temp_file_path}")
        except Exception as e:
            logger.error(f"Failed to save temporary file: {e}")
            return jsonify({
                "error": "File processing error",
                "message": f"Failed to process uploaded file: {str(e)}",
                "status": "error"
            }), 500
        
        # Extract text from PDF
        try:
            text = extract_text_from_pdf(temp_file_path)
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            return jsonify({
                "error": "PDF processing error",
                "message": f"Failed to extract text from PDF: {str(e)}",
                "status": "error"
            }), 422
        
        # Perform matching analysis with LLM
        matching_result = match_with_llm(text, job_offer)
        
        if matching_result is None:
            logger.error("LLM job matching failed completely")
            # Return error but include the expected key for the frontend
            return jsonify({
                "matching_score": None, # Include the key even on failure
                "error": "Matching analysis failed",
                "message": "Failed to analyze CV-job compatibility with AI. Please try again or contact support.",
                "status": "error"
            }), 500
        
        # Add job offer details to result
        matching_result['job_offer'] = job_offer
        
        # Add metadata
        matching_result['metadata'] = {
            "filename": file.filename,
            "processing_time_seconds": round(time.time() - start_time, 2),
            "text_length": len(text),
            "analysis_timestamp": datetime.now().isoformat(),
            "model_used": LLM_CONFIG["model_name"],
            "version": "2.1.3"
        }
        
        # Add status
        matching_result['status'] = 'success'
        
        # Wrap the result under the key expected by the frontend
        response_data = {"matching_score": matching_result}
        
        logger.info(f"CV-Job matching completed successfully in {time.time() - start_time:.2f} seconds")
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in match_cv: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Internal server error",
            "message": f"An unexpected error occurred: {str(e)}",
            "status": "error"
        }), 500
        
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"Temporary file cleaned up: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file: {e}")

@app.route('/health', methods=['GET'])
def health_check():
    """Comprehensive health check endpoint with component status"""
    try:
        start_time = time.time()
        
        # Check LLM availability
        llm_status = "unknown"
        llm_error = None
        try:
            test_response = ollama.chat(
                model=LLM_CONFIG["model_name"],
                messages=[{"role": "user", "content": "Hello"}],
                options={"num_predict": 10}
            )
            if test_response and test_response.get("message", {}).get("content"):
                llm_status = "healthy"
            else:
                llm_status = "unhealthy"
                llm_error = "Empty response from LLM"
        except Exception as e:
            llm_status = "unhealthy"
            llm_error = str(e)
        
        # Check disk space in temp directory
        temp_dir = tempfile.gettempdir()
        disk_space = "unknown"
        try:
            if hasattr(os, 'statvfs'):  # Unix/Linux
                statvfs = os.statvfs(temp_dir)
                free_space = statvfs.f_frsize * statvfs.f_bavail
                disk_space = f"{free_space / (1024**3):.2f} GB available"
            elif hasattr(os, 'GetDiskFreeSpaceEx'):  # Windows
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(temp_dir),
                    ctypes.pointer(free_bytes),
                    None,
                    None
                )
                disk_space = f"{free_bytes.value / (1024**3):.2f} GB available"
        except Exception as e:
            disk_space = f"Error checking disk space: {str(e)}"
        
        response_time = time.time() - start_time
        
        health_data = {
            "status": "healthy" if llm_status == "healthy" else "degraded",
            "timestamp": datetime.now().isoformat(),
            "service": "CV Analyzer API Enhanced",
            "version": "2.1.3",
            "uptime": f"Available since service start",
            "response_time_ms": round(response_time * 1000, 2),
            "components": {
                "api": {
                    "status": "healthy",
                    "message": "API endpoints responding"
                },
                "llm": {
                    "status": llm_status,
                    "model": LLM_CONFIG["model_name"],
                    "message": llm_error if llm_error else "LLM responding normally"
                },
                "pdf_processor": {
                    "status": "healthy",
                    "message": "PyMuPDF ready for PDF processing"
                },
                "file_system": {
                    "status": "healthy",
                    "temp_directory": temp_dir,
                    "disk_space": disk_space
                }
            },
            "configuration": {
                "max_file_size": f"{app.config['MAX_CONTENT_LENGTH'] / (1024*1024):.0f}MB",
                "supported_formats": app.config['UPLOAD_EXTENSIONS'],
                "llm_timeout": f"{LLM_CONFIG['timeout_seconds']}s",
                "max_text_length": LLM_CONFIG['max_text_length']
            },
            "endpoints": {
                "/analyze": "CV analysis endpoint",
                "/match": "CV-job matching endpoint",
                "/health": "Health check endpoint"
            }
        }
        
        status_code = 200 if llm_status == "healthy" else 503
        return jsonify(health_data), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 503

# Application startup
if __name__ == '__main__':
    try:
        logger.info("=" * 60)
        logger.info("STARTING CV ANALYZER API ENHANCED v2.1.3")
        logger.info("=" * 60)
        logger.info(f"LLM Model: {LLM_CONFIG['model_name']}")
        logger.info(f"Max file size: {app.config['MAX_CONTENT_LENGTH'] / (1024*1024):.0f}MB")
        logger.info(f"Supported formats: {app.config['UPLOAD_EXTENSIONS']}")
        logger.info(f"Available categories: {len(CV_CATEGORIES)} categories")
        
        # Test LLM connection on startup
        try:
            logger.info("Testing LLM connection...")
            test_response = ollama.chat(
                model=LLM_CONFIG["model_name"],
                messages=[{"role": "user", "content": "Test"}],
                options={"num_predict": 5}
            )
            if test_response:
                logger.info("✓ LLM connection successful")
            else:
                logger.warning("⚠ LLM connection test returned empty response")
        except Exception as e:
            logger.error(f"❌ LLM connection failed: {e}")
            logger.error("Please ensure Ollama is running and the model is available")
        
        logger.info("Server starting on http://localhost:5000")
        logger.info("Available endpoints:")
        logger.info("  GET  /         - API documentation")
        logger.info("  POST /analyze  - Analyze CV")
        logger.info("  POST /match    - Match CV with job offer")
        logger.info("  GET  /health   - Health check")
        logger.info("=" * 60)
        
        # Start the Flask application
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,  # Set to False in production
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

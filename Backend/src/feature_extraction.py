import os
import re
import json
import spacy
from pdfminer.high_level import extract_text
import fitz  # PyMuPDF

# Chargement des modèles spaCy
nlp_fr = spacy.load("fr_core_news_sm")
nlp_en = spacy.load("en_core_web_sm")

# Compétences communes à rechercher
common_skills = [
    "Python", "Java", "C++", "Machine Learning", "Deep Learning",
    "Data Analysis", "SQL", "NoSQL", "Pandas", "Numpy", "Django", "Flask",
    "React", "JavaScript", "HTML", "CSS", "TensorFlow", "Keras",
    "Scikit-learn", "Power BI", "Tableau", "Excel", "Spark", "Hadoop", "Hive", "Pig", "LLM"
]

# ----------- UTILS -----------

def clean_text(text):
    """Nettoie le texte pour supprimer les caractères indésirables et les espaces superflus."""
    return re.sub(r'\s+', ' ', text.replace('\xa0', ' ')).strip()

def extract_text_from_pdf(pdf_path):
    """Extrait le texte brut d'un fichier PDF à l'aide de fitz (PyMuPDF)."""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text("text")
        return text
    except Exception as e:
        print(f"Erreur lors de l'extraction du texte PDF: {str(e)}")
        return ""

def detect_language(text):
    """Détecte la langue du texte (simplifié)."""
    if not text:
        return "en"  # Default to English if empty text
    
    french_words = ['le', 'la', 'les', 'un', 'une', 'des']
    english_words = ['the', 'a', 'an', 'is', 'are']
    
    fr_count = sum(1 for word in french_words if word in text.lower())
    en_count = sum(1 for word in english_words if word in text.lower())
    
    return "fr" if fr_count > en_count else "en"

# ----------- EXTRACTION CONTACT -----------

def extract_email(text):
    """Extrait l'email d'un texte donné."""
    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    return emails[0] if emails else None

def extract_phone_number(text):
    """Extrait le numéro de téléphone d'un texte donné."""
    patterns = [
        r'(\+216[\s\-\.]?\d{2}[\s\-\.]?\d{3}[\s\-\.]?\d{3})',  # Format Tunisien international
        r'(\b\d{8}\b)',  # Format Tunisien local
        r'(\(\+\d+\)\s*\d+)',  # Format international général
        r'(\d{3}[\s\-\.]?\d{3}[\s\-\.]?\d{4})'  # Format US/Canada
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            return matches[0].strip()
    
    return None

def extract_links(text):
    """Extrait les liens LinkedIn, GitHub et Portfolio depuis un texte."""
    links = re.findall(r'(https?://[^\s\)\]]+)', text)
    return {
        "linkedin": next((l for l in links if "linkedin.com" in l.lower()), None),
        "github": next((l for l in links if "github.com" in l.lower()), None),
        "portfolio": next((l for l in links if "port" in l.lower() or "folio" in l.lower()), None)
    }

# ----------- EXTRACTION DES SECTIONS -----------

def extract_name(text):
    """Extrait le nom du candidat à partir du texte du CV."""
    if not text:
        return None
        
    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
    
    # Recherche plus spécifique pour les noms en majuscules
    for i in range(min(3, len(lines))):
        line = lines[i]
        if line == line.upper() and len(line.split()) <= 4:
            return line
    
    # Utiliser NER pour identifier les noms de personnes
    potential_names = []
    for i in range(min(5, len(lines))):  # Examiner les 5 premières lignes
        line = lines[i]
        lang = detect_language(line)
        nlp = nlp_fr if lang == "fr" else nlp_en
        doc = nlp(line)
        
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                potential_names.append(ent.text)
    
    if potential_names:
        return potential_names[0]
    
    return lines[0] if lines else None

def extract_job_title(text):
    """Extrait le titre du poste à partir du texte du CV."""
    if not text:
        return None
        
    job_keywords = [
        "Engineer", "Data Scientist", "Manager", "Consultant", "Developer",
        "Analyst", "Intern", "Technician", "Supervisor", "Coordinator",
        "Architect", "Administrator", "Director", "Assistant", "Specialist",
        "Officer", "Trainer", "Executive", "CEO", "CTO", "Founder", "Étudiant",
        # Versions françaises
        "Ingénieur", "Développeur", "Analyste", "Stagiaire", "Technicien", 
        "Superviseur", "Coordinateur", "Architecte", "Administrateur", 
        "Directeur", "Assistant", "Spécialiste", "Officier", "Formateur"
    ]
    
    lines = text.split('\n')
    
    # Chercher dans les 10 premières lignes
    for i in range(min(10, len(lines))):
        line = lines[i].strip()
        
        if "~" in line:
            parts = line.split("~")
            return parts[1].strip()
        
        for title in job_keywords:
            if title.lower() in line.lower():
                pos = line.lower().find(title.lower())
                start = max(0, pos - 15)
                end = min(len(line), pos + len(title) + 15)
                return line[start:end].strip()
    
    if "data scientist" in text.lower():
        return "Data Scientist"
    
    return None

def extract_location(text):
    """Extrait la localisation du candidat."""
    if not text:
        return None
    
    if "tunisie" in text.lower():
        return "Tunisie"
    
    tunisian_cities = ["tunis", "sfax", "sousse", "monastir", "gabès", "bizerte", "ariana", "gafsa"]
    for city in tunisian_cities:
        if city in text.lower():
            return city.capitalize()
    
    lang = detect_language(text)
    nlp = nlp_fr if lang == "fr" else nlp_en
    doc = nlp(text)
    
    for ent in doc.ents:
        if ent.label_ == "GPE":
            return ent.text
    
    return None

def extract_summary(text):
    """Extrait le résumé ou la synthèse du profil."""
    if not text:
        return None

    summary_patterns = [
        r'SUMMARY\s*(.*?)(?=PROJECTS|SKILLS|EDUCATION|EXPERIENCE|LANGUAGES|\Z)',
        r'PROFILE\s*(.*?)(?=PROJECTS|SKILLS|EDUCATION|EXPERIENCE|LANGUAGES|\Z)',
        r'ABOUT\s*(.*?)(?=PROJECTS|SKILLS|EDUCATION|EXPERIENCE|LANGUAGES|\Z)'
    ]

    for pattern in summary_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return clean_text(match.group(1).strip())

    return None


def extract_skills_section(text):
    """Extrait la section compétences du CV."""
    if not text:
        return None
        
    skills_patterns = [
        r'SKILLS\s*(.*?)(?=PROJECTS|EDUCATION|EXPERIENCE|LANGUAGES|\Z)',
        r'COMPETENCES\s*(.*?)(?=PROJECTS|EDUCATION|EXPERIENCE|LANGUAGES|\Z)',
        r'TECHNICAL SKILLS\s*(.*?)(?=PROJECTS|EDUCATION|EXPERIENCE|LANGUAGES|\Z)'
    ]
    
    for pattern in skills_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            skills_text = match.group(1).strip()
            skills_list = re.findall(r'[A-Za-zÀ-ÖØ-öø-ÿ\s\+\#]+', skills_text)
            
            skills_cleaned = []
            for skill in skills_list:
                skill = skill.strip()
                if skill and len(skill) > 1:
                    skills_cleaned.append(skill)
            
            detected_skills = [skill for skill in common_skills 
                             if skill.lower() in text.lower() or skill in text]
            
            all_skills = list(set(skills_cleaned + detected_skills))
            return [s for s in all_skills if s and len(s.strip()) > 1]
    
    return None

def extract_projects(text):
    """Extrait les projets mentionnés dans le CV."""
    if not text:
        return []
    
    projects = []
    
    project_patterns = [
        r'Technology My project (\d+)\s*:(.+?)(?=Technology My project \d+|EDUCATION|EXPERIENCE|LANGUAGES|\Z)',
        r'PROJECT\s*(.*?)(?=PROJECT|EDUCATION|EXPERIENCE|LANGUAGES|\Z)',
        r'PROJET\s*(.*?)(?=PROJET|EDUCATION|EXPERIENCE|LANGUAGES|\Z)'
    ]
    
    for pattern in project_patterns:
        matches = re.finditer(pattern, text, re.DOTALL)
        for match in matches:
            project_num = match.group(1) if len(match.groups()) > 1 else "1"
            project_content = match.group(2 if len(match.groups()) > 1 else 1).strip()
            
            lines = project_content.split('\n', 1)
            title = lines[0].strip()
            description = lines[1].strip() if len(lines) > 1 else ""
            
            technologies = []
            for skill in common_skills:
                if skill.lower() in project_content.lower() or skill in project_content:
                    technologies.append(skill)
            
            projects.append({
                "number": project_num,
                "title": title,
                "description": description,
                "technologies": technologies
            })
    
    return projects

def extract_languages(text):
    """Extrait les langues mentionnées dans le CV."""
    if not text:
        return []
        
    lang_patterns = [
        r'LANGUAGES\s*(.*?)(?=\Z)',
        r'LANGUE\s*(.*?)(?=\Z)',
        r'LANGUES\s*(.*?)(?=\Z)'
    ]
    
    for pattern in lang_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            lang_text = match.group(1).strip()
            languages = re.split(r'[,\n]', lang_text)
            return [lang.strip() for lang in languages if lang.strip()]
    
    known_langs = ['English', 'French', 'Arabic', 'Spanish', 'German', 'Mandarin', 
                  "Français", "Anglais", "Arabe", "Espagnol", "Allemand", "Chinois"]
    
    detected_langs = []
    for lang in known_langs:
        if lang.lower() in text.lower():
            detected_langs.append(lang)
    
    return detected_langs

def extract_experience(text):
    """Extrait et structure les expériences professionnelles."""
    if not text:
        return []
        
    experiences = []
    
    exp_section_patterns = [
        r'EXPERIENCE\s*(.*?)(?=LANGUAGES|\Z)',
        r'EXPERIENCES\s*(.*?)(?=LANGUAGES|\Z)',
        r'EXPERIENCE PROFESSIONNELLE\s*(.*?)(?=LANGUAGES|\Z)'
    ]
    
    exp_text = ""
    for pattern in exp_section_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            exp_text = match.group(1).strip()
            break
    
    if not exp_text:
        return []
    
    exp_patterns = [
        r'(\d{1,2}/\d{4}\s*–\s*\d{1,2}/\d{4}|\d{1,2}/\d{4}\s*–\s*\w+)\s*(.*?)(?=\d{1,2}/\d{4}|•|\Z)',
        r'(\d{4}\s*-\s*\d{4})\s*(.*?)(?=\d{4}\s*-\s*\d{4}|•|\Z)'
    ]
    
    for pattern in exp_patterns:
        matches = re.finditer(pattern, exp_text, re.DOTALL)
        for match in matches:
            date_range = match.group(1).strip()
            content = match.group(2).strip()
            
            lines = content.split('\n', 1)
            company_line = lines[0].strip()
            
            date_parts = re.split(r'\s*–\s*|\s*-\s*', date_range)
            start_date = date_parts[0].strip() if date_parts else None
            end_date = date_parts[1].strip() if len(date_parts) > 1 else None
            
            responsibilities_text = lines[1].strip() if len(lines) > 1 else ""
            responsibilities = [resp.strip() for resp in re.split(r'•|\n', responsibilities_text) if resp.strip()]
            
            position_type = None
            position_keywords = ["Stage", "CDD", "CDI", "PFE", "Alternance", "Mission", "Guichetier"]
            for keyword in position_keywords:
                if keyword.lower() in content.lower():
                    position_type = keyword
                    break
            
            technologies = []
            tech_pattern = r'Technologies utilisées\s*:(.+?)(?=\n\n|\Z)'
            tech_match = re.search(tech_pattern, content, re.DOTALL | re.IGNORECASE)
            if tech_match:
                tech_text = tech_match.group(1).strip()
                for skill in common_skills:
                    if skill.lower() in tech_text.lower() or skill in tech_text:
                        technologies.append(skill)
            
            company = None
            company_parts = company_line.split('-', 1)
            if len(company_parts) > 1:
                company = company_parts[0].strip()
            else:
                company_indicators = ["Société", "société", "SOCIÉTÉ", "S o c i é t é"]
                for indicator in company_indicators:
                    if indicator in company_line:
                        company_parts = company_line.split(indicator, 1)
                        if len(company_parts) > 1:
                            company = company_parts[1].strip()
                            break
            
            if not company:
                company = company_line
            
            if company:
                company = re.sub(r'\s*[\-\|]\s*', ' ', company).strip()
            
            # Extraction du sujet si présent
            sujet = None
            subject_pattern = r'Sujet\s*:(.+?)(?=\n\n|\Z)'
            subject_match = re.search(subject_pattern, content, re.DOTALL | re.IGNORECASE)
            if subject_match:
                sujet = subject_match.group(1).strip()
            
            try:
                experience = {
                    "Société": company,
                    "Type": position_type,
                    "Date Début": start_date,
                    "Date Fin": end_date,
                    "sujet": sujet,
                    "Technologies": technologies,
                    "Responsabilités": responsibilities
                }
                experiences.append(experience)
            except Exception as e:
                print(f"Erreur lors de la création de l'entrée d'expérience: {str(e)}")
                continue
    
    return experiences

def extract_education(text):
    """Extrait et structure les diplômes/formations à partir du CV."""
    if not text:
        return []
        
    education = []
    
    edu_section_patterns = [
        r'EDUCATION\s*(.*?)(?=EXPERIENCE|LANGUAGES|\Z)',
        r'FORMATION\s*(.*?)(?=EXPERIENCE|LANGUAGES|\Z)',
        r'ÉDUCATION\s*(.*?)(?=EXPERIENCE|LANGUAGES|\Z)'
    ]
    
    edu_text = ""
    for pattern in edu_section_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            edu_text = match.group(1).strip()
            break
    
    if not edu_text:
        return []
    
    edu_patterns = [
        r'(\d{4}\s*-\s*\d{4})\s*(.*?)(?=\d{4}\s*-\s*\d{4}|\Z)',
        r'(\d{4}\s*–\s*\d{4})\s*(.*?)(?=\d{4}\s*–\s*\d{4}|\Z)'
    ]
    
    for pattern in edu_patterns:
        matches = re.finditer(pattern, edu_text, re.DOTALL)
        for match in matches:
            date_range = match.group(1).strip()
            content = match.group(2).strip()
            
            lines = content.split('\n', 1)
            diploma = lines[0].strip()
            institution = lines[1].strip() if len(lines) > 1 else ""
            
            date_parts = re.split(r'\s*-\s*|\s*–\s*', date_range)
            start_date = date_parts[0].strip() if date_parts else None
            end_date = date_parts[1].strip() if len(date_parts) > 1 else None
            
            diploma_type = None
            diploma_keywords = {
                "master": "MASTER",
                "mastère": "MASTER",
                "licence": "LICENCE",
                "ingénieur": "INGÉNIEUR",
                "baccalauréat": "BACCALAURÉAT",
                "bac": "BACCALAURÉAT",
                "bts": "BTS",
                "dut": "DUT",
                "doctorat": "DOCTORAT",
                "formation": "FORMATION",
                "diplôme": "DIPLÔME"
            }
            
            for key, value in diploma_keywords.items():
                if key.lower() in diploma.lower():
                    diploma_type = value
                    break
            
            education.append({
                "Type": diploma_type,
                "Diplôme": diploma,
                "Institution": institution,
                "Date Début": start_date,
                "Date Fin": end_date
            })
    
    return education

# ----------- ANALYSE PRINCIPALE -----------

def analyze_resume(pdf_path):
    """Fonction principale pour analyser un CV et extraire les informations principales."""
    try:
        text = extract_text_from_pdf(pdf_path)
        if not text:
            print(f"Avertissement: PDF vide ou non lisible - {pdf_path}")
            return None
        
        # Extraction des entités nommées
        lang = detect_language(text)
        nlp = nlp_fr if lang == "fr" else nlp_en
        doc = nlp(text)
        
        entities = {
            "PERSON": [],
            "ORG": [],
            "GPE": [],
            "SKILL": []
        }
        
        for ent in doc.ents:
            if ent.label_ in entities:
                entities[ent.label_].append(ent.text)
        
        # Extraction des informations principales
        result = {
            "title": extract_job_title(text),
            "name": extract_name(text),
            "contact": {
                "email": extract_email(text),
                "phone": extract_phone_number(text),
                "linkedin": extract_links(text).get("linkedin"),
                "github": extract_links(text).get("github"),
                "portfolio": extract_links(text).get("portfolio"),
                "location": extract_location(text)
            },
            "summary": extract_summary(text),
            "experience": extract_experience(text),
            "education": extract_education(text),
            "projects": extract_projects(text),
            "skills": extract_skills_section(text) or entities["SKILL"],
            "languages": extract_languages(text),
            "entities": entities
        }
        
        return result
    
    except Exception as e:
        print(f"Erreur lors de l'analyse du CV {pdf_path}: {str(e)}")
        return None

# ----------- TRAITEMENT PAR LOT -----------

def process_all_resumes(input_folder, output_folder):
    """Traite tous les CV d'un dossier et exporte les résultats sous forme de fichiers JSON."""
    os.makedirs(output_folder, exist_ok=True)
    processed = 0
    errors = 0
    
    for filename in os.listdir(input_folder):
        if filename.lower().endswith(".pdf"):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, os.path.splitext(filename)[0] + ".json")
            
            try:
                data = analyze_resume(input_path)
                if data:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)
                    print(f"✔ Fichier traité : {filename}")
                    processed += 1
                else:
                    print(f"⚠ Fichier non traité (vide ou erreur) : {filename}")
                    errors += 1
            except Exception as e:
                print(f"❌ Erreur lors du traitement de {filename}: {str(e)}")
                errors += 1
    
    print(f"\nRésumé du traitement:")
    print(f"- Fichiers traités avec succès: {processed}")
    print(f"- Fichiers en erreur: {errors}")
    print(f"- Total: {processed + errors}")

# ----------- UTILISATION -----------

if __name__ == "__main__":
    input_dir = r"C:\analyse_cv\Backend\data\cv_brut"
    output_dir = r"C:\analyse_cv\Backend\data\dossier_feature"
    
    print("Début du traitement des CV...")
    process_all_resumes(input_dir, output_dir)
    print("Traitement terminé.")
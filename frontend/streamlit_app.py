import streamlit as st
import os 
import requests
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time
import io
from typing import Optional, Dict, Any, List

# Configuration de la page
st.set_page_config(
    page_title="Analyse Intelligente de Données à partir de CV",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration de l'API
API_BASE_URL = "http://localhost:5000"  # Assurez-vous que c'est la bonne adresse
API_HEALTH_ENDPOINT = f"{API_BASE_URL}/health"
API_ANALYZE_ENDPOINT = f"{API_BASE_URL}/analyze"
API_MATCH_ENDPOINT = f"{API_BASE_URL}/match"

# CSS personnalisé pour améliorer l'apparence
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-block-end: 2rem;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
    }
    
    .metric-card {
        background: white;
        padding: 1rem; /* Réduit pour compétences */
        border-radius: 8px; /* Réduit */
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); /* Plus léger */
        border-inline-start: 4px solid #667eea;
        margin-block-end: 0.5rem; /* Réduit */
        transition: transform 0.2s ease;
        block-size: 90px; /* Hauteur fixe pour alignement */
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    .metric-card strong {
        font-size: 0.9rem;
        margin-block-end: 0.2rem;
        color: #333;
    }
    
    .metric-card small {
        font-size: 0.75rem;
        color: #666;
    }
    
    .success-message {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
    
    .error-message {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        color: #721c24;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #f5c6cb;
        margin: 1rem 0;
    }
    
    .info-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-inline-start: 4px solid #17a2b8;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .section-header {
        color: #333;
        border-block-end: 2px solid #667eea;
        padding-block-end: 0.5rem;
        margin-block-start: 1.5rem; /* Ajout espace avant */
        margin-block-end: 1.5rem;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px; /* Espace entre les onglets */
    }

    .stTabs [data-baseweb="tab"] {
        block-size: 44px; /* Hauteur ajustée */
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 8px 8px 0 0; /* Coins arrondis en haut */
        padding: 0.5rem 1rem;
    }

    .stTabs [aria-selected="true"] {
        background-color: #667eea; /* Couleur active */
        color: white;
    }
    
    .stTab > div > div > div > div {
        padding-block-start: 1rem;
    }
    
    .skill-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        margin: 0.2rem;
        display: inline-block;
        font-size: 0.85rem;
    }
    
    .interest-badge {
        background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        margin: 0.2rem;
        display: inline-block;
        font-size: 0.85rem;
    }
    
    .role-badge {
        background: linear-gradient(135deg, #ffc107 0%, #fd7e14 100%);
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 15px;
        margin: 0.1rem;
        display: inline-block;
        font-size: 0.8rem;
        font-weight: bold;
    }
    
    .expandable-section {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        margin-block-end: 1rem;
        overflow: hidden;
    }
    
    .score-display {
        text-align: center;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    
    .score-excellent { background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; }
    .score-good { background: linear-gradient(135deg, #ffc107 0%, #fd7e14 100%); color: white; }
    .score-average { background: linear-gradient(135deg, #fd7e14 0%, #dc3545 100%); color: white; }
    .score-poor { background: linear-gradient(135deg, #dc3545 0%, #6f42c1 100%); color: white; }
    
    .activity-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-inline-start: 4px solid #28a745;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .api-status {
        padding: 0.5rem 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        font-weight: bold;
    }
    
    .api-connected {
        background: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    
    .api-disconnected {
        background: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }
</style>
""", unsafe_allow_html=True)

def check_api_health() -> tuple[bool, str]:
    """Vérifier l'état de l'API avec plus de détails"""
    try:
        response = requests.get(API_HEALTH_ENDPOINT, timeout=10)
        if response.status_code == 200:
            return True, "API accessible et fonctionnelle"
        else:
            return False, f"API répond avec le code: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, f"Impossible de se connecter à l'API ({API_HEALTH_ENDPOINT}). Vérifiez que le serveur backend est démarré."
    except requests.exceptions.Timeout:
        return False, f"Timeout: L'API ({API_HEALTH_ENDPOINT}) ne répond pas dans les temps"
    except Exception as e:
        try:
            # Tentative sur l'URL de base si /health échoue
            response = requests.get(API_BASE_URL, timeout=5)
            return True, f"API accessible (endpoint de base: {API_BASE_URL})"
        except Exception as base_e:
            return False, f"Erreur de connexion générale à l'API ({API_BASE_URL}). Détails: {str(e)} / {str(base_e)}"

def test_api_endpoints() -> Dict[str, bool]:
    """Tester les différents endpoints de l'API"""
    endpoints = {
        "Base": API_BASE_URL,
        "Health": API_HEALTH_ENDPOINT,
        "Analyze": API_ANALYZE_ENDPOINT,
        "Match": API_MATCH_ENDPOINT
    }
    results = {}
    for name, url in endpoints.items():
        try:
            response = requests.get(url, timeout=5)
            # Considère 200 (OK), 404 (Not Found), 405 (Method Not Allowed) comme des endpoints existants
            results[name] = response.status_code in [200, 404, 405] 
        except requests.exceptions.RequestException:
            results[name] = False
    return results

def analyze_cv(file) -> Optional[Dict[str, Any]]:
    """Analyser un CV via l'API avec gestion d'erreur améliorée"""
    if not file:
        st.error("Erreur interne: Aucun fichier fourni à analyze_cv.")
        return None
        
    endpoint_url = API_ANALYZE_ENDPOINT
    st.info(f"Tentative d'appel API vers: {endpoint_url}")
    
    try:
        # Préparer les fichiers pour l'upload
        files = {
            'file': (file.name, file.getvalue(), file.type or 'application/pdf')
        }
        
        # Faire la requête
        response = requests.post(
            endpoint_url, 
            files=files, 
            timeout=600,  # 10 minutes timeout
            headers={'Accept': 'application/json'} # Spécifier qu'on attend du JSON
        )
        
        # Vérifier le statut de la réponse
        if response.status_code == 200:
            try:
                # Essayer de décoder le JSON
                result_json = response.json()
                st.success(f"Réponse API reçue (status {response.status_code})")
                return result_json
            except json.JSONDecodeError as json_err:
                st.error(f"Erreur: Réponse API reçue (status {response.status_code}) mais invalide (pas du JSON). Détail: {json_err}")
                st.text_area("Contenu brut de la réponse (début)", response.text[:500], height=100)
                return None
        else:
            # Gérer les autres codes d'erreur HTTP
            st.error(f"Erreur API lors de l'analyse: Status {response.status_code}")
            try:
                # Essayer d'afficher le détail de l'erreur si c'est du JSON
                error_detail = response.json()
                st.error(f"Détail de l'erreur (JSON): {error_detail}")
            except json.JSONDecodeError:
                # Sinon, afficher le texte brut
                st.error("La réponse d'erreur de l'API n'est pas au format JSON.")
                st.text_area("Contenu brut de la réponse d'erreur (début)", response.text[:500], height=100)
            return None
            
    except requests.exceptions.Timeout:
        st.error(f"Timeout: L'appel à l'API d'analyse ({endpoint_url}) a dépassé le délai de 10 minutes. Le serveur est peut-être surchargé ou l'analyse est très longue.")
        return None
    except requests.exceptions.ConnectionError as conn_err:
        st.error(f"Erreur de Connexion: Impossible de joindre l'API d'analyse à l'adresse {endpoint_url}. Vérifiez que le serveur backend est démarré et accessible.")
        st.error(f"Détail technique: {conn_err}")
        return None
    except requests.exceptions.RequestException as req_err:
        # Autres erreurs liées à la requête (ex: problème DNS, SSL...)
        st.error(f"Erreur de Requête vers {endpoint_url}: {req_err}")
        return None
    except Exception as e:
        # Erreur générique (ex: problème de lecture du fichier?)
        st.error(f"Erreur inattendue lors de la préparation ou de l'envoi de la requête d'analyse: {e}")
        return None

def match_cv_job(file, job_offer: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Matcher un CV avec une offre d'emploi via l'API avec gestion d'erreur améliorée"""
    if not file or not job_offer:
        st.error("Erreur interne: Fichier CV ou données de l'offre manquants pour match_cv_job.")
        return None
        
    endpoint_url = API_MATCH_ENDPOINT
    st.info(f"Tentative d'appel API vers: {endpoint_url}")
    
    try:
        # Préparer les fichiers et données
        files = {
            'file': (file.name, file.getvalue(), file.type or 'application/pdf')
        }
        # S'assurer que l'offre est bien sérialisée en JSON
        try:
            job_offer_json = json.dumps(job_offer, ensure_ascii=False)
        except TypeError as json_ser_err:
            st.error(f"Erreur interne: Impossible de sérialiser les données de l'offre d'emploi en JSON. Détail: {json_ser_err}")
            return None
            
        data = {'job_offer': job_offer_json}
        
        # Faire la requête
        response = requests.post(
            endpoint_url, 
            files=files, 
            data=data, 
            timeout=600, # 10 minutes timeout
            headers={'Accept': 'application/json'}
        )
        
        # Vérifier le statut de la réponse
        if response.status_code == 200:
            try:
                result_json = response.json()
                st.success(f"Réponse API reçue (status {response.status_code})")
                return result_json
            except json.JSONDecodeError as json_err:
                st.error(f"Erreur: Réponse API reçue (status {response.status_code}) mais invalide (pas du JSON). Détail: {json_err}")
                st.text_area("Contenu brut de la réponse (début)", response.text[:500], height=100)
                return None
        else:
            # Gérer les autres codes d'erreur HTTP
            st.error(f"Erreur API lors du matching: Status {response.status_code}")
            try:
                error_detail = response.json()
                st.error(f"Détail de l'erreur (JSON): {error_detail}")
            except json.JSONDecodeError:
                st.error("La réponse d'erreur de l'API n'est pas au format JSON.")
                st.text_area("Contenu brut de la réponse d'erreur (début)", response.text[:500], height=100)
            return None
            
    except requests.exceptions.Timeout:
        st.error(f"Timeout: L'appel à l'API de matching ({endpoint_url}) a dépassé le délai de 10 minutes.")
        return None
    except requests.exceptions.ConnectionError as conn_err:
        st.error(f"Erreur de Connexion: Impossible de joindre l'API de matching à l'adresse {endpoint_url}. Vérifiez que le serveur backend est démarré et accessible.")
        st.error(f"Détail technique: {conn_err}")
        return None
    except requests.exceptions.RequestException as req_err:
        st.error(f"Erreur de Requête vers {endpoint_url}: {req_err}")
        return None
    except Exception as e:
        st.error(f"Erreur inattendue lors de la préparation ou de l'envoi de la requête de matching: {e}")
        return None

def get_score_class(score: float) -> str:
    """Retourner la classe CSS en fonction du score"""
    if score >= 80:
        return "score-excellent"
    elif score >= 65:
        return "score-good"
    elif score >= 50:
        return "score-average"
    else:
        return "score-poor"

def display_score_gauge(score: float, title: str):
    """Afficher un gauge circulaire (donut) pour le score."""
    try:
        numeric_score = float(score)
        if not (0 <= numeric_score <= 100):
             # Clamp score to 0-100 range for display
             numeric_score = max(0, min(100, numeric_score))
             st.warning(f"Score '{score}' hors de la plage 0-100, ajusté à {numeric_score} pour l'affichage.")
    except (ValueError, TypeError):
        numeric_score = 0 # Valeur par défaut si non numérique
        st.warning(f"Score invalide ('{score}') pour le gauge '{title}', affichage à 0.")

    # Déterminer la couleur en fonction du score
    if numeric_score >= 80:
        color = "#28a745" # Vert (Excellent)
    elif numeric_score >= 65:
        color = "#ffc107" # Jaune (Bon)
    elif numeric_score >= 50:
        color = "#fd7e14" # Orange (Moyen)
    else:
        color = "#dc3545" # Rouge (Faible)

    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = numeric_score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title, 'font': {'size': 18, 'color': '#555'}}, # Titre légèrement plus petit et gris
        number = {'font': {'size': 48, 'color': '#333'}}, # Score en grand au centre
        gauge = {
            'axis': {'range': [0, 100], 'visible': False}, # Cacher l'axe
            'shape': "angular", # Forme circulaire
            'bar': {'color': color, 'thickness': 0.3}, # Barre de score colorée
            'bgcolor': "#f0f2f6", # Couleur de fond de la jauge (gris clair)
            'borderwidth': 1,
            'bordercolor': "#cccccc" # Bordure légère
            # Pas de steps ou threshold ici pour un look épuré
        }
    ))

    fig.update_layout(
        height=250, # Hauteur réduite
        margin=dict(l=20, r=20, t=50, b=20), # Marges ajustées
        paper_bgcolor='rgba(0,0,0,0)', # Fond transparent
        plot_bgcolor='rgba(0,0,0,0)', # Fond du plot transparent
        font={'color': "#333", 'family': "Arial"}
    )
    return fig

def safe_get(data: Optional[Dict], key: str, default=None):
    """Récupération sécurisée des données avec valeur par défaut"""
    return data.get(key, default) if isinstance(data, dict) else default

def safe_get_nested(data: Optional[Dict], keys: List[str], default=None):
    """Récupération sécurisée des données imbriquées"""
    if not isinstance(data, dict):
        return default
    temp_data = data
    for key in keys:
        if isinstance(temp_data, dict) and key in temp_data:
            temp_data = temp_data[key]
        else:
            return default
    return temp_data

def format_date_range(date_debut: Optional[str], date_fin: Optional[str]) -> str:
    """Formater une plage de dates (gère None)"""
    date_debut = str(date_debut) if date_debut else ""
    date_fin = str(date_fin) if date_fin else ""
    
    if not date_debut and not date_fin:
        return "Période non spécifiée"
    elif not date_fin:
        return f"Depuis {date_debut}"
    elif not date_debut:
        return f"Jusqu'à {date_fin}"
    else:
        # Simple comparaison de chaînes pour 'présent' ou similaire
        if date_fin.lower() in ["présent", "present", "aujourd'hui", "current", "now"]:
             return f"{date_debut} - {date_fin}"
        # Si les dates sont identiques (ex: événement ponctuel)
        elif date_debut == date_fin:
             return date_debut
        else:
             return f"{date_debut} - {date_fin}"

# --- Fonctions d'affichage pour chaque section --- 

def display_classification_section(result: Dict[str, Any]):
    """Afficher la section Synthèse & Score (anciennement Classification)"""
    st.markdown('<h3 class="section-header">📊 classification & Score du Profil</h3>', unsafe_allow_html=True)
    
    classification = safe_get(result, 'classification', {})
    score_data = safe_get(result, 'score_total', {})
    
    if not classification and not score_data:
        st.info("Aucune donnée de classification ou de score disponible pour cette section.")
        return

    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Score global
        main_score = safe_get(score_data, 'score', None) 
        if main_score is not None:
            st.plotly_chart(display_score_gauge(main_score, "Score Global"), use_container_width=True)
        else:
            st.warning("Score global non disponible.")
        
        # Classification
        if classification:
            st.markdown("#### 📊 Classification Automatique")
            metrics_col1, metrics_col2 = st.columns(2)
            with metrics_col1:
                st.metric("Catégorie", safe_get(classification, 'categorie', 'N/A'))
            with metrics_col2:
                confiance = safe_get(classification, 'confiance')
                if isinstance(confiance, (int, float)):
                    st.metric("Confiance", f"{confiance:.1%}")
                else:
                    st.metric("Confiance", str(confiance) if confiance else 'N/A')
            
            justification = safe_get(classification, 'justification')
            if justification:
                st.info(f"**Justification:** {justification}")
    
    with col2:
        # Détails de l'évaluation
        st.markdown("#### 📈 Évaluation Détaillée")
        details = safe_get(score_data, 'details_evaluation', {})
        
        if details:
            details_list = [
                {"Critère": "Complétude", "Score": safe_get(details, 'completude_informations', 0)},
                {"Critère": "Expériences", "Score": safe_get(details, 'qualite_experiences', 0)},
                {"Critère": "Compétences", "Score": safe_get(details, 'pertinence_competences', 0)},
                {"Critère": "Formation", "Score": safe_get(details, 'formation_adequation', 0)},
                {"Critère": "Présentation", "Score": safe_get(details, 'presentation_structure', 0)}
            ]
            # Filtrer les scores non nuls ou non None
            details_df = pd.DataFrame([d for d in details_list if d["Score"] is not None and d["Score"] > 0])
            
            if not details_df.empty:
                fig = px.bar(details_df, x="Score", y="Critère", orientation='h',
                           color="Score", color_continuous_scale="Viridis",
                           title="Scores par Critère")
                fig.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucun détail de score disponible.")
        else:
            st.info("Aucun détail de score disponible.")
    
    st.markdown("--- ")
    # Points forts et améliorations
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### ✅ Points Forts")
        points_forts = safe_get(score_data, 'points_forts', [])
        if points_forts and isinstance(points_forts, list):
            for point in points_forts:
                st.success(f"• {point}")
        else:
            st.info("Aucun point fort spécifique identifié")
    
    with col2:
        st.markdown("#### 🔧 Axes d'Amélioration")
        points_amelioration = safe_get(score_data, 'points_amelioration', [])
        if points_amelioration and isinstance(points_amelioration, list):
            for point in points_amelioration:
                st.warning(f"• {point}")
        else:
            st.info("Aucun axe d'amélioration identifié")
    
    # Commentaire général
    commentaire = safe_get(score_data, 'commentaire_general', '')
    if commentaire:
        st.markdown("#### 💬 Analyse Générale")
        st.info(commentaire)

def display_profile_section(result: Dict[str, Any]):
    """Afficher la section Profil"""
    st.markdown('<h3 class="section-header">👤 Informations Personnelles et Coordonnées</h3>', unsafe_allow_html=True)
    
    perso_info = safe_get(result, 'informations_personnelles', {})
    profil = safe_get(result, 'profil', '')
    
    if not perso_info and not profil:
        st.info("Aucune information de profil ou personnelle disponible pour cette section.")
        return

    # Informations de contact
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📞 Contact")
        contact_data = [
            ("👤 Nom", safe_get(perso_info, 'nom_prenom')),
            ("📧 Email", safe_get(perso_info, 'email')),
            ("📱 Téléphone", safe_get(perso_info, 'telephone')),
            ("🏠 Adresse", safe_get(perso_info, 'adresse'))
        ]
        
        has_contact = False
        for label, value in contact_data:
            if value:
                st.success(f"{label}: {value}")
                has_contact = True
        if not has_contact:
            st.info("Aucune information de contact principale.")

    with col2:
        st.markdown("#### 🌐 Présence en Ligne")
        online_data = [
            ("💼 LinkedIn", safe_get(perso_info, 'linkedin')),
            ("💻 GitHub", safe_get(perso_info, 'github')),
            ("🎨 Portfolio", safe_get(perso_info, 'portfolio')),
            ("🌍 Site Web", safe_get(perso_info, 'site_web'))
        ]
        
        has_online = False
        for label, value in online_data:
            if value:
                has_online = True
                if isinstance(value, str) and value.startswith(('http', 'www')):
                    url = value if value.startswith('http') else 'https://' + value
                    # Essayer d'afficher un nom de domaine plus court
                    display_url = value.split('//')[-1].split('/')[0]
                    st.success(f"{label}: [{display_url}]({url})")
                else:
                    st.info(f"{label}: {value}")
        if not has_online:
            st.info("Aucun lien de présence en ligne détecté.")
    
    # Profil professionnel
    if profil:
        st.markdown("#### 📝 Profil Professionnel")
        st.info(profil)
    

def display_experiences_section(result: Dict[str, Any]):
    """Afficher la section Expériences"""
    st.markdown('<h3 class="section-header">💼 Parcours Professionnel Détaillé</h3>', unsafe_allow_html=True)
    
    experiences = safe_get(result, 'experiences_professionnelles', [])
    
    if experiences and isinstance(experiences, list):
        # Statistiques des expériences
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Nombre d'expériences", len(experiences))
        with col2:
            total_exp = 0
            try:
                # Calcul plus robuste de la durée totale
                durations = [exp.get('duree_mois') for exp in experiences if isinstance(exp.get('duree_mois'), (int, float))]
                total_exp = sum(durations)
            except Exception:
                 pass # Ignorer les erreurs de calcul
                 
            if total_exp > 0:
                st.metric("Expérience totale", f"{total_exp // 12} ans {total_exp % 12} mois")
            else:
                st.metric("Expérience totale", "N/A")
        with col3:
            secteurs = list(set([safe_get(exp, 'secteur') for exp in experiences if safe_get(exp, 'secteur')]))
            st.metric("Secteurs", len(secteurs) if secteurs else 0)
        
        st.markdown("#### Détails des Expériences")
        # Détails des expériences
        for i, exp in enumerate(experiences):
            if not isinstance(exp, dict): continue # Ignorer les éléments non valides
            
            poste = safe_get(exp, 'poste', 'Poste non spécifié')
            entreprise = safe_get(exp, 'entreprise', 'Entreprise non spécifiée')
            
            with st.expander(f"💼 {poste} chez {entreprise}", expanded=i==0):
                exp_col1, exp_col2 = st.columns([2, 1])
                
                with exp_col1:
                    date_debut = safe_get(exp, 'date_debut')
                    date_fin = safe_get(exp, 'date_fin')
                    st.markdown(f"**📅 Période:** {format_date_range(date_debut, date_fin)}")
                    st.markdown(f"**🏢 Entreprise:** {entreprise}")
                    st.markdown(f"**📍 Lieu:** {safe_get(exp, 'lieu', 'N/A')}")
                    st.markdown(f"**📋 Type:** {safe_get(exp, 'type', 'N/A')}")
                    
                    description = safe_get(exp, 'description')
                    if description:
                        st.markdown("**📝 Description:**")
                        st.write(description)
                
                with exp_col2:
                    duree = safe_get(exp, 'duree')
                    if duree:
                        st.metric("Durée", str(duree))
                    
                    secteur = safe_get(exp, 'secteur')
                    if secteur:
                        st.info(f"**Secteur:** {secteur}")
                
                # Réalisations
                realisations = safe_get(exp, 'realisations', [])
                if realisations and isinstance(realisations, list):
                    st.markdown("**🎯 Réalisations:**")
                    for real in realisations:
                        st.success(f"• {real}")
                
                # Compétences utilisées
                competences_exp = safe_get(exp, 'competences_utilisees', [])
                if competences_exp and isinstance(competences_exp, list):
                    st.markdown("**🔧 Compétences utilisées:**")
                    comp_html = " ".join([f'<span class="skill-badge">{comp}</span>' for comp in competences_exp])
                    st.markdown(comp_html, unsafe_allow_html=True)
    else:
        st.info("Aucune expérience professionnelle détectée pour cette section.")

def display_education_section(result: Dict[str, Any]):
    """Afficher la section Formation"""
    st.markdown('<h3 class="section-header">🎓 Cursus Académique et Diplômes</h3>', unsafe_allow_html=True)
    
    formations = safe_get(result, 'formation', [])
    
    if formations and isinstance(formations, list):
        # Statistiques de formation
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Nombre de formations", len(formations))
        with col2:
            niveaux = [str(safe_get(f, 'niveau', '')) for f in formations if safe_get(f, 'niveau')]
            # Trouver le niveau le plus long (suppose une hiérarchie textuelle)
            niveau_max = max(niveaux, key=len) if niveaux else "N/A"
            st.metric("Niveau max", niveau_max)
        with col3:
            domaines = list(set([safe_get(f, 'domaine') for f in formations if safe_get(f, 'domaine')]))
            st.metric("Domaines", len(domaines) if domaines else 0)
        
        st.markdown("#### Détails des Formations")
        # Détails des formations
        for i, form in enumerate(formations):
            if not isinstance(form, dict): continue
            
            diplome = safe_get(form, 'diplome', 'Diplôme')
            etablissement = safe_get(form, 'etablissement', 'Établissement')
            
            with st.expander(f"🎓 {diplome} - {etablissement}", expanded=i==0):
                form_col1, form_col2 = st.columns([2, 1])
                
                with form_col1:
                    st.markdown(f"**🏫 Établissement:** {etablissement}")
                    st.markdown(f"**📚 Spécialité:** {safe_get(form, 'specialite', 'N/A')}")
                    
                    date_debut = safe_get(form, 'date_debut')
                    date_fin = safe_get(form, 'date_fin')
                    st.markdown(f"**📅 Période:** {format_date_range(date_debut, date_fin)}")
                    st.markdown(f"**📍 Lieu:** {safe_get(form, 'lieu', 'N/A')}")
                    
                    description = safe_get(form, 'description')
                    if description:
                        st.markdown("**📝 Description:**")
                        st.write(description)
                
                with form_col2:
                    niveau = safe_get(form, 'niveau')
                    if niveau:
                        st.info(f"**Niveau:** {niveau}")
                    
                    mention = safe_get(form, 'mention')
                    if mention:
                        st.success(f"**Mention:** {mention}")
                
                notes = safe_get(form, 'notes')
                if notes:
                    st.markdown("**📋 Notes:**")
                    st.info(str(notes))
    else:
        st.info("Aucune formation détectée pour cette section.")

def display_projects_section(result: Dict[str, Any]):
    """Afficher la section Projets"""
    st.markdown('<h3 class="section-header">🚀 Réalisations et Contributions</h3>', unsafe_allow_html=True)
    
    projets = safe_get(result, 'projets', [])
    
    if projets and isinstance(projets, list):
        # Statistiques des projets
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Nombre de projets", len(projets))
        with col2:
            types_projet = list(set([safe_get(p, 'type') for p in projets if safe_get(p, 'type')]))
            st.metric("Types de projets", len(types_projet) if types_projet else 0)
        with col3:
            statuts = [str(safe_get(p, 'statut', '')).lower() for p in projets if safe_get(p, 'statut')]
            completes = len([s for s in statuts if 'terminé' in s or 'fini' in s or 'completed' in s])
            st.metric("Projets terminés", completes)
        
        st.markdown("#### Détails des Projets")
        # Détails des projets
        for i, proj in enumerate(projets):
             if not isinstance(proj, dict): continue
             
             titre = safe_get(proj, 'titre', 'Projet')
             type_proj = safe_get(proj, 'type', 'Type non spécifié')
            
             with st.expander(f"🚀 {titre} ({type_proj})", expanded=i==0):
                proj_col1, proj_col2 = st.columns([2, 1])
                
                with proj_col1:
                    date_debut = safe_get(proj, 'date_debut')
                    date_fin = safe_get(proj, 'date_fin')
                    st.markdown(f"**📅 Période:** {format_date_range(date_debut, date_fin)}")
                    
                    description = safe_get(proj, 'description')
                    if description:
                        st.markdown("**📝 Description:**")
                        st.write(description)
                    
                    contexte = safe_get(proj, 'contexte')
                    if contexte:
                        st.markdown("**🎯 Contexte:**")
                        st.info(contexte)
                
                with proj_col2:
                    statut = safe_get(proj, 'statut')
                    if statut:
                        status_lower = str(statut).lower()
                        status_color = "success" if 'terminé' in status_lower or 'fini' in status_lower else "info"
                        if status_color == "success":
                            st.success(f"**Statut:** {statut}")
                        else:
                            st.info(f"**Statut:** {statut}")
                    
                    duree = safe_get(proj, 'duree')
                    if duree:
                        st.metric("Durée", str(duree))
                
                # Technologies utilisées
                technologies = safe_get(proj, 'technologies_utilisees', [])
                if technologies and isinstance(technologies, list):
                    st.markdown("**💻 Technologies:**")
                    tech_html = " ".join([f'<span class="skill-badge">{tech}</span>' for tech in technologies])
                    st.markdown(tech_html, unsafe_allow_html=True)
                
                # Réalisations du projet
                realisations = safe_get(proj, 'realisations', [])
                if realisations and isinstance(realisations, list):
                    st.markdown("**🎯 Réalisations:**")
                    for real in realisations:
                        st.success(f"• {real}")
    else:
        st.info("Aucun projet détecté pour cette section.")

def safe_get(dictionary, key, default=None):
    """Helper function to safely get values from dictionary"""
    return dictionary.get(key, default) if isinstance(dictionary, dict) else default



def display_skills_section_improved(result: Dict[str, Any]):

    st.markdown('<h3 class="section-header">🔧 Compétences Techniques, Transversales et Outils</h3>', unsafe_allow_html=True)

    competences_dict = safe_get(result, 'competences', {})

    # --- Récupération Structurée des Compétences Techniques ---
    # Essayer d'abord sous result['competences'], puis à la racine result.
    tech_skills_categories = {
        "Langages de Programmation": safe_get(competences_dict, 'langages_programmation', []) or safe_get(result, 'langages_programmation', []),
        "Frameworks & Bibliothèques": safe_get(competences_dict, 'frameworks_bibliotheques', []) or safe_get(result, 'frameworks_bibliotheques', []),
        "Bases de Données": safe_get(competences_dict, 'bases_donnees', []) or safe_get(result, 'bases_donnees', []),
        "Cloud & DevOps": safe_get(competences_dict, 'cloud_devops', []) or safe_get(result, 'cloud_devops', []),
        "Systèmes d'Exploitation": safe_get(competences_dict, 'systemes_exploitation', []) or safe_get(result, 'systemes_exploitation', []),
        "Outils de Développement": safe_get(competences_dict, 'outils_developpement', []) or safe_get(result, 'outils_developpement', []),
        "Méthodologies": safe_get(competences_dict, 'methodologies', []) or safe_get(result, 'methodologies', []),
        "Design & Multimédia": safe_get(competences_dict, 'design_multimedia', []) or safe_get(result, 'design_multimedia', []),
        "Gestion de Projet": safe_get(competences_dict, 'gestion_projet', []) or safe_get(result, 'gestion_projet', []),
        # Pour 'autres', on peut supposer qu'elles sont moins structurées
        "Autres Compétences Techniques": safe_get(competences_dict, 'autres', []) or safe_get(result, 'autres', [])
    }
    # Nettoyer les listes vides potentielles résultant du 'or []'
    for key in tech_skills_categories:
        if not tech_skills_categories[key]:
             tech_skills_categories[key] = []

    # Tentative de récupération via une clé imbriquée, puis une clé directe comme fallback.
    comp_trans = safe_get_nested(result, ['competences', 'transversales'], [])
    if not comp_trans:
         comp_trans = safe_get(result, 'competences_transversales', []) # Clé directe alternative
    if not comp_trans: # Assurer que c'est une liste
        comp_trans = []

    # Essayer d'abord sous result['competences'], puis à la racine result.
    outils_generaux = safe_get(competences_dict, 'outils', []) or safe_get(result, 'outils', [])
    if not outils_generaux: # Assurer que c'est une liste
        outils_generaux = []

    dev_tools_set = set(tech_skills_categories.get("Outils de Développement", []))
    # Filtrage pour ne garder que les outils non classés comme 'développement'
    outils_generaux_filtered = [outil for outil in outils_generaux if outil and outil not in dev_tools_set]

    # Utiliser les listes potentiellement vides après nettoyage/fallback
    has_technical_skills = any(bool(skills) for skills in tech_skills_categories.values() if isinstance(skills, list))
    has_soft_skills = bool(comp_trans and isinstance(comp_trans, list))
    has_general_tools = bool(outils_generaux_filtered and isinstance(outils_generaux_filtered, list))


    # Si aucune compétence n'est détectée, afficher un message informatif et terminer.
    if not has_technical_skills and not has_soft_skills and not has_general_tools:
        st.info("Aucune compétence (technique, transversale ou outil) n'a été détectée dans les données fournies.")
        return

    # --- Affichage des Compétences Techniques par Catégorie ---
    st.markdown("#### 💻 Compétences Techniques")
    displayed_tech_skills = False
    if has_technical_skills:
        for category, skills in tech_skills_categories.items():
            # Vérification que la liste de compétences pour la catégorie n'est pas vide et est une liste
            if skills and isinstance(skills, list) and any(s for s in skills):
                displayed_tech_skills = True
                st.markdown(f"##### {category}")
                skills_html = " ".join([f'<span class="skill-badge tech">{skill}</span>' for skill in skills if skill])
                st.markdown(skills_html, unsafe_allow_html=True)
                st.write("") # Ajoute un petit espace vertical pour l'aération.

    if not displayed_tech_skills:
        # Message si aucune compétence technique n'a été trouvée OU affichée.
        st.info("Aucune compétence technique spécifique n'a été détectée ou affichée.")

    st.markdown("--- ") # Séparateur visuel entre les sections.

    # --- Affichage des Compétences Transversales ---
    st.markdown("#### 🤝 Compétences Transversales (Soft Skills)")
    if has_soft_skills:
        # Formatage des soft skills avec un style de badge distinct.
        soft_skills_html = " ".join([f'<span class="skill-badge soft">{comp}</span>' for comp in comp_trans if comp])
        if soft_skills_html:
            st.markdown(soft_skills_html, unsafe_allow_html=True)
        else:
             st.info("Aucune compétence transversale listée.")
    else:
        st.info("Aucune compétence transversale n'a été détectée.")

    st.markdown("--- ") 

    # --- Affichage des Autres Outils & Logiciels ---
    st.markdown("#### 🛠️ Autres Outils & Logiciels")
    if has_general_tools:
        # Formatage des outils généraux avec un style de badge spécifique.
        tools_html = " ".join([f'<span class="skill-badge tool">{outil}</span>' for outil in outils_generaux_filtered if outil])
        if tools_html:
             st.markdown(tools_html, unsafe_allow_html=True)
        else:
             st.info("Aucun outil ou logiciel général supplémentaire n'a été détecté.")
    else:
        st.info("Aucun autre outil ou logiciel général n'a été détecté (en dehors des outils de développement listés ci-dessus).")

    st.markdown("---") 
    # Section Outils (selon competences.outils et autres sources)
    st.markdown("#### 🛠️ Outils et Logiciels (Généraux)")
    if all_outils and isinstance(all_outils, list):
        # Filtrer pour éviter les doublons avec outils_dev si nécessaire
        outils_display = [o for o in all_outils if o not in outils_dev] if outils_dev else all_outils
        if outils_display:
            outils_html = " ".join([f'<span class="skill-badge" style="background: linear-gradient(135deg, #ffc107 0%, #fd7e14 100%);">{outil}</span>' for outil in outils_display if outil])
            if outils_html:
                st.markdown(outils_html, unsafe_allow_html=True)
            else:
                st.info("Aucun outil général supplémentaire détecté.")
        else:
            st.info("Aucun outil général supplémentaire détecté.")
    else:
        st.info("Aucun outil spécifique détecté")
        
def display_languages_section(result: Dict[str, Any]):
    """Afficher la section Langues"""
    st.markdown('<h3 class="section-header">🌐 Langues Maîtrisées</h3>', unsafe_allow_html=True)
    # Essayer la clé imbriquée d'abord, puis la clé directe
    langues = safe_get_nested(result, ['competences', 'langues'], [])
    if not langues:
        langues = safe_get(result, 'langues', []) # Clé directe

    if langues and isinstance(langues, list):
        st.metric("Nombre de langues détectées", len(langues))
        st.markdown("--- ") # Séparateur

        for langue in langues:
            if isinstance(langue, dict):
                nom = safe_get(langue, 'langue', 'Langue')
                niveau = safe_get(langue, 'niveau', 'Non spécifié')
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown(f"**{nom}**")
                with col2:
                    niveau_map = {
                        'Débutant': 25, 'A1': 25, 'A2': 40, 'Élémentaire': 40, 
                        'Intermédiaire': 60, 'B1': 60, 'B2': 75,
                        'Avancé': 80, 'C1': 85, 'Courant': 90, 
                        'Natif': 100, 'Bilingue': 100, 'C2': 100
                    }
                    # Normaliser le niveau pour la recherche
                    niveau_norm = niveau.replace('(', '').replace(')', '').strip()
                    progress = niveau_map.get(niveau_norm, 0) 
                    
                    if progress > 0:
                        st.progress(progress / 100)
                    st.caption(niveau) # Afficher le niveau original
            elif isinstance(langue, str):
                 st.markdown(f"- {langue}")
    else:
        st.info("Aucune langue détectée pour cette section.")

def display_certifications_section(result: Dict[str, Any]):
    """Afficher la section Certifications"""
    st.markdown('<h3 class="section-header">🏆 Accréditations et Certifications</h3>', unsafe_allow_html=True)
    
    certifications = safe_get(result, 'certifications', [])
    
    if certifications and isinstance(certifications, list):
        st.metric("Nombre de certifications détectées", len(certifications))
        st.markdown("--- ") # Séparateur
        
        st.markdown("#### Détails des Certifications")
        for i, cert in enumerate(certifications):
            if not isinstance(cert, dict): continue
            
            nom = safe_get(cert, 'nom', 'Certification')
            organisme = safe_get(cert, 'organisme', 'Organisme')
            
            with st.expander(f"🏆 {nom} - {organisme}", expanded=i==0):
                cert_col1, cert_col2 = st.columns([2, 1])
                
                with cert_col1:
                    st.markdown(f"**🏢 Organisme:** {organisme}")
                    date_obtention = safe_get(cert, 'date_obtention')
                    if date_obtention:
                        st.markdown(f"**📅 Date d'obtention:** {date_obtention}")
                    
                    date_expiration = safe_get(cert, 'date_expiration')
                    if date_expiration:
                        st.markdown(f"**⏰ Date d'expiration:** {date_expiration}")
                    
                    description = safe_get(cert, 'description')
                    if description:
                        st.markdown("**📝 Description:**")
                        st.write(description)
                
                with cert_col2:
                    identifiant = safe_get(cert, 'identifiant')
                    if identifiant:
                        st.info(f"**ID:** {identifiant}")
                    
                    lien = safe_get(cert, 'lien')
                    if lien and isinstance(lien, str) and lien.startswith(('http', 'www')):
                        url = lien if lien.startswith('http') else 'https://' + lien
                        st.link_button("Vérifier la certification", url)
    else:
        st.info("Aucune certification détectée pour cette section.")

def display_interests_section(result: Dict[str, Any]):
    """Afficher la section Centres d'Intérêt"""
    st.markdown('<h3 class="section-header">🎯 Centres d\'Intérêt</h3>', unsafe_allow_html=True)
    interests = safe_get(result, 'centres_interet', []) 

    if interests and isinstance(interests, list):
        st.metric("Nombre de centres d'intérêt détectés", len(interests))
        st.markdown("--- ")
        st.markdown("##### Liste des centres d'intérêt:")
        interests_html = " ".join([f'<span class="interest-badge">{interest}</span>' for interest in interests if interest])
        if interests_html:
            st.markdown(interests_html, unsafe_allow_html=True)
        else:
            st.info("Liste des centres d'intérêt vide.")
    else:
        st.info("Aucun centre d'intérêt détecté pour cette section. (Vérifiez la clé 'centres_interet')")

def display_associative_life_section(result: Dict[str, Any]):
    """Afficher la section Vie Associative"""
    st.markdown('<h3 class="section-header">🤝 Vie Associative et Bénévolat</h3>', unsafe_allow_html=True)
    activities = safe_get(result, 'vie_associative', []) 

    if activities and isinstance(activities, list):
        st.metric("Nombre d'activités associatives détectées", len(activities))
        st.markdown("--- ")
        st.markdown("##### Activités associatives et bénévoles:")
        for activity in activities:
            if isinstance(activity, dict):
                role = safe_get(activity, 'role', 'Rôle non spécifié')
                orga = safe_get(activity, 'organisation', 'Organisation non spécifiée')
                desc = safe_get(activity, 'description', '')
                period = format_date_range(safe_get(activity, 'date_debut'), safe_get(activity, 'date_fin'))

                with st.container():
                     st.markdown('<div class="activity-card">', unsafe_allow_html=True)
                     st.markdown(f"**{role}** chez **{orga}**")
                     st.caption(f"📅 {period}")
                     if desc:
                         st.write(desc)
                     # --- Ajout des compétences développées ---
                     competences_dev = safe_get(activity, 'competences_developpees', [])
                     if competences_dev and isinstance(competences_dev, list):
                         st.markdown("**🔧 Compétences développées:**")
                         comp_html = " ".join([f'<span class=\"skill-badge\">{comp}</span>' for comp in competences_dev if comp])
                         if comp_html:
                             st.markdown(comp_html, unsafe_allow_html=True)
                     # -----------------------------------------
                     st.markdown('</div>', unsafe_allow_html=True)
            elif isinstance(activity, str):
                st.markdown(f"- {activity}")
    else:
        st.info("Aucune activité associative ou bénévole détectée pour cette section. (Vérifiez la clé 'vie_associative')")

def display_matching_section(result: Dict[str, Any]):
    """Afficher la section Matching avec offre d'emploi"""
    st.markdown('<h3 class="section-header">🎯 Analyse de Compatibilité avec l\'Offre</h3>', unsafe_allow_html=True)
    
    matching = safe_get(result, 'matching_score', {})
    
    if matching and isinstance(matching, dict):
        # Score global de matching
        score_global = safe_get(matching, 'score_global', None) 
        col1, col2 = st.columns([1, 2])
        
        with col1:
             if score_global is not None:
                 st.plotly_chart(display_score_gauge(score_global, "Score de Compatibilité"), use_container_width=True)
             else:
                 st.warning("Score de compatibilité non disponible.")
        
        with col2:
            # Détails du matching
            details = safe_get(matching, 'details', {})
            if details and isinstance(details, dict):
                st.markdown("#### 📊 Analyse Détaillée")
                
                details_list = [
                    {"Critère": "Compétences", "Score": safe_get(details, 'competences', 0)},
                    {"Critère": "Expérience", "Score": safe_get(details, 'experience', 0)},
                    {"Critère": "Formation", "Score": safe_get(details, 'formation', 0)},
                    {"Critère": "Secteur", "Score": safe_get(details, 'secteur', 0)}
                ]
                details_df = pd.DataFrame([d for d in details_list if d["Score"] is not None and d["Score"] > 0])
                
                if not details_df.empty:
                    fig = px.bar(details_df, x="Score", y="Critère", orientation='h',
                               color="Score", color_continuous_scale="RdYlGn",
                               title="Scores de Matching par Critère")
                    fig.update_layout(height=300, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Aucun détail de score de matching disponible.")
            else:
                st.info("Aucun détail de score de matching disponible.")
        
        st.markdown("--- ")
        # Points de correspondance et manques
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### ✅ Points de Correspondance")
            correspondances = safe_get(matching, 'points_correspondance', [])
            if correspondances and isinstance(correspondances, list):
                for point in correspondances:
                    st.success(f"• {point}")
            else:
                st.info("Aucun point de correspondance spécifique")
        
        with col2:
            st.markdown("#### ❌ Points Manquants")
            manques = safe_get(matching, 'points_manquants', [])
            if manques and isinstance(manques, list):
                for manque in manques:
                    st.error(f"• {manque}")
            else:
                st.info("Aucun point manquant identifié")
        
        # Recommandations
        recommandations = safe_get(matching, 'recommandations', [])
        if recommandations and isinstance(recommandations, list):
            st.markdown("#### 💡 Recommandations")
            for rec in recommandations:
                st.info(f"• {rec}")
        
        # Conclusion du matching
        conclusion = safe_get(matching, 'conclusion', '')
        if conclusion:
            st.markdown("#### 📝 Conclusion")
            st.markdown(f'<div class="info-card">{conclusion}</div>', unsafe_allow_html=True)
    else:
        st.warning("Aucune donnée de matching disponible.")

# --- Configuration des onglets et de leurs fonctions --- 
# Utilise les clés JSON attendues de l'API pour déterminer si un onglet doit être affiché
tabs_config = {
    "📊 classification & Score": {
        "function": display_classification_section,
        "required_keys": ["classification", "score_total"] 
    },
    "👤 Profil": {
        "function": display_profile_section,
        "required_keys": ["informations_personnelles", "profil"]
    },
    "💼 Expériences": {
        "function": display_experiences_section,
        "required_keys": ["experiences_professionnelles"]
    },
    "🎓 Formation": {
        "function": display_education_section,
        "required_keys": ["formation"]
    },
    "🚀 Projets": {
        "function": display_projects_section,
        "required_keys": ["projets"]
    },
     "🔧 Compétences": {
        "function": display_skills_section_improved, 
        # Clés possibles pour les compétences techniques (à adapter à votre API)
        "required_keys": ["competences.techniques",  "competences.outils","langages_programmation", "outils_developpement",  "bases_donnees", "frameworks" ]
    },
    "🌐 Langues": {
        "function": display_languages_section,
        "required_keys": ["competences.langues", "langues"] 
    },
    "🏆 Certifications": {
        "function": display_certifications_section,
        "required_keys": ["certifications"]
    },
    "🎯 Centres d'Intérêt": {
        "function": display_interests_section,
        "required_keys": ["centres_interet"]
    },
    "🤝 Vie Associative": {
        "function": display_associative_life_section,
        "required_keys": ["vie_associative"]
    }
}

def main():
    """Fonction principale de l'application"""
    # En-tête principal
    st.markdown("""
    <div class="main-header">
        <h1>🧠 Analyse Intelligente de Données à partir de CV avec LLM (Llama3-2:3B) </h1>
        <p>Automatisation avancée de l'extraction et de l'évaluation des profils candidats grâce à l'IA</p>
    </div>
    """, unsafe_allow_html=True)

    # Vérification de l'état de l'API
    api_ok, api_msg = check_api_health()
    if not api_ok:
        st.error(f"🔴 Problème de connexion à l'API: {api_msg}")
        # Optionnel: Afficher les tests des endpoints pour le débogage
        if st.button("Tester les Endpoints API"):
            with st.spinner("Test en cours..."):
                endpoint_results = test_api_endpoints()
                st.write("Résultats des tests des endpoints:", endpoint_results)
        st.stop()
    else:
        st.success(f"🟢 {api_msg}")

    # Sidebar pour les paramètres
    with st.sidebar:
        # Logo en haut de la sidebar
        try:
            # Essayer chemin relatif d'abord
            logo_path = "logo/logo-unilog.png" 
            if os.path.exists(logo_path):
                 st.image(logo_path, width=400)
            else:
                 # Tenter le chemin absolu fourni initialement si relatif échoue
                 abs_logo_path = r"C:\analyse_cv_LLM\frontend\logo\logo-unilog.png"
                 if os.path.exists(abs_logo_path):
                     st.image(abs_logo_path, width=400)
                 # else:
                 #     st.caption("Logo non trouvé.")
        except Exception as e:
            st.caption(f"Erreur chargement logo: {e}")

        st.markdown("## ⚙️ Paramètres")

        # Mode d’analyse
        mode = st.selectbox(
            "Mode d'analyse",
            ["Analyse Simple", "Matching avec Offre"],  
            index=0, # Défaut sur Analyse Simple
            help="Choisissez le type d'analyse à effectuer"
        )

        st.markdown("---")
        st.markdown("### 📊 Informations")
        st.info("Cette application utilise l'IA (LLM(llama3.2:3b)) pour analyser automatiquement les CV et fournir des insights détaillés.")

        st.markdown("### 🎨 Affichage")
        show_raw_data = st.checkbox("Afficher les données brutes JSON", value=False)

    # Chargement du fichier CV
    uploaded_file = st.file_uploader(
        "📄 Téléchargez un CV (PDF)",
        type=['pdf'],
        help="Sélectionnez un fichier CV au format PDF pour l'analyse"
    )

    # Zone pour offre d'emploi si mode matching
    job_offer_data = None
    if mode == "Matching avec Offre":
        st.markdown("### 💼 Offre d'Emploi pour Matching")
        # Utiliser un expander pour ne pas surcharger l'interface par défaut
        with st.expander("Saisir les détails de l'offre", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                job_title = st.text_input("Titre du poste *", placeholder="Ex: Développeur Full Stack")
                job_company = st.text_input("Entreprise", placeholder="Ex: TechCorp")
                job_location = st.text_input("Lieu", placeholder="Ex: Paris, France")

            with col2:
                job_experience = st.text_input("Expérience requise", placeholder="Ex: 3-5 ans")
                job_contract = st.selectbox("Type de contrat", ["", "CDI", "CDD", "Stage", "Freelance", "Autre"], index=0)
                job_sector = st.text_input("Secteur", placeholder="Ex: Technologie")

            job_description = st.text_area(
                "Description du poste *",
                placeholder="Décrivez les responsabilités, missions et contexte du poste...",
                height=150 
            )

            job_requirements = st.text_area(
                "Compétences requises",
                placeholder="Listez les compétences techniques et transversales requises...",
                height=150 
            )

            # Validation simple pour activer le bouton
            if job_title.strip() and job_description.strip():
                job_offer_data = {
                    "title": job_title,
                    "company": job_company or None,
                    "location": job_location or None,
                    "experience_required": job_experience or None,
                    "contract_type": job_contract or None,
                    "sector": job_sector or None,
                    "description": job_description,
                    "required_skills": job_requirements or None
                }
            # else: Message affiché près du bouton si nécessaire

    # Bouton pour lancer l'analyse
    analysis_button_disabled = uploaded_file is None or (mode == "Matching avec Offre" and not job_offer_data)
    button_label = "🚀 Lancer l'Analyse" if mode == "Analyse Simple" else "🎯 Lancer le Matching"
    
    # Afficher un avertissement si le matching est sélectionné mais les infos manquantes
    if mode == "Matching avec Offre" and uploaded_file is not None and not job_offer_data:
        st.warning("☝️ Veuillez renseigner au moins le Titre et la Description du poste pour activer le matching.")

    if st.button(button_label, type="primary", use_container_width=True, disabled=analysis_button_disabled):
        # Double vérification avant l'appel API pour le matching
        if mode == "Matching avec Offre" and not job_offer_data:
             st.error("⚠️ Impossible de lancer le matching. Titre et Description du poste sont requis.")
        else:
            with st.spinner("🔄 Analyse en cours... Cela peut prendre quelques minutes."):
                start_time = time.time()
                result = None
                
                # --- Appel API --- 
                try:
                    if mode == "Analyse Simple":
                        result = analyze_cv(uploaded_file)
                    elif mode == "Matching avec Offre": # job_offer_data est forcément valide ici
                        result = match_cv_job(uploaded_file, job_offer_data)
                except Exception as api_call_err:
                     # Sécurité supplémentaire si une exception non gérée survient dans analyze/match
                     st.error(f"Erreur critique lors de l'appel API: {api_call_err}")
                     result = None 
                # -----------------
                
                end_time = time.time()
                processing_time = end_time - start_time

                # --- Traitement du résultat --- 
                if result is not None and isinstance(result, dict): 
                    st.balloons()
                    st.success(f"✅ Analyse terminée avec succès en {processing_time:.2f} secondes!")

                    # --- Affichage des onglets (TOUJOURS TOUS LES ONGLETS) --- 
                    if mode == "Analyse Simple":
                        st.markdown("### Résultats de l'Analyse")
                        
                        # Obtenir la liste complète des noms d'onglets définis
                        all_tab_names = list(tabs_config.keys())
                        
                        # Créer les onglets Streamlit pour TOUS les onglets définis
                        tabs = st.tabs(all_tab_names)

                        # Remplir chaque onglet
                        for i, tab_name in enumerate(all_tab_names):
                            with tabs[i]:
                                # Récupérer la fonction d'affichage associée à cet onglet
                                tab_func = tabs_config[tab_name]["function"]
                                try: 
                                    # La fonction elle-même doit gérer l'absence de données (déjà fait)
                                    tab_func(result) 
                                except Exception as e:
                                  st.warning("Aucun autre outil ou logiciel général n'a été détecté.")
                                    # st.text_area(f"Traceback {tab_name}", traceback.format_exc(), height=100)

                    elif mode == "Matching avec Offre":
                        # Pour le matching, afficher seulement l'onglet correspondant
                        st.markdown("### Résultats du Matching")
                        # Check specifically for matching_score within the valid result
                        if "matching_score" in result and result["matching_score"]: # Check if key exists AND is not empty/falsy
                             tabs = st.tabs(["🎯 Matching"])
                             with tabs[0]:
                                 try:
                                     display_matching_section(result) 
                                 except Exception as e:
                                     st.error(f"Erreur lors de l'affichage du matching: {e}")
                        # If matching_score is missing or empty, provide more context
                        elif "matching_score" not in result:
                             st.warning("La réponse de l'API ne contient pas la clé 'matching_score'. Le matching n'a peut-être pas été effectué ou a échoué côté serveur.")
                        else: # Key 'matching_score' exists but is empty/falsy (e.g., {}, None, [])
                             st.info("Aucun résultat de matching spécifique retourné par l'API.") # Changed from warning to info
                      
                    # Données brutes (optionnel)
                    if show_raw_data:
                        st.markdown("---")
                        st.markdown("### 🔍 Données Brutes (JSON)")
                        try:
                            st.json(result, expanded=False)
                        except Exception as json_display_err:
                             st.error(f"Impossible d'afficher les données brutes JSON: {json_display_err}")
                             st.text(str(result)) # Afficher en texte simple si JSON échoue

                    # Sauvegarde
                    st.markdown("---")
                    st.markdown("### 💾 Sauvegarde")
                    try:
                        report_data = {
                            "timestamp": datetime.now().isoformat(),
                            "filename": uploaded_file.name,
                            "mode": mode,
                            "processing_time_seconds": round(processing_time, 2),
                            "results": result
                        }
                        report_json = json.dumps(report_data, indent=2, ensure_ascii=False)
                        
                        # Nom de fichier plus sûr
                        safe_filename = uploaded_file.name.split('.')[0].replace(" ", "_").replace("/", "_")
                        download_filename = f"rapport_cv_{safe_filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                        
                        st.download_button(
                            label="📥 Télécharger le Rapport d'Analyse (JSON)",
                            data=report_json,
                            file_name=download_filename,
                            mime="application/json"
                        )
                    except Exception as e:
                        st.error(f"Erreur lors de la préparation du téléchargement: {e}")
                
                # Si result est None ou pas un dict après l'appel API
                elif result is None:
                     # Le message d'erreur spécifique devrait déjà avoir été affiché par analyze_cv/match_cv_job
                     st.error(f"❌ Échec de l'analyse (durée: {processing_time:.2f}s). Veuillez vérifier les messages d'erreur ci-dessus ou la console.")
                else:
                     st.error(f"❌ Type de résultat inattendu reçu de l'API (type: {type(result)}). Vérifiez la réponse de l'API.")
                     st.text(str(result))

    # Messages si le bouton est désactivé
    elif analysis_button_disabled and uploaded_file is None:
        st.info("☝️ Veuillez d'abord télécharger un fichier CV.")

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; margin-block-start: 2rem;">
        <p><strong>🧠 Analyse Intelligente de Données à partir de CV</strong></p>
        <p><small>Développé par Chaker BELTAIEF @2025</small></p>
    </div>
    """, unsafe_allow_html=True)

# Appel final
if __name__ == "__main__":
    try:
        main()
    except Exception as main_err:
        # Capturer les erreurs globales non gérées
        st.error("Une erreur critique est survenue dans l'application.")
        st.exception(main_err)

# 🧠 Analyse Intelligente de CV

Ce projet exploite la puissance de l'intelligence artificielle, notamment les modèles de langage (LLM), pour analyser automatiquement des CV au format PDF. Il permet d'extraire les informations clés, de classifier les profils professionnels et de fournir un score global de qualité du CV.


##  Fonctionnalités principales

- **Extraction intelligente d'informations** via un LLM (Llama3.2:3b)
- **Classification précise des profils** professionnels
- **Interface utilisateur intuitive** avec Streamlit
- **Analyse détaillée**  classification du profil et Score, coordonnées, expériences professionnelles, projets réalisés, formations, certifications, compétences, langues, centres d’intérêt, vie associative, etc.
- **Visualisations interactives** résultats


## 🔄 Schéma global du pipeline


    A[ CV (PDF)] --> B[🔍 Extraction de texte]
    B --> C[🧹 Prétraitement NLP]
    C --> D[ LLM: Extraction d'entités + Classification + Score]
    D --> E[ Données structurées]
    E --> F[🖥️ Interface utilisateur (Streamlit)]

🛠️ Technologies utilisées
Backend :
Python 3.10.0
LLM: model:llama3.2:3b
Flask (API Flask)
Streamlit
💻 Interface Utilisateur avec Streamlit
Un fichier streamlit_app.py est inclus pour permettre aux utilisateurs d’interagir avec le modèle (llama3.2:3b) via une interface simple.

### Prérequis
- Python 3.10.0
- pip

### Installation des dépendances

cd analyse_cv_LLM
# Créer un environnement virtuel
python -m venv venv
# Sur Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Utilisation
Démarrer l'API Backend
cd backend
python app.py
L'API sera accessible à l'adresse http://127.0.0.1:5000

Lancer l'interface Streamlit
cd frontend
streamlit run streamlit_app.py
L'interface sera disponible à l'adresse http://localhost:8501/

👨‍💻 Projet créé par Chaker Beltaief
#  Analyse Intelligente de CV

Ce projet utilise l'intelligence artificielle, notamment des modèles de langage (LLM), pour analyser automatiquement des CV au format PDF. Il extrait les informations clés, classe les profils professionnels et attribue un score global de qualité du CV.

##  Fonctionnalités principales

- **Extraction intelligente d'informations** à l'aide du modèle LLM (Llama3.2:3b)
- **Interface utilisateur intuitive** développée avec Streamlit
- **Analyse détaillée** : classification du profil, score global, coordonnées, expériences professionnelles, projets réalisés, formations, certifications, compétences, langues, centres d'intérêt, vie associative, etc.
- **Visualisations interactives** des résultats

## Schéma global du pipeline

```
graph TD
    A[CV (PDF)] --> B[🔍 Extraction de texte]
    B --> C[🧹 Prétraitement NLP]
    C --> D[LLM : Extraction d'entités + Classification + Score]
    D --> E[Données structurées]
    E --> F[🖥️ Interface utilisateur (Streamlit)]
```

##  Technologies utilisées

### Backend
- Python 3.10.0
- LLM : Llama3.2:3b
- Flask (API)
- Streamlit

### Frontend
- Interface utilisateur avec Streamlit (fichier `streamlit_app.py`)

##  Prérequis

- Python 3.10.0
- pip
- Environnement virtuel 
 # Installation


1. Créez et activez un environnement virtuel :
   ```
   python -m venv venv
   # Sur Windows : venv\Scripts\activate
   ```
2. Installez les dépendances :
    ```
    pip install -r requirements.txt

    ```

##  Utilisation

1. **Démarrer l'API Backend** :
   ```
   cd api
   python app.py
   ```
   L'API sera accessible à l'adresse : `http://127.0.0.1:5000`

2. **Lancer l'interface Streamlit** :
   ```
   cd frontend
   streamlit run streamlit_app.py
   ```
   L'interface sera disponible à l'adresse : `http://localhost:8501`

## 👨‍💻 Auteur
Projet créé par **Chaker Beltaief**
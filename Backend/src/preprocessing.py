import os
import re
import string
import pandas as pd
import nltk
import sys

from nltk.tokenize import RegexpTokenizer, word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# Télécharger les ressources nécessaires de NLTK
nltk.download('stopwords')
nltk.download('punkt')
nltk.download('wordnet')

# Fonction de prétraitement
def preprocess(sentence):
    sentence = str(sentence).lower()

    # Supprimer les balises HTML
    sentence = sentence.replace('{html}', "")
    cleanr = re.compile('<.*?>')
    sentence = re.sub(cleanr, '', sentence)

    # Supprimer les URLs
    sentence = re.sub(r'http\S+', '', sentence)

    # Supprimer les chiffres
    sentence = re.sub('[0-9]+', '', sentence)

    # Supprimer la ponctuation
    sentence = sentence.translate(str.maketrans('', '', string.punctuation))

    # Tokenisation
    tokenizer = RegexpTokenizer(r'\w+')
    tokens = tokenizer.tokenize(sentence)

    # Stopwords
    stop_words = set(stopwords.words('english'))

    # Lemmatization
    lemmatizer = WordNetLemmatizer()
    filtered_words = [
        lemmatizer.lemmatize(w) for w in tokens if len(w) > 2 and w not in stop_words
    ]

    return ' '.join(filtered_words)

# ✅ CHEMINS - Ajuste ce nom de fichier si besoin
input_path = r'C:\analyse_cv_LLM\Backend\data\raw_resume\raw_resume.csv'
output_path = r'C:\analyse_cv_LLM\Backend\data\cleaned_resume\cleaned_resume.csv'

# Vérifier que le fichier existe
if not os.path.exists(input_path):
    print(f"❌ Fichier introuvable : {input_path}")
    dir_path = os.path.dirname(input_path)
    print(f"📁 Contenu de {dir_path} :")
    for file in os.listdir(dir_path):
        print(f" - {file}")
    sys.exit()

# Créer le dossier de sortie s’il n’existe pas
os.makedirs(os.path.dirname(output_path), exist_ok=True)

# Charger les données
resume_data = pd.read_csv(input_path)

# Appliquer le prétraitement
resume_data['Resume_Details'] = resume_data['Raw_Details'].apply(preprocess)

# Supprimer la colonne brute
resume_data.drop(['Raw_Details'], axis=1, inplace=True)

# Sauvegarder le fichier nettoyé
resume_data.to_csv(output_path, index=False)
print(f"✅ Données nettoyées enregistrées dans : {output_path}")

# ---- Analyse de fréquence des mots ----
oneSetOfStopWords = set(stopwords.words('english') + ['``', "''"])
totalWords = []

Sentences = resume_data['Resume_Details'].values
cleanedSentences = ""

for records in Sentences:
    cleanedText = preprocess(records)
    cleanedSentences += cleanedText + " "
    requiredWords = word_tokenize(cleanedText)
    for word in requiredWords:
        if word not in oneSetOfStopWords and word not in string.punctuation:
            totalWords.append(word)

# Statistiques de fréquence
wordfreqdist = nltk.FreqDist(totalWords)
mostcommon = wordfreqdist.most_common(50)

print("\n Les 50 mots les plus fréquents :")
for word, freq in mostcommon:
    print(f"{word}: {freq}")
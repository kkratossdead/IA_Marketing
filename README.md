# Auto Creative Lab – Gemini

## Prérequis
- Un PC sous Windows, macOS ou Linux
- Accès à Internet
- Une clé API Gemini (Google)

## Installation complète (PC sans Python)

1. **Installer Python**
   - Rendez-vous sur https://www.python.org/downloads/
   - Téléchargez la dernière version stable (3.10 ou supérieure recommandée)
   - Pendant l'installation, cochez la case **"Add Python to PATH"** puis terminez l'installation

2. **Ouvrir un terminal**
   - Windows : Touche Windows, tapez "cmd" ou "PowerShell"
   - macOS : Applications > Utilitaires > Terminal
   - Linux : Ctrl+Alt+T

3. **Aller dans le dossier du projet**
   ```
   cd chemin/vers/le/dossier/product-search
   ```
   (Remplacez par le chemin réel)

4. **Créer un environnement virtuel (recommandé)**
   ```
   python -m venv .venv
   ```
   - Activez-le :
     - Windows :
       ```
       .venv\Scripts\activate
       ```
     - macOS/Linux :
       ```
       source .venv/bin/activate
       ```

5. **Installer les dépendances**
   ```
   pip install -r requirements.txt
   ```

6. **Configurer la clé API Gemini**
   - Créez un fichier `.env` à la racine du projet avec :
     ```
     GEMINI_API_KEY=VOTRE_CLE_API_ICI
     ```

7. **Lancer l'application**
   ```
   streamlit run app_streamlit.py
   ```

8. **Utilisation**
   - L'application s'ouvre dans votre navigateur.
   - Entrez votre clé API Gemini si elle n'est pas détectée automatiquement.
   - Ajoutez vos images et prompts, puis générez !

---

**Dépannage**
- Si une commande échoue, vérifiez que Python et pip sont bien installés (commande `python --version` et `pip --version`).
- Pour réinstaller les dépendances :
  ```
  pip install --upgrade --force-reinstall -r requirements.txt
  ```

**Sécurité**
- Ne partagez jamais votre clé API publiquement.
- Utilisez un environnement virtuel pour isoler les dépendances.

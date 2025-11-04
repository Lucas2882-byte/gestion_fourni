import streamlit as st
st.set_page_config(page_title="Gestion Avis", layout="wide")
if "connecte" not in st.session_state:
    st.session_state.connecte = False
if "utilisateur" not in st.session_state:
    st.session_state.utilisateur = None
if "role" not in st.session_state:
    st.session_state.role = None
import sqlite3
from datetime import datetime, timedelta
import random
import pandas as pd
import time
import base64
import requests
import os
from datetime import datetime
from streamlit.components.v1 import html
import gspread
import streamlit as st
import calendar
import plotly.express as px
import threading

st.markdown("""
<style>
    .st-expander {
        transition: all 0.3s ease-in-out;
    }
</style>
""", unsafe_allow_html=True)

def afficher_carte_fiches(conn):
    st.subheader("🗺️ Répartition des fiches par localité")

    # Collecte des localités dans toutes les tables
    localites = set()
    for table in category_map.values():
        try:
            cursor_fiches.execute(f"SELECT DISTINCT localite FROM {table}")
            localites.update(row[0] for row in cursor_fiches.fetchall() if row[0])
        except:
            continue

    localites = sorted(localites)

    for loc in localites:
        with st.expander(f"📍 {loc}", expanded=False):
            nb_couvreur = 0
            nb_autres = 0

            for cat, table in category_map.items():
                try:
                    cursor_fiches.execute(f"SELECT COUNT(*) FROM {table} WHERE localite = ?", (loc,))
                    count = cursor_fiches.fetchone()[0]
                    if "COUVREUR" in cat.upper():
                        nb_couvreur += count
                    else:
                        nb_autres += count
                except:
                    continue

            st.markdown(f"""
                <div style="background:#1c1c1c;padding:16px;border-radius:12px;margin-bottom:10px;">
                    <p style="font-size:16px;margin-bottom:8px;">
                        🧱 <b>Couvreurs</b> : <span style="color:#f39c12;font-weight:bold;">{nb_couvreur}</span> fiche(s)
                    </p>
                    <p style="font-size:16px;">
                        🛠️ <b>Autres catégories</b> : <span style="color:#1abc9c;font-weight:bold;">{nb_autres}</span> fiche(s)
                    </p>
                </div>
            """, unsafe_allow_html=True)
            
def afficher_dashboard_admin(conn):
    st.subheader("📊 Suivi global des avis (et par utilisateur)")

    today = datetime.today().date()
    jours = {
        "Aujourd'hui": today,
        "Demain": today + timedelta(days=1),
        "Après-demain": today + timedelta(days=2)
    }

    utilisateurs = ["olaf", "alex"]

    for label, date_obj in jours.items():
        total_global = 0
        utilisateurs_data = {}

        if st.button(f"⚖️ Rééquilibrer la charge {label} (60% Olaf / 40% Alex)", key=f"balance_{label}"):
            fiches_cible = []
        
            for table in category_map.values():
                try:
                    cursor_fiches.execute(
                        f"""
                        SELECT id FROM {table}
                        WHERE DATE(prochain_avis) = DATE(?)
                          AND LOWER(assigne_a) IN ('olaf', 'alex')
                        """,
                        (date_obj.strftime("%Y-%m-%d"),)
                    )
                    rows = cursor_fiches.fetchall()
                    for row in rows:
                        fiches_cible.append((table, row[0]))
                except:
                    continue
        
            total = len(fiches_cible)
            if total < 2:
                st.info(f"ℹ️ Pas assez de fiches Olaf/Alex à équilibrer pour {label}.")
            else:
                nb_olaf = int(round(total * 0.6))
                nb_alex = total - nb_olaf
        
                random.shuffle(fiches_cible)
                nouvelles_fiches_olaf = fiches_cible[:nb_olaf]
                nouvelles_fiches_alex = fiches_cible[nb_olaf:]
        
                for table, fid in nouvelles_fiches_olaf:
                    cursor_fiches.execute(f"UPDATE {table} SET assigne_a = 'olaf' WHERE id = ?", (fid,))
                for table, fid in nouvelles_fiches_alex:
                    cursor_fiches.execute(f"UPDATE {table} SET assigne_a = 'alex' WHERE id = ?", (fid,))
        
                conn_fiches.commit()
                st.success(f"✅ Rééquilibrage effectué ({nb_olaf} Olaf / {nb_alex} Alex) pour {label}")
                st.rerun()


        for user in utilisateurs:
            total_user = 0
            for table in category_map.values():
                try:
                    cursor_fiches.execute(
                        f"""
                        SELECT COUNT(*) FROM {table}
                        WHERE DATE(prochain_avis) = DATE(?)
                          AND LOWER(COALESCE(assigne_a, '')) = ?
                        """,
                        (date_obj.strftime("%Y-%m-%d"), user)
                    )
                    total_user += cursor_fiches.fetchone()[0]
                except:
                    continue
            utilisateurs_data[user] = total_user
            total_global += total_user

        # Affichage global
        st.markdown(f"""
        <div style="background:#222;padding:14px;margin:10px 0;border-radius:8px;">
            <b style="color:white;">🗓 {label} :</b>
            <span style="float:right;color:#2ecc71;font-weight:bold;">{total_global} fiche(s) à traiter</span>
        </div>
        """, unsafe_allow_html=True)

        # Affichage par utilisateur
        for user, count in utilisateurs_data.items():
            st.markdown(f"""
            <div style="background:#333;padding:10px;margin:6px 0 16px 20px;border-left:5px solid #2ecc71;border-radius:6px;">
                👤 <b>{user.capitalize()}</b> : <span style="color:#2ecc71;font-weight:bold;">{count}</span> fiche(s)
            </div>
            """, unsafe_allow_html=True)









import hashlib
mdp = "olafmotdepassegoogle"
print(hashlib.sha256(mdp.encode()).hexdigest())
def hasher_mot_de_passe(mdp):
    return hashlib.sha256(mdp.encode()).hexdigest()

def verifier_utilisateur(nom, mot_de_passe):
    conn = sqlite3.connect("comptes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT mot_de_passe_hash, role FROM comptes WHERE nom_utilisateur = ?", (nom,))
    row = cursor.fetchone()
    conn.close()

    if row:
        hash_stocke, role = row
        if hasher_mot_de_passe(mot_de_passe) == hash_stocke:
            return True, role
    return False, None

# Fonctions GitHub pour upload auto
try:
    GITHUB_TOKEN = st.secrets.get("GH_TOKEN", "")
    if not GITHUB_TOKEN and "GH_TOKEN" in os.environ:
        GITHUB_TOKEN = os.environ["GH_TOKEN"]
except Exception:
    GITHUB_TOKEN = os.environ.get("GH_TOKEN", "")
GITHUB_REPO = "Lucas2882-byte/gestion_fourni"
GITHUB_BRANCH = "main"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents"


def upload_db_to_github(filepath, repo_filename):
    if not GITHUB_TOKEN:
        return

    snapshot_path = filepath + ".snapshot"
    try:
        _snapshot_sqlite(filepath, snapshot_path, conn_existing=None)
        path_to_read = snapshot_path
    except Exception:
        path_to_read = filepath

    with open(path_to_read, "rb") as f:
        local_bytes = f.read()
    local_b64 = base64.b64encode(local_bytes).decode()

    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    get_resp = requests.get(f"{GITHUB_API_URL}/{repo_filename}", headers=headers, timeout=10)
    sha = None
    if get_resp.status_code == 200:
        data = get_resp.json()
        sha = data.get("sha")
        if data.get("encoding") == "base64" and data.get("content"):
            if data["content"].strip() == local_b64.strip():
                return

    data_put = {"message": f"update {repo_filename}", "content": local_b64, "branch": GITHUB_BRANCH}
    if sha:
        data_put["sha"] = sha

    put_resp = requests.put(f"{GITHUB_API_URL}/{repo_filename}", headers=headers, json=data_put, timeout=20)

def upload_db_to_github_async(filepath, repo_filename):
    """Lance l'upload GitHub en arrière-plan sans bloquer l'interface"""
    thread = threading.Thread(target=upload_db_to_github, args=(filepath, repo_filename), daemon=True)
    thread.start()



import os, json, hashlib

def _sha256_file(path:str)->str:
    h = hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def _snapshot_sqlite(src_path: str, snapshot_path: str, conn_existing=None):
    # copie transactionnelle de la DB (sécurisée pendant que l'app l'utilise)
    if conn_existing is None:
        conn = sqlite3.connect(src_path, check_same_thread=False)
        owns_conn = True
    else:
        conn = conn_existing
        owns_conn = False
    backup = sqlite3.connect(snapshot_path)
    with backup:
        conn.backup(backup)
    backup.close()
    if owns_conn:
        conn.close()

def download_db_from_github(repo_filename: str, local_path: str) -> bool:
    """
    Télécharge la DB depuis GitHub si elle existe et si différente de la locale.
    Retourne True si un nouveau fichier a été écrit.
    """
    if not GITHUB_TOKEN:
        # pas de token => on ne fait rien
        return False

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    resp = requests.get(f"{GITHUB_API_URL}/{repo_filename}", headers=headers, timeout=15)

    if resp.status_code == 404:
        # pas encore de fichier dans le repo -> rien à faire
        return False
    if resp.status_code >= 400:
        try:
            err = resp.json()
        except Exception:
            err = {"message": resp.text}
        st.warning(f"Impossible de récupérer {repo_filename} sur GitHub ({resp.status_code}) : {err.get('message','')}")
        return False

    data = resp.json()

    # Si gros fichier, utiliser download_url
    download_url = data.get("download_url")
    content_b64 = data.get("content", "")
    encoding = data.get("encoding", "")
    truncated = data.get("truncated", False)
    
    if (not content_b64 or encoding != "base64" or truncated) and download_url:
        raw = requests.get(download_url, headers=headers, timeout=30)
        if raw.status_code >= 400:
            st.warning(f"Impossible de télécharger {repo_filename} (raw): {raw.status_code}")
            return False
        remote_bytes = raw.content
    else:
        if encoding != "base64" or not content_b64:
            st.warning("Réponse GitHub inattendue (pas de contenu base64).")
            return False
        remote_bytes = base64.b64decode(content_b64)
    
    remote_hash = hashlib.sha256(remote_bytes).hexdigest()
    
    if os.path.exists(local_path):
        local_hash = _sha256_file(local_path)
        if local_hash == remote_hash:
            return False  # déjà à jour
    
    # sauvegarde l'ancien en .bak puis écrit
    if os.path.exists(local_path):
        try:
            os.replace(local_path, local_path + ".bak")
        except Exception:
            pass
    
    with open(local_path, "wb") as f:
        f.write(remote_bytes)
    
    return True


# Connexions aux bases
# --- SYNC DOWN : récupérer la dernière DB depuis GitHub au démarrage ---
download_db_from_github("fiches.db", "fiches.db")
download_db_from_github("fiches_final.db", "fiches_final.db")
conn_fiches = sqlite3.connect("fiches.db", check_same_thread=False)
cursor_fiches = conn_fiches.cursor()

conn_avis = sqlite3.connect("fiches_final.db", check_same_thread=False)
cursor_avis = conn_avis.cursor()

# Rechargement dynamique des catégories depuis les bases
def charger_categories():
    cursor_fiches.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'fiches_%'")
    fiches_tables = [row[0] for row in cursor_fiches.fetchall()]

    cursor_avis.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'avis_%'")
    avis_tables = [row[0] for row in cursor_avis.fetchall()]

    category_map = {}
    avis_table_map = {}

    for ft in fiches_tables:
        cat = ft.replace("fiches_", "").replace("_", " ").upper()
        category_map[cat] = ft

    for at in avis_tables:
        cat = at.replace("avis_", "").replace("_", " ").upper()
        avis_table_map[cat] = at

    return category_map, avis_table_map

category_map, avis_table_map = charger_categories()

from datetime import date
import sqlite3, time as _time

def _exec_with_retry(conn, sql, params=(), retries=4, base_delay=0.2):
    for i in range(retries):
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            conn.commit()
            try:
                cur2 = conn.cursor()
                cur2.execute("SELECT changes()")
                return cur2.fetchone()[0] or 0
            except Exception:
                return 0
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and i < retries - 1:
                _time.sleep(base_delay * (2 ** i))
            else:
                raise

def backfill_prochain_avis_safe():
    """
    Répare l’historique sans tout toucher :
    - prochain_avis IS NULL
    - prochain_avis = dernier_avis
    - DATE(prochain_avis) <= DATE(dernier_avis)
    """
    total = 0
    for _, table in category_map.items():
        sql = f"""
        UPDATE {table}
        SET prochain_avis = DATE(dernier_avis, '+' || COALESCE(delai, 1) || ' days')
        WHERE dernier_avis IS NOT NULL
          AND (
                prochain_avis IS NULL
             OR prochain_avis = dernier_avis
             OR DATE(prochain_avis) <= DATE(dernier_avis)
          )
        """
        try:
            total += _exec_with_retry(conn_fiches, sql)
        except Exception as e:
            print(f"[backfill_safe] {table}: {e}")
    return total

def backfill_prochain_avis_force():
    """
    Recalcule pour TOUTES les lignes ayant dernier_avis non NULL.
    Utile pour un réalignement complet.
    """
    total = 0
    for _, table in category_map.items():
        sql = f"""
        UPDATE {table}
        SET prochain_avis = DATE(dernier_avis, '+' || COALESCE(delai, 1) || ' days')
        WHERE dernier_avis IS NOT NULL
        """
        try:
            total += _exec_with_retry(conn_fiches, sql)
        except Exception as e:
            print(f"[backfill_force] {table}: {e}")
    return total


def create_triggers_for_single_table(cursor, conn, table):
    """Crée les triggers pour une seule table (optimisation pour la création de catégorie)"""
    trig_ins = f"trg_{table}_after_insert"
    trig_upd = f"trg_{table}_after_update"

    # 1) Après INSERT : calcule prochain_avis si dernier_avis non nul
    cursor.execute(f"""
    CREATE TRIGGER IF NOT EXISTS {trig_ins}
    AFTER INSERT ON {table}
    FOR EACH ROW
    WHEN NEW.dernier_avis IS NOT NULL
    BEGIN
        UPDATE {table}
        SET prochain_avis = DATE(NEW.dernier_avis, '+' || COALESCE(NEW.delai, 1) || ' days')
        WHERE id = NEW.id;
    END;
    """)

    # 2) Après UPDATE de dernier_avis OU delai : recalcule prochain_avis
    cursor.execute(f"""
    CREATE TRIGGER IF NOT EXISTS {trig_upd}
    AFTER UPDATE OF dernier_avis, delai ON {table}
    FOR EACH ROW
    WHEN NEW.dernier_avis IS NOT NULL
    BEGIN
        UPDATE {table}
        SET prochain_avis = DATE(NEW.dernier_avis, '+' || COALESCE(NEW.delai, 1) || ' days')
        WHERE id = NEW.id
          AND (prochain_avis IS NULL
               OR prochain_avis != DATE(NEW.dernier_avis, '+' || COALESCE(NEW.delai, 1) || ' days'));
    END;
    """)

    conn.commit()

def create_triggers_for_fiches(cursor, conn, category_map):
    for _, table in category_map.items():
        create_triggers_for_single_table(cursor, conn, table)

# crée/assure l’existence des triggers au lancement
create_triggers_for_fiches(cursor_fiches, conn_fiches, category_map)


# Style général
theme_css = '''
<style>
    html, body, [data-testid="stApp"] {
        background-color: #0e1117 !important;
        color: white !important;
    }
    label, .stSelectbox label, .css-1cpxqw2 {
        color: white !important;
    }
    button[kind="secondary"] {
        color: white !important;
        background-color: #0e1117 !important;
        border: 1px solid #555 !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
    }
    button[kind="secondary"]:hover {
        background-color: #1a1f25 !important;
        border-color: #888 !important;
    }
</style>
'''
st.markdown(theme_css, unsafe_allow_html=True)

st.markdown("<h1 style='text-align:center;'>📜 Gestion Avis</h1>", unsafe_allow_html=True)
if not st.session_state.connecte:
    st.subheader("🔐 Connexion requise")
    nom = st.text_input("Nom d'utilisateur")
    mdp = st.text_input("Mot de passe", type="password")
    
    if st.button("Se connecter"):
        valide, role = verifier_utilisateur(nom, mdp)
        if valide:
            st.session_state.connecte = True
            st.session_state.utilisateur = nom
            st.session_state.role = role
            st.success(f"Bienvenue {nom} 👋")
            st.rerun()
        else:
            st.error("Identifiants incorrects ❌")
    st.stop()


today = datetime.now().date()

# Auth
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False
if "fiche_loaded" not in st.session_state:
    st.session_state.fiche_loaded = False

def parse_date(val):
    try:
        return val if isinstance(val, datetime) else datetime.strptime(val, "%Y-%m-%d")
    except Exception:
        return datetime.today()
fiche = None 

if not st.session_state.admin_mode:
    with st.expander("🔧 Connexion admin", expanded=True):
        pwd = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter"):
            if pwd == "Aurasing1!":
                st.session_state.admin_mode = True
                st.rerun()
            else:
                st.error("Mot de passe incorrect ❌")

# Ajout/suppression de catégorie si admin
if st.session_state.admin_mode:
    with st.expander("➕ Ajouter ou supprimer une catégorie"):
        new_cat = st.text_input("Nom de la nouvelle catégorie (ex: MAÇON)", key="new_cat_input")
        if st.button("Créer la catégorie", key="create_cat"):
            if new_cat:
                cat_clean = new_cat.strip().upper().replace(" ", "_").replace("É", "E").replace("È", "E")
                table_fiche = f"fiches_{cat_clean.lower()}"
                table_avis = f"avis_{cat_clean.lower()}"

                # 1. Créer les tables
                cursor_fiches.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table_fiche} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nom_de_la_fiche TEXT,
                        categorie TEXT,
                        lien_fiche TEXT,
                        bref_descriptif TEXT,
                        dernier_avis TEXT,
                        prochain_avis TEXT,
                        observations TEXT,
                        delai INTEGER DEFAULT 1,
                        localite TEXT,
                        duree_cycle INTEGER DEFAULT 3,
                        type_avis INTEGER DEFAULT 0,
                        assigne_a TEXT,
                        type TEXT DEFAULT 'valide',
                        nom TEXT,
                        id_texte_utilise INTEGER
                    )
                """)
                conn_fiches.commit()
                
                cursor_avis.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table_avis} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        texte TEXT,
                        pris INTEGER DEFAULT 0
                    )
                """)
                conn_avis.commit()

                # 2. Créer les triggers UNIQUEMENT pour la nouvelle table (rapide)
                create_triggers_for_single_table(cursor_fiches, conn_fiches, table_fiche)
                
                # 3. Lancer la synchronisation GitHub en arrière-plan (non-bloquant)
                upload_db_to_github_async("fiches_final.db", "fiches_final.db")
                upload_db_to_github_async("fiches.db", "fiches.db")
                
                # 4. Affichage immédiat - l'utilisateur voit tout de suite les nouvelles tables
                st.success(f"✅ Catégorie '{new_cat}' ajoutée avec succès.")
                st.rerun()

            else:
                st.warning("⚠️ Merci de saisir un nom de catégorie.")

        cat_to_delete = st.selectbox("Catégorie à supprimer", list(category_map.keys()), key="cat_del")
        if st.button("Supprimer la catégorie", key="delete_cat"):
            table_fiche = category_map[cat_to_delete]
            table_avis = avis_table_map[cat_to_delete]

            cursor_fiches.execute(f"DROP TABLE IF EXISTS {table_fiche}")
            cursor_avis.execute(f"DROP TABLE IF EXISTS {table_avis}")
            conn_fiches.commit()
            conn_avis.commit()
            
            upload_db_to_github_async("fiches_final.db", "fiches_final.db")
            upload_db_to_github_async("fiches.db", "fiches.db")

            st.success(f"❌ Catégorie '{cat_to_delete}' supprimée avec succès.")
            st.rerun()

# ADMIN
if st.session_state.admin_mode:
    if st.button("🚪 Se déconnecter"):
        st.session_state.admin_mode = False
        st.rerun()
    
    # 🧹 Réparation historique des prochains avis
    st.markdown("### 🧹 Réparer l’historique des `prochain_avis`")
    c1, c2 = st.columns(2)

    with c1:
        if st.button("Réparer (mode SÛR)", key="btn_backfill_safe"):
            n = backfill_prochain_avis_safe()
            st.success(f"Mode SÛR terminé — {n} ligne(s) mise(s) à jour.")
            st.rerun()
        
    with c2:
        if st.button("Tout recalculer (mode FORCE)", key="btn_backfill_force"):
            n = backfill_prochain_avis_force()
            st.success(f"Mode FORCE terminé — {n} ligne(s) à jour.")
            st.rerun()


    tab1, tab2, tab3 = st.tabs(["👢 Fiches", "📜 Textes d'avis", "📊 Dashboard"])

    with tab3:
        sous_tab1, sous_tab2 = st.tabs(["📊 Résumé par jour", "🗺️ Répartition des fiches"])
    
        with sous_tab1:
            afficher_dashboard_admin(conn_fiches)
    
        with sous_tab2:
            afficher_carte_fiches(conn_fiches)

    with tab1:
        st.subheader("👢 Gestion des Fiches")
        cat = st.selectbox("📁 Choisir une catégorie de fiches", list(category_map.keys()), key="fiche_cat")
        table = category_map[cat]

        df = pd.read_sql_query(f"SELECT * FROM {table}", conn_fiches)

        if "prochain_avis" in df.columns:
            df["✅"] = df["prochain_avis"].apply(lambda d: "✅" if d and d <= today.strftime("%Y-%m-%d") else "❌")

        st.dataframe(df.drop(columns=["etat"], errors="ignore"), use_container_width=True, height=600)

        with st.expander("➕ Ajouter une fiche"):
            col1, col2 = st.columns(2)
            with col1:
                nom = st.text_input("Nom de la fiche")
                lien = st.text_input("Lien Google Maps")
                delai = st.number_input("Délai (en jours)", min_value=1, max_value=30, value=1)
                duree_cycle = st.number_input("Durée du cycle (jours)", min_value=1, value=30, key="add_duree_cycle")
            with col2:
                dernier = st.date_input("Dernier avis")
                prochain = st.date_input("Prochain avis")
                type_avis = st.selectbox("Type d'avis", options=[0, 1], 
                                         format_func=lambda x: "⭐️⭐️⭐️⭐️⭐️" if x == 0 else "⭐️⭐️⭐️⭐️", 
                                         key="add_type_avis")
                localites_possibles = ["Paris", "Nord", "Strasbourg", "Lyon", "Marseille", "Sud-Ouest", "Tours", "Rennes", "Suisse", "Belgique"]
                localite = st.selectbox("Localité", localites_possibles, key="add_localite")
            desc = st.text_area("Descriptif")
            obs = st.text_area("Observations")
            
            assigne_a = st.selectbox("👤 Assigner à", ["", "alex", "olaf", "leiko", "teiko", "gerald", "fournigoogle", "fourniavis"], key="add_assign")
            
            # Nouveaux champs
            type_fiche = st.selectbox("Type", options=["valide", "red", "bateau","bateau2"], key="add_type_fiche")
            nom_entreprise = st.text_input("Nom de l'entreprise", key="add_nom_entreprise")

            if st.button("Ajouter", key="add_fiche"):
                cursor_fiches.execute(f"""
                    INSERT INTO {table} (
                        nom_de_la_fiche, categorie, lien_fiche, bref_descriptif, 
                        dernier_avis, prochain_avis, observations, delai, 
                        duree_cycle, type_avis, localite, assigne_a, type, nom
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    nom, cat, lien, desc, 
                    dernier.strftime("%Y-%m-%d"), prochain.strftime("%Y-%m-%d"), 
                    obs, delai, duree_cycle, type_avis, localite, assigne_a, type_fiche, nom_entreprise
                ))

                conn_fiches.commit()
                upload_db_to_github("fiches.db", "fiches.db")
                st.success("Fiche ajoutée avec succès !")
                st.rerun()



        with st.expander("✏️ Modifier une fiche"):
            modif_id = st.number_input("ID de la fiche à modifier", min_value=1, step=1, key="modif_id")
        
            if st.button("Charger la fiche"):
                cursor_fiches.execute(f"SELECT * FROM {table} WHERE id = ?", (modif_id,))
                fiche = cursor_fiches.fetchone()
                if fiche:
                    noms_colonnes = [col[0] for col in cursor_fiches.description]
                    st.session_state.fiche_data = dict(zip(noms_colonnes, fiche))
                    st.session_state.fiche_loaded = True
                else:
                    st.warning("Fiche introuvable")
        
            if st.session_state.get("fiche_loaded"):
                fiche_data = st.session_state.fiche_data
        
                for key in ["nom_de_la_fiche", "lien_fiche", "bref_descriptif", "observations"]:
                    fiche_data[key] = st.text_input(key, value=fiche_data.get(key, ""), key=f"mod_{key}")
        
                fiche_data["localite"] = st.text_input("Localité", value=fiche_data.get("localite", ""), key="mod_localite")
        
                fiche_data["dernier_avis"] = st.date_input("Dernier avis", value=parse_date(fiche_data["dernier_avis"]), key="mod_dernier")
                fiche_data["prochain_avis"] = st.date_input("Prochain avis", value=parse_date(fiche_data["prochain_avis"]), key="mod_prochain")
                fiche_data["delai"] = st.number_input("Délai", value=int(fiche_data.get("delai", 1)), min_value=1, key="mod_delai")
                assignables = ["", "alex", "olaf", "leiko", "teiko", "gerald", "fournigoogle", "fourniavis"]
                valeur_actuelle = fiche_data.get("assigne_a")
                if not isinstance(valeur_actuelle, str):
                    valeur_actuelle = ""
                else:
                    valeur_actuelle = valeur_actuelle.strip().lower()

                if valeur_actuelle not in assignables:
                    valeur_actuelle = ""
                
                fiche_data["assigne_a"] = st.selectbox("👤 Assigné à", assignables, 
                    index=assignables.index(valeur_actuelle), 
                    key="mod_assigne_a")

                # Convertir duree_cycle uniquement si c'est un entier ou chiffre
                try:
                    duree_cycle_val = int(fiche_data.get("duree_cycle", 30) or 30)
                except (ValueError, TypeError):
                    duree_cycle_val = 30
                
                fiche_data["duree_cycle"] = st.number_input("Durée du cycle (jours)", value=duree_cycle_val, min_value=1, key="mod_duree_cycle")
                fiche_data["type_avis"] = st.selectbox("Type d'avis", options=[0, 1], format_func=lambda x: "⭐️⭐️⭐️⭐️⭐️" if x == 0 else "⭐️⭐️⭐️⭐️", key="mod_type_avis")

                
                # Nouveaux champs
                types_possibles = ["valide", "red", "bateau","bateau2"]
                type_actuel = fiche_data.get("type", "valide")
                if type_actuel not in types_possibles:
                    type_actuel = "valide"
                fiche_data["type"] = st.selectbox("Type", options=types_possibles, index=types_possibles.index(type_actuel), key="mod_type_fiche")
                fiche_data["nom"] = st.text_input("Nom de l'entreprise", value=fiche_data.get("nom", ""), key="mod_nom_entreprise")
        
                if st.button("Mettre à jour"):
                    cursor_fiches.execute(f"""
                
                        UPDATE {table}
                        SET nom_de_la_fiche=?, lien_fiche=?, bref_descriptif=?, observations=?, localite=?, 
                            dernier_avis=?, prochain_avis=?, delai=?, duree_cycle=?, type_avis=?, assigne_a=?, type=?, nom=?
                        WHERE id=?
                    """, (
                        fiche_data["nom_de_la_fiche"], fiche_data["lien_fiche"], fiche_data["bref_descriptif"], fiche_data["observations"],
                        fiche_data["localite"], fiche_data["dernier_avis"].strftime("%Y-%m-%d"),
                        fiche_data["prochain_avis"].strftime("%Y-%m-%d"),
                        fiche_data["delai"], fiche_data["duree_cycle"], fiche_data["type_avis"], fiche_data["assigne_a"], fiche_data["type"], fiche_data["nom"], modif_id
                    ))

                    conn_fiches.commit()
                    upload_db_to_github("fiches.db", "fiches.db")
                    st.success("Fiche mise à jour ✅")
                    st.session_state.fiche_loaded = False
                    st.rerun()



        with st.expander("🗑️ Supprimer une fiche"):
            delete_id = st.number_input("ID de la fiche à supprimer", min_value=1, step=1, key="del_fiche")
            confirm_del = st.checkbox("Je confirme la suppression de cette fiche")
            if st.button("Supprimer"):
                if confirm_del:
                    cursor_fiches.execute(f"DELETE FROM {table} WHERE id = ?", (delete_id,))
                    conn_fiches.commit()
                    upload_db_to_github("fiches.db", "fiches.db")
                    st.success("Fiche supprimée ❌")
                    st.rerun()
                else:
                    st.info("Merci de cocher la confirmation avant de supprimer.")
                    
        
    with tab2:
        st.subheader("📜 Textes d'avis")
        avis_cat = st.selectbox("🗂 Choisir une catégorie d'avis", list(avis_table_map.keys()), key="avis_cat")
        table_avis = avis_table_map[avis_cat]

        df_avis = pd.read_sql_query(f"SELECT * FROM {table_avis}", conn_avis)
        st.dataframe(df_avis, use_container_width=True, height=600)

        cursor_avis.execute(f"SELECT COUNT(*) FROM {table_avis} WHERE pris = 1")
        nb_pris = cursor_avis.fetchone()[0]
        
        if nb_pris > 0:
            st.info(f"ℹ️ {nb_pris} texte(s) déjà utilisé(s) (pris = 1)")
            if st.button("🔄 Réinitialiser tous les textes (remettre à prendre)", key="reset_pris"):
                cursor_avis.execute(f"UPDATE {table_avis} SET pris = 0")
                conn_avis.commit()
                upload_db_to_github("fiches_final.db", "fiches_final.db")
                st.success("✅ Tous les textes ont été réinitialisés !")
                st.rerun()

        with st.expander("➕ Ajouter un texte d'avis"):
            texte = st.text_area("Texte")
            if st.button("Ajouter", key="add_avis"):
                cursor_avis.execute(f"INSERT INTO {table_avis} (texte) VALUES (?)", (texte,))
                conn_avis.commit()
                upload_db_to_github("fiches_final.db", "fiches_final.db")
                st.success("Texte ajouté ✅")
                st.rerun()

        with st.expander("📥 Importer plusieurs textes d'avis en masse"):
            st.markdown("""
            **Mode d'emploi :**
            - Collez vos textes d'avis ci-dessous
            - Chaque ligne doit être entourée de guillemets : `"Votre texte d'avis ici"`
            - Un avis par ligne
            - Les lignes sans guillemets seront ignorées
            """)
            
            textes_bulk = st.text_area(
                "Collez vos textes d'avis (un par ligne, entre guillemets)",
                height=300,
                key="bulk_avis",
                placeholder='"Excellent service, très professionnel !"\n"Travail impeccable, je recommande vivement."\n"Équipe sympathique et efficace."'
            )
            
            if st.button("Importer les avis", key="import_bulk_avis"):
                if textes_bulk.strip():
                    lines = textes_bulk.strip().split('\n')
                    count_added = 0
                    count_skipped = 0
                    
                    for line in lines:
                        line = line.strip()
                        if line.startswith('"') and line.endswith('"'):
                            texte_avis = line[1:-1]
                            if texte_avis:
                                cursor_avis.execute(f"INSERT INTO {table_avis} (texte) VALUES (?)", (texte_avis,))
                                count_added += 1
                        else:
                            count_skipped += 1
                    
                    conn_avis.commit()
                    upload_db_to_github("fiches_final.db", "fiches_final.db")
                    
                    st.success(f"✅ {count_added} avis ajouté(s) avec succès !")
                    if count_skipped > 0:
                        st.info(f"ℹ️ {count_skipped} ligne(s) ignorée(s) (format incorrect)")
                    st.rerun()
                else:
                    st.warning("⚠️ Veuillez coller au moins un texte d'avis")

        with st.expander("✏️ Modifier un texte d'avis"):
            avis_id = st.number_input("ID de l'avis à modifier", min_value=1, step=1, key="mod")
            if st.button("Charger l'avis", key="load_avis"):
                cursor_avis.execute(f"SELECT texte FROM {table_avis} WHERE id=?", (avis_id,))
                avis = cursor_avis.fetchone()
                if avis:
                    st.session_state.avis_loaded = True
                    st.session_state.avis_texte_a_modifier = avis[0]
                    st.session_state.avis_id_en_cours = avis_id
                else:
                    st.warning("Avis non trouvé ❌")
                    st.session_state.avis_loaded = False

            if st.session_state.get("avis_loaded"):
                nouveau = st.text_area("Nouveau texte", value=st.session_state.avis_texte_a_modifier, key="new_text")
                if st.button("Mettre à jour"):
                    cursor_avis.execute(
                        f"UPDATE {table_avis} SET texte=? WHERE id=?",
                        (nouveau, st.session_state.avis_id_en_cours)
                    )
                    conn_avis.commit()
                    upload_db_to_github("fiches_final.db", "fiches_final.db")
                    st.success("Avis modifié ✅")
                    st.session_state.avis_loaded = False
                    st.rerun()

        with st.expander("🗑️ Supprimer un texte d'avis"):
            avis_id_suppr = st.number_input("ID de l'avis à supprimer", min_value=1, step=1, key="del_avis")
            confirm_avis = st.checkbox("Je confirme la suppression de cet avis")
            if st.button("Supprimer cet avis"):
                if confirm_avis:
                    cursor_avis.execute(f"DELETE FROM {table_avis} WHERE id=?", (avis_id_suppr,))
                    conn_avis.commit()
                    upload_db_to_github("fiches_final.db", "fiches_final.db")
                    st.warning("Avis supprimé ❌")
                    st.rerun()
                else:
                    st.info("Merci de confirmer la suppression avant de continuer.")
# Partie utilisateur
if not st.session_state.admin_mode:
    # Collecte des localités disponibles
    # Construction dynamique d’une requête UNION de toutes les tables fiches_*
    union_queries = []
    for table in category_map.values():
        union_queries.append(f"SELECT localite FROM {table}")
    full_union_sql = " UNION ALL ".join(union_queries)
    final_sql = f"SELECT DISTINCT localite FROM ({full_union_sql})"
    
    cursor_fiches.execute(final_sql)
    localites = sorted(set([row[0] for row in cursor_fiches.fetchall() if row[0]]))
    
    selected_localite = st.selectbox("📍 Choisir une localité", localites)
    
    # Calcul du total global (assigné à l'utilisateur connecté)
    today = datetime.now().date()
    user = st.session_state.utilisateur.strip().lower()
    today_str = today.strftime("%Y-%m-%d")
    
    global_total = 0
    for table in category_map.values():
        try:
            cursor_fiches.execute(f"""
                SELECT COUNT(*) FROM {table}
                WHERE DATE(prochain_avis) <= DATE(?)
                  AND LOWER(COALESCE(assigne_a, '')) = ?
            """, (today_str, user))
            global_total += cursor_fiches.fetchone()[0]
        except:
            continue
    
    # Calcul des catégories disponibles pour la localité
    category_counts = {}
    for cat, table in category_map.items():
        try:
            cursor_fiches.execute(
                f"""SELECT COUNT(*) FROM {table} 
                    WHERE DATE(prochain_avis) <= DATE(?) 
                      AND localite = ? 
                      AND LOWER(COALESCE(assigne_a, '')) = ?""",
                (today, selected_localite, user)
            )
            count = cursor_fiches.fetchone()[0]
            if count > 0:
                category_counts[cat] = count
        except:
            continue
    
    # 🟢 Toujours afficher le total global ici
    st.markdown(f"""
    <div style="background:#1f1f1f;padding:18px;border-radius:10px;margin-bottom:15px;">
        <span style="color:white;font-size:16px;">📅 <b>Total à traiter aujourd'hui :</b></span>
        <span style="float:right;background:#2ecc71;padding:6px 14px;border-radius:8px;color:white;font-weight:bold;">{global_total}</span>
    </div>
    """, unsafe_allow_html=True)

    
    if category_counts:
        # ✅ Tri décroissant
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        total_fiches = global_total
    
        # Format d'affichage avec pastille
        def format_cat(cat, count):
            badge = "🟢" if count > 0 else "🔴"
            return f"{cat} {badge} [{count}]"
    
        cat_display_list = [format_cat(cat, count) for cat, count in sorted_categories]
        reverse_map = {format_cat(cat, count): cat for cat, count in sorted_categories}

    
        # Sélecteur de catégorie
        selected_display_cat = st.selectbox("📂 Catégorie à traiter", cat_display_list)
        selected_category = reverse_map[selected_display_cat]
    
        avis_table = avis_table_map[selected_category]
        table_name = category_map[selected_category]
    
        cursor_fiches.execute(f"""
            SELECT id, nom_de_la_fiche, lien_fiche, dernier_avis, prochain_avis, delai
            FROM {table_name}
            WHERE DATE(prochain_avis) <= DATE(?) 
              AND localite = ?
              AND LOWER(assigne_a) = ?
            ORDER BY DATE(dernier_avis) ASC
            LIMIT 1
        """, (today, selected_localite, st.session_state.utilisateur.lower()))


        fiche = cursor_fiches.fetchone()
    
        if not fiche:
            st.info("✅ Aucune fiche à traiter aujourd'hui dans cette catégorie/localité.")
    else:
        st.info("Aucune catégorie disponible pour cette localité aujourd'hui.")
        fiche = None


if fiche:
    fiche_id, nom, lien, dernier, prochain, delai = fiche

    st.markdown(f"<h2 style='color:#fff;'>📌 {nom}</h2>", unsafe_allow_html=True)

    cursor_fiches.execute(f"SELECT type_avis FROM {table_name} WHERE id = ?", (fiche_id,))
    type_avis = cursor_fiches.fetchone()
    type_avis = type_avis[0] if type_avis else 0  # fallback
    
    type_avis = int(type_avis) if type_avis is not None else 0
    # Détection de la note
    # Déduction du texte et des étoiles
    stars_display = "⭐️⭐️⭐️⭐️⭐️" if type_avis == 0 else "⭐️⭐️⭐️⭐️"
    # Déterminer texte à copier
    etoiles_texte = "5 Étoiles ⭐️⭐️⭐️⭐️⭐️" if type_avis == 0 else "4 Étoiles ⭐️⭐️⭐️⭐️"
    etoiles_texte_js = etoiles_texte.replace("'", "\\'")  # pour JS
    
    # HTML complet avec bouton fonctionnel
    html(f"""
    <div style="background:#2c2f33;padding:16px;border-radius:10px;margin-top:10px;margin-bottom:15px;display:flex;justify-content:space-between;align-items:center;font-family:Arial,sans-serif;">
        <div>
            <div style="color:white;font-size:16px;margin-bottom:4px;"><b>Note de l'avis à laisser :</b></div>
            <div style="font-size:22px;color:#f1c40f;">{"⭐️⭐️⭐️⭐️⭐️" if type_avis == 0 else "⭐️⭐️⭐️⭐️"}</div>
        </div>
        <button onclick="navigator.clipboard.writeText('{etoiles_texte_js}')"
            style="background:#f39c12;color:white;padding:10px 18px;border:none;border-radius:8px;font-weight:bold;font-size:14px;cursor:pointer;">
            📋 Copier
        </button>
    </div>
    """, height=100)

    # --- Petite box "Bref descriptif" (à coller dans le if fiche:, après les étoiles) ---

    # Récupérer le bref descriptif de la fiche
    cursor_fiches.execute(f"SELECT bref_descriptif FROM {table_name} WHERE id = ?", (fiche_id,))
    row = cursor_fiches.fetchone()
    bref_descriptif = row[0] if row and row[0] else ""
    
    # Afficher la box seulement s'il y a du contenu
    if bref_descriptif:
        # Échapper un minimum pour éviter l'injection HTML
        safe_bref = (bref_descriptif
                     .replace("&", "&amp;")
                     .replace("<", "&lt;")
                     .replace(">", "&gt;"))
    
        st.markdown(f"""
        <div style="
            background:#2c2f33;
            padding:14px;
            border-radius:10px;
            margin:10px 0 12px 0;
            font-family:Arial,sans-serif;">
            <div style="
                color:#9ca3af;
                font-size:12px;
                text-transform:uppercase;
                letter-spacing:.06em;
                margin-bottom:6px;">
                Bref descriptif
            </div>
            <div style="color:#ffffff; font-size:14px; line-height:1.6;">
                {safe_bref}
            </div>
        </div>
        """, unsafe_allow_html=True)
    # --- fin de la box ---



    # Récupération du premier avis non pris (pris = 0) dans l'ordre
    cursor_avis.execute(f"SELECT id, texte FROM {avis_table} WHERE texte IS NOT NULL AND pris = 0 ORDER BY id LIMIT 1")
    result = cursor_avis.fetchone()

    if result:
        texte_id, exemple_avis = result
        st.session_state.texte_id_actuel = texte_id

        # Nettoyage du texte pour JavaScript
        avis_clean_js = exemple_avis.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
        
        # 👉 Bloc 1 : Texte d'avis avec bouton copier
        st.markdown("""
        <h3 style="margin-bottom:0px; color:white;">💬 Avis à laisser :</h3>
        """, unsafe_allow_html=True)
        st.components.v1.html(f"""
            <div style="background:#2c2f33;padding:16px;border-radius:10px;display:flex;justify-content:space-between;align-items:center;font-family:Arial, sans-serif;\">
                <div style="color:white;font-size:15px;line-height:1.6;max-width:80%;">{exemple_avis}</div>
                <button onclick="navigator.clipboard.writeText('{avis_clean_js}')" 
                        style="background:black;color:white;padding:10px 18px;border:none;border-radius:8px;font-size:14px;font-weight:bold;cursor:pointer;">
                    📋 Copier
                </button>
            </div>
        """, height=130)

        
        # 👉 Bloc 2 : Lien + bouton orange qui copie ET déclenche traitement
        # 1. Nettoyage JS
        # Nettoyage du lien pour JS
        safe_lien = lien.replace("\\", "\\\\").replace("'", "\\'")
        
        # ✅ 1. Bouton masqué Streamlit (réel), rendu dans un conteneur masqué
        with st.container():
            st.markdown("""<div class="mon-bouton">""", unsafe_allow_html=True)

            if st.button("📋 COPIER & TRAITÉ", key="copier_traite_hidden"):
                today_str = datetime.now().strftime("%Y-%m-%d")
                try:
                    delai = int(delai)
                except:
                    delai = 1
                next_str = (datetime.now() + timedelta(days=delai)).strftime("%Y-%m-%d")
        
                # Récupération de duree_cycle et type_avis
                cursor_fiches.execute(f"SELECT duree_cycle, type_avis FROM {table_name} WHERE id = ?", (fiche_id,))
                current_cycle, current_type = cursor_fiches.fetchone()
                
                if current_type == 0 and current_cycle > 1:
                    new_cycle = current_cycle - 1
                    new_type = current_type
                elif current_type == 0 and current_cycle <= 1:
                    new_cycle = 1
                    new_type = 1
                elif current_type == 1:
                    new_cycle = random.randint(2, 5)
                    new_type = 0
                else:
                    new_cycle = current_cycle
                    new_type = current_type  # fallback de sécurité
                
                texte_id_a_marquer = st.session_state.get("texte_id_actuel", None)
                
                cursor_fiches.execute(f"""
                    UPDATE {table_name}
                    SET dernier_avis = ?, prochain_avis = ?, duree_cycle = ?, type_avis = ?, id_texte_utilise = ?
                    WHERE id = ?
                """, (today_str, next_str, new_cycle, new_type, texte_id_a_marquer, fiche_id))

                texte_marque_ok = True
                if texte_id_a_marquer:
                    cursor_avis.execute(f"""
                        UPDATE {avis_table}
                        SET pris = 1
                        WHERE id = ? AND pris = 0
                    """, (texte_id_a_marquer,))
                    
                    if cursor_avis.rowcount == 0:
                        texte_marque_ok = False
                        st.warning("⚠️ Ce texte d'avis a déjà été utilisé par quelqu'un d'autre. Rechargement...")
                    
                    conn_avis.commit()

                if texte_marque_ok:
                    conn_fiches.commit()
                    upload_db_to_github("fiches.db", "fiches.db")
                    upload_db_to_github("fiches_final.db", "fiches_final.db")
                    st.success("✅ Fiche mise à jour et lien copié.")
                
                time.sleep(1)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        st.components.v1.html("""
            <script>
            setTimeout(() => {
              const buttons = Array.from(parent.document.querySelectorAll('button'));
              buttons.forEach(btn => {
                if (btn.innerText.trim() === "📋 COPIER & TRAITÉ") {
                      btn.style.position = "absolute";
                      btn.style.top = "-9999px";
                      btn.style.left = "-9999px";
                      btn.style.width = "1px";
                      btn.style.height = "1px";
                      btn.style.padding = "0px";
                      btn.style.margin = "0px";
                      btn.style.border = "none";
                      btn.style.outline = "none";
                      btn.style.opacity = "0";
                      btn.style.boxShadow = "none";
                      btn.style.background = "transparent";
                      btn.style.zIndex = "-999";
                    }

              });
            }, 100);
            </script>
            """, height=0)
        


            
        st.markdown("""
        <h3 style="margin-top:10px; margin-bottom:8px; color:white;">📝 Fiche à traiter :</h3>
        """, unsafe_allow_html=True)
        # ✅ 2. Bouton HTML visible qui copie + déclenche le traitement
        st.components.v1.html(f"""
        <div style="background:#2c2f33;padding:16px;border-radius:10px;margin-top:0px;display:flex;justify-content:space-between;align-items:center;font-family:Arial, sans-serif;\">
          <div style="color:white;font-size:15px;">
            Lien de la fiche
          </div>
          <button onclick="copyAndTrigger()" 
                  style="background:#f39c12;color:white;padding:10px 18px;border:none;border-radius:8px;font-weight:bold;font-size:15px;cursor:pointer;">
            📋 Copier & Traité
          </button>
        </div>
        
        <script>
        function copyAndTrigger() {{
            navigator.clipboard.writeText('{safe_lien}');
            const btns = window.parent.document.querySelectorAll("button");
            btns.forEach(btn => {{
                if (btn.innerText.trim() === "📋 COPIER & TRAITÉ") {{
                    btn.click();
                }}
            }});
        }}
        </script>
        """, height=85)












    else:
        cursor_avis.execute(f"SELECT COUNT(*) FROM {avis_table} WHERE texte IS NOT NULL")
        total_avis = cursor_avis.fetchone()[0]
        
        if total_avis > 0:
            st.warning("⚠️ Tous les textes d'avis ont déjà été utilisés pour cette catégorie.")
            if st.session_state.admin_mode:
                st.info("💡 Vous pouvez réinitialiser les textes dans l'onglet 'Textes d'avis' pour les réutiliser.")
        else:
            st.warning("⚠️ Aucun texte d'avis disponible pour cette catégorie.")
elif not st.session_state.admin_mode:
    st.success("✅ Aucune fiche à traiter aujourd'hui.")




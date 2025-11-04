import sqlite3
import hashlib

def hasher_mot_de_passe(mdp):
    return hashlib.sha256(mdp.encode()).hexdigest()

# Connexion à la base de données
conn = sqlite3.connect("comptes.db")
cursor = conn.cursor()

# Création de la table si elle n'existe pas
cursor.execute("""
    CREATE TABLE IF NOT EXISTS comptes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom_utilisateur TEXT UNIQUE NOT NULL,
        mot_de_passe_hash TEXT NOT NULL,
        role TEXT NOT NULL
    )
""")

# Suppression de tous les comptes existants
cursor.execute("DELETE FROM comptes")

# Ajout des deux comptes
comptes = [
    ("fournigoogle", "fournigoogle1!", "google"),
    ("fourniavis", "fourniavis1!", "avis")
]

for nom, mdp, role in comptes:
    hash_mdp = hasher_mot_de_passe(mdp)
    cursor.execute(
        "INSERT INTO comptes (nom_utilisateur, mot_de_passe_hash, role) VALUES (?, ?, ?)",
        (nom, hash_mdp, role)
    )

conn.commit()
conn.close()

print("✅ Base de données des comptes initialisée avec succès !")
print("Comptes créés :")
print("  - fournigoogle / fournigoogle1!")
print("  - fourniavis / fourniavis1!")

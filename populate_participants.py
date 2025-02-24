import os
import psycopg2
from dotenv import load_dotenv
from leaderboboard import PREDEFINED_PARTICIPANTS

# Charger les variables d'environnement
load_dotenv()


# Connexion à la base de données PostgreSQL
def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
    )


# Fonction pour peupler la table des participants
def populate_participants():
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Insérer chaque participant dans la table
        for participant in PREDEFINED_PARTICIPANTS:
            cur.execute(
                "INSERT INTO participants (name, sexe) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING",
                (participant["name"], participant["sexe"]),
            )
        conn.commit()
        print("Participants ajoutés avec succès !")
    except Exception as e:
        print(f"Erreur lors de l'insertion des participants : {e}")
    finally:
        cur.close()
        conn.close()


# Exécuter le script
if __name__ == "__main__":
    populate_participants()

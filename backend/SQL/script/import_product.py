import psycopg2
import csv
from datetime import datetime

# Connexion à la base de données
try:
    conn = psycopg2.connect(
        dbname="livrerjardiner",
        user="monuser",
        password="moncode",
        host="localhost"
    )
    cur = conn.cursor()
    print("Connexion à la base de données réussie")
except Exception as e:
    print(f"Erreur lors de la connexion à la base de données : {str(e)}")
    exit(1)

# Lire le fichier CSV et insérer les données
try:
    with open("products.csv", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Insérer dans la table products
            cur.execute(
                """
                INSERT INTO products (reference, name, description, category, unit_price, image_url)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    row["reference"],
                    row["name"],
                    row["description"],
                    row["category"],
                    float(row["unit_price"]),
                    row["image_url"]
                )
            )
            product_id = cur.fetchone()[0]

            # Insérer dans la table stock
            cur.execute(
                """
                INSERT INTO stock (product_id, quantity, last_updated)
                VALUES (%s, %s, %s)
                """,
                (product_id, int(row["quantity"]), datetime.now())
            )

    # Valider les changements
    conn.commit()
    print("Importation terminée avec succès !")
except Exception as e:
    print(f"Erreur lors de l'importation : {str(e)}")
    conn.rollback()
finally:
    # Fermer la connexion
    cur.close()
    conn.close()
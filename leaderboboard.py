import dash
import dash_auth
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
from datetime import datetime
import os
import psycopg2
from psycopg2 import sql
import locale
from dotenv import load_dotenv
from flask import Flask

# Charger les variables d'environnement
load_dotenv()

# Configuration de l'application Flask et Dash
server = Flask(__name__)
app = dash.Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Leaderboard App"

locale.setlocale(locale.LC_TIME, "")

# Authentification avec dash_auth
VALID_USERNAME_PASSWORD_PAIRS = {
    "coloc": os.getenv("APP_PASSWORD")  # Mot de passe admin depuis les variables d'environnement
}
auth = dash_auth.BasicAuth(app, VALID_USERNAME_PASSWORD_PAIRS)

# Liste prédéfinie de participants avec leur sexe
PREDEFINED_PARTICIPANTS = [
    {"name": os.getenv("COLOC_ONE"), "sexe": "homme"},
    {"name": os.getenv("COLOC_TWO"), "sexe": "femme"},
    {"name": os.getenv("COLOC_THREE"), "sexe": "homme"},
    {"name": os.getenv("COLOC_FOUR"), "sexe": "homme"},
]

dico_english_days = {
    "Monday": "Lundi",
    "Tuesday": "Mardi",
    "Wednesday": "Mercredi",
    "Thursday": "Jeudi",
    "Friday": "Vendredi",
    "Saturday": "Samedi",
    "Sunday": "Dimanche",
}

dico_english_months = {
    "January": "Janvier",
    "February": "Février",
    "March": "Mars",
    "April": "Avril",
    "May": "Mai",
    "June": "Juin",
    "July": "Juillet",
    "August": "Août",
    "September": "Septembre",
    "October": "Octobre",
    "November": "Novembre",
    "December": "Décembre",
}


# Connexion à la base de données PostgreSQL
def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
    )


# Initialisation de la base de données
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS participants (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            sexe TEXT NOT NULL
        );
    """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scores (
            id SERIAL PRIMARY KEY,
            participant_id INTEGER NOT NULL REFERENCES participants(id),
            points INTEGER NOT NULL,
            motif TEXT NOT NULL,
            date TEXT NOT NULL
        );
    """
    )
    conn.commit()
    cur.close()
    conn.close()


init_db()

# Layout de l'application Dash
app.layout = dbc.Container(
    [
        dcc.Location(id="url", refresh=False),  # Pour gérer la navigation
        dbc.Modal(  # Modal pour l'historique
            [
                dbc.ModalHeader("Historique des points"),
                dbc.ModalBody(id="history-table"),
                dbc.ModalFooter(dbc.Button("Fermer", id="close-history", className="ms-auto")),
                dbc.Alert(  # alert pour le retour visuel
                    "Suppression",
                    id="delete_alert",
                    is_open=False,
                    dismissable=True,
                    duration=2000,
                    color="danger",
                    style={"position": "fixed", "top": 10, "right": 10, "width": 350},
                ),
            ],
            id="history-modal",
            size="lg",
            is_open=False,
        ),
        dbc.Alert(  # alert pour le retour visuel
            "Succès",
            id="add_alert",
            is_open=False,
            dismissable=True,
            duration=3000,
            color="success",
            style={"position": "fixed", "top": 10, "right": 10, "width": 350},
        ),
        dbc.Row(dbc.Col(html.H1("Leaderboboard", className="text-center"))),
        dbc.Row(
            dbc.Col(html.Div(id="king-message", className="text-center mb-3"))
        ),  # Message du roi/la reine
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Ajouter des points à plusieurs colocs"),
                        dcc.Dropdown(
                            id="names-input",
                            options=[
                                {"label": p["name"], "value": p["name"]}
                                for p in PREDEFINED_PARTICIPANTS
                            ],
                            multi=True,
                            placeholder="Sélectionnez les participants",
                            className="mb-3",
                        ),
                        dbc.Input(
                            id="batch-motif-input",
                            type="text",
                            placeholder="Entrez le motif",
                            className="mb-3",
                        ),
                        dbc.Input(
                            id="batch-points-input",
                            type="number",
                            placeholder="Entrez les points",
                            className="mb-3",
                        ),
                        dbc.Button(
                            "Ajouter des points",
                            id="batch-add-points-button",
                            color="primary",
                            className="w-100 mb-3",
                        ),
                        dbc.Button(
                            "Voir l'historique",
                            id="open-history",
                            color="secondary",
                            className="w-100 mb-3",
                        ),
                    ],
                    width=12,
                    md=8,
                    className="mx-auto",
                )  # Centrage sur les écrans mobiles
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H3("Classement", className="text-center"),
                        html.Div(id="leaderboard-table", className="mb-3"),
                    ],
                    width=12,
                )
            ]
        ),
    ],
    fluid=True,
    style={"maxWidth": "800px", "padding": "20px"},
)  # Centrage et largeur maximale


# Callback pour ajouter des points à plusieurs participants
@app.callback(
    Output("leaderboard-table", "children", allow_duplicate=True),
    Output("king-message", "children", allow_duplicate=True),
    Output("add_alert", "is_open"),
    Output("add_alert", "children"),
    Input("batch-add-points-button", "n_clicks"),
    State("names-input", "value"),
    State("batch-points-input", "value"),
    State("batch-motif-input", "value"),
    prevent_initial_call="initial_duplicate",
)
def update_leaderboard(batch_clicks, names, batch_points, batch_motif):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        if names and batch_points is not None and batch_motif:
            date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for n in names:
                # Récupérer l'ID du participant
                cur.execute("SELECT id FROM participants WHERE name = %s", (n,))
                participant_id = cur.fetchone()[0]
                # Insérer le score
                cur.execute(
                    sql.SQL(
                        "INSERT INTO scores (participant_id, points, motif, date) VALUES (%s, %s, %s, %s)"
                    ),
                    (participant_id, batch_points, batch_motif, date),
                )
            conn.commit()
    except Exception as e:
        print(f"Erreur lors de la mise à jour de la base de données : {e}")
    finally:
        cur.close()
        conn.close()

    # Mettre à jour le tableau du leaderboard et le message du roi/la reine
    leaderboard_table = get_leaderboard_table()
    king_message = get_king_message()
    return (
        leaderboard_table,
        king_message,
        batch_clicks is not None,
        f"Evénement {batch_motif} ajouté au leaderboboard",
    )


# Fonction pour générer le tableau du leaderboard
def get_leaderboard_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.name, SUM(s.points) as total_points
        FROM participants p
        JOIN scores s ON p.id = s.participant_id
        GROUP BY p.name
        ORDER BY total_points DESC
        """
    )
    participants = cur.fetchall()
    cur.close()
    conn.close()
    rows = []
    for participant in participants:
        rows.append(html.Tr([html.Td(participant[0]), html.Td(participant[1])]))
    return dbc.Table(
        [html.Thead(html.Tr([html.Th("Nom"), html.Th("Total des points")])), html.Tbody(rows)],
        bordered=True,
        hover=True,
        responsive=True,
    )


# Fonction pour déterminer le roi ou la reine
def get_king_message():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.name, p.sexe, SUM(s.points) as total_points
        FROM participants p
        JOIN scores s ON p.id = s.participant_id
        GROUP BY p.name, p.sexe
        ORDER BY total_points DESC
        LIMIT 1
        """
    )
    king = cur.fetchone()
    cur.close()
    conn.close()
    if king:
        if king[1] == "homme":
            return html.H4(f"{king[0]} est le roi des bobos 👑", style={"color": "gold"})
        else:
            return html.H4(f"{king[0]} est la reine des bobos 👑", style={"color": "gold"})
    else:
        return html.H4("Aucun participant n'a encore de points.")


# Fonction pour formater la date en français
def format_date_fr(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    date = date_obj.strftime("%A %d %B %Y, %Hh %Mmin %Ss")
    for en_day, fr_day in dico_english_days.items():
        date = date.replace(en_day, fr_day)
    for en_month, fr_month in dico_english_months.items():
        date = date.replace(en_month, fr_month)
    return date


# Fonction pour générer le tableau d'historique
def get_history_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT s.id, p.name, s.points, s.motif, s.date
        FROM scores s
        JOIN participants p ON s.participant_id = p.id
        ORDER BY s.id DESC
        """
    )
    history = cur.fetchall()
    cur.close()
    conn.close()
    rows = []
    for entry in history:
        rows.append(
            html.Tr(
                [
                    html.Td(entry[1]),
                    html.Td(entry[2]),
                    html.Td(entry[3]),
                    html.Td(format_date_fr(entry[4])),
                    html.Td(
                        dbc.Button(
                            "Supprimer",
                            id={"type": "delete-button", "index": entry[0]},
                            color="danger",
                            size="sm",
                        )
                    ),
                ]
            )
        )
    return dbc.Table(
        [
            html.Thead(
                html.Tr(
                    [
                        html.Th("Nom"),
                        html.Th("Points"),
                        html.Th("Motif"),
                        html.Th("Date"),
                        html.Th("Action"),
                    ]
                )
            ),
            html.Tbody(rows),
        ],
        bordered=True,
        hover=True,
        responsive=True,
    )


# Callback pour afficher l'historique en overlay
@app.callback(
    Output("history-modal", "is_open"),
    Input("open-history", "n_clicks"),
    Input("close-history", "n_clicks"),
    State("history-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_history(open_clicks, close_clicks, is_open):
    if open_clicks or close_clicks:
        return not is_open
    return is_open


@app.callback(
    Output("leaderboard-table", "children", allow_duplicate=True),
    Output("king-message", "children", allow_duplicate=True),
    Input("history-modal", "is_open"),
    prevent_initial_call=True,
)
def refresh_homepage(is_open):
    if not is_open:
        leaderboard_table = get_leaderboard_table()
        king_message = get_king_message()
        return leaderboard_table, king_message
    return dash.no_update, dash.no_update


# Callback pour mettre à jour le contenu de l'historique
@app.callback(
    Output("history-table", "children", allow_duplicate=True),
    Input("history-modal", "is_open"),
    prevent_initial_call=True,
)
def update_history(is_open):
    if is_open:
        return get_history_table()
    return dash.no_update


# Callback pour supprimer un événement
@app.callback(
    Output("history-table", "children", allow_duplicate=True),
    Output("delete_alert", "children"),
    Output("delete_alert", "is_open"),
    Input({"type": "delete-button", "index": dash.dependencies.ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def delete_event(n_clicks):
    ctx = dash.callback_context
    if not ctx.triggered or not (any(prop["value"] is not None for prop in ctx.triggered)):
        return dash.no_update, dash.no_update, dash.no_update

    # Récupérer l'ID de l'événement à supprimer
    event_id = ctx.triggered_id.index

    # Récupération de l'événement à supprimer
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT motif FROM scores WHERE id = %s", (event_id,))
    deleted_event_motif = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    # Supprimer l'événement de la base de données
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM scores WHERE id = %s", (event_id,))
    conn.commit()
    cur.close()
    conn.close()

    # Mettre à jour l'historique
    return get_history_table(), f"Evénement {deleted_event_motif} supprimé du leaderboboard", True


# Callback pour activer les boutons avec la touche Entrée
@app.callback(
    Output("batch-add-points-button", "n_clicks", allow_duplicate=True),
    Input("batch-points-input", "n_submit"),
    Input("batch-motif-input", "n_submit"),
    prevent_initial_call=True,
)
def handle_enter_key(n_submit_points, n_submit_motif):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update

    return 1


# Lancement de l'application
if __name__ == "__main__":
    app.run_server(debug=True)

import dash
from dash import dcc, html, Input, Output, Stat
import dash_bootstrap_components as dbc
from datetime import datetime
import os
import psycopg2
from psycopg2 import sql
import locale
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration de la locale pour le formatage des dates en français
locale.setlocale(locale.LC_TIME, "fr_FR")

# Initialisation de l'application Dash
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Leaderboard App"

# Configuration du mot de passe via une variable d'environnement
PASSWORD = os.getenv("APP_PASSWORD")

# Liste prédéfinie de participants avec leur sexe
PREDEFINED_PARTICIPANTS = [
    {"name": os.getenv("COLOC_ONE"), "sexe": "homme"},
    {"name": os.getenv("COLOC_TWO"), "sexe": "femme"},
    {"name": os.getenv("COLOC_THREE"), "sexe": "homme"},
    {"name": os.getenv("COLOC_FOUR"), "sexe": "homme"},
]


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
            name TEXT NOT NULL,
            points INTEGER NOT NULL,
            motif TEXT NOT NULL,
            sexe TEXT NOT NULL,
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
        dcc.Store(id="deleted-event", data=None),  # Pour stocker l'événement supprimé
        html.Div(id="page-content"),  # Contenu de la page (login ou leaderboard)
        dbc.Modal(  # Modal pour l'historique
            [
                dbc.ModalHeader("Historique des points"),
                dbc.ModalBody(id="history-table"),
                dbc.ModalFooter(dbc.Button("Fermer", id="close-history", className="ms-auto")),
            ],
            id="history-modal",
            size="lg",
            is_open=False,
        ),
        dbc.Toast(  # Notification pour annuler la suppression
            id="undo-toast",
            header="Événement supprimé",
            duration=5000,  # 5 secondes
            is_open=False,
            dismissable=True,
            icon="danger",
            style={"position": "fixed", "top": "10px", "right": "10px", "width": "350px"},
        ),
    ],
    fluid=True,
    style={"maxWidth": "800px", "padding": "20px"},
)  # Centrage et largeur maximale

# Layout de la page de login
login_layout = dbc.Container(
    [
        dbc.Row(dbc.Col(html.H1("Connexion au Leaderboboard", className="text-center"))),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Mot de passe"),
                        dbc.Input(
                            id="password-input",
                            type="password",
                            placeholder="Entrez le mot de passe",
                            className="mb-3",
                        ),
                        dbc.Button(
                            "Se connecter", id="login-button", color="primary", className="w-100"
                        ),
                        html.Div(
                            id="login-message", className="mt-3"
                        ),  # Pour afficher les messages d'erreur
                    ],
                    width=12,
                    md=6,
                    className="mx-auto",
                )  # Centrage sur les écrans mobiles
            ]
        ),
    ],
    fluid=True,
)

# Layout du tableau de bord
leaderboard_layout = dbc.Container(
    [
        dbc.Row(dbc.Col(html.H1("Leaderboard", className="text-center"))),
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
                            id="batch-points-input",
                            type="number",
                            placeholder="Entrez les points",
                            className="mb-3",
                        ),
                        dbc.Input(
                            id="batch-motif-input",
                            type="text",
                            placeholder="Entrez le motif",
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
)


# Callback pour gérer la navigation entre les pages
@app.callback(
    Output("page-content", "children"), Input("url", "pathname"), State("url", "pathname")
)
def display_page(pathname, _):
    if pathname == "/leaderboard":
        return leaderboard_layout
    else:
        return login_layout


# Callback pour vérifier le mot de passe
@app.callback(
    Output("login-message", "children"),
    Output("url", "pathname"),
    Input("login-button", "n_clicks"),
    State("password-input", "value"),
    prevent_initial_call=True,
)
def check_password(n_clicks, password):
    if password == PASSWORD:
        return "", "/leaderboard"  # Redirection vers le tableau de bord
    else:
        return dbc.Alert("Mot de passe incorrect", color="danger"), "/"  # Message d'erreur


# Callback pour ajouter des points à plusieurs participants
@app.callback(
    Output("leaderboard-table", "children", allow_duplicate=True),
    Output("king-message", "children", allow_duplicate=True),
    Input("batch-add-points-button", "n_clicks"),
    State("names-input", "value"),
    State("batch-points-input", "value"),
    State("batch-motif-input", "value"),
    State("url", "pathname"),  # Ajoutez l'état de l'URL
    prevent_initial_call=True,
)
def update_leaderboard(batch_clicks, names, batch_points, batch_motif, pathname):
    # Ne pas exécuter le callback si l'utilisateur n'est pas sur la page du tableau de bord
    if pathname != "/leaderboard":
        return dash.no_update, dash.no_update

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        if names and batch_points is not None and batch_motif:
            date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for n in names:
                sexe = next(p["sexe"] for p in PREDEFINED_PARTICIPANTS if p["name"] == n)
                cur.execute(
                    sql.SQL(
                        "INSERT INTO participants (name, points, motif, sexe, date) VALUES (%s, %s, %s, %s, %s)"
                    ),
                    (n, batch_points, batch_motif, sexe, date),
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
    return leaderboard_table, king_message


# Fonction pour générer le tableau du leaderboard
def get_leaderboard_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT name, SUM(points) as total_points FROM participants GROUP BY name ORDER BY total_points DESC"
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
        "SELECT name, sexe, SUM(points) as total_points FROM participants GROUP BY name ORDER BY total_points DESC LIMIT 1"
    )
    king = cur.fetchone()
    cur.close()
    conn.close()
    if king:
        if king[1] == "homme":
            return html.H4(f"{king[0]} est le roi de la bourgeoisie 👑", style={"color": "gold"})
        else:
            return html.H4(f"{king[0]} est la reine de la bourgeoisie 👑", style={"color": "gold"})
    else:
        return html.H4("Aucun participant n'a encore de points.")


# Fonction pour formater la date en français
def format_date_fr(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    return date_obj.strftime("%A %d %B %Y, %Hh %Mmin %Ss")


# Fonction pour générer le tableau d'historique
def get_history_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, points, motif, date FROM participants ORDER BY id DESC")
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


# Callback pour mettre à jour le contenu de l'historique
@app.callback(
    Output("history-table", "children", allow_duplicate=True),
    Input("history-modal", "is_open"),
    Input("deleted-event", "data"),
    prevent_initial_call=True,
)
def update_history(is_open, deleted_event):
    if is_open:
        return get_history_table()
    return dash.no_update


# Callback pour supprimer un événement
@app.callback(
    Output("leaderboard-table", "children", allow_duplicate=True),
    Output("king-message", "children", allow_duplicate=True),
    Output("deleted-event", "data"),
    Output("undo-toast", "is_open"),
    Output("history-table", "children", allow_duplicate=True),
    Input({"type": "delete-button", "index": dash.dependencies.ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def delete_event(n_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update, None, False, dash.no_update

    button_id = ctx.triggered[0]["prop_id"]
    event_id = eval(button_id.split(".")[0])["index"]

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM participants WHERE id = %s", (event_id,))
    deleted_event = cur.fetchone()
    cur.execute("DELETE FROM participants WHERE id = %s", (event_id,))
    conn.commit()
    cur.close()
    conn.close()

    # Mettre à jour le tableau du leaderboard, le message du roi/la reine et l'historique
    leaderboard_table = get_leaderboard_table()
    king_message = get_king_message()
    history_table = get_history_table()
    return leaderboard_table, king_message, deleted_event, True, history_table


# Callback pour annuler la suppression
@app.callback(
    Output("leaderboard-table", "children", allow_duplicate=True),
    Output("king-message", "children", allow_duplicate=True),
    Output("deleted-event", "data"),
    Output("history-table", "children", allow_duplicate=True),
    Input("undo-toast", "n_dismiss"),
    State("deleted-event", "data"),
    prevent_initial_call=True,
)
def undo_delete(n_dismiss, deleted_event):
    if deleted_event:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            sql.SQL(
                "INSERT INTO participants (name, points, motif, sexe, date) VALUES (%s, %s, %s, %s, %s)"
            ),
            (
                deleted_event[1],
                deleted_event[2],
                deleted_event[3],
                deleted_event[4],
                deleted_event[5],
            ),
        )
        conn.commit()
        cur.close()
        conn.close()

        # Mettre à jour le tableau du leaderboard, le message du roi/la reine et l'historique
        leaderboard_table = get_leaderboard_table()
        king_message = get_king_message()
        history_table = get_history_table()
        return leaderboard_table, king_message, None, history_table
    return dash.no_update, dash.no_update, None, dash.no_update


# Lancement de l'application
if __name__ == "__main__":
    app.run_server(debug=True)

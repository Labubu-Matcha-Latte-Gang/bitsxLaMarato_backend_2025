from flask import send_from_directory
from flask_smorest import Blueprint, abort

from globals import FAVICON_PATH

blp = Blueprint(
    "favicon",
    __name__,
    description="Serveix l'arxiu de favicon.ico.",
)

@blp.route('')
@blp.doc(
    summary="Serveix el favicon de l'aplicació.",
    description="Retorna l'arxiu favicon.ico per a ser utilitzat com a icona del lloc web.",
    security=[]
)
def favicon():
    try:
        return send_from_directory(
            FAVICON_PATH.rsplit('/', 1)[0],
            FAVICON_PATH.rsplit('/', 1)[1],
            mimetype='image/vnd.microsoft.icon'
        )
    except FileNotFoundError as e:
        abort(404, message="Favicon no trobat: " + str(e))
    except Exception as e:
        abort(500, message="Error inesperat en servir el favicon: " + str(e))
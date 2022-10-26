import uuid
from flask import Flask, request, render_template

app = Flask(__name__)


@app.route('/', methods=['POST'])
def index():
    action = request.headers.get('SOAPAction')

    if action == 'http://www.egem.nl/StUF/sector/zkn/0310/genereerZaakIdentificatie_Di02':
        app.logger.info(f'Received genereerzaakIdentificatie: {request.data}')
        return render_template('mocks/genereerZaakIdentificatie_Du02.xml', generated_id=str(uuid.uuid4()))
    if action == 'http://www.egem.nl/StUF/sector/zkn/0310/creeerZaak_Lk01':
        app.logger.info(f'Received creerZaak_Lk01: {request.data}')
        return render_template('mocks/ontvangstbevestiging_Bv03.xml')
    if action == 'http://www.egem.nl/StUF/sector/zkn/0310/actualiseerZaakstatus_Lk01':
        app.logger.info(f'Received actualiseerZaakstatus_Lk01: {request.data}')
        return render_template('mocks/ontvangstbevestiging_Bv03.xml')

    app.logger.info(f'Received invalid action: {action}')
    return 'Invalid action', 404

from datetime import datetime
import time
import base64
import binascii
import os
import re
import uuid
from urllib.parse import urljoin
from flask import Flask, Response, request
import requests
from requests.exceptions import JSONDecodeError
import json
import xmltodict
from xml.parsers.expat import ExpatError
from lxml import etree
from lib import GenereerZaakIdentificatieMessage, CreerZaakMessage, ActualiseerZaakStatusMessage, OntvangstbevestigingBv03, is_valid_email

app = Flask(__name__)
app.config.from_object('settings')
app.logger.setLevel(os.getenv('LOG_LEVEL', 'ERROR'))

@app.route('/')
def index():
    return ''

@app.route('/healthz')
def health():
    return ''

@app.route('/buitenbeter/soap.svc', methods=['POST'])
def buitenbeter():
    namespaces = {
        'http://schemas.xmlsoap.org/soap/envelope/': 'soap',
        'http://www.egem.nl/StUF/StUF0301:x': 'stuf',
        'http://www.egem.nl/StUF/sector/bg/0310:y': 'bg'
    }

    try:
        data = xmltodict.parse(request.get_data(), process_namespaces=True, namespaces=namespaces)
    except ExpatError:
        return 'Not a well-formatted XML document', 400

    body = data['soap:Envelope']['soap:Body']
    stuurgegevens = body['http://www.egem.nl/StUF/sector/ef/0310:wloLk01']['http://www.egem.nl/StUF/sector/ef/0310:stuurgegevens']
    referentienummer = stuurgegevens['http://www.egem.nl/StUF/StUF0301:referentienummer']

    response_message = OntvangstbevestigingBv03(
        zender=app.config['ZDS_ZENDER'],
        ontvanger=app.config['ZDS_ONTVANGER'],
        cross_ref_number=referentienummer
    )

    if not app.config['BUITENBETER_ENABLED']:
        return Response(response_message.tostring(), mimetype='text/xml')

    object = body['http://www.egem.nl/StUF/sector/ef/0310:wloLk01']['http://www.egem.nl/StUF/sector/ef/0310:object']
    melding = object['http://www.egem.nl/StUF/sector/ef/0310:melding']
    betreftAdres = object['http://www.egem.nl/StUF/sector/ef/0310:plaats'].get('http://www.egem.nl/StUF/sector/ef/0310:betreftAdres')
    gerelateerde = None
    adresAanduidingGrp = None

    if betreftAdres:
        gerelateerde = betreftAdres.get('http://www.egem.nl/StUF/sector/ef/0310:gerelateerde')
    if gerelateerde:
        adresAanduidingGrp = gerelateerde.get('http://www.egem.nl/StUF/sector/bg/0310:adresAanduidingGrp')

    adres = None
    if betreftAdres and gerelateerde and adresAanduidingGrp and isinstance(adresAanduidingGrp['http://www.egem.nl/StUF/sector/bg/0310:gor.openbareRuimteNaam'], str) and isinstance(adresAanduidingGrp['http://www.egem.nl/StUF/sector/bg/0310:wpl.woonplaatsNaam'], str):
        adres = {
            'openbare_ruimte': adresAanduidingGrp['http://www.egem.nl/StUF/sector/bg/0310:gor.openbareRuimteNaam'],
            'huisnummer': adresAanduidingGrp.get('http://www.egem.nl/StUF/sector/bg/0310:aoa.huisnummer', ''),
            'postcode': '',
            'woonplaats': adresAanduidingGrp['http://www.egem.nl/StUF/sector/bg/0310:wpl.woonplaatsNaam']
        }

    bijlage = object.get('http://www.egem.nl/StUF/sector/ef/0310:bijlage')
    aangevraagdDoorGerelateerde = object['http://www.egem.nl/StUF/sector/ef/0310:isAangevraagdDoor']['http://www.egem.nl/StUF/sector/ef/0310:gerelateerde']

    omschrijvingMelding = melding['http://www.egem.nl/StUF/sector/ef/0310:omschrijvingMelding']
    waarGaatDeMeldingOver = melding['http://www.egem.nl/StUF/sector/ef/0310:waarGaatDeMeldingOver']

    emailadres = aangevraagdDoorGerelateerde['http://www.egem.nl/StUF/sector/bg/0310:sub.emailadres']
    if not is_valid_email(emailadres):
        emailadres = None

    telefoonnummer = aangevraagdDoorGerelateerde['http://www.egem.nl/StUF/sector/bg/0310:sub.telefoonnummer']

    extraElementen = object['http://www.egem.nl/StUF/StUF0301:extraElementen']['http://www.egem.nl/StUF/StUF0301:extraElement']

    longitude = None
    latitude = None

    for element in extraElementen:
        if element['@naam'] == 'longitude':
            longitude = element['#text']

        if element['@naam'] == 'latitude':
            latitude = element['#text']

    text = ''
    if waarGaatDeMeldingOver and isinstance(waarGaatDeMeldingOver, str):
        text = f'{waarGaatDeMeldingOver} '

    if omschrijvingMelding and isinstance(omschrijvingMelding, str):
        text += omschrijvingMelding

    if not text:
        text = 'niet ingevuld'

    data = {
        'text': text
    }

    headers = {
        'Content-type': 'application/json'
    }

    url = urljoin(app.config['SIGNALEN_ENDPOINT'], '/signals/category/prediction')
    response = requests.post(url, data=json.dumps(data), headers={ **headers, **app.config['ADDITIONAL_SIGNALEN_HEADERS'] })

    sub_category = urljoin(app.config['SIGNALEN_ENDPOINT'], '/signals/v1/public/terms/categories/overig/sub_categories/overig')

    try:
        classification_data = response.json()

        if classification_data['subrubriek'][1][0] >= app.config['BUITENBETER_MACHINE_LEARNING_MINIMUM_CERTAINTY']:
            sub_category = classification_data['subrubriek'][0][0]
        elif classification_data['hoofdrubriek'][1][0] >= app.config['BUITENBETER_MACHINE_LEARNING_MINIMUM_CERTAINTY']:
            main_category_name = re.search(r"/terms/categories/(.*)$", classification_data['hoofdrubriek'][0][0])[1]
            sub_category = classification_data['hoofdrubriek'][0][0] + f'/sub_categories/overig-{main_category_name}'
    except (JSONDecodeError, IndexError):
        app.logger.error('Could not decode or index prediction response: ', response.text)

    data = {
        'text': text,
        'category': {
            'sub_category': sub_category
        },
        'location': {
            'address': adres,
            'geometrie': {
                'type': 'Point',
                'coordinates': [ float(longitude), float(latitude) ]
            }
        },
        'reporter': {
            'email': emailadres,
            'phone': telefoonnummer,
            'sharing_allowed': False
        },
        'source': app.config['BUITENBETER_SOURCE_NAME'],
        'incident_date_start': datetime.now().astimezone().isoformat(),
    }

    url = urljoin(app.config['SIGNALEN_ENDPOINT'], '/signals/v1/private/signals/')
    response = requests.post(url, data=json.dumps(data), headers={ **headers, **app.config['ADDITIONAL_SIGNALEN_HEADERS'] })

    signal_data = response.json()
    signal_id = signal_data.get('signal_id')
    if not signal_id:
        return 'Could not fetch Signal id from Signal post', 400

    if bijlage:
        bijlage_data = bijlage.get('#text')
        if not bijlage_data:
            return 'Could not find bijlage data', 400

        bijlage_bestandsnaam = bijlage.get('@http://www.egem.nl/StUF/StUF0301:bestandsnaam')
        if not bijlage_bestandsnaam:
            return 'Could not find bijlage bestandsnaam', 400

        data = {
            'signal_id': signal_id
        }

        try:
            files = {
                'file': (bijlage_bestandsnaam, base64.b64decode(bijlage_data), 'application/octet-stream')
            }
        except binascii.Error:
            return 'Signal is created, but provided bijlage is not correctly base64 encoded and not created', 400


        url = urljoin(app.config['SIGNALEN_ENDPOINT'], f'/signals/v1/public/signals/{signal_id}/attachments/')
        response = requests.post(url, data=data, files=files, headers=app.config['ADDITIONAL_SIGNALEN_HEADERS'])
        if not response.ok:
            app.logger.info(f'Could not create attachment in Signalen: {response.text}')
            return 'Could not create attachment in Signalen', 400

        attachment_data = response.json()

    return Response(response_message.tostring(), mimetype='text/xml')

@app.route('/zgw/zaken', methods=['POST'])
def zaken():
    zaak = request.get_json()

    if not app.config['ZDS_ENABLED']:
        return {
            'url': f'{request.base_url}/{uuid.uuid4()}',
            'uuid': uuid.uuid4()
        }

    message = GenereerZaakIdentificatieMessage(
        zender=app.config['ZDS_ZENDER'],
        ontvanger=app.config['ZDS_ONTVANGER'],
    )

    result = message.send(app.config['ZDS_ENDPOINT'], app.config['ADDITIONAL_ZDS_HEADERS'])
    app.logger.info(f'GenereerZaakIdentificatieMessage. Received: {etree.tostring(result)}')

    nsmap_soap = {
        'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
        'xs': 'http://www.w3.org/2001/XMLSchema',
        'StUF': 'http://www.egem.nl/StUF/StUF0301',
        'ZKN': 'http://www.egem.nl/StUF/sector/zkn/0310'
    }

    identificatie = result.find('.//soap:Body/ZKN:genereerZaakIdentificatie_Du02/ZKN:zaak/ZKN:identificatie', namespaces=nsmap_soap).text

    message = CreerZaakMessage(
        zender=app.config['ZDS_ZENDER'],
        ontvanger=app.config['ZDS_ONTVANGER'],
        identificatie=identificatie,
        omschrijving=zaak['omschrijving'],
        startdatum=datetime.strptime(zaak['startdatum'], '%Y-%m-%d').date(),
        tijdstip_registratie=datetime.strptime(zaak['tijdstipRegistratie'], '%Y-%m-%d %H:%M'),
        einddatum_gepland=datetime.strptime(zaak['einddatumGepland'], '%Y-%m-%d').date(),
        toelichting=zaak['toelichting'],
        archiefnominatie='J',
        zaaktype_omschrijving=app.config['ZDS_ZAAKTYPES'][zaak['zaaktype']]['omschrijving'],
        zaaktype_code=app.config['ZDS_ZAAKTYPES'][zaak['zaaktype']]['code'],
        registratienummer=zaak['kenmerken'][0]['kenmerk'],
        registratienummer_code=zaak['kenmerken'][0]['bron']
    )

    result = message.send(app.config['ZDS_ENDPOINT'], app.config['ADDITIONAL_ZDS_HEADERS'])
    app.logger.info(f'CreerZaakMessage. Received: {etree.tostring(result)}')

    return {
        'url': f'{request.base_url}/{identificatie}',
        'uuid': identificatie
    }

@app.route('/zgw/statussen', methods=['POST'])
def statussen():
    status = request.get_json()
    statustype = status['statustype']

    if not app.config['ZDS_ENABLED']:
        return {
            'url': f'{request.base_url}/{statustype}',
            'uuid': uuid.uuid4(),
            'zaak': status['zaak'],
            'statustype': statustype,
            'datumStatusGezet': status['datumStatusGezet']
        }

    message = ActualiseerZaakStatusMessage(
        zender=app.config['ZDS_ZENDER'],
        ontvanger=app.config['ZDS_ONTVANGER'],
        identificatie=status['zaak'],
        datum_status_gezet=datetime.strptime(status['datumStatusGezet'], '%Y-%m-%d'),
        statustype_volgnummer=app.config['ZDS_STATUSTYPES'][statustype]['volgnummer'],
        statustype_omschrijving=app.config['ZDS_STATUSTYPES'][statustype]['omschrijving'],
    )

    result = message.send(app.config['ZDS_ENDPOINT'], app.config['ADDITIONAL_ZDS_HEADERS'])
    app.logger.info(f'ActualiseerZaakStatusMessage. Received: {etree.tostring(result)}')

    return {
        'url': f'{request.base_url}/{statustype}',
        'uuid': uuid.uuid4(),
        'zaak': status['zaak'],
        'statustype': statustype,
        'datumStatusGezet': status['datumStatusGezet']
    }

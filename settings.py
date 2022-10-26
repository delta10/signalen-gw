import os

ZDS_ENABLED = True
BUITENBETER_ENABLED = True

ZDS_ENDPOINT = 'http://127.0.0.1:8002'
SIGNALEN_ENDPOINT = 'http://127.0.0.1:8000'

BUITENBETER_MACHINE_LEARNING_MINIMUM_CERTAINTY = 0.41
BUITENBETER_SOURCE_NAME = 'BuitenBeter'

ADDITIONAL_ZDS_HEADERS = {
  'x-opentunnel-api-key': os.getenv('ZDS_API_KEY', 'something-secret')
}

ADDITIONAL_SIGNALEN_HEADERS = {
  'Authorization': 'Bearer ' + os.getenv('SIGNALEN_TOKEN', 'something-secret')
}

ZDS_ZENDER = {
  'organisatie': 'Gemeente Test',
  'applicatie': 'SIGNALEN'
}

ZDS_ONTVANGER = {
  'organisatie': 'Gemeente Test',
  'applicatie': 'UITSTEKEND'
}

ZDS_ZAAKTYPES = {
  'MLDSIG': {
    'omschrijving': 'Melding Signalen',
    'code': 'MLDSIG'
  }
}

ZDS_STATUSTYPES = {
  'Ontvangen': {
    'volgnummer': '1',
    'omschrijving': 'Ontvangen'
  },
  'Afgehandeld': {
    'volgnummer': '2',
    'omschrijving': 'Afgehandeld'
  }
}

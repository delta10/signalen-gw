import re
import uuid
from datetime import datetime
from lxml import etree
from lxml.builder import ElementMaker
import requests

nsmap_soap = {
    'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
    'xs': 'http://www.w3.org/2001/XMLSchema',
}

nsmap_stuf_xsi = {
    'StUF': 'http://www.egem.nl/StUF/StUF0301',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
}

nsmap_stuf = {
    None: 'http://www.egem.nl/StUF/StUF0301'
}

nsmap_zkn = {
    'StUF': 'http://www.egem.nl/StUF/StUF0301',
    'ZKN': 'http://www.egem.nl/StUF/sector/zkn/0310'
}

soap = ElementMaker(namespace='http://schemas.xmlsoap.org/soap/envelope/', nsmap=nsmap_soap)
stuf_xsi = ElementMaker(namespace='http://www.egem.nl/StUF/StUF0301', nsmap=nsmap_stuf_xsi)
stuf = ElementMaker(namespace='http://www.egem.nl/StUF/StUF0301', nsmap=nsmap_stuf)
zkn = ElementMaker(namespace='http://www.egem.nl/StUF/sector/zkn/0310', nsmap=nsmap_zkn)


class Message:
    SOAP_ACTION = ''

    def tostring(self):
        header = soap.Header()
        body = soap.Body()
        envelope = soap.Envelope(header, body)

        return etree.tostring(envelope, pretty_print=True, xml_declaration=True, encoding='UTF-8')

    def send(self, endpoint, additional_headers):
        headers = {
            'Content-Type': 'text/xml; charset=UTF-8',
            'SOAPAction': self.SOAP_ACTION
        }

        response = requests.post(endpoint, self.tostring(), headers={ **headers, **additional_headers }, timeout=5)
        response.raise_for_status()

        return etree.fromstring(response.content)


class GenereerZaakIdentificatieMessage(Message):
    SOAP_ACTION = 'http://www.egem.nl/StUF/sector/zkn/0310/genereerZaakIdentificatie_Di02'

    def __init__(self, **kwargs):
        self.zender = kwargs.get('zender')
        self.ontvanger = kwargs.get('ontvanger')

    def tostring(self):
        berichtcode = stuf_xsi.berichtcode('Di02')

        organisatie = stuf_xsi.organisatie(self.zender['organisatie'])
        applicatie = stuf_xsi.applicatie(self.zender['applicatie'])
        zender = stuf_xsi.zender(organisatie, applicatie)

        organisatie = stuf_xsi.organisatie(self.ontvanger['organisatie'])
        applicatie = stuf_xsi.applicatie(self.ontvanger['applicatie'])
        ontvanger = stuf_xsi.ontvanger(organisatie, applicatie)

        referentienummer = stuf_xsi.referentienummer(str(uuid.uuid4()))
        tijdstipBericht = stuf_xsi.tijdstipBericht(datetime.today().strftime('%Y%m%d%H%M%S'))
        functie = stuf_xsi.functie('genereerZaakidentificatie')

        stuurgegevens = stuf_xsi.stuurgegevens(berichtcode, zender, ontvanger, referentienummer, tijdstipBericht, functie)

        bericht = zkn.genereerZaakIdentificatie_Di02(stuurgegevens)

        header = soap.Header()
        body = soap.Body(bericht)
        envelope = soap.Envelope(header, body)

        return etree.tostring(envelope, pretty_print=True, xml_declaration=True, encoding='UTF-8')


class CreerZaakMessage(Message):
    SOAP_ACTION = 'http://www.egem.nl/StUF/sector/zkn/0310/creeerZaak_Lk01'

    def __init__(self, **kwargs):
        self.zender = kwargs.get('zender')
        self.ontvanger = kwargs.get('ontvanger')
        self.identificatie = kwargs.get('identificatie')
        self.omschrijving = kwargs.get('omschrijving')
        self.startdatum = kwargs.get('startdatum')
        self.tijdstip_registratie = kwargs.get('tijdstip_registratie')
        self.einddatum_gepland = kwargs.get('einddatum_gepland')
        self.toelichting = kwargs.get('toelichting')
        self.archiefnominatie = kwargs.get('archiefnominatie')
        self.zaaktype_omschrijving = kwargs.get('zaaktype_omschrijving')
        self.zaaktype_code = kwargs.get('zaaktype_code')
        self.registratienummer = kwargs.get('registratienummer')
        self.registratienummer_code = kwargs.get('registratienummer_code')

    def tostring(self):
        berichtcode = stuf_xsi.berichtcode('Lk01')

        organisatie = stuf_xsi.organisatie(self.zender['organisatie'])
        applicatie = stuf_xsi.applicatie(self.zender['applicatie'])
        zender = stuf_xsi.zender(organisatie, applicatie)

        organisatie = stuf_xsi.organisatie(self.ontvanger['organisatie'])
        applicatie = stuf_xsi.applicatie(self.ontvanger['applicatie'])
        ontvanger = stuf_xsi.ontvanger(organisatie, applicatie)

        referentienummer = stuf_xsi.referentienummer(str(uuid.uuid4()))
        tijdstipBericht = stuf_xsi.tijdstipBericht(datetime.today().strftime('%Y%m%d%H%M%S'))
        entiteittype = stuf_xsi.entiteittype('ZAK')

        stuurgegevens = zkn.stuurgegevens(berichtcode, zender, ontvanger, referentienummer, tijdstipBericht, entiteittype)

        mutatiesoort = stuf_xsi.mutatiesoort('T')
        indicatorOvername = stuf_xsi.indicatorOvername('V')
        parameters = zkn.parameters(mutatiesoort, indicatorOvername)

        identificatie = zkn.identificatie(self.identificatie)
        omschrijving = zkn.omschrijving(self.omschrijving)
        startdatum = zkn.startdatum(self.startdatum.strftime('%Y%m%d'))
        tijdstipRegistratie = zkn.tijdstipRegistratie(self.tijdstip_registratie.strftime('%Y%m%d%H%M%S'))
        einddatumGepland = zkn.einddatumGepland(self.einddatum_gepland.strftime('%Y%m%d'))
        toelichting = zkn.toelichting(self.toelichting)
        archiefnominatie = zkn.archiefnominatie(self.archiefnominatie)
        zaakniveau = zkn.zaakniveau('1')
        deelzakenIndicatie = zkn.deelzakenIndicatie('N')

        gerelateerde_omschrijving = zkn.omschrijving(self.zaaktype_omschrijving)
        gerelateerde_code = zkn.code(self.zaaktype_code)

        gerelateerde = zkn.gerelateerde(gerelateerde_omschrijving, gerelateerde_code)
        gerelateerde.attrib['{http://www.egem.nl/StUF/StUF0301}entiteittype'] = 'ZKT'
        gerelateerde.attrib['{http://www.egem.nl/StUF/StUF0301}sleutelOntvangend'] = self.identificatie
        gerelateerde.attrib['{http://www.egem.nl/StUF/StUF0301}verwerkingssoort'] = 'T'

        isVan = zkn.isVan(gerelateerde)
        isVan.attrib['{http://www.egem.nl/StUF/StUF0301}entiteittype'] = 'ZAKZKT'
        isVan.attrib['{http://www.egem.nl/StUF/StUF0301}verwerkingssoort'] = 'T'

        extraElementKanaal = stuf_xsi.extraElement('OVERIGE')
        extraElementKanaal.attrib['naam'] = 'kanaal'

        extraElementRegistratienummer = stuf_xsi.extraElement(self.registratienummer)
        extraElementRegistratienummer.attrib['naam'] = 'registratienummer'

        extraElementRegistratienummerCode = stuf_xsi.extraElement(self.registratienummer_code)
        extraElementRegistratienummerCode.attrib['naam'] = 'registratienummerCode'

        extraElementen = stuf_xsi.extraElementen(extraElementKanaal, extraElementRegistratienummer, extraElementRegistratienummerCode)

        object = zkn.object(identificatie, omschrijving, startdatum, tijdstipRegistratie, einddatumGepland, toelichting, archiefnominatie, zaakniveau, deelzakenIndicatie, extraElementen, isVan)
        object.attrib['{http://www.egem.nl/StUF/StUF0301}entiteittype'] = 'ZAK'
        object.attrib['{http://www.egem.nl/StUF/StUF0301}sleutelGegevensbeheer'] = ''
        object.attrib['{http://www.egem.nl/StUF/StUF0301}verwerkingssoort'] = 'T'

        bericht = zkn.zakLk01(stuurgegevens, parameters, object)

        header = soap.Header()
        body = soap.Body(bericht)
        envelope = soap.Envelope(header, body)

        return etree.tostring(envelope, pretty_print=True, xml_declaration=True, encoding='UTF-8')


class ActualiseerZaakStatusMessage(Message):
    SOAP_ACTION = 'http://www.egem.nl/StUF/sector/zkn/0310/actualiseerZaakstatus_Lk01'

    def __init__(self, **kwargs):
        self.zender = kwargs.get('zender')
        self.ontvanger = kwargs.get('ontvanger')
        self.identificatie = kwargs.get('identificatie')
        self.einddatum = kwargs.get('einddatum')
        self.datum_status_gezet = kwargs.get('datum_status_gezet')
        self.statustype_volgnummer = kwargs.get('statustype_volgnummer')
        self.statustype_omschrijving = kwargs.get('statustype_omschrijving')

    def tostring(self):
        berichtcode = stuf_xsi.berichtcode('Lk01')

        organisatie = stuf_xsi.organisatie(self.zender['organisatie'])
        applicatie = stuf_xsi.applicatie(self.zender['applicatie'])
        zender = stuf_xsi.zender(organisatie, applicatie)

        organisatie = stuf_xsi.organisatie(self.ontvanger['organisatie'])
        applicatie = stuf_xsi.applicatie(self.ontvanger['applicatie'])
        ontvanger = stuf_xsi.ontvanger(organisatie, applicatie)

        referentienummer = stuf_xsi.referentienummer(str(uuid.uuid4()))
        tijdstipBericht = stuf_xsi.tijdstipBericht(datetime.today().strftime('%Y%m%d%H%M%S'))
        entiteittype = stuf_xsi.entiteittype('ZAK')

        stuurgegevens = zkn.stuurgegevens(berichtcode, zender, ontvanger, referentienummer, tijdstipBericht, entiteittype)

        mutatiesoort = stuf_xsi.mutatiesoort('W')
        indicatorOvername = stuf_xsi.indicatorOvername('V')
        parameters = zkn.parameters(mutatiesoort, indicatorOvername)

        identificatie = zkn.identificatie(self.identificatie)

        if self.einddatum:
            einddatum = zkn.einddatum(self.einddatum.strftime('%Y%m%d'))
        else:
            einddatum = zkn.einddatum()

        gerelateerde_volgnummer = zkn.volgnummer(self.statustype_volgnummer)
        gerelateerde_omschrijving = zkn.omschrijving(self.statustype_omschrijving)

        datumStatusGezet = zkn.datumStatusGezet(self.datum_status_gezet.strftime('%Y%m%d'))

        gerelateerde = zkn.gerelateerde(gerelateerde_volgnummer, gerelateerde_omschrijving)
        gerelateerde.attrib['{http://www.egem.nl/StUF/StUF0301}entiteittype'] = 'STT'
        gerelateerde.attrib['{http://www.egem.nl/StUF/StUF0301}verwerkingssoort'] = 'T'

        heeft = zkn.heeft(gerelateerde, datumStatusGezet)
        heeft.attrib['{http://www.egem.nl/StUF/StUF0301}entiteittype'] = 'ZAKSTT'
        heeft.attrib['{http://www.egem.nl/StUF/StUF0301}verwerkingssoort'] = 'T'

        object = zkn.object(identificatie, einddatum, heeft)

        object.attrib['{http://www.egem.nl/StUF/StUF0301}entiteittype'] = 'ZAK'
        object.attrib['{http://www.egem.nl/StUF/StUF0301}sleutelGegevensbeheer'] = ''
        object.attrib['{http://www.egem.nl/StUF/StUF0301}verwerkingssoort'] = 'T'

        bericht = zkn.zakLk01(stuurgegevens, parameters, object)
        body = soap.Body(bericht)
        envelope = soap.Envelope(body)

        return etree.tostring(envelope, pretty_print=True, xml_declaration=True, encoding='UTF-8')


class OntvangstbevestigingBv03:
    def __init__(self, **kwargs):
        self.zender = kwargs.get('zender')
        self.ontvanger = kwargs.get('ontvanger')
        self.cross_ref_number = kwargs.get('cross_ref_number')

    def tostring(self):
        berichtcode = stuf_xsi.berichtcode('Bv03')

        organisatie = stuf_xsi.organisatie(self.zender['organisatie'])
        applicatie = stuf_xsi.applicatie(self.zender['applicatie'])
        zender = stuf_xsi.zender(organisatie, applicatie)

        organisatie = stuf_xsi.organisatie(self.ontvanger['organisatie'])
        applicatie = stuf_xsi.applicatie(self.ontvanger['applicatie'])
        ontvanger = stuf_xsi.ontvanger(organisatie, applicatie)

        referentienummer = stuf_xsi.referentienummer(str(uuid.uuid4()))
        tijdstipBericht = stuf_xsi.tijdstipBericht(datetime.today().strftime('%Y%m%d%H%M%S'))
        crossRefnummer = stuf_xsi.crossRefnummer(self.cross_ref_number)

        stuurgegevens = stuf_xsi.stuurgegevens(berichtcode, zender, ontvanger, referentienummer, tijdstipBericht, crossRefnummer)

        bericht = stuf_xsi.Bv03Bericht(stuurgegevens)
        body = soap.Body(bericht)
        envelope = soap.Envelope(body)

        return etree.tostring(envelope, pretty_print=True, xml_declaration=True, encoding='UTF-8')


class FoutmeldingFo03:
    def __init__(self, **kwargs):
        self.zender = kwargs.get('organisatie')
        self.ontvanger = kwargs.get('ontvanger')
        self.cross_ref_number = kwargs.get('cross_ref_number')

    def tostring(self):
        berichtcode = stuf_xsi.berichtcode('Bv03')

        organisatie = stuf_xsi.organisatie(self.zender['organisatie'])
        applicatie = stuf_xsi.applicatie(self.zender['applicatie'])
        zender = stuf_xsi.zender(organisatie, applicatie)

        organisatie = stuf_xsi.organisatie(self.ontvanger['organisatie'])
        applicatie = stuf_xsi.applicatie(self.ontvanger['applicatie'])
        ontvanger = stuf_xsi.ontvanger(organisatie, applicatie)

        referentienummer = stuf_xsi.referentienummer(str(uuid.uuid4()))
        tijdstipBericht = stuf_xsi.tijdstipBericht(datetime.today().strftime('%Y%m%d%H%M%S'))
        crossRefnummer = stuf_xsi.crossRefnummer(self.cross_ref_number)

        stuurgegevens = stuf_xsi.stuurgegevens(berichtcode, zender, ontvanger, referentienummer, tijdstipBericht, crossRefnummer)

        bericht = stuf_xsi.Bv03Bericht(stuurgegevens)
        body = soap.Body(bericht)
        envelope = soap.Envelope(body)

        return etree.tostring(envelope, pretty_print=True, xml_declaration=True, encoding='UTF-8')


def is_valid_email(email):
    email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

    if re.fullmatch(email_regex, email):
        return True

    return False

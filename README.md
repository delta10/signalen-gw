# Signalen gateway

This gateway can be used to translate ZGW API calls from Signalen to StUF-ZKN to replicate Signals to a case-management system. Also the gateway can be used to translate StUF Lk01 messages from BuitenBeter to the Signalen API. This allows creating reports in Signalen from BuitenBeter.

## Run a development environment

Install the prerequisites with:

```bash
pip3 install -r requirements.txt
```

Then run a watch server with:

```bash
FLASK_APP=server FLASK_ENV=development flask run
```

## Run a production environment

Consider using the [Helm chart](https://github.com/delta10/helm-charts/tree/master/charts/signalen-gw).

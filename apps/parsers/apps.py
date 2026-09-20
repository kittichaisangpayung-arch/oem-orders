from django.apps import AppConfig


class ParsersConfig(AppConfig):
    name = 'apps.parsers'
    label = 'parsers'

    def ready(self):
        try:
            from . import donki  # noqa: F401  (registers DonkiParser with the registry)
            from . import lopia  # noqa: F401  (registers LopiaParser with the registry)
        except ImportError:
            pass  # pdfplumber not available, skip parser registration

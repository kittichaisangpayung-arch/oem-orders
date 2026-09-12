from django.apps import AppConfig


class ParsersConfig(AppConfig):
    name = 'apps.parsers'
    label = 'parsers'

    def ready(self):
        from . import donki  # noqa: F401  (registers DonkiParser with the registry)

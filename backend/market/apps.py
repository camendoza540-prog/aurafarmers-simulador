from django.apps import AppConfig


class MarketConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "market"
    verbose_name = "Mercado e instrumentos"

    def ready(self):
        import os
        import sys
        import threading

        # Con runserver, arrancar el reloj solo en el proceso que atiende peticiones
        serving = "runserver" in sys.argv and (os.environ.get("RUN_MAIN") == "true" or "--noreload" in sys.argv)
        serving = serving or "gunicorn" in sys.argv[0] or "uvicorn" in sys.argv[0]
        if serving:
            from .services.engine import start_market_clock
            threading.Timer(3.0, start_market_clock).start()

from django.core.management.base import BaseCommand

from market.models import Instrument
from market.services.engine import generate_history


class Command(BaseCommand):
    help = "Regenera la historia simulada o (con --real) intenta descargar datos reales de Yahoo Finance."

    def add_arguments(self, parser):
        parser.add_argument("--real", action="store_true", help="Intentar datos reales de Yahoo Finance.")
        parser.add_argument("symbols", nargs="*", help="Símbolos (por defecto todos).")

    def handle(self, *args, **opts):
        qs = Instrument.objects.filter(is_active=True)
        if opts["symbols"]:
            qs = qs.filter(symbol__in=[s.upper() for s in opts["symbols"]])
        for inst in qs:
            if opts["real"]:
                from market.services.yahoo import sync_instrument
                ok = sync_instrument(inst)
                msg = self.style.SUCCESS("datos reales") if ok else self.style.WARNING("sin conexión — se conserva lo simulado")
                self.stdout.write(f"{inst.symbol:<6} {msg}")
            else:
                n = generate_history(inst)
                self.stdout.write(f"{inst.symbol:<6} {n} días simulados")

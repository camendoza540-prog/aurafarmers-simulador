"""
Carga los datos iniciales del simulador (idempotente):
  · Catálogo de instrumentos + 2 años de historia de precios
  · Lecciones, cuestionarios y glosario
  · Usuario demo con portafolio y CDT de ejemplo
  · Superusuario para el panel /admin

Uso:  python manage.py seed            (crea lo que falte)
      python manage.py seed --reset-market   (regenera toda la historia de precios)
"""
import os
import secrets
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from learning.seed_data import seed_learning
from market.catalog import INSTRUMENTS
from market.models import Instrument
from market.services.engine import ensure_intraday, generate_history

CREDENTIALS_FILE = Path(settings.BASE_DIR) / "credenciales_locales.txt"


def _password(env_var: str) -> str:
    """Contraseña desde variable de entorno o aleatoria. Nunca se guarda en el código."""
    return os.environ.get(env_var) or f"Af-{secrets.token_urlsafe(9)}"


DEMO_USER = ("demo", "demo@aurafarmers.co", _password("AF_DEMO_PASSWORD"))
FRIEND_USER = ("ana", "ana@aurafarmers.co", _password("AF_ANA_PASSWORD"))
ADMIN_USER = ("admin", "admin@aurafarmers.co", _password("AF_ADMIN_PASSWORD"))
SUPPORT_USER = ("soporte", "soporte@aurafarmers.co", _password("AF_SUPPORT_PASSWORD"))


class Command(BaseCommand):
    help = "Carga instrumentos, historia de precios, contenido educativo y usuarios demo."

    def add_arguments(self, parser):
        parser.add_argument("--reset-market", action="store_true", help="Regenera la historia de precios.")
        parser.add_argument("--no-demo", action="store_true", help="No crea el usuario demo.")

    def handle(self, *args, **opts):
        self.stdout.write(self.style.MIGRATE_HEADING("1/4 Instrumentos e historia de precios"))
        for spec in INSTRUMENTS:
            inst, created = Instrument.objects.update_or_create(
                symbol=spec["symbol"],
                defaults=dict(
                    name=spec["name"], type=spec["type"], sector=spec["sector"],
                    asset_class=spec.get("asset_class", "equity"),
                    country=spec.get("country", "Estados Unidos"),
                    description=spec.get("description", ""),
                    news_query=spec.get("news_query", ""),
                    base_currency=spec.get("base", ""), quote_currency=spec.get("quote", "USD"),
                    leverage_cap=spec.get("cap"), spread=spec.get("spread"),
                    anchor_price=Decimal(str(spec["anchor"])),
                    annual_drift=spec["mu"], annual_volatility=spec["sigma"],
                    beta=spec.get("beta", 1.0), duration=spec.get("duration", 0.0),
                    base_volume=spec.get("volume", 1_000_000),
                ),
            )
            if created or opts["reset_market"] or not inst.bars.exists():
                n = generate_history(inst)
                ensure_intraday(inst)
                self.stdout.write(f"   {inst.symbol:<7} {inst.get_type_display():<14} {n} días + velas de 1 minuto")
        self.stdout.write(self.style.SUCCESS(f"   {Instrument.objects.count()} instrumentos listos"))

        self.stdout.write(self.style.MIGRATE_HEADING("2/4 Contenido educativo"))
        lessons, terms = seed_learning()
        self.stdout.write(self.style.SUCCESS(f"   {lessons} lecciones · {terms} términos de glosario"))

        self.stdout.write(self.style.MIGRATE_HEADING("3/4 Administración y soporte"))
        User = get_user_model()
        if not User.objects.filter(username=ADMIN_USER[0]).exists():
            User.objects.create_superuser(*ADMIN_USER)
            self._remember(ADMIN_USER, "Panel de administración (/admin)")
            self.stdout.write(self.style.SUCCESS("   admin creado"))
        else:
            self.stdout.write("   admin ya existía")
        if not User.objects.filter(username=SUPPORT_USER[0]).exists():
            User.objects.create_user(*SUPPORT_USER, first_name="Laura", last_name="Gómez", is_staff=True)
            self._remember(SUPPORT_USER, "Agente del equipo de soporte")
            self.stdout.write(self.style.SUCCESS("   agente de soporte creado"))

        self.stdout.write(self.style.MIGRATE_HEADING("4/4 Usuario demo"))
        if opts["no_demo"]:
            self.stdout.write("   omitido")
        elif User.objects.filter(username=DEMO_USER[0]).exists():
            self.stdout.write("   demo ya existía")
        else:
            self._create_demo(User)
            self._remember(DEMO_USER, "Usuario de prueba con portafolios, CFD y CDT")
            self._remember(FRIEND_USER, "Segunda usuaria, amiga de demo")
            self.stdout.write(self.style.SUCCESS("   usuarios demo y ana creados"))

        if CREDENTIALS_FILE.exists():
            self.stdout.write(self.style.WARNING(
                f"\nLas contraseñas de las cuentas de ejemplo están en {CREDENTIALS_FILE.name} "
                "(solo en este equipo; no lo compartas ni lo subas al repositorio)."))
        self.stdout.write(self.style.SUCCESS("\nListo. Ejecuta el backend con: python manage.py runserver"))

    def _remember(self, user_tuple, purpose):
        User = get_user_model()
        u = User.objects.filter(username=user_tuple[0]).first()
        if u and not u.profile.terms_accepted_at:
            u.profile.accept_terms()
        username, _, password = user_tuple
        new = not CREDENTIALS_FILE.exists()
        with CREDENTIALS_FILE.open("a", encoding="utf-8") as f:
            if new:
                f.write("Credenciales locales — Aura Farmers (generadas al instalar)\n"
                        "NO compartas este archivo ni lo subas al repositorio.\n"
                        "Para cambiar una contraseña: python manage.py changepassword <usuario>\n\n")
            f.write(f"{purpose}\n  usuario: {username}\n  contraseña: {password}\n\n")

    @transaction.atomic
    def _create_demo(self, User):
        from portfolios.services import create_portfolio, execute_trade
        from savings.services import open_account

        user = User.objects.create_user(DEMO_USER[0], DEMO_USER[1], DEMO_USER[2], first_name="Inversionista", last_name="Demo")
        user.profile.risk_profile = "moderado"
        user.profile.experience = "basica"
        user.profile.bio = "Aprender a invertir a largo plazo con un portafolio diversificado."
        user.profile.save()

        growth = create_portfolio(user, "Crecimiento", Decimal("40000"), "Acciones tecnológicas y el S&P 500.")
        for sym, amount in [("SPY", 12000), ("AAPL", 7000), ("NVDA", 6000), ("MSFT", 6000), ("QQQ", 5000)]:
            execute_trade(growth, sym, "BUY", amount=Decimal(amount))

        col = create_portfolio(user, "Colombia y defensivo", Decimal("20000"), "Exposición a Colombia, bonos y oro.")
        for sym, amount in [("GXG", 5000), ("CIB", 3000), ("EC", 2000), ("AGG", 5000), ("GLD", 3000)]:
            execute_trade(col, sym, "BUY", amount=Decimal(amount))

        open_account(user, "CDT90", Decimal("10000"), name="CDT de prueba")
        open_account(user, "AHORRO", Decimal("5000"), name="Fondo de emergencia")

        # Trading con margen: una compra apalancada con protección
        from portfolios.trading import open_position
        spy = Instrument.objects.get(symbol="SPY")
        open_position(growth, "SPY", "LONG", leverage=5, margin_amount=Decimal("2000"),
                      take_profit=(spy.current_price * Decimal("1.05")).quantize(Decimal("0.01")),
                      stop_loss=(spy.current_price * Decimal("0.97")).quantize(Decimal("0.01")))

        # Segunda usuaria, amistad y conversación
        from social.models import FriendRequest, Message
        ana = User.objects.create_user(FRIEND_USER[0], FRIEND_USER[1], FRIEND_USER[2], first_name="Ana", last_name="Rincón")
        ana.profile.risk_profile = "agresivo"
        ana.profile.description = "Estudiante de economía. Me interesan la tecnología y los mercados emergentes."
        ana.profile.save()
        pa = create_portfolio(ana, "Tecnología", Decimal("50000"), "Apuesta por semiconductores y nube.")
        for sym, amount in [("NVDA", 15000), ("MSFT", 10000), ("QQQ", 10000)]:
            execute_trade(pa, sym, "BUY", amount=Decimal(amount))
        FriendRequest.objects.create(from_user=ana, to_user=user, status="accepted")
        for sender, body in [
            (ana, "¡Hola! Vi que tienes SPY apalancado 1:5. ¿Dónde pusiste el stop loss?"),
            (user, "Hola Ana, lo dejé 3 % por debajo de la entrada. Con 1:5 eso es perder 15 % del margen como máximo."),
            (ana, "Tiene sentido. Yo estoy probando $NVDA en contado, la volatilidad está fuerte."),
        ]:
            Message.objects.create(sender=sender, recipient=ana if sender == user else user, body=body)

"""Formato de cifras para los mensajes al usuario (convención colombiana)."""


def usd(value, decimals: int = 2) -> str:
    txt = f"{float(value):,.{decimals}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"US$ {txt}"

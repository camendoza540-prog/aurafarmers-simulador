"""Preguntas frecuentes y respuesta automática inicial del soporte."""

FAQ = [
    {"category": "cuenta", "q": "¿Cómo cambio mi contraseña o mi foto?",
     "a": "Ve a Mi perfil. En «Seguridad» escribe tu contraseña actual y dos veces la nueva. En la parte superior puedes subir una foto (JPG, PNG o WebP, máximo 5 MB)."},
    {"category": "cuenta", "q": "¿El dinero es real?",
     "a": "No. Cada cuenta empieza con US$ 100.000 ficticios. Puedes reiniciar la simulación cuando quieras desde Mi perfil."},
    {"category": "operaciones", "q": "¿Qué diferencia hay entre «Contado» y «CFD con margen»?",
     "a": "En contado compras el activo completo con tu efectivo y solo ganas si sube. Con CFD depositas un margen, puedes usar apalancamiento y ganar si sube (compra) o si baja (venta en corto); las ganancias y pérdidas se multiplican."},
    {"category": "operaciones", "q": "¿Qué son el take profit y el stop loss?",
     "a": "Son órdenes automáticas. El take profit cierra la operación cuando alcanza la ganancia que fijaste; el stop loss la cierra para limitar la pérdida. Puedes editarlos desde la tabla de posiciones."},
    {"category": "operaciones", "q": "¿Por qué se cerró sola mi posición?",
     "a": "Por tres motivos: tocó tu take profit, tocó tu stop loss, o el nivel de margen bajó de 50 % y la plataforma cerró la posición con mayor pérdida (cierre forzoso), como hacen los brókeres regulados."},
    {"category": "operaciones", "q": "¿Qué es el spread?",
     "a": "Es la diferencia entre el precio de venta (bid) y el de compra (ask). Por eso una operación recién abierta muestra una pequeña pérdida."},
    {"category": "ahorro", "q": "¿Por qué no puedo retirar mi CDT?",
     "a": "Un CDT inmoviliza el dinero hasta su vencimiento a cambio de una tasa mayor. Usa «Simular el paso del tiempo» para llegar a la fecha de vencimiento y luego redímelo."},
    {"category": "escenarios", "q": "¿Qué significa el abanico de la simulación de escenarios?",
     "a": "Son 1.000 futuros posibles de tu portafolio. La línea central es el caso típico; la banda oscura contiene la mitad de los casos y la clara, el 90 %."},
]

CATEGORY_HINTS = {
    "operaciones": "Mientras tanto, en Aprende → «Riesgo y volatilidad» encontrarás cómo funciona el apalancamiento.",
    "ahorro": "Mientras tanto, revisa la lección «Interés compuesto, CDT y cuentas de ahorro».",
    "escenarios": "Mientras tanto, la lección «Crisis, tasas de interés y ciclos de mercado» explica los escenarios.",
}


def auto_reply(ticket) -> str:
    related = [f["q"] for f in FAQ if f["category"] == ticket.category][:2]
    text = (f"Hola, {ticket.user.first_name or ticket.user.username}. Recibimos tu solicitud #{ticket.pk}. "
            "Un agente del equipo de soporte te responderá en este mismo hilo.")
    if related:
        text += " Tal vez te sirvan estas preguntas frecuentes: " + " · ".join(related) + "."
    hint = CATEGORY_HINTS.get(ticket.category)
    if hint:
        text += " " + hint
    return text

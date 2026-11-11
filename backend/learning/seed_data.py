"""Contenido educativo inicial. Se carga con `python manage.py seed` (idempotente)."""
from django.db import transaction

LESSONS = [
    {
        "slug": "que-es-invertir", "order": 1, "category": "fundamentos", "level": "basico", "minutes": 4,
        "title": "¿Qué es invertir?",
        "summary": "La diferencia entre ahorrar e invertir, y por qué el tiempo es tu mejor aliado.",
        "try_it": "/portafolios",
        "content": """
Invertir es **poner tu dinero a trabajar** comprando algo que esperas que aumente de valor o que te pague ingresos: una parte de una empresa (acción), un fondo (ETF), un préstamo al gobierno (bono) o un depósito a plazo (CDT).

## Ahorrar no es lo mismo que invertir

Ahorrar es guardar dinero. Invertir es asumir un **riesgo** a cambio de un **rendimiento** esperado. Si guardas US$ 1.000 debajo del colchón durante 10 años con una inflación del 5 % anual, al final ese dinero comprará lo que hoy compran unos US$ 614.

## Tres preguntas antes de invertir

1. **¿Para qué es el dinero?** Un fondo de emergencia no debería estar en acciones.
2. **¿Cuándo lo necesito?** Entre más largo el horizonte, más riesgo puedes asumir, porque tienes tiempo para recuperarte de las caídas.
3. **¿Cuánta caída soporto sin vender?** Esa es tu tolerancia al riesgo, y define tu perfil: conservador, moderado o agresivo.

## Cómo usar este simulador

Empiezas con **US$ 100.000 ficticios** en tu cuenta principal. Desde ahí puedes crear portafolios, abrir CDT o cuentas de ahorro y simular crisis. Nada de esto es dinero real: equivócate aquí para no equivocarte allá afuera.
""",
        "questions": [
            ("¿Qué distingue a invertir de ahorrar?",
             ["Invertir no tiene riesgo", "Invertir implica asumir riesgo a cambio de un rendimiento esperado", "Ahorrar siempre rinde más", "No hay diferencia"],
             1, "Invertir es aceptar incertidumbre a cambio de la posibilidad de un mayor rendimiento."),
            ("Si necesitas el dinero en tres meses, ¿qué es más prudente?",
             ["Acciones de alta volatilidad", "Una cuenta de ahorro o un CDT corto", "Criptomonedas", "Un ETF tecnológico"],
             1, "Con horizontes cortos no hay tiempo para recuperarse de una caída del mercado."),
            ("¿Qué efecto tiene la inflación sobre el dinero quieto?",
             ["Lo aumenta", "No lo afecta", "Reduce su poder de compra", "Lo convierte en dólares"],
             2, "Con inflación positiva, la misma cantidad de dinero compra menos cosas con el tiempo."),
        ],
    },
    {
        "slug": "acciones", "order": 2, "category": "instrumentos", "level": "basico", "minutes": 5,
        "title": "Acciones: ser dueño de una empresa",
        "summary": "Qué compras cuando compras una acción y de dónde viene su rendimiento.",
        "try_it": "/mercado",
        "content": """
Una **acción** es una pequeña porción de propiedad de una empresa. Si compras una acción de Bancolombia (CIB), eres dueño de una fracción diminuta del banco.

## ¿De dónde viene la ganancia?

- **Valorización**: si la empresa crece y gana más, otros inversionistas estarán dispuestos a pagar más por sus acciones.
- **Dividendos**: algunas empresas reparten parte de sus utilidades entre los accionistas.

## ¿Por qué se mueve el precio?

El precio es el punto donde se encuentran compradores y vendedores. Lo mueven los resultados de la empresa, las noticias, las tasas de interés y el ánimo general del mercado. Por eso, aunque una empresa sea buena, su acción puede caer en una crisis.

## ADR: acciones colombianas en Nueva York

Ecopetrol (EC) y Bancolombia (CIB) cotizan en la Bolsa de Nueva York mediante **ADR**, certificados que representan acciones de empresas extranjeras y se negocian en dólares.

## En el simulador

En **Mercado** verás el precio actual, la variación del día y gráficas históricas. Puedes comprar **fracciones** de acción: si NVDA cuesta US$ 135, puedes invertir solo US$ 50. Cada operación paga una comisión de 0,1 % (mínimo US$ 1), como en un bróker real.
""",
        "questions": [
            ("Al comprar una acción, te conviertes en…",
             ["Acreedor de la empresa", "Copropietario de la empresa", "Empleado de la empresa", "Cliente preferencial"],
             1, "Una acción representa una fracción de la propiedad de la compañía."),
            ("¿Cuáles son las dos fuentes de rendimiento de una acción?",
             ["Intereses y comisiones", "Valorización y dividendos", "Cupones y amortizaciones", "Impuestos y subsidios"],
             1, "Ganas si sube el precio (valorización) o si la empresa reparte utilidades (dividendos)."),
            ("¿Qué es un ADR?",
             ["Un tipo de CDT", "Un certificado que permite negociar acciones extranjeras en EE. UU.", "Un índice bursátil", "Una criptomoneda"],
             1, "Los ADR permiten que empresas como Ecopetrol se negocien en Nueva York en dólares."),
        ],
    },
    {
        "slug": "etfs", "order": 3, "category": "instrumentos", "level": "basico", "minutes": 5,
        "title": "ETFs: diversificar con una sola compra",
        "summary": "Fondos que replican índices y por qué son la base de muchos portafolios.",
        "try_it": "/mercado",
        "content": """
Un **ETF** (Exchange Traded Fund, fondo cotizado en bolsa) es una canasta de activos que se compra y vende como si fuera una acción.

## Ejemplos del simulador

| ETF | Qué contiene |
|---|---|
| SPY | Las 500 empresas más grandes de EE. UU. |
| QQQ | Las 100 mayores empresas del Nasdaq (mucha tecnología) |
| GXG | Las principales empresas colombianas |
| AGG | Bonos de grado de inversión |
| GLD | Oro físico |

## Ventajas

- **Diversificación inmediata**: con una compra de SPY quedas expuesto a 500 empresas.
- **Bajo costo**: suelen cobrar comisiones de administración muy bajas.
- **Transparencia**: sabes exactamente qué índice siguen.

## Desventaja

Un ETF de índice nunca le gana al mercado: **es** el mercado. Si el S&P 500 cae 30 %, SPY también.

## Índice de referencia

En el simulador, **SPY** es el *benchmark*: en tu portafolio verás cómo te habría ido frente a simplemente comprar SPY. Ganarle al índice de forma consistente es mucho más difícil de lo que parece.
""",
        "questions": [
            ("¿Qué es un ETF?",
             ["Un préstamo bancario", "Una canasta de activos que se negocia como una acción", "Una cuenta de ahorro", "Una acción de una sola empresa"],
             1, "Un ETF agrupa muchos activos y se compra y vende en bolsa."),
            ("¿Cuál es la principal ventaja de SPY frente a comprar una sola acción?",
             ["Siempre sube", "No tiene comisiones", "Diversifica entre 500 empresas", "Paga intereses fijos"],
             2, "Con una sola compra tienes exposición a 500 empresas, lo que reduce el riesgo específico."),
            ("Si el S&P 500 cae 20 %, ¿qué pasa con SPY?",
             ["Sube 20 %", "Cae aproximadamente 20 %", "No cambia", "Cae 50 %"],
             1, "SPY replica el índice, así que se mueve casi igual."),
        ],
    },
    {
        "slug": "interes-compuesto-cdt", "order": 4, "category": "fundamentos", "level": "basico", "minutes": 6,
        "title": "Interés compuesto, CDT y cuentas de ahorro",
        "summary": "La fórmula que hace crecer el dinero y cómo leer una tasa efectiva anual.",
        "try_it": "/ahorro",
        "content": """
Con **interés simple** solo ganas intereses sobre el capital inicial. Con **interés compuesto** ganas intereses sobre los intereses ya ganados.

## La fórmula

**VF = VP × (1 + i)ⁿ**

- VP: valor presente (lo que depositas)
- i: tasa por periodo
- n: número de periodos

US$ 10.000 al 9 % E.A. durante 10 años: con interés simple terminas con US$ 19.000; con interés compuesto, con **US$ 23.674**.

## Tasa efectiva anual (E.A.)

En Colombia los bancos anuncian la tasa como **efectiva anual**: ya incluye la capitalización. Si ves una tasa **nominal** (por ejemplo 9 % N.M.V., nominal mes vencido), conviértela:

**E.A. = (1 + nominal / m)^m − 1**, donde m es el número de periodos al año.

Un 9 % N.M.V. equivale a 9,38 % E.A.

## CDT frente a cuenta de ahorro

| | Cuenta de ahorro | CDT |
|---|---|---|
| Liquidez | Inmediata | Al vencimiento |
| Tasa | Baja | Mayor |
| Aportes adicionales | Sí | No |

## Regla del 72

Divide 72 entre la tasa anual para estimar en cuántos años se duplica tu dinero: al 9 %, unos **8 años**.

En **Ahorro** puedes abrir CDT y usar el botón **Avanzar tiempo** para ver crecer el saldo sin esperar meses reales.
""",
        "questions": [
            ("¿Qué diferencia al interés compuesto del simple?",
             ["Tiene una tasa más alta", "Genera intereses sobre los intereses acumulados", "Solo existe en los CDT", "Se paga por adelantado"],
             1, "La capitalización hace que los intereses ganados también generen intereses."),
            ("Según la regla del 72, ¿en cuántos años se duplica el dinero al 6 % anual?",
             ["6", "12", "18", "72"],
             1, "72 ÷ 6 = 12 años aproximadamente."),
            ("¿Por qué un CDT suele pagar más que una cuenta de ahorro?",
             ["Porque no tiene riesgo", "Porque el dinero queda inmovilizado hasta el vencimiento", "Porque lo garantiza la bolsa", "Porque paga en dólares"],
             1, "Renunciar a la liquidez se compensa con una tasa mayor."),
        ],
    },
    {
        "slug": "riesgo-volatilidad", "order": 5, "category": "riesgo", "level": "intermedio", "minutes": 6,
        "title": "Riesgo y volatilidad",
        "summary": "Cómo se mide el riesgo: volatilidad, beta, caída máxima y VaR.",
        "try_it": "/mercado",
        "content": """
En finanzas, **riesgo** es la incertidumbre sobre el resultado. La forma más común de medirlo es la **volatilidad**.

## Volatilidad (σ)

Es la desviación estándar de los rendimientos, expresada en términos anuales. Una volatilidad del 17 % (como el S&P 500) significa que, en un año típico, es normal que el rendimiento se aleje unos 17 puntos de su promedio, para arriba o para abajo.

- Coca-Cola (KO): ~15 % → baja
- Apple (AAPL): ~27 % → media
- Tesla (TSLA): ~58 % → muy alta

## Beta (β)

Mide cuánto se mueve un activo cuando se mueve el mercado. β = 1,5 significa que si el mercado sube 10 %, el activo tiende a subir 15 %, y lo mismo en las caídas.

## Caída máxima (*drawdown*)

La mayor pérdida desde un pico hasta un valle. Es la métrica que mejor refleja lo que **se siente** invertir.

## Valor en riesgo (VaR 95 %)

Es la pérdida que no deberías superar en el 95 % de los días. Si tu VaR diario es US$ 1.200, uno de cada veinte días podrías perder más que eso.

## Riesgo y rendimiento van juntos

No existe rendimiento alto sin riesgo alto. Desconfía de cualquiera que te prometa lo contrario. El **índice de Sharpe** mide cuánto rendimiento obtienes por cada unidad de riesgo: más alto es mejor.
""",
        "questions": [
            ("Un activo con beta 0,5 frente a una caída del mercado de 10 % tiende a…",
             ["Caer 5 %", "Caer 10 %", "Caer 20 %", "Subir 5 %"],
             0, "Beta 0,5 implica que se mueve la mitad que el mercado."),
            ("¿Qué mide la caída máxima (drawdown)?",
             ["El rendimiento promedio", "La mayor pérdida desde un pico hasta un valle", "La comisión pagada", "El precio mínimo histórico"],
             1, "Es la peor racha de pérdidas que habrías vivido."),
            ("¿Qué indica un índice de Sharpe alto?",
             ["Más riesgo sin recompensa", "Más rendimiento por cada unidad de riesgo", "Menos liquidez", "Mayor inflación"],
             1, "El Sharpe compara el rendimiento extra frente a la volatilidad asumida."),
        ],
    },
    {
        "slug": "rendimiento", "order": 6, "category": "riesgo", "level": "intermedio", "minutes": 5,
        "title": "Cómo medir tu rendimiento",
        "summary": "Ganancia realizada vs. no realizada, comisiones y comparación con un índice.",
        "try_it": "/portafolios",
        "content": """
Saber si lo estás haciendo bien exige medir correctamente.

## Ganancia no realizada y realizada

- **No realizada**: la diferencia entre el valor actual de tus posiciones y lo que pagaste por ellas. Existe solo en papel.
- **Realizada**: la ganancia o pérdida que se concreta al vender.

## Costo promedio

Si compras 10 acciones a US$ 100 y luego 10 a US$ 120, tu costo promedio es US$ 110. El simulador incluye la comisión en el costo.

## Rendimiento total

**Rendimiento = (Valor actual − Aportes netos) / Aportes netos**

Los aportes netos son lo que depositaste menos lo que retiraste. Así un depósito nuevo no se confunde con una ganancia.

## Compárate con un índice

Ganar 8 % en un año suena bien, pero si el S&P 500 ganó 20 %, tu estrategia rindió menos que comprar SPY y olvidarte. En cada portafolio verás la línea de **SPY** como referencia.

## Las comisiones importan

Una comisión de 0,1 % parece poca, pero quien compra y vende todos los días la paga cientos de veces. El simulador te avisará si las comisiones se están comiendo tu rendimiento.
""",
        "questions": [
            ("¿Cuándo se convierte una ganancia en realizada?",
             ["Cuando sube el precio", "Cuando vendes la posición", "Al final del año", "Nunca"],
             1, "Mientras no vendas, la ganancia es solo potencial."),
            ("Compras 10 acciones a US$ 50 y 10 a US$ 70. ¿Cuál es tu costo promedio (sin comisiones)?",
             ["US$ 50", "US$ 60", "US$ 70", "US$ 120"],
             1, "(10×50 + 10×70) / 20 = US$ 60."),
            ("¿Para qué sirve comparar tu portafolio con SPY?",
             ["Para pagar menos impuestos", "Para saber si tu estrategia supera simplemente invertir en el mercado", "Para aumentar la liquidez", "No sirve"],
             1, "El benchmark muestra si tus decisiones agregan valor frente a la alternativa pasiva."),
        ],
    },
    {
        "slug": "diversificacion", "order": 7, "category": "estrategia", "level": "intermedio", "minutes": 5,
        "title": "Diversificación",
        "summary": "Por qué no poner todos los huevos en la misma canasta funciona matemáticamente.",
        "try_it": "/portafolios",
        "content": """
Diversificar es repartir tu dinero entre activos que **no se mueven exactamente igual**. Cuando uno cae, otro puede mantenerse o subir.

## Riesgo específico y riesgo de mercado

- **Específico**: el que afecta a una sola empresa (un mal resultado, un escándalo). Se reduce diversificando.
- **De mercado** o sistemático: el que afecta a todos (una recesión). No desaparece diversificando entre acciones.

## Correlación

Mide qué tanto se mueven dos activos juntos, de −1 a +1. Combinar acciones con bonos u oro, que suelen tener correlación baja o negativa con las acciones, reduce la volatilidad total.

## Cómo la mide el simulador

Usamos el **índice Herfindahl-Hirschman (HHI)**: la suma de los pesos al cuadrado. Con 1/HHI obtienes el número de **activos efectivos**: un portafolio de 10 acciones con 90 % en una sola se comporta como si tuviera poco más de 1 activo.

## Errores comunes

- Comprar cinco acciones tecnológicas y creer que estás diversificado.
- Tener más del 25 % en una sola posición.
- Olvidar otras clases de activo: bonos, oro, inmobiliario.

## Diversificar no es garantía

En crisis fuertes las correlaciones suben y casi todo cae junto. Por eso la renta fija y el efectivo cumplen un papel de amortiguador.
""",
        "questions": [
            ("¿Qué tipo de riesgo se reduce al diversificar entre muchas acciones?",
             ["El riesgo de mercado", "El riesgo específico de cada empresa", "El riesgo de inflación", "Ninguno"],
             1, "Los problemas de una sola empresa pesan menos cuando tienes muchas."),
            ("Tienes AAPL, MSFT, NVDA, GOOGL y META. ¿Estás bien diversificado?",
             ["Sí, son cinco empresas", "No, todas pertenecen al sector tecnológico y se mueven parecido", "Sí, porque son grandes", "Depende del día"],
             1, "Mismo sector implica alta correlación: caen juntas."),
            ("¿Qué activo suele amortiguar las caídas de las acciones?",
             ["Una acción de alto beta", "Bonos de alta calidad u oro", "Otra acción del mismo sector", "Un ETF apalancado"],
             1, "Tienden a tener baja o negativa correlación con la renta variable en crisis."),
        ],
    },
    {
        "slug": "crisis-y-ciclos", "order": 8, "category": "estrategia", "level": "intermedio", "minutes": 6,
        "title": "Crisis, tasas de interés y ciclos de mercado",
        "summary": "Qué pasó en 2000, 2008, 2020 y 2022, y qué enseñan para tu portafolio.",
        "try_it": "/escenarios",
        "content": """
Los mercados alternan periodos de crecimiento (**mercado alcista**) con caídas de 20 % o más (**mercado bajista**). Las caídas no son la excepción: son parte del ciclo.

## Cuatro episodios

- **2000 – Burbuja puntocom**: empresas de internet sin utilidades llegaron a precios absurdos. El Nasdaq cayó 78 %.
- **2008 – Crisis financiera**: hipotecas de mala calidad contaminaron a los bancos. El S&P 500 perdió más de 50 %.
- **2020 – Pandemia**: caída de 34 % en apenas 23 días hábiles y recuperación total en cinco meses.
- **2022 – Inflación**: la Reserva Federal subió tasas con fuerza. Cayeron a la vez acciones y bonos.

## Tasas de interés

Cuando suben las tasas:

- Los **bonos existentes pierden valor**; más entre mayor su duración.
- Las acciones suelen caer, sobre todo las de crecimiento.
- El efectivo y los **CDT rinden más**.

La **duración** de un bono indica cuánto cae su precio por cada punto que suben las tasas: TLT tiene duración ~16, así que +1 punto de tasa ≈ −16 % de precio.

## Lecciones

1. Nadie predice el momento exacto de una crisis.
2. Vender en pánico convierte una caída temporal en pérdida permanente.
3. Un horizonte largo y un portafolio diversificado son la mejor defensa.

En **Escenarios** puedes aplicar cada una de estas crisis a tu propio portafolio y ver mil futuros posibles.
""",
        "questions": [
            ("¿Qué le pasa al precio de un bono existente cuando suben las tasas de interés?",
             ["Sube", "Baja", "No cambia", "Se duplica"],
             1, "Los bonos nuevos pagan más, así que los antiguos valen menos."),
            ("¿Qué distinguió la caída de 2020?",
             ["Duró diez años", "Fue la más rápida de la historia y se recuperó en meses", "Solo afectó a Colombia", "Afectó solo a los bonos"],
             1, "Cayó 34 % en 23 días hábiles y recuperó su máximo en agosto de 2020."),
            ("¿Qué suele convertir una caída temporal en una pérdida permanente?",
             ["Mantener la inversión", "Vender en pánico en el punto bajo", "Diversificar", "Invertir en ETFs"],
             1, "Al vender en el fondo se materializa la pérdida y se pierde la recuperación."),
        ],
    },
]

GLOSSARY = [
    ("Acción", "Título que representa una fracción de la propiedad de una empresa."),
    ("ADR", "American Depositary Receipt: certificado que permite negociar en EE. UU. acciones de empresas extranjeras, como Ecopetrol o Bancolombia."),
    ("Benchmark", "Índice de referencia con el que se compara el rendimiento de un portafolio. En el simulador es SPY (S&P 500)."),
    ("Beta", "Sensibilidad de un activo a los movimientos del mercado. Beta 1 = se mueve como el mercado."),
    ("Bono", "Préstamo que haces a un gobierno o empresa a cambio de intereses periódicos y la devolución del capital."),
    ("CDT", "Certificado de Depósito a Término: depósito a plazo fijo con una tasa pactada, muy común en Colombia."),
    ("Comisión", "Costo cobrado por el intermediario en cada operación. En el simulador: 0,1 % con mínimo de US$ 1."),
    ("Diversificación", "Repartir la inversión entre activos distintos para reducir el riesgo."),
    ("Dividendo", "Parte de las utilidades que una empresa reparte entre sus accionistas."),
    ("Drawdown", "Caída porcentual desde el máximo previo hasta un mínimo posterior."),
    ("Duración", "Medida de la sensibilidad del precio de un bono a cambios en la tasa de interés."),
    ("ETF", "Fondo cotizado en bolsa que replica un índice o una canasta de activos."),
    ("Interés compuesto", "Interés que se calcula sobre el capital más los intereses acumulados."),
    ("Liquidez", "Facilidad con la que un activo se convierte en efectivo sin perder valor."),
    ("Monte Carlo", "Técnica que simula miles de escenarios aleatorios para estimar la distribución de resultados posibles."),
    ("Portafolio", "Conjunto de inversiones de una persona o entidad."),
    ("RSI", "Índice de fuerza relativa: indicador entre 0 y 100. Sobre 70 sugiere sobrecompra; bajo 30, sobreventa."),
    ("Sharpe", "Rendimiento por encima de la tasa libre de riesgo dividido entre la volatilidad."),
    ("Tasa efectiva anual (E.A.)", "Tasa que expresa el rendimiento real de un año incluyendo la capitalización de intereses."),
    ("VaR", "Valor en Riesgo: pérdida máxima esperada con un nivel de confianza dado (p. ej., 95 %) en un periodo."),
    ("Volatilidad", "Desviación estándar anualizada de los rendimientos; la medida más usada de riesgo."),
]


@transaction.atomic
def seed_learning():
    from .models import GlossaryTerm, Lesson, QuizQuestion

    for spec in LESSONS:
        data = {k: v for k, v in spec.items() if k not in ("slug", "questions")}
        data["content"] = data["content"].strip()
        lesson, _ = Lesson.objects.update_or_create(slug=spec["slug"], defaults=data)
        lesson.questions.all().delete()
        QuizQuestion.objects.bulk_create([
            QuizQuestion(lesson=lesson, question=q, options=opts, correct_index=ci, explanation=exp, order=i)
            for i, (q, opts, ci, exp) in enumerate(spec["questions"])
        ])
    for term, definition in GLOSSARY:
        GlossaryTerm.objects.update_or_create(term=term, defaults={"definition": definition})
    return len(LESSONS), len(GLOSSARY)

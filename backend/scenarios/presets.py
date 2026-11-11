"""Escenarios predefinidos inspirados en episodios reales del mercado."""

PRESETS = [
    {
        "key": "normal", "name": "Mercado normal",
        "summary": "Sin choques: el mercado se comporta según su historia reciente.",
        "context": "Sirve como línea base para comparar los demás escenarios.",
        "params": {"market_shock": 0, "shock_days": 0, "recovery": 0, "volatility_multiplier": 1.0,
                   "rate_change": 0, "drift_adjustment": 0, "horizon_days": 252},
    },
    {
        "key": "crisis_2008", "name": "Crisis financiera 2008",
        "summary": "Caída de −38 % en seis meses, volatilidad 2,3× y recuperación lenta.",
        "context": "La quiebra de Lehman Brothers y la crisis hipotecaria de EE. UU. llevaron al S&P 500 a perder más del 50 % entre 2007 y 2009. Los bonos del Tesoro subieron mientras la Reserva Federal bajaba tasas.",
        "params": {"market_shock": -38, "shock_days": 120, "recovery": 20, "volatility_multiplier": 2.3,
                   "rate_change": -2.0, "drift_adjustment": -2, "horizon_days": 504},
    },
    {
        "key": "covid_2020", "name": "Pandemia 2020",
        "summary": "Desplome de −32 % en un mes y rebote casi total.",
        "context": "En marzo de 2020 el S&P 500 cayó 34 % en 23 días hábiles, la caída más rápida de la historia. Los estímulos fiscales y monetarios produjeron una recuperación completa en cinco meses.",
        "params": {"market_shock": -32, "shock_days": 23, "recovery": 90, "volatility_multiplier": 2.0,
                   "rate_change": -1.5, "drift_adjustment": 0, "horizon_days": 252},
    },
    {
        "key": "tasas_2022", "name": "Inflación y alza de tasas 2022",
        "summary": "Tasas +3,5 puntos, acciones −18 % y bonos largos castigados.",
        "context": "Para frenar la inflación, los bancos centrales subieron tasas al ritmo más rápido en 40 años. Cayeron a la vez acciones y bonos: el ETF TLT perdió cerca de 30 %.",
        "params": {"market_shock": -18, "shock_days": 180, "recovery": 0, "volatility_multiplier": 1.4,
                   "rate_change": 3.5, "drift_adjustment": -1, "horizon_days": 252},
    },
    {
        "key": "puntocom_2000", "name": "Burbuja puntocom 2000",
        "summary": "Caída larga de −45 % durante casi dos años.",
        "context": "Las empresas de internet sobrevaloradas colapsaron entre 2000 y 2002. El Nasdaq perdió 78 % y tardó 15 años en recuperar su máximo.",
        "params": {"market_shock": -45, "shock_days": 400, "recovery": 10, "volatility_multiplier": 1.6,
                   "rate_change": -3.0, "drift_adjustment": -3, "horizon_days": 504},
    },
    {
        "key": "alcista", "name": "Mercado alcista",
        "summary": "Rendimiento esperado +10 puntos y volatilidad baja.",
        "context": "Periodos como 2013, 2017 o 2021 combinaron crecimiento económico, tasas bajas y optimismo, con subidas sostenidas y pocas caídas.",
        "params": {"market_shock": 0, "shock_days": 0, "recovery": 0, "volatility_multiplier": 0.8,
                   "rate_change": -0.5, "drift_adjustment": 10, "horizon_days": 252},
    },
]

PRESETS_BY_KEY = {p["key"]: p for p in PRESETS}

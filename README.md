# Aura Farmers · Plataforma de Simulación de Inversión

Proyecto final de **Ingeniería de Software I** — UIS, 2026-2 · Grupo 5 (Aura Farmers).

Plataforma web educativa para simular inversiones en acciones, ETFs, cuentas de ahorro y CDT con dinero ficticio. Incluye un terminal de trading con gráficos en vivo, operaciones con apalancamiento, take profit y stop loss, simulación de crisis históricas, ranking, chat entre usuarios y soporte.

**Stack:** Django 5 + Django REST Framework + JWT (backend) · React 18 + Vite + Recharts (frontend) · SQLite.

---

## 1. Requisitos

| Herramienta | Versión | Descarga |
|---|---|---|
| Python | 3.10 o superior | https://www.python.org/downloads/ (en Windows marca **"Add python.exe to PATH"**) |
| Node.js | 20.19 o superior (LTS; recomendado 22 o 24) | https://nodejs.org/ |
| VS Code | cualquiera | https://code.visualstudio.com/ |

No se necesitan API keys ni conexión a internet para usar el simulador (los precios se generan localmente).

---

## 2. Instalación y ejecución

### Opción A — Windows con doble clic

1. Descomprime el proyecto.
2. Doble clic en **`setup.bat`** (solo la primera vez; tarda unos minutos).
3. Doble clic en **`run.bat`**. Se abren dos ventanas (backend y frontend) y el navegador en **http://localhost:5173**.

### Opción B — Desde VS Code

1. `Archivo → Abrir carpeta…` y selecciona la carpeta del proyecto.
2. Primera vez: `Ctrl + Shift + P` → **Tasks: Run Task** → **Instalar todo (primera vez)**.
3. Para ejecutar: **`Ctrl + Shift + B`** (tarea **Ejecutar todo**). Levanta Django y Vite en dos terminales.

Otras tareas disponibles (`Tasks: Run Task`): **Pruebas del backend**, **Reiniciar base de datos**. En la pestaña *Run and Debug* está **Depurar Django** para poner puntos de interrupción.

### Opción C — macOS / Linux

```bash
./setup.sh   # primera vez
./run.sh     # cada vez que quieras ejecutarlo
```

### Opción D — Manual (cualquier sistema)

```bash
# Terminal 1 — backend
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python manage.py migrate
python manage.py seed
python manage.py runserver

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

### Cuentas incluidas

La instalación crea cuatro cuentas de ejemplo: `demo` (con portafolios, una posición CFD y CDT), `ana` (amiga de `demo`, con conversación), `soporte` (agente del equipo de soporte) y `admin` (panel http://localhost:8000/admin).

**Las contraseñas no están en el código.** Se generan al azar durante `setup` y quedan solo en `backend/credenciales_locales.txt`. Ese archivo está en `.gitignore`: no se sube al repositorio ni se comparte.

- Para fijarlas tú mismo, define antes del `setup` las variables `AF_DEMO_PASSWORD`, `AF_ANA_PASSWORD`, `AF_SUPPORT_PASSWORD` y `AF_ADMIN_PASSWORD`.
- Para cambiarlas después: `python manage.py changepassword <usuario>`.

También puedes registrar cuentas nuevas desde la pantalla de inicio: cada usuario empieza con **US$ 100.000 ficticios**.

---|---|---|
| Usuario demo: 2 portafolios, una posición CFD 1:5 con TP/SL, CDT y cuenta de ahorro | `demo` | `Demo12345!` |
| Segunda usuaria, amiga de `demo`, con conversación de ejemplo | `ana` | `Demo12345!` |
| Agente del equipo de soporte (ve y responde todos los tickets) | `soporte` | `Soporte12345!` |
| Panel de administración Django — http://localhost:8000/admin | `admin` | `Admin12345!` |

También puedes registrar cuentas nuevas desde la pantalla de inicio: cada usuario empieza con **US$ 100.000 ficticios**.

---

### Opción en la nube: GitHub Codespaces (sin instalar nada)

El repositorio incluye la configuración `.devcontainer`, así que se puede ejecutar completo desde GitHub, en el navegador:

1. En la página del repositorio en GitHub: **Code → Codespaces → Create codespace on main**.
2. Espera unos minutos: el entorno se crea con Python 3.12 y Node 22, y `setup.sh` se ejecuta solo.
3. En la terminal del Codespace escribe `./run.sh`.
4. Abre la pestaña **PORTS** y haz clic en el puerto **5173** («Aura Farmers»). También puedes usar la dirección que imprime `run.sh`.
5. Las contraseñas de las cuentas de ejemplo están en `backend/credenciales_locales.txt`.

GitHub ofrece horas gratuitas de Codespaces cada mes para cuentas personales; detén el Codespace cuando termines. GitHub Pages **no** sirve para este proyecto, porque solo publica páginas estáticas y la plataforma necesita el servidor de Django.

```bash
export NVM_DIR="/usr/local/share/nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs
fi
bash setup.sh && bash run.sh
```

## 3. Funcionalidades (según el enunciado)

| Requisito del enunciado | Implementación |
|---|---|
| **1. Registro y perfil** — autenticación, saldo ficticio, portafolios | Registro e inicio de sesión con JWT; perfil con saldo inicial, perfil de riesgo, experiencia y objetivo; cambio de contraseña; reinicio de la simulación. |
| **2. Simulación de inversiones** — compra/venta, precios históricos y actuales, ahorro con interés compuesto | 66 instrumentos con precios en vivo y 2 años de historia (ver tabla siguiente). Compra/venta de contado por unidades o por monto, acciones fraccionadas y comisión de 0,1 % (mín. US$ 1). Cuenta de ahorro y CDT a 90/180/360 días con tasa efectiva anual. |

### Catálogo de instrumentos

| Tipo | Cantidad | Ejemplos | Cómo se opera | Apalancamiento máx. |
|---|---|---|---|---|
| Acciones | 16 | AAPL, NVDA, TSLA, MELI, Ecopetrol (EC), Bancolombia (CIB) | Contado o CFD | 1:5 |
| ETFs | 27 | SPY, VOO, QQQ, DIA, IWM, sectoriales (XLK, XLF, XLE, XLV), GXG (Colombia), EWZ, ILF, VEA, EEM, ARKK, SCHD, oro, plata, petróleo, bitcoin (IBIT) y bonos (AGG, BND, TLT, SHY, HYG) | Contado o CFD | 1:5 |
| Forex | 9 | EURUSD, GBPUSD, AUDUSD, USDJPY, USDCHF, USDCAD, USDCOP, USDMXN, USDBRL | Solo CFD | 1:30 mayores · 1:20 exóticas |
| Índices | 4 | US500 (S&P 500), US100 (Nasdaq 100), US30 (Dow Jones), US2000 (Russell 2000) | Solo CFD | 1:20 |
| Materias primas | 7 | Oro (XAUUSD), plata, petróleo WTI y Brent, gas natural, café arábica, cobre | Solo CFD | 1:20 oro · 1:10 resto |
| Criptomonedas | 3 | BTCUSD, ETHUSD, SOLUSD | Solo CFD | 1:2 |

Los pares cuya moneda base es el dólar (USDJPY, USDCOP, USDMXN…) cotizan en la moneda local. El margen y las ganancias se convierten automáticamente a USD, como en un bróker real.
| **3. Portafolios** — múltiples portafolios, rendimiento y balance | Hasta 10 portafolios por usuario, cada uno con su efectivo; aportes y retiros; valoración en tiempo real; ganancia realizada/no realizada; historial de operaciones; cierre con liquidación automática. |
| **4. Datos y gráficos** — rendimiento por instrumento y portafolio, tendencias y estadísticas | Gráficas de precio con promedios móviles de 20 y 50 días; rendimientos 1D/1M/3M/6M/YTD/1A; volatilidad, beta, Sharpe, RSI, caída máxima y tendencia. En portafolios: distribución por activo/sector/clase, volatilidad, VaR 95 %, índice de diversificación, comparación contra el S&P 500 y evolución del valor. |
| **5. Aprendizaje y guías** | 8 lecciones (fundamentos, instrumentos, riesgo, estrategia) con cuestionario, seguimiento de progreso y glosario de 21 términos. Retroalimentación automática sobre cada portafolio (concentración, efectivo quieto, riesgo frente al perfil, comisiones…). |
| **6. Simulación de escenarios** — crisis, incrementos, tasas de interés, volatilidad | Monte Carlo de 1.000 trayectorias sobre el portafolio del usuario, incluidas sus posiciones apalancadas. Escenarios predefinidos (crisis 2008, pandemia 2020, alza de tasas 2022, burbuja puntocom, mercado alcista) y personalizados: choque, duración, recuperación, volatilidad, tasas, rendimiento y horizonte. La volatilidad extra sube durante el choque y se normaliza después. |

### Funcionalidades adicionales

| Módulo | Qué incluye |
|---|---|
| **Terminal de trading** (`/mercado/<símbolo>`) | Gráfico interactivo con velas, Heikin Ashi, barras OHLC, línea o área. Temporalidades de 1m, 5m, 15m, 30m, 1h, 1D, 1S y 1M. Indicadores SMA 20/50, EMA 20, Bollinger, volumen, RSI y MACD. Herramientas de línea horizontal y línea de tendencia, guardadas por activo. El precio se actualiza cada segundo. |
| **Trading con margen (CFD)** | Compra (largo) o venta en corto con apalancamiento 1:1 a 1:30, limitado según la clase de activo con los topes ESMA (ver catálogo). Precios bid/ask con spread y margen bloqueado. Aviso de margen bajo 100 % y cierre forzoso bajo 50 %. Protección de saldo negativo. |
| **Take profit y stop loss** | En posiciones CFD y en compras de contado. Se fijan al abrir y se editan después. Se ejecutan solos con el movimiento del precio y se notifican. |
| **Noticias** | Titulares recientes de cada activo desde Google Noticias en español, con Yahoo Finance como respaldo; enlazan a la nota original. Requiere internet en el servidor. |
| **CDT rediseñado** | Simulador con monto, plazo y fecha de vencimiento. Comparación contra cuenta de ahorro e inflación. Tarjetas con progreso y valor al vencimiento. Opciones para simular el paso del tiempo, cobrar y renovar. |
| **Ranking** | Podio y tabla con nombre, foto, patrimonio, ganancia en US$ y %, operaciones y operaciones ganadoras. Cada usuario decide si aparece. |
| **Comunidad** | Búsqueda de usuarios, solicitudes de amistad (enviar, aceptar, rechazar, cancelar) y chat 1 a 1. Al escribir `$AAPL` se crea un enlace al activo. Insignias de mensajes sin leer. |
| **Soporte** | Preguntas frecuentes con buscador, tickets por categoría, respuesta automática inicial y bandeja del equipo de soporte. El usuario recibe aviso cuando le responden. |
| **Privacidad y datos (Ley 1581)** | Aceptación obligatoria de los términos y de la política de tratamiento de datos al registrarse, con fecha y versión guardadas. Página pública `/legal`. Si la versión cambia, se pide aceptarla de nuevo. Desde el perfil se puede eliminar la cuenta con todos sus datos (contraseña + «ELIMINAR»). |
| **Perfil** | Foto (se recorta a 320×320 px), descripción breve, datos personales, preferencias, cambio de contraseña con confirmación e indicador de fortaleza, y reinicio de la simulación. |

Además: calculadora de interés compuesto (tasa E.A. o nominal, inflación, regla del 72) e interfaz responsiva.

---

## 4. Arquitectura

```
┌────────────────────────────┐   HTTP/JSON + JWT   ┌──────────────────────────────────────┐
│  Frontend  (React + Vite)  │ ──────────────────▶ │  Backend  (Django + DRF)             │
│  localhost:5173            │   proxy /api → 8000 │  localhost:8000                      │
│                            │                     │                                      │
│  pages/      pantallas     │                     │  users       autenticación, perfil   │
│  components/ UI reusable   │                     │  market      instrumentos, precios   │
│  context/    sesión, avisos│                     │  portfolios  operaciones, métricas   │
│  api/        cliente axios │                     │  savings     ahorro, CDT, calculadora│
│  hooks/      polling       │                     │  scenarios   Monte Carlo             │
└────────────────────────────┘                     │  learning    lecciones, glosario     │
                                                   │            │                         │
                                                   │            ▼                         │
                                                   │        SQLite (db.sqlite3)           │
                                                   └──────────────────────────────────────┘
```

Cada app de Django sigue la misma organización por capas:

- `models.py` — entidades y persistencia.
- `services.py` — **lógica de negocio** (reglas de compra/venta, interés compuesto, métricas). Las vistas no contienen reglas de negocio.
- `serializers.py` — validación de entrada y formato de salida.
- `views.py` / `urls.py` — API REST.
- `tests.py` — pruebas automáticas.

Dependencias entre módulos: `portfolios → market`, `scenarios → portfolios + market`, `users → portfolios + savings` (para el patrimonio neto y el ranking). `market` llama a `portfolios.trading` en cada movimiento de precio para ejecutar TP, SL y cierres forzosos. `learning`, `savings`, `social` y `support` son independientes del mercado.

### Modelo de precios

Los precios se generan con un **movimiento browniano geométrico con factor de mercado común**, para que los activos se muevan de forma correlacionada como en la realidad:

```
r = (μ − σ²/2)·dt + β·σ_mercado·√dt·Z_mercado + σ_propia·√dt·Z_propia (+ saltos ocasionales)
```

- La historia (2 años de días hábiles) termina en un precio de referencia cercano al real de cada instrumento.
- El reloj del mercado va a **6× la velocidad real**, así que el precio cambia cada segundo de forma visible.
- Un **reloj de mercado en segundo plano** (un hilo del servidor) es el único proceso que escribe precios: mueve los 66 instrumentos cada segundo en una sola transacción y ejecuta take profit, stop loss y cierres forzosos aunque nadie tenga la plataforma abierta. Las peticiones de los usuarios solo leen. Se desactiva con `AF_MARKET_CLOCK=0`.
- Se guardan velas de 1 minuto de los últimos 3 días para los gráficos intradía, en hora de Colombia.
- Si el servidor estuvo apagado, al encenderlo se completan automáticamente los días y minutos faltantes.
- Las semillas aleatorias son deterministas (símbolo + fecha), por lo que la historia es reproducible.

**Datos reales (opcional):** `python manage.py sync_market --real` intenta descargar la historia real desde Yahoo Finance. Si falla (sin internet o con la API bloqueada), el instrumento conserva sus datos simulados.

---

## 5. API REST

Todas las rutas requieren `Authorization: Bearer <token>` excepto registro y login. Con el backend corriendo puedes explorarlas en el navegador (DRF Browsable API).

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/auth/register/` | Crear cuenta (devuelve tokens) |
| POST | `/api/auth/login/` | Obtener tokens JWT |
| POST | `/api/auth/refresh/` | Renovar token de acceso |
| GET / PATCH | `/api/auth/me/` | Perfil y patrimonio neto |
| POST | `/api/auth/change-password/` | Cambiar contraseña |
| POST | `/api/auth/reset/` | Reiniciar simulación (`{"confirm": "REINICIAR"}`) |
| GET | `/api/market/instruments/?type=&sector=&search=` | Lista con precio, variación y minigráfica |
| GET | `/api/market/quotes/?symbols=AAPL,SPY` | Cotizaciones livianas |
| GET | `/api/market/overview/` | Índice, más suben/bajan, sectores |
| GET | `/api/market/instruments/{símbolo}/` | Detalle y estadísticas |
| GET | `/api/market/instruments/{símbolo}/history/?range=1M\|3M\|6M\|1A\|2A` | Barras OHLCV + promedios móviles |
| GET / POST | `/api/portfolios/` | Listar / crear (`initial_deposit`) |
| GET / PATCH / DELETE | `/api/portfolios/{id}/` | Detalle con métricas / editar / cerrar |
| POST | `/api/portfolios/{id}/trade/` | `{"symbol", "side": "BUY"\|"SELL", "quantity" o "amount"}` |
| POST | `/api/portfolios/{id}/deposit/` · `/withdraw/` | Mover efectivo con la cuenta principal |
| GET | `/api/portfolios/{id}/transactions/` | Historial |
| GET | `/api/portfolios/{id}/performance/?range=1A` | Snapshots + comparación con SPY |
| GET | `/api/dashboard/` | Resumen general, ranking |
| GET | `/api/transactions/` | Todas las operaciones del usuario |
| GET | `/api/savings/products/` | Productos de ahorro y tasas |
| GET / POST | `/api/savings/accounts/` | Listar / abrir cuenta o CDT |
| POST | `/api/savings/accounts/{id}/advance/` | Avanzar días simulados |
| POST | `/api/savings/accounts/{id}/deposit/` · `/withdraw/` | Aportar / redimir |
| POST | `/api/savings/calculator/` | Calculadora de interés compuesto |
| GET | `/api/scenarios/presets/` | Escenarios predefinidos |
| POST | `/api/scenarios/simulate/` | Ejecutar Monte Carlo sobre un portafolio |
| GET | `/api/scenarios/history/` | Simulaciones anteriores |
| GET | `/api/learning/lessons/` · `/lessons/{slug}/` | Lecciones y progreso |
| POST | `/api/learning/lessons/{slug}/quiz/` | Calificar cuestionario |
| GET | `/api/learning/glossary/` | Glosario |
| GET | `/api/market/instruments/{símbolo}/candles/?tf=1m\|5m\|15m\|30m\|1h\|1D\|1S\|1M` | Velas OHLCV por temporalidad |
| GET | `/api/market/instruments/{símbolo}/news/` · `/api/market/news/` | Noticias del activo / del mercado |
| GET | `/api/trading/account/` | Efectivo, margen y posiciones de contado por portafolio |
| GET / POST | `/api/portfolios/{id}/positions/` | Listar / abrir posición CFD (`side`, `leverage`, `margin_amount` o `quantity`, `take_profit`, `stop_loss`) |
| GET | `/api/positions/?status=OPEN\|CLOSED&symbol=` | Posiciones CFD del usuario |
| PATCH | `/api/positions/{id}/` | Cambiar take profit / stop loss |
| POST | `/api/positions/{id}/close/` | Cerrar posición |
| POST | `/api/portfolios/{id}/holdings/{símbolo}/protection/` | TP/SL de una posición de contado |
| POST | `/api/savings/accounts/{id}/renew/` | Renovar un CDT vencido |
| POST · DELETE | `/api/auth/avatar/` | Subir / quitar foto de perfil (multipart, campo `avatar`) |
| GET | `/api/auth/ranking/` | Ranking de inversionistas |
| POST | `/api/auth/accept-terms/` | Aceptar la versión vigente de los términos (`{"accept": true}`) |
| POST | `/api/auth/delete-account/` | Eliminar la cuenta y todos sus datos (`password`, `confirm: "ELIMINAR"`) |
| GET | `/api/social/users/?q=` · `/api/social/friends/` · `/api/social/summary/` | Buscar usuarios, amigos y contadores |
| GET / POST | `/api/social/requests/` · POST `/api/social/requests/{id}/accept\|reject/` | Solicitudes de amistad |
| GET / POST | `/api/social/messages/{usuario}/?after=` | Conversación |
| GET / POST | `/api/support/tickets/` · `/api/support/tickets/{id}/messages/` · `/close/` | Tickets de soporte |
| GET | `/api/support/faq/` | Preguntas frecuentes |

---

## 6. Pruebas

```bash
cd backend
.venv\Scripts\python manage.py test -v 2     # macOS/Linux: .venv/bin/python manage.py test -v 2
```

66 pruebas automáticas (80 % de cobertura en la lógica de negocio, medida con coverage.py) que cubren:

- motor de precios: consistencia OHLC, ancla del precio, avance en vivo;
- autenticación: registro, validaciones, JWT, débitos atómicos sin sobregiro;
- operaciones: comisiones, fondos insuficientes, ventas mayores a lo poseído, aislamiento entre usuarios, cierre de portafolio;
- ahorro: fórmula de interés compuesto, bloqueo de CDT antes del vencimiento, conversión de tasa nominal a E.A.;
- escenarios: una crisis empeora el resultado, percentiles ordenados, el alza de tasas golpea los bonos largos;
- aprendizaje: calificación del cuestionario sin filtrar las respuestas;
- trading con margen: margen y precio ask al abrir, límite de apalancamiento por clase de activo, efecto multiplicador, ganancia en corto, validación de TP/SL, ejecución automática de TP y SL, topes de forex, índices y cripto, conversión a USD en pares como USDJPY, bloqueo de contado en activos solo CFD, cierre forzoso con protección de saldo negativo, stop loss de contado y aislamiento entre usuarios;
- comunidad: no se puede escribir sin amistad; flujo completo de búsqueda, solicitud, aceptación, chat y lectura;
- soporte: ciclo del ticket, respuesta automática, privacidad entre usuarios y aviso de respuesta;
- perfil: confirmación de contraseña, recorte de la foto y rechazo de archivos que no son imágenes;
- privacidad (Ley 1581): registro sin aceptar términos rechazado, aceptación para cuentas anteriores y eliminación de la cuenta con todos sus datos;
- reloj de mercado: candado contra escrituras duplicadas y caché de minigráficas.

---

## 7. Estructura de carpetas

```
aurafarmers-simulador/
├── setup.bat / run.bat          Instalación y ejecución en Windows
├── setup.sh  / run.sh           Instalación y ejecución en macOS/Linux
├── .vscode/                     Tareas, depurador y ajustes de VS Code
├── backend/
│   ├── config/                  settings.py, urls.py, parámetros de la simulación
│   ├── users/                   Perfil, registro, JWT, patrimonio neto, ranking
│   ├── market/                  Instrumentos, motor de precios, estadísticas, comando seed
│   ├── portfolios/              Portafolios, contado, CFD con margen (trading.py), métricas de riesgo
│   ├── savings/                 Cuenta de ahorro, CDT, calculadora
│   ├── scenarios/               Escenarios y simulación Monte Carlo
│   ├── learning/                Lecciones, cuestionarios, glosario
│   ├── social/                  Amistad y chat entre usuarios
│   ├── support/                 Tickets y preguntas frecuentes
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── api/client.js        Axios con JWT y renovación automática
    │   ├── context/             Sesión (AuthContext) y avisos (ToastContext)
    │   ├── components/          Layout, boleta de órdenes, tablas de posiciones, noticias
    │   │   └── chart/           Gráfico interactivo, indicadores y línea de tendencia
    │   ├── pages/               Una pantalla por ruta
    │   └── styles.css           Sistema visual
    ├── package.json
    └── vite.config.js           Proxy /api → Django
```

---

## 8. Parámetros configurables

En `backend/config/settings.py`, diccionario `SIMULATION`:

| Parámetro | Valor | Significado |
|---|---|---|
| `INITIAL_BALANCE` | 100000 | Saldo ficticio inicial (USD) |
| `COMMISSION_RATE` / `MIN_COMMISSION` | 0,1 % / US$ 1 | Comisión por operación |
| `MARKET_SPEED` | 6 | Aceleración del reloj del mercado |
| `MAX_LEVERAGE` | forex 30 · índices 20 · materias primas 10 · cripto 2 | Apalancamiento por clase de activo; cada instrumento puede fijar su tope (`leverage_cap`), y acciones y ETF siempre usan 1:5 |
| `SPREAD` | 0,04–0,06 % | Diferencia entre bid y ask |
| `MARGIN_CALL_LEVEL` / `STOP_OUT_LEVEL` | 100 % / 50 % | Aviso y cierre forzoso por nivel de margen |
| `MARKET_VOLATILITY` | 0,17 | Volatilidad anual del factor de mercado |
| `RISK_FREE_RATE` | 0,04 | Tasa libre de riesgo (Sharpe, efectivo en escenarios) |
| `HISTORY_YEARS` | 2 | Años de historia generada |

Después de cambiar parámetros del mercado: `python manage.py seed --reset-market`.

---

## 9. Rendimiento medido

Prueba de carga con 50 usuarios simultáneos sobre el servidor local (consultan precios cada segundo, abren su portafolio cada 5 s, el resumen cada 15 s y operan cada 20 s):

| Métrica | Resultado |
|---|---|
| Peticiones | 9.400 |
| Errores | 0 |
| Tiempo de respuesta (mediana / percentil 95) | 0,11 s / 1,53 s |
| Integridad tras 3.835 transacciones concurrentes | 0 inconsistencias de efectivo o unidades |

Con un perfil de estrés (50 usuarios comprando y vendiendo cada 1,5 s) la tasa de error fue de 0,5 %, por el límite de un escritor a la vez de SQLite. Para un despliegue con muchos usuarios se recomienda PostgreSQL.

## 10. Seguridad

- Contraseñas con hash PBKDF2 (Django) y validadores de longitud, similitud y contraseñas comunes.
- Autenticación JWT con renovación automática; cada consulta filtra por el usuario autenticado (un recurso ajeno responde 404).
- Límites de peticiones: inicio de sesión 10/min, registro 5/min, cambio de contraseña 5/min, mensajes 40/min, tickets 10/min.
- Transacciones SQLite en modo `IMMEDIATE`: dos peticiones simultáneas no pueden cerrar la misma posición ni acreditar dinero dos veces.
- Fotos de perfil validadas, recortadas y recodificadas como JPEG (se descartan archivos que no son imágenes o «bombas» de descompresión).
- Con `DJANGO_DEBUG=0` el servidor exige `DJANGO_SECRET_KEY` y activa HTTPS, HSTS y cookies seguras.
- Protección de datos (Ley 1581 y Decreto 1377): autorización expresa con fecha y versión (`LEGAL` en `config/settings.py` y `src/legal.js`; si cambia el texto, suban la versión en ambos), política pública y derecho de supresión.
- Dependencias auditadas: `pip-audit -r requirements.txt` y `npm audit` sin vulnerabilidades conocidas (Django REST Framework 3.18).

## 11. Problemas frecuentes

| Síntoma | Solución |
|---|---|
| "No hay conexión con el servidor" en la página | El backend no está corriendo. Revisa la ventana/terminal de Django (puerto 8000). |
| `'python' no se reconoce…` | Reinstala Python marcando *Add to PATH*, o usa `py` en lugar de `python`. |
| `npm` no se reconoce | Instala Node.js LTS y abre una terminal nueva. |
| PowerShell bloquea `activate` | Usa `run.bat`, o ejecuta `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. |
| El puerto 8000 o 5173 está ocupado | Cierra la otra aplicación o cambia el puerto (`runserver 8001` y `target` en `vite.config.js`). |
| No sé la contraseña de `demo` | Está en `backend/credenciales_locales.txt`, o cámbiala con `python manage.py changepassword demo`. |
| «Demasiadas solicitudes» al iniciar sesión | Hay un límite de 10 intentos por minuto contra ataques de fuerza bruta. Espera un minuto. |
| Quiero empezar desde cero | Tarea de VS Code **Reiniciar base de datos**, o borra `backend/db.sqlite3` y ejecuta `migrate` y `seed`. |
| Las fuentes se ven distintas | Sin internet no cargan Fraunces y Public Sans desde Google Fonts; se usan fuentes del sistema. |
| «Noticias no disponibles» | El servidor no tiene internet o las fuentes RSS bloquearon la petición. El resto de la plataforma funciona igual. |
| `npm install` falla por la versión de Node | Instala Node.js 20.19 o superior (`node -v` para revisar). |
| No veo los instrumentos nuevos (forex, cripto…) tras actualizar | Ejecuta de nuevo `setup.bat` (o `migrate` y `seed`): agrega los instrumentos que falten sin borrar tus datos. |
| Mi posición se cerró sola | Revisa el motivo en Historial: take profit, stop loss o cierre forzoso por margen. |

---

## 12. Créditos

Los gráficos del terminal usan [Lightweight Charts™](https://www.tradingview.com/lightweight-charts/) de TradingView (licencia Apache 2.0); el logotipo de atribución que aparece en el gráfico es requisito de esa licencia. Los indicadores, las herramientas de dibujo y toda la lógica de trading son propios del proyecto.

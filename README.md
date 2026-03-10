# Short-Circuit Calculator

Profesionálna webová aplikácia na výpočet skratových pomerov v trojfázových elektrických sieťach podľa normy **IEC 60909-0**.

## Prehľad

- **Výpočtové jadro:** IEC 60909-0 compliant
- **Podporované skraty:** Ik3, Ik2, Ik1 (max/min)
- **Podporované prvky:** Transformátory, autotransformátory, generátory, motory, PSU, vedenia, káble
- **Export:** PDF, XLSX
- **Import:** JSON, XLSX

## Tech Stack

| Vrstva | Technológia |
|--------|-------------|
| Backend | Python 3.11 + FastAPI |
| Engine | pandapower + vlastné rozšírenia |
| Database | SQLAlchemy + SQLite (V1) |
| Auth | JWT + bcrypt |
| Frontend | React + Vite + Tailwind CSS |
| Export | reportlab (PDF), openpyxl (XLSX) |

## Štruktúra projektu

```
short-circuit-calc/
├── backend/
│   ├── app/
│   │   ├── engine/      # IEC 60909 výpočtový modul
│   │   ├── api/         # REST endpointy
│   │   ├── models/      # SQLAlchemy modely
│   │   └── schemas/     # Pydantic schémy
│   ├── tests/
│   └── cli/
├── frontend/
├── specs/
└── docker-compose.yml
```

## Spustenie (Development)

```bash
# Skopírovať environment
cp .env.example .env

# Spustiť v development móde
docker compose -f docker-compose.dev.yml up --build
```

## Spustenie (Production)

```bash
docker compose up --build -d
```

## Vývojové etapy

- **V1a:** Výpočtové jadro + CLI testy (20 acceptance testov)
- **V1b:** API + UI + Reporty

## Licencia

Proprietárny softvér.

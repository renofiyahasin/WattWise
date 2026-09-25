# WattWise ⚡

A professional software-only electricity usage estimation and saving assistant.

## Features
- Dashboard with estimated monthly kWh and cost
- Add/edit-style appliance tracking (delete + re-add)
- Appliance-wise usage analysis
- Personalized saving suggestions
- What-if Saving Simulator
- Monthly saving goal
- Usage history
- User profile and electricity tariff
- SQLite database
- Responsive modern UI

## Important
WattWise does NOT read an actual electricity meter. All estimates are based on user-entered appliance wattage, usage duration, number of days, and tariff.

## Run in VS Code

### 1. Open this folder
Open the `WattWise` folder in VS Code.

### 2. Create virtual environment
Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run
```bash
python app.py
```

### 5. Open
Go to:
`http://127.0.0.1:5000`

The SQLite database is automatically created in `instance/wattwise.db`.

## Calculation
Estimated kWh:
`(Wattage × Hours/day × Days/month) / 1000`

Estimated cost:
`kWh × User-entered tariff`

## Suggested demo data
- Fan — 75 W — 8 hours/day
- LED Light — 12 W — 6 hours/day
- TV — 100 W — 4 hours/day
- Refrigerator — 150 W — 12 hours/day
- AC — 1500 W — 6 hours/day

## Project structure
- `app.py` — Flask backend
- `templates/` — HTML pages
- `static/css/style.css` — UI
- `static/js/` — interactive features
- `instance/wattwise.db` — SQLite database

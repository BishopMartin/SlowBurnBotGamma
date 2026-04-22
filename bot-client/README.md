# SlowBurnBot desktop client (Delta)

Python + Selenium runner that talks to the **Gamma** FastAPI backend (`burnBot_apiClient.py`) instead of Google Sheets.

## Setup

1. From this folder, create a venv and install deps:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Copy `burnBot_config.ini.example` to `burnBot_config.ini` and set `[api] api_url`, Chrome paths, and optional `[api_credentials]`. The real `burnBot_config.ini` is gitignored.

3. Install portable Chrome under `PortableChrome\` (Windows) as in your existing Delta layout, or adjust `chrome_path` / `chrome_user_data_dir_base` in the ini.

4. Run from **this directory** so relative paths resolve:

   ```bash
   python burnBot.py burnBot_config.ini
   ```

`burnBot_runs.json` is written next to the working directory unless you change `RunCounter` usage.

## Source of truth

This tree was merged from **SlowBurnBotDelta** into the Gamma monorepo. Continue editing the client here; treat the old standalone Delta folder as legacy unless you still use it for local Chrome profiles only.

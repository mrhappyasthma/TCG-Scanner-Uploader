# TCG-Scanner-Uploader

## Prerequisites

1. Get an API key for the pokemon API: https://dev.pokemontcg.io/dashboard

2. Get an API key for Gemini: https://aistudio.google.com/u/1/api-keys

3. Copy `config.example.json` to `config.json`.

4. Update `config.json` with the API key values from steps 1 and 2.

## Run

To run (after all prerequisites are done)

This project uses modern Python dependencies and requires a virtual environment to run safely on macOS and Linux.

1. In the project directory, create a virtual environment `python3 -m venv venv`

2. Activate the virtual environment. (you will know this worked if `(venv)` is shown at the start of your terminal).

```
# On macOS and Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

3. `pip install -r requirements.txt`

4. `python gui_scanner.py`

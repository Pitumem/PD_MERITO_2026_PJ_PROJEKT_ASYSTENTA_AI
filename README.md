# Projekt i implementacja asystenta analitycznego AI opartego na kontrolowanych mikroserwisach raportowych 


Projekt aplikacji do analizy danych biznesowych z wykorzystaniem modelu językowego. Aplikacja pozwala użytkownikowi zadawać pytania w języku naturalnym i korzystać z przygotowanych wcześniej raportów.
Model językowy nie generuje SQL i nie ma bezpośredniego dostępu do bazy danych. Wybiera tylko odpowiednią ścieżkę działania i pomaga opisać wynik.

## Funkcje

* chat w języku naturalnym,
* lista dostępnych raportów,
* wybór raportu przez rozmowę,
* analiza danych przez LLM,
* proste narzędzia Python do obliczeń

## Główne komponenty

* **Streamlit** — interfejs użytkownika.
* **Python** — logika aplikacji.
* **Orchestrator** — kontrola przepływu zapytania.
* **MicroserviceManager** — uruchamianie raportów.
* **Supabase/PostgreSQL** — baza danych i konfiguracja.
* **LLM Connector** — komunikacja z modelem językowym.
* **Analytical Tools** — proste obliczenia na danych.

## Przepływ działania

Użytkownik wpisuje wiadomość w aplikacji. Streamlit przekazuje ją do Orchestratora. Orchestrator decyduje, czy odpowiedź może zostać zwrócona od razu, czy trzeba uruchomić raport.

Raporty korzystają z wcześniej przygotowanych zapytań SQL. Dane są potem przekazywane dalej jako:

* **DataFrame** — do aplikacji i narzędzi Python,
* **JSON** — do modelu językowego.

## Konfiguracja

Sekrety nie są zapisane w repozytorium. 

Przykład:

```toml
DATABASE_URL = "your-database-url"
MODEL_URL = "your-model-url"
API_KEY = "your-api-key"
REVIEW_PASSWORD = "your-review-password"
```

## Uruchomienie

Instalacja zależności:

```bash
pip install -r requirements.txt
```

Uruchomienie aplikacji:

```bash
streamlit run app.py
```


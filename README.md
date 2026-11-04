# IT Report Service — LAB2

Uzupełnienie dla Lab 1. Celem serwisu jest obługa zgłoszeń IT z zastosowaniem bazy danych SQL oraz warstwy pamięci podręcznej cache o nazwie Redis, stosującacą mechanizm *cache-aside*.

## Zmiany i decyzje

- **Co zachowano z LAB1:** Model Pydantic, endpointy dla API, logika biznesowa, odpowiedzi HTTP
- **Co zmieniono i dlaczego:** Zaminana tymczasowej bazy RAM w bazę SQLite używaną przez SQLAlchemy, co umożliwia niezależność operacji. Dodanie warstwy pamięci podręcznej Redis w celu przyspieszenia odczytu zasobów.
- **Właściciel danych oraz granice drugiej usługi:** Report Service jest odpowiedzialny za zgłaszanie awarii, a walidacja departamentów odbywa się poprzez powiązanie z Department Service
- **Model tabel, klucze, powiązania i ograniczenia:** Tabela `reports` zawierająca klucz główny `id` z opcją autoinkrementacji, pola tekstowe oraz ograniczeniem `unique=True` na kolumnie `description` w celu zapewnieniau unikalności opisu.
- **Zachowana reguła biznesowa, operacja dozwolona i odrzucona:** 
    - Nowe zgłoszenie otrzymuje automatycznie status `unsolved`. 
    - Próba dodania zgłoszenia z istniejącym opisem skutkuje  odrzuceniem operacji z kodem `409 Conflict` bez modyfikacji stanu bazy.
- **Odczyt objęty cache, uzasadnienie, dopuszczalna nieaktualność:** 
    - Odczyt szczegółów zgłoszenia dla `GET /reports/{id}`. 
    - Uzasadnienie: czestę wykonywanie operacji odczytu pojedynczego zasobu, a dopuszczalna nieaktualność danych jest ograniczona czasem TTL.
- **Prefiks, klucz, TTL, unieważnianie po zapisie:** 
    - **Prefiks**: `$env:CACHE_PREFIX`: `lab2:131534:report`
    - **Klucz**: `{prefiks}:report:{id}`
    - **TTL**: domyślnie `60` sekund
    - **Unieważnienie**: operacja modyfikacji lub usunięcia zasobu powoduje usunięcie klucza z Redis.

## Uruchomienie

Python minimum 3.12+, PowerShell, Docker

Do uruchomienia w tym katalogu:


```powershell
#Konfiguracja środowiska
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q


# Uruchomienie API
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8101

#Określenie parametrów środowiska
$env:DATABASE_URL = 'sqlite:///./app.db'
$env:CACHE_PREFIX = 'lab2:131534:report' 
$env:CACHE_TTL_SECONDS = '60'

#Uruchomienie Redis
docker run --name lab2-redis -p 127.0.0.1:6379:6379 -d redis:7-alpine
$env:REDIS_URL = 'redis://localhost:6379/0'
```

## Dowody

| Scenariusz | Stan początkowy i żądanie | Oczekiwany wynik | Wynik rzeczywisty | Reset |
|---|---|---|---|---|
| Zapis i odczyt po restarcie bez cache | Dodanie zgłoszenia, restart aplikacji bez cache | Poprawny odczyt danych z SQL | Zgodny | Automatyczny |
| Reguła: sukces i odrzucenie bez zmiany | Baza z istniejącym wpisem, próba ponownego dodania identycznego wpisu | Status 409 Conflict, brak zmiany w bazie danych | Zgodny | Automatyczny |
| MISS → HIT, liczba odczytów bazy | GET /reports/1 i następny GET | Pierwszy: MISS, drugi: HIT | Zgodny | Automatyczny |
| Wygaśnięcie TTL | Próba odczytu po upływie określonego czasu TTL | Ponowne pobranie danych z bazy - MISS | Zgodny | Automatyczny |
| Zmiana i unieważnienie | Usunięcie lub edycja zasobu i ponowne użycie GET | Usunięcie cache, następnę żądanie zwraca MISS | Zgodny | Automatyczny |
| Awaria GET, SET, DELETE cache | Odłączenie Redis | Przejście w tryb bypass, wykonanie operacji w bazie działa prawidłowo | Zgodny | Automatyczny |
| Przywrócenie Redis, możliwa stara wartość | Powrót połączenia | Powrót buforowania | Zgodny | Automatyczny |

Testy z LAB1:
- **Test Health**: Sprawdza poprawność działania endpointu /health i zwracany status usługi.   
- **Test listy i szczegółów**: Weryfikuje poprawność pobierania listy zgłoszeń oraz szczegółów konkretnego zasobu.   
- **Test zapisu i odczytu**: Testuje poprawne utworzenie nowego zgłoszenia (POST /reports) i jego odczyt.   
- **Test braku zasobu**: Sprawdza zwrócenie kodu 404 Not Found dla nieistniejącego identyfikatora.   
- **Test usunięcia zasobu**: Weryfikuje usunięcie zgłoszenia kończące się kodem 204 No Content.   
- **Test błędnych danych**: Sprawdza obsługę błędów walidacji danych wejściowych biblioteki Pydantic (422 Unprocessable Entity).   
- **Test konfliktu**: Weryfikuje zwrócenie kodu 409 Conflict przy próbie utworzenia zgłoszenia z duplikatem opisu.   
- **Test reguły biznesowej**: Sprawdza zachowanie dozwolonych i niedozwolonych operacji bez zmiany stanu bazy.   
- **Test restartu**: Sprawdza zachowanie systemu po restarcie procesu i wyczyszczeniu stanu pamięci.   

Testy z LAB2 z użyciem zamiennika:
- **Test perspektywy nowej instancji silnika (test_persists_with_new_engine)**: Sprawdza trwałość danych i poprawność odczytu przy użyciu nowej sesji bazy danych.   
- **Test wycofania duplikatu (test_duplicate_rolls_back)**: Weryfikuje, że próba dodania zduplikowanego zgłoszenia wywołuje błąd i wycofuje transakcję, zachowując spójność bazy.   
- **Test cyklu MISS → HIT i inwalidacji (test_miss_hit_and_invalidation)**: Sprawdza poprawne przejście cache ze stanu MISS do HIT oraz inwalidację (usuwanie) klucza po usunięciu zasobu.   
- **Test odporności na błąd zapisu (test_failed_cache_set_still_returns_database_value)**: Weryfikuje, że błąd podczas zapisu do cache nie przerywa działania aplikacji i poprawnie zwraca wartość bezpośrednio z bazy danych. 

Ręczne próby z rzeczywistym Redis:
- **Test polecenia PING**: Weryfikacja poprawnego połączenia z prawdziwym serwerem Redis.   
- **Weryfikacja MISS → HIT oraz TTL**: Sprawdzenie przejścia ze stanu MISS do HIT przy ponownym odczycie oraz kontrola czasu życia (TTL) utworzonego klucza.   
- **Odczyt po wygaśnięciu TTL**: Obserwacja zachowania systemu i odświeżenia danych po upływie zdefiniowanego czasu TTL.   
- **Odłączenie klienta (Tryb BYPASS)**: Zmiana adresu REDIS_URL na nieużywany port w celu symulacji awarii i sprawdzenia, czy operacje przechodzą w tryb BYPASS.   
- **Operacja modyfikacji przy awarii**: Sprawdzenie zachowania systemu i stanu bazy podczas próby edycji danych w warunkach niedostępności cache.   
- **Przywrócenie konfiguracji Redis**: Przywrócenie poprawnego adresu serwera, weryfikacja wystąpienia starej wartości (przed wygaśnięciem TTL) oraz przejścia na aktualną wartość z bazy po upływie TTL.   

## Porównanie i ograniczenia

- **Nieudane unieważnienie**: Jeśli podczas modyfikacji lub usunięcia zasobu w bazie danych wystąpi problem z połączeniem z Redisem, Usunięcia klucza z cache może się nie udać. W pamięci cache pozostanie stara wartość, która będzie zwracana klientom aż do momentu wygaśnięcia TTL.   
- **Współbieżność**: Prosty cache-aside nie rozwiązuje problemu współbieżności i nie gwarantuje spójności danych w przypadku wykonywania wielu operacji zapisu i odczytu w  przez różne wątki lub procesy w tym samym czasie.   
- **Zmiany schematu**: Baza danych SQLite jest tworzona automatycznie przy użyciu metody create_all, przez cokażda modyfikacja struktury tabel zgłoszeń wymaga migracji schematu lub ręcznego odtworzenia bazy, ponieważ tabele nie są aktualizowane z tą metodą.
- **Zastosowanie cache jest uzasadnione dla usługi obsługującej zgłoszenia IT, ponieważ operacje odczytu szczegółów zgłoszeń są częste, a chwilowa nieaktualność danych nie wpływa negatywnie na proces biznesowy, dzięki czemu odciąża bazę danych i skraca czas odpowiedzi od API.

## Dokumentacja i autorzy

| Źródło | Problem | Zastosowanie | Weryfikacja |
|---|---|---|---|
|https://fastapi.tiangolo.com/ |Walidacja danych wejściowych JSON,obsługa niestandardowych kodów błędów| Modele Pydantic oraz HTTPException z odpowiednimi statusami HTTP|Wykonanie automatycznych testów dla kodów 404, 409 i 422|
| https://docs.sqlalchemy.org/ | Konfiguracja relacyjnej bazy danych, fabryki sesji, mapowanie ORM | Zaimplementowanie make_database, Base i modelu ReportRow | Testy integracyjne oraz izolacja bazy w katalogu tymczasowym |


- Wkład każdej osoby: Bartosz Winczowski - implementacja struktury modularnego monolitu, SQL, cache, testów integracyjnych i dokumentacji.
- AI: Gemini, pomoc przy projektowaniu struktury aplikacji, rozwiązywaniu problemów z izolacją testów w pytest oraz weryfikacji błędów. Weryfikacja: kod oraz testy zostały uruchomione i zweryfikowane lokalnie.   
- Kolejny etap pierwszej i planowanej drugiej usługi: Izolacja Department Service jako niezależnej mikrousługi komunikującej się przez HTTP.

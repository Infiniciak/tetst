# Report Service - LAB3

Projekt tworzy architekturę opartą na dwóch mikrousługach zintegrowanych z **Eureka Server**, wykorzystujących bazę danych SQLite i pamięć cache Redis z LAB2.

## Wymagania

- Docker Desktop z `docker compose` albo JDK 21 i Maven do lokalnego uruchomienia serwera,
- Python 3.12 lub nowszy,
- wolne porty `8761` (Eureka Server), `8101` (Report Service) i `8102` (Department Service).

## Uruchomienie rejestru Eureka

W katalogu pakietu należy uruchomić:

```powershell
docker compose up --build -d eureka
```

Panel znajduje się pod adresem `http://localhost:8761/`. 

## Uruchomienie dwóch usług

Środowisko Python należy utworzyć, a zależności zainstalować z katalogu pakietu:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Pierwszy terminal (Report Service)**

```powershell
$env:EUREKA_SERVER_URL = 'http://127.0.0.1:8761'
$env:SERVICE_NAME = 'REPORT-SERVICE'
$env:SERVICE_PORT = '8101'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8101
```

**Drugi terminal (Department Service)**

```powershell
$env:EUREKA_SERVER_URL = 'http://127.0.0.1:8761'
$env:SERVICE_NAME = 'DEPARTMENT-SERVICE'
$env:SERVICE_PORT = '8102'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8102
```

Po pojawieniu się obu wpisów `UP` w panelu należy wykonać:

```powershell
Invoke-RestMethod http://127.0.0.1:8102/reports/1/department-info
```

Oba terminale należy otworzyć w katalogu pakietu. Należy wcześniej zatrzymać własne aplikacje zajmujące porty `8101` i `8102`. Zmienne trzeba ustawić osobno dla każdego procesu; na czas eksperymentu należy pracować bez `--reload`.

`REPORT-SERVICE` wybiera adres `DEPARTMENT-SERVICE` z lokalnej, okresowo odświeżanej kopii rejestru i wywołuje `GET /departments/1`. Oczekiwana odpowiedź ma status `200` oraz odpowiednie dane departamentu. Eureka nie przekazuje danych biznesowych usług.

Kod HTTP `404` dla `GET /departments/UNKNOWN` oznacza brak departamentu. Inny błąd HTTP zależności jest mapowany na `502`, a brak połączenia lub timeout na `503`. Limit pojedynczego wywołania HTTP wynosi 3 sekundy. Przy kilku instancjach nie jest to limit czasu całego przepływu.

Należy sprawdzić odpowiedzi przez `curl.exe -i http://127.0.0.1:8101/reports/1/department-info` albo dokumentację `/docs`. Po zatrzymaniu `DEPARTMENT-SERVICE` żądanie znanego paczkomatu powinno dać `503`, a `http://127.0.0.1:8102/health` lub `http://127.0.0.1:8102/reports/health` nadal `200`. Po przywróceniu zależności i odświeżeniu rejestru klienta należy ponownie oczekiwać `200` z danymi. Wpis `UP` nie gwarantuje dostępności procesu; aktualizacja rejestru i jego lokalnej kopii nie jest natychmiastowa.

## Testy jednostkowe

Testy nie wymagają działającego serwera Eureka:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Testy sprawdzają wywołanie po nazwie, przekazanie limitu czasu, zachowanie kontraktu danych, cykl życia klienta oraz odpowiedzi `404`, `502` i `503`. Atrapa nie potwierdza rzeczywistej rejestracji; należy osobno wykonać scenariusze ręczne z instrukcji głównej.

## Zatrzymanie

Oba procesy Uvicorna należy zatrzymać skrótem `Ctrl+C`. Serwer Eureka należy zatrzymać w zależności od wybranej metody:

```powershell
docker compose down
```

Jeśli Eureka działa przez Maven, proces należy zakończyć skrótem `Ctrl+C` w terminalu, w którym uruchomiono `mvn spring-boot:run`.

Adresy i porty można zmieniać przez zmienne środowiskowe, ale port klienta rejestrowany w Eurece musi odpowiadać portowi Uvicorna. `SERVICE_PORT` w przykładzie jest używany przez klienta rejestru; parametr `--port` uruchamia serwer HTTP.

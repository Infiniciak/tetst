## Etap LAB4 — konfiguracja bramki API (API Gateway)

### Autorzy i ciągłość projektu z LAB1–LAB3

- Autorzy i indywidualny wkład każdej osoby w parze:
- Temat projektu oraz zachowane komponenty z LAB1–LAB3 (pierwsza usługa z bazą SQLite i cache Redis, druga usługa, Eureka Server):
    - **REPORT-SERVICE (:8101):** Pierwsza usługa obsługująca bazy SQLite, cache Redis i walidację Pydantic.
    - **DEPARTMENT-SERVICE (:8102):** Druga usługa komunikująca się z pierwszą usługą przez odnajdywanie po nazwie w Eurece.
    - **Eureka Server (:8761):** Odpowiada za Service Discovery, dzięki czemu usługi mogą odnajdywać się nawzajem.
- Dodane i zmodyfikowane pliki w repozytorium:
    - **gateway/application.yml**
    - **tests/test_gateway_integration.py**

### API udostępniane przez bramkę i podział odpowiedzialności

| Metoda i ścieżka klienta (`:8080`) | Identyfikator trasy (`id`) | Usługa docelowa w Eurece (`uri`) | Ścieżka wewnętrzna po `StripPrefix` | Właściciel danych i uzasadnienie udostępnienia |
|---|---|---|---|---|
| GET /api/reports, POST /api/reports, GET /api/reports/{id} | reports | lb://REPORT-SERVICE | /reports, /reports/{id} | REPORT-SERVICE (zarządzanie zgłoszeniami, bazą danych i  cache). Udostępnione dla końcowego klienta. |
| GET /api/departments, GET /api/departments/{id} | departments | lb://DEPARTMENT-SERVICE | /departments, /departments/{id} | DEPARTMENT-SERVICE (odczyt departamentów i integracja ze zgłoszeniami). Udostępnione dla końcowego klienta. |

- Endpointy pozostawione wyłącznie wewnątrz usług (nieudostępnione w bramce) wraz z uzasadnieniem:
    - Techniczne endpointy /health, /docs oraz /openapi.json poszczególnych usług nie posiadają tras w bramce, aby nie ujawniać wewnętrznej struktury technicznej. Interaktywna dokumentacja dostępna jest bezpośrednio na portach usług (8101, 8102)
- Podział odpowiedzialności pomiędzy API Gateway, Eureka Server oraz dwie usługi domenowe (właściciele danych, cache i reguły biznesowej):
    - **API Gateway: Przyjmowanie żądań klienta, trasowanie przez lb://, usuwanie prefiksu , dodawanie nagłówkaX-Gateway: lab4. Brak bazy danych i logiki biznesowej.
    - **Eureka Server: Przechowywanie rejestru aktywnych instancji.
    - **Mikrousługi: Właściciele baz danych , cache (Redis) oraz reguł biznesowych i walidacji.
- Uzasadnienie limitów `connect-timeout` i `response-timeout` względem limitu wywołania usługa–usługa z LAB3:
    - **Limity w bramce (connect-timeout: 1000ms, response-timeout: 5s) są dłuższe niż limit wywołania usługa–usługa (timeout=3s w DEPARTMENT-SERVICE -> REPORT-SERVICE), co pozwala usłudze zależnej obsłużyć błąd i zwrócić kontrolowany status 503 zanim bramka przerwie połączenie.
- Diagram przepływu żądania przez bramkę, odnajdywania w Eurece, komunikacji między usługami oraz dostępu do SQLite i Redis:
    Klient HTTP -> API Gateway (:8080) --[lb://REPORT-SERVICE]--> REPORT-SERVICE (:8101) <-> SQLite / Redis
                                  --[lb://DEPARTMENT-SERVICE]--> DEPARTMENT-SERVICE (:8102) --[HTTP]--> REPORT-SERVICE (:8101)

### Uruchomienie, weryfikacja i zatrzymanie środowiska

- Wersje narzędzi (Python, JDK, Apache Maven, użyte biblioteki):
    - **Python 3.12**
    - **JDK 21**
    - **Apache Maven**
    - **FastAPI**
    - **Spring Cloud Gateway**
- Zestaw wymaganych procesów, ich katalogi robocze, porty oraz zmienne środowiskowe:
    - **Redis** (localhost:6379)
    - **Eureka Server** (localhost:8761)
    - **REPORT-SERVICE** (localhost:8101)
    - **DEPARTMENT-SERVICE** (localhost:8102)
    - **API Gateway** (localhost:8080)
- Polecenia uruchomienia procesów we właściwej kolejności:
1. Eureka Server oraz Redis:
docker compose up -d
2. REPORT-SERVICE:

$env:EUREKA_SERVER_URL = 'http://127.0.0.1:8761'
$env:SERVICE_NAME = 'REPORT-SERVICE'
$env:SERVICE_PORT = '8101'
$env:PYTHONPATH = "."
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8101


3. DEPARTMENT-SERVICE:

$env:EUREKA_SERVER_URL = 'http://127.0.0.1:8761'
$env:SERVICE_NAME = 'DEPARTMENT-SERVICE'
$env:SERVICE_PORT = '8102'
$env:PYTHONPATH = "."
.\.venv\Scripts\python.exe -m uvicorn department.app.main:app --port 8102


4. API Gateway (Terminal 3):

Set-Location .\gateway
mvn spring-boot:run

- Sposób przygotowania danych testowych bez kasowania bazy danych projektu:
- Polecenie uruchomienia dotychczasowych testów jednostkowych (LAB1–LAB3):
 $env:PYTHONPATH = "."
.\.venv\Scripts\python.exe -m pytest -q

- Polecenie uruchomienia testów integracyjnych przechodzących przez bramkę (LAB4):
$env:PYTHONPATH = "."
.\.venv\Scripts\python.exe -m pytest tests/integration/test_gateway_integration.py -q
- Polecenia poprawnego zatrzymania procesów:
 - **Maven, Unicorn**: skrót Ctrl + C
 - **Eureka, Redis**: docker compose down

### Wyniki weryfikacji i eksperymentów awarii

| Scenariusz | Żądanie i stan procesów | Oczekiwany wynik | Rzeczywisty status, treść i nagłówki (`X-Gateway`, `X-Cache`) | Wniosek techniczny |
|---|---|---|---|---|
| Odczyt z pierwszej usługi przez bramkę (MISS → HIT) | GET /api/reports/1 | Status 200 OK, nagłówki bramki i cache | 200 OK, X-Gateway: lab4, X-Cache: MISS (pierwsze wywołanie) / HIT (drugie wywołanie) | Trasa w bramce przekazuje nagłówki diagnostyczne wygenerowane przez warstwę cache usługi. |
| Zapis przez bramkę, unieważnienie cache i ponowny odczyt | POST /api/reports -> GET /api/reports/{id} | Status 201/200, zmiana widoczna, cache unieważniony | 201 Created / 200 OK, X-Gateway: lab4, kolejny GET daje X-Cache: MISS | Operacje modyfikujące przechodzące przez bramkę trwale zapisują dane w bazy SQLite i unieważniają wpisy w Redis. |
| Błąd walidacji (`422`) i reguły biznesowej (`409`) przez bramkę | POST /api/reports z błędnym JSON | Status 422 lub 409 z opisem szczegółów | 422 Unprocessable Entity, X-Gateway: lab4, body: {"detail": [...]} | Bramka bez zmian przekazuje kody błędów walidacji oraz strukturę odpowiedzi wygenerowaną przez FastAPI |
| Odczyt z drugiej usługi przez bramkę (przepływ z LAB3) | GET /api/departments/1 | Status 200 OK i powiązane dane | 200 OK, X-Gateway: lab4, poprawne dane połączenia usług | Wywołanie klienta przez bramkę uruchamia wewnętrzny mechanizm odnajdywania i komunikacji między usługami. |
| Brak zasobu (`404` z usługi) vs brak trasy (`404` z bramki) | GET /api/reports/UNKNOWN vs GET /not-a-route | Oba status 404, ale różne źródła i nagłówki | Odpowiedź z usługi: 404, X-Gateway: lab4. Brak trasy: 404, brak nagłówka X-Gateway | Nagłówek X-Gateway: lab4 pozwala jednoznacznie odróżnić błąd braku zasobu w rocie od braku trasy w bramce. |
| Zatrzymana druga usługa (wywołująca) | GET /api/departments/1 przy zgaszonym DEPARTMENT-SERVICE | Błąd połączenia / braku instancji w bramce | 503 Service Unavailable lub 500, brak reakcji na /api/departments | Wyłączenie usługi uniemożliwia realizację jej tras, pierwsza usługa (/api/reports) działa dalej. |
| Zatrzymana pierwsza usługa (zależność z LAB3) | GET /api/departments/1 przy zgaszonym REPORT-SERVICE | Błąd zależności przekazany przez drugą usługę | 503 Service Unavailable wygenerowany przez DEPARTMENT-SERVICE, X-Gateway: lab4 | Awaria usługi bazowej jest obsługiwana i mapowana na 503 przez usługę wywołującą zgodnie z logiką z LAB3. |
| Ponowne uruchomienie zatrzymanej usługi i odświeżenie rejestru | Uruchomienie usuniętej usługi i ponowne żądanie | Powrót odpowiedzi 200 OK bez restartu bramki | 200 OK po odczekaniu ok. 10–30 sekund na odświeżenie rejestru Eureki | Bramka automatycznie wykrywa powrót instancji dzięki okresowemu odświeżaniu lokalnej kopii rejestru. |
| Zatrzymany proces `API Gateway` | Żądanie na port 8080 | Brak odpowiedzi HTTP (odmowa połączenia) | Connection refused (ERR_CONNECTION_REFUSED) na porcie 8080 | Bramka jest pojedynczym punktem wejścia; jej zatrzymanie blokuje ruch zewnętrzny mimo działania samych usług (8101, 8102). |

- Wykaz co najmniej czterech własnych testów integracyjnych (nazwy funkcji testowych i sprawdzane asercje):
    - test_gateway_process_health: sprawdzanie zdrowia bramki (GET /health).
    - test_report_route_and_header: sprawdzenie routingu do REPORT-SERVICE i obecności nagłówka diagnostycznego.
    - test_department_route_calls_dependency: sprawdzenie routingu do DEPARTMENT-SERVICE i przepływu usługa-usługa.
    - test_domain_404_is_forwarded: weryfikacja przekazywania błędu 404 z nagłówkiem diagnostycznym.
    - test_unknown_route_is_not_forwarded: weryfikacja braku nagłówka diagnostycznego przy braku dopasowanej trasy
- Zaobserwowane opóźnienia aktualizacji rejestru oraz ograniczenia zastosowanego rozwiązania:

### Wykorzystana dokumentacja techniczna (EK_03) i użycie AI

| Źródło oficjalnej dokumentacji i wersja | Rozwiązywany problem | Zastosowana konfiguracja lub rozwiązanie | Sposób weryfikacji działania |
|---|---|---|---|
| Spring Cloud Gateway Reference Documentation (v4.x) | Konfiguracja filtrów modyfikujących ścieżki i nagłówki odpowiedzi. | Zastosowanie filtrów StripPrefix=1 oraz AddResponseHeader=X-Gateway, lab4 w pliku application.yml. | Weryfikacja nagłówka X-Gateway w odpowiedziach oraz sprawdzenie logów Uvicorn (otrzymana ścieżka). |
| Spring Cloud Netflix Eureka Client Documentation | Pobieranie rejestru instancji bez rejestrowania bramki jako osobnej usługi. | Ustawienie eureka.client.fetch-registry: true oraz register-with-eureka: false. | Weryfikacja braku wpisu bramki w panelu Eureki (:8761) oraz poprawne rozwiązywanie prefiksów lb://. |

- Zakres wykorzystania narzędzi AI oraz sposób samodzielnej weryfikacji wygenerowanych fragmentów (albo „nie korzystano”):
Wykorzystanie AI do przerobienia struktury pliku application.yml, szablonu testów integracyjnych oraz ustrukturyzowania dokumentacji. Kod został zweryfikowany przez wykonanie zestawu testów integracyjnych pytest i testów manualnych przez curl.

# Virtual Clinic Auth

init-db na razie ustawiony jako reset bazy danych - odpalic tylko raz; bo przy istniejacej bazie usuwa!

## Technologie
- Python
- Flask
- Jinja2 - renderowanie szablonow HTML
- SQLite przez `sqlite3`
- `hashlib.pbkdf2_hmac` do hashowania hasel
- `hmac.compare_digest` do porownywania hashy
- `secrets` do generowania soli i tokenow
- Bootstrap przez CDN

## Dokumentacja
linki do dokumentacji w `REFERENCES.md`

## Ocena ryzyka
znajduje sie w pliku `OCENA_RYZYKA.md`

## Dodatkowe pliki
`NOTES.md` - krotki opis i decyzje implementacji

## Aktualny stan
- Rejestracja i logowanie uzytkownika dzialaja na formularzach Flask/Jinja
- Hasla sa hashowane przez `PBKDF2-HMAC` z osobna sola dla kazdego uzytkownika
- Sesje sa przechowywane w bazie SQLite, a cookie trzyma tylko `session_token`
- Obslugiwane role: `PATIENT`, `DOCTOR`, `STAFF`
- Panele i nawigacja sa ograniczone zgodnie z rola uzytkownika
- `/dashboard` przekierowuje do panelu zgodnego z rola
- Formularze `POST` sa chronione tokenem CSRF, a `/logout` przyjmuje tylko `POST`
- Logowanie ma ograniczenie nieudanych prob per `IP + email`
- Możliwość dodawania notatek, aby zaprezentować różnice między rolami

## Struktura
- `run.py` - punkt startowy 
- `app/__init__.py` - tworzenie i konfiguracja app
- `app/db.py` - polaczenie z SQLite i `init-db`
- `app/auth.py` - logika rejestracji, logowania, sesji i operacje na bazie danych
- `app/security.py` - CSRF, ograniczenie prob logowania i pomocnicze zabezpieczenia
- `app/routes.py` - route'ingi do odpowiednich HTML'ow
- `app/schema.sql` - definicje tabel SQLite
- `templates/` - szablony HTML

## Uruchomienie
srodowisko:
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```
zaleznosci:
```powershell
python -m pip install -r requirements.txt
```
Wymagana konfiguracja `SECRET_KEY`:
```powershell
$env:SECRET_KEY="your-secret-key"
```
Opcjonalna konfiguracja dla lokalnego HTTP:
```powershell
$env:COOKIE_SECURE="0"
```
Opcjonalne wlaczenie debug:
```powershell
$env:FLASK_DEBUG="1"
```
Tworzenie tabeli w bazie (tylko raz - 1'sze odpalenie):
```powershell
python -m flask --app run init-db
```
Uruchom:
```powershell
python run.py
```
Dostep pod adresem:
```text
http://127.0.0.1:5000
```

## Aktualny route'ing
- `/` - przekierowanie do `/login`
- `/login` i `/register` - formularze logowania i rejestracji
- `/logout` - `POST`, usuniecie sesji i cookie
- `/dashboard` - przekierowanie do panelu zgodnego z rola
- `/patient`, `/doctor`, `/staff` - panele ograniczone do odpowiednich rol
- `/profile` - profil użytkownika
- `/delete_account` - `POST`, usunięcie konta
- `/add_note/<int:patient_id>` - `GET, POST`, dodanie notatki do pacjenta o <id> (ograniczone do roli doktora)
- `/delete_note/<int:note_id>` - `POST`, usunięcie notatki o <id> (ograniczone do roli doktora)
- `/add_personel/<int:patient_id>` - przekierowuje do listy użytkowników (staff i doktorzy) do dodania dostępu do notatki (ograniczone do roli doktora)
- `/add_personel/<int:patient_id>/<int:user_id>` - `POST`, dodanie użytkownika o <id> do notatki (ograniczone do roli doktora)



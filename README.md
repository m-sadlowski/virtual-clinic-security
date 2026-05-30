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

## Dodatkowe pliki
`NOTES.md` - krotki opis i decyzje implementacji

## Aktualny stan
- Rejestracja uzytkownika obslugiwana przez formularz w `/register`
- Obslugiwane role: `PATIENT`, `DOCTOR`, `STAFF`
- Haslo jest zapisywane jako hash PBKDF2-HMAC z osobna sola dla kazdego uzytkownika
- Dane uzytkownika sa zapisywane w tabeli `users`
- Logowanie obsluguje formularz w `/login`
- Logowanie sprawdza email i haslo
- Komunikaty bledu i sukcesu sa pokazywane przez `flash`

## Struktura
- `run.py` - punkt startowy 
- `app/__init__.py` - tworzenie i konfiguracja app
- `app/db.py` - polaczenie z SQLite i `init-db`
- `app/auth.py` - logika rejestracji, logowania i sesji
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
- `/login` - formularz i obsluga logowania
- `/register` - formularz i zapis rejestracji uzytkownika
- `/dashboard` - panel glowny
- `/patient` - panel pacjenta
- `/doctor` - panel lekarza
- `/staff` - panel staffu

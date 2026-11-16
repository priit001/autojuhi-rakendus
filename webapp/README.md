# Autojuhi rakendus

Flaski ja SQLite'i rakendus sõitude lisamiseks, vaatamiseks, statistika kuvamiseks ning CSV importimiseks ja eksportimiseks. Rakendus võimaldab luua ja kontrollida SQLite'i varukoopiaid.

## Tavakasutus

Käivita rakendus `webapp` kaustast:

```powershell
python app.py
```

Ava rakendus kohalikus arvutis aadressil http://127.0.0.1:5000. Tavakäivitus kasutab ainult `127.0.0.1` aadressi ja Flaski debug-režiim on välja lülitatud. `main.py` jääb samale käivitusfunktsioonile suunavaks ühilduvaks käivitajaks; tavaliseks kasutuseks kasuta `app.py`.

**Turvahoiatus:** praegusel versioonil puudub autentimine. Ära muuda host-aadressi ega ava rakendust LAN-i või interneti kaudu enne autentimise lisamist ja eraldi turvakontrolli.

## Testid

Käivita `webapp` kaustast:

```powershell
python -m unittest discover -s tests -p "test_app.py" -v
```

Testid kasutavad ajutisi andmebaase ja varunduskaustu.

## Andmefailid

- SQLite'i andmebaas: `webapp/users.db`
- SQLite'i varukoopiad: `webapp/backups/`; kaust luuakse esimese varundamise ajal.
- CSV ekspordid: `webapp/exports/`

Andmebaasi, varukoopiaid ja ekspordifaile ei lisata Git-i. Hoia varukoopiat eraldi turvalises asukohas; samas arvutis olev varukoopia ei kaitse ketta rikke ega arvuti kadumise eest.

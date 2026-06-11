# gedcom

Repository for the GEDCOM project.

## Arbeitsdokumentation

Öffne bei jeder neuen Arbeitssitzung die Datei `ARBEITSDOKUMENTATION.md` im Projektverzeichnis.
Diese Datei enthält den aktuellen Stand, die Vereinbarungen und die nächsten Aufgaben.

## Session-Skript

Nutze das PowerShell-Skript `session.ps1`, um die Sitzungen automatisch zu dokumentieren und Git zu synchronisieren.

- Zum Beenden des Tages:
  `.\session.ps1 -Phrase "fertig für heute"`
- Zum Starten eines Arbeitstags:
  `.\session.ps1 -Phrase "weiter gehts heute"`

Das Skript:
- dokumentiert den Eintrag in `ARBEITSDOKUMENTATION.md`
- führt bei `fertig für heute` ein `git commit` + `git push` aus
- führt bei `weiter gehts heute` ein `git pull` aus

# Arbeitsdokumentation

Diese Datei dokumentiert alle Vereinbarungen, Befunde und den aktuellen Stand der Arbeit am Projekt.
Sie wird bei jedem neuen Arbeitstag geöffnet und fortgeführt.

## Zweck

- Festhalten, was wir besprochen und vereinbart haben
- Beschreiben, welche Änderungen als nächstes geplant sind
- Sicherstellen, dass bei einem Rechnerwechsel der letzte Stand klar ist

## Vorgehen

1. Öffne diese Datei am Beginn jeder neuen Arbeitssitzung.
2. Lies den letzten Eintrag, um den aktuellen Stand zu verstehen.
3. Füge neue Abschnitte hinzu, sobald du etwas Wesentliches erledigt oder beschlossen hast.
4. Wenn du fertig für heute bist, schreibe einen Abschluss-Eintrag mit dem Hinweis `fertig für heute`.
5. Push die Änderungen ins Repository, damit du auf einem anderen Rechner mit `git pull` weiterarbeiten kannst.

## Format für Sitzungs-Einträge

Nutze ein klares Format pro Sitzung, z.B.:  

- Datum: YYYY-MM-DD
- Status: In Arbeit / Fertig für heute
- Was gemacht wurde:
  - ...
- Nächste Schritte:
  - ...
- Bemerkung:
  - ...

## Beispiel

- Datum: 2026-06-11
- Status: In Arbeit
- Was gemacht wurde:
  - Repository-Struktur geprüft
  - README und Dokumentationsablage geplant
- Nächste Schritte:
  - `ARBEITSDOKUMENTATION.md` anlegen
  - README mit Verweis aktualisieren
- Bemerkung:
  - Bei "fertig für heute" das Datum und den Stand hier eintragen.

## Kontrollfragen beim Start

- Was war der letzte Eintrag?
- Welche Aufgaben sind noch offen?
- Welche Dateien sind zuletzt bearbeitet worden?

## Start einer neuen Sitzung

Wenn du auf einem anderen Rechner weiterarbeitest:

1. `git pull` ausführen
2. `gedcom/ARBEITSDOKUMENTATION.md` öffnen
3. Letzten Eintrag lesen
4. Weiterarbeiten und neue Einträge ergänzen

---

## Aktueller Stand

- Datum: 2026-06-11
- Status: Erste Einrichtung der Dokumentation
- Was gemacht wurde:
  - Dokumentationsdatei angelegt
  - Prozess zum Weiterarbeiten auf mehreren Rechnern beschrieben
- Nächste Schritte:
  - Weitere Projektdateien prüfen
  - Inhalte der Arbeitsdokumentation bei jeder Sitzung fortführen
- Datum: 2026-06-11 10:30:01
- Status: Fertig für heute
- Was gemacht wurde:
Arbeitsende dokumentiert. Änderungen werden gepusht.
- Nächste Schritte:
  - ...
- Bemerkung:
  - Automatisch protokolliert durch session.ps1

- Datum: 2026-06-11 10:32:13
- Status: Fertig für heute
- Was gemacht wurde:
  - Arbeitsende dokumentiert. Änderungen werden gepusht.
- Nächste Schritte:
  - ...
- Bemerkung:
  - Automatisch protokolliert durch session.ps1

- Datum: 2026-06-11 10:33:00
- Status: Fertig für heute
- Was gemacht wurde:
  - Arbeitsende dokumentiert. Änderungen werden gepusht.
- Nächste Schritte:
  - ...
- Bemerkung:
  - Automatisch protokolliert durch session.ps1

- Datum: 2026-06-11 10:35:17
- Status: Weiter gehts heute
- Was gemacht wurde:
  - Repository aktualisiert und letzter Stand eingelesen.
- Nächste Schritte:
  - ...
- Bemerkung:
  - Automatisch protokolliert durch session.ps1

- Datum: 2026-06-11 10:53:52
- Status: Fertig fuer heute
- Was gemacht wurde:
  - Arbeitsende dokumentiert. Aenderungen werden gepusht.
- Nächste Schritte:
  - ...
- Bemerkung:
  - Automatisch protokolliert durch session.ps1

- Datum: 2026-06-11 10:55:24
- Status: Weiter gehts heute
- Was gemacht wurde:
  - Repository aktualisiert und letzter Stand eingelesen.
- Nächste Schritte:
  - ...
- Bemerkung:
  - Automatisch protokolliert durch session.ps1

- Datum: 2026-06-11 11:21:16
- Status: In Arbeit
- Was gemacht wurde:
  - Personensuche für gezielte Personen robuster gemacht.
  - Datumsnormalisierung erweitert, damit GEDCOM-Daten wie `16 JAN 1778` korrekt mit Eingaben wie `16.01.1778` zusammenfinden.
  - Jahresableitung aus Geburtsdaten korrigiert, damit Tag-Monat-Jahr-Daten nicht mehr falsch ausgewertet werden.
- Nächste Schritte:
  - Ausgabe für die gesuchte Person und ihre Geschwister-Ehepartner weiter verfeinern, falls sich im Praxistest noch Mehrdeutigkeiten zeigen.
- Bemerkung:
  - Fortsetzung der Arbeit auf Basis der Wiederaufnahmebeschreibung für Anna Margaretha Hirnwurst.

- Datum: 2026-06-11 11:30:00
- Status: In Arbeit
- Was gemacht wurde:
  - Den allgemeinen Vergleich auf einen Enrichment-Report umgestellt.
  - Nur noch Personen ausgegeben, bei denen sich aus anderen GEDCOM-Dateien konkrete Ergänzungen zu Eltern, Geschwistern, Ehepartnern, Ehepartnern der Geschwister oder Kindern ableiten lassen.
  - Unsichere fuzzy Treffer reduziert, damit der Abgleich belastbarer bleibt.
- Nächste Schritte:
  - Bei Bedarf Ausgabeformat weiter schärfen oder auf einzelne Beziehungstypen eingrenzen.
- Bemerkung:
  - Ziel ist ein stammbauweiter Abgleich statt der vorherigen Listen mit allgemeinen Vergleichswerten.

- Datum: 2026-06-11 11:40:00
- Status: In Arbeit
- Was gemacht wurde:
  - Die Berichtsausgabe auf echte Fettformatierung für Personenüberschriften umgestellt.
  - Unter den fett markierten Namen werden nur noch neue Entdeckungen aus der anderen GEDCOM angezeigt.
  - Ehepartner-Blöcke wurden klarer beschriftet, damit die Ausgabe leichter lesbar bleibt.
- Nächste Schritte:
  - Prüfen, ob die neue Darstellung im Praxisbeispiel Anna Barbara GÜNZLER genau die gewünschten Ergänzungen zeigt.
- Bemerkung:
  - Übereinstimmungen selbst bleiben ausgeblendet.

- Datum: 2026-06-11 11:50:00
- Status: In Arbeit
- Was gemacht wurde:
  - Den Bericht so umgebaut, dass Ehepartner nicht mehr als verschachtelte Untereinträge erscheinen.
  - Jeder Personenblock zeigt jetzt nur direkte Ergänzungen, die aus der anderen GEDCOM abgeleitet werden können.
  - Die Ausgabe innerhalb der Personenliste alphabetisch aufsteigend sortiert.
- Nächste Schritte:
  - Prüfen, ob die direkte Darstellung im Beispiel mit Johann Michael EPPLER und Maria Barbara DAHINTEN jetzt logisch wirkt.
- Bemerkung:
  - Ziel ist eine klare Trennung zwischen Person und eigenem Ergänzungsblock, ohne Familienverschachtelung.

- Datum: 2026-06-11 12:00:00
- Status: In Arbeit
- Was gemacht wurde:
  - Die Ergänzungszeilen klarer beschriftet, damit die Quell-GEDCOM direkt sichtbar ist.
- Nächste Schritte:
  - Prüfen, ob die neue Formulierung `Ergänzungen aus <Datei>` im Report besser lesbar ist.
- Bemerkung:
  - Damit ist sofort erkennbar, welche GEDCOM jeweils den Stammbaum ergänzt.

- Datum: 2026-06-11 12:10:00
- Status: In Arbeit
- Was gemacht wurde:
  - Die Personen im Report nach Nachname sortiert.
  - Die Reihenfolge der Ergänzungsarten im Personenblock festgelegt: Eltern, Geschwister, Ehepartner, Kinder, Geschwister-Ehepartner, Kinder der Geschwister.
  - Die inneren Listen zusätzlich nach Nachname sortiert.
- Nächste Schritte:
  - Kurz prüfen, ob die neue Reihenfolge im Beispielreport logisch und ruhig lesbar wirkt.
- Bemerkung:
  - Ziel ist ein stabiler, genealogisch sinnvoller Lesefluss.

- Datum: 2026-06-11 12:20:00
- Status: In Arbeit
- Was gemacht wurde:
  - Die Ausgabe der Personennamen auf `Nachname / Vorname` umgestellt.
  - Die Darstellung wirkt damit näher an der genealogischen GEDCOM-Schreibweise.
- Nächste Schritte:
  - Prüfen, ob die neue Namensdarstellung in allen Reportzeilen sauber greift.
- Bemerkung:
  - Beispiel: `Ernst Albert/BARTHOLOMÄUS/` wird zu `BARTHOLOMÄUS / Ernst Albert`.

- Datum: 2026-06-11 12:30:00
- Status: In Arbeit
- Was gemacht wurde:
  - Einen PDF-Import ergänzt, der eine ausgewählte PDF-Datei in die SQLite-Datenbank schreibt.
  - Dazu die Tabellen `pdf_files`, `pdf_pages` und `pdf_records` angelegt.
  - Einen neuen Button `PDF importieren` in der Oberfläche ergänzt.
- Nächste Schritte:
  - Prüfen, ob die extrahierten PDF-Daten im Ziel-PDF die passenden Personenzeilen erkennen.
- Bemerkung:
  - Der Import versucht zuerst PyMuPDF und fällt sonst auf `pypdf` bzw. `PyPDF2` zurück.

- Datum: 2026-06-11 12:40:00
- Status: In Arbeit
- Was gemacht wurde:
  - Einen PDF-Datenbrowser ergänzt, der importierte PDF-Datensätze in einer Tabelle anzeigt.
  - Such- und Filterfelder für freie Suche, Nachname und Vorname eingebaut.
  - Die PDF-Ausgabe mit Seiten- und Zeilenangaben an den Import gekoppelt.
- Nächste Schritte:
  - Prüfen, ob die Filter im Praxisfall die gewünschten Datensätze sauber eingrenzen.
- Bemerkung:
  - Damit können die ausgelesenen PDF-Daten direkt durchsucht und kontrolliert werden.

- Datum: 2026-06-11 12:50:00
- Status: In Arbeit
- Was gemacht wurde:
  - Den PDF-Import auf eine vorherige Layout-Analyse umgestellt.
  - Blocknummern und Analyse-Metadaten in der Datenbank gespeichert.
  - Die Browser-Tabelle um die Blockspalte ergänzt.
- Nächste Schritte:
  - Prüfen, ob die strukturierte Auslese auf typischen genealogischen PDFs ausreichend präzise ist.
- Bemerkung:
  - Damit wird nicht nur Text gelesen, sondern die Seitenstruktur mit ausgewertet.

- Datum: 2026-06-11 13:00:00
- Status: In Arbeit
- Was gemacht wurde:
  - Den PDF-Import auf strukturierte Personendatensätze erweitert.
  - Felder für Auswanderung, Heirat, Herkunft, Wohnort und Zielort ergänzt.
  - Die PDF-Ansicht auf die „schönen“ Datensätze umgestellt.
- Nächste Schritte:
  - Prüfen, ob ein konkretes PDF noch spezielle Begriffe braucht, um die Ereignisse vollständig zu erkennen.
- Bemerkung:
  - Ziel ist ein direkt nutzbarer genealogischer Datensatz statt nur Rohtext.

- Datum: 2026-06-11 13:10:00
- Status: In Arbeit
- Was gemacht wurde:
  - `Auswanderer.pdf` als Beispiel berücksichtigt und die Extraktion darauf zugeschnitten.
  - Die Ausgabe um Alter/Geburtsdatum, Herkunft, Ziel, Jahr, Beruf, Quelle und Bemerkungen erweitert.
  - Die Browser-Tabelle so umgebaut, dass diese Felder direkt lesbar sind.
- Nächste Schritte:
  - Den Import mit einem echten Auswanderer-Datensatz testen und die Erkennung bei Bedarf nachschärfen.
- Bemerkung:
  - Damit wird aus dem PDF ein brauchbarer genealogischer Auswanderer-Datensatz.

- Datum: 2026-06-11 13:20:00
- Status: In Arbeit
- Was gemacht wurde:
  - Die Auswanderer-Extraktion auf saubere Datensatzgrenzen umgestellt, damit Überschriften und Folgezeilen nicht mehr vermischt werden.
  - OCR-Toleranz für zerlegte Labels wie `Alter oder Geburtsdatum` und `aus:` eingebaut.
  - Den angezeigten Namen auf das Format `NACHNAME / Vorname(n)` normalisiert und den Geburtsnamen separat gehalten.
- Nächste Schritte:
  - Einen kompletten Import von `Auswanderer.pdf` im GUI prüfen und die ersten Treffer visuell gegenkontrollieren.
- Bemerkung:
  - Die Ausgabe soll jetzt nur noch echte Personenblöcke enthalten und keine gemischten Rohtextzeilen mehr.


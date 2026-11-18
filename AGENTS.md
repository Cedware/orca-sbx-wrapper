# Projekt

In diesem Repository entstehen Wrapper-Skripte für KI-Agenten in
[Orca](https://github.com/stablyai/orca). Orca läuft wie gewohnt auf dem Host;
die Wrapper starten die eigentlichen Agenten über SBX in einer Sandbox.
Die Skripte setzen voraus, dass im jeweiligen Zielprojekt eine `sbxenv.yaml`
liegt und die SBX-Umgebung eingerichtet ist.

- `src/codex-sbx`: Bash-Wrapper für Codex; Orcas Modellkatalog-Abfrage läuft
  mit der lokalen Codex-Installation, andere Aufrufe laufen in SBX.
- `src/opencode-sbx.py`: Python-Wrapper für OpenCode; `models` läuft lokal,
  damit projektunabhängige Modelllisten etwa in Orcas Einstellungen ohne
  `sbxenv.yaml` geladen werden können. Andere Agentenaufrufe laufen in SBX.
  Für `serve` übernimmt der Wrapper Port-Veröffentlichung,
  Bereitschaftsmeldung und Aufräumen.
- `README.md`: Einrichtung in Orca, Voraussetzungen, Diagnose und Grenzen.

# Vor Arbeiten an den Wrappern: Orca main abrufen

Vor jeder Arbeit an den Wrapper-Skripten den **aktuellen Quellcode von Orcas
`main`** abrufen und die betroffenen Aufrufstellen lesen. Nicht allein auf
Erinnerung, eine installierte Orca-Version oder einen alten Checkout vertrauen.
Das gilt auch für die Dokumentation ihrer Orca-Anbindung.

Den Referenz-Checkout außerhalb dieses Repositorys anlegen, beispielsweise:

```sh
git clone --depth 1 --single-branch --branch main \
  https://github.com/stablyai/orca.git /tmp/orca-main
```

Bei einem bereits vorhandenen Referenz-Checkout `origin/main` mit
`git fetch origin main` aktualisieren und diesen Stand lesen; lokale Änderungen
nicht überschreiben. Den untersuchten Commit mit `git rev-parse origin/main`
festhalten und bei relevanten Kompatibilitätsaussagen nennen.

Besonders prüfen:

- Orcas Einstellungen und Auflösung der Agentenkommandos sowie deren
  Argumente, Arbeitsverzeichnis und Umgebung.
- Codex-Modellkatalog-Probe und deren exaktes Argument-Suffix; dieses bestimmt
  im Wrapper, ob Host-Codex oder SBX verwendet wird.
- OpenCode-Modell- und Versionsabfragen, ACP-/Serverstarts,
  Bereitschaftsformate, Authentifizierung, Zeitlimits und stdin-Lebenszyklus.
  Projektunabhängige Modellabfragen in den Einstellungen dabei getrennt von
  der Modellermittlung für Native Chat untersuchen.
- Unterschiede zwischen Orca `main` und der vom Nutzer eingesetzten Version.

Wenn der aktuelle Quellcode nicht erreichbar ist, die Einschränkung benennen
und keine ungeprüfte Kompatibilität behaupten.

# Regeln für Änderungen

- Arbeitsverzeichnis und Agentenargumente erhalten; die Auswahl der
  `sbxenv.yaml` an `sbx env exec` delegieren. Keine Projektpfade fest einbauen.
- Modellabfragen auf dem Host bewusst von Sandbox-Sitzungen unterscheiden.
  Host und Sandbox müssen dieselben gewünschten Modelle anbieten; die Wrapper
  synchronisieren weder Installationen noch Konfiguration oder Zugangsdaten.
- stdout für Orcas Protokollausgaben freihalten. Eigene Diagnosen auf stderr
  schreiben und keine Passwörter oder Tokens protokollieren.
- Beim OpenCode-Server nur auf Host-Loopback veröffentlichen; Port-Freigabe
  und Unterprozesse auch bei EOF, Signalen und Startfehlern aufräumen.
- macOS/Linux berücksichtigen. Bash beziehungsweise Python-Standardbibliothek
  beibehalten, sofern die Aufgabe keine weiteren Abhängigkeiten erfordert.
- Bei Verhaltensänderungen die README aktualisieren. Routing und betroffene
  Protokolle gezielt prüfen; echte SBX-/Orca-Tests nur als durchgeführt melden,
  wenn die benötigte Laufzeit vorhanden war.

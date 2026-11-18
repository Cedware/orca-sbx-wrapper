# Orca SBX Wrapper

Diese Skripte verbinden [Orca](https://github.com/stablyai/orca) auf dem Host
mit KI-Agenten in einer SBX-Sandbox. Orca wird wie gewohnt benutzt; als
Agentenkommando wird ein Wrapper eingetragen, der den eigentlichen Agenten
über `sbx env exec` startet.

Enthalten sind [Codex](src/codex-sbx) und [OpenCode](src/opencode-sbx.py).
Bestimmte Modellabfragen verwenden weiterhin die **lokale Installation auf dem
Host**. Die Wrapper installieren keine Agenten und synchronisieren keine
Konfigurationen oder Zugangsdaten.

## Voraussetzungen

| Auf dem Host | In der SBX-Umgebung des Zielprojekts |
| --- | --- |
| Orca und eine eingerichtete SBX-Laufzeit mit `sbx` im PATH von Orca | Der gewünschte Agent als `codex` bzw. `opencode` im PATH |
| Bash für den Codex-Wrapper; Python 3 für den OpenCode-Wrapper, ohne zusätzliche Python-Pakete | Funktionierende Agenten-Anmeldung bzw. Provider-Zugangsdaten und Netzwerkzugriff |
| Echtes lokales Codex bzw. OpenCode für die jeweiligen lokalen Modellabfragen | Passende Modelle, Provider und Agentenversionen |

Die Wrapper sind für **macOS/Linux** geschrieben. Die benötigten Hostprogramme
müssen auch aus der Umgebung des Orca-Prozesses erreichbar sein. Eine
funktionierende Installation in einer interaktiven Shell allein genügt dafür
bei einer Desktop-App unter Umständen nicht.

Host und Sandbox müssen dieselben gewünschten Modelle unter denselben IDs
anbieten. Am einfachsten ist das mit gleichen Agentenversionen, passenden
Provider-Konfigurationen und entsprechenden Berechtigungen. Sonst kann Orca
ein lokal angebotenes Modell auswählen, das der Agent in der Sandbox nicht
verwenden kann. Die Wrapper prüfen diese Übereinstimmung nicht.

## Einrichtung

### 1. Wrapper auf dem Host bereitstellen

```sh
git clone https://github.com/Cedware/orca-sbx-wrapper.git
cd orca-sbx-wrapper
chmod +x src/codex-sbx src/opencode-sbx.py
```

Das Repository an einem dauerhaften Ort belassen, da Orca die Dateien über
ihren absoluten Pfad aufruft. Die echten lokalen Programme `codex` und
`opencode` weiterhin verfügbar lassen. Insbesondere den Codex-Wrapper nicht
als Ersatz für das echte `codex` in den PATH legen: Die lokale Modellabfrage
könnte sonst wieder den Wrapper aufrufen.

### 2. SBX je Zielprojekt vorbereiten

Im **Projektverzeichnis, in dem der Agent arbeiten soll**, muss eine
`sbxenv.yaml` liegen. Ein minimales Beispiel für eine Codex-Umgebung:

```yaml
schemaVersion: "1"
name: mein-projekt
agent: codex
workspace: .
```

Name, Workspace und weitere Einstellungen an das Projekt und die verwendete
SBX-Version anpassen. Für OpenCode muss die SBX-Umgebung entsprechend ein
ausführbares `opencode` enthalten; das Codex-Beispiel stellt dies nicht sicher.
Anmeldung, Secrets, Netzwerkregeln und benötigte Werkzeuge über SBX einrichten.

Die Wrapper übernehmen das Arbeitsverzeichnis von Orca. Sie wechseln nicht
selbst zum Repository und lesen die YAML-Datei nicht selbst ein. Die Auflösung
übernimmt `sbx env exec`. Bei Orca-Worktrees darauf achten, dass auch im
tatsächlich gestarteten Worktree eine passende `sbxenv.yaml` vorhanden ist;
eine nur lokal im Haupt-Checkout liegende Datei wird nicht automatisch in
neue Worktrees übernommen. Relative Workspace-Pfade müssen dort ebenfalls
passen.

Vor der Orca-Einrichtung aus diesem Zielprojekt den benötigten Agenten prüfen:

```sh
sbx env exec -- codex --version
# Bei Verwendung von OpenCode:
sbx env exec -- opencode --version
```

Die Sandbox muss für automatische Starts ohne interaktive Rückfragen bereit
sein. Insbesondere OpenCodes Versionsabfragen müssen schnell genug antworten.

### 3. In Orca eintragen

In **Settings → Agents** die Zeile **Codex** bzw. **OpenCode** aufklappen.
Im Feld **Command** den vollständigen Pfad zum jeweiligen ausführbaren Skript
eintragen, zum Beispiel:

| Agent in Orca | Command |
| --- | --- |
| Codex | `/home/alex/orca-sbx-wrapper/src/codex-sbx` |
| OpenCode | `/home/alex/orca-sbx-wrapper/src/opencode-sbx.py` |

Die Beispielpfade durch die eigenen absoluten Pfade ersetzen. Die Skripte
direkt über ihren Shebang starten; zusätzliche SBX-Argumente im Feld
**Arguments** sind für die Wrapper nicht nötig. Orca übergibt die
Agentenargumente selbst. **Command** wird mit Enter oder beim Verlassen des
Feldes gespeichert; **Reset** stellt das Orca-Standardkommando wieder her.

Falls der echte lokale Agent nicht zuverlässig über den PATH gefunden wird,
im selben Bereich unter **Environment** die passende Variable als
`NAME=WERT` eintragen, ohne `export`. Mehrere Variablen durch Leerzeichen
trennen; Werte mit Leerzeichen in Anführungszeichen setzen. Das lokale
Environment-Feld speichert mit Enter oder beim Verlassen des Feldes.

| Variable | Bedeutung |
| --- | --- |
| `CODEX_SBX_HOST_CODEX` | Echtes Host-Codex, z. B. `/usr/local/bin/codex`. Standard: `codex` aus dem PATH. Niemals auf den Wrapper selbst setzen. |
| `OPENCODE_SBX_LOCAL_BINARY` | Absoluter ausführbarer Pfad zum echten Host-OpenCode, z. B. `/home/alex/.opencode/bin/opencode`. Relative Pfade werden abgewiesen. Ohne diese Variable wird der PATH durchsucht und der Wrapper selbst ausgeschlossen. |

Beispiel für das lokale OpenCode-Environment-Feld:

```text
OPENCODE_SBX_LOCAL_BINARY=/home/alex/.opencode/bin/opencode
```

Diese Variablen steuern die **Hostseite**. In der Sandbox werden weiterhin
die Programme `codex` bzw. `opencode` aus deren eigenem PATH verwendet.
Bei alternativ über die Shell gesetzten Variablen muss Orca sie beim Start
erben; ein nachträgliches `export` in einem anderen Terminal erreicht eine
bereits laufende Orca-App nicht.

### 4. Aus dem Zielprojekt starten

Das vorbereitete Projekt oder den vorbereiteten Worktree in Orca öffnen und
den konfigurierten Agenten starten. Neben dem Sitzungsstart auch die
Modellauswahl prüfen: Beide verwenden je nach Agent unterschiedliche Wege.

## Welche Aufrufe laufen wo?

| Wrapper und Aufruf | Ausführung |
| --- | --- |
| Codex: erkannte Orca-Modellkatalog-Probe | Echtes lokales Host-Codex |
| Codex: alle übrigen Aufrufe, auch normaler `app-server` und `--version` | SBX |
| OpenCode: `models …`, etwa für projektunabhängige Listen in den Einstellungen | Echtes lokales Host-OpenCode; keine `sbxenv.yaml` nötig |
| OpenCode: `acp`, `--version`, `-v`, TUI und sonstige Agentenaufrufe | SBX |
| OpenCode: `serve …` | SBX, zusätzlich Port-Veröffentlichung und Bereitschaftsmeldung für Orca |

Der Codex-Wrapper erkennt die Modellkatalog-Probe an diesem **exakten
Argument-Suffix**; davor dürfen weitere Argumente stehen:

```text
-c project_root_markers=[] -c approval_policy=never -c features.plugins=false -s read-only -a never app-server
```

Diese Ausnahme ermöglicht Modellabfragen auch außerhalb eines Projekts mit
`sbxenv.yaml`. Ändert Orca die Argumentfolge, muss die Erkennung im Wrapper
angepasst werden. Normale Codex-Sitzungen verwenden diesen lokalen Sonderweg
nicht.

**Projektunabhängige OpenCode-Modelllisten laufen lokal.** Zum Beispiel ruft
Orca für die Modellauswahl in den Source-Control-AI-Einstellungen `models`
auf. Der Wrapper leitet diese Aufrufe ausdrücklich an die echte
Hostinstallation weiter, unabhängig vom Arbeitsverzeichnis und ohne
`sbxenv.yaml`. Dieser Einstellungs-Pfad verwendet auch für OpenCode 2.x
`models`. Deshalb muss die lokale Installation vorhanden sein und die in
der Sandbox gewünschten Modelle anbieten.

Davon getrennt ist die Modellermittlung für **Native Chat**: Im untersuchten
Orca-`main` starten native OpenCode-Chats mit `acp`. Für deren Modellermittlung
wird bei OpenCode 1.x `models --verbose` verwendet; bei 2.x verwendet Orca
eine kurzlebige ACP-Sitzung. `models` läuft auch hier lokal, `acp` dagegen in
SBX. Eine pauschale Unterscheidung allein nach OpenCode-Version wäre daher
falsch; entscheidend ist der konkrete Aufrufweg.

Versions- und Hilfsabfragen werden weiterhin nach SBX geleitet. Werden diese
außerhalb des Projekts gestartet, können sie ohne dort auflösbare
SBX-Umgebung scheitern. Die lokale `models`-Abfrage ist davon unabhängig.

## OpenCode-Server und Ports

Für `serve` startet der Python-Wrapper OpenCode in SBX und erzwingt dort
`--hostname 0.0.0.0`. Er liest den Sandboxnamen aus `SANDBOX_NAME`, veröffentlicht
den Server auf einem freien **Hostport an `127.0.0.1`** und gibt erst danach
die umgeschriebene lokale Adresse an Orca weiter. Bei `--stdio` erwartet er
eine JSON-Bereitschaftsmeldung mit `url`, sonst die Textmeldung
`opencode server listening on …`.

Die eingesetzte SBX-Version muss insbesondere diese vom Skript verwendeten
CLI-Formen unterstützen:

```text
sbx --no-input env exec -i -- …
sbx ports <sandbox> --publish 127.0.0.1:<hostport>:<sandboxport>/tcp4
sbx ports <sandbox> --unpublish 127.0.0.1:<hostport>:<sandboxport>/tcp4
```

Manche SBX-Versionen dokumentieren stattdessen `sbx port publish …`. Entscheidend
ist, dass die tatsächlich vom Wrapper verwendete Schreibweise verfügbar ist;
die Skripte erkennen alternative CLI-Formen nicht automatisch.

Beim Serverstart überträgt der Wrapper ausdrücklich `OPENCODE_PASSWORD`,
`OPENCODE_SERVER_USERNAME`, `OPENCODE_SERVER_PASSWORD` und
`OPENCODE_DISABLE_SHARE` aus der Hostumgebung an den Sandboxprozess. Diese
Werte dienen Orcas Serverauthentifizierung bzw. Share-Einstellung. Andere
Hostvariablen, Account-Verzeichnisse, Provider-Einstellungen und
Konfigurationsdateien werden durch die Wrapper nicht ausdrücklich in die
Sandbox übertragen; ihre Verfügbarkeit hängt von der SBX-Konfiguration ab.

Orca hält stdin als Lebenszeichen offen. Bei EOF, SIGINT oder SIGTERM räumt
der Wrapper die Portfreigabe und seinen SBX-Unterprozess auf. Die gesamte
Sandbox wird dabei nicht ausdrücklich gelöscht. Der Serverstart hat ein
Zeitlimit von 45 Sekunden, einzelne Portoperationen von 10 Sekunden.

## Diagnose

Alle Aufrufe auf dem Host möglichst mit derselben Umgebung wie Orca
ausführen. Sandbox-Aufrufe aus dem vorbereiteten Zielprojekt starten.
Die lokale Modellabfrage funktioniert auch außerhalb eines Projekts, ohne
`sbxenv.yaml`. Die Beispielpfade ersetzen.

```sh
# Lokale OpenCode-Modellliste anzeigen:
/absoluter/pfad/orca-sbx-wrapper/src/opencode-sbx.py models

# OpenCode-Version über den Sandbox-Pfad prüfen:
/absoluter/pfad/orca-sbx-wrapper/src/opencode-sbx.py --version

# Codex über den Sandbox-Pfad prüfen:
/absoluter/pfad/orca-sbx-wrapper/src/codex-sbx --version
```

Modelllisten von Host und Sandbox mit für die jeweilige OpenCode-Version
passenden Befehlen vergleichen. Auch den tatsächlichen Sitzungsstart mit
dem gewünschten Modell prüfen.

| Problem | Prüfen |
| --- | --- |
| Agent startet nicht / `sbx` oder Interpreter fehlt | Absoluter Wrapperpfad, Ausführungsrechte und PATH des Orca-Prozesses; Bash bzw. Python 3 auf dem Host. |
| SBX findet kein Projekt | Tatsächliches Arbeitsverzeichnis, `sbxenv.yaml` im Zielprojekt/Worktree und SBX-Konfiguration. |
| Lokale Modellliste fehlt oder zeigt andere Modelle | Echtes Hostprogramm, die beiden Host-Binärpfadvariablen, verwendeter Account und Providerkonfiguration auf Host und Sandbox. |
| OpenCode scheitert bereits an der Version | Orca verwendet für mehrere Versionsprüfungen fünf Sekunden; eine kalte Sandbox vorher mit `sbx env exec -- opencode --version` starten und erneut prüfen. |
| OpenCode meldet keine erreichbare Serveradresse | `SANDBOX_NAME`, unterstützte `sbx ports`-Syntax und Startdauer prüfen. |
| Manueller `serve`-Test beendet sich sofort | stdin offen halten; ein Start mit `</dev/null` beendet den Serverpfad durch EOF. |

## Kompatibilität und Entwicklungsstand

Die Dokumentation wurde am **18.11.2026** mit Orca `main`, Commit
[`44599fe14711e4855f79c904950a92cbcb62ab59`](https://github.com/stablyai/orca/tree/44599fe14711e4855f79c904950a92cbcb62ab59),
und den vorhandenen Wrappern abgeglichen. Das ist eine Quellcodeanalyse;
ein vollständiger Lauf mit Orca und SBX wurde in dieser Entwicklungsumgebung
nicht durchgeführt.

Die Wrapper transportieren Agentenaufrufe. Orca-Funktionen, die Hostdateien,
lokale Agentendaten oder weitere Umgebungsvariablen benötigen, müssen für die
Sandbox gesondert eingerichtet und geprüft werden. Das betrifft etwa
Accountwechsel, Hooks, Sitzungsverlauf und OpenCode-Konfigurations-Overlays.
Bei OpenCode 2.x erkennt Orcas Umschreibung der TUI-Modellauswahl außerdem
die Executable-Namen `opencode`/`opencode2`; der direkte Wrappername
`opencode-sbx.py` erfüllt diese Erkennung nicht. Eine erfolgreiche
Serververbindung allein bestätigt diese Funktionen daher nicht.

Nach Orca- oder Agentenupdates die betroffenen Start- und Modellabfragen erneut
prüfen. Die Vorgaben für Änderungen, insbesondere das Abrufen von Orcas
aktuellem `main` vor Wrapperarbeiten, stehen in [AGENTS.md](AGENTS.md).

Quellstellen des untersuchten Orca-Stands:

- [Agenteneinrichtung und Command-Feld](https://github.com/stablyai/orca/blob/44599fe14711e4855f79c904950a92cbcb62ab59/docs/site/content/docs/agents/supported.mdx)
- [Codex-Modellkatalog-Probe](https://github.com/stablyai/orca/blob/44599fe14711e4855f79c904950a92cbcb62ab59/src/main/codex/structured/catalog/codex-model-catalog-probe.ts)
- [Codex-Probe-Argumente](https://github.com/stablyai/orca/blob/44599fe14711e4855f79c904950a92cbcb62ab59/src/main/codex-cli/codex-read-only-app-server-args.ts)
- [Projektunabhängige Modellabfrage aus den Einstellungen](https://github.com/stablyai/orca/blob/44599fe14711e4855f79c904950a92cbcb62ab59/src/renderer/src/components/settings/source-control/text-actions/use-text-action-model-discovery.ts)
- [OpenCode-Modellkommando für diese Abfrage](https://github.com/stablyai/orca/blob/44599fe14711e4855f79c904950a92cbcb62ab59/src/shared/source-control/ai/generation/commit-message-agent-specs-primary.ts)
- [OpenCode-ACP und versionsabhängige Modellermittlung für Native Chat](https://github.com/stablyai/orca/blob/44599fe14711e4855f79c904950a92cbcb62ab59/src/main/acp/launch/acp-launch-registry.ts)
- [OpenCode-Versionsprobe](https://github.com/stablyai/orca/blob/44599fe14711e4855f79c904950a92cbcb62ab59/src/main/opencode/model-launch/opencode-cli-version.ts)
- [OpenCode-TUI-Modellumschreibung](https://github.com/stablyai/orca/blob/44599fe14711e4855f79c904950a92cbcb62ab59/src/main/opencode/model-launch/opencode-root-model-overlay.ts)

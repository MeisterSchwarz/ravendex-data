# Upload-Ordner

Hier werden geprüfte JSON-Dateien per Drag-and-drop hochgeladen.

Erlaubte Dateinamen:

- `enemy_zones__<Welt>__<Sprache>.json`
- `enemy_names__<Welt>__<Sprache>.json`

Beispiel:

- `enemy_zones__WizardCity__de.json`
- `enemy_names__WizardCity__de.json`

Die GitHub Action verarbeitet die Dateien, merged sie in die Zieldateien und
entfernt die Upload-Dateien anschließend wieder.

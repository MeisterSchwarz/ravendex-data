#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
contribute = ROOT / "contribute"

UPLOAD_PATTERN = re.compile(
    r"^enemy_(zones|names)__([A-Za-z0-9_-]+)__([A-Za-z0-9_-]+)\.json$"
)


def read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Ungültiges JSON in {path.relative_to(ROOT)}: "
            f"Zeile {exc.lineno}, Spalte {exc.colno}: {exc.msg}"
        ) from exc


def write_translation_json(path: Path, data: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sorted_data = dict(sorted(data.items(), key=lambda item: item[0].casefold()))

    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(sorted_data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def write_zone_json(
    path: Path,
    zones: list[str],
    enemies: dict[str, set[str]],
) -> None:
    """Schreibt kompakte Enemy-Zeilen, aber eine gut lesbare Zonenliste."""
    path.parent.mkdir(parents=True, exist_ok=True)

    zone_to_index = {zone: index for index, zone in enumerate(zones)}
    sorted_enemies = sorted(enemies.items(), key=lambda item: item[0].casefold())

    lines: list[str] = ["{", '  "zones": [']

    for index, zone in enumerate(zones):
        comma = "," if index < len(zones) - 1 else ""
        lines.append(f"    {json.dumps(zone, ensure_ascii=False)}{comma}")

    lines.extend(["  ],", '  "enemies": {'])

    for index, (enemy_id, enemy_zones) in enumerate(sorted_enemies):
        zone_indexes = sorted(zone_to_index[zone] for zone in enemy_zones)
        comma = "," if index < len(sorted_enemies) - 1 else ""
        enemy_json = json.dumps(enemy_id, ensure_ascii=False)
        indexes_json = json.dumps(zone_indexes, ensure_ascii=False)
        lines.append(f'    {enemy_json}: {{ "zones": {indexes_json} }}{comma}')

    lines.extend(["  }", "}"])

    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def load_existing_zone_data(path: Path) -> tuple[dict[str, set[str]], set[str]]:
    if not path.exists():
        return {}, set()

    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(ROOT)} muss ein JSON-Objekt sein.")

    zones = data.get("zones")
    enemies = data.get("enemies")

    if not isinstance(zones, list) or not all(isinstance(zone, str) for zone in zones):
        raise ValueError(
            f"{path.relative_to(ROOT)}: 'zones' muss eine Liste aus Strings sein."
        )
    if len(zones) != len(set(zones)):
        raise ValueError(f"{path.relative_to(ROOT)} enthält doppelte globale Zonen.")
    if not isinstance(enemies, dict):
        raise ValueError(
            f"{path.relative_to(ROOT)}: 'enemies' muss ein JSON-Objekt sein."
        )

    result: dict[str, set[str]] = {}

    for enemy_id, enemy_data in enemies.items():
        if not isinstance(enemy_id, str) or not isinstance(enemy_data, dict):
            raise ValueError(
                f"{path.relative_to(ROOT)} enthält einen ungültigen Enemy-Eintrag."
            )

        indexes = enemy_data.get("zones")
        if not isinstance(indexes, list) or not all(
            isinstance(index, int) and not isinstance(index, bool)
            for index in indexes
        ):
            raise ValueError(
                f"{path.relative_to(ROOT)}: Zonen von {enemy_id!r} "
                "müssen ganzzahlige Indizes sein."
            )

        resolved: set[str] = set()
        for index in indexes:
            if index < 0 or index >= len(zones):
                raise ValueError(
                    f"{path.relative_to(ROOT)}: {enemy_id!r} verweist "
                    f"auf den ungültigen Zonenindex {index}."
                )
            resolved.add(zones[index])

        result[enemy_id] = resolved

    return result, set(zones)


def merge_zone_upload(upload_path: Path, world: str) -> None:
    target = ROOT / "core" / "enemies" / f"{world}.json"
    upload = read_json(upload_path)

    if not isinstance(upload, dict) or not isinstance(upload.get("enemies"), dict):
        raise ValueError(
            f"{upload_path.name}: Erwartet wird "
            '{"enemies": {"Enemy-ID": {"zones": ["Zonenpfad"]}}}.'
        )

    merged, known_zones = load_existing_zone_data(target)

    for enemy_id, enemy_data in upload["enemies"].items():
        if not isinstance(enemy_id, str) or not enemy_id:
            raise ValueError(f"{upload_path.name}: Ungültige Enemy-ID.")
        if not isinstance(enemy_data, dict):
            raise ValueError(
                f"{upload_path.name}: Daten für {enemy_id!r} müssen ein Objekt sein."
            )

        uploaded_zones = enemy_data.get("zones")
        if not isinstance(uploaded_zones, list) or not all(
            isinstance(zone, str) and zone for zone in uploaded_zones
        ):
            raise ValueError(
                f"{upload_path.name}: Zonen für {enemy_id!r} "
                "müssen eine Liste aus nicht leeren Strings sein."
            )

        # Bestehende und neu hochgeladene Zonen werden vereinigt.
        merged.setdefault(enemy_id, set()).update(uploaded_zones)
        known_zones.update(uploaded_zones)

    # Auch vorhandene, aktuell noch nicht referenzierte Zonen bleiben erhalten.
    all_zones = sorted(known_zones, key=str.casefold)
    write_zone_json(target, all_zones, merged)


def merge_name_upload(upload_path: Path, world: str, language: str) -> None:
    target = ROOT / "i18n" / language / "enemies" / f"{world}.json"
    upload = read_json(upload_path)

    if not isinstance(upload, dict) or not all(
        isinstance(enemy_id, str)
        and enemy_id
        and isinstance(name, str)
        and name
        for enemy_id, name in upload.items()
    ):
        raise ValueError(
            f"{upload_path.name}: Erwartet wird "
            '{"Enemy-ID": "Übersetzter Name"}.'
        )

    existing: dict[str, str] = {}
    if target.exists():
        loaded = read_json(target)
        if not isinstance(loaded, dict) or not all(
            isinstance(enemy_id, str) and isinstance(name, str)
            for enemy_id, name in loaded.items()
        ):
            raise ValueError(
                f"{target.relative_to(ROOT)} muss ein Objekt aus String-Werten sein."
            )
        existing.update(loaded)

    # Neue Übersetzungen überschreiben denselben vorhandenen Schlüssel.
    existing.update(upload)
    write_translation_json(target, existing)


def main() -> None:
    contribute.mkdir(parents=True, exist_ok=True)

    uploads = sorted(
        (
            path
            for path in contribute.iterdir()
            if path.is_file() and path.suffix.lower() == ".json"
        ),
        key=lambda path: path.name.casefold(),
    )

    if not uploads:
        print("Keine JSON-Uploads in contribute/ gefunden.")
        return

    processed: list[Path] = []

    for upload_path in uploads:
        match = UPLOAD_PATTERN.fullmatch(upload_path.name)
        if not match:
            raise ValueError(
                f"Ungültiger Dateiname: {upload_path.name}\n"
                "Erlaubt sind:\n"
                "  enemy_zones__<Welt>__<Sprache>.json\n"
                "  enemy_names__<Welt>__<Sprache>.json"
            )

        kind, world, language = match.groups()

        if kind == "zones":
            merge_zone_upload(upload_path, world)
        else:
            merge_name_upload(upload_path, world, language)

        processed.append(upload_path)
        print(f"Verarbeitet: {upload_path.relative_to(ROOT)}")

    # Erst löschen, nachdem alle Uploads erfolgreich verarbeitet wurden.
    for upload_path in processed:
        upload_path.unlink()

    print(f"{len(processed)} Upload-Datei(en) erfolgreich verarbeitet.")


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        raise SystemExit(f"FEHLER: {exc}") from exc

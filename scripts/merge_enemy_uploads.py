#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRIBUTE_DIR = ROOT / "contribute"
MANIFEST_PATH = ROOT / "manifest.json"

UPLOAD_PATTERN = re.compile(
    r"^enemy_names__([A-Za-z0-9_-]+)__([A-Za-z0-9_-]+)\.json$"
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


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")


def load_supported_languages() -> set[str]:
    manifest = read_json(MANIFEST_PATH)

    if not isinstance(manifest, dict):
        raise ValueError(
            "manifest.json muss ein JSON-Objekt sein."
        )

    languages = manifest.get("languages")

    if not isinstance(languages, list) or not all(
        isinstance(language, str) and language.strip()
        for language in languages
    ):
        raise ValueError(
            "manifest.json: 'languages' muss eine Liste "
            "aus nicht leeren Strings sein."
        )

    if not languages:
        raise ValueError(
            "manifest.json: 'languages' darf nicht leer sein."
        )

    normalized = {
        language.strip()
        for language in languages
    }

    if len(normalized) != len(languages):
        raise ValueError(
            "manifest.json enthält doppelte oder ungültige Sprachen."
        )

    return normalized


def sorted_dict(data: dict[str, Any]) -> dict[str, Any]:
    return dict(
        sorted(
            data.items(),
            key=lambda item: item[0].casefold(),
        )
    )


def validate_name_upload(
    upload_path: Path,
    upload: Any,
) -> dict[str, str]:
    if not isinstance(upload, dict):
        raise ValueError(
            f"{upload_path.name}: Erwartet wird ein JSON-Objekt "
            'im Format {"Enemy-ID": "Übersetzter Name"}.'
        )

    validated: dict[str, str] = {}

    for enemy_id, enemy_name in upload.items():
        if not isinstance(enemy_id, str):
            raise ValueError(
                f"{upload_path.name}: Enemy-IDs müssen Strings sein."
            )

        if not isinstance(enemy_name, str):
            raise ValueError(
                f"{upload_path.name}: Der Name für {enemy_id!r} "
                "muss ein String sein."
            )

        enemy_id = enemy_id.strip()
        enemy_name = enemy_name.strip()

        if not enemy_id:
            raise ValueError(
                f"{upload_path.name}: Eine Enemy-ID darf nicht leer sein."
            )

        if not enemy_name:
            raise ValueError(
                f"{upload_path.name}: Der Name für {enemy_id!r} "
                "darf nicht leer sein."
            )

        validated[enemy_id] = enemy_name

    return validated


def load_existing_names(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    loaded = read_json(path)

    if not isinstance(loaded, dict):
        raise ValueError(
            f"{path.relative_to(ROOT)} muss ein JSON-Objekt sein."
        )

    names: dict[str, str] = {}

    for enemy_id, enemy_name in loaded.items():
        if not isinstance(enemy_id, str) or not isinstance(enemy_name, str):
            raise ValueError(
                f"{path.relative_to(ROOT)} muss ausschließlich "
                "String-Schlüssel und String-Werte enthalten."
            )

        clean_id = enemy_id.strip()
        clean_name = enemy_name.strip()

        if not clean_id or not clean_name:
            raise ValueError(
                f"{path.relative_to(ROOT)} enthält einen leeren "
                "Gegner-Schlüssel oder Namen."
            )

        names[clean_id] = clean_name

    return names


def load_existing_core_enemies(
    path: Path,
) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}

    loaded = read_json(path)

    if not isinstance(loaded, dict):
        raise ValueError(
            f"{path.relative_to(ROOT)} muss ein JSON-Objekt sein."
        )

    enemies: dict[str, dict[str, Any]] = {}

    for enemy_id, metadata in loaded.items():
        if not isinstance(enemy_id, str) or not enemy_id.strip():
            raise ValueError(
                f"{path.relative_to(ROOT)} enthält eine ungültige Enemy-ID."
            )

        if not isinstance(metadata, dict):
            raise ValueError(
                f"{path.relative_to(ROOT)}: Metadaten für {enemy_id!r} "
                "müssen ein JSON-Objekt sein."
            )

        enemies[enemy_id.strip()] = metadata

    return enemies


def merge_name_upload(
    upload_path: Path,
    world: str,
    language: str,
) -> None:
    upload_raw = read_json(upload_path)
    upload = validate_name_upload(upload_path, upload_raw)

    translation_target = (
        ROOT
        / "i18n"
        / language
        / "enemies"
        / f"{world}.json"
    )

    core_target = (
        ROOT
        / "core"
        / "enemies"
        / f"{world}.json"
    )

    # Übersetzungen zusammenführen.
    existing_names = load_existing_names(translation_target)

    # Neue Werte überschreiben vorhandene Übersetzungen derselben ID.
    existing_names.update(upload)

    write_json(
        translation_target,
        sorted_dict(existing_names),
    )

    # Enemy-IDs in die Core-Datei übernehmen.
    existing_enemies = load_existing_core_enemies(core_target)

    for enemy_id in upload:
        # Vorhandene Metadaten niemals überschreiben.
        existing_enemies.setdefault(enemy_id, {})

    write_json(
        core_target,
        sorted_dict(existing_enemies),
    )


def main() -> None:
    CONTRIBUTE_DIR.mkdir(parents=True, exist_ok=True)

    uploads = sorted(
        (
            path
            for path in CONTRIBUTE_DIR.iterdir()
            if path.is_file()
            and path.suffix.lower() == ".json"
        ),
        key=lambda path: path.name.casefold(),
    )

    if not uploads:
        print("Keine JSON-Uploads in contribute/ gefunden.")
        return

    supported_languages = load_supported_languages()

    processed: list[Path] = []
    for upload_path in uploads:
        match = UPLOAD_PATTERN.fullmatch(upload_path.name)

        if not match:
            raise ValueError(
                f"Ungültiger Dateiname: {upload_path.name}\n"
                "Erlaubtes Format:\n"
                "  enemy_names__<Welt>__<Sprache>.json"
            )

        world, language = match.groups()
        if language not in supported_languages:
            supported = ", ".join(
                sorted(supported_languages, key=str.casefold)
            )

            raise ValueError(
                f"{upload_path.name}: Sprache {language!r} "
                f"wird nicht unterstützt. "
                f"Erlaubt sind: {supported}"
            )

        merge_name_upload(
            upload_path,
            world,
            language,
        )

        processed.append(upload_path)

        print(
            f"Verarbeitet: {upload_path.relative_to(ROOT)}"
        )

    # Erst löschen, nachdem alle Uploads erfolgreich verarbeitet wurden.
    for upload_path in processed:
        upload_path.unlink()

    print(
        f"{len(processed)} Upload-Datei(en) "
        "erfolgreich verarbeitet."
    )


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        raise SystemExit(f"FEHLER: {exc}") from exc
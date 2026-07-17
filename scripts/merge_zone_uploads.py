#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, TypeAlias


ROOT = Path(__file__).resolve().parents[1]
CONTRIBUTE_DIR = ROOT / "contribute"
MANIFEST_PATH = ROOT / "manifest.json"

UPLOAD_PATTERN = re.compile(
    r"^missing_zones__([A-Za-z0-9_-]+)__([A-Za-z0-9_-]+)\.json$"
)

ZoneTranslation: TypeAlias = str | list[str]


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

    formatted = json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
    )

    # Arrays aus genau zwei Strings wieder in eine einzelne Zeile setzen.
    formatted = re.sub(
        r'\[\n'
        r'\s*"((?:[^"\\]|\\.)*)",\n'
        r'\s*"((?:[^"\\]|\\.)*)"\n'
        r'\s*\]',
        lambda match: (
            "["
            + json.dumps(
                match.group(1),
                ensure_ascii=False,
            )
            + ", "
            + json.dumps(
                match.group(2),
                ensure_ascii=False,
            )
            + "]"
        ),
        formatted,
    )

    with path.open("w", encoding="utf-8", newline="\n") as file:
        file.write(formatted)
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


def validate_translation_value(
    source_name: str,
    zone_id: str,
    value: Any,
) -> ZoneTranslation:
    """
    Erlaubte Übersetzungswerte:

    "Die Basilika"

    oder:

    ["Das Atheneum", "Vorplatz"]
    """

    if isinstance(value, str):
        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError(
                f"{source_name}: Die Übersetzung für "
                f"{zone_id!r} darf nicht leer sein."
            )

        return cleaned_value

    if isinstance(value, list):
        if len(value) != 2:
            raise ValueError(
                f"{source_name}: Das Array für {zone_id!r} "
                "muss genau zwei Strings enthalten."
            )

        if not all(
            isinstance(item, str) and item.strip()
            for item in value
        ):
            raise ValueError(
                f"{source_name}: Das Array für {zone_id!r} "
                "muss aus genau zwei nicht leeren Strings bestehen."
            )

        return [
            value[0].strip(),
            value[1].strip(),
        ]

    raise ValueError(
        f"{source_name}: Die Übersetzung für {zone_id!r} "
        "muss entweder ein String oder ein Array aus genau "
        "zwei Strings sein."
    )


def validate_zone_upload(
    upload_path: Path,
    upload: Any,
) -> dict[str, ZoneTranslation]:
    if not isinstance(upload, dict):
        raise ValueError(
            f"{upload_path.name}: Erwartet wird ein JSON-Objekt "
            "im Format:\n"
            '  {"Zone-ID": "Übersetzter Name"}\n'
            "oder:\n"
            '  {"Zone-ID": ["Name", "Zusatz"]}'
        )

    validated: dict[str, ZoneTranslation] = {}

    for zone_id, translation in upload.items():
        if not isinstance(zone_id, str):
            raise ValueError(
                f"{upload_path.name}: Zone-IDs müssen Strings sein."
            )

        clean_id = zone_id.strip()

        if not clean_id:
            raise ValueError(
                f"{upload_path.name}: Eine Zone-ID darf nicht leer sein."
            )

        if clean_id in validated:
            raise ValueError(
                f"{upload_path.name}: Die Zone-ID {clean_id!r} "
                "ist mehrfach vorhanden."
            )

        validated[clean_id] = validate_translation_value(
            upload_path.name,
            clean_id,
            translation,
        )

    return validated


def load_existing_translations(
    path: Path,
) -> dict[str, ZoneTranslation]:
    if not path.exists():
        return {}

    loaded = read_json(path)

    if not isinstance(loaded, dict):
        raise ValueError(
            f"{path.relative_to(ROOT)} muss ein JSON-Objekt sein."
        )

    translations: dict[str, ZoneTranslation] = {}

    for zone_id, translation in loaded.items():
        if not isinstance(zone_id, str) or not zone_id.strip():
            raise ValueError(
                f"{path.relative_to(ROOT)} enthält eine ungültige Zone-ID."
            )

        clean_id = zone_id.strip()

        translations[clean_id] = validate_translation_value(
            str(path.relative_to(ROOT)),
            clean_id,
            translation,
        )

    return translations


def load_existing_core_zones(
    path: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """
    Erwartete Core-Struktur:

    {
      "zones": {
        "DragonSpire/DS_Hub_Cathedral": {}
      }
    }

    Andere Top-Level-Felder bleiben erhalten.
    """

    if not path.exists():
        return {"zones": {}}, {}

    loaded = read_json(path)

    if not isinstance(loaded, dict):
        raise ValueError(
            f"{path.relative_to(ROOT)} muss ein JSON-Objekt sein."
        )

    zones = loaded.get("zones")

    if zones is None:
        zones = {}
    elif not isinstance(zones, dict):
        raise ValueError(
            f"{path.relative_to(ROOT)}: 'zones' muss "
            "ein JSON-Objekt sein."
        )

    validated_zones: dict[str, dict[str, Any]] = {}

    for zone_id, metadata in zones.items():
        if not isinstance(zone_id, str) or not zone_id.strip():
            raise ValueError(
                f"{path.relative_to(ROOT)} enthält eine "
                "ungültige Zone-ID."
            )

        if not isinstance(metadata, dict):
            raise ValueError(
                f"{path.relative_to(ROOT)}: Der Wert für "
                f"{zone_id!r} muss ein JSON-Objekt sein."
            )

        validated_zones[zone_id.strip()] = metadata

    return loaded, validated_zones


def merge_zone_upload(
    upload_path: Path,
    world: str,
    language: str,
) -> None:
    upload_raw = read_json(upload_path)
    upload = validate_zone_upload(upload_path, upload_raw)

    translation_target = (
        ROOT
        / "i18n"
        / language
        / "zones"
        / f"{world}.json"
    )

    core_target = (
        ROOT
        / "core"
        / "zones"
        / f"{world}.json"
    )

    # Übersetzungen in i18n/<Sprache>/zones/<Welt>.json eintragen.
    existing_translations = load_existing_translations(
        translation_target
    )

    # Neue Upload-Werte überschreiben vorhandene Werte derselben Zone-ID.
    existing_translations.update(upload)

    write_json(
        translation_target,
        sorted_dict(existing_translations),
    )

    # Zone-IDs in core/zones/<Welt>.json übernehmen.
    core_document, existing_zones = load_existing_core_zones(
        core_target
    )

    for zone_id in upload:
        # Vorhandene Core-Metadaten niemals überschreiben.
        # Neue Zone-IDs erhalten lediglich eine leere geschweifte Klammer.
        existing_zones.setdefault(zone_id, {})

    core_document["zones"] = sorted_dict(existing_zones)

    write_json(
        core_target,
        core_document,
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
                "  missing_zones__<Welt>__<Sprache>.json"
            )

        world, language = match.groups()

        if language not in supported_languages:
            supported = ", ".join(
                sorted(
                    supported_languages,
                    key=str.casefold,
                )
            )

            raise ValueError(
                f"{upload_path.name}: Sprache {language!r} "
                f"wird nicht unterstützt. "
                f"Erlaubt sind: {supported}"
            )

        merge_zone_upload(
            upload_path=upload_path,
            world=world,
            language=language,
        )

        processed.append(upload_path)

        print(
            f"Verarbeitet: {upload_path.relative_to(ROOT)}"
        )

    # Uploads erst löschen, wenn alle Dateien erfolgreich
    # validiert und verarbeitet wurden.
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
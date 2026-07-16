# RavenDex Data

Shared game data for the **RavenDex** ecosystem.

This repository contains structured data extracted from Wizard101, including internal game IDs, localizations, and community-maintained metadata.

The goal of this repository is to provide a single, version-controlled source of truth that can be reused by RavenDex and other community projects.

> **Application:** https://github.com/MeisterSchwarz/ravendex

---

## 🎯 Goals

- Provide a centralized dataset for Wizard101.
- Separate application code from game data.
- Support multiple languages through community translations.
- Offer stable identifiers for developers building tools on top of the data.
- Enable community contributions without requiring changes to the application itself.

---

## 📦 Currently Included

The repository currently contains data for:

- Enemy IDs
- Zone IDs
- NPC IDs
- Object IDs
- Localized names
- Community translations
- Contribution files submitted through RavenDex

The dataset will continue to grow over time as additional game data is collected and verified.

---

## 🌍 Localization

RavenDex stores game entities using their internal IDs rather than language-specific names.

This allows every entity to have translations for multiple languages while keeping references stable across the entire project.

Example:

```json
{
  "id": 12345,
  "translations": {
    "en": "Gobbler",
    "de": "Vielfraß"
  }
}
```

---

## 💙 Using the Data

Everyone is welcome to use the data provided in this repository for their own Wizard101 projects.

Whether you're building a website, Discord bot, desktop application, API, or any other community tool, feel free to use this dataset.

If you improve or expand the data, contributions back to the repository are always appreciated so the entire community can benefit.

---

## 🤝 Contributing

Contributions are welcome!

The recommended way to contribute is through **RavenDex**, which can generate contribution files for newly identified game entities.

Simply attach the generated file to a new GitHub Issue in this repository.

You can also submit corrections or improvements manually through Issues or Pull Requests.

---

## 🚀 Future Plans

Planned additions include:

- Item metadata
- Community-verified drop rates
- Boss metadata
- Quest references
- World and zone relationships
- Search metadata
- Additional localizations

---

## 📄 License

This repository contains community-maintained game metadata intended for use by the Wizard101 community.

It does **not** contain copyrighted game assets.

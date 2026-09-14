# Open Source Mac Apps → RSS

Erzeugt einen RSS-2.0-Feed aus `applications.json` von
`serhii-londar/open-source-mac-os-apps`.

## Verwendung

Das Repository kann als eigenes GitHub-Repository verwendet werden. Die GitHub Action
läuft täglich und veröffentlicht `feed.xml` über GitHub Pages.

### Einrichtung

1. Dateien dieses Projekts in ein neues GitHub-Repository kopieren.
2. In GitHub unter **Settings → Pages** bei *Build and deployment*:
   - **Source:** GitHub Actions
3. Unter **Settings → Actions → General** sicherstellen, dass Actions Schreibzugriff
   auf den Repository-Inhalt haben, falls GitHub Pages/Deployment danach fragt.
4. Nach dem ersten erfolgreichen Workflow liegt der Feed unter:

   `https://<DEIN-USERNAME>.github.io/<REPO>/feed.xml`

Den Feed kannst du anschließend in NetNewsWire, Reeder, Feedly, FreshRSS usw. abonnieren.

## Was der Feed macht

- lädt die aktuelle `applications.json` des Originalprojekts
- erkennt neue Einträge anhand ihrer `repo_url`
- erzeugt nur für neu hinzugekommene Apps RSS-Einträge
- speichert den bisher bekannten Stand in `state.json`
- enthält beim ersten Lauf **keine tausenden alten Apps**, sondern markiert den aktuellen
  Bestand nur als bekannt
- neue Apps werden beim nächsten Lauf automatisch veröffentlicht
- bei jedem Lauf werden maximal 50 neue Apps veröffentlicht

Die Quelle wird nicht verändert.

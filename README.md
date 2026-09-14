# Open Source Mac Apps → RSS

Generates an RSS 2.0 feed from `applications.json` in
`serhii-londar/open-source-mac-os-apps`.

## Usage

The repository can be used as a standalone GitHub repository. The GitHub Action
runs daily and publishes `feed.xml` via GitHub Pages.

### Set-up

1. Copy the files from this project into a new GitHub repository.
2. In GitHub, go to **Settings → Pages** and under *Build and deployment*:
   - **Source:** GitHub Actions
3. Under **Settings → Actions → General**, ensure that Actions have write access
   to the repository’s contents, should GitHub Pages/Deployment request this.
4. After the first successful workflow, the feed will be available at:

   `https://<YOUR-USERNAME>.github.io/<REPO>/feed.xml`

You can then subscribe to the feed in NetNewsWire, Reeder, Feedly, FreshRSS, etc.

## What the feed does

- loads the latest `applications.json` from the original project
- identifies new entries based on their `repo_url`
- generates RSS entries only for newly added apps
- saves the current known status in `state.json`
- on the first run, it does **not contain thousands of old apps**, but simply marks the current
  list as known
- new apps are automatically published on the next run
- a maximum of 50 new apps are published on each run

The source is not modified.

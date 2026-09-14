# Open Source Mac Apps → RSS

RSS generator for `serhii-londar/open-source-mac-os-apps`.

## Features

- New apps, updates and removed apps
- Categories and separate category feeds
- App icon as an RSS enclosure if `icon_url` is provided
- Persistent state in `state.json`
- No flood on first run: the first run only creates a baseline
- **GitHub Action once an hour**
- Manual workflow start
- GitHub Pages for the XML feeds

## Set-up

1. Create a new GitHub repository, e.g. `open-source-mac-apps-rss`.
2. Push all files from this package to the default branch (usually `main`).
3. Under `Settings → Pages`, select **GitHub Actions** as the source.
4. The `Update RSS feeds` action runs automatically **once an hour**, at 17 minutes past the hour (UTC), and can also be triggered manually.

The feed URL is automatically generated from the repository name and owner:

`https://OWNER.github.io/REPOSITORY/feeds/feed.xml`

Example:

`https://meinname.github.io/open-source-mac-apps-rss/feeds/feed.xml`

## Important

GitHub Actions cron jobs are not precise to the second. `17 * * * *` means approximately once an hour; GitHub may delay the actual start time slightly.

On the first run, all existing apps are saved as a baseline only. Only afterwards will new, modified or removed apps appear in the RSS feed.

Category feeds are located under `feeds/category-*.xml`. Categories such as `Editors / Text` are standardised to `editors-text` for the filename.

On Linux, you can edit files using `vi`, for example:

```bash
vi generate_feed.py
```
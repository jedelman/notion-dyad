# Notion Dyad

Auto-discovering Notion database presenter with dynamic rendering and frontmatter control.

## Setup

### Local Development

1. Clone the repo:
   ```bash
   git clone https://github.com/jedelman/notion-dyad.git
   cd notion-dyad
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create `.streamlit/secrets.toml`:
   ```toml
   NOTION_API_KEY = "your-notion-api-key-here"
   ```

4. Get your Notion API key:
   - Go to https://www.notion.so/my-integrations
   - Create a new integration
   - Copy the "Internal Integration Token"
   - Share databases with the integration (open database → share → select integration)

5. Run locally:
   ```bash
   streamlit run app.py
   ```

### Streamlit Cloud Deployment

1. Push repo to GitHub
2. Go to https://streamlit.io/cloud
3. Click "New app" → select your repo
4. Set repo branch: `main`
5. Set main file path: `app.py`
6. Click "Deploy"
7. Once deployed, go to **Advanced settings**:
   - Add secret: `NOTION_API_KEY = your-token-here`
   - Save

## Usage

1. **Database Discovery**: App auto-discovers all databases your integration has access to
2. **View Modes**: Toggle between Wiki (article), Card Grid (dashboard), or Slide Deck (presentation)
3. **Frontmatter Control**: Add a `Frontmatter` property to any Notion page with YAML config:

```yaml
render:
  view: wiki | card | slide
  title_field: "Custom Title Property"
  hide_fields: ["internal_notes", "draft"]
  template: default
  theme:
    mode: light | dark
```

### Frontmatter Options

- `view`: Override rendering mode for this page
- `title_field`: Which property contains the title (default: "title")
- `hide_fields`: List of properties to hide from render
- `template`: Future: custom templates
- `theme`: Visual overrides

## Architecture

- **Discovery**: Scans workspace for all accessible databases
- **Schema Inspection**: Reads property types (title, rich_text, select, relation, etc.)
- **Dynamic Render**: Smart defaults for each property type
- **Frontmatter Override**: YAML config in Notion properties for fine-grained control
- **Multi-view**: Wiki (article), Card (grid), Slide (presentation) modes

## Next Steps

- [ ] Full-text search across pages
- [ ] Relation/backlink visualization
- [ ] Custom CSS per database
- [ ] Export to markdown/PDF
- [ ] Real-time sync via Notion webhooks

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from notion_client import Client
import yaml
import os
from jinja2 import Template
from typing import Dict, List, Any

app = FastAPI()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
if not NOTION_API_KEY:
    raise ValueError("NOTION_API_KEY environment variable not set")

notion_client = Client(auth=NOTION_API_KEY)

def discover_databases() -> Dict[str, str]:
    try:
        response = notion_client.search(filter={"value": "database", "property": "object"}, page_size=100)
        return {item["title"][0]["plain_text"]: item["id"] for item in response["results"] if item["object"] == "database"}
    except Exception as e:
        return {"error": str(e)}

def get_database_schema(database_id: str) -> Dict[str, Any]:
    try:
        db = notion_client.databases.retrieve(database_id)
        return db.get("properties", {})
    except Exception as e:
        return {"error": str(e)}

def query_database(database_id: str) -> List[Dict[str, Any]]:
    try:
        pages, cursor = [], None
        while True:
            response = notion_client.databases.query(database_id=database_id, start_cursor=cursor, page_size=100)
            pages.extend(response.get("results", []))
            cursor = response.get("next_cursor")
            if not cursor:
                break
        return pages
    except Exception as e:
        return [{"error": str(e)}]

def parse_frontmatter(page: Dict[str, Any]) -> Dict[str, Any]:
    config = {"view": "wiki", "title_field": "title", "hide_fields": [], "template": "default", "theme": {"mode": "light"}}
    for prop_name in ["Frontmatter", "Config", "Render Config", "Schema"]:
        if prop_name in page.get("properties", {}):
            prop_value = page["properties"][prop_name]
            if prop_value["type"] == "rich_text":
                text = "".join([block["plain_text"] for block in prop_value.get("rich_text", [])])
                if text.strip():
                    try:
                        user_config = yaml.safe_load(text)
                        if user_config and isinstance(user_config, dict):
                            config.update(user_config)
                    except yaml.YAMLError:
                        pass
    return config

def extract_property_value(prop_value: Dict[str, Any], prop_type: str) -> Any:
    if prop_type == "title":
        return "".join([block["plain_text"] for block in prop_value.get("title", [])])
    elif prop_type in ["rich_text", "text"]:
        return "".join([block["plain_text"] for block in prop_value.get("rich_text", [])])
    elif prop_type == "number":
        return prop_value.get("number")
    elif prop_type == "select":
        select = prop_value.get("select")
        return select["name"] if select else None
    elif prop_type == "multi_select":
        return [item["name"] for item in prop_value.get("multi_select", [])]
    elif prop_type == "date":
        date_obj = prop_value.get("date")
        return date_obj["start"] if date_obj else None
    elif prop_type == "checkbox":
        return prop_value.get("checkbox", False)
    elif prop_type == "url":
        return prop_value.get("url")
    elif prop_type == "email":
        return prop_value.get("email")
    elif prop_type == "relation":
        return [item["id"] for item in prop_value.get("relation", [])]
    elif prop_type == "people":
        return [person.get("name", person.get("id")) for person in prop_value.get("people", [])]
    return None

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Notion Dyad</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        h1 { margin-bottom: 10px; }
        .controls { display: flex; gap: 10px; margin-top: 15px; flex-wrap: wrap; }
        select, button { padding: 8px 16px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
        button { background: #007bff; color: white; cursor: pointer; border: none; }
        button:hover { background: #0056b3; }
        .wiki { background: white; padding: 30px; border-radius: 8px; line-height: 1.8; }
        .wiki h2 { margin-top: 20px; margin-bottom: 10px; font-size: 18px; }
        .wiki hr { margin: 40px 0; border: none; border-top: 1px solid #ddd; }
        .card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .card h3 { margin-bottom: 12px; font-size: 16px; }
        .card p { font-size: 14px; color: #666; margin: 8px 0; }
        .slide { background: white; padding: 60px 40px; border-radius: 8px; min-height: 600px; text-align: center; }
        .slide h1 { font-size: 48px; margin-bottom: 40px; }
        .slide ul { text-align: left; display: inline-block; font-size: 24px; line-height: 1.8; }
        .error { background: #f8d7da; color: #721c24; padding: 20px; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📚 Notion Dyad</h1>
            <p>Auto-discovering Notion databases with dynamic rendering</p>
            <div class="controls">
                <form method="GET" style="display: flex; gap: 10px;">
                    <select name="db_id" required>
                        <option value="">Select database...</option>
                        {% for name, id in databases.items() %}
                        <option value="{{ id }}" {% if id == selected_db_id %}selected{% endif %}>{{ name }}</option>
                        {% endfor %}
                    </select>
                    <select name="view" required>
                        <option value="wiki" {% if view == 'wiki' %}selected{% endif %}>Wiki</option>
                        <option value="card" {% if view == 'card' %}selected{% endif %}>Card Grid</option>
                        <option value="slide" {% if view == 'slide' %}selected{% endif %}>Slide Deck</option>
                    </select>
                    <button type="submit">Load</button>
                </form>
            </div>
        </header>

        {% if error %}
        <div class="error">{{ error }}</div>
        {% else %}

        {% if view == 'wiki' %}
        <div class="wiki">
            {% for page in pages %}
            <h2>{{ page.title }}</h2>
            <p><em>Last edited: {{ page.last_edited }}</em></p>
            {% for key, value in page.properties.items() %}
                {% if value %}<p><strong>{{ key }}:</strong> {{ value }}</p>{% endif %}
            {% endfor %}
            <hr>
            {% endfor %}
        </div>
        {% elif view == 'card' %}
        <div class="card-grid">
            {% for page in pages %}
            <div class="card">
                <h3>{{ page.title }}</h3>
                {% for key, value in page.properties.items() %}
                    {% if value and key != 'title' %}<p><strong>{{ key }}:</strong> {{ value }}</p>{% endif %}
                {% endfor %}
            </div>
            {% endfor %}
        </div>
        {% elif view == 'slide' %}
        <div class="slide">
            {% set page = pages[page_idx] %}
            <h1>{{ page.title }}</h1>
            <ul>
            {% for key, value in page.properties.items() %}
                {% if value and key != 'title' %}<li><strong>{{ key }}:</strong> {{ value }}</li>{% endif %}
            {% endfor %}
            </ul>
            <div style="margin-top: 40px;">
                <p>Slide {{ page_idx + 1 }} of {{ pages|length }}</p>
                {% if page_idx > 0 %}
                <a href="?db_id={{ selected_db_id }}&view=slide&page={{ page_idx - 1 }}"><button>← Prev</button></a>
                {% endif %}
                {% if page_idx < pages|length - 1 %}
                <a href="?db_id={{ selected_db_id }}&view=slide&page={{ page_idx + 1 }}"><button>Next →</button></a>
                {% endif %}
            </div>
        </div>
        {% endif %}

        {% endif %}
    </div>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def root(db_id: str = Query(None), view: str = Query("wiki"), page: int = Query(0)):
    databases = discover_databases()
    
    if "error" in databases:
        return f"<div class='error'>Error: {databases['error']}</div>"
    
    if not db_id:
        template = Template(HTML_TEMPLATE)
        return template.render(databases=databases, selected_db_id=None, view=view, pages=[], page_idx=0, error="Select a database")
    
    schema = get_database_schema(db_id)
    pages_raw = query_database(db_id)
    
    pages = []
    for p in pages_raw:
        if "error" in p:
            continue
        config = parse_frontmatter(p)
        hide_fields = set(config.get("hide_fields", []) + ["Frontmatter", "Config", "Render Config", "Schema"])
        
        title_field = config.get("title_field", "title")
        title = "Untitled"
        if title_field in p["properties"]:
            val = extract_property_value(p["properties"][title_field], schema[title_field]["type"])
            if val:
                title = val
        
        properties = {}
        for prop_name, prop_value in p["properties"].items():
            if prop_name in hide_fields:
                continue
            prop_type = schema[prop_name]["type"]
            value = extract_property_value(prop_value, prop_type)
            if value and value != [] and value != "":
                properties[prop_name] = str(value) if not isinstance(value, list) else ", ".join(str(v) for v in value)
        
        pages.append({"title": title, "last_edited": p["last_edited_time"][:10], "properties": properties})
    
    template = Template(HTML_TEMPLATE)
    return template.render(databases=databases, selected_db_id=db_id, view=view, pages=pages, page_idx=page, error=None)

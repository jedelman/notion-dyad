import streamlit as st
from notion_client import Client
import yaml
import json
from typing import Dict, List, Any
from datetime import datetime
import hashlib

st.set_page_config(page_title="Notion Dyad", layout="wide")

@st.cache_resource
def get_notion_client():
    """Initialize Notion client with API key from secrets."""
    api_key = st.secrets.get("NOTION_API_KEY")
    if not api_key:
        st.error("❌ NOTION_API_KEY not found in Streamlit secrets")
        st.stop()
    return Client(auth=api_key)

def discover_databases(notion_client: Client) -> Dict[str, str]:
    """Discover all accessible databases in the workspace."""
    try:
        # Search for all databases
        response = notion_client.search(
            filter={"value": "database", "property": "object"},
            page_size=100
        )
        databases = {item["title"][0]["plain_text"]: item["id"] for item in response["results"] if item["object"] == "database"}
        return databases
    except Exception as e:
        st.error(f"Failed to discover databases: {e}")
        return {}

def get_database_schema(notion_client: Client, database_id: str) -> Dict[str, Any]:
    """Inspect database schema and return property definitions."""
    try:
        db = notion_client.databases.retrieve(database_id)
        return db.get("properties", {})
    except Exception as e:
        st.error(f"Failed to retrieve schema: {e}")
        return {}

def query_database(notion_client: Client, database_id: str) -> List[Dict[str, Any]]:
    """Query all pages in a database."""
    try:
        pages = []
        cursor = None
        while True:
            response = notion_client.databases.query(
                database_id=database_id,
                start_cursor=cursor,
                page_size=100
            )
            pages.extend(response.get("results", []))
            cursor = response.get("next_cursor")
            if not cursor:
                break
        return pages
    except Exception as e:
        st.error(f"Failed to query database: {e}")
        return []

def parse_frontmatter(page: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and parse YAML frontmatter from a page property (e.g., 'Frontmatter' or 'Config')."""
    config = {
        "view": "wiki",
        "title_field": "title",
        "hide_fields": [],
        "template": "default",
        "theme": {"mode": "light"}
    }
    
    # Look for frontmatter in common property names
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
    """Extract readable value from a Notion property."""
    if prop_type == "title":
        return "".join([block["plain_text"] for block in prop_value.get("title", [])])
    elif prop_type == "rich_text":
        return "".join([block["plain_text"] for block in prop_value.get("rich_text", [])])
    elif prop_type == "text":
        return "".join([block["plain_text"] for block in prop_value.get("rich_text", [])])
    elif prop_type == "number":
        return prop_value.get("number")
    elif prop_type == "select":
        select = prop_value.get("select")
        return select["name"] if select else None
    elif prop_type == "multi_select":
        multi = prop_value.get("multi_select", [])
        return [item["name"] for item in multi]
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
        relations = prop_value.get("relation", [])
        return [item["id"] for item in relations]
    elif prop_type == "people":
        people = prop_value.get("people", [])
        return [person.get("name", person.get("id")) for person in people]
    else:
        return None

def render_page_wiki(page: Dict[str, Any], schema: Dict[str, Any], config: Dict[str, Any]):
    """Render page as a wiki article."""
    title_field = config.get("title_field", "title")
    hide_fields = set(config.get("hide_fields", []) + ["Frontmatter", "Config", "Render Config", "Schema"])
    
    # Extract title
    title = "Untitled"
    if title_field in page["properties"]:
        title = extract_property_value(page["properties"][title_field], schema[title_field]["type"])
    
    st.markdown(f"# {title}")
    st.markdown(f"*Last edited: {page['last_edited_time'][:10]}*")
    st.divider()
    
    # Render properties
    for prop_name, prop_value in page["properties"].items():
        if prop_name in hide_fields:
            continue
        
        prop_type = schema[prop_name]["type"]
        value = extract_property_value(prop_value, prop_type)
        
        if value is None or value == [] or value == "":
            continue
        
        st.markdown(f"**{prop_name}:** ", unsafe_allow_html=True)
        if isinstance(value, list):
            st.write(", ".join(str(v) for v in value))
        else:
            st.write(value)

def render_page_card(page: Dict[str, Any], schema: Dict[str, Any], config: Dict[str, Any]):
    """Render page as a card."""
    title_field = config.get("title_field", "title")
    hide_fields = set(config.get("hide_fields", []) + ["Frontmatter", "Config", "Render Config", "Schema"])
    
    title = "Untitled"
    if title_field in page["properties"]:
        title = extract_property_value(page["properties"][title_field], schema[title_field]["type"])
    
    with st.container(border=True):
        st.markdown(f"### {title}")
        
        for prop_name, prop_value in page["properties"].items():
            if prop_name in hide_fields or prop_name == title_field:
                continue
            
            prop_type = schema[prop_name]["type"]
            value = extract_property_value(prop_value, prop_type)
            
            if value and value != [] and value != "":
                if isinstance(value, list):
                    st.caption(f"{prop_name}: {', '.join(str(v) for v in value)}")
                else:
                    st.caption(f"{prop_name}: {value}")

def render_page_slide(page: Dict[str, Any], schema: Dict[str, Any], config: Dict[str, Any]):
    """Render page as a presentation slide."""
    title_field = config.get("title_field", "title")
    hide_fields = set(config.get("hide_fields", []) + ["Frontmatter", "Config", "Render Config", "Schema"])
    
    title = "Untitled"
    if title_field in page["properties"]:
        title = extract_property_value(page["properties"][title_field], schema[title_field]["type"])
    
    st.markdown(f"# {title}")
    
    content = []
    for prop_name, prop_value in page["properties"].items():
        if prop_name in hide_fields or prop_name == title_field:
            continue
        
        prop_type = schema[prop_name]["type"]
        value = extract_property_value(prop_value, prop_type)
        
        if value and value != [] and value != "":
            if isinstance(value, list):
                content.append(f"- {prop_name}: {', '.join(str(v) for v in value)}")
            else:
                content.append(f"- {prop_name}: {value}")
    
    if content:
        st.markdown("\n".join(content))

# Main UI
st.title("📚 Notion Dyad")
st.markdown("Auto-discovering Notion databases with dynamic rendering and frontmatter control.")

notion_client = get_notion_client()

# Discover and select database
databases = discover_databases(notion_client)

if not databases:
    st.warning("No databases found. Check your Notion API key permissions.")
    st.stop()

selected_db_name = st.selectbox("Select a database:", list(databases.keys()))
selected_db_id = databases[selected_db_name]

# Get schema and pages
schema = get_database_schema(notion_client, selected_db_id)
pages = query_database(notion_client, selected_db_id)

st.success(f"Found {len(pages)} pages in '{selected_db_name}'")
st.divider()

# View selector
view_type = st.radio("View type:", ["Wiki", "Card Grid", "Slide Deck"], horizontal=True)

# Render pages
if view_type == "Wiki":
    for page in pages:
        config = parse_frontmatter(page)
        render_page_wiki(page, schema, config)
        st.divider()

elif view_type == "Card Grid":
    cols = st.columns(3)
    for idx, page in enumerate(pages):
        config = parse_frontmatter(page)
        with cols[idx % 3]:
            render_page_card(page, schema, config)

elif view_type == "Slide Deck":
    page_idx = st.number_input("Page:", min_value=0, max_value=len(pages) - 1, step=1)
    page = pages[page_idx]
    config = parse_frontmatter(page)
    render_page_slide(page, schema, config)
    st.markdown(f"*Slide {page_idx + 1} of {len(pages)}*")

# Debug panel
with st.expander("📋 Debug: Raw data"):
    st.write(f"Database ID: `{selected_db_id}`")
    st.write(f"Schema: {json.dumps({k: v['type'] for k, v in schema.items()}, indent=2)}")

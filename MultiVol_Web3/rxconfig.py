from dotenv import load_dotenv
import os
# rxconfig.py
import reflex as rx
load_dotenv()
config = rx.Config(
    app_name="MultiVol2",
    cli_multivol_path=os.getenv("CLI_MULTIVOL_PATH"),
    is_container=os.getenv("IS_CONTAINER"),
    reflex_env_mode="prod",
    disable_plugins=['reflex.plugins.sitemap.SitemapPlugin']
)

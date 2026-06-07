from tools.file_tools import read_file, write_file, edit_file, list_files, search_in_files, delete_file
from tools.terminal_tools import run_command
from tools.browser_tools import open_url, click_element, type_text, screenshot, get_page_text
from tools.search_tools import web_search

ALL_TOOLS = [
    # File tools (same pattern as ai_agent/tools.py)
    read_file,
    write_file,
    edit_file,
    list_files,
    search_in_files,
    delete_file,
    # Terminal tools (NEW)
    run_command,
    # Browser tools (NEW)
    open_url,
    click_element,
    type_text,
    screenshot,
    get_page_text,
    # Search tools (NEW)
    web_search,
]

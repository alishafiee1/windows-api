import os
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.getenv("PORT", 4001))
BLOCKLIST_PATH = os.getenv("BLOCKLIST_PATH", "data/blocklist.txt")
CONFIRM_TIMEOUT = int(os.getenv("CONFIRM_TIMEOUT", 120))
SHELL = os.getenv("SHELL", "powershell")

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
SUPER_ADMIN_ID = int(os.environ["SUPER_ADMIN_ID"])

# SUPABASE_URL secret actually contains the service_role JWT (keys were swapped on entry)
# SUPABASE_KEY secret actually contains the anon JWT
# We derive the real project URL from SUPABASE_PROJECT_URL env var (set automatically)
# and use SUPABASE_URL (which holds service_role key) as the API key for full access
_raw_url = os.environ.get("SUPABASE_URL", "")
_project_url = os.environ.get("SUPABASE_PROJECT_URL", "")

# If SUPABASE_PROJECT_URL is set, use it as the real URL
if _project_url.startswith("http"):
    SUPABASE_URL = _project_url
    SUPABASE_KEY = _raw_url  # service_role key (was stored in URL slot)
else:
    SUPABASE_URL = _raw_url
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

PROVIDERS = {
    "smmglobe": {
        "name": "SMMGlobe",
        "api_url": os.environ.get("SMMGLOBE_API_URL", ""),
        "api_key": os.environ.get("SMMGLOBE_API_KEY", ""),
        "priority": 1,
    },
    "jap": {
        "name": "Just Another Panel",
        "api_url": os.environ.get("JAP_API_URL", ""),
        "api_key": os.environ.get("JAP_API_KEY", ""),
        "priority": 2,
    },
    "isp": {
        "name": "Indian Smart Panel",
        "api_url": os.environ.get("ISP_API_URL", ""),
        "api_key": os.environ.get("ISP_API_KEY", ""),
        "priority": 3,
    },
}

UPI_ID = os.environ.get("UPI_ID", "your-upi@paytm")
MIN_DEPOSIT = 50
MAX_DEPOSIT = 50000

SERVICE_SYNC_INTERVAL_HOURS = 1
ORDER_TRACK_INTERVAL_MINUTES = 5

KEEP_ALIVE_PORT = int(os.environ.get("PORT", 8080))

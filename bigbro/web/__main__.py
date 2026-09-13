"""Start the BigBro web dashboard:  python -m bigbro.web"""

from ..config import load_config
from .app import serve

if __name__ == "__main__":
    serve(load_config())

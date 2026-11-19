import sys
from pathlib import Path

# deixa "import main" e "import ptax" funcionarem rodando o pytest da raiz do repo
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

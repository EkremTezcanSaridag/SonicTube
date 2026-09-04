import sys
import os
from pathlib import Path

# Add project root to sys.path so imports work properly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.gui.app import SonicTubeApp

def main():
    app = SonicTubeApp()
    app.mainloop()

if __name__ == "__main__":
    main()

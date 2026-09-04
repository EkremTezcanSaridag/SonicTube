import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

def build():
    print("========================================")
    print("   SonicTube EXE Derleme Araci          ")
    print("========================================")

    import customtkinter
    ctk_dir = Path(customtkinter.__file__).resolve().parent
    print(f"[1/4] CustomTkinter dizini bulundu: {ctk_dir}")

    # Output directory
    dist_dir = ROOT_DIR / "dist"
    build_dir = ROOT_DIR / "build"
    assets_dir = ROOT_DIR / "assets"
    ico_path = assets_dir / "icon.ico"

    # PyInstaller arguments
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--name=SonicTube",
        f"--add-data={ctk_dir};customtkinter",
        "--clean",
        "-y",
    ]

    # Include Icon if exists
    if ico_path.exists():
        print(f"[2/4] Logo ve ikon pakete ekleniyor: {ico_path}")
        pyinstaller_args.append(f"--icon={ico_path}")
        pyinstaller_args.append(f"--add-data={assets_dir};assets")

    # Include bin directory if ffmpeg is downloaded
    bin_dir = ROOT_DIR / "bin"
    if bin_dir.exists() and any(bin_dir.iterdir()):
        print(f"[3/4] FFmpeg binaryleri pakete dahil ediliyor: {bin_dir}")
        pyinstaller_args.append(f"--add-data={bin_dir};bin")
    else:
        print("[3/4] bin/ dizini henuz bos (uygulama calisinca otomatik temin edebilir).")

    pyinstaller_args.append(str(ROOT_DIR / "src" / "main.py"))

    print("[4/4] PyInstaller calistiriliyor...")
    print("Komut:", " ".join(pyinstaller_args))
    
    result = subprocess.run(pyinstaller_args, cwd=str(ROOT_DIR))
    
    if result.returncode == 0:
        dist_app = dist_dir / "SonicTube"
        if bin_dir.exists():
            shutil.copytree(bin_dir, dist_app / "bin", dirs_exist_ok=True)
        if assets_dir.exists():
            shutil.copytree(assets_dir, dist_app / "assets", dirs_exist_ok=True)
            
        exe_path = dist_app / "SonicTube.exe"
        
        # Create or update Desktop shortcut with icon
        try:
            import win32com.client # if available or powershell
        except ImportError:
            pass

        print("\n========================================")
        print("[OK] TEBRIKLER! SonicTube EXE Basariyla Uretildi!")
        print(f"Konum: {exe_path}")
        print("========================================\n")
    else:
        print("\n[HATA] Derleme sirasinda bir sorun olustu.")

if __name__ == "__main__":
    build()

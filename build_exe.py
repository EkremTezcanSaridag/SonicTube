import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

def build():
    print("========================================")
    print("   SonicTube EXE Derleme Aracı          ")
    print("========================================")

    import customtkinter
    ctk_dir = Path(customtkinter.__file__).resolve().parent
    print(f"[1/3] CustomTkinter dizini bulundu: {ctk_dir}")

    # Output directory
    dist_dir = ROOT_DIR / "dist"
    build_dir = ROOT_DIR / "build"
    
    # PyInstaller arguments
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--name=SonicTube",
        f"--add-data={ctk_dir};customtkinter",
        "--clean",
        "-y",
    ]

    # Include bin directory if ffmpeg is downloaded
    bin_dir = ROOT_DIR / "bin"
    if bin_dir.exists() and any(bin_dir.iterdir()):
        print(f"[2/3] FFmpeg binaryleri pakete dahil ediliyor: {bin_dir}")
        pyinstaller_args.append(f"--add-data={bin_dir};bin")
    else:
        print("[2/3] bin/ dizini henüz boş (uygulama çalışınca otomatik temin edebilir).")

    pyinstaller_args.append(str(ROOT_DIR / "src" / "main.py"))

    print("[3/3] PyInstaller çalıştırılıyor...")
    print("Komut:", " ".join(pyinstaller_args))
    
    result = subprocess.run(pyinstaller_args, cwd=str(ROOT_DIR))
    
    if result.returncode == 0:
        exe_path = dist_dir / "SonicTube" / "SonicTube.exe"
        print("\n========================================")
        print("✓ TEBRİKLER! EXE Başarıyla Üretildi!")
        print(f"Konum: {exe_path}")
        print("========================================\n")
    else:
        print("\n❌ Hata: Derleme sırasında bir sorun oluştu.")

if __name__ == "__main__":
    build()

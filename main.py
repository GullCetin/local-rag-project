"""
main.py — Local RAG AI Assistant Giriş Noktası
===============================================
Kullanım:
  python main.py           # Streamlit web arayüzü (varsayılan)
  python main.py --ui cli  # Terminal arayüzü
"""

import sys
import os
import argparse
import subprocess


def run_streamlit() -> None:
    """Streamlit web arayüzünü başlatır."""
    app_path = os.path.join(os.path.dirname(__file__), "ui", "app.py")
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])


def run_cli_ui() -> None:
    """Terminal arayüzünü başlatır."""
    from ui.cli import run_cli
    run_cli()


def main() -> None:
    parser = argparse.ArgumentParser(description="Local RAG AI Assistant")
    parser.add_argument(
        "--ui",
        choices=["web", "cli"],
        default="web",
        help="Arayüz modu: web (Streamlit, varsayılan) veya cli",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="CLI modunda başlat (kısayol)",
    )
    args = parser.parse_args()

    if args.cli or args.ui == "cli":
        run_cli_ui()
    else:
        run_streamlit()


if __name__ == "__main__":
    main()
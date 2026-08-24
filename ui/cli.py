"""
ui/cli.py — Komut Satırı Arayüzü
==================================
Kullanıcının terminalde sorularını yazıp cevap aldığı basit CLI.

Çalıştır:
  python ui/cli.py

Veya main.py üzerinden:
  python main.py --ui cli
"""

import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rag.pipeline import RAGPipeline

logging.basicConfig(
    level=logging.WARNING,  # CLI'da sadece kritik loglar göster
    format="%(levelname)s: %(message)s",
)


BANNER = """
╔══════════════════════════════════════════════════════╗
║       Local RAG AI Assistant — CLI Modu              ║
║       Powered by Microsoft Foundry Local             ║
╚══════════════════════════════════════════════════════╝
Komutlar:
  'q' veya 'quit' → Çıkış
  'sources'       → Yüklü kaynak belgelerini listele
  'clear'         → Ekranı temizle
"""

SEPARATOR = "─" * 56


def print_response(response) -> None:
    """Cevabı ve kaynakları formatlı şekilde yazdırır."""
    print(f"\n{SEPARATOR}")
    print("🤖 Cevap:")
    print(f"\n{response.answer}\n")

    if response.unique_sources:
        print("📚 Kaynaklar:")
        for src in response.unique_sources:
            print(f"  • {src}")
    print(SEPARATOR)


def run_cli() -> None:
    """CLI döngüsünü başlatır."""
    print(BANNER)

    # Pipeline'ı yükle
    print("⏳ Modeller yükleniyor, lütfen bekleyin...\n")
    pipeline = RAGPipeline()
    try:
        pipeline.load()
    except Exception as e:
        print(f"\n❌ Model yükleme hatası: {e}")
        print("Foundry Local kurulumunu kontrol edin.")
        sys.exit(1)

    print("\n✅ Hazır! Sorularınızı yazabilirsiniz.\n")

    history = []

    while True:
        try:
            question = input("❓ Soru: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGüle güle!")
            break

        if not question:
            continue

        if question.lower() in ("q", "quit", "exit", "çıkış"):
            print("\nGüle güle!")
            break

        if question.lower() == "clear":
            os.system("cls" if os.name == "nt" else "clear")
            history = []
            continue

        if question.lower() == "sources":
            from db.manager import get_sources
            sources = get_sources()
            if sources:
                print("\n📚 Yüklü kaynaklar:")
                for s in sources:
                    print(f"  • {s}")
                print()
            else:
                print("\n⚠️  Henüz belge yüklenmemiş. 'python ingest.py' çalıştırın.\n")
            continue

        # Soru sor
        print("\n🔍 Aranıyor...")
        try:
            response = pipeline.ask(question, chat_history=history)
            print_response(response)

            # Geçmişe ekle
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": response.answer})
            # Son 6 mesajı tut
            if len(history) > 6:
                history = history[-6:]
        except ValueError as e:
            print(f"\n⚠️  {e}\n")
        except Exception as e:
            print(f"\n❌ Beklenmedik hata: {e}\n")


if __name__ == "__main__":
    run_cli()

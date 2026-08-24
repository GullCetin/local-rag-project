import sys
from foundry_local_sdk import Configuration, FoundryLocalManager

def main():
    print("Yapay zeka motoru başlatılıyor... Lütfen bekleyin.")
    
    config = Configuration(app_name="local-rag-test")
    
    FoundryLocalManager.initialize(config)
    
    manager = FoundryLocalManager.instance
    
    model = manager.catalog.get_model("phi-3.5-mini")
    if model is None:
        print("Hata: Belirtilen model katalogda bulunamadı!")
        return
    if not model.is_cached:
        print("Model yerel bilgisayarda bulunamadı. İndirme başlatılıyor...")
        def progress_callback(progress):
            print(f"İndiriliyor: %{round(progress)}")
        model.download(progress_callback)
    
    print("Model hafızaya yükleniyor...")
    model.load()
    
    chat_client = model.get_chat_client()
    
    print("\n--- Model Test Ediliyor ---")
    response = chat_client.complete_chat([
        {"role": "system", "content": "You are a helpful assistant. Keep your answer under 10 words."},
        {"role": "user", "content": "Hello, world!"}
    ])
    
    print(f"\nModelden Gelen Cevap: {response.choices[0].message.content}")

if __name__ == "__main__":
    main()
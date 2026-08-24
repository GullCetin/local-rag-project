import sys
# DÜZELTME: Hem Configuration hem de FoundryLocalManager'ı içe aktarıyoruz
from foundry_local_sdk import Configuration, FoundryLocalManager

def main():
    print("Yapay zeka motoru başlatılıyor... Lütfen bekleyin.")
    
    # 1. SDK için yapılandırma ayarını oluşturuyoruz
    config = Configuration(app_name="local-rag-test")
    
    # 2. SDK'yı bu yapılandırma ile başlatıyoruz (Initialize)
    FoundryLocalManager.initialize(config)
    
    # 3. Başlatılan yöneticinin tekil örneğini (instance) alıyoruz
    manager = FoundryLocalManager.instance
    
    # 4. Katalogdan en hafif model olan 'phi-3.5-mini'yi seçiyoruz
    model = manager.catalog.get_model("phi-3.5-mini")
    if model is None:
        print("Hata: Belirtilen model katalogda bulunamadı!")
        return
    # 5. Model bilgisayarda kayıtlı değilse indiriyoruz (yaklaşık 1-2 GB sürebilir)
    if not model.is_cached:
        print("Model yerel bilgisayarda bulunamadı. İndirme başlatılıyor...")
        # İndirme durumunu takip etmek için basit bir callback fonksiyonu
        def progress_callback(progress):
            print(f"İndiriliyor: %{round(progress)}")
        model.download(progress_callback)
    
    # 6. Modeli bilgisayarımızın hafızasına (RAM) yüklüyoruz
    print("Model hafızaya yükleniyor...")
    model.load()
    
    # 7. Model ile sohbet etmek için bir istemci (client) oluşturuyoruz
    chat_client = model.get_chat_client()
    
    # 8. Test sorumuzu soruyoruz (Hello Model Testi)
    print("\n--- Model Test Ediliyor ---")
    response = chat_client.complete_chat([
        {"role": "system", "content": "You are a helpful assistant. Keep your answer under 10 words."},
        {"role": "user", "content": "Hello, world!"}
    ])
    
    # Cevabı ekrana yazdırıyoruz
    print(f"\nModelden Gelen Cevap: {response.choices[0].message.content}")

if __name__ == "__main__":
    main()
# 🎤 Sunum Metni — Local RAG Asistanı (~2 Dakika)

---

## Konuşma Metni

Merhaba ben Nasibe Gül Çetin. Microsoft stajı kapsamında tamamen çevrimdışı çalışan, kurumsal belgeler üzerine soru sorulabilen bir yapay zeka asistanı geliştirdim.

Projenin çıkış noktası şu: kurumlar çok fazla iç doküman üretiyorlar ve bu verilere hızlıca ulaşmak istiyorlar aynı zamanda da bu verileri gizlilik gerekçesiyle buluta atmak istemiyorlar. 

Bu noktada RAG devreye giriyor. RAG, yani Retrieval-Augmented Generation; yapay zekanın ezberden konuşmak yerine yerine sorulan sorunun cevabını doğrudan harici belgeleri tarayıp bularak vermesini sağlayan bir yöntem.
Projem bu mimaride tamamen yerel çalışıyor. Tüm hesaplama kendi bilgisayarımda, hiçbir veri dışarı çıkmıyor. Microsoft Foundry Local'ı kullanıyorum — bu sayede hem embedding hem de LLM modeli RAM'de, yerel olarak çalışıyor.

Pipeline'a baktığımızda: Önce belgeler sisteme alınıyor — bu adıma ingestion diyoruz. Belgeler önce temizleniyor, gereksiz header'lar, içerik tabloları, tekrar eden uyarılar ayıklanıyor. Sonra anlamlı chunk'lara bölünüyor. Bölme işlemi sabit karakter sayısıyla değil, anlam bütünlüğüne göre yapılıyor; başlık-içerik ilişkisi korunuyor, istisnalar bağlı oldukları kuraldan koparılmıyor. Sonra her chunk `qwen3-embedding-0.6b` modeliyle vektöre çevriliyor ve SQLite'a yazılıyor.

Soru geldiğinde ise hibrit arama çalışıyor: hem semantik hem kelime bazlı arama yapıyor, cosine similarity ile skorlanıyor ve eşik altındakiler eleniyor. En ilgili üç chunk LLM'e veriliyor. LLM de yalnızca bu belgelerden konuşuyor — belgede yoksa "bu bilgi verilen belgelerde yer almıyor" diyor. Bu çok kritik; çünkü kurumsal kullanımda akıcı ama yanlış bir cevap, hiç cevap vermemekten daha tehlikeli.

Bu projeyi yaparken en çok zorlandığım şey chunking ve encoding konularıydı. Türkçe belgeler bazen farklı encoding'lerde geliyor, bunu otomatik tespit etmek için chardet kullandım. Chunking'de ise "kaç karakter?" sorusu değil, "bu parça tek başına anlamlı mı?" sorusu rehberim oldu. Overlap eklemek, başlıkları chunk'a dahil etmek, min-max sınırlar koymak — bunların hepsini iteratif olarak geliştirdim.

Bir diğer zorlandığım alan retrieval'ı dengelemek oldu. Çok az chunk getirince model eksik kalıyor, çok fazla getirince gürültüye batıyor. Hibrit ağırlıkları ve skor eşiği bunun için var.

Bu projeyi bitirdiğimde en değerli öğrendiklerim teknikten çok mimari kararlar oldu: kaliteyi belirleyen model seçimi değil, bilginin nasıl hazırlandığı ve nasıl getirildiğidir. Bu bakış açısı benim için en büyük kazanım oldu.

Teşekkürler.

---

> **Süre tahmini:** ~1 dakika 50 saniye (normal konuşma hızında)

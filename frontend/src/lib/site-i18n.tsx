"use client";

/*
 * Translations for the public website.
 *
 * Keyed by the English text itself: pages render <S t="English text" />
 * (pre-rendered in English, then shown in the visitor's language: the one
 * they picked, else their browser's). Missing entries simply stay English,
 * so new copy can ship before it is translated. Order: es, fr, de, tr.
 * Use {name} placeholders with `vars` for numbers and names.
 */

import { useI18n } from "@/lib/i18n";

type Row = [es: string, fr: string, de: string, tr: string];

const SITE: Record<string, Row> = {
  // --- header, footer, shared ---
  "Templates": ["Plantillas", "Modèles", "Vorlagen", "Şablonlar"],
  "Integrations": ["Integraciones", "Intégrations", "Integrationen", "Entegrasyonlar"],
  "Pricing": ["Precios", "Tarifs", "Preise", "Fiyatlar"],
  "Security": ["Seguridad", "Sécurité", "Sicherheit", "Güvenlik"],
  "Sign in": ["Iniciar sesión", "Se connecter", "Anmelden", "Giriş yap"],
  "Start free": ["Empieza gratis", "Commencer gratuitement", "Kostenlos starten", "Ücretsiz başla"],
  "Open the app": ["Abrir la app", "Ouvrir l'application", "App öffnen", "Uygulamayı aç"],
  "Menu": ["Menú", "Menu", "Menü", "Menü"],
  "Product": ["Producto", "Produit", "Produkt", "Ürün"],
  "Account": ["Cuenta", "Compte", "Konto", "Hesap"],
  "Create an account": ["Crear una cuenta", "Créer un compte", "Konto erstellen", "Hesap oluştur"],
  "Report abuse": ["Denunciar abuso", "Signaler un abus", "Missbrauch melden", "Kötüye kullanımı bildir"],
  "Language": ["Idioma", "Langue", "Sprache", "Dil"],
  "Tell it what you want done. AutoFlow builds the workflow, connects your apps, and runs it for you.": [
    "Dile lo que quieres hacer. AutoFlow crea el flujo, conecta tus apps y lo ejecuta por ti.",
    "Dites-lui ce que vous voulez faire. AutoFlow crée le flux, connecte vos applis et l'exécute pour vous.",
    "Sagen Sie, was erledigt werden soll. AutoFlow baut den Workflow, verbindet Ihre Apps und führt ihn für Sie aus.",
    "Ne yapılmasını istediğinizi söyleyin. AutoFlow iş akışını kurar, uygulamalarınızı bağlar ve sizin için çalıştırır.",
  ],
  "Your first automation is five minutes away.": [
    "Tu primera automatización está a cinco minutos.",
    "Votre première automatisation est à cinq minutes.",
    "Ihre erste Automatisierung ist fünf Minuten entfernt.",
    "İlk otomasyonunuz beş dakika uzakta.",
  ],
  "Free to start. Test with sample data first: nothing reaches your customers until you switch it on.": [
    "Gratis para empezar. Prueba primero con datos de ejemplo: nada llega a tus clientes hasta que lo actives.",
    "Gratuit pour commencer. Testez d'abord avec des données d'exemple : rien n'atteint vos clients avant l'activation.",
    "Kostenlos zum Start. Erst mit Beispieldaten testen: Nichts erreicht Ihre Kunden, bevor Sie einschalten.",
    "Başlamak ücretsiz. Önce örnek verilerle test edin: siz açana kadar müşterilerinize hiçbir şey ulaşmaz.",
  ],

  // --- home ---
  "Automation for online shops": ["Automatización para tiendas online", "L'automatisation pour les boutiques en ligne", "Automatisierung für Onlineshops", "Online mağazalar için otomasyon"],
  "Tell it what you want done.": ["Dile lo que quieres hacer.", "Dites-lui ce que vous voulez faire.", "Sagen Sie, was erledigt werden soll.", "Ne yapılmasını istediğinizi söyleyin."],
  "AutoFlow builds the workflow, connects your store and apps, and runs it for you. A person stays in the loop for anything that matters.": [
    "AutoFlow crea el flujo, conecta tu tienda y tus apps y lo ejecuta por ti. Una persona sigue al tanto de todo lo importante.",
    "AutoFlow crée le flux, connecte votre boutique et vos applis, et l'exécute pour vous. Une personne garde la main sur tout ce qui compte.",
    "AutoFlow baut den Workflow, verbindet Ihren Shop und Ihre Apps und führt ihn aus. Bei allem Wichtigen entscheidet ein Mensch.",
    "AutoFlow iş akışını kurar, mağazanızı ve uygulamalarınızı bağlar ve sizin için çalıştırır. Önemli her şeyde bir insan devrede kalır.",
  ],
  "See templates": ["Ver plantillas", "Voir les modèles", "Vorlagen ansehen", "Şablonları gör"],
  "Free plan available. No card needed to try it.": [
    "Plan gratuito disponible. No necesitas tarjeta para probarlo.",
    "Offre gratuite disponible. Aucune carte nécessaire pour essayer.",
    "Kostenloser Tarif verfügbar. Zum Testen keine Karte nötig.",
    "Ücretsiz plan var. Denemek için kart gerekmez.",
  ],
  "Works with": ["Funciona con", "Fonctionne avec", "Funktioniert mit", "Şunlarla çalışır"],
  "Gmail and any email": ["Gmail y cualquier correo", "Gmail et toute messagerie", "Gmail und jede E-Mail", "Gmail ve tüm e-postalar"],
  "Any REST API": ["Cualquier API REST", "Toute API REST", "Jede REST-API", "Her REST API"],
  "Live in three steps": ["En marcha en tres pasos", "En ligne en trois étapes", "In drei Schritten live", "Üç adımda canlıda"],
  "Describe it": ["Descríbelo", "Décrivez-le", "Beschreiben Sie es", "Anlatın"],
  "Type what should happen, in your own words. AutoFlow asks about anything unclear.": [
    "Escribe lo que debe pasar, con tus palabras. AutoFlow pregunta lo que no esté claro.",
    "Écrivez ce qui doit se passer, avec vos mots. AutoFlow pose des questions sur ce qui n'est pas clair.",
    "Schreiben Sie in eigenen Worten, was passieren soll. AutoFlow fragt nach, wenn etwas unklar ist.",
    "Ne olması gerektiğini kendi sözlerinizle yazın. AutoFlow belirsiz olanı sorar.",
  ],
  "Test it safely": ["Pruébalo sin riesgos", "Testez sans risque", "Sicher testen", "Güvenle test edin"],
  "See every step on a diagram and run it with an example order. Nothing reaches customers.": [
    "Ve cada paso en un diagrama y pruébalo con un pedido de ejemplo. Nada llega a los clientes.",
    "Voyez chaque étape sur un schéma et testez avec une commande d'exemple. Rien n'atteint les clients.",
    "Sehen Sie jeden Schritt im Diagramm und testen Sie mit einer Beispielbestellung. Nichts erreicht Kunden.",
    "Her adımı bir şemada görün ve örnek bir siparişle çalıştırın. Müşterilere hiçbir şey ulaşmaz.",
  ],
  "Switch it on": ["Actívalo", "Activez-le", "Einschalten", "Açın"],
  "Publish, and it runs on real orders, with your approval for anything that matters.": [
    "Publica y funcionará con pedidos reales, con tu aprobación para todo lo importante.",
    "Publiez, et il traite les vraies commandes, avec votre accord pour tout ce qui compte.",
    "Veröffentlichen, und er läuft mit echten Bestellungen, mit Ihrer Freigabe für alles Wichtige.",
    "Yayınlayın; önemli her şey için onayınızla gerçek siparişlerde çalışır.",
  ],
  "Powerful underneath. Simple on top.": ["Potente por dentro. Sencillo por fuera.", "Puissant dessous. Simple dessus.", "Leistungsstark im Kern. Einfach in der Bedienung.", "İçi güçlü. Kullanımı basit."],
  "The reliability of an engineering tool, explained in words a shop owner uses.": [
    "La fiabilidad de una herramienta técnica, explicada con las palabras de un dueño de tienda.",
    "La fiabilité d'un outil d'ingénieur, expliquée avec les mots d'un commerçant.",
    "Die Zuverlässigkeit eines Profi-Werkzeugs, erklärt in der Sprache von Shopbetreibern.",
    "Bir mühendislik aracının güvenilirliği, bir mağaza sahibinin kullandığı sözcüklerle.",
  ],
  "Built from plain words": ["Creado con palabras sencillas", "Créé avec des mots simples", "Aus einfachen Worten gebaut", "Sade sözcüklerle kurulur"],
  "The AI builder turns a sentence into a working workflow you can read, edit and test.": [
    "El creador con IA convierte una frase en un flujo que puedes leer, editar y probar.",
    "Le créateur IA transforme une phrase en un flux que vous pouvez lire, modifier et tester.",
    "Der KI-Baukasten macht aus einem Satz einen Workflow, den Sie lesen, bearbeiten und testen können.",
    "Yapay zekâ oluşturucusu bir cümleyi okuyup düzenleyebileceğiniz ve test edebileceğiniz bir iş akışına çevirir.",
  ],
  "You approve what matters": ["Tú apruebas lo importante", "Vous approuvez ce qui compte", "Sie geben Wichtiges frei", "Önemli olanı siz onaylarsınız"],
  "Emails to customers wait for a tap of approval. One emergency stop pauses everything.": [
    "Los correos a clientes esperan tu aprobación. Una parada de emergencia lo pausa todo.",
    "Les e-mails aux clients attendent votre accord. Un arrêt d'urgence met tout en pause.",
    "E-Mails an Kunden warten auf Ihre Freigabe. Ein Not-Aus pausiert alles.",
    "Müşterilere giden e-postalar onayınızı bekler. Tek bir acil durdurma her şeyi duraklatır.",
  ],
  "Dependable by design": ["Fiable por diseño", "Fiable par conception", "Zuverlässig von Grund auf", "Tasarımı gereği güvenilir"],
  "Automatic retries, time limits, and protection against doing the same thing twice.": [
    "Reintentos automáticos, límites de tiempo y protección para no hacer nada dos veces.",
    "Nouvelles tentatives automatiques, délais et protection contre les doublons.",
    "Automatische Wiederholungen, Zeitlimits und Schutz davor, etwas doppelt zu tun.",
    "Otomatik yeniden denemeler, süre sınırları ve aynı şeyi iki kez yapmaya karşı koruma.",
  ],
  "See exactly what happened": ["Mira exactamente qué pasó", "Voyez exactement ce qui s'est passé", "Sehen Sie genau, was passiert ist", "Tam olarak ne olduğunu görün"],
  "Every run explained step by step, in plain language. Retry a failed step in one click.": [
    "Cada ejecución explicada paso a paso, en lenguaje claro. Reintenta un paso fallido con un clic.",
    "Chaque exécution expliquée étape par étape, en langage clair. Relancez une étape échouée en un clic.",
    "Jeder Lauf Schritt für Schritt in klarer Sprache erklärt. Fehlgeschlagene Schritte mit einem Klick wiederholen.",
    "Her çalıştırma adım adım, sade bir dille anlatılır. Başarısız bir adımı tek tıkla yeniden deneyin.",
  ],
  "Approve from your phone": ["Aprueba desde el móvil", "Approuvez depuis votre téléphone", "Vom Handy aus freigeben", "Telefonunuzdan onaylayın"],
  "Add it to your home screen and clear approvals in seconds, wherever you are.": [
    "Añádelo a tu pantalla de inicio y resuelve aprobaciones en segundos, estés donde estés.",
    "Ajoutez-le à votre écran d'accueil et traitez les approbations en quelques secondes, où que vous soyez.",
    "Zum Startbildschirm hinzufügen und Freigaben in Sekunden erledigen, wo immer Sie sind.",
    "Ana ekranınıza ekleyin ve onayları nerede olursanız olun saniyeler içinde halledin.",
  ],
  "Made for teams": ["Hecho para equipos", "Conçu pour les équipes", "Für Teams gemacht", "Ekipler için yapıldı"],
  "Invite your team with roles, keep an activity log, and secure sign-in with two-factor login.": [
    "Invita a tu equipo con roles, guarda un registro de actividad y protege el acceso con verificación en dos pasos.",
    "Invitez votre équipe avec des rôles, gardez un journal d'activité et sécurisez la connexion en deux étapes.",
    "Laden Sie Ihr Team mit Rollen ein, führen Sie ein Aktivitätsprotokoll und sichern Sie die Anmeldung mit zwei Faktoren.",
    "Ekibinizi rollerle davet edin, etkinlik günlüğü tutun ve iki adımlı girişle oturumu güvenceye alın.",
  ],
  "Start from a ready-made automation": ["Empieza con una automatización lista", "Partez d'une automatisation prête", "Mit einer fertigen Automatisierung starten", "Hazır bir otomasyonla başlayın"],
  "Built for the jobs online shops repeat every day.": [
    "Pensadas para las tareas que las tiendas online repiten cada día.",
    "Pensées pour les tâches que les boutiques en ligne répètent chaque jour.",
    "Für die Aufgaben, die Onlineshops jeden Tag wiederholen.",
    "Online mağazaların her gün tekrarladığı işler için.",
  ],
  "All templates →": ["Todas las plantillas →", "Tous les modèles →", "Alle Vorlagen →", "Tüm şablonlar →"],
  "Order → invoice": ["Pedido → factura", "Commande → facture", "Bestellung → Rechnung", "Sipariş → fatura"],
  "A numbered PDF invoice for every paid order, emailed after your OK.": [
    "Una factura PDF numerada por cada pedido pagado, enviada tras tu visto bueno.",
    "Une facture PDF numérotée pour chaque commande payée, envoyée après votre accord.",
    "Eine nummerierte PDF-Rechnung für jede bezahlte Bestellung, versendet nach Ihrem OK.",
    "Ödenen her sipariş için numaralı bir PDF fatura, onayınızdan sonra gönderilir.",
  ],
  "Abandoned-cart follow-up": ["Seguimiento de carritos abandonados", "Relance des paniers abandonnés", "Erinnerung bei abgebrochenem Kauf", "Terk edilen sepet takibi"],
  "A friendly reminder an hour later, skipped if they already bought.": [
    "Un recordatorio amable una hora después, que se omite si ya compraron.",
    "Un rappel aimable une heure plus tard, ignoré s'ils ont déjà acheté.",
    "Eine freundliche Erinnerung eine Stunde später, entfällt, wenn schon gekauft wurde.",
    "Bir saat sonra nazik bir hatırlatma; zaten satın aldılarsa atlanır.",
  ],
  "Review reply assistant": ["Asistente de respuestas a reseñas", "Assistant de réponse aux avis", "Assistent für Bewertungsantworten", "Yorum yanıt asistanı"],
  "AI drafts a personal reply to each review; you approve before it goes.": [
    "La IA redacta una respuesta personal a cada reseña; tú apruebas antes de enviarla.",
    "L'IA rédige une réponse personnelle à chaque avis ; vous approuvez avant l'envoi.",
    "Die KI entwirft eine persönliche Antwort auf jede Bewertung; Sie geben sie vor dem Versand frei.",
    "Yapay zekâ her yoruma kişisel bir yanıt taslağı hazırlar; gönderilmeden önce siz onaylarsınız.",
  ],
  "Your store, your customers, your data": ["Tu tienda, tus clientes, tus datos", "Votre boutique, vos clients, vos données", "Ihr Shop, Ihre Kunden, Ihre Daten", "Mağazanız, müşterileriniz, verileriniz"],
  "Encrypted credentials, separate workspaces, signed webhooks, approvals, an activity log, and export or delete your data at any time.": [
    "Credenciales cifradas, espacios separados, webhooks firmados, aprobaciones, registro de actividad y exporta o borra tus datos cuando quieras.",
    "Identifiants chiffrés, espaces séparés, webhooks signés, approbations, journal d'activité, et export ou suppression de vos données à tout moment.",
    "Verschlüsselte Zugangsdaten, getrennte Arbeitsbereiche, signierte Webhooks, Freigaben, ein Aktivitätsprotokoll und Export oder Löschung Ihrer Daten jederzeit.",
    "Şifreli kimlik bilgileri, ayrı çalışma alanları, imzalı webhook'lar, onaylar, etkinlik günlüğü ve verilerinizi istediğiniz zaman dışa aktarma veya silme.",
  ],
  "How we keep it safe": ["Cómo lo protegemos", "Comment nous le protégeons", "So schützen wir es", "Nasıl güvende tutuyoruz"],

  // --- "type a task" demo ---
  "What should happen?": ["¿Qué debería pasar?", "Que doit-il se passer ?", "Was soll passieren?", "Ne olmalı?"],
  "Show me": ["Muéstramelo", "Montrez-moi", "Zeig es mir", "Göster"],
  "You approve": ["Tú apruebas", "Vous approuvez", "Sie geben frei", "Siz onaylarsınız"],
  "A preview. After sign-up, the AI drafts the real workflow from your words.": [
    "Una vista previa. Tras registrarte, la IA redacta el flujo real a partir de tus palabras.",
    "Un aperçu. Après l'inscription, l'IA rédige le vrai flux à partir de vos mots.",
    "Eine Vorschau. Nach der Anmeldung entwirft die KI den echten Workflow aus Ihren Worten.",
    "Bir önizleme. Kayıttan sonra yapay zekâ gerçek iş akışını sizin sözlerinizden hazırlar.",
  ],
  "Build this for real": ["Créalo de verdad", "Créez-le pour de vrai", "Jetzt wirklich bauen", "Bunu gerçekten kur"],
  "When an order is paid, email the customer a PDF invoice": [
    "Cuando se pague un pedido, envía al cliente una factura en PDF",
    "Quand une commande est payée, envoyer au client une facture PDF",
    "Wenn eine Bestellung bezahlt ist, dem Kunden eine PDF-Rechnung mailen",
    "Bir sipariş ödendiğinde müşteriye PDF fatura gönder",
  ],
  "Remind people who leave items in their cart": [
    "Recuerda a quien deja productos en el carrito",
    "Relancer ceux qui laissent des articles dans leur panier",
    "Leute erinnern, die Artikel im Warenkorb lassen",
    "Sepetinde ürün bırakanlara hatırlat",
  ],
  "Draft replies to new product reviews for me to approve": [
    "Redacta respuestas a nuevas reseñas para que yo las apruebe",
    "Rédiger des réponses aux nouveaux avis, à faire valider par moi",
    "Antworten auf neue Bewertungen entwerfen, die ich freigebe",
    "Yeni ürün yorumlarına onaylamam için yanıt taslakları hazırla",
  ],
  "Put supplier invoices from my inbox into a spreadsheet": [
    "Pasa las facturas de proveedores de mi correo a una hoja de cálculo",
    "Mettre les factures fournisseurs de ma boîte mail dans un tableur",
    "Lieferantenrechnungen aus meinem Postfach in eine Tabelle übernehmen",
    "Gelen kutumdaki tedarikçi faturalarını bir tabloya aktar",
  ],
  "A customer starts a checkout": ["Un cliente empieza a pagar", "Un client commence un paiement", "Ein Kunde beginnt den Bezahlvorgang", "Bir müşteri ödemeye başlar"],
  "Wait 1 hour": ["Esperar 1 hora", "Attendre 1 heure", "1 Stunde warten", "1 saat bekle"],
  "Check whether they already bought": ["Comprobar si ya compró", "Vérifier s'il a déjà acheté", "Prüfen, ob schon gekauft wurde", "Zaten satın aldı mı kontrol et"],
  "Email a friendly reminder with their cart link": ["Enviar un recordatorio amable con el enlace al carrito", "Envoyer un rappel aimable avec le lien du panier", "Freundliche Erinnerung mit Warenkorb-Link senden", "Sepet bağlantısıyla nazik bir hatırlatma gönder"],
  "A new product review arrives": ["Llega una reseña nueva", "Un nouvel avis arrive", "Eine neue Bewertung kommt an", "Yeni bir ürün yorumu gelir"],
  "AI reads the review and its tone": ["La IA lee la reseña y su tono", "L'IA lit l'avis et son ton", "Die KI liest die Bewertung und ihren Ton", "Yapay zekâ yorumu ve tonunu okur"],
  "AI drafts a polite, personal reply": ["La IA redacta una respuesta amable y personal", "L'IA rédige une réponse polie et personnelle", "Die KI entwirft eine höfliche, persönliche Antwort", "Yapay zekâ kibar, kişisel bir yanıt hazırlar"],
  "Send the reply to the reviewer": ["Enviar la respuesta a quien escribió", "Envoyer la réponse à l'auteur", "Antwort an den Verfasser senden", "Yanıtı yorumu yazana gönder"],
  "A supplier invoice lands in your inbox": ["Llega una factura de proveedor a tu correo", "Une facture fournisseur arrive dans votre boîte", "Eine Lieferantenrechnung landet im Postfach", "Gelen kutunuza bir tedarikçi faturası düşer"],
  "AI reads the PDF: supplier, date, total, tax": ["La IA lee el PDF: proveedor, fecha, total, impuestos", "L'IA lit le PDF : fournisseur, date, total, taxes", "Die KI liest das PDF: Lieferant, Datum, Summe, Steuer", "Yapay zekâ PDF'i okur: tedarikçi, tarih, toplam, vergi"],
  "Add a row to your bookkeeping spreadsheet": ["Añadir una fila a tu hoja de contabilidad", "Ajouter une ligne à votre tableau comptable", "Eine Zeile in Ihre Buchhaltungstabelle einfügen", "Muhasebe tablonuza bir satır ekle"],
  "An order is paid in your store": ["Se paga un pedido en tu tienda", "Une commande est payée dans votre boutique", "Eine Bestellung wird in Ihrem Shop bezahlt", "Mağazanızda bir sipariş ödenir"],
  "Create a numbered PDF invoice": ["Crear una factura PDF numerada", "Créer une facture PDF numérotée", "Eine nummerierte PDF-Rechnung erstellen", "Numaralı bir PDF fatura oluştur"],
  "Record the order and customer": ["Registrar el pedido y el cliente", "Enregistrer la commande et le client", "Bestellung und Kunden erfassen", "Siparişi ve müşteriyi kaydet"],
  "Email the invoice to the customer": ["Enviar la factura al cliente", "Envoyer la facture au client", "Rechnung an den Kunden mailen", "Faturayı müşteriye gönder"],
  "Something happens in one of your apps": ["Pasa algo en una de tus apps", "Quelque chose se passe dans une de vos applis", "In einer Ihrer Apps passiert etwas", "Uygulamalarınızdan birinde bir şey olur"],
  "AI works out what it means": ["La IA entiende qué significa", "L'IA comprend ce que cela signifie", "Die KI erkennt, was es bedeutet", "Yapay zekâ ne anlama geldiğini çıkarır"],
  "Do what you described": ["Hacer lo que describiste", "Faire ce que vous avez décrit", "Tun, was Sie beschrieben haben", "Anlattığınızı yap"],
  "Let you check anything that goes to a customer": ["Dejarte revisar todo lo que va a un cliente", "Vous laisser vérifier tout ce qui part vers un client", "Sie alles prüfen lassen, was an Kunden geht", "Müşteriye giden her şeyi kontrol etmenize izin ver"],

  // --- pricing ---
  "Pay for work that gets done": ["Paga por el trabajo hecho", "Payez le travail accompli", "Zahlen Sie für erledigte Arbeit", "Yapılan iş için ödeyin"],
  "Start free. Upgrade when your automations are saving you time. Prices in US dollars.": [
    "Empieza gratis. Cambia de plan cuando tus automatizaciones te ahorren tiempo. Precios en dólares estadounidenses.",
    "Commencez gratuitement. Passez à l'offre supérieure quand vos automatisations vous font gagner du temps. Prix en dollars US.",
    "Kostenlos starten. Upgraden, wenn Ihre Automatisierungen Zeit sparen. Preise in US-Dollar.",
    "Ücretsiz başlayın. Otomasyonlarınız zaman kazandırınca yükseltin. Fiyatlar ABD doları cinsindendir.",
  ],
  "Questions": ["Preguntas", "Questions", "Fragen", "Sorular"],
  "What counts as a task?": ["¿Qué cuenta como tarea?", "Qu'est-ce qu'une tâche ?", "Was zählt als Aufgabe?", "Görev olarak ne sayılır?"],
  "A step that succeeds and does something in an app or with AI, for example sending an email or creating an invoice. Failed steps, retries and test runs are free.": [
    "Un paso que sale bien y hace algo en una app o con IA, por ejemplo enviar un correo o crear una factura. Los pasos fallidos, reintentos y pruebas son gratis.",
    "Une étape réussie qui agit dans une appli ou avec l'IA, par exemple envoyer un e-mail ou créer une facture. Les échecs, nouvelles tentatives et tests sont gratuits.",
    "Ein erfolgreicher Schritt, der in einer App oder mit KI etwas tut, z. B. eine E-Mail senden oder eine Rechnung erstellen. Fehlgeschlagene Schritte, Wiederholungen und Tests sind kostenlos.",
    "Bir uygulamada ya da yapay zekâyla bir şey yapan başarılı bir adım; örneğin e-posta göndermek veya fatura oluşturmak. Başarısız adımlar, yeniden denemeler ve testler ücretsizdir.",
  ],
  "What happens if I run out of tasks?": ["¿Qué pasa si me quedo sin tareas?", "Que se passe-t-il si je n'ai plus de tâches ?", "Was passiert, wenn meine Aufgaben aufgebraucht sind?", "Görevlerim biterse ne olur?"],
  "You choose: keep running and pay for what you use, or pause billable steps at the limit. You get an alert before you get there.": [
    "Tú eliges: seguir y pagar lo que uses, o pausar los pasos facturables al llegar al límite. Recibes un aviso antes.",
    "Vous choisissez : continuer et payer ce que vous utilisez, ou suspendre les étapes facturables à la limite. Vous êtes prévenu avant.",
    "Sie entscheiden: weiterlaufen und nach Verbrauch zahlen oder abrechenbare Schritte am Limit pausieren. Vorher bekommen Sie eine Warnung.",
    "Siz seçersiniz: çalışmaya devam edip kullandığınız kadar ödemek ya da sınırda ücretli adımları duraklatmak. Oraya varmadan uyarı alırsınız.",
  ],
  "Can I change or cancel my plan?": ["¿Puedo cambiar o cancelar mi plan?", "Puis-je changer ou annuler mon offre ?", "Kann ich meinen Tarif ändern oder kündigen?", "Planımı değiştirebilir veya iptal edebilir miyim?"],
  "Yes, at any time from Plan & usage. Changes take effect right after payment.": [
    "Sí, cuando quieras desde Plan y uso. Los cambios se aplican justo después del pago.",
    "Oui, à tout moment depuis Offre et utilisation. Les changements s'appliquent juste après le paiement.",
    "Ja, jederzeit unter Tarif & Nutzung. Änderungen gelten direkt nach der Zahlung.",
    "Evet, istediğiniz zaman Plan ve kullanım bölümünden. Değişiklikler ödemeden hemen sonra geçerli olur.",
  ],
  "Do I need a card to start?": ["¿Necesito tarjeta para empezar?", "Ai-je besoin d'une carte pour commencer ?", "Brauche ich zum Start eine Karte?", "Başlamak için kart gerekir mi?"],
  "No. The free plan is enough to build, test and run your first automations.": [
    "No. El plan gratuito basta para crear, probar y ejecutar tus primeras automatizaciones.",
    "Non. L'offre gratuite suffit pour créer, tester et lancer vos premières automatisations.",
    "Nein. Der kostenlose Tarif reicht, um Ihre ersten Automatisierungen zu bauen, zu testen und zu nutzen.",
    "Hayır. Ücretsiz plan ilk otomasyonlarınızı kurmak, test etmek ve çalıştırmak için yeterli.",
  ],
  "Good place to start": ["Buen punto de partida", "Bon point de départ", "Guter Einstieg", "Başlamak için iyi"],
  "/ month": ["/ mes", "/ mois", "/ Monat", "/ ay"],
  "Custom": ["A medida", "Sur mesure", "Individuell", "Özel"],
  "Talk to us": ["Habla con nosotros", "Contactez-nous", "Sprechen Sie mit uns", "Bizimle konuşun"],
  "Choose {plan}": ["Elegir {plan}", "Choisir {plan}", "{plan} wählen", "{plan} seç"],
  "{n} tasks a month": ["{n} tareas al mes", "{n} tâches par mois", "{n} Aufgaben im Monat", "Ayda {n} görev"],
  "Unlimited tasks a month": ["Tareas ilimitadas al mes", "Tâches illimitées par mois", "Unbegrenzte Aufgaben im Monat", "Ayda sınırsız görev"],
  "{n} workflows": ["{n} flujos", "{n} flux", "{n} Workflows", "{n} iş akışı"],
  "Unlimited workflows": ["Flujos ilimitados", "Flux illimités", "Unbegrenzte Workflows", "Sınırsız iş akışı"],
  "1 team seat": ["1 puesto de equipo", "1 siège", "1 Teamplatz", "1 ekip koltuğu"],
  "{n} team seats": ["{n} puestos de equipo", "{n} sièges", "{n} Teamplätze", "{n} ekip koltuğu"],
  "Unlimited team seats": ["Puestos ilimitados", "Sièges illimités", "Unbegrenzte Teamplätze", "Sınırsız ekip koltuğu"],
  "Trying it out": ["Para probar", "Pour essayer", "Zum Ausprobieren", "Denemek için"],
  "Solo owners and micro-businesses": ["Autónomos y microempresas", "Indépendants et micro-entreprises", "Einzelunternehmer und Kleinstbetriebe", "Tek kişilik işletmeler ve mikro işletmeler"],
  "Small teams": ["Equipos pequeños", "Petites équipes", "Kleine Teams", "Küçük ekipler"],
  "Mid-sized companies": ["Empresas medianas", "Entreprises de taille moyenne", "Mittelgroße Unternehmen", "Orta ölçekli şirketler"],
  "Custom terms; set up by our team": ["Condiciones a medida; lo configura nuestro equipo", "Conditions sur mesure ; mis en place par notre équipe", "Individuelle Bedingungen; von unserem Team eingerichtet", "Özel koşullar; ekibimiz kurar"],

  // --- templates ---
  "Ready-made automations": ["Automatizaciones listas", "Automatisations prêtes à l'emploi", "Fertige Automatisierungen", "Hazır otomasyonlar"],
  "Install one in a click, test it with an example, then switch it on. Every template can be edited afterwards.": [
    "Instala una con un clic, pruébala con un ejemplo y actívala. Todas las plantillas se pueden editar después.",
    "Installez-en un en un clic, testez-le avec un exemple, puis activez-le. Chaque modèle reste modifiable.",
    "Mit einem Klick installieren, mit einem Beispiel testen, dann einschalten. Jede Vorlage lässt sich später anpassen.",
    "Tek tıkla kurun, bir örnekle test edin, sonra açın. Her şablon sonradan düzenlenebilir.",
  ],
  "Don't see yours? Describe it in a sentence.": ["¿No ves la tuya? Descríbela en una frase.", "Vous ne trouvez pas le vôtre ? Décrivez-le en une phrase.", "Ihre ist nicht dabei? Beschreiben Sie sie in einem Satz.", "Sizinkini göremiyor musunuz? Tek cümleyle anlatın."],
  "Early access": ["Acceso anticipado", "Accès anticipé", "Früher Zugang", "Erken erişim"],
  "What it needs": ["Qué necesita", "Ce qu'il faut", "Was es braucht", "Gerekenler"],
  "Use this template →": ["Usar esta plantilla →", "Utiliser ce modèle →", "Diese Vorlage nutzen →", "Bu şablonu kullan →"],

  // --- integrations ---
  "Connects to the tools you already use": ["Se conecta con las herramientas que ya usas", "Se connecte aux outils que vous utilisez déjà", "Verbindet sich mit Ihren vorhandenen Tools", "Zaten kullandığınız araçlara bağlanır"],
  "Credentials are encrypted and never shown again. Disconnect any app at any time.": [
    "Las credenciales se cifran y no se vuelven a mostrar. Desconecta cualquier app cuando quieras.",
    "Les identifiants sont chiffrés et jamais réaffichés. Déconnectez une appli à tout moment.",
    "Zugangsdaten werden verschlüsselt und nie wieder angezeigt. Jede App lässt sich jederzeit trennen.",
    "Kimlik bilgileri şifrelenir ve bir daha gösterilmez. Herhangi bir uygulamanın bağlantısını istediğiniz zaman kesin.",
  ],
  "Your store": ["Tu tienda", "Votre boutique", "Ihr Shop", "Mağazanız"],
  "Paid orders, checkouts and more arrive as signed webhooks. Tag orders and add notes through the Admin API.": [
    "Pedidos pagados, pagos iniciados y más llegan como webhooks firmados. Etiqueta pedidos y añade notas con la API de administración.",
    "Commandes payées, paiements et plus arrivent en webhooks signés. Étiquetez les commandes et ajoutez des notes via l'API Admin.",
    "Bezahlte Bestellungen, Checkouts und mehr kommen als signierte Webhooks. Bestellungen über die Admin-API taggen und mit Notizen versehen.",
    "Ödenen siparişler, ödeme başlangıçları ve daha fazlası imzalı webhook olarak gelir. Admin API ile siparişleri etiketleyin ve not ekleyin.",
  ],
  "Order webhooks with WooCommerce signatures, plus order notes and status updates through the REST API.": [
    "Webhooks de pedidos con firmas de WooCommerce, además de notas y cambios de estado con la API REST.",
    "Webhooks de commande avec signatures WooCommerce, plus notes et changements de statut via l'API REST.",
    "Bestell-Webhooks mit WooCommerce-Signaturen sowie Notizen und Statusänderungen über die REST-API.",
    "WooCommerce imzalı sipariş webhook'ları, ayrıca REST API ile sipariş notları ve durum güncellemeleri.",
  ],
  "Email": ["Correo", "E-mail", "E-Mail", "E-posta"],
  "Gmail and any email account": ["Gmail y cualquier cuenta de correo", "Gmail et toute adresse e-mail", "Gmail und jedes E-Mail-Konto", "Gmail ve her e-posta hesabı"],
  "Send from your own address, and start workflows when an email or invoice lands in a folder.": [
    "Envía desde tu propia dirección y arranca flujos cuando llegue un correo o una factura a una carpeta.",
    "Envoyez depuis votre propre adresse et lancez des flux quand un e-mail ou une facture arrive dans un dossier.",
    "Von Ihrer eigenen Adresse senden und Workflows starten, wenn eine E-Mail oder Rechnung in einem Ordner landet.",
    "Kendi adresinizden gönderin ve bir klasöre e-posta ya da fatura geldiğinde iş akışlarını başlatın.",
  ],
  "Data and spreadsheets": ["Datos y hojas de cálculo", "Données et tableurs", "Daten und Tabellen", "Veriler ve tablolar"],
  "Add rows to your spreadsheets with secure Google sign-in.": [
    "Añade filas a tus hojas con un acceso seguro de Google.",
    "Ajoutez des lignes à vos tableurs avec une connexion Google sécurisée.",
    "Zeilen zu Ihren Tabellen hinzufügen, mit sicherer Google-Anmeldung.",
    "Güvenli Google girişiyle tablolarınıza satır ekleyin.",
  ],
  "Create and update records in your bases.": ["Crea y actualiza registros en tus bases.", "Créez et mettez à jour des enregistrements dans vos bases.", "Datensätze in Ihren Bases anlegen und ändern.", "Tabanlarınızda kayıt oluşturun ve güncelleyin."],
  "Team and alerts": ["Equipo y avisos", "Équipe et alertes", "Team und Benachrichtigungen", "Ekip ve uyarılar"],
  "Get approval requests and failure alerts in a channel.": [
    "Recibe solicitudes de aprobación y avisos de fallos en un canal.",
    "Recevez les demandes d'approbation et les alertes d'échec dans un canal.",
    "Freigabeanfragen und Fehlermeldungen in einem Kanal erhalten.",
    "Onay isteklerini ve hata uyarılarını bir kanalda alın.",
  ],
  "Everything else": ["Todo lo demás", "Tout le reste", "Alles andere", "Diğer her şey"],
  "Any app that can send a signed webhook can start a workflow.": [
    "Cualquier app que envíe un webhook firmado puede iniciar un flujo.",
    "Toute appli capable d'envoyer un webhook signé peut lancer un flux.",
    "Jede App, die einen signierten Webhook senden kann, kann einen Workflow starten.",
    "İmzalı webhook gönderebilen her uygulama bir iş akışı başlatabilir.",
  ],
  "Call other services with stored, encrypted credentials.": [
    "Llama a otros servicios con credenciales guardadas y cifradas.",
    "Appelez d'autres services avec des identifiants enregistrés et chiffrés.",
    "Andere Dienste mit gespeicherten, verschlüsselten Zugangsdaten aufrufen.",
    "Kayıtlı, şifreli kimlik bilgileriyle diğer hizmetleri çağırın.",
  ],
  "AI steps": ["Pasos con IA", "Étapes IA", "KI-Schritte", "Yapay zekâ adımları"],
  "Read documents and PDFs, sort messages, summarise, translate and draft replies.": [
    "Lee documentos y PDF, clasifica mensajes, resume, traduce y redacta respuestas.",
    "Lisez documents et PDF, triez les messages, résumez, traduisez et rédigez des réponses.",
    "Dokumente und PDFs lesen, Nachrichten sortieren, zusammenfassen, übersetzen und Antworten entwerfen.",
    "Belgeleri ve PDF'leri okuyun, mesajları sınıflandırın, özetleyin, çevirin ve yanıt taslağı hazırlayın.",
  ],

  // --- security ---
  "Built to be trusted with your store": ["Hecho para que confíes tu tienda", "Conçu pour mériter la confiance de votre boutique", "Gebaut, damit Sie ihm Ihren Shop anvertrauen können", "Mağazanızı emanet edebilmeniz için yapıldı"],
  "Automation touches your customers and your money. Here is how we keep both safe.": [
    "La automatización toca a tus clientes y tu dinero. Así protegemos ambos.",
    "L'automatisation touche vos clients et votre argent. Voici comment nous protégeons les deux.",
    "Automatisierung betrifft Ihre Kunden und Ihr Geld. So schützen wir beides.",
    "Otomasyon müşterilerinize ve paranıza dokunur. İkisini de böyle koruyoruz.",
  ],
  "Received spam or phishing sent through us?": ["¿Recibiste spam o phishing enviado a través de nosotros?", "Vous avez reçu du spam ou de l'hameçonnage envoyé via nous ?", "Spam oder Phishing über uns erhalten?", "Bizim üzerimizden gönderilmiş spam veya oltalama mı aldınız?"],
  "Report it": ["Denúncialo", "Signalez-le", "Melden Sie es", "Bildirin"],
  "Your data stays yours": ["Tus datos siguen siendo tuyos", "Vos données restent les vôtres", "Ihre Daten bleiben Ihre", "Verileriniz sizin kalır"],
  "Separate workspaces": ["Espacios separados", "Espaces séparés", "Getrennte Arbeitsbereiche", "Ayrı çalışma alanları"],
  "Every business gets its own workspace. Each request is checked against it, so one shop can never see another's data.": [
    "Cada negocio tiene su propio espacio. Cada solicitud se comprueba, así que una tienda nunca ve los datos de otra.",
    "Chaque entreprise a son propre espace. Chaque demande est vérifiée, donc une boutique ne voit jamais les données d'une autre.",
    "Jedes Unternehmen hat einen eigenen Arbeitsbereich. Jede Anfrage wird geprüft, sodass kein Shop die Daten eines anderen sieht.",
    "Her işletmenin kendi çalışma alanı vardır. Her istek buna göre denetlenir; bir mağaza başka birinin verilerini asla göremez.",
  ],
  "Encrypted credentials": ["Credenciales cifradas", "Identifiants chiffrés", "Verschlüsselte Zugangsdaten", "Şifreli kimlik bilgileri"],
  "Passwords and tokens for your apps are encrypted before they are stored and are never shown again, not even to you.": [
    "Las contraseñas y tokens de tus apps se cifran antes de guardarse y no se vuelven a mostrar, ni siquiera a ti.",
    "Les mots de passe et jetons de vos applis sont chiffrés avant stockage et ne sont plus jamais affichés, même à vous.",
    "Passwörter und Tokens Ihrer Apps werden vor dem Speichern verschlüsselt und nie wieder angezeigt, auch Ihnen nicht.",
    "Uygulamalarınızın şifreleri ve anahtarları saklanmadan önce şifrelenir ve bir daha gösterilmez, size bile.",
  ],
  "Export or delete at any time": ["Exporta o borra cuando quieras", "Exportez ou supprimez à tout moment", "Jederzeit exportieren oder löschen", "İstediğiniz zaman dışa aktarın veya silin"],
  "Download everything in your workspace, or delete the workspace and your account yourself, from Settings.": [
    "Descarga todo tu espacio, o borra el espacio y tu cuenta tú mismo, desde Ajustes.",
    "Téléchargez tout votre espace, ou supprimez vous-même l'espace et votre compte, depuis les Réglages.",
    "Laden Sie alles herunter oder löschen Sie Arbeitsbereich und Konto selbst, in den Einstellungen.",
    "Ayarlar'dan çalışma alanınızdaki her şeyi indirin ya da çalışma alanını ve hesabınızı kendiniz silin.",
  ],
  "You stay in control": ["Tú mantienes el control", "Vous gardez le contrôle", "Sie behalten die Kontrolle", "Kontrol sizde kalır"],
  "Approvals for what matters": ["Aprobaciones para lo importante", "Des approbations pour ce qui compte", "Freigaben für das Wichtige", "Önemli olanlar için onaylar"],
  "Emails to customers wait for a person to approve them. You can require approval for every outside action.": [
    "Los correos a clientes esperan a que una persona los apruebe. Puedes exigir aprobación para cualquier acción externa.",
    "Les e-mails aux clients attendent l'accord d'une personne. Vous pouvez exiger une approbation pour toute action externe.",
    "E-Mails an Kunden warten auf die Freigabe durch einen Menschen. Sie können für jede externe Aktion eine Freigabe verlangen.",
    "Müşterilere giden e-postalar bir insanın onayını bekler. Her dış işlem için onay zorunlu kılabilirsiniz.",
  ],
  "Emergency stop and limits": ["Parada de emergencia y límites", "Arrêt d'urgence et limites", "Not-Aus und Limits", "Acil durdurma ve sınırlar"],
  "One switch pauses every automation. Daily limits on runs, emails and AI use prevent runaway costs.": [
    "Un interruptor pausa todas las automatizaciones. Los límites diarios de ejecuciones, correos e IA evitan costes descontrolados.",
    "Un interrupteur met en pause toutes les automatisations. Des limites quotidiennes d'exécutions, d'e-mails et d'IA évitent les dérapages de coûts.",
    "Ein Schalter pausiert alle Automatisierungen. Tageslimits für Läufe, E-Mails und KI verhindern ausufernde Kosten.",
    "Tek bir düğme tüm otomasyonları duraklatır. Çalıştırma, e-posta ve yapay zekâ için günlük sınırlar kontrolsüz maliyeti önler.",
  ],
  "No spam or phishing": ["Sin spam ni phishing", "Ni spam ni hameçonnage", "Kein Spam, kein Phishing", "Spam ve oltalama yok"],
  "Outgoing email is checked before it is approved or sent; phishing is blocked. New accounts start with lower limits, and anyone can report abuse.": [
    "El correo saliente se revisa antes de aprobarse o enviarse; el phishing se bloquea. Las cuentas nuevas empiezan con límites más bajos y cualquiera puede denunciar abusos.",
    "Les e-mails sortants sont vérifiés avant approbation ou envoi ; l'hameçonnage est bloqué. Les nouveaux comptes démarrent avec des limites plus basses et chacun peut signaler un abus.",
    "Ausgehende E-Mails werden vor Freigabe oder Versand geprüft; Phishing wird blockiert. Neue Konten starten mit niedrigeren Limits, und jeder kann Missbrauch melden.",
    "Giden e-postalar onaylanmadan veya gönderilmeden önce kontrol edilir; oltalama engellenir. Yeni hesaplar daha düşük sınırlarla başlar ve herkes kötüye kullanımı bildirebilir.",
  ],
  "Careful AI": ["IA prudente", "Une IA prudente", "Vorsichtige KI", "Dikkatli yapay zekâ"],
  "AI steps can only do what the workflow allows. Messages that look like manipulation attempts, and unsure answers, go to a person for review.": [
    "Los pasos con IA solo hacen lo que permite el flujo. Los mensajes que parecen intentos de manipulación y las respuestas dudosas pasan a revisión humana.",
    "Les étapes IA ne font que ce que le flux autorise. Les messages qui ressemblent à des manipulations et les réponses incertaines passent par une personne.",
    "KI-Schritte tun nur, was der Workflow erlaubt. Nachrichten, die nach Manipulation aussehen, und unsichere Antworten prüft ein Mensch.",
    "Yapay zekâ adımları yalnızca iş akışının izin verdiğini yapar. Manipülasyon girişimine benzeyen mesajlar ve emin olunmayan yanıtlar bir insana gider.",
  ],
  "Secure accounts and connections": ["Cuentas y conexiones seguras", "Comptes et connexions sécurisés", "Sichere Konten und Verbindungen", "Güvenli hesaplar ve bağlantılar"],
  "Two-factor login": ["Inicio de sesión en dos pasos", "Connexion en deux étapes", "Zwei-Faktor-Anmeldung", "İki adımlı giriş"],
  "Protect sign-in with any authenticator app, with one-time recovery codes. Passwords are stored only as salted scrypt hashes.": [
    "Protege el acceso con cualquier app de autenticación y códigos de recuperación de un solo uso. Las contraseñas solo se guardan como hashes scrypt con sal.",
    "Protégez la connexion avec n'importe quelle appli d'authentification et des codes de secours à usage unique. Les mots de passe ne sont stockés que sous forme de hachages scrypt salés.",
    "Schützen Sie die Anmeldung mit jeder Authenticator-App und Einmal-Wiederherstellungscodes. Passwörter werden nur als gesalzene scrypt-Hashes gespeichert.",
    "Girişi herhangi bir doğrulama uygulaması ve tek kullanımlık kurtarma kodlarıyla koruyun. Şifreler yalnızca tuzlu scrypt özetleri olarak saklanır.",
  ],
  "Roles and an activity log": ["Roles y registro de actividad", "Rôles et journal d'activité", "Rollen und Aktivitätsprotokoll", "Roller ve etkinlik günlüğü"],
  "Give teammates owner, admin, member or viewer access. Sign-ins, permission changes, publishes and approvals are logged.": [
    "Da a tu equipo acceso de propietario, administrador, miembro o lector. Se registran accesos, cambios de permisos, publicaciones y aprobaciones.",
    "Donnez à l'équipe un accès propriétaire, admin, membre ou lecteur. Connexions, changements de droits, publications et approbations sont journalisés.",
    "Geben Sie Teammitgliedern Besitzer-, Admin-, Mitglieds- oder Lesezugriff. Anmeldungen, Rechteänderungen, Veröffentlichungen und Freigaben werden protokolliert.",
    "Ekip arkadaşlarına sahip, yönetici, üye veya görüntüleyici erişimi verin. Girişler, yetki değişiklikleri, yayınlar ve onaylar kaydedilir.",
  ],
  "Signed webhooks": ["Webhooks firmados", "Webhooks signés", "Signierte Webhooks", "İmzalı webhook'lar"],
  "Incoming store events are checked against a shared secret (including Shopify and WooCommerce signatures) before anything runs.": [
    "Los eventos de la tienda se verifican con un secreto compartido (incluidas las firmas de Shopify y WooCommerce) antes de ejecutar nada.",
    "Les événements de la boutique sont vérifiés avec un secret partagé (y compris les signatures Shopify et WooCommerce) avant toute exécution.",
    "Eingehende Shop-Ereignisse werden vor jeder Ausführung gegen ein gemeinsames Geheimnis geprüft (inklusive Shopify- und WooCommerce-Signaturen).",
    "Gelen mağaza olayları, bir şey çalışmadan önce ortak bir gizli anahtarla (Shopify ve WooCommerce imzaları dahil) doğrulanır.",
  ],
  "No double actions": ["Sin acciones duplicadas", "Pas d'actions en double", "Keine doppelten Aktionen", "Çift işlem yok"],
  "Retries are automatic but never repeat a step that may already have happened. Those runs are flagged for you to check.": [
    "Los reintentos son automáticos pero nunca repiten un paso que pudo haber ocurrido. Esas ejecuciones se marcan para que las revises.",
    "Les nouvelles tentatives sont automatiques mais ne répètent jamais une étape qui a peut-être déjà eu lieu. Ces exécutions vous sont signalées.",
    "Wiederholungen sind automatisch, wiederholen aber nie einen Schritt, der vielleicht schon passiert ist. Solche Läufe werden zur Prüfung markiert.",
    "Yeniden denemeler otomatiktir ama gerçekleşmiş olabilecek bir adımı asla tekrarlamaz. Bu çalıştırmalar kontrol etmeniz için işaretlenir.",
  ],
  "A record of every run": ["Un registro de cada ejecución", "Une trace de chaque exécution", "Ein Protokoll jedes Laufs", "Her çalıştırmanın kaydı"],
  "Each run keeps what it received, what every step did, and why anything failed.": [
    "Cada ejecución guarda lo que recibió, lo que hizo cada paso y por qué falló algo.",
    "Chaque exécution garde ce qu'elle a reçu, ce que chaque étape a fait et pourquoi quelque chose a échoué.",
    "Jeder Lauf hält fest, was er erhalten hat, was jeder Schritt tat und warum etwas fehlschlug.",
    "Her çalıştırma neyi aldığını, her adımın ne yaptığını ve bir şeyin neden başarısız olduğunu saklar.",
  ],
  "Safe outbound calls": ["Llamadas salientes seguras", "Appels sortants sécurisés", "Sichere ausgehende Aufrufe", "Güvenli dış çağrılar"],
  "Workflows can't be pointed at internal network addresses, which blocks a common class of attacks.": [
    "Los flujos no pueden apuntar a direcciones de red internas, lo que bloquea un tipo común de ataque.",
    "Les flux ne peuvent pas viser des adresses réseau internes, ce qui bloque une catégorie d'attaques courante.",
    "Workflows können nicht auf interne Netzwerkadressen zeigen, was eine verbreitete Angriffsart blockiert.",
    "İş akışları iç ağ adreslerine yönlendirilemez; bu yaygın bir saldırı türünü engeller.",
  ],

  // --- report abuse ---
  "Trust and safety": ["Confianza y seguridad", "Confiance et sécurité", "Vertrauen und Sicherheit", "Güven ve güvenlik"],
  "Report spam or phishing": ["Denunciar spam o phishing", "Signaler du spam ou de l'hameçonnage", "Spam oder Phishing melden", "Spam veya oltalamayı bildirin"],
  "Got an email sent through our platform that looks like spam or phishing? Tell us. Every report is reviewed, and a workspace that breaks the rules can be stopped from sending.": [
    "¿Recibiste un correo enviado por nuestra plataforma que parece spam o phishing? Cuéntanoslo. Revisamos cada denuncia y podemos impedir que un espacio que incumple las normas siga enviando.",
    "Vous avez reçu un e-mail envoyé via notre plateforme qui ressemble à du spam ou de l'hameçonnage ? Dites-le-nous. Chaque signalement est examiné, et un espace qui enfreint les règles peut être bloqué.",
    "Eine E-Mail über unsere Plattform erhalten, die nach Spam oder Phishing aussieht? Sagen Sie es uns. Jede Meldung wird geprüft, und ein Arbeitsbereich, der gegen die Regeln verstößt, kann am Senden gehindert werden.",
    "Platformumuz üzerinden gönderilmiş, spam veya oltalamaya benzeyen bir e-posta mı aldınız? Bize bildirin. Her bildirim incelenir ve kuralları çiğneyen bir çalışma alanının gönderimi durdurulabilir.",
  ],
  "What happened?": ["¿Qué pasó?", "Que s'est-il passé ?", "Was ist passiert?", "Ne oldu?"],
  "Phishing (asks for passwords, codes or payment)": ["Phishing (pide contraseñas, códigos o pagos)", "Hameçonnage (demande mots de passe, codes ou paiement)", "Phishing (fragt nach Passwörtern, Codes oder Zahlungen)", "Oltalama (şifre, kod veya ödeme istiyor)"],
  "Spam (unwanted marketing or bulk email)": ["Spam (publicidad no deseada o envíos masivos)", "Spam (publicité non sollicitée ou envoi de masse)", "Spam (unerwünschte Werbung oder Massenmails)", "Spam (istenmeyen pazarlama veya toplu e-posta)"],
  "Something else": ["Otra cosa", "Autre chose", "Etwas anderes", "Başka bir şey"],
  "Details": ["Detalles", "Détails", "Details", "Ayrıntılar"],
  "Paste the message or describe it. Include the sender address and date if you can.": [
    "Pega el mensaje o descríbelo. Incluye la dirección del remitente y la fecha si puedes.",
    "Collez le message ou décrivez-le. Indiquez l'adresse de l'expéditeur et la date si possible.",
    "Fügen Sie die Nachricht ein oder beschreiben Sie sie. Wenn möglich mit Absenderadresse und Datum.",
    "Mesajı yapıştırın veya anlatın. Mümkünse gönderen adresini ve tarihi ekleyin.",
  ],
  "Your email (optional)": ["Tu correo (opcional)", "Votre e-mail (facultatif)", "Ihre E-Mail (optional)", "E-postanız (isteğe bağlı)"],
  "Only used if we need to ask you something.": ["Solo se usa si necesitamos preguntarte algo.", "Utilisé seulement si nous devons vous poser une question.", "Nur genutzt, falls wir Rückfragen haben.", "Yalnızca size bir şey sormamız gerekirse kullanılır."],
  "Workspace number (optional)": ["Número de espacio (opcional)", "Numéro d'espace (facultatif)", "Nummer des Arbeitsbereichs (optional)", "Çalışma alanı numarası (isteğe bağlı)"],
  "From the email's X-AutoFlow-Workspace header.": ["Del encabezado X-AutoFlow-Workspace del correo.", "Dans l'en-tête X-AutoFlow-Workspace de l'e-mail.", "Aus dem Header X-AutoFlow-Workspace der E-Mail.", "E-postanın X-AutoFlow-Workspace başlığından."],
  "Send report": ["Enviar denuncia", "Envoyer le signalement", "Meldung senden", "Bildirimi gönder"],
  "Sending…": ["Enviando…", "Envoi…", "Wird gesendet…", "Gönderiliyor…"],
  "Thank you. Our team reviews every report and can stop a workspace from sending while we look into it.": [
    "Gracias. Nuestro equipo revisa cada denuncia y puede detener los envíos de un espacio mientras lo investiga.",
    "Merci. Notre équipe examine chaque signalement et peut bloquer l'envoi d'un espace pendant l'enquête.",
    "Danke. Unser Team prüft jede Meldung und kann das Senden eines Arbeitsbereichs währenddessen stoppen.",
    "Teşekkürler. Ekibimiz her bildirimi inceler ve inceleme sürerken bir çalışma alanının gönderimini durdurabilir.",
  ],
};

const COLUMN = { es: 0, fr: 1, de: 2, tr: 3 } as const;

/** Site text in the visitor's language (English while pre-rendering). */
export function useSiteText() {
  const { language } = useI18n();
  return (english: string, vars?: Record<string, string | number>) => {
    const column = COLUMN[language as keyof typeof COLUMN];
    let text = column === undefined ? english : (SITE[english]?.[column] ?? english);
    for (const [name, value] of Object.entries(vars ?? {})) text = text.replaceAll(`{${name}}`, String(value));
    return text;
  };
}

/** <S t="English text" />: a sentence of the website, translated. */
export function S({ t, vars }: { t: string; vars?: Record<string, string | number> }) {
  const translate = useSiteText();
  return <>{translate(t, vars)}</>;
}

/** Every English sentence that has translations (used by the coverage check). */
export const TRANSLATED = Object.keys(SITE);

"use client";

import { useCallback, useSyncExternalStore } from "react";

/*
 * Interface translations.
 *
 * Adding a language = adding one dictionary below. Missing keys fall back
 * to English, so pages can be translated step by step.
 */

const en = {
  "nav.dashboard": "Dashboard",
  "nav.workflows": "Workflows",
  "nav.runs": "Run history",
  "nav.approvals": "Approvals",
  "nav.invoices": "Invoices",
  "nav.connections": "Connected apps",
  "nav.billing": "Plan & usage",
  "nav.settings": "Settings",
  "nav.menu": "Menu",
  "nav.signOut": "Sign out",
  "nav.toApprove": "{count} to approve",
  "nav.language": "Language",
  "banner.stopped": "All automations are stopped.",
  "banner.resume": "Resume in Settings",

  "auth.signIn": "Sign in",
  "auth.createAccount": "Create your account",
  "auth.create": "Create account",
  "auth.name": "Your name",
  "auth.email": "Email",
  "auth.password": "Password",
  "auth.passwordHint": "At least 8 characters.",
  "auth.wait": "Please wait…",
  "auth.newHere": "New here?",
  "auth.haveAccount": "Have an account?",
  "auth.code": "Code from your authenticator app",
  "auth.codeHint": "Or one of your recovery codes.",

  "dash.subtitle": "What your automations did for you.",
  "dash.newWorkflow": "New workflow",
  "dash.timeSaved": "Time saved (30 days)",
  "dash.timeSavedHint": "Successful live runs × minutes per run",
  "dash.runsToday": "Runs today",
  "dash.failed": "{count} failed",
  "dash.waiting": "Waiting for you",
  "dash.waitingHint": "Approvals and reviews",
  "dash.workflows": "Workflows",
  "dash.workflowsHint": "{active} active · {paused} paused",
  "dash.recentRuns": "Recent runs",
  "dash.noRuns": "No runs yet",
  "dash.noRunsHint": "Open a workflow and press “Test run” to see it work step by step.",
  "dash.limits": "Today’s limits",
  "dash.limitRuns": "Runs",
  "dash.limitAi": "AI calls",
  "dash.limitEmails": "Emails sent",
  "dash.byWorkflow": "Time saved by workflow",
  "dash.noWorkflows": "No workflows yet.",

  "appr.title": "Approvals",
  "appr.subtitle": "Anything sensitive waits here for a person: emails to customers, unsure AI results, and possible prompt-injection attempts.",
  "appr.waiting": "Waiting",
  "appr.decided": "Decided",
  "appr.nothingWaiting": "Nothing waiting for you",
  "appr.noDecisions": "No decisions yet",
  "appr.checkCategory": "Check the AI’s category",
  "appr.sendEmail": "Send this email?",
  "appr.reviewResult": "Review AI result: {name}",
  "appr.approveStep": "Approve step: {name}",
  "appr.aiSays": "AI says",
  "appr.category": "Category",
  "appr.to": "To:",
  "appr.subject": "Subject:",
  "appr.whatAiRead": "What the AI read",
  "appr.resultEdit": "Result (correct it if needed)",
  "appr.result": "Result",
  "appr.approve": "Approve",
  "appr.accept": "Accept and continue",
  "appr.reject": "Reject",
  "appr.run": "run #{id}",
  "appr.badJson": "The corrected result is not valid JSON.",
};

export type MessageKey = keyof typeof en;
type Dictionary = Partial<Record<MessageKey, string>>;

const es: Dictionary = {
  "nav.dashboard": "Panel", "nav.workflows": "Flujos de trabajo", "nav.runs": "Historial", "nav.approvals": "Aprobaciones",
  "nav.invoices": "Facturas", "nav.connections": "Apps conectadas", "nav.billing": "Plan y uso", "nav.settings": "Ajustes",
  "nav.menu": "Menú", "nav.signOut": "Cerrar sesión", "nav.toApprove": "{count} por aprobar", "nav.language": "Idioma",
  "banner.stopped": "Todas las automatizaciones están detenidas.", "banner.resume": "Reanudar en Ajustes",
  "auth.signIn": "Iniciar sesión", "auth.createAccount": "Crea tu cuenta", "auth.create": "Crear cuenta",
  "auth.name": "Tu nombre", "auth.email": "Correo electrónico", "auth.password": "Contraseña",
  "auth.passwordHint": "Al menos 8 caracteres.", "auth.wait": "Un momento…", "auth.newHere": "¿Eres nuevo?",
  "auth.haveAccount": "¿Ya tienes cuenta?",
  "auth.code": "Código de tu app de autenticación", "auth.codeHint": "O uno de tus códigos de recuperación.",
  "dash.subtitle": "Lo que tus automatizaciones hicieron por ti.", "dash.newWorkflow": "Nuevo flujo",
  "dash.timeSaved": "Tiempo ahorrado (30 días)", "dash.timeSavedHint": "Ejecuciones reales correctas × minutos por ejecución",
  "dash.runsToday": "Ejecuciones hoy", "dash.failed": "{count} fallidas", "dash.waiting": "Esperándote",
  "dash.waitingHint": "Aprobaciones y revisiones", "dash.workflows": "Flujos", "dash.workflowsHint": "{active} activos · {paused} en pausa",
  "dash.recentRuns": "Ejecuciones recientes", "dash.noRuns": "Aún no hay ejecuciones",
  "dash.noRunsHint": "Abre un flujo y pulsa «Prueba» para verlo funcionar paso a paso.",
  "dash.limits": "Límites de hoy", "dash.limitRuns": "Ejecuciones", "dash.limitAi": "Llamadas de IA", "dash.limitEmails": "Correos enviados",
  "dash.byWorkflow": "Tiempo ahorrado por flujo", "dash.noWorkflows": "Aún no hay flujos.",
  "appr.title": "Aprobaciones",
  "appr.subtitle": "Todo lo delicado espera aquí a una persona: correos a clientes, resultados de IA dudosos e intentos de manipulación.",
  "appr.waiting": "Pendientes", "appr.decided": "Decididas", "appr.nothingWaiting": "No hay nada pendiente",
  "appr.noDecisions": "Aún no hay decisiones", "appr.checkCategory": "Revisa la categoría de la IA", "appr.sendEmail": "¿Enviar este correo?",
  "appr.reviewResult": "Revisar resultado de IA: {name}", "appr.approveStep": "Aprobar paso: {name}", "appr.aiSays": "La IA dice",
  "appr.category": "Categoría", "appr.to": "Para:", "appr.subject": "Asunto:", "appr.whatAiRead": "Lo que leyó la IA",
  "appr.resultEdit": "Resultado (corrígelo si hace falta)", "appr.result": "Resultado", "appr.approve": "Aprobar",
  "appr.accept": "Aceptar y continuar", "appr.reject": "Rechazar", "appr.run": "ejecución #{id}",
  "appr.badJson": "El resultado corregido no es JSON válido.",
};

const fr: Dictionary = {
  "nav.dashboard": "Tableau de bord", "nav.workflows": "Workflows", "nav.runs": "Historique", "nav.approvals": "Validations",
  "nav.invoices": "Factures", "nav.connections": "Apps connectées", "nav.billing": "Offre et usage", "nav.settings": "Paramètres",
  "nav.menu": "Menu", "nav.signOut": "Se déconnecter", "nav.toApprove": "{count} à valider", "nav.language": "Langue",
  "banner.stopped": "Toutes les automatisations sont arrêtées.", "banner.resume": "Reprendre dans Paramètres",
  "auth.signIn": "Se connecter", "auth.createAccount": "Créez votre compte", "auth.create": "Créer le compte",
  "auth.name": "Votre nom", "auth.email": "E-mail", "auth.password": "Mot de passe",
  "auth.passwordHint": "Au moins 8 caractères.", "auth.wait": "Un instant…", "auth.newHere": "Nouveau ici ?",
  "auth.haveAccount": "Déjà un compte ?",
  "auth.code": "Code de votre application d’authentification", "auth.codeHint": "Ou l’un de vos codes de récupération.",
  "dash.subtitle": "Ce que vos automatisations ont fait pour vous.", "dash.newWorkflow": "Nouveau workflow",
  "dash.timeSaved": "Temps gagné (30 jours)", "dash.timeSavedHint": "Exécutions réelles réussies × minutes par exécution",
  "dash.runsToday": "Exécutions aujourd’hui", "dash.failed": "{count} en échec", "dash.waiting": "En attente de vous",
  "dash.waitingHint": "Validations et vérifications", "dash.workflows": "Workflows", "dash.workflowsHint": "{active} actifs · {paused} en pause",
  "dash.recentRuns": "Exécutions récentes", "dash.noRuns": "Aucune exécution pour l’instant",
  "dash.noRunsHint": "Ouvrez un workflow et cliquez sur « Test » pour le voir étape par étape.",
  "dash.limits": "Limites du jour", "dash.limitRuns": "Exécutions", "dash.limitAi": "Appels IA", "dash.limitEmails": "E-mails envoyés",
  "dash.byWorkflow": "Temps gagné par workflow", "dash.noWorkflows": "Aucun workflow pour l’instant.",
  "appr.title": "Validations",
  "appr.subtitle": "Tout ce qui est sensible attend ici une personne : e-mails aux clients, résultats d’IA incertains et tentatives de manipulation.",
  "appr.waiting": "En attente", "appr.decided": "Traitées", "appr.nothingWaiting": "Rien ne vous attend",
  "appr.noDecisions": "Aucune décision pour l’instant", "appr.checkCategory": "Vérifiez la catégorie de l’IA", "appr.sendEmail": "Envoyer cet e-mail ?",
  "appr.reviewResult": "Vérifier le résultat de l’IA : {name}", "appr.approveStep": "Valider l’étape : {name}", "appr.aiSays": "L’IA indique",
  "appr.category": "Catégorie", "appr.to": "À :", "appr.subject": "Objet :", "appr.whatAiRead": "Ce que l’IA a lu",
  "appr.resultEdit": "Résultat (corrigez-le si besoin)", "appr.result": "Résultat", "appr.approve": "Valider",
  "appr.accept": "Accepter et continuer", "appr.reject": "Refuser", "appr.run": "exécution n°{id}",
  "appr.badJson": "Le résultat corrigé n’est pas un JSON valide.",
};

const de: Dictionary = {
  "nav.dashboard": "Übersicht", "nav.workflows": "Workflows", "nav.runs": "Verlauf", "nav.approvals": "Freigaben",
  "nav.invoices": "Rechnungen", "nav.connections": "Verbundene Apps", "nav.billing": "Tarif & Nutzung", "nav.settings": "Einstellungen",
  "nav.menu": "Menü", "nav.signOut": "Abmelden", "nav.toApprove": "{count} freizugeben", "nav.language": "Sprache",
  "banner.stopped": "Alle Automatisierungen sind gestoppt.", "banner.resume": "In den Einstellungen fortsetzen",
  "auth.signIn": "Anmelden", "auth.createAccount": "Konto erstellen", "auth.create": "Konto erstellen",
  "auth.name": "Ihr Name", "auth.email": "E-Mail", "auth.password": "Passwort",
  "auth.passwordHint": "Mindestens 8 Zeichen.", "auth.wait": "Bitte warten…", "auth.newHere": "Neu hier?",
  "auth.haveAccount": "Schon ein Konto?",
  "auth.code": "Code aus Ihrer Authenticator-App", "auth.codeHint": "Oder einer Ihrer Wiederherstellungscodes.",
  "dash.subtitle": "Was Ihre Automatisierungen für Sie erledigt haben.", "dash.newWorkflow": "Neuer Workflow",
  "dash.timeSaved": "Gesparte Zeit (30 Tage)", "dash.timeSavedHint": "Erfolgreiche Live-Läufe × Minuten pro Lauf",
  "dash.runsToday": "Läufe heute", "dash.failed": "{count} fehlgeschlagen", "dash.waiting": "Wartet auf Sie",
  "dash.waitingHint": "Freigaben und Prüfungen", "dash.workflows": "Workflows", "dash.workflowsHint": "{active} aktiv · {paused} pausiert",
  "dash.recentRuns": "Letzte Läufe", "dash.noRuns": "Noch keine Läufe",
  "dash.noRunsHint": "Öffnen Sie einen Workflow und klicken Sie auf „Testlauf“, um ihn Schritt für Schritt zu sehen.",
  "dash.limits": "Heutige Limits", "dash.limitRuns": "Läufe", "dash.limitAi": "KI-Aufrufe", "dash.limitEmails": "Gesendete E-Mails",
  "dash.byWorkflow": "Gesparte Zeit pro Workflow", "dash.noWorkflows": "Noch keine Workflows.",
  "appr.title": "Freigaben",
  "appr.subtitle": "Alles Heikle wartet hier auf einen Menschen: E-Mails an Kunden, unsichere KI-Ergebnisse und mögliche Manipulationsversuche.",
  "appr.waiting": "Offen", "appr.decided": "Entschieden", "appr.nothingWaiting": "Nichts wartet auf Sie",
  "appr.noDecisions": "Noch keine Entscheidungen", "appr.checkCategory": "Kategorie der KI prüfen", "appr.sendEmail": "Diese E-Mail senden?",
  "appr.reviewResult": "KI-Ergebnis prüfen: {name}", "appr.approveStep": "Schritt freigeben: {name}", "appr.aiSays": "Die KI sagt",
  "appr.category": "Kategorie", "appr.to": "An:", "appr.subject": "Betreff:", "appr.whatAiRead": "Was die KI gelesen hat",
  "appr.resultEdit": "Ergebnis (bei Bedarf korrigieren)", "appr.result": "Ergebnis", "appr.approve": "Freigeben",
  "appr.accept": "Übernehmen und fortfahren", "appr.reject": "Ablehnen", "appr.run": "Lauf #{id}",
  "appr.badJson": "Das korrigierte Ergebnis ist kein gültiges JSON.",
};

const tr: Dictionary = {
  "nav.dashboard": "Gösterge paneli", "nav.workflows": "İş akışları", "nav.runs": "Çalışma geçmişi", "nav.approvals": "Onaylar",
  "nav.invoices": "Faturalar", "nav.connections": "Bağlı uygulamalar", "nav.billing": "Plan ve kullanım", "nav.settings": "Ayarlar",
  "nav.menu": "Menü", "nav.signOut": "Çıkış yap", "nav.toApprove": "{count} onay bekliyor", "nav.language": "Dil",
  "banner.stopped": "Tüm otomasyonlar durduruldu.", "banner.resume": "Ayarlar’dan devam ettirin",
  "auth.signIn": "Giriş yap", "auth.createAccount": "Hesabınızı oluşturun", "auth.create": "Hesap oluştur",
  "auth.name": "Adınız", "auth.email": "E-posta", "auth.password": "Şifre",
  "auth.passwordHint": "En az 8 karakter.", "auth.wait": "Lütfen bekleyin…", "auth.newHere": "Yeni misiniz?",
  "auth.haveAccount": "Hesabınız var mı?",
  "auth.code": "Doğrulama uygulamanızdaki kod", "auth.codeHint": "Ya da kurtarma kodlarınızdan biri.",
  "dash.subtitle": "Otomasyonlarınızın sizin için yaptıkları.", "dash.newWorkflow": "Yeni iş akışı",
  "dash.timeSaved": "Kazanılan zaman (30 gün)", "dash.timeSavedHint": "Başarılı canlı çalışmalar × çalışma başına dakika",
  "dash.runsToday": "Bugünkü çalışmalar", "dash.failed": "{count} başarısız", "dash.waiting": "Sizi bekleyenler",
  "dash.waitingHint": "Onaylar ve incelemeler", "dash.workflows": "İş akışları", "dash.workflowsHint": "{active} aktif · {paused} duraklatıldı",
  "dash.recentRuns": "Son çalışmalar", "dash.noRuns": "Henüz çalışma yok",
  "dash.noRunsHint": "Bir iş akışını açın ve adım adım görmek için “Test çalıştır”a basın.",
  "dash.limits": "Bugünkü limitler", "dash.limitRuns": "Çalışmalar", "dash.limitAi": "Yapay zekâ çağrıları", "dash.limitEmails": "Gönderilen e-postalar",
  "dash.byWorkflow": "İş akışına göre kazanılan zaman", "dash.noWorkflows": "Henüz iş akışı yok.",
  "appr.title": "Onaylar",
  "appr.subtitle": "Hassas olan her şey burada bir insanı bekler: müşterilere e-postalar, emin olunamayan yapay zekâ sonuçları ve olası manipülasyon girişimleri.",
  "appr.waiting": "Bekleyenler", "appr.decided": "Karar verilenler", "appr.nothingWaiting": "Sizi bekleyen bir şey yok",
  "appr.noDecisions": "Henüz karar yok", "appr.checkCategory": "Yapay zekânın kategorisini kontrol edin", "appr.sendEmail": "Bu e-posta gönderilsin mi?",
  "appr.reviewResult": "Yapay zekâ sonucunu inceleyin: {name}", "appr.approveStep": "Adımı onaylayın: {name}", "appr.aiSays": "Yapay zekâya göre",
  "appr.category": "Kategori", "appr.to": "Kime:", "appr.subject": "Konu:", "appr.whatAiRead": "Yapay zekânın okuduğu",
  "appr.resultEdit": "Sonuç (gerekirse düzeltin)", "appr.result": "Sonuç", "appr.approve": "Onayla",
  "appr.accept": "Kabul et ve devam et", "appr.reject": "Reddet", "appr.run": "çalışma #{id}",
  "appr.badJson": "Düzeltilmiş sonuç geçerli bir JSON değil.",
};

export const LANGUAGES = {
  en: { label: "English", messages: en as Dictionary },
  es: { label: "Español", messages: es },
  fr: { label: "Français", messages: fr },
  de: { label: "Deutsch", messages: de },
  tr: { label: "Türkçe", messages: tr },
} as const;

export type Language = keyof typeof LANGUAGES;

const STORAGE_KEY = "autoflow.language";
const listeners = new Set<() => void>();

function isLanguage(value: string | null | undefined): value is Language {
  return Boolean(value && value in LANGUAGES);
}

function readLanguage(): Language {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (isLanguage(stored)) return stored;
  } catch {
    // storage unavailable: use the browser language
  }
  const browser = navigator.language?.slice(0, 2).toLowerCase();
  return isLanguage(browser) ? browser : "en";
}

export function setLanguage(language: Language) {
  try {
    window.localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // the choice lasts for this page only
  }
  document.documentElement.lang = language;
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function translate(language: Language, key: MessageKey, vars?: Record<string, string | number>) {
  let text = LANGUAGES[language].messages[key] ?? en[key] ?? key;
  for (const [name, value] of Object.entries(vars ?? {})) {
    text = text.replaceAll(`{${name}}`, String(value));
  }
  return text;
}

/** Current language and a translate function. Server render uses English. */
export function useI18n() {
  const language = useSyncExternalStore(subscribe, readLanguage, () => "en" as Language);
  const t = useCallback(
    (key: MessageKey, vars?: Record<string, string | number>) => translate(language, key, vars),
    [language],
  );
  return { language, t, setLanguage };
}

export const APP_NAME = "Cadora.pro";
export const APP_TAGLINE = "De planos arquitectónicos a CAD";
export const APP_DESCRIPTION =
  "Sube tu plano arquitectónico y obtén un archivo DXF/DWG editable con detección automática de muros, puertas, ventanas, habitaciones, textos y cotas.";

export const NAV_ITEMS = [
  { label: "Inicio", href: "/" },
  { label: "Cómo funciona", href: "/como-funciona" },
  { label: "Precios", href: "/pricing" },
] as const;

export const DASHBOARD_NAV = [
  { label: "Dashboard", href: "/dashboard", icon: "LayoutDashboard" },
  { label: "Historial", href: "/dashboard/history", icon: "History" },
  { label: "Mis Proyectos", href: "/projects", icon: "FolderKanban" },
  { label: "Facturación", href: "/billing", icon: "CreditCard" },
  { label: "Perfil", href: "/profile", icon: "User" },
  { label: "Configuración", href: "/settings", icon: "Settings" },
] as const;

export const PLANS = [
  {
    id: "free",
    name: "Free",
    price: 0,
    paddlePriceId: "",
    description: "Para pruebas ocasionales",
    features: [
      "3 conversiones/mes",
      "50 MB de almacenamiento",
      "Exportación DXF",
      "Detección básica",
    ],
    cta: "Comenzar gratis",
    popular: false,
    conversions: "3/mes",
    storage: "50 MB",
    priority: false,
  },
  {
    id: "starter",
    name: "Starter",
    price: 19,
    paddlePriceId: "price_starter_id",
    description: "Para profesionales independientes",
    features: [
      "50 conversiones/mes",
      "1 GB de almacenamiento",
      "Exportación DXF",
      "Detección avanzada",
      "OCR de textos y cotas",
      "Soporte por email",
    ],
    cta: "Suscribirse",
    popular: false,
    conversions: "50/mes",
    storage: "1 GB",
    priority: false,
  },
  {
    id: "pro",
    name: "Pro",
    price: 49,
    paddlePriceId: "price_pro_id",
    description: "Para estudios y equipos pequeños",
    features: [
      "200 conversiones/mes",
      "5 GB de almacenamiento",
      "Exportación DXF + DWG",
      "Detección avanzada",
      "OCR de textos y cotas",
      "Procesamiento prioritario",
      "Soporte prioritario",
    ],
    cta: "Suscribirse",
    popular: true,
    conversions: "200/mes",
    storage: "5 GB",
    priority: true,
  },
  {
    id: "business",
    name: "Business",
    price: 99,
    paddlePriceId: "price_business_id",
    description: "Para empresas con alto volumen",
    features: [
      "Conversiones ilimitadas",
      "25 GB de almacenamiento",
      "Exportación DXF + DWG",
      "Detección avanzada",
      "OCR de textos y cotas",
      "Procesamiento prioritario",
      "API dedicada",
      "Soporte dedicado 24/7",
    ],
    cta: "Suscribirse",
    popular: false,
    conversions: "Ilimitadas",
    storage: "25 GB",
    priority: true,
  },
] as const;

export const DETECTION_STEPS = [
  { id: "preprocessing", label: "Preprocesando imagen" },
  { id: "walls", label: "Detectando muros" },
  { id: "doors_windows", label: "Detectando puertas y ventanas" },
  { id: "rooms", label: "Segmentando ambientes" },
  { id: "text", label: "Reconociendo textos" },
  { id: "dimensions", label: "Extrayendo cotas" },
  { id: "cad", label: "Generando archivo CAD" },
] as const;

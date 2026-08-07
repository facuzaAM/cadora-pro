"use client";

import { useState } from "react";
import Link from "next/link";
import { Mail, RefreshCw, CheckCircle, ArrowRight } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/services/api";

export function EmailVerificationBanner() {
  const { user, refreshUser } = useAuth();
  const [sending, setSending] = useState(false);
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"idle" | "sent" | "verifying" | "done" | "error">("idle");
  const [message, setMessage] = useState("");

  if (!user || user.email_verified) return null;

  const handleSend = async () => {
    setSending(true);
    setMessage("");
    try {
      const token = api.getAccessToken();
      await api.post("/auth/send-verification", {}, token);
      setStep("sent");
      setMessage("Código enviado a tu email");
    } catch {
      setMessage("Error al enviar el código. Intentá de nuevo.");
      setStep("error");
    } finally {
      setSending(false);
    }
  };

  const handleVerify = async () => {
    if (code.length !== 6) return;
    setSending(true);
    setMessage("");
    try {
      const token = api.getAccessToken();
      await api.post("/auth/verify-email", { code }, token);
      setStep("done");
      await refreshUser();
    } catch {
      setMessage("Código incorrecto o expirado");
      setStep("error");
    } finally {
      setSending(false);
    }
  };

  if (step === "done") {
    return (
      <div className="mb-6 flex items-center gap-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
        <CheckCircle className="h-5 w-5 shrink-0 text-emerald-500" />
        <span>Email verificado correctamente</span>
      </div>
    );
  }

  return (
    <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <Mail className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
          <div className="text-sm text-amber-800">
            <p className="font-medium">Verificá tu email</p>
            <p className="mt-0.5 text-amber-700">
              {step === "idle"
                ? "Te enviamos un código de verificación al registrarte."
                : step === "sent"
                  ? "Revisá tu email e ingresá el código de 6 dígitos."
                  : message}
            </p>
          </div>
        </div>
        <Link
          href="/verify-email"
          className="inline-flex shrink-0 items-center gap-1 rounded-md px-2 py-1 text-sm font-medium text-amber-700 underline-offset-4 hover:bg-amber-100 hover:underline"
        >
          Verificar
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      {step === "idle" && (
        <div className="mt-3">
          <button
            onClick={handleSend}
            disabled={sending}
            className="inline-flex items-center gap-2 rounded-md bg-amber-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
          >
            {sending && <RefreshCw className="h-3 w-3 animate-spin" />}
            Reenviar código
          </button>
        </div>
      )}

      {step === "sent" && (
        <div className="mt-3 flex items-center gap-2">
          <input
            type="text"
            inputMode="numeric"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            placeholder="000000"
            className="w-28 rounded-md border border-amber-300 bg-white px-3 py-1.5 text-center text-sm font-mono tracking-widest text-amber-900 placeholder-amber-300 focus:outline-none focus:ring-2 focus:ring-amber-500"
          />
          <button
            onClick={handleVerify}
            disabled={sending || code.length !== 6}
            className="inline-flex items-center gap-2 rounded-md bg-amber-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
          >
            {sending && <RefreshCw className="h-3 w-3 animate-spin" />}
            Verificar
          </button>
          <button
            onClick={handleSend}
            disabled={sending}
            className="text-sm text-amber-700 underline hover:text-amber-800 disabled:opacity-50"
          >
            Reenviar
          </button>
        </div>
      )}

      {step === "error" && (
        <div className="mt-3">
          <button
            onClick={() => { setStep("idle"); setMessage(""); }}
            className="text-sm text-amber-700 underline hover:text-amber-800"
          >
            Intentar de nuevo
          </button>
        </div>
      )}
    </div>
  );
}

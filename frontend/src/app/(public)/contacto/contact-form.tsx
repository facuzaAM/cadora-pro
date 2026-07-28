"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { AlertCircle } from "lucide-react";
import { api, ApiError } from "@/services/api";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function ContactForm() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const e: Record<string, string> = {};
    if (!name.trim() || name.trim().length < 2) e.name = "El nombre debe tener al menos 2 caracteres";
    if (!EMAIL_RE.test(email)) e.email = "Email inválido";
    if (!subject.trim()) e.subject = "El asunto es requerido";
    if (!message.trim() || message.trim().length < 10) e.message = "El mensaje debe tener al menos 10 caracteres";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setSending(true);
    try {
      await api.post("/contact", { name: name.trim(), email, subject: subject.trim(), message: message.trim() });
      toast.success("Mensaje enviado. Te responderemos pronto.");
      setName("");
      setEmail("");
      setSubject("");
      setMessage("");
      setErrors({});
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(err.message || "Error al enviar. Intentá de nuevo.");
      } else {
        toast.error("Error de conexión. Intentá más tarde.");
      }
    } finally {
      setSending(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">Nombre</Label>
        <Input
          id="name"
          placeholder="Tu nombre"
          value={name}
          onChange={(e) => { setName(e.target.value); setErrors((prev) => ({ ...prev, name: "" })); }}
          className={errors.name ? "border-destructive" : ""}
        />
        {errors.name && <p className="flex items-center gap-1 text-xs text-destructive"><AlertCircle className="h-3 w-3" />{errors.name}</p>}
      </div>
      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          placeholder="tu@email.com"
          value={email}
          onChange={(e) => { setEmail(e.target.value); setErrors((prev) => ({ ...prev, email: "" })); }}
          className={errors.email ? "border-destructive" : ""}
        />
        {errors.email && <p className="flex items-center gap-1 text-xs text-destructive"><AlertCircle className="h-3 w-3" />{errors.email}</p>}
      </div>
      <div className="space-y-2">
        <Label htmlFor="subject">Asunto</Label>
        <Input
          id="subject"
          placeholder="¿En qué podemos ayudarte?"
          value={subject}
          onChange={(e) => { setSubject(e.target.value); setErrors((prev) => ({ ...prev, subject: "" })); }}
          className={errors.subject ? "border-destructive" : ""}
        />
        {errors.subject && <p className="flex items-center gap-1 text-xs text-destructive"><AlertCircle className="h-3 w-3" />{errors.subject}</p>}
      </div>
      <div className="space-y-2">
        <Label htmlFor="message">Mensaje</Label>
        <Textarea
          id="message"
          rows={5}
          placeholder="Describe tu consulta o problema..."
          value={message}
          onChange={(e) => { setMessage(e.target.value); setErrors((prev) => ({ ...prev, message: "" })); }}
          className={errors.message ? "border-destructive" : ""}
        />
        {errors.message && <p className="flex items-center gap-1 text-xs text-destructive"><AlertCircle className="h-3 w-3" />{errors.message}</p>}
      </div>
      <Button type="submit" className="w-full" disabled={sending}>
        {sending ? "Enviando..." : "Enviar mensaje"}
      </Button>
    </form>
  );
}

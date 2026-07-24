"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ThemeToggle } from "@/components/shared/theme-toggle";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/services/api";
import { billingService } from "@/services/billing.service";
import { toast } from "sonner";
import Link from "next/link";

const profileSchema = z.object({
  full_name: z.string().min(2, "Nombre muy corto"),
});

type ProfileForm = z.infer<typeof profileSchema>;

export function SettingsForm() {
  const { user, loading, refreshUser } = useAuth();
  const [planName, setPlanName] = useState("Free");

  const form = useForm<ProfileForm>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: user?.name || "",
    },
  });

  useEffect(() => {
    if (user) {
      form.reset({ full_name: user.name });
    }
  }, [user, form]);

  useEffect(() => {
    const token = api.getAccessToken();
    billingService.getSubscription(token).then((sub) => {
      setPlanName(sub.plan.charAt(0).toUpperCase() + sub.plan.slice(1));
    }).catch(() => {});
  }, []);

  const onSubmit = async (data: ProfileForm) => {
    if (!user) return;
    try {
      await api.patch("/auth/me", { name: data.full_name }, api.getAccessToken());
      await refreshUser();
      toast.success("Perfil actualizado");
    } catch {
      toast.error("Error al guardar");
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Perfil</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? (
            <div className="space-y-3">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : (
            <>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input id="email" value={user?.email || ""} disabled />
              </div>
              <div className="space-y-2">
                <Label htmlFor="full_name">Nombre</Label>
                <Input id="full_name" {...form.register("full_name")} />
              </div>
              <Button onClick={form.handleSubmit(onSubmit)}>Guardar Cambios</Button>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Apariencia</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-between">
          <div>
            <p className="font-medium">Modo Oscuro</p>
            <p className="text-sm text-muted-foreground">
              Alterna entre tema claro y oscuro
            </p>
          </div>
          <ThemeToggle />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Plan Actual</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-between">
          <div>
            <p className="font-medium">Plan {planName}</p>
            <p className="text-sm text-muted-foreground">
              Actualiza para obtener más conversiones y almacenamiento
            </p>
          </div>
          <Button variant="outline" asChild>
            <Link href="/pricing">Mejorar Plan</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

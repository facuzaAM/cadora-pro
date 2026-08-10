"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Users,
  FolderKanban,
  Search,
  Trash2,
  ShieldCheck,
  Mail,
  Loader2,
  DollarSign,
  CreditCard,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/shared/page-header";
import { useAuth } from "@/hooks/useAuth";
import { adminService, type AdminStats, type AdminUser } from "@/services/admin.service";
import { api } from "@/services/api";
import { toast } from "sonner";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("es-AR", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export default function AdminPage() {
  const { user, loading } = useAuth();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [query, setQuery] = useState("");
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(async (q = "") => {
    const token = api.getAccessToken();
    setLoadingUsers(true);
    try {
      const [s, list] = await Promise.all([
        adminService.getStats(token),
        adminService.listUsers({ q, limit: 100 }, token),
      ]);
      setStats(s);
      setUsers(list);
    } catch {
      toast.error("Error al cargar datos de administración");
    } finally {
      setLoadingUsers(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleSearch = () => load(query.trim());

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`¿Eliminar la cuenta de "${name}"? Esta acción es irreversible.`)) return;
    setDeleting(id);
    try {
      await adminService.deleteUser(id, api.getAccessToken());
      toast.success("Usuario eliminado");
      setUsers((prev) => prev.filter((u) => u.id !== id));
    } catch {
      toast.error("Error al eliminar el usuario");
    } finally {
      setDeleting(null);
    }
  };

  if (loading) {
    return <div className="h-48 animate-pulse rounded-lg border bg-muted/30" />;
  }

  if (!user?.is_admin) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed bg-muted/30 px-6 py-16 text-center">
        <ShieldCheck className="mb-4 h-8 w-8 text-muted-foreground" />
        <h2 className="text-xl font-bold">Acceso restringido</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Esta sección es solo para administradores de Cadora.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Administración"
        description="Usuarios y métricas de la plataforma"
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="flex items-center gap-3 p-5">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10">
              <DollarSign className="h-5 w-5 text-emerald-500" />
            </div>
            <div>
              <p className="text-2xl font-bold tabular-nums">
                {stats?.mrr != null ? `$${stats.mrr}` : "—"}
              </p>
              <p className="text-xs text-muted-foreground">MRR (USD)</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-5">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <CreditCard className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold tabular-nums">{stats?.paying_users ?? "—"}</p>
              <p className="text-xs text-muted-foreground">Clientes pagos</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-5">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <Users className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold tabular-nums">{stats?.total_users ?? "—"}</p>
              <p className="text-xs text-muted-foreground">Usuarios</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-5">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10">
              <FolderKanban className="h-5 w-5 text-emerald-500" />
            </div>
            <div>
              <p className="text-2xl font-bold tabular-nums">{stats?.total_projects ?? "—"}</p>
              <p className="text-xs text-muted-foreground">Proyectos</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Buscar por email o nombre..."
            className="pl-9"
            aria-label="Buscar usuarios"
          />
        </div>
        <Button onClick={handleSearch} variant="outline">
          Buscar
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          {loadingUsers ? (
            <div className="space-y-3 p-5">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-12 animate-pulse rounded-lg bg-muted/30" />
              ))}
            </div>
          ) : users.length === 0 ? (
            <div className="p-10 text-center text-sm text-muted-foreground">
              No se encontraron usuarios.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="px-5 py-3 font-medium">Usuario</th>
                    <th className="px-5 py-3 font-medium">Plan</th>
                    <th className="px-5 py-3 font-medium">Conversiones</th>
                    <th className="px-5 py-3 font-medium">Almacenamiento</th>
                    <th className="px-5 py-3 font-medium">Proyectos</th>
                    <th className="px-5 py-3 font-medium">Registro</th>
                    <th className="px-5 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-b last:border-0 hover:bg-muted/30">
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{u.name}</span>
                          {u.is_admin && (
                            <Badge variant="secondary" className="gap-1">
                              <ShieldCheck className="h-3 w-3" />
                              Admin
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Mail className="h-3 w-3" />
                          {u.email}
                          {!u.email_verified && (
                            <Badge variant="outline" className="ml-1 text-[10px]">
                              sin verificar
                            </Badge>
                          )}
                        </div>
                      </td>
                      <td className="px-5 py-3">
                        <Badge variant={u.subscription_status === "active" ? "success" : "secondary"}>
                          {u.subscription_plan}
                        </Badge>
                      </td>
                      <td className="px-5 py-3 tabular-nums">
                        {u.conversions_used}/{u.conversions_limit > 0 ? u.conversions_limit : "∞"}
                      </td>
                      <td className="px-5 py-3 tabular-nums text-xs">
                        {formatBytes(u.storage_used)}
                      </td>
                      <td className="px-5 py-3 tabular-nums">{u.project_count}</td>
                      <td className="px-5 py-3 text-xs text-muted-foreground">
                        {formatDate(u.created_at)}
                      </td>
                      <td className="px-5 py-3 text-right">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-destructive"
                          disabled={u.is_admin || deleting === u.id}
                          onClick={() => handleDelete(u.id, u.name)}
                          title="Eliminar usuario"
                        >
                          {deleting === u.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Trash2 className="h-4 w-4" />
                          )}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

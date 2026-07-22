import Link from "next/link";
import { FileText, MoreHorizontal } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";

interface ProjectCardProps {
  id: string;
  name: string;
  status: string;
  statusVariant: "success" | "warning" | "secondary" | "default";
  updatedAt: string;
  documentCount: number;
}

export function ProjectCard({
  id,
  name,
  status,
  statusVariant,
  updatedAt,
  documentCount,
}: ProjectCardProps) {
  return (
    <Link href={`/projects/${id}/result`}>
      <Card className="transition-colors hover:border-primary/50">
        <CardContent className="p-5">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                <FileText className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold leading-none">{name}</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  {documentCount} documento{documentCount !== 1 ? "s" : ""} · {updatedAt}
                </p>
              </div>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild onClick={(e) => e.preventDefault()}>
                <Button variant="ghost" size="icon" className="-mr-2 -mt-2">
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem>Ver proyecto</DropdownMenuItem>
                <DropdownMenuItem>Subir archivo</DropdownMenuItem>
                <DropdownMenuItem className="text-destructive">Eliminar</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardContent>
        <CardFooter className="border-t px-5 py-3">
          <Badge variant={statusVariant}>{status}</Badge>
        </CardFooter>
      </Card>
    </Link>
  );
}

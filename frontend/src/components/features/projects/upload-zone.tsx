"use client";

import { useState, useCallback } from "react";
import { Upload, FileText, X, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface UploadZoneProps {
  onFileSelect: (file: File) => void;
  accept?: string;
  maxSizeMB?: number;
}

export function UploadZone({
  onFileSelect,
  accept = ".pdf,.png,.jpg,.jpeg,.tiff",
  maxSizeMB = 50,
}: UploadZoneProps) {
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const validateFile = useCallback(
    (f: File) => {
      const ext = "." + f.name.split(".").pop()?.toLowerCase();
      const allowed = accept.split(",");
      if (!allowed.includes(ext)) {
        setError("Formato no soportado. Usa PDF, PNG, JPG o TIFF.");
        return false;
      }
      if (f.size > maxSizeMB * 1024 * 1024) {
        setError(`El archivo excede el límite de ${maxSizeMB} MB.`);
        return false;
      }
      return true;
    },
    [accept, maxSizeMB],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const f = e.dataTransfer.files[0];
      if (f && validateFile(f)) {
        setFile(f);
        setError(null);
        onFileSelect(f);
      }
    },
    [validateFile, onFileSelect],
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (f && validateFile(f)) {
        setFile(f);
        setError(null);
        onFileSelect(f);
      }
    },
    [validateFile, onFileSelect],
  );

  const removeFile = () => {
    setFile(null);
    setError(null);
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      className={cn(
        "relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-12 transition-colors",
        dragOver && "border-primary bg-primary/5",
        file ? "border-primary/50 bg-primary/5" : "border-muted-foreground/25 hover:border-muted-foreground/50",
      )}
      onClick={() => !file && document.getElementById("file-upload")?.click()}
    >
      {!file ? (
        <>
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 mb-4">
            <Upload className="h-8 w-8 text-primary" />
          </div>
          <h3 className="font-semibold">Sube tu plano arquitectónico</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Arrastra tu archivo aquí o haz clic para seleccionar
          </p>
          <Badge variant="secondary" className="mt-4">
            PDF, PNG, JPG, TIFF — hasta {maxSizeMB} MB
          </Badge>
        </>
      ) : (
        <div className="flex items-center gap-4" onClick={(e) => e.stopPropagation()}>
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
            <FileText className="h-6 w-6 text-primary" />
          </div>
          <div className="text-left">
            <p className="font-medium">{file.name}</p>
            <p className="text-sm text-muted-foreground">
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
          <Button variant="ghost" size="icon" onClick={removeFile}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      )}

      {error && (
        <div className="mt-4 flex items-center gap-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      <input
        id="file-upload"
        type="file"
        accept={accept}
        className="hidden"
        onChange={handleChange}
      />
    </div>
  );
}

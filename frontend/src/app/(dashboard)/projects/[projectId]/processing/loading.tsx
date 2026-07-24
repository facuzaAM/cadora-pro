import { Skeleton } from "@/components/ui/skeleton";

export default function ProcessingLoading() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-24" />
      <Skeleton className="h-64 w-full rounded-lg" />
    </div>
  );
}

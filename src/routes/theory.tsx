import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { TheoryView } from "@/components/TheoryView";

export const Route = createFileRoute("/theory")({ component: TheoryPage });

function TheoryPage() {
  return (
    <AppShell>
      <TheoryView />
    </AppShell>
  );
}

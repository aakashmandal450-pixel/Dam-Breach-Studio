import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { InstallView } from "@/components/InstallView";

export const Route = createFileRoute("/install")({ component: InstallPage });

function InstallPage() {
  return (
    <AppShell>
      <InstallView />
    </AppShell>
  );
}

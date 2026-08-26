import { Download, Monitor, Share2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function InstallView() {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-8 pb-16">
      <header className="flex flex-col gap-2">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-accent">Desktop use</p>
        <h1 className="font-display text-3xl font-medium tracking-tight md:text-4xl">Install and share</h1>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Dam Breach Studio is a self-contained web application. The formation engine runs entirely on
          the device — no server calculation, no account. Install it like a normal desktop program, then
          hand colleagues the same link or a project file.
        </p>
      </header>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2 text-accent">
            <Monitor className="size-4" />
            <CardTitle>Install on this computer</CardTitle>
          </div>
          <CardDescription>Works on Windows, macOS and Linux through Chrome or Edge.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 text-sm leading-relaxed text-muted-foreground">
          <ol className="flex list-decimal flex-col gap-2 pl-5">
            <li>Open this studio in Chrome or Microsoft Edge.</li>
            <li>
              Use the browser install control — the plus / install icon in the address bar, or the menu
              item <span className="text-foreground">Install Dam Breach Studio</span> /{" "}
              <span className="text-foreground">Apps → Install this site as an app</span>.
            </li>
            <li>The studio appears in the Start menu or Applications folder and opens in its own window.</li>
          </ol>
          <p>
            After install it can be used offline for a previously loaded session. Inputs are stored on
            this device only.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2 text-accent">
            <Share2 className="size-4" />
            <CardTitle>Share with another engineer</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 text-sm leading-relaxed text-muted-foreground">
          <p>
            Send them this app’s address. They open it, optionally install it the same way, and they
            have a full copy of the engine — no extra runtime, no Python, no spreadsheet macros.
          </p>
          <p>
            To share a specific dam, use <span className="text-foreground">Export project</span> on the
            Simulate page. That JSON file contains every input. They load it with{" "}
            <span className="text-foreground">Import project</span>. Hydrographs export as CSV for
            routing models.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2 text-accent">
            <Download className="size-4" />
            <CardTitle>What is not a desktop installer</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="text-sm leading-relaxed text-muted-foreground">
          This is not an .exe / .msi / .dmg package and does not require administrator rights. The
          installed app is the studio itself, signed by the browser as a progressive web app — the
          same pattern used by professional web-based engineering tools that need to travel between
          machines without an IT install.
        </CardContent>
      </Card>
    </div>
  );
}

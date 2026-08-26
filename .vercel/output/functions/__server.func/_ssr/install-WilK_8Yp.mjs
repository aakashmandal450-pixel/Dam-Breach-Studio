import { s as require_jsx_runtime } from "../_libs/@radix-ui/react-collection+[...].mjs";
import { a as Share2, s as Monitor, u as Download } from "../_libs/lucide-react.mjs";
import { a as CardDescription, i as CardContent, o as CardHeader, r as Card, s as CardTitle, t as AppShell } from "./card-C9FRDXWz.mjs";
//#region node_modules/.nitro/vite/services/ssr/assets/install-WilK_8Yp.js
var import_jsx_runtime = require_jsx_runtime();
function InstallView() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto flex w-full max-w-3xl flex-col gap-8 pb-16",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
				className: "flex flex-col gap-2",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs font-medium uppercase tracking-[0.16em] text-accent",
						children: "Desktop use"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
						className: "font-display text-3xl font-medium tracking-tight md:text-4xl",
						children: "Install and share"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-sm leading-relaxed text-muted-foreground",
						children: "Dam Breach Studio is a self-contained web application. The formation engine runs entirely on the device — no server calculation, no account. Install it like a normal desktop program, then hand colleagues the same link or a project file."
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(CardHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2 text-accent",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Monitor, { className: "size-4" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardTitle, { children: "Install on this computer" })]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardDescription, { children: "Works on Windows, macOS and Linux through Chrome or Edge." })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(CardContent, {
				className: "flex flex-col gap-3 text-sm leading-relaxed text-muted-foreground",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("ol", {
					className: "flex list-decimal flex-col gap-2 pl-5",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: "Open this studio in Chrome or Microsoft Edge." }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", { children: [
							"Use the browser install control — the plus / install icon in the address bar, or the menu item ",
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "text-foreground",
								children: "Install Dam Breach Studio"
							}),
							" /",
							" ",
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "text-foreground",
								children: "Apps → Install this site as an app"
							}),
							"."
						] }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: "The studio appears in the Start menu or Applications folder and opens in its own window." })
					]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { children: "After install it can be used offline for a previously loaded session. Inputs are stored on this device only." })]
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardHeader, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2 text-accent",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Share2, { className: "size-4" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardTitle, { children: "Share with another engineer" })]
			}) }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(CardContent, {
				className: "flex flex-col gap-3 text-sm leading-relaxed text-muted-foreground",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { children: "Send them this app’s address. They open it, optionally install it the same way, and they have a full copy of the engine — no extra runtime, no Python, no spreadsheet macros." }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", { children: [
					"To share a specific dam, use ",
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-foreground",
						children: "Export project"
					}),
					" on the Simulate page. That JSON file contains every input. They load it with",
					" ",
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-foreground",
						children: "Import project"
					}),
					". Hydrographs export as CSV for routing models."
				] })]
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardHeader, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-center gap-2 text-accent",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Download, { className: "size-4" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardTitle, { children: "What is not a desktop installer" })]
			}) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardContent, {
				className: "text-sm leading-relaxed text-muted-foreground",
				children: "This is not an .exe / .msi / .dmg package and does not require administrator rights. The installed app is the studio itself, signed by the browser as a progressive web app — the same pattern used by professional web-based engineering tools that need to travel between machines without an IT install."
			})] })
		]
	});
}
function InstallPage() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AppShell, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(InstallView, {}) });
}
//#endregion
export { InstallPage as component };

// REMURA V30.7 LAB — 26/11/2026 09:13 CET.
// Wraps the existing v1.10 UI without altering permissions or mounting a route.
import {renderContributorsPageV110} from "./contributors_ui_v110_lab.mjs";
import {deskNavigation} from "./v306_desk_navigation_lab.mjs";
export function renderVerifiedDeskV307(path, profile) {
  // verified must be supplied by authenticated server middleware.
  if (!profile || profile.verified !== true) return null;
  if (profile.role === "INVITED") {
    if (path !== "/join/") return null;
    return renderContributorsPageV110(path, profile);
  }
  const d=deskNavigation(profile);
  if (!d || ![d.home,d.levels].includes(path)) return null;
  const page=renderContributorsPageV110(path,profile);
  if (typeof page !== "string") return null;
  // No source data or privileged links are inserted.
  const banner='<aside aria-label="Versione REMURA" style="padding:8px 16px;font-size:12px">REMURA V30.7 LAB · 26/11/2026 · 09:13 CET</aside>';
  return page.replace(/<body(?:\s[^>]*)?>/i,m=>m+banner);
}

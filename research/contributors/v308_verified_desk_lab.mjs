// REMURA V30.9 pilot LAB — 26/11/2026 09:24 CET.
// Only called after native Access authentication AND D1 profile resolution.
import {renderContributorsPageV110} from "./contributors_ui_v110_lab.mjs";
import {deskNavigation} from "./v306_desk_navigation_lab.mjs";
export const PILOT_RELEASE = Object.freeze({version:"30.9 LAB",updatedAt:"2026-11-26T09:24:00+01:00"});
export function renderVerifiedDeskV308(path, profile) {
  if (!profile || profile.verified !== true || profile.can_read !== true) return null;
  if (profile.role === "INVITED") {
    if (path !== "/join/" || !["friend-b","friend-c"].includes(profile.slot)) return null;
  } else {
    const d=deskNavigation(profile);
    if (!d || !d.canRead || ![d.home,d.levels].includes(path)) return null;
  }
  const page=renderContributorsPageV110(path,profile);
  if (typeof page !== "string") return null;
  // Keep the existing CSS and CSP; replace the single native version banner.
  const old='<div class="version">REMURA Contributors v1.10 LAB · <time datetime="2026-11-24T23:28:00+01:00">24/11/2026 23:28 CET (Europe/Rome)</time></div>';
  const next='<div class="version">REMURA V30.9 LAB · <time datetime="2026-11-26T09:24:00+01:00">26/11/2026 09:24 CET (Europe/Rome)</time></div>';
  if (page.split(old).length !== 2) return null;
  return page.replace(old,next).replaceAll("REMURA Contributors v1.10 LAB","REMURA V30.9 LAB");
}

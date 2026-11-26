// REMURA V30.6 LAB, 26/11/2026 07:04 CET.
// Only a server-verified profile may reach this adapter. No auth decisions
// based on URL, client input or an unverified browser profile.
// No Oracle bridge, private intelligence, write operation or deployment.
export function deskNavigation(profile) {
  if (!profile || profile.verified !== true) return null;
  const owner = profile.role === "OWNER" && profile.slot === "owner";
  const member = profile.role === "CONTRIBUTOR" && ["friend-a","friend-b","friend-c"].includes(profile.slot);
  if (!owner && !member) return null;
  const home = owner ? "/owner/" : "/contributors/";
  return Object.freeze({
    home,
    levels: home+"levels/",
    canRead: profile.can_read === true,
    canWrite: profile.can_write === true,
    privateIntelligence: false,
    accessManagedBy: "CONTRIBUTORS_V110",
    version: "30.6 LAB"
  });
}

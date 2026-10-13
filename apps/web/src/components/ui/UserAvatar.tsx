/**
 * UserAvatar — one avatar everywhere a user is shown (B330).
 *
 * 1. The uploaded photo, if there is one AND it loads.
 * 2. Otherwise the first letter of the display name (else the email), white
 *    on a colour picked from the email: the same user keeps the same colour.
 * 3. Otherwise (no name, no email, or no letter in either) a generic person
 *    glyph, inline SVG.
 * A photo that fails to load (404, an HTML page instead of the image, a
 * blocked request) falls back to 2 or 3, so a broken image is never shown.
 */

import { useEffect, useState, type CSSProperties } from "react";

// White text passes WCAG AA (4.5:1) on every colour (4.6–7.6:1).
const PALETTE = ["#2563EB", "#7C3AED", "#C026D3", "#DB2777", "#BE123C", "#C2410C",
                 "#A16207", "#4D7C0F", "#047857", "#0F766E", "#0E7490", "#475569"];

function colourFor(key: string): string {
  let h = 0;
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0;
  return PALETTE[h % PALETTE.length];
}

function initialOf(name?: string | null, email?: string | null): string | null {
  for (const s of [name, email]) {
    const m = (s || "").trim().match(/\p{L}|\p{N}/u);      // first letter or digit, any script
    if (m) return m[0].toLocaleUpperCase();
  }
  return null;
}

// The generic person: a circle, a head, and shoulders cut to the circle by
// an arc (no clipPath, so no shared ids when many avatars are on one page).
const glyph = (
  <>
    <circle cx="16" cy="16" r="16" fill="#334155" />
    <circle cx="16" cy="12.6" r="5.6" fill="#CBD5E1" />
    <path d="M6.3 28.7C7.6 23.9 11.4 20.6 16 20.6s8.4 3.3 9.7 8.1A16 16 0 0 1 6.3 28.7z" fill="#CBD5E1" />
  </>
);

export function UserAvatar({ url, name, email, size = 24, className }: {
  url?: string | null; name?: string | null; email?: string | null; size?: number; className?: string;
}) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [url]);               // a new photo gets a fresh try
  const label = name || email || "User";
  // Shape and centring inline, so the avatar is right wherever it is used.
  const box: CSSProperties = { width: size, height: size, borderRadius: "50%", flex: "none" };

  if (url && !failed) {
    return <img src={url} alt="" title={label} style={{ ...box, objectFit: "cover" }} onError={() => setFailed(true)}
                className={className} />;
  }
  const initial = initialOf(name, email);
  if (!initial) {
    return <span role="img" aria-label={label} title={label} style={{ ...box, display: "inline-block" }} className={className}>
      <svg viewBox="0 0 32 32" width={size} height={size} aria-hidden="true">{glyph}</svg></span>;
  }
  return (
    <span role="img" aria-label={label} title={label}
          style={{ ...box, display: "inline-flex", alignItems: "center", justifyContent: "center", color: "#FFFFFF",
                   background: colourFor((email || name || "").toLowerCase()), fontSize: Math.round(size * 0.46),
                   fontWeight: 600, lineHeight: 1, userSelect: "none" }}
          className={className}>
      {initial}
    </span>
  );
}

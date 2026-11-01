# Frontend design system

The existing React/TypeScript application uses a shared token-based visual
foundation rather than separate light and dark component implementations.

## Color and typography

The theme tokens in `frontend/src/index.css` provide:

| Token | Light | Dark |
|---|---|---|
| Background | `#F6F8FC` | `#0B1220` |
| Surface | `#FFFFFF` | `#111C2E` |
| Secondary surface | `#F1F5F9` | `#172338` |
| Elevated surface | `#FFFFFF` | `#1E2B40` |
| Primary teal | `#0F766E` | `#2DD4BF` |
| Secondary blue | `#2563EB` | `#60A5FA` |
| Main text | `#0F172A` | `#E5EDF7` |
| Secondary text | `#475569` | `#CBD5E1` |
| Muted text | `#64748B` | `#94A3B8` |
| Border | `#E2E8F0` | `#263449` |

Semantic success, warning, danger, and information colors are also exposed as
CSS variables. Existing slate and indigo utility classes are theme-mapped to
the palette to retain page behavior while sharing the same color language.
Spacing and breakpoints continue to use the project's Tailwind CSS setup.

The interface requests Inter for Latin text and Hind Siliguri for Bengali text
from Google Fonts. System fonts and Noto Sans Bengali are fallbacks; no font
files are bundled in the project.

## Theme selection and preference scope

The selector offers **Light**, **Dark**, and **System** modes on the login,
required-password-rotation, main-header, and appearance settings screens.
System mode follows `prefers-color-scheme` changes. The selected mode is saved
separately for a guest and for each authenticated user ID in local storage.
Signing out removes the active-user marker and returns to the guest preference.
An inline bootstrap in `frontend/index.html` applies the stored preference
before the React application paints when possible.

Theme preference storage contains no access token. Browser storage may be
unavailable; in that case, the selected appearance still applies for the
current session.

## Shell, responsive behavior, and accessibility

`frontend/src/components/Layout.tsx` provides the responsive desktop sidebar,
collapsible navigation, mobile drawer, page context header, notification link,
theme selector, and sign-out actions. Administrative and operator links are
filtered by the authenticated role; backend authorization remains authoritative.
The existing routes use responsive Tailwind layouts, and globally scrollable
table wrappers remain independent from page scrolling.

Controls have visible focus outlines and touch-sized navigation/theme targets.
The mobile drawer can be dismissed by its close controls or backdrop. Reduced
motion preferences are respected. Recharts axes, tooltips, and series colors on
the dashboard consume the shared CSS tokens.

The design foundation applies across the currently implemented routes:
Dashboard, Entry, Exit, Vehicles, Slots, Reservations, Notifications, Sensors,
Payments, Payment Result, Audit, History, Blacklist, Cameras, Monitor, Reports,
Settings, Login, and Password Rotation.

## Existing feature boundaries

This visual update does not add backend features or placeholder screens. The
current route set has no registration or forgot-password flow, separate camera
health dashboard, ROI editor, dedicated ALPR review queue, analytics route, or
backup management route. Parking occupancy is represented by the existing
slot dashboard and sensor/transaction data; it is not presented as confirmed
camera-derived occupancy.

## Verification

The frontend production build includes TypeScript checking. Browser checks
recorded in `docs/FRONTEND_RESPONSIVE_VERIFICATION.md` cover the login screen,
theme selection, theme persistence, system preference changes, and responsive
widths. Authenticated-route checks use mocked API responses where noted; they
do not replace role-specific acceptance testing against a production account.

# Branding & Styles Guide

How to customize branding, colors, and common styles in the ReDIB Portal.

## Directory Layout

```
static/
├── css/
│   ├── main.css              # Global styles, brand variables, Bootstrap overrides
│   └── auth.css              # Login/signup page styles
├── images/
│   ├── ReDiB_logo.png        # Compact logo (navbar)
│   └── ReDIB_logo_text.png   # Wide logo with tagline (auth pages)
└── js/
    └── (future scripts)
```

After editing any file in `static/`, run:

```bash
python manage.py collectstatic --noinput
```

## Replacing the Logos

The portal uses two separate logo images:

- **Navbar (compact):** `ReDiB_logo.png` — referenced in `templates/base.html`, displayed at `height="32"`
- **Auth pages (wide):** `ReDIB_logo_text.png` — referenced in `templates/account/base_entrance.html`, max-height `64px` (set in `auth.css`)

To swap either logo:

1. Place the new file in `static/images/`
2. Update the filename in the corresponding template
3. Run `collectstatic`

**Note:** Filenames are case-sensitive on Linux. Double-check capitalization if the logo doesn't appear.

## Changing Brand Colors

All brand colors are defined as CSS custom properties at the top of `static/css/main.css`:

```css
:root {
    --redib-primary: #1A3D50;       /* Deep navy-teal (navbar, buttons, links) */
    --redib-secondary: #6B7780;     /* Warm gray (muted text, secondary elements) */
    --redib-accent: #BE2845;        /* Crimson red (badges, alerts, highlights) */
}
```

These are derived from the ReDIB logo colors but darkened/adjusted so the logo remains visible on colored backgrounds.

To change the brand color scheme:

1. Edit the hex values in `static/css/main.css` under `:root`
2. The "Bootstrap Overrides" section directly below the variables wires them into Bootstrap's `.bg-primary`, `.btn-primary`, `.btn-outline-primary`, `a`, `.bg-info`, `.bg-secondary`, and related classes — so changing the variables automatically updates the navbar, buttons, links, and card headers
3. If you change `--redib-primary`, also update the hover/active shades in the `.btn-primary:hover` and `.btn-primary:active` rules (make them slightly darker than your new primary)
4. Run `collectstatic` after saving

## Key CSS Files

### `static/css/main.css`

Loaded on every page via `templates/base.html`. Contains:

| Section | What it controls |
|---------|-----------------|
| `:root` variables | Brand colors used throughout |
| Bootstrap Overrides | Maps brand variables to `.bg-primary`, `.btn-primary`, `a`, etc. |
| `.sidebar` | Dashboard sidebar layout and hover/active states |
| `.text-pre-wrap` | Preserves line breaks in scientific content display |
| `.progress-lg` | Taller progress bar in the application wizard |
| `.sticky-sidebar-card` | Sticky positioning for wizard step sidebar |
| `.form-check-label` | Evaluation form radio button styling |

### `static/css/auth.css`

Loaded only on login/signup/logout pages. Controls the centered card layout:

| Class | Purpose |
|-------|---------|
| `.auth-wrapper` | Full-height centered flex container |
| `.auth-card` | Max-width card wrapper (440px) |
| `.auth-brand` | Logo + heading area above the card |
| `.auth-footer` | Links below the card (e.g., "Don't have an account?") |

## Template Structure

Auth pages follow this inheritance chain:

```
base.html                          ← global navbar, Bootstrap, main.css
└── account/base_entrance.html     ← auth.css, centered card, logo
    ├── account/login.html
    ├── account/signup.html
    └── account/logout.html
```

Dashboard pages follow:

```
base.html
└── dashboard_base.html            ← sidebar navigation
    └── (all dashboard child templates)
```

## Common Tasks

### Change the site name in the navbar

Edit `templates/base.html`, find the `navbar-brand` link and change the text after the `<img>` tag.

### Change the auth page heading

Edit `templates/account/base_entrance.html`, find the `<h2>` and `<p>` inside `.auth-brand`.

### Add a new global CSS rule

Add it to `static/css/main.css`, then run `collectstatic`. It will be available on every page.

### Add a page-specific style

Use the `{% block extra_css %}` block in the child template to add a `<link>` or `<style>` tag that only loads on that page.

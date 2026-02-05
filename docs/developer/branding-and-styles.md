# Branding & Styles Guide

How to customize branding, colors, and common styles in the ReDIB Portal.

## Directory Layout

```
static/
├── css/
│   ├── main.css              # Global styles and brand variables
│   └── auth.css              # Login/signup page styles
├── images/
│   └── logo-placeholder.svg  # Logo (replace with real logo)
└── js/
    └── (future scripts)
```

After editing any file in `static/`, run:

```bash
python manage.py collectstatic --noinput
```

## Replacing the Logo

1. Place your logo file (SVG, PNG, or similar) in `static/images/`
2. Update the two references to the logo:
   - **Navbar:** `templates/base.html` — look for `logo-placeholder.svg` and change the filename
   - **Auth pages:** `templates/account/base_entrance.html` — same search/replace
3. Run `collectstatic`

SVG is recommended because it scales cleanly at any size. The navbar uses `height="32"` and the auth pages use `max-height: 64px` (set in `auth.css`).

## Changing Brand Colors

All brand colors are defined as CSS custom properties at the top of `static/css/main.css`:

```css
:root {
    --redib-primary: #0d6efd;       /* Main brand color */
    --redib-secondary: #6c757d;     /* Secondary/muted color */
    --redib-accent: #0dcaf0;        /* Accent/highlight color */
}
```

To change the brand color scheme:

1. Edit the hex values in `static/css/main.css` under `:root`
2. These variables are used by the sidebar active/hover states and the auth page styles
3. The navbar and buttons still use Bootstrap's `bg-primary` class — to change those too, override Bootstrap's primary color by adding this to `main.css`:

```css
/* Override Bootstrap primary color */
.bg-primary { background-color: var(--redib-primary) !important; }
.btn-primary { background-color: var(--redib-primary); border-color: var(--redib-primary); }
.btn-primary:hover { background-color: color-mix(in srgb, var(--redib-primary) 85%, black); }
```

## Key CSS Files

### `static/css/main.css`

Loaded on every page via `templates/base.html`. Contains:

| Section | What it controls |
|---------|-----------------|
| `:root` variables | Brand colors used throughout |
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

"""Anti-aliased graphics for a Tk UI.

Tk's canvas draws hard-aliased primitives - no smoothing at all, which is
why arcs and circles come out jagged. Everything here is drawn with PIL at
4x and downsampled, so curves land smooth, then blitted as an image.
"""

import math

from PIL import Image, ImageDraw, ImageFilter

SS = 4          # supersample factor


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _lerp(c1, c2, t):
    a, b = _hex(c1), _hex(c2)
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def ring(size, pct, fg, track="#232327", bg="#171719", width=13,
         glow=True, gradient_to=None):
    """A progress ring. Returns a PIL Image ready for ImageTk.PhotoImage."""
    s = size * SS
    w = width * SS
    img = Image.new("RGB", (s, s), _hex(bg))
    d = ImageDraw.Draw(img)
    pad = w // 2 + SS
    box = [pad, pad, s - pad, s - pad]

    d.arc(box, 0, 360, fill=_hex(track), width=w)

    pct = max(0.0, min(100.0, pct))
    if pct > 0:
        sweep = 359.999 * pct / 100.0
        if gradient_to:
            # step the arc so the colour travels around it
            steps = max(24, int(sweep / 3))
            for i in range(steps):
                a0 = -90 + sweep * i / steps
                a1 = -90 + sweep * (i + 1) / steps + 0.6
                col = _lerp(fg, gradient_to, i / max(1, steps - 1))
                d.arc(box, a0, a1, fill=col, width=w)
        else:
            d.arc(box, -90, -90 + sweep, fill=_hex(fg), width=w)

        # rounded cap at each end
        r = w / 2
        cx = cy = s / 2
        rad = (s - 2 * pad) / 2
        for ang, col in ((-90, _hex(fg)),
                         (-90 + sweep,
                          _hex(gradient_to) if gradient_to else _hex(fg))):
            a = math.radians(ang)
            x, y = cx + rad * math.cos(a), cy + rad * math.sin(a)
            d.ellipse([x - r, y - r, x + r, y + r], fill=col)

    if glow and pct > 0:
        halo = img.filter(ImageFilter.GaussianBlur(radius=6 * SS))
        img = Image.blend(img, halo, 0.28)
        d = ImageDraw.Draw(img)
        # redraw crisp on top of its own bloom
        d.arc(box, 0, 360, fill=_hex(track), width=w)
        if gradient_to:
            sweep = 359.999 * pct / 100.0
            steps = max(24, int(sweep / 3))
            for i in range(steps):
                a0 = -90 + sweep * i / steps
                a1 = -90 + sweep * (i + 1) / steps + 0.6
                d.arc(box, a0, a1,
                      fill=_lerp(fg, gradient_to, i / max(1, steps - 1)),
                      width=w)
        else:
            d.arc(box, -90, -90 + 359.999 * pct / 100.0, fill=_hex(fg),
                  width=w)

    return img.resize((size, size), Image.LANCZOS)


def pill(width, height, colour, bg="#171719", radius=None):
    """A smooth rounded bar."""
    w, h = width * SS, height * SS
    r = (h // 2) if radius is None else radius * SS
    img = Image.new("RGB", (w, h), _hex(bg))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=_hex(colour))
    return img.resize((width, height), Image.LANCZOS)


def split_bar(width, height, split, left, right, bg="#171719", marker=None):
    """Two-tone rounded bar - used for the bufferbloat unloaded/loaded split."""
    w, h = width * SS, height * SS
    r = h // 2
    img = Image.new("RGB", (w, h), _hex(bg))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=_hex(right))
    x = max(r, min(w - r, int(w * split)))
    d.rounded_rectangle([0, 0, x, h - 1], radius=r, fill=_hex(left))
    if marker is not None:
        mx = max(2 * SS, min(w - 2 * SS, int(w * marker)))
        d.rounded_rectangle([mx - SS, -SS, mx + SS, h + SS], radius=SS,
                            fill=_hex("#f4f4f5"))
    return img.resize((width, height), Image.LANCZOS)


def soft_panel(width, height, base="#171719", tint="#20222c", radius=14,
               border="#2a2a33"):
    """Rounded card with a gentle top-down sheen instead of a flat fill."""
    w, h = width * SS, height * SS
    grad = Image.new("RGB", (1, h))
    gd = ImageDraw.Draw(grad)
    for y in range(h):
        gd.point((0, y), fill=_lerp(tint, base, min(1.0, y / (h * 0.75))))
    grad = grad.resize((w, h))

    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1],
                                           radius=radius * SS, fill=255)
    out = Image.new("RGB", (w, h), _hex(base))
    out.paste(grad, (0, 0), mask)
    ImageDraw.Draw(out).rounded_rectangle(
        [0, 0, w - 1, h - 1], radius=radius * SS, outline=_hex(border),
        width=SS)
    return out.resize((width, height), Image.LANCZOS)

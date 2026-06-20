#!/usr/bin/env python3
"""Generate icon.png (1024 px) and icon.ico (multi-size) for the app.

Design concept
--------------
Dark rounded-square background (#121212) — three horizontal white bars
representing a playlist — with a pair of Spotify-green arrows (↑ ↓) on
the right side conveying "reorder".
"""

from PIL import Image, ImageDraw


def create_icon(size: int = 1024) -> Image.Image:
    # Palette
    BG    = (18,  18,  18,  255)   # #121212
    GREEN = (29, 185,  84,  255)   # #1DB954
    W_HI  = (255, 255, 255, 229)   # white  90 %
    W_MID = (255, 255, 255, 150)   # white  59 %
    W_LO  = (255, 255, 255,  76)   # white  30 %

    def s(n: float) -> int:
        return round(n * size / 1024)

    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ── Background ────────────────────────────────────────────────
    draw.rounded_rectangle(
        [(0, 0), (size - 1, size - 1)],
        radius=s(196),
        fill=BG,
    )

    # ── Track bars ────────────────────────────────────────────────
    bh  = s(80)   # bar height
    br  = s(40)   # bar corner radius
    gap = s(60)   # gap between consecutive bars
    bx  = s(80)   # bar left edge

    total_h = 3 * bh + 2 * gap        # 360 px at 1024
    by1 = (size - total_h) // 2       # ~332
    by2 = by1 + bh + gap              # ~472
    by3 = by2 + bh + gap              # ~612

    draw.rounded_rectangle(
        [(bx, by1), (bx + s(580), by1 + bh)], radius=br, fill=W_HI
    )
    draw.rounded_rectangle(
        [(bx, by2), (bx + s(420), by2 + bh)], radius=br, fill=W_MID
    )
    draw.rounded_rectangle(
        [(bx, by3), (bx + s(500), by3 + bh)], radius=br, fill=W_LO
    )

    # ── Arrows ────────────────────────────────────────────────────
    ax = s(860)   # horizontal centre of both arrows
    sw = s(52)    # shaft width
    hw = s(80)    # arrowhead half-width
    ah = s(90)    # arrowhead height
    gp = s(24)    # half-gap between the two shafts at canvas centre

    mid = size // 2   # 512

    # Up arrow — tip points upward
    up_tip = by1 - s(60)          # ~272  (above bar 1)
    up_hb  = up_tip + ah          # bottom edge of arrowhead
    up_sb  = mid - gp             # shaft bottom (stops before centre)

    draw.polygon(
        [(ax, up_tip), (ax - hw, up_hb), (ax + hw, up_hb)],
        fill=GREEN,
    )
    draw.rectangle(
        [(ax - sw // 2, up_hb), (ax + sw // 2, up_sb)],
        fill=GREEN,
    )

    # Down arrow — tip points downward
    dn_tip = by3 + bh + s(60)     # ~752  (below bar 3)
    dn_ht  = dn_tip - ah          # top edge of arrowhead
    dn_st  = mid + gp             # shaft top (starts after centre)

    draw.polygon(
        [(ax, dn_tip), (ax - hw, dn_ht), (ax + hw, dn_ht)],
        fill=GREEN,
    )
    draw.rectangle(
        [(ax - sw // 2, dn_st), (ax + sw // 2, dn_ht)],
        fill=GREEN,
    )

    return img


if __name__ == "__main__":
    icon = create_icon(1024)

    icon.save("icon.png")
    print("OK  icon.png  saved  (1024 × 1024)")

    ico_sizes = [256, 128, 64, 48, 32, 16]
    icon.save(
        "icon.ico",
        format="ICO",
        sizes=[(n, n) for n in ico_sizes],
    )
    print(f"OK  icon.ico  saved  ({', '.join(str(n) for n in ico_sizes)} px)")

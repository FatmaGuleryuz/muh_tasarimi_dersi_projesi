"""Arayuz icin erisilebilir (WCAG AA) renk paleti secimi ve kaydi.
Cikti: ../palette.json
"""
import json


def relative_luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4))

    def channel(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = channel(r), channel(g), channel(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(hex1: str, hex2: str) -> float:
    l1, l2 = relative_luminance(hex1), relative_luminance(hex2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


PALETTE = {
    "name": "churn-karar-destek",
    "background": "#0F172A",
    "surface": "#1E293B",
    "text_primary": "#F1F5F9",
    "text_secondary": "#94A3B8",
    "primary": "#38BDF8",
    "danger": "#FB7185",
    "warning": "#F4A261",
    "success": "#2A9D8F",
    "border": "#334155",
}


def main():
    checks = {
        "text_primary/background": contrast_ratio(PALETTE["text_primary"], PALETTE["background"]),
        "text_primary/surface": contrast_ratio(PALETTE["text_primary"], PALETTE["surface"]),
        "primary/background": contrast_ratio(PALETTE["primary"], PALETTE["background"]),
        "danger/background": contrast_ratio(PALETTE["danger"], PALETTE["background"]),
        "success/background": contrast_ratio(PALETTE["success"], PALETTE["background"]),
    }

    for pair, ratio in checks.items():
        status = "OK (AA)" if ratio >= 4.5 else "YETERSIZ"
        print(f"[palette] {pair}: {ratio:.2f}:1 -> {status}")

    output = dict(PALETTE)
    output["wcag_aa_contrast_checks"] = {k: round(v, 2) for k, v in checks.items()}
    with open("palette.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("[palette] palette.json yazildi.")


if __name__ == "__main__":
    main()

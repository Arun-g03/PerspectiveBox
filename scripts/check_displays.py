"""Print DXGI desktop outputs PerspectiveBox will use (left-to-right order)."""

from __future__ import annotations

import sys

from perspectivebox.capture.monitors import load_capture_targets, wall_source_indices


def main() -> int:
    targets = load_capture_targets()
    n = len(targets)
    print(f"DXGI attached outputs: {n}")
    if not targets:
        print("No desktop-attached outputs found.", file=sys.stderr)
        return 1

    for i, t in enumerate(targets):
        print(
            f"  [{i}] device={t.device_idx} output={t.output_idx} "
            f"bounds=({t.left},{t.top})-({t.right},{t.bottom}) "
            f"size={t.width}x{t.height}"
        )

    if n >= 3:
        li, bi, ri = wall_source_indices(n)
        print(f"Wall mapping left/back/right -> indices {li}/{bi}/{ri}")
        print("Ready for three-wall capture.")
    elif n == 1:
        print(
            "Only 1 display: PerspectiveBox will use L/C/R region split. "
            "For full walls, install two virtual displays - see Docs/VirtualDisplays.md"
        )
    else:
        print(
            f"Only {n} displays: walls will share/duplicate sources. "
            "Add virtual displays until you have 3 - see Docs/VirtualDisplays.md"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

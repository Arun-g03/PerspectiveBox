from __future__ import annotations

import sys


def main() -> None:
    if "--debug-track" in sys.argv:
        from perspectivebox.tracking.face_track import debug_main

        debug_main()
        return
    from perspectivebox.app import run

    run()


if __name__ == "__main__":
    main()

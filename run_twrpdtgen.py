#!/usr/bin/env python3
"""twrpdtgen shim: use pre-cloned local AIK instead of cloning GitHub every run."""
import sys
import sebaubuntu_libs.libaik as libaik

libaik.AIK_REPO = "/home/gravity/Documents/Valkyrie/twrp/aik-linux"

from twrpdtgen.main import main

if __name__ == "__main__":
    sys.argv = ["twrpdtgen"] + sys.argv[1:]
    main()

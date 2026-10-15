# SPDX-License-Identifier: GPL-3.0-only
"""App-local numerical budgets, configured before capture or audio workers start."""
import os


def configure_runtime():
    # Tiny marker matrices and audio windows do not benefit from a full BLAS pool.
    # These environment variables affect this app's process, never Windows settings.
    os.environ['OPENBLAS_NUM_THREADS']='1'
    os.environ['OPENBLAS_DEFAULT_NUM_THREADS']='1'
    import cv2
    # OpenCV's global setter is not thread-safe: call only during app startup.
    cv2.setNumThreads(2)

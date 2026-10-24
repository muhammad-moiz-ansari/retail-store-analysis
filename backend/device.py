"""Inference device switch shared by every backend model."""

USE_GPU = False  # set True on a CUDA machine (e.g. RTX 5060 laptop)

DEVICE = "cuda:0" if USE_GPU else "cpu"

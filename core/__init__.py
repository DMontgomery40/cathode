"""Lazy exports for Cathode pipeline helpers."""


def generate_storyboard(*args, **kwargs):
    from .director import generate_storyboard as _generate_storyboard

    return _generate_storyboard(*args, **kwargs)


def generate_image(*args, **kwargs):
    from .image_gen import generate_image as _generate_image

    return _generate_image(*args, **kwargs)


def edit_image(*args, **kwargs):
    from .image_gen import edit_image as _edit_image

    return _edit_image(*args, **kwargs)


def generate_audio(*args, **kwargs):
    from .voice_gen import generate_audio as _generate_audio

    return _generate_audio(*args, **kwargs)


def assemble_video(*args, **kwargs):
    from .video_assembly import assemble_video as _assemble_video

    return _assemble_video(*args, **kwargs)


__all__ = ["generate_storyboard", "generate_image", "edit_image", "generate_audio", "assemble_video"]

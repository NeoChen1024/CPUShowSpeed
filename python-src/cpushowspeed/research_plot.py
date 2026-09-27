"""Common figure export; scientific labels and cohort choices stay with callers."""


def save_figure(fig, output, stem, *, dpi=150, formats=("png", "svg")):
    for suffix in formats:
        fig.savefig(output / f"{stem}.{suffix}", dpi=dpi)

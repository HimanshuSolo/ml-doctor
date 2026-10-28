"""Loss-curve PNG via matplotlib. Imported lazily; never on page load."""
import math


def render_loss_png(curves, out_path, title="loss curves"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5, 3), dpi=100)
    for i, curve in enumerate(curves):
        ys = [y if (y is not None and math.isfinite(y)) else float("nan") for y in curve]
        ax.plot(range(len(ys)), ys, label=f"run {i}")
    ax.set_xlabel("step")
    ax.set_ylabel("loss")
    ax.set_title(title)
    if curves:
        ax.legend(fontsize="small")
    fig.tight_layout()
    fig.savefig(out_path, format="png")
    plt.close(fig)
    return str(out_path)

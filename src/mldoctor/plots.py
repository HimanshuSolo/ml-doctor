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


def render_loss_png_b64(evidence, max_curves=3):
    """Small low-res loss-curve PNG as base64 for the opt-in vision probe.

    Returns (b64, used). Renders nothing when there is no usable curve."""
    curves = (evidence or {}).get("loss_curves") or []
    curves = [c for c in curves if c and any(v is not None for v in c)][:max_curves]
    if not curves:
        return "", False
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(3, 2), dpi=80)
    for i, curve in enumerate(curves):
        ys = [y if (y is not None and math.isfinite(y)) else float("nan") for y in curve]
        ax.plot(range(len(ys)), ys, label=f"run {i}", linewidth=1)
    ax.set_xlabel("step")
    ax.set_ylabel("loss")
    ax.set_title("loss curves")
    fig.tight_layout()
    import base64
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode(), True

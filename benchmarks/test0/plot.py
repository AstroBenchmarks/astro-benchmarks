def plot(input_dir, output_dir):
    import matplotlib.pyplot as plt
    import h5py
    import os

    data_file = os.path.join(input_dir, "data.h5")
    if not os.path.exists(data_file):
        raise ValueError("data.h5 file is required for plotting")

    with h5py.File(data_file, "r") as f:
        rho = f["rho"][:]
        vx = f["vx"][:]
        vy = f["vy"][:]

    fig, axes = plt.subplots(1, 3, figsize=(3, 1))

    axes[0].imshow(rho, origin="lower", cmap="viridis", vmin=0, vmax=1)
    axes[0].set_aspect("equal")
    axes[0].axis("off")

    axes[1].imshow(vx, origin="lower", cmap="bwr", vmin=-1, vmax=1)
    axes[1].set_aspect("equal")
    axes[1].axis("off")

    axes[2].imshow(vy, origin="lower", cmap="bwr", vmin=-1, vmax=1)
    axes[2].set_aspect("equal")
    axes[2].axis("off")

    plt.subplots_adjust(wspace=0, hspace=0, left=0, right=1, top=1, bottom=0)

    plt.savefig(
        os.path.join(output_dir, "result.png"),
        bbox_inches="tight",
        pad_inches=0,
        dpi=128,
    )
    plt.close()

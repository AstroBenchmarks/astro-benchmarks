def plot(input_dir, output_dir):
    import matplotlib.pyplot as plt
    import h5py
    import os

    data_file = os.path.join(input_dir, "data.h5")
    if not os.path.exists(data_file):
        raise ValueError("data.h5 file is required for plotting")

    with h5py.File(data_file, "r") as f:
        rho = f["rho"][:]

    fig, axes = plt.subplots(1, 1, figsize=(1, 1))

    axes.imshow(rho.T, origin="lower", cmap="jet", vmin=0.06, vmax=0.5)
    axes.set_aspect("equal")
    axes.axis("off")

    plt.subplots_adjust(wspace=0, hspace=0, left=0, right=1, top=1, bottom=0)

    plt.savefig(
        os.path.join(output_dir, "result.png"),
        bbox_inches="tight",
        pad_inches=0,
        dpi=512,
    )
    plt.close()

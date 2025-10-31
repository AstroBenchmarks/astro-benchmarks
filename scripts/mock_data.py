# Generate mock data for testing purposes

import h5py
import numpy as np
import os


def generate_mock_data(benchmark_dir):
    # Create the benchmark directory if it doesn't exist
    os.makedirs(benchmark_dir, exist_ok=True)

    # Generate mock data for each file in the benchmark
    filename = "data.h5"
    filepath = os.path.join(benchmark_dir, filename)
    with h5py.File(filepath, "w") as f:
        # Generate mock data
        rho = np.random.rand(128, 128)
        f.create_dataset("rho", data=rho)

        vx = np.random.rand(128, 128)
        f.create_dataset("vx", data=vx)

        vy = np.random.rand(128, 128)
        f.create_dataset("vy", data=vy)


if __name__ == "__main__":
    benchmark_directory = "."
    generate_mock_data(benchmark_directory)

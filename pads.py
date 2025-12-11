import skrf as rf
import matplotlib.pyplot as plt
import numpy as np

def enforce_reciprocal_symmetric(network: rf.Network) -> rf.Network:
    """
    Returns a reciprocal and symmetric version of the given Network.
    Reciprocity -> S = S^T
    Symmetry   -> diagonal elements are averaged, and off-diagonals are mirrored.
    Works for any N-port network.
    """
    # Copy data to avoid modifying the original
    s = network.s.copy()
    n_freq, n_ports, _ = s.shape

    # Enforce reciprocity: S = (S + S^T) / 2 for each frequency point
    for i in range(n_freq):
        s[i] = (s[i] + s[i].T) / 2

    # Enforce symmetry: average the diagonal elements
    for i in range(n_freq):
        avg_diag = np.mean(np.diag(s[i]))
        np.fill_diagonal(s[i], avg_diag)

    # Return a new Network with same frequency, z0, etc.
    new_net = rf.Network(f=network.f, s=s, z0=network.z0)
    return new_net

import numpy as np
import matplotlib.pyplot as plt

def investigate_network(net):
    """
    Investigate Z11 and Z21 relations for a 2-port network.

    Plots:
        • |Z21| / |Z11|
        • Real and Imag parts of Z21/Z11
        • Phase(Z21/Z11)
        • Re{Z21} & Re{Z11}
        • Im{Z21} & Im{Z11}
    """

    Z = net.z                         # shape: (n_freqs, 2, 2)
    Z11 = Z[:, 0, 0]
    Z21 = Z[:, 1, 0]
    freqs = net.frequency.f          # Hz


    # Complex ratio
    ratio = Z21 / Z11
    ratio_mag  = np.abs(ratio)
    ratio_real = np.real(ratio)
    ratio_imag = np.imag(ratio)
    ratio_phase = np.angle(ratio, deg=True)

    fig, axs = plt.subplots(5, 1, figsize=(10, 14), sharex=True)

    # |Z21| / |Z11|
    axs[0].plot(freqs, ratio_mag)
    axs[0].set_ylabel(r"$|Z_{21}/Z_{11}|$")
    axs[0].set_title("Magnitude Ratio |Z21/Z11|")

    # Real ratio
    axs[1].plot(freqs, ratio_real)
    axs[1].set_ylabel(r"Real$\{Z_{21}/Z_{11}\}$")
    axs[1].set_title("Real Part of Z21/Z11")

    # Imag ratio
    axs[2].plot(freqs, ratio_imag)
    axs[2].set_ylabel(r"Imag$\{Z_{21}/Z_{11}\}$")
    axs[2].set_title("Imaginary Part of Z21/Z11")

    # Phase difference
    axs[3].plot(freqs, ratio_phase)
    axs[3].set_ylabel(r"∠(Z21/Z11) [deg]")
    axs[3].set_title("Phase Ratio ∠(Z21/Z11)")

    # Plot the raw Z components for context
    axs[4].plot(freqs, np.real(Z11), label="Re(Z11)")
    axs[4].plot(freqs, np.real(Z21), label="Re(Z21)")
    axs[4].plot(freqs, np.imag(Z11), "--", label="Im(Z11)")
    axs[4].plot(freqs, np.imag(Z21), "--", label="Im(Z21)")
    axs[4].set_ylabel("Ω")
    axs[4].set_xlabel("Frequency (Hz)")
    axs[4].legend()
    axs[4].set_title("Raw Impedances (Real & Imag)")

    plt.tight_layout()
    plt.show()



def extract_pad(net: rf.Network):
    """
    Extract T-pad impedances Z1, Z2, Z3 per frequency with root selection rules:
      Im(Z1) > 0  (series inductive)
      Im(Z2) < 0  (shunt capacitive)
    Assumption: Z1 * k = Z3
    """
    Z = net.z                 # shape: (nf, 2, 2)
    Z11 = Z[:, 0, 0]
    Z21 = Z[:, 1, 0]
    f = net.f
    k = - Z21 **2 / (-1 * (2 * Z21 * Z11 + Z21 **2))
    #find Z1
    a = 1
    b = -2 * (Z11 + Z21 * k)
    c = Z11 * Z11 - Z21 * Z21
    disc = b * b - 4 * a * c
    x1 = (-1 * b + np.sqrt(disc)) / (2 * a)
    x2 = (-1 * b - np.sqrt(disc)) / (2 * a)

    # Choose the solution with positive imaginary part (inductive)
    Z1 = np.where(np.imag(x1) >= 0, x1, x2)

    #find Z2 from Z1

    Z2 = Z11 + Z21 - Z1

    #set Z3
    Z3 = k * Z1

    return f, Z1, Z2, Z3


def tee_network(freqs_hz, Z1, Z2, Z3, Z0=50):
    """
    Creates a Tee network as a 2-port in scikit-rf.

    Z1: series impedance on Port 1 side
    Z2: shunt impedance to ground (T branch)
    Z3: series impedance on Port 2 side
    Z0: characteristic impedance
    freqs_hz: array of frequencies in Hz
    """
    f = rf.Frequency.from_f(freqs_hz, unit='Hz')
    n = len(freqs_hz)

    # Z-parameter matrix for a generic T-network
    # Z11 = Z1 + Z2
    # Z12 = Z2
    # Z21 = Z2
    # Z22 = Z2 + Z3
    z = np.zeros((n, 2, 2), dtype=complex)
    z[:,0,0] = Z1 + Z2
    z[:,0,1] = Z2
    z[:,1,0] = Z2
    z[:,1,1] = Z2 + Z3

    ntwk = rf.Network(frequency=f, z=z, z0=Z0)
    return ntwk

def get_pads(file1, file2):
    L_line = rf.Network(file1)
    L2_line = rf.Network(file2)

    pads = L_line ** L2_line.inv ** L_line

    f, Z1, Z2, Z3 = extract_pad(enforce_reciprocal_symmetric(pads))

    left_pad = tee_network(f, Z1 = Z1, Z2 = Z2, Z3 = Z3)

    right_pad = tee_network(f, Z1 = Z3, Z2 = Z2, Z3 = Z1)

    left_pad.write_touchstone(f"left_pad_{year}_{length}")
    right_pad.write_touchstone(f"right_pad_{year}_{length}")

    return left_pad, right_pad

year = 2015
length = 600

#below will be parameters to feed into the backend
file1 = f'{year}_{length}.s2p'
file2 = f'{year}_{2 * length}.s2p'

lp, rp = get_pads(file1, file2)

length = 300

#below will be parameters to feed into the backend
file1 = f'{year}_{length}.s2p'
file2 = f'{year}_{2 * length}.s2p'

lp, rp = get_pads(file1, file2)

def run_pad_extraction(file1, file2, year, length):
    return get_pads(file1, file2, year, length)


if __name__ == "__main__":
    import sys
    file1 = sys.argv[1]
    file2 = sys.argv[2]
    year = int(sys.argv[3])
    length = int(sys.argv[4])

    left_name, right_name = run_pad_extraction(file1, file2, year, length)

    # print each output filename on its own line
    print(left_name)
    print(right_name)
